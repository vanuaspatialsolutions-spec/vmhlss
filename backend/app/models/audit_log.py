"""Audit Log model."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, BigInteger, DateTime, String, JSON, ForeignKey, func, INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AuditLog(Base):
    """Audit Log table model (append-only, immutable)."""

    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String, nullable=True)
    user_role = Column(String, nullable=True)
    action_type = Column(String, nullable=False, index=True)  # 'create' | 'read' | 'update' | 'delete' | 'login' | 'logout' | 'export' | etc.
    resource_type = Column(String, nullable=True, index=True)  # 'user' | 'dataset_upload' | 'analysis' | 'report' | etc.
    resource_id = Column(String, nullable=True, index=True)
    detail = Column(JSON, nullable=True)  # Additional details about the action
    ip_address = Column(INET, nullable=True)
    session_id = Column(String, nullable=True, index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, timestamp={self.timestamp}, action_type={self.action_type}, user_id={self.user_id})>"
