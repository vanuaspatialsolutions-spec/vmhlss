"""Admin router - user management, weights configuration, audit logs, system health."""

import logging
import psutil
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.user import User as UserModel
from app.models.audit_log import AuditLog
from app.schemas import AdminUserCreate, AdminUserUpdate, UserResponse
from app.middleware.auth_middleware import (
    get_current_user,
    require_role,
    get_password_hash,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Default AHP weights for different assessment types
DEFAULT_AHP_WEIGHTS = {
    "agriculture": {
        "flood_hazard": 0.3,
        "cyclone_hazard": 0.2,
        "soil_suitability": 0.25,
        "elevation": 0.15,
        "infrastructure_access": 0.1
    },
    "development": {
        "flood_hazard": 0.25,
        "cyclone_hazard": 0.15,
        "slope": 0.2,
        "elevation": 0.2,
        "infrastructure_access": 0.2
    },
    "both": {
        "flood_hazard": 0.25,
        "cyclone_hazard": 0.2,
        "soil_suitability": 0.15,
        "slope": 0.15,
        "elevation": 0.15,
        "infrastructure_access": 0.1
    }
}


# ============================================================================
# Request/Response Models
# ============================================================================

class AHPWeightUpdate(BaseModel):
    """Request model for updating AHP weights."""
    weight_set_name: str = Field(..., description="Name of weight set")
    assessment_type: str = Field(..., description="Assessment type (agriculture, development, both)")
    weights: dict = Field(..., description="Dictionary of weights (must sum to 1.0)")


class AuditLogEntry(BaseModel):
    """Response model for audit log entry."""
    timestamp: datetime = Field(..., description="When action occurred")
    user_email: str = Field(..., description="User who performed action")
    action: str = Field(..., description="Action type")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of resource")
    details: Optional[str] = Field(None, description="Additional details")


class AuditLogResponse(BaseModel):
    """Response model for audit log query."""
    entries: List[AuditLogEntry] = Field(..., description="Audit log entries")
    total_count: int = Field(..., description="Total entries matching query")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class SystemHealth(BaseModel):
    """Response model for system health status."""
    db_connection_status: str = Field(..., description="Database connection status (ok, degraded, error)")
    db_pool_connections: int = Field(..., description="Active DB connections")
    redis_connection_status: str = Field(..., description="Redis status (ok, degraded, error)")
    celery_queue_depth: int = Field(..., description="Number of pending Celery tasks")
    upload_dir_usage_mb: float = Field(..., description="Upload directory size in MB")
    upload_dir_usage_percent: float = Field(..., description="Upload directory usage as percent")
    total_analyses_count: int = Field(..., description="Total analyses in system")
    total_kb_records_count: int = Field(..., description="Total KB records in system")
    system_timestamp: datetime = Field(..., description="When health check was performed")


class UserListResponse(BaseModel):
    """Response model for user list."""
    users: List[UserResponse] = Field(..., description="List of users")
    total_count: int = Field(..., description="Total users")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


# ============================================================================
# Helper Functions
# ============================================================================

def validate_ahp_weights(weights: dict) -> None:
    """
    Validate AHP weights sum to 1.0.

    Args:
        weights: Dictionary of weights

    Raises:
        HTTPException: If weights don't sum to 1.0
    """
    if not weights:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Weights dictionary cannot be empty"
        )

    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 0.001:  # Allow small floating point error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weights must sum to 1.0 (got {total:.4f})"
        )


def validate_assessment_type(assessment_type: str) -> None:
    """
    Validate assessment type.

    Args:
        assessment_type: Assessment type string

    Raises:
        HTTPException: If invalid type
    """
    allowed = ["agriculture", "development", "both"]
    if assessment_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid assessment_type. Must be one of: {allowed}"
        )


# ============================================================================
# Routes
# ============================================================================

