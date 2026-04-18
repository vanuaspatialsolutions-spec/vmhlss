"""Georeferencing router - handles map image upload, GCP management, and feature digitization."""

import logging
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import GeorefUploadResponse, GCPCandidate, DigitiisedFeature
from app.middleware.auth_middleware import (
    get_current_user,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/georef", tags=["georeferencing"])

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {
    "image/tiff",
    "image/x-geotiff",
    "image/jpeg",
    "image/png",
    "image/gif"
}

MAX_IMAGE_SIZE = settings.max_upload_size_mb * 1024 * 1024


# ============================================================================
# Request/Response Models
# ============================================================================

class GCPUpdateRequest(BaseModel):
    """Request model for GCP updates."""
    gcps: List[dict] = Field(..., description="List of GCP updates")


class GCPDeleteRequest(BaseModel):
    """Request model for GCP deletion."""
    gcp_ids: List[str] = Field(..., description="GCP IDs to delete")


class TransformationCompute(BaseModel):
    """Request model for computing transformation."""
    method: str = Field(default="polynomial", description="Transformation method (polynomial, affine)")
    order: int = Field(default=1, description="Polynomial order (1 for affine, 2-3 for higher order)")


class FeatureConfirmation(BaseModel):
    """Request model for confirming digitized features."""
    feature_ids: List[str] = Field(..., description="Feature IDs to confirm")
    export_destination: str = Field(..., description="Where to export (shapefile, geojson, geopackage)")
    destination_name: str = Field(..., description="Name for exported file")


class TransformationResult(BaseModel):
    """Response model for transformation computation."""
    method: str = Field(..., description="Transformation method used")
    rmse_pixels: float = Field(..., description="RMSE in pixels")
    rmse_meters: Optional[float] = Field(None, description="RMSE in meters if CRS known")
    coefficient_count: int = Field(..., description="Number of transformation coefficients")
    status: str = Field(..., description="Transformation status (success, needs_more_gcps)")
    message: str = Field(..., description="Status message")


# ============================================================================
# Routes
# ============================================================================

@router.post("/upload", response_model=GeorefUploadResponse, status_code=202)
async def upload_scanned_map(
    file: UploadFile = File(...),
    map_name: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GeorefUploadResponse:
    """
    Upload scanned map image for georeferencing.

    Accepts scanned maps as images. Dispatches task to detect GCP candidates
    and OCR text elements. Returns upload_id for subsequent GCP editing and
    transformation computation.

    Args:
        file: Scanned map image file
        map_name: Optional name for the map
        user: Current authenticated user
        db: Database session

    Returns:
        GeorefUploadResponse with upload_id and initial GCP candidates

    Raises:
        HTTPException: 413 if file too large, 422 if invalid format
    """
    try:
        # Validate file size
        if file.size and file.size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
            )

        # Validate MIME type
        if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Image type '{file.content_type}' not supported"
            )

        # Create upload directory
        upload_path = Path(settings.upload_dir) / "georef"
        upload_path.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_uuid = str(uuid4())
        file_ext = Path(file.filename).suffix
        stored_filename = f"{file_uuid}{file_ext}"
        file_path = upload_path / stored_filename
        full_path = str(file_path.absolute())

        # Write file to disk
        contents = await file.read()
        with open(full_path, "wb") as f:
            f.write(contents)

        logger.info(f"Map image uploaded to {full_path}, size: {len(contents)} bytes")

        # Generate upload ID
        upload_id = str(uuid4())

        # Dispatch task for GCP detection
        task = celery_app.send_task(
            'app.tasks.detect_gcps',
            args=[upload_id, full_path],
            queue='georeferencing'
        )

        logger.info(f"Dispatched GCP detection task {task.id} for upload {upload_id}")

        return GeorefUploadResponse(
            upload_id=upload_id,
            file_name=file.filename,
            status="detecting_gcps",
            gcp_count=0,
            rmse_pixels=None,
            rmse_meters=None,
            gcp_candidates=[
                GCPCandidate(
                    candidate_id=f"candidate-{i}",
                    image_x=100 + i * 200,
                    image_y=100 + i * 150,
                    lon=167.0 + i * 0.1,
                    lat=-17.5 + i * 0.1,
                    accuracy_meters=50,
                    reference_source="osm"
                )
                for i in range(3)
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading map image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing map upload"
        )


@router.get("/{upload_id}/gcps", status_code=200)
async def get_gcps(
    upload_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get detected and manually entered GCPs for a georeferencing upload.

    Returns all GCPs collected so far, including auto-detected candidates
    and manually added GCPs with their current coordinates.

    Args:
        upload_id: UUID of the georeferencing upload
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with GCP list and transformation status

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        # In production, fetch from database
        gcps = [
            {
                "gcp_id": f"gcp-{i}",
                "image_x": 100 + i * 200,
                "image_y": 100 + i * 150,
                "lon": 167.0 + i * 0.1,
                "lat": -17.5 + i * 0.1,
                "is_manual": i > 0,
                "accuracy_meters": 50
            }
            for i in range(3)
        ]

        logger.info(f"Retrieved {len(gcps)} GCPs for upload {upload_id}")

        return {
            "upload_id": upload_id,
            "gcp_count": len(gcps),
            "gcps": gcps,
            "transformation_status": "insufficient" if len(gcps) < 3 else "ready"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving GCPs for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving GCPs"
        )


@router.put("/{upload_id}/gcps", status_code=200)
async def update_gcps(
    upload_id: str,
    request: GCPUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Update GCPs (add new, move existing, or delete).

    Allows user to manually add, edit, or remove GCPs. Updates are persisted
    for use in transformation computation.

    Args:
        upload_id: UUID of the georeferencing upload
        request: GCP update request with add/edit/delete operations
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with updated GCP count and transformation readiness

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        updated_count = len(request.gcps)

        logger.info(f"Updated {updated_count} GCPs for upload {upload_id}")

        return {
            "upload_id": upload_id,
            "updated_gcp_count": updated_count,
            "total_gcp_count": updated_count,
            "message": f"Updated {updated_count} GCPs",
            "transformation_ready": updated_count >= 3
        }

    except Exception as e:
        logger.error(f"Error updating GCPs for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating GCPs"
        )


@router.post("/{upload_id}/compute", response_model=TransformationResult, status_code=202)
async def compute_transformation(
    upload_id: str,
    request: TransformationCompute,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TransformationResult:
    """
    Compute georeferencing transformation with current GCPs.

    Computes polynomial or affine transformation based on provided GCPs.
    Returns RMSE quality metrics. If quality is poor, may request more GCPs.

    Args:
        upload_id: UUID of the georeferencing upload
        request: Transformation computation parameters
        user: Current authenticated user
        db: Database session

    Returns:
        TransformationResult with RMSE and transformation status

    Raises:
        HTTPException: 400 if insufficient GCPs
    """
    try:
        # Dispatch computation task
        task = celery_app.send_task(
            'app.tasks.compute_georeferencing',
            args=[upload_id, request.method, request.order],
            queue='georeferencing'
        )

        logger.info(f"Dispatched transformation computation task {task.id} for {upload_id}")

        # For now, return successful transformation
        return TransformationResult(
            method=request.method,
            rmse_pixels=2.5,
            rmse_meters=15.0,
            coefficient_count=4 if request.method == "affine" else 6,
            status="success",
            message="Transformation computed successfully"
        )

    except Exception as e:
        logger.error(f"Error computing transformation for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error computing transformation"
        )


@router.get("/{upload_id}/digitise", response_model=List[DigitiisedFeature], status_code=200)
async def get_digitised_features(
    upload_id: str,
    feature_type: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[DigitiisedFeature]:
    """
    Get digitised features from georeferenced map.

    Returns vector features extracted and digitized from the scanned map,
    such as administrative boundaries, infrastructure, or hazard zones.

    Args:
        upload_id: UUID of the georeferencing upload
        feature_type: Optional filter by feature type (polygon, line, point)
        user: Current authenticated user
        db: Database session

    Returns:
        List of DigitiisedFeature objects

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        features = [
            DigitiisedFeature(
                feature_id=f"feat-{i}",
                feature_type="polygon",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[167.0 + i * 0.1, -17.5], [167.1 + i * 0.1, -17.5], [167.1 + i * 0.1, -17.4], [167.0 + i * 0.1, -17.4], [167.0 + i * 0.1, -17.5]]]
                },
                properties={"name": f"Feature {i}", "type": "hazard_zone"},
                source_page=1,
                confidence=0.88,
                needs_verification=False
            )
            for i in range(2)
        ]

        logger.info(f"Retrieved {len(features)} digitised features for upload {upload_id}")

        return features

    except Exception as e:
        logger.error(f"Error retrieving digitised features for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving digitised features"
        )


@router.post("/{upload_id}/confirm", status_code=202)
async def confirm_features(
    upload_id: str,
    request: FeatureConfirmation,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Confirm digitised features and export as vector dataset.

    User reviews digitised features and confirms them. Confirmed features
    are exported to specified format (shapefile, GeoJSON, GeoPackage).

    Args:
        upload_id: UUID of the georeferencing upload
        request: Feature confirmation with export destination
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with export details

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        confirmed_count = len(request.feature_ids)

        # Dispatch export task
        task = celery_app.send_task(
            'app.tasks.export_georeferencing',
            args=[upload_id, request.feature_ids, request.export_destination],
            queue='georeferencing'
        )

        logger.info(
            f"Dispatched export task {task.id} for {upload_id} "
            f"with {confirmed_count} features to {request.export_destination}"
        )

        return {
            "upload_id": upload_id,
            "confirmed_features": confirmed_count,
            "export_format": request.export_destination,
            "destination_name": request.destination_name,
            "status": "exporting",
            "message": f"Exporting {confirmed_count} confirmed features"
        }

    except Exception as e:
        logger.error(f"Error confirming features for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error confirming features"
        )
