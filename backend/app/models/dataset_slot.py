"""Dataset Slot model."""

from uuid import UUID
from sqlalchemy import Column, String, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import declarative_base
from sqlalchemy import func

Base = declarative_base()


class DatasetSlot(Base):
    """Dataset Slots table model."""

    __tablename__ = "dataset_slots"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slot_code = Column(String, nullable=False, unique=True, index=True)  # 'DS-01' through 'DS-14'
    slot_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_for = Column(Text, nullable=True)
    phase = Column(String, nullable=False)  # 'phase1' | 'phase2'
    is_compulsory = Column(Boolean, nullable=False)
    minimum_standard = Column(Text, nullable=True)
    fallback_source = Column(String, nullable=True)
    accepted_formats = Column(ARRAY(String), nullable=True)
    required_attributes = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<DatasetSlot(id={self.id}, slot_code={self.slot_code}, slot_name={self.slot_name})>"
