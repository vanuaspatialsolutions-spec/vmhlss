"""User model."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """User table model."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    organisation = Column(String, nullable=True)
    role = Column(String, nullable=False)  # 'admin' | 'data_manager' | 'analyst' | 'reviewer' | 'public'
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    two_factor_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
