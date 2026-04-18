"""Knowledge Base Record model."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KnowledgeBaseRecord(Base):
    """Knowledge Base Records table model."""

    __tablename__ = "knowledge_base_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    category = Column(String, nullable=False, index=True)  # e.g., 'hazard', 'methodology', 'policy', 'best_practice'
    subcategory = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    author = Column(String, nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, nullable=False, default=False, server_default="false")
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of strings stored as JSON for flexibility
    relevance_score = Column(String, nullable=True)  # Could be float or descriptive
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    def __repr__(self):
        return f"<KnowledgeBaseRecord(id={self.id}, category={self.category}, title={self.title})>"
