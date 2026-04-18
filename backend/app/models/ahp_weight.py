from sqlalchemy import Column, String, DECIMAL, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AHPWeight(Base):
    """
    Analytic Hierarchy Process (AHP) Weighting Matrix Model.

    Stores user-configurable weights for multi-criteria evaluation.
    Each weight represents the relative importance of a criteria within
    a specific assessment type (development, agriculture, conservation, infrastructure).

    Attributes:
        id: Unique identifier (UUID)
        weight_set_name: Name of weight configuration (e.g., 'default', 'conservative', 'development-focused')
        assessment_type: Type of assessment ('development' | 'agriculture' | 'conservation' | 'infrastructure')
        criteria_key: Identifier for the criteria being weighted (e.g., 'seismic', 'cyclone', 'soil_quality')
        weight: Normalized weight value (0.0000 to 1.0000), must sum to 1.0 across criteria within assessment type
        updated_by: UUID of user who last modified this weight (foreign key to users table)
        updated_at: Timestamp of last modification (auto-set to current time in UTC)
    """

    __tablename__ = "ahp_weights"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for this weight entry"
    )

    weight_set_name = Column(
        String(100),
        default='default',
        nullable=False,
        doc="Name of this weight configuration set (e.g., 'default', 'conservative')"
    )

    assessment_type = Column(
        String(50),
        nullable=False,
        doc="Assessment type: 'development', 'agriculture', 'conservation', or 'infrastructure'"
    )

    criteria_key = Column(
        String(100),
        nullable=False,
        doc="Unique identifier for the criteria (e.g., 'seismic_hazard', 'cyclone', 'soil_quality')"
    )

    weight = Column(
        DECIMAL(5, 4),
        nullable=False,
        doc="Normalized weight (0.0000 to 1.0000); must sum to 1.0 across all criteria in assessment type"
    )

    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        doc="UUID of the user who last modified this weight"
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
        doc="Timestamp of last modification (UTC)"
    )

    def __repr__(self):
        return (
            f"AHPWeight("
            f"id={self.id}, "
            f"weight_set='{self.weight_set_name}', "
            f"assessment='{self.assessment_type}', "
            f"criteria='{self.criteria_key}', "
            f"weight={self.weight}"
            f")"
        )
