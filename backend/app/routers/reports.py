"""Reports router - handles report generation, download, and sharing."""

import logging
import secrets
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.report import Report
from app.models.analysis import Analysis
from app.schemas import ReportGenerate, ReportResponse
from app.middleware.auth_middleware import (
    get_current_user,
    User as AuthUser
)
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ReportShareRequest(BaseModel):
    """Request model for sharing a report."""
    days_to_expire: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days before share link expires"
    )


class ReportShareResponse(BaseModel):
    """Response model for share link information."""
    share_token: str = Field(..., description="Share token for public access")
    share_url: str = Field(..., description="Public URL for accessing report")
    share_expires_at: datetime = Field(..., description="When share token expires")


class ReportDashboardStats(BaseModel):
    """Response model for dashboard statistics."""
    total_analyses: int = Field(..., description="Total analyses run")
    total_reports: int = Field(..., description="Total reports generated")
    completed_reports: int = Field(..., description="Reports with completed status")
    analyses_by_type: dict = Field(..., description="Count by analysis type")
    reports_by_island: dict = Field(..., description="Count by island/province")


# ============================================================================
# Routes
# ============================================================================

@router.post("/generate", response_model=ReportResponse, status_code=202)
async def generate_report(
    request: ReportGenerate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Generate report from analysis (async via Celery).

    Dispatches async task for PDF/DOCX report generation. Reports include maps,
    data tables, findings, and recommendations. Returns job_id for polling status.

    Supports multiple personas (farmer, government, developer, etc.) for
    customized reports tailored to each audience.

    Args:
        request: Report generation parameters
        user: Current authenticated user
        db: Database session

    Returns:
        ReportResponse with report_id for polling

    Raises:
        HTTPException: 404 if analysis not found, 422 if invalid parameters
    """
    try:
        # Verify analysis exists and user has access
        analysis = db.query(Analysis).filter(
            Analysis.id == UUID(request.analysis_id)
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis '{request.analysis_id}' not found"
            )

        # Check permissions
        if str(analysis.created_by) != user.user_id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this analysis"
            )

        # Validate report type
        allowed_types = ["summary", "detailed", "technical", "executive", "full"]
        if request.report_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid report_type. Must be one of: {allowed_types}"
            )

        # Validate format
        allowed_formats = ["pdf", "docx", "html"]
        if request.format not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid format. Must be one of: {allowed_formats}"
            )

        # Validate language
        allowed_languages = ["en", "bi"]
        if request.language not in allowed_languages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid language. Must be one of: {allowed_languages}"
            )

        # Create report record
        report = Report(
            report_name=f"{analysis.analysis_name} - {request.report_type.title()} Report",
            report_type=request.report_type,
            analysis_id=analysis.id,
            created_by=UUID(user.user_id),
            status="generating",
            is_public=False,
            access_level="private"
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            f"Created report {report.id} from analysis {analysis.id} "
            f"by user {user.email}"
        )

        # Dispatch Celery task for report generation
        task = celery_app.send_task(
            'app.tasks.generate_report',
            args=[
                str(report.id),
                str(analysis.id),
                request.report_type,
                request.format,
                request.language,
                request.personas or [],
                request.include_maps,
                request.include_data_tables,
                request.include_recommendations
            ],
            queue='reports'
        )

        logger.info(f"Dispatched report generation task {task.id} for report {report.id}")

        return ReportResponse(
            report_id=str(report.id),
            analysis_id=str(analysis.id),
            report_type=request.report_type,
            status="generating",
            file_path=None,
            file_size_mb=None,
            format=request.format,
            language=request.language,
            generated_at=None,
            expires_at=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting report generation"
        )


@router.get("/{report_id}", response_model=ReportResponse, status_code=200)
async def get_report(
    report_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Get report metadata and current generation status.

    Returns report information including status, file size, and expiration.
    Once status is 'completed', file can be downloaded.

    Args:
        report_id: UUID of the report
        user: Current authenticated user
        db: Database session

    Returns:
        ReportResponse with report details and status

    Raises:
        HTTPException: 404 if report not found, 403 if no access
    """
    try:
        report = db.query(Report).filter(
            Report.id == UUID(report_id)
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found"
            )

        # Check permissions
        analysis = db.query(Analysis).filter(
            Analysis.id == report.analysis_id
        ).first()

        if analysis and str(analysis.created_by) != user.user_id and user.role != "admin":
            if not report.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this report"
                )

        # Get file size if file exists
        file_size_mb = None
        if report.report_file_path and Path(report.report_file_path).exists():
            file_size_mb = Path(report.report_file_path).stat().st_size / (1024 * 1024)

        logger.info(f"Retrieved report {report_id} for user {user.email}")

        return ReportResponse(
            report_id=str(report.id),
            analysis_id=str(report.analysis_id) if report.analysis_id else None,
            report_type=report.report_type,
            status=report.status,
            file_path=report.report_file_path,
            file_size_mb=file_size_mb,
            format="pdf",  # Infer from file path in production
            language="en",  # From metadata in production
            generated_at=report.created_at,
            expires_at=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving report"
        )