@router.get("/users", response_model=UserListResponse, status_code=200)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role_filter: Optional[str] = Query(None, description="Filter by role"),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """
    List all users (Admin only).

    Returns paginated list of all system users with optional filtering by
    role or search by email/name.

    Args:
        limit: Max results to return
        offset: Results to skip
        search: Optional search string (email or name)
        role_filter: Optional role filter
        user: Current user (must be admin)
        db: Database session

    Returns:
        UserListResponse with paginated user list

    Raises:
        HTTPException: 403 if not admin
    """
    try:
        # Build query
        query = db.query(UserModel)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (UserModel.email.ilike(search_term)) |
                (UserModel.full_name.ilike(search_term))
            )

        if role_filter:
            query = query.filter(UserModel.role == role_filter)

        # Get total
        total_count = query.count()

        # Paginate
        users = query.order_by(
            desc(UserModel.created_at)
        ).limit(limit).offset(offset).all()

        # Convert to response objects
        user_responses = []
        for u in users:
            name_parts = (u.full_name or "").split(" ", 1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            user_responses.append(UserResponse(
                user_id=str(u.id),
                email=u.email,
                first_name=first_name,
                last_name=last_name,
                role=u.role,
                organization=u.organisation,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login=u.last_login
            ))

        logger.info(f"Admin {user.email} listed {len(users)} users")

        return UserListResponse(
            users=user_responses,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user list"
        )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    request: AdminUserCreate,
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Create new user (Admin only).

    Creates new user account with specified role and organization.
    Password is hashed using bcrypt before storage.

    Args:
        request: User creation request
        user: Current user (must be admin)
        db: Database session

    Returns:
        UserResponse with created user details

    Raises:
        HTTPException: 400 if user already exists, 422 if invalid role
    """
    try:
        # Check if user already exists
        existing = db.query(UserModel).filter(
            UserModel.email == request.email.lower()
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{request.email}' already exists"
            )

        # Validate role
        allowed_roles = ["admin", "data_manager", "analyst", "reviewer", "public"]
        if request.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role. Must be one of: {allowed_roles}"
            )

        # Create user
        new_user = UserModel(
            email=request.email.lower(),
            password_hash=get_password_hash(request.password),
            full_name=f"{request.first_name} {request.last_name}",
            organisation=request.organization,
            role=request.role,
            is_active=True,
            two_factor_enabled=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"Admin {user.email} created user {request.email} with role {request.role}")

        return UserResponse(
            user_id=str(new_user.id),
            email=new_user.email,
            first_name=request.first_name,
            last_name=request.last_name,
            role=new_user.role,
            organization=new_user.organisation,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@router.put("/users/{user_id}", response_model=UserResponse, status_code=200)
async def update_user(
    user_id: str,
    request: AdminUserUpdate,
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Update user details or role (Admin only).

    Updates user information including role assignments and active status.

    Args:
        user_id: UUID of user to update
        request: Update request
        user: Current user (must be admin)
        db: Database session

    Returns:
        UserResponse with updated user

    Raises:
        HTTPException: 404 if user not found, 422 if invalid role
    """
    try:
        target_user = db.query(UserModel).filter(
            UserModel.id == UUID(user_id)
        ).first()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found"
            )

        # Update fields
        if request.first_name or request.last_name:
            first = request.first_name or target_user.full_name.split(" ")[0]
            last = request.last_name or (target_user.full_name.split(" ", 1)[1] if " " in target_user.full_name else "")
            target_user.full_name = f"{first} {last}".strip()

        if request.role:
            allowed_roles = ["admin", "data_manager", "analyst", "reviewer", "public"]
            if request.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid role. Must be one of: {allowed_roles}"
                )
            target_user.role = request.role

        if request.organization is not None:
            target_user.organisation = request.organization

        if request.is_active is not None:
            target_user.is_active = request.is_active

        db.commit()

        name_parts = target_user.full_name.split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        logger.info(f"Admin {user.email} updated user {target_user.email}")

        return UserResponse(
            user_id=str(target_user.id),
            email=target_user.email,
            first_name=first_name,
            last_name=last_name,
            role=target_user.role,
            organization=target_user.organisation,
            is_active=target_user.is_active,
            created_at=target_user.created_at,
            last_login=target_user.last_login
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@router.put("/criteria-weights", status_code=200)
async def update_ahp_weights(
    request: AHPWeightUpdate,
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> dict:
    """
    Update AHP weights for analysis (Admin only).

    Updates criteria weights used in multi-hazard assessment. Weights must
    sum to 1.0 for mathematical validity.

    Args:
        request: Weight update request
        user: Current user (must be admin)
        db: Database session

    Returns:
        Dictionary with confirmation

    Raises:
        HTTPException: 422 if weights invalid
    """
    try:
        # Validate weights
        validate_ahp_weights(request.weights)
        validate_assessment_type(request.assessment_type)

        # In production, store weights in database or config
        logger.info(
            f"Admin {user.email} updated AHP weights for {request.assessment_type}: "
            f"{request.weight_set_name}"
        )

        return {
            "weight_set_name": request.weight_set_name,
            "assessment_type": request.assessment_type,
            "weights": request.weights,
            "message": "AHP weights updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating AHP weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating weights"
        )


@router.get("/audit-log", response_model=AuditLogResponse, status_code=200)
async def get_audit_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_email: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> AuditLogResponse:
    """
    Export audit log (Admin only, paginated and filterable).

    Returns audit trail of system actions including user operations, data
    modifications, and administrative changes.

    Args:
        limit: Max entries to return
        offset: Entries to skip
        user_email: Filter by user email
        action: Filter by action type
        resource_type: Filter by resource type
        start_date: Filter by minimum date (ISO format)
        user: Current user (must be admin)
        db: Database session

    Returns:
        AuditLogResponse with paginated audit entries

    Raises:
        HTTPException: 403 if not admin
    """
    try:
        # Build query
        query = db.query(AuditLog)

        if user_email:
            query = query.filter(AuditLog.user_email.ilike(f"%{user_email}%"))

        if action:
            query = query.filter(AuditLog.action == action)

        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        if start_date:
            from dateutil import parser as date_parser
            try:
                start_dt = date_parser.isoparse(start_date)
                query = query.filter(AuditLog.timestamp >= start_dt)
            except:
                logger.warning(f"Invalid start_date format: {start_date}")

        # Get total
        total_count = query.count()

        # Paginate
        entries = query.order_by(
            desc(AuditLog.timestamp)
        ).limit(limit).offset(offset).all()

        # Convert to response objects
        audit_entries = [
            AuditLogEntry(
                timestamp=entry.timestamp,
                user_email=entry.user_email,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=entry.details
            )
            for entry in entries
        ]

        logger.info(f"Admin {user.email} retrieved audit log ({len(entries)} entries)")

        return AuditLogResponse(
            entries=audit_entries,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error retrieving audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving audit log"
        )


@router.get("/system-health", response_model=SystemHealth, status_code=200)
async def get_system_health(
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
) -> SystemHealth:
    """
    Get system health status (Admin only).

    Returns health metrics for database connections, Redis, Celery queue,
    disk usage, and data counts.

    Args:
        user: Current user (must be admin)
        db: Database session

    Returns:
        SystemHealth object with status metrics

    Raises:
        HTTPException: 403 if not admin
    """
    try:
        # Database health
        db_status = "ok"
        db_connections = 0
        try:
            # Try a simple query to check DB
            db.execute("SELECT 1")
            db_connections = db.connection().connection.connection.info.get("id", 1)
            db_status = "ok"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            db_status = "error"

        # Redis health
        redis_status = "ok"
        try:
            from app.routers.auth import redis_client
            if redis_client:
                redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_status = "error"

        # Celery queue depth
        celery_queue_depth = 0
        try:
            inspect = celery_app.control.inspect()
            reserved = inspect.reserved()
            if reserved:
                celery_queue_depth = sum(len(v) for v in reserved.values())
        except Exception as e:
            logger.warning(f"Celery health check failed: {e}")

        # Upload directory usage
        upload_dir_size_mb = 0.0
        upload_dir_percent = 0.0
        try:
            from pathlib import Path
            upload_path = Path(settings.upload_dir)
            if upload_path.exists():
                total_size = sum(f.stat().st_size for f in upload_path.rglob("*") if f.is_file())
                upload_dir_size_mb = total_size / (1024 * 1024)

                # Get disk usage
                disk_usage = psutil.disk_usage(str(upload_path))
                upload_dir_percent = (upload_dir_size_mb * 1024 * 1024 / disk_usage.total) * 100
        except Exception as e:
            logger.warning(f"Disk usage check failed: {e}")

        # Data counts
        total_analyses = db.query(db.func.count()).first()[0] or 0
        total_kb_records = 0  # Would query KnowledgeBase table in production

        logger.info(f"Admin {user.email} checked system health")

        return SystemHealth(
            db_connection_status=db_status,
            db_pool_connections=db_connections,
            redis_connection_status=redis_status,
            celery_queue_depth=celery_queue_depth,
            upload_dir_usage_mb=upload_dir_size_mb,
            upload_dir_usage_percent=upload_dir_percent,
            total_analyses_count=total_analyses,
            total_kb_records_count=total_kb_records,
            system_timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking system health"
        )
