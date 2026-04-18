"""Dataset management router - handles dataset uploads, QA pipeline, and slot management."""

import logging
import os
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.dataset_upload import DatasetUpload
from app.models.dataset_slot import DatasetSlot
from app.models.user import User as UserModel
from app.schemas import DatasetSlotResponse, DatasetUploadResponse, QAReport
from app.middleware.auth_middleware import (
    get_current_user,
    require_permission,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# MIME types and file extensions for validation
ALLOWED_VECTOR_MIMETYPES = {
    "application/zip",  # Shapefile in zip
    "application/x-zip-compressed",
    "application/geopackage+sqlite3",  # GeoPackage
    "application/octet-stream"  # Generic for GeoPackage
}

ALLOWED_RASTER_MIMETYPES = {
    "image/tiff",
    "image/x-geotiff",
    "application/octet-stream"  # GeoTIFF sometimes comes as octet-stream
}

ALLOWED_EXTENSIONS = {".shp", ".gpkg", ".tif", ".tiff", ".zip", ".gml"}

# Maximum file size in bytes (500MB)
MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024


# ============================================================================
# Helper Functions
# ============================================================================

def validate_file_upload(
    file: UploadFile,
    slot: DatasetSlot
) -> None:
    """
    Validate uploaded file format, size, and MIME type.

    Args:
        file: Uploaded file object
        slot: Target dataset slot

    Raises:
        HTTPException: If file validation fails
    """
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
        )

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{file_ext}' not allowed. Supported: {ALLOWED_EXTENSIONS}"
        )

    # Check MIME type based on slot type
    if slot.geometry_type == "raster":
        allowed_types = ALLOWED_RASTER_MIMETYPES
    else:
        allowed_types = ALLOWED_VECTOR_MIMETYPES

    if file.content_type and file.content_type not in allowed_types:
        logger.warning(
            f"Invalid MIME type for slot {slot.id}: {file.content_type}"
        )
        # Log but don't fail on MIME type - some servers misreport this
        # Rely on GDAL validation in QA pipeline


def test_gdal_readability(file_path: str) -> None:
    """
    Test if GDAL can read the uploaded file.

    Args:
        file_path: Path to file to test

    Raises:
        HTTPException: If GDAL cannot read the file
    """
    try:
        from osgeo import gdal
        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')

        dataset = gdal.Open(file_path)
        if dataset is None:
            error_msg = gdal.GetLastErrorMsg()
            logger.error(f"GDAL cannot read file {file_path}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid geospatial file format: {error_msg}"
            )

        dataset = None

    except ImportError:
        logger.warning("GDAL not available - skipping readability test")
    except Exception as e:
        logger.error(f"Error testing GDAL readability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating file format"
        )


# ============================================================================
# Routes
# ============================================================================

@router.get("/slots", response_model=List[DatasetSlotResponse], status_code=200)
async def list_dataset_slots(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[DatasetSlotResponse]:
    """
    List all available dataset slots with current upload status.

    Returns information about all dataset slots including required/optional
    status, expected formats, and current upload status.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        List of DatasetSlotResponse objects

    Raises:
        HTTPException: 500 on database error
    """
    try:
        slots = db.query(DatasetSlot).filter(
            DatasetSlot.is_active == True
        ).all()

        slot_responses = []
        for slot in slots:
            # Get latest upload for this slot
            latest_upload = db.query(DatasetUpload).filter(
                DatasetUpload.slot_id == slot.id,
                DatasetUpload.is_active == True
            ).order_by(desc(DatasetUpload.upload_timestamp)).first()

            status_str = "empty"
            updated_at = None

            if latest_upload:
                updated_at = latest_upload.upload_timestamp
                if latest_upload.qa_status == "pass":
                    status_str = "ready"
                elif latest_upload.qa_status in ["pending", "processing"]:
                    status_str = "processing"
                elif latest_upload.qa_status in ["conditional", "auto_fixed"]:
                    status_str = "uploaded"
                else:
                    status_str = "error"

            slot_responses.append(DatasetSlotResponse(
                slot_id=str(slot.id),
                dataset_type=slot.dataset_type,
                name=slot.name,
                description=slot.description,
                required=slot.is_required,
                status=status_str,
                file_format=slot.file_format,
                geometry_type=slot.geometry_type,
                updated_at=updated_at
            ))

        logger.info(f"Listed {len(slot_responses)} dataset slots for user {user.email}")
        return slot_responses

    except Exception as e:
        logger.error(f"Error listing dataset slots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dataset slots"
        )


@router.get("/slots/{code}", response_model=DatasetSlotResponse, status_code=200)
async def get_dataset_slot(
    code: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DatasetSlotResponse:
    """
    Get details for a specific dataset slot.

    Args:
        code: Dataset slot code/identifier
        user: Current authenticated user
        db: Database session

    Returns:
        DatasetSlotResponse with slot details

    Raises:
        HTTPException: 404 if slot not found
    """
    try:
        slot = db.query(DatasetSlot).filter(
            DatasetSlot.code == code,
            DatasetSlot.is_active == True
        ).first()

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset slot '{code}' not found"
            )

        # Get latest upload
        latest_upload = db.query(DatasetUpload).filter(
            DatasetUpload.slot_id == slot.id,
            DatasetUpload.is_active == True
        ).order_by(desc(DatasetUpload.upload_timestamp)).first()

        status_str = "empty"
        updated_at = None

        if latest_upload:
            updated_at = latest_upload.upload_timestamp
            if latest_upload.qa_status == "pass":
                status_str = "ready"
            elif latest_upload.qa_status in ["pending", "processing"]:
                status_str = "processing"
            elif latest_upload.qa_status in ["conditional", "auto_fixed"]:
                status_str = "uploaded"
            else:
                status_str = "error"

        logger.info(f"Retrieved slot details for {code}")

        return DatasetSlotResponse(
            slot_id=str(slot.id),
            dataset_type=slot.dataset_type,
            name=slot.name,
            description=slot.description,
            required=slot.is_required,
            status=status_str,
            file_format=slot.file_format,
            geometry_type=slot.geometry_type,
            updated_at=updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving slot {code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dataset slot"
        )


@router.post("/upload/{code}", response_model=DatasetUploadResponse, status_code=202)
async def upload_dataset_file(
    code: str,
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DatasetUploadResponse:
    """
    Upload file to a dataset slot with automatic QA pipeline dispatch.

    Validates file format and size, stores to disk, creates dataset_upload record,
    and dispatches Celery task for QA pipeline processing. Returns immediately
    with job_id for polling status.

    Args:
        code: Dataset slot code
        file: Uploaded file (multipart/form-data)
        user: Current authenticated user
        db: Database session

    Returns:
        DatasetUploadResponse with upload_id for polling

    Raises:
        HTTPException: 400 if slot not found, 413 if file too large, 422 if invalid format
    """
    try:
        # Get dataset slot
        slot = db.query(DatasetSlot).filter(
            DatasetSlot.code == code,
            DatasetSlot.is_active == True
        ).first()

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset slot '{code}' not found"
            )

        # Validate file
        validate_file_upload(file, slot)

        # Create upload directory if needed
        upload_path = Path(settings.upload_dir)
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

        logger.info(f"File uploaded to {full_path}, size: {len(contents)} bytes")

        # Test GDAL readability
        test_gdal_readability(full_path)

        # Get current user from database
        db_user = db.query(UserModel).filter(UserModel.id == UUID(user.user_id)).first()

        # Create dataset_upload record
        dataset_upload = DatasetUpload(
            slot_id=slot.id,
            uploaded_by=UUID(user.user_id),
            organisation=user.organization,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=full_path,
            file_format=Path(file.filename).suffix.lower().lstrip("."),
            file_size_bytes=len(contents),
            upload_timestamp=datetime.utcnow(),
            qa_status="pending",
            is_active=True
        )

        db.add(dataset_upload)
        db.commit()
        db.refresh(dataset_upload)

        logger.info(f"Created upload record {dataset_upload.id} for slot {code}")

        # Dispatch Celery task for QA pipeline
        task = celery_app.send_task(
            'app.tasks.qa_pipeline',
            args=[str(dataset_upload.id), full_path, slot.dataset_type],
            queue='qa'
        )

        logger.info(f"Dispatched QA pipeline task {task.id} for upload {dataset_upload.id}")

        return DatasetUploadResponse(
            upload_id=str(dataset_upload.id),
            dataset_type=slot.dataset_type,
            file_name=file.filename,
            file_size_mb=len(contents) / (1024 * 1024),
            status="uploading",
            crs=None,
            geometry_count=None,
            bounds=None,
            qa_stage="pending",
            created_at=dataset_upload.upload_timestamp,
            errors=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to slot {code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing upload"
        )


@router.get("/upload/{upload_id}/qa-status", status_code=200)
async def get_qa_pipeline_status(
    upload_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Poll QA pipeline status for an upload.

    Returns current QA status including stage, issues found, and any error messages.
    Used by frontend for progress polling while QA is running.

    Args:
        upload_id: UUID of the dataset upload
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with status, progress_percent, and qa_report

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        upload = db.query(DatasetUpload).filter(
            DatasetUpload.id == UUID(upload_id)
        ).first()

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload '{upload_id}' not found"
            )

        # Map qa_status to progress
        progress_map = {
            "pending": 10,
            "processing": 50,
            "pass": 100,
            "conditional": 80,
            "auto_fixed": 100,
            "failed": 0
        }

        progress = progress_map.get(upload.qa_status or "pending", 0)

        logger.info(f"Retrieved QA status for upload {upload_id}: {upload.qa_status}")

        return {
            "upload_id": str(upload.id),
            "status": upload.qa_status or "pending",
            "progress_percent": progress,
            "qa_report": upload.qa_report or {},
            "fix_log": upload.fix_log or [],
            "errors": []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving QA status for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving QA status"
        )


@router.post("/upload/{upload_id}/apply-field-mapping", status_code=200)
async def apply_field_mapping(
    upload_id: str,
    field_mapping: dict,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Resolve partial-fix field mapping for dataset upload.

    Used when QA pipeline finds field mapping issues that need user confirmation.
    Applies the provided field mapping and re-runs relevant QA stages.

    Args:
        upload_id: UUID of the dataset upload
        field_mapping: Dictionary mapping detected fields to standard fields
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with updated qa_status

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        upload = db.query(DatasetUpload).filter(
            DatasetUpload.id == UUID(upload_id)
        ).first()

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload '{upload_id}' not found"
            )

        # Store field mapping in qa_report
        if not upload.qa_report:
            upload.qa_report = {}

        upload.qa_report["field_mapping_applied"] = field_mapping
        upload.qa_report["field_mapping_applied_at"] = datetime.utcnow().isoformat()

        # Dispatch re-validation task
        task = celery_app.send_task(
            'app.tasks.qa_field_mapping_validation',
            args=[str(upload.id), field_mapping],
            queue='qa'
        )

        db.commit()

        logger.info(f"Applied field mapping for upload {upload_id}, task {task.id}")

        return {
            "upload_id": str(upload.id),
            "status": "revalidating",
            "message": "Field mapping applied, re-validating dataset"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying field mapping for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error applying field mapping"
        )


@router.post("/upload/{upload_id}/apply-crs-selection", status_code=200)
async def apply_crs_selection(
    upload_id: str,
    crs_selection: dict,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Resolve partial-fix CRS selection for dataset upload.

    Used when QA pipeline cannot determine CRS and needs user to select from
    candidates. Applies the selected CRS and re-runs geometry validation.

    Args:
        upload_id: UUID of the dataset upload
        crs_selection: Dictionary with selected CRS (e.g., {"crs": "EPSG:4326"})
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with updated qa_status

    Raises:
        HTTPException: 404 if upload not found
    """
    try:
        upload = db.query(DatasetUpload).filter(
            DatasetUpload.id == UUID(upload_id)
        ).first()

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload '{upload_id}' not found"
            )

        # Store CRS selection
        selected_crs = crs_selection.get("crs")
        upload.crs_assigned = selected_crs
        upload.crs_detected = selected_crs

        if not upload.qa_report:
            upload.qa_report = {}

        upload.qa_report["crs_selected"] = selected_crs
        upload.qa_report["crs_selected_at"] = datetime.utcnow().isoformat()

        # Dispatch re-validation task
        task = celery_app.send_task(
            'app.tasks.qa_crs_validation',
            args=[str(upload.id), selected_crs],
            queue='qa'
        )

        db.commit()

        logger.info(f"Applied CRS selection for upload {upload_id}: {selected_crs}")

        return {
            "upload_id": str(upload.id),
            "status": "revalidating",
            "message": f"CRS {selected_crs} assigned, re-validating geometry"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying CRS selection for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error applying CRS selection"
        )


@router.delete("/upload/{upload_id}", status_code=204)
async def delete_dataset_upload(
    upload_id: str,
    user: AuthUser = Depends(require_permission("upload_delete")),
    db: Session = Depends(get_db)
) -> None:
    """
    Remove/delete a dataset upload (Data Manager+ only).

    Marks upload as inactive (soft delete) and removes file from disk.
    This is a permission-restricted endpoint - only data managers and admins.

    Args:
        upload_id: UUID of the dataset upload
        user: Current authenticated user (must have upload_delete permission)
        db: Database session

    Returns:
        204 No Content

    Raises:
        HTTPException: 404 if upload not found, 403 if insufficient permissions
    """
    try:
        upload = db.query(DatasetUpload).filter(
            DatasetUpload.id == UUID(upload_id)
        ).first()

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload '{upload_id}' not found"
            )

        # Mark as inactive (soft delete)
        upload.is_active = False

        # Remove file from disk
        try:
            if os.path.exists(upload.file_path):
                os.remove(upload.file_path)
                logger.info(f"Deleted file from disk: {upload.file_path}")
        except Exception as e:
            logger.error(f"Error deleting file {upload.file_path}: {e}")

        db.commit()

        logger.info(f"Deleted upload {upload_id} by user {user.email}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting upload"
        )
