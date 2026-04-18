"""Analysis router - handles multi-hazard land suitability analysis execution and results."""

import logging
import json
from typing import List, Optional, Dict, Any
from uuid import uuid4, UUID
from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.user import User as UserModel
from app.schemas import AnalysisResponse, AnalysisCreate, AnalysisStatus
from app.middleware.auth_middleware import (
    get_current_user,
    get_optional_user,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Vanuatu bounding box (approximate)
VANUATU_BBOX = {
    "min_lat": -20.5,
    "max_lat": -12.0,
    "min_lon": 166.0,
    "max_lon": 170.0
}


# ============================================================================
# Request/Response Models
# ============================================================================

class AnalysisRunRequest(BaseModel):
    """Request model for running new analysis."""
    analysis_name: str = Field(..., description="Name of the analysis")
    description: Optional[str] = Field(None, description="Analysis description")
    aoi_geom: Dict[str, Any] = Field(
        ...,
        description="GeoJSON geometry for area of interest"
    )
    assessment_type: str = Field(
        ...,
        description="Type of assessment (development, agriculture, both)"
    )
    personas_requested: List[str] = Field(
        default=[],
        description="List of personas to generate analysis for"
    )
    ahp_weight_set: Optional[str] = Field(
        None,
        description="Name of predefined AHP weight set"
    )
    custom_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom AHP weights (must sum to 1.0)"
    )
    input_datasets: Optional[List[str]] = Field(
        None,
        description="List of dataset upload IDs to use"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_name": "Flood Risk - Efate",
                "description": "Agricultural suitability assessment",
                "aoi_geom": {
                    "type": "Polygon",
                    "coordinates": [[[167.0, -17.5], [167.5, -17.5], [167.5, -17.0], [167.0, -17.0], [167.0, -17.5]]]
                },
                "assessment_type": "agriculture",
                "personas_requested": ["farmer", "government"]
            }
        }


class AnalysisHistoryResponse(BaseModel):
    """Response model for analysis history."""
    analyses: List[AnalysisResponse] = Field(..., description="List of analyses")
    total_count: int = Field(..., description="Total number of analyses")
    limit: int = Field(..., description="Result limit used")
    offset: int = Field(..., description="Result offset used")


class AnalysisShareResponse(BaseModel):
    """Response model for analysis share information."""
    share_token: str = Field(..., description="Share token for public access")
    share_url: str = Field(..., description="Public URL for accessing analysis")
    share_expires_at: datetime = Field(..., description="Token expiration time")


# ============================================================================
# Helper Functions
# ============================================================================

def validate_aoi_geometry(geom: Dict[str, Any]) -> None:
    """
    Validate AOI geometry is within Vanuatu bounds.

    Args:
        geom: GeoJSON geometry dict

    Raises:
        HTTPException: If geometry is invalid or outside Vanuatu
    """
    if not geom or "type" not in geom:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid GeoJSON geometry"
        )

    geom_type = geom.get("type")
    coordinates = geom.get("coordinates", [])

    if not coordinates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GeoJSON geometry has no coordinates"
        )

    # Extract all coordinate pairs based on geometry type
    all_coords = []

    if geom_type == "Point":
        all_coords = [coordinates]
    elif geom_type in ["LineString", "MultiPoint"]:
        all_coords = coordinates
    elif geom_type == "Polygon":
        # Extract from first ring (outer ring)
        all_coords = coordinates[0] if coordinates else []
    elif geom_type == "MultiLineString":
        for line in coordinates:
            all_coords.extend(line)
    elif geom_type == "MultiPolygon":
        for polygon in coordinates:
            if polygon:
                all_coords.extend(polygon[0])
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported geometry type: {geom_type}"
        )

    # Validate all coordinates are within Vanuatu bounds
    bbox = VANUATU_BBOX
    for coord in all_coords:
        if len(coord) < 2:
            continue
        lon, lat = coord[0], coord[1]

        if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and
                bbox["min_lon"] <= lon <= bbox["max_lon"]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"AOI geometry contains coordinates outside Vanuatu bounds: ({lon}, {lat})"
            )


def validate_assessment_type(assessment_type: str) -> None:
    """
    Validate assessment type is one of allowed values.

    Args:
        assessment_type: Assessment type string

    Raises:
        HTTPException: If assessment type is invalid
    """
    allowed = ["development", "agriculture", "both"]
    if assessment_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid assessment_type. Must be one of: {allowed}"
        )


