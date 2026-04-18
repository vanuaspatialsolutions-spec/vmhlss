"""Dataset Upload model."""

from datetime import datetime
from uuid import UUID
from decimal import Decimal
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, JSON, Date, Numeric, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DatasetUpload(Base):
    """Dataset Uploads table model."""

    __tablename__ = "dataset_uploads"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slot_id = Column(PG_UUID(as_uuid=True), ForeignKey("dataset_slots.id"), nullable=False, index=True)
    uploaded_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organisation = Column(String, nullable=True)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_format = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    upload_timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    qa_status = Column(String, nullable=True)  # 'pending' | 'pass' | 'conditional' | 'auto_fixed' | 'failed'
    qa_report = Column(JSON, nullable=True)
    fix_log = Column(ARRAY(JSON), nullable=True)
    geometry_type = Column(String, nullable=True)
    crs_detected = Column(String, nullable=True)
    crs_assigned = Column(String, nullable=True)
    coverage_pct = Column(Numeric(5, 2), nullable=True)
    data_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    geom_extent = Column(Geometry("POLYGON", srid=4326), nullable=True)

    def __repr__(self):
        return f"<DatasetUpload(id={self.id}, original_filename={self.original_filename}, qa_status={self.qa_status})>"
