"""Seed script for VMHLSS database.

Usage:
    python -m app.seed_data
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

# Import models
from app.models.dataset_slot import DatasetSlot
from app.models.user import User
from app.models.dataset_upload import DatasetUpload
from app.models.knowledge_base import KnowledgeBaseRecord
from app.models.analysis import Analysis
from app.models.audit_log import AuditLog
from app.models.report import Report


def get_session() -> Session:
    """Create and return a database session."""
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost/vmhlss")
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


def seed_dataset_slots(session: Session) -> None:
    """Seed dataset_slots table."""
    slots_data = [
        {
            "slot_code": "DS-01",
            "slot_name": "Digital Elevation Model (DEM)",
            "description": "High-resolution elevation data for terrain analysis",
            "required_for": "Slope calculation, surface modeling",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "30m resolution or better",
            "accepted_formats": ["GeoTIFF", "COG GeoTIFF"],
        },
        {
            "slot_code": "DS-02",
            "slot_name": "Cyclone Wind Hazard",
            "description": "Maximum sustained wind speed hazard zones",
            "required_for": "Wind risk assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Vanuatu extent coverage",
            "accepted_formats": ["GeoTIFF", "Shapefile", "GeoPackage"],
        },
        {
            "slot_code": "DS-03",
            "slot_name": "Tsunami Hazard Zones",
            "description": "Modeled tsunami inundation extents and return periods",
            "required_for": "Coastal hazard assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Coastal zones mapped",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoJSON"],
        },
        {
            "slot_code": "DS-04",
            "slot_name": "Volcanic Hazard Zones",
            "description": "Volcanic risk zones, lahar and tephra hazard areas",
            "required_for": "Volcanic hazard assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Active volcano zones identified",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoJSON"],
        },
        {
            "slot_code": "DS-05",
            "slot_name": "Flood Hazard",
            "description": "Flood-prone areas and flood inundation zones",
            "required_for": "Flood risk assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Vanuatu extent coverage",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoTIFF"],
        },
        {
            "slot_code": "DS-06",
            "slot_name": "Earthquake/Seismic Hazard (PGA)",
            "description": "Peak ground acceleration hazard data",
            "required_for": "Seismic risk assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "National coverage",
            "accepted_formats": ["GeoTIFF", "Shapefile"],
        },
        {
            "slot_code": "DS-07",
            "slot_name": "Landslide Susceptibility",
            "description": "Landslide susceptibility and slope failure zones",
            "required_for": "Slope stability assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Vanuatu extent coverage",
            "accepted_formats": ["GeoTIFF", "Shapefile"],
        },
        {
            "slot_code": "DS-08",
            "slot_name": "Protected Areas / Legal Exclusions",
            "description": "National parks, marine protected areas, restricted zones",
            "required_for": "Legal constraints",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "All protected areas mapped",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoJSON"],
        },
        {
            "slot_code": "DS-09",
            "slot_name": "Sea Level Rise Scenarios",
            "description": "Projected sea level rise inundation extents",
            "required_for": "Climate change impact assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Multiple scenarios (0.5m, 1m, 2m)",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoTIFF"],
        },
        {
            "slot_code": "DS-10",
            "slot_name": "Land Use / Land Cover (LULC)",
            "description": "Current land use and land cover classification",
            "required_for": "Land suitability assessment",
            "phase": "phase1",
            "is_compulsory": True,
            "minimum_standard": "Vanuatu extent, 10+ classes",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoTIFF"],
        },
        {
            "slot_code": "DS-11",
            "slot_name": "Soil Capability",
            "description": "Soil capability classification for agriculture and development",
            "required_for": "Agricultural suitability",
            "phase": "phase2",
            "is_compulsory": False,
            "minimum_standard": "Capability classes mapped",
            "accepted_formats": ["Shapefile", "GeoPackage"],
        },
        {
            "slot_code": "DS-12",
            "slot_name": "Cadastral Parcels",
            "description": "Land ownership and parcel boundaries",
            "required_for": "Land tenure analysis",
            "phase": "phase2",
            "is_compulsory": False,
            "minimum_standard": "Current cadastral data",
            "accepted_formats": ["Shapefile", "GeoPackage"],
        },
        {
            "slot_code": "DS-13",
            "slot_name": "Administrative Boundaries",
            "description": "Provincial, municipality, and district boundaries",
            "required_for": "Administrative analysis",
            "phase": "phase2",
            "is_compulsory": False,
            "minimum_standard": "Current administrative divisions",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoJSON"],
        },
        {
            "slot_code": "DS-14",
            "slot_name": "Infrastructure Networks",
            "description": "Roads, utilities, airports, ports, communications",
            "required_for": "Infrastructure accessibility",
            "phase": "phase2",
            "is_compulsory": False,
            "minimum_standard": "Major infrastructure mapped",
            "accepted_formats": ["Shapefile", "GeoPackage", "GeoJSON"],
        },
    ]

    for slot_data in slots_data:
        # Check if slot already exists
        existing = session.query(DatasetSlot).filter_by(slot_code=slot_data["slot_code"]).first()
        if not existing:
            slot = DatasetSlot(**slot_data)
            session.add(slot)
            print(f"Added dataset slot: {slot_data['slot_code']}")

    session.commit()


def seed_ahp_weights(session: Session) -> None:
    """Seed ahp_weights table with development and agriculture weights."""
    from sqlalchemy import text

    # Development weights
    development_weights = [
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "composite_hazard_index", "weight": Decimal("0.35")},
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "slope_degrees", "weight": Decimal("0.20")},
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "distance_from_coast_m", "weight": Decimal("0.15")},
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "soil_stability", "weight": Decimal("0.15")},
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "lulc_compatibility", "weight": Decimal("0.10")},
        {"weight_set_name": "development", "assessment_type": "development", "criteria_key": "slr_1m_inundation", "weight": Decimal("0.05")},
    ]

    # Agriculture weights
    agriculture_weights = [
        {"weight_set_name": "agriculture", "assessment_type": "agriculture", "criteria_key": "soil_capability_class", "weight": Decimal("0.30")},
        {"weight_set_name": "agriculture", "assessment_type": "agriculture", "criteria_key": "composite_hazard_index", "weight": Decimal("0.25")},
        {"weight_set_name": "agriculture", "assessment_type": "agriculture", "criteria_key": "slope_degrees", "weight": Decimal("0.20")},
        {"weight_set_name": "agriculture", "assessment_type": "agriculture", "criteria_key": "topographic_wetness_index", "weight": Decimal("0.15")},
        {"weight_set_name": "agriculture", "assessment_type": "agriculture", "criteria_key": "lulc_current", "weight": Decimal("0.10")},
    ]

    all_weights = development_weights + agriculture_weights

    for weight_data in all_weights:
        # Check if weight already exists
        existing = session.query(
            text("SELECT * FROM ahp_weights WHERE weight_set_name = :name AND criteria_key = :key")
        ).params(name=weight_data["weight_set_name"], key=weight_data["criteria_key"]).first()

        if not existing:
            # Use raw SQL insert to avoid model issues
            session.execute(
                text("""
                INSERT INTO ahp_weights (weight_set_name, assessment_type, criteria_key, weight)
                VALUES (:name, :type, :key, :weight)
                """),
                {
                    "name": weight_data["weight_set_name"],
                    "type": weight_data["assessment_type"],
                    "key": weight_data["criteria_key"],
                    "weight": float(weight_data["weight"]),
                },
            )
            print(f"Added AHP weight: {weight_data['weight_set_name']} - {weight_data['criteria_key']}")

    session.commit()


def main():
    """Run all seeding functions."""
    session = get_session()

    try:
        print("Starting database seeding...")
        print("\nSeeding dataset slots...")
        seed_dataset_slots(session)
        print("\nSeeding AHP weights...")
        seed_ahp_weights(session)
        print("\nDatabase seeding completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
