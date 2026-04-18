"""Analysis model."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey, func, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Analysis(Base):
    """Analyses table model."""

    __tablename__ = "analyses"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    analysis_name = Column(String, nullable=False)
    analysis_type = Column(String, nullable=False)  # 'development' | 'agriculture' | 'infrastructure' | 'custom'
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")  # 'draft' | 'in_progress' | 'completed' | 'archived'

    # Input parameters
    study_area_geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    ahp_weight_set = Column(String, nullable=True)  # Reference to weight set name
    custom_weights = Column(JSON, nullable=True)  # Custom weights if not using predefined set
    input_datasets = Column(JSON, nullable=True)  # List of dataset_upload IDs used

    # Processing
    processing_params = Column(JSON, nullable=True)  # Additional processing parameters
    processing_status = Column(String, nullable=True)  # 'pending' | 'processing' | 'completed' | 'failed'
    processing_log = Column(Text, nullable=True)
    processing_error = Column(Text, nullable=True)

    # Results
    suitability_raster = Column(String, nullable=True)  # File path to output raster
    suitability_classes = Column(JSON, nullable=True)  # Classification breakdown
    output_geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)  # Output geometry with classification
    statistics = Column(JSON, nullable=True)  # Summary statistics

    # Constraints applied
    constraints_applied = Column(JSON, nullable=True)  # List of constraints used
    exclusion_masks = Column(JSON, nullable=True)  # Exclusion geometries

    # Metadata
    crs = Column(String, nullable=True, default="EPSG:4326")
    resolution_m = Column(Numeric(10, 2), nullable=True)  # Grid resolution in meters
    metadata = Column(JSON, nullable=True)
    is_public = Column(Boolean, nullable=False, default=False, server_default="false")
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self):
        return f"<Analysis(id={self.id}, analysis_name={self.analysis_name}, analysis_type={self.analysis_type})>"
