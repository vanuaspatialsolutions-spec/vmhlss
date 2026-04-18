"""Report model."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Report(Base):
    """Reports table model."""

    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    report_name = Column(String, nullable=False)
    report_type = Column(String, nullable=False, index=True)  # 'suitability_assessment' | 'qa_summary' | 'executive_summary' | 'detailed_analysis' | 'custom'
    analysis_id = Column(PG_UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=True, index=True)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text, nullable=True)

    # Report content and metadata
    executive_summary = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)  # Array of report sections with content
    findings = Column(JSON, nullable=True)  # Key findings and insights
    recommendations = Column(JSON, nullable=True)  # List of recommendations
    limitations = Column(JSON, nullable=True)  # Limitations of the analysis/report

    # Report data
    statistics = Column(JSON, nullable=True)  # Summary statistics
    visualizations = Column(JSON, nullable=True)  # References to charts/maps
    maps = Column(JSON, nullable=True)  # Embedded maps or map references
    tables = Column(JSON, nullable=True)  # Embedded tables or table references

    # Technical
    data_sources = Column(JSON, nullable=True)  # List of datasets used
    methodology = Column(Text, nullable=True)  # Description of methodology
    crs = Column(String, nullable=True, default="EPSG:4326")
    study_area_geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)

    # Distribution and access
    status = Column(String, nullable=False, default="draft")  # 'draft' | 'review' | 'approved' | 'published' | 'archived'
    is_public = Column(Boolean, nullable=False, default=False, server_default="false")
    distribution_list = Column(JSON, nullable=True)  # List of user IDs or emails for distribution
    access_level = Column(String, nullable=True)  # 'private' | 'internal' | 'public'

    # Files
    report_file_path = Column(String, nullable=True)  # Path to PDF/DOCX export
    attachments = Column(JSON, nullable=True)  # Array of attachment file paths

    # Metadata
    tags = Column(JSON, nullable=True)  # Array of tags
    metadata = Column(JSON, nullable=True)  # Additional metadata

    def __repr__(self):
        return f"<Report(id={self.id}, report_name={self.report_name}, report_type={self.report_type})>"
