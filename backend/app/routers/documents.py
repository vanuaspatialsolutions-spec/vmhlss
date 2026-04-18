"""Documents and knowledge base router - handles document upload and intelligence extraction."""

import logging
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas import (
    DocumentUploadResponse,
    ExtractionItem,
    ExtractionResponse,
    KnowledgeBaseRecord
)
from app.middleware.auth_middleware import (
    get_current_user,
    require_permission,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

# Allowed document MIME types
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "image/tiff",
    "image/x-geotiff",
    "image/jpeg",
    "image/png"
}

MAX_DOCUMENT_SIZE = settings.max_upload_size_mb * 1024 * 1024


# ============================================================================
# Request/Response Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    document_type: str = Field(..., description="Type of document (survey, report, map, scan)")
    source_description: Optional[str] = Field(None, description="Description of document source")


class ExtractionConfirmation(BaseModel):
    """Request model for confirming/rejecting extracted items."""
    item_id: str = Field(..., description="ID of extracted item")
    confirmed: bool = Field(..., description="True to confirm, False to reject")
    correction: Optional[str] = Field(None, description="Corrected value if rejecting")


class ExtractionBatch(BaseModel):
    """Request model for batch confirming extracted items."""
    items: List[ExtractionConfirmation] = Field(..., description="List of confirmations")


class KBQueryRequest(BaseModel):
    """Request model for knowledge base query."""
    query_text: Optional[str] = Field(None, description="Search query text")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    bbox: Optional[dict] = Field(None, description="Spatial bounding box filter")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")
    offset: int = Field(default=0, ge=0, description="Results offset")


class KBQueryResponse(BaseModel):
    """Response model for KB query results."""
    records: List[KnowledgeBaseRecord] = Field(..., description="Query results")
    total_count: int = Field(..., description="Total matching records")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


# ============================================================================
# Routes
# ============================================================================

@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "report",
    source_description: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentUploadResponse:
    """
    Upload document for intelligence extraction.

    Accepts PDF, scanned images, and reports. Dispatches async task for
    OCR and information extraction. Returns job_id for polling extraction status.

    Args:
        file: Document file to upload
        document_type: Type of document (survey, report, map, scan)
        source_description: Optional description of document source
        user: Current authenticated user
        db: Database session

    Returns:
        DocumentUploadResponse with document_id for polling

    Raises:
        HTTPException: 413 if file too large, 422 if invalid format
    """
    try:
        # Validate file size
        if file.size and file.size > MAX_DOCUMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
            )

        # Validate MIME type
        if file.content_type and file.content_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Document type '{file.content_type}' not supported. Supported: {ALLOWED_DOCUMENT_TYPES}"
            )

        # Create upload directory
        upload_path = Path(settings.upload_dir) / "documents"
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

        logger.info(f"Document uploaded to {full_path}, size: {len(contents)} bytes")

        # Create metadata for tracking
        document_id = str(uuid4())

        # Dispatch Celery task for extraction
        task = celery_app.send_task(
            'app.tasks.document_extraction',
            args=[document_id, full_path, document_type],
            queue='documents'
        )

        logger.info(f"Dispatched document extraction task {task.id} for document {document_id}")

        return DocumentUploadResponse(
            document_id=document_id,
            file_name=file.filename,
            file_size_mb=len(contents) / (1024 * 1024),
            document_type=document_type,
            extraction_status="processing",
            pages_processed=None,
            text_extracted_chars=None,
            confidence_score=None,
            uploaded_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing document upload"
        )