def validate_custom_weights(weights: Dict[str, float]) -> None:
    """
    Validate custom AHP weights sum to 1.0.

    Args:
        weights: Dictionary of weight values

    Raises:
        HTTPException: If weights don't sum to 1.0
    """
    if not weights:
        return

    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 0.001:  # Allow small floating point error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Custom weights must sum to 1.0 (got {total:.4f})"
        )


# ============================================================================
# Routes
# ============================================================================

@router.post("/run", response_model=AnalysisResponse, status_code=202)
async def run_analysis(
    request: AnalysisRunRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AnalysisResponse:
    """
    Start new multi-hazard land suitability analysis.

    Validates input parameters, creates analysis record with status='queued',
    and dispatches async task via Celery. Returns immediately with analysis_id
    for polling status.

    Args:
        request: Analysis request with AOI, assessment type, parameters
        user: Current authenticated user
        db: Database session

    Returns:
        AnalysisResponse with analysis_id for polling

    Raises:
        HTTPException: 400-500 for validation or processing errors
    """
    try:
        # Validate input parameters
        validate_aoi_geometry(request.aoi_geom)
        validate_assessment_type(request.assessment_type)

        if request.custom_weights:
            validate_custom_weights(request.custom_weights)

        # Create analysis record
        analysis = Analysis(
            analysis_name=request.analysis_name,
            analysis_type=request.assessment_type,
            created_by=UUID(user.user_id),
            description=request.description,
            status="queued",
            processing_status="pending",
            is_public=False,
            is_archived=False
        )

        # Set geometry - convert GeoJSON to WKT for storage
        # For now, store as JSON in metadata
        analysis.study_area_geom = None  # Will be set by task
        analysis.metadata = {
            "aoi_geom": request.aoi_geom,
            "personas_requested": request.personas_requested,
            "ahp_weight_set": request.ahp_weight_set,
            "custom_weights": request.custom_weights,
            "input_datasets": request.input_datasets
        }

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        logger.info(
            f"Created analysis {analysis.id} '{request.analysis_name}' "
            f"by user {user.email}"
        )

        # Dispatch Celery task for analysis execution
        task = celery_app.send_task(
            'app.tasks.run_analysis',
            args=[str(analysis.id)],
            queue='analysis'
        )

        logger.info(f"Dispatched analysis task {task.id} for analysis {analysis.id}")

        return AnalysisResponse(
            analysis_id=str(analysis.id),
            name=analysis.analysis_name,
            description=analysis.description,
            status=analysis.status,
            user_id=str(analysis.created_by),
            area_of_interest=request.aoi_geom,
            hazard_types=[],
            land_use_type=request.assessment_type,
            area_sq_km=None,
            suitability_score=None,
            primary_risk=None,
            created_at=analysis.created_at,
            completed_at=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting analysis"
        )


@router.get("/{analysis_id}", response_model=AnalysisResponse, status_code=200)
async def get_analysis(
    analysis_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AnalysisResponse:
    """
    Get analysis result and current processing status.

    Returns full analysis details including results if available, geometry,
    statistics, and processing information.

    Args:
        analysis_id: UUID of the analysis
        user: Current authenticated user
        db: Database session

    Returns:
        AnalysisResponse with analysis details

    Raises:
        HTTPException: 404 if analysis not found
    """
    try:
        analysis = db.query(Analysis).filter(
            Analysis.id == UUID(analysis_id)
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis '{analysis_id}' not found"
            )

        # Check permissions - user must be creator or have admin role
        if str(analysis.created_by) != user.user_id and user.role != "admin":
            if not analysis.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this analysis"
                )

        metadata = analysis.metadata or {}

        logger.info(f"Retrieved analysis {analysis_id} for user {user.email}")

        return AnalysisResponse(
            analysis_id=str(analysis.id),
            name=analysis.analysis_name,
            description=analysis.description,
            status=analysis.status,
            user_id=str(analysis.created_by),
            area_of_interest=metadata.get("aoi_geom", {}),
            hazard_types=metadata.get("hazard_types", []),
            land_use_type=analysis.analysis_type,
            area_sq_km=analysis.statistics.get("area_sq_km") if analysis.statistics else None,
            suitability_score=analysis.statistics.get("mean_suitability") if analysis.statistics else None,
            primary_risk=analysis.statistics.get("primary_risk") if analysis.statistics else None,
            created_at=analysis.created_at,
            completed_at=analysis.updated_at if analysis.status == "completed" else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving analysis"
        )


@router.get("", response_model=AnalysisHistoryResponse, status_code=200)
async def list_analyses(
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AnalysisHistoryResponse:
    """
    List past analyses with pagination (paginated).

    Returns analyses created by the current user, ordered by creation date.
    Admin users can see all analyses.

    Args:
        limit: Maximum results to return (default 20, max 100)
        offset: Number of results to skip for pagination
        user: Current authenticated user
        db: Database session

    Returns:
        AnalysisHistoryResponse with paginated analysis list

    Raises:
        HTTPException: 500 on database error
    """
    try:
        # Build query
        query = db.query(Analysis)

        if user.role != "admin":
            # Non-admin users see only their own analyses
            query = query.filter(Analysis.created_by == UUID(user.user_id))

        query = query.filter(Analysis.is_archived == False)

        # Get total count
        total_count = query.count()

        # Get paginated results
        analyses = query.order_by(
            desc(Analysis.created_at)
        ).limit(limit).offset(offset).all()

        # Convert to response objects
        analysis_responses = []
        for analysis in analyses:
            metadata = analysis.metadata or {}

            analysis_responses.append(AnalysisResponse(
                analysis_id=str(analysis.id),
                name=analysis.analysis_name,
                description=analysis.description,
                status=analysis.status,
                user_id=str(analysis.created_by),
                area_of_interest=metadata.get("aoi_geom", {}),
                hazard_types=metadata.get("hazard_types", []),
                land_use_type=analysis.analysis_type,
                area_sq_km=analysis.statistics.get("area_sq_km") if analysis.statistics else None,
                suitability_score=analysis.statistics.get("mean_suitability") if analysis.statistics else None,
                primary_risk=analysis.statistics.get("primary_risk") if analysis.statistics else None,
                created_at=analysis.created_at,
                completed_at=analysis.updated_at if analysis.status == "completed" else None
            ))

        logger.info(
            f"Retrieved {len(analyses)} analyses for user {user.email} "
            f"(total: {total_count})"
        )

        return AnalysisHistoryResponse(
            analyses=analysis_responses,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error listing analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving analyses"
        )


@router.get("/share/{share_token}", response_model=AnalysisResponse, status_code=200)
async def get_shared_analysis(
    share_token: str,
    db: Session = Depends(get_db)
) -> AnalysisResponse:
    """
    Get public read-only view of shared analysis (no authentication required).

    Validates share token existence and expiration. Returns filtered analysis
    results appropriate for public visibility.

    Args:
        share_token: Public share token for the analysis
        db: Database session

    Returns:
        AnalysisResponse with public data (filtered for sensitivity)

    Raises:
        HTTPException: 404 if token invalid, 401 if token expired
    """
    try:
        # Find analysis by share token in metadata
        analysis = db.query(Analysis).filter(
            Analysis.is_public == True
        ).all()

        # Check each analysis for matching share token
        found_analysis = None
        for a in analysis:
            metadata = a.metadata or {}
            if metadata.get("share_token") == share_token:
                found_analysis = a
                break

        if not found_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share token not found"
            )

        # Check expiration
        share_expires = found_analysis.metadata.get("share_expires_at")
        if share_expires:
            expires_dt = datetime.fromisoformat(share_expires)
            if datetime.utcnow() > expires_dt:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Share token has expired"
                )

        metadata = found_analysis.metadata or {}

        logger.info(f"Accessed shared analysis via token {share_token[:20]}...")

        return AnalysisResponse(
            analysis_id=str(found_analysis.id),
            name=found_analysis.analysis_name,
            description=found_analysis.description,
            status=found_analysis.status,
            user_id=str(found_analysis.created_by),
            area_of_interest=metadata.get("aoi_geom", {}),
            hazard_types=metadata.get("hazard_types", []),
            land_use_type=found_analysis.analysis_type,
            area_sq_km=found_analysis.statistics.get("area_sq_km") if found_analysis.statistics else None,
            suitability_score=found_analysis.statistics.get("mean_suitability") if found_analysis.statistics else None,
            primary_risk=found_analysis.statistics.get("primary_risk") if found_analysis.statistics else None,
            created_at=found_analysis.created_at,
            completed_at=found_analysis.updated_at if found_analysis.status == "completed" else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving shared analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving shared analysis"
        )