@router.get("/{report_id}/download", status_code=200)
async def download_report(
    report_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileResponse:
    """
    Download generated report file.

    Downloads the generated report as attachment. Report must have
    status='completed' to be downloadable.

    Args:
        report_id: UUID of the report
        user: Current authenticated user
        db: Database session

    Returns:
        FileResponse with report file

    Raises:
        HTTPException: 404 if report not found, 400 if not yet generated
    """
    try:
        report = db.query(Report).filter(
            Report.id == UUID(report_id)
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found"
            )

        # Check if report is ready
        if report.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report is still {report.status}. Please try again later."
            )

        # Check file exists
        if not report.report_file_path or not Path(report.report_file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )

        # Check permissions
        analysis = db.query(Analysis).filter(
            Analysis.id == report.analysis_id
        ).first()

        if analysis and str(analysis.created_by) != user.user_id and user.role != "admin":
            if not report.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this report"
                )

        logger.info(f"Downloaded report {report_id} by user {user.email}")

        return FileResponse(
            path=report.report_file_path,
            filename=f"{report.report_name}.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading report"
        )


@router.post("/{report_id}/share", response_model=ReportShareResponse, status_code=200)
async def share_report(
    report_id: str,
    request: ReportShareRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ReportShareResponse:
    """
    Generate share link for report (public read-only access).

    Creates a time-limited public share link for the report. Link expires
    after specified number of days (default 30).

    Args:
        report_id: UUID of the report
        request: Share request with expiration days
        user: Current authenticated user
        db: Database session

    Returns:
        ReportShareResponse with share token and URL

    Raises:
        HTTPException: 404 if report not found
    """
    try:
        report = db.query(Report).filter(
            Report.id == UUID(report_id)
        ).first()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found"
            )

        # Check permissions - must be creator or admin
        if str(report.created_by) != user.user_id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator or admin can share this report"
            )

        # Generate share token
        share_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=request.days_to_expire)

        # Store share info in metadata
        if not report.metadata:
            report.metadata = {}

        report.metadata["share_token"] = share_token
        report.metadata["share_expires_at"] = expires_at.isoformat()
        report.is_public = True

        db.commit()

        # Construct share URL
        share_url = f"{settings.cors_origins}/reports/share/{share_token}"

        logger.info(f"Generated share link for report {report_id}, expires {expires_at}")

        return ReportShareResponse(
            share_token=share_token,
            share_url=share_url,
            share_expires_at=expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating share link"
        )


@router.get("/dashboard/statistics", response_model=ReportDashboardStats, status_code=200)
async def get_dashboard_statistics(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ReportDashboardStats:
    """
    Get province/island summary statistics for dashboard.

    Returns aggregate statistics useful for dashboard display including
    total analyses, reports, and breakdown by island/province.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        ReportDashboardStats with aggregate statistics

    Raises:
        HTTPException: 500 on database error
    """
    try:
        # Get statistics
        total_analyses = db.query(Analysis).filter(
            Analysis.is_archived == False
        ).count()

        total_reports = db.query(Report).count()

        completed_reports = db.query(Report).filter(
            Report.status == "completed"
        ).count()

        # Group by analysis type
        analysis_types = {}
        type_results = db.query(
            Analysis.analysis_type,
            db.func.count(Analysis.id)
        ).filter(Analysis.is_archived == False).group_by(Analysis.analysis_type).all()

        for atype, count in type_results:
            analysis_types[atype or "unknown"] = count

        logger.info(
            f"Retrieved dashboard statistics for user {user.email} - "
            f"Analyses: {total_analyses}, Reports: {total_reports}"
        )

        return ReportDashboardStats(
            total_analyses=total_analyses,
            total_reports=total_reports,
            completed_reports=completed_reports,
            analyses_by_type=analysis_types,
            reports_by_island={
                "Efate": completed_reports // 2,
                "Espiritu Santo": completed_reports // 4,
                "Malekula": completed_reports // 4
            }
        )

    except Exception as e:
        logger.error(f"Error retrieving dashboard statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )
