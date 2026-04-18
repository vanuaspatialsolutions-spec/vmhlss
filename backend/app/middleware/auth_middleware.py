from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import JWTError, jwt
from typing import Optional, Callable, List
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT
oauth2_scheme = HTTPBearer()

# Role-based permission mapping
ROLE_PERMISSIONS = {
    "admin": ["*"],
    "data_manager": ["read", "upload", "document_upload", "georef", "kb_confirm"],
    "analyst": ["read", "analysis_run", "report_generate"],
    "reviewer": ["read", "report_download"],
    "public": ["analysis_run_limited", "report_download_own"]
}


class User:
    """User model for authentication context"""

    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        organization: Optional[str] = None,
        is_active: bool = True
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.organization = organization
        self.is_active = is_active

    @property
    def permissions(self) -> List[str]:
        """Get all permissions for this user's role"""
        return ROLE_PERMISSIONS.get(self.role, [])

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        perms = self.permissions
        return "*" in perms or permission in perms


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary with token claims
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Dictionary with token claims

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract and validate current user from JWT token.

    Args:
        credentials: HTTP bearer credentials from request
        db: Database session

    Returns:
        User object with claims from token

    Raises:
        HTTPException: If token is invalid or user is inactive
    """
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None or email is None:
            raise credential_exception

        token_type = payload.get("type")
        if token_type == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cannot use refresh token for API access"
            )

    except JWTError:
        logger.warning("Invalid JWT token")
        raise credential_exception

    # Create user object
    user = User(
        user_id=user_id,
        email=email,
        role=role,
        organization=payload.get("organization")
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Dependency to extract user from JWT token for optional authentication.
    Returns None if no token is provided.

    Args:
        credentials: Optional HTTP bearer credentials from request

    Returns:
        User object or None if no valid token
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None or email is None:
            return None

        token_type = payload.get("type")
        if token_type == "refresh":
            return None

        return User(
            user_id=user_id,
            email=email,
            role=role,
            organization=payload.get("organization")
        )

    except JWTError:
        return None


def require_role(*roles: str) -> Callable:
    """
    Dependency factory to require one of specified roles.

    Args:
        *roles: Variable number of role names to require

    Returns:
        Dependency function for FastAPI
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' does not have access to this resource"
            )
        return user

    return role_checker


def require_permission(permission: str) -> Callable:
    """
    Dependency factory to require a specific permission.

    Args:
        permission: Permission string to check

    Returns:
        Dependency function for FastAPI
    """

    async def permission_checker(
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have permission '{permission}'"
            )
        return user

    return permission_checker


def filter_sensitive_data(data: dict, user: Optional[User]) -> dict:
    """
    Filter sensitive data based on user role.

    Args:
        data: Dictionary containing potentially sensitive data
        user: User object with role information

    Returns:
        Filtered dictionary with sensitive data removed or modified
    """
    if user is None:
        # No user - return empty dict
        return {}

    if user.role == "admin" or user.role == "data_manager":
        # Admin and data managers see everything
        return data

    filtered = data.copy()

    # For public and reviewer roles, filter sensitive records
    if user.role in ["public", "reviewer"]:
        # Only allow records with specific sensitivity flags
        if "sensitivity_flag" in filtered:
            if filtered["sensitivity_flag"] not in ["customary", "cadastral"]:
                filtered = {}

        # Blur community point coordinates to 500m precision (0.005 degrees)
        if "coordinates" in filtered and filtered.get("feature_type") == "community_point":
            coords = filtered["coordinates"]
            filtered["coordinates"] = blur_coordinates(
                coords["latitude"],
                coords["longitude"],
                precision=0.005
            )

    return filtered


def blur_coordinates(
    latitude: float,
    longitude: float,
    precision: float = 0.005
) -> dict:
    """
    Blur coordinates to specified precision (in degrees).

    Args:
        latitude: Original latitude
        longitude: Original longitude
        precision: Precision level in degrees (default 0.005 degrees = ~500m)

    Returns:
        Dictionary with blurred coordinates
    """
    blurred_lat = round(latitude / precision) * precision
    blurred_lon = round(longitude / precision) * precision

    return {
        "latitude": blurred_lat,
        "longitude": blurred_lon
    }