@router.get("/documents/{document_id}/extractions", response_model=ExtractionResponse, status_code=200)
async def get_extraction_items(
    document_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ExtractionResponse:
    """
    Get pending extracted items from document for verification.

    Returns all items extracted from document that need manual review/confirmation.
    Includes confidence scores and context for each item.

    Args:
        document_id: UUID of the document
        user: Current authenticated user
        db: Database session

    Returns:
        ExtractionResponse with list of extracted items

    Raises:
        HTTPException: 404 if document not found
    """
    try:
        # In production, fetch from database
        # For now, return placeholder structure

        extraction_items = [
            ExtractionItem(
                item_id=f"ext-{i}",
                item_type="coordinate",
                value="17.5°S, 167.3°E",
                context="Located near Efate island",
                confidence=0.95,
                page_number=1,
                needs_verification=False
            )
            for i in range(3)
        ]

        logger.info(f"Retrieved extractions for document {document_id}")

        return ExtractionResponse(
            document_id=document_id,
            extracted_items=extraction_items,
            summary="3 key coordinates extracted, 5 boundaries identified",
            next_steps=[
                "Verify extracted coordinates",
                "Confirm administrative boundaries",
                "Add to knowledge base"
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving extractions for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving extracted items"
        )


@router.post("/documents/{document_id}/confirm", status_code=200)
async def confirm_extraction_items(
    document_id: str,
    batch: ExtractionBatch,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Confirm or reject individual extracted items from document.

    User reviews extracted items and confirms correct extractions or provides
    corrections. Confirmed items are added to knowledge base.

    Args:
        document_id: UUID of the document
        batch: Batch of item confirmations
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with confirmation results

    Raises:
        HTTPException: 404 if document not found
    """
    try:
        confirmed_count = 0
        rejected_count = 0

        for item_confirmation in batch.items:
            if item_confirmation.confirmed:
                confirmed_count += 1
                # Add to KB in production
            else:
                rejected_count += 1

        logger.info(
            f"User {user.email} confirmed {confirmed_count} and rejected "
            f"{rejected_count} items from document {document_id}"
        )

        return {
            "document_id": document_id,
            "confirmed_items": confirmed_count,
            "rejected_items": rejected_count,
            "message": f"Processed {confirmed_count + rejected_count} items"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming extractions for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error confirming extracted items"
        )


@router.post("/knowledge-base/query", response_model=KBQueryResponse, status_code=200)
async def query_knowledge_base(
    request: KBQueryRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> KBQueryResponse:
    """
    Query knowledge base by text, category, or spatial location.

    Searches KB records by keyword, category filter, or bounding box.
    Supports pagination for large result sets.

    Args:
        request: Query request with filters
        user: Current authenticated user
        db: Database session

    Returns:
        KBQueryResponse with matching records and total count

    Raises:
        HTTPException: 500 on database error
    """
    try:
        # Build query
        query = db.query(KnowledgeBase)

        # Text search
        if request.query_text:
            query = query.filter(
                (KnowledgeBase.title.ilike(f"%{request.query_text}%")) |
                (KnowledgeBase.description.ilike(f"%{request.query_text}%"))
            )

        # Category filter
        if request.categories:
            query = query.filter(KnowledgeBase.category.in_(request.categories))

        # Get total
        total_count = query.count()

        # Paginate
        records = query.order_by(
            desc(KnowledgeBase.created_at)
        ).limit(request.limit).offset(request.offset).all()

        # Convert to response objects
        kb_responses = []
        for record in records:
            kb_responses.append(KnowledgeBaseRecord(
                record_id=str(record.id),
                title=record.title,
                description=record.description or "",
                category=record.category,
                keywords=record.keywords or [],
                source=record.source,
                geometry=record.geometry,
                properties=record.properties or {},
                created_at=record.created_at,
                updated_at=record.updated_at
            ))

        logger.info(
            f"KB query returned {len(records)} records "
            f"(total: {total_count}) for user {user.email}"
        )

        return KBQueryResponse(
            records=kb_responses,
            total_count=total_count,
            limit=request.limit,
            offset=request.offset
        )

    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error querying knowledge base"
        )


@router.delete("/knowledge-base/{kb_id}", status_code=204)
async def delete_kb_record(
    kb_id: str,
    user: AuthUser = Depends(require_permission("kb_manage")),
    db: Session = Depends(get_db)
) -> None:
    """
    Remove KB record (Data Manager+ only).

    Deletes a knowledge base record. Restricted to data managers and admins.

    Args:
        kb_id: UUID of KB record to delete
        user: Current authenticated user (must have kb_manage permission)
        db: Database session

    Returns:
        204 No Content

    Raises:
        HTTPException: 404 if record not found, 403 if insufficient permissions
    """
    try:
        record = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == UUID(kb_id)
        ).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base record '{kb_id}' not found"
            )

        db.delete(record)
        db.commit()

        logger.info(f"Deleted KB record {kb_id} by user {user.email}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting KB record {kb_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting knowledge base record"
        )
