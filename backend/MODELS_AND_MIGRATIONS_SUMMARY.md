# VMHLSS SQLAlchemy Models and Alembic Migrations

## Summary

Complete SQLAlchemy models, Alembic migration files, and seeding scripts have been created for the Vanuatu Multi-Hazard Land Suitability System (VMHLSS).

## Files Created

### 1. SQLAlchemy Models (`app/models/`)

#### `app/models/__init__.py`
- Central import hub for all models
- Exports: User, DatasetSlot, DatasetUpload, KnowledgeBaseRecord, Analysis, AuditLog, Report

#### `app/models/user.py`
**Table: `users`**
- `id`: UUID PK (gen_random_uuid)
- `email`: VARCHAR UNIQUE NOT NULL
- `password_hash`: VARCHAR NOT NULL
- `full_name`: VARCHAR NOT NULL
- `organisation`: VARCHAR
- `role`: VARCHAR (admin, data_manager, analyst, reviewer, public)
- `is_active`: BOOLEAN (default: true)
- `two_factor_enabled`: BOOLEAN (default: false)
- `created_at`: TIMESTAMPTZ (default: now())
- `last_login`: TIMESTAMPTZ

#### `app/models/dataset_slot.py`
**Table: `dataset_slots`**
- `id`: UUID PK (gen_random_uuid)
- `slot_code`: VARCHAR UNIQUE (DS-01 to DS-14)
- `slot_name`: VARCHAR
- `description`: TEXT
- `required_for`: TEXT
- `phase`: VARCHAR (phase1, phase2)
- `is_compulsory`: BOOLEAN
- `minimum_standard`: TEXT
- `fallback_source`: VARCHAR
- `accepted_formats`: ARRAY[VARCHAR]
- `required_attributes`: JSONB

#### `app/models/dataset_upload.py`
**Table: `dataset_uploads`**
- `id`: UUID PK
- `slot_id`: UUID FK → dataset_slots
- `uploaded_by`: UUID FK → users
- `organisation`: VARCHAR
- `original_filename`: VARCHAR
- `stored_filename`: VARCHAR
- `file_path`: VARCHAR
- `file_format`: VARCHAR
- `file_size_bytes`: BIGINT
- `upload_timestamp`: TIMESTAMPTZ (default: now())
- `qa_status`: VARCHAR (pending, pass, conditional, auto_fixed, failed)
- `qa_report`: JSONB
- `fix_log`: ARRAY[JSONB]
- `geometry_type`: VARCHAR
- `crs_detected`: VARCHAR
- `crs_assigned`: VARCHAR
- `coverage_pct`: NUMERIC(5,2)
- `data_date`: DATE
- `is_active`: BOOLEAN (default: true)
- `geom_extent`: GEOMETRY(POLYGON, 4326)

#### `app/models/knowledge_base.py`
**Table: `knowledge_base_records`**
- `id`: UUID PK
- `category`: VARCHAR (hazard, methodology, policy, best_practice)
- `subcategory`: VARCHAR
- `title`: VARCHAR
- `content`: TEXT
- `source`: VARCHAR
- `source_url`: VARCHAR
- `author`: VARCHAR
- `created_by`: UUID FK → users
- `created_at`: TIMESTAMPTZ (default: now())
- `updated_at`: TIMESTAMPTZ (default: now())
- `is_published`: BOOLEAN (default: false)
- `metadata`: JSONB
- `tags`: JSONB
- `relevance_score`: VARCHAR
- `is_active`: BOOLEAN (default: true)

#### `app/models/analysis.py`
**Table: `analyses`**
- `id`: UUID PK
- `analysis_name`: VARCHAR
- `analysis_type`: VARCHAR (development, agriculture, infrastructure, custom)
- `created_by`: UUID FK → users
- `created_at`: TIMESTAMPTZ (default: now())
- `updated_at`: TIMESTAMPTZ (default: now())
- `description`: TEXT
- `status`: VARCHAR (draft, in_progress, completed, archived)
- `study_area_geom`: GEOMETRY(MULTIPOLYGON, 4326)
- `ahp_weight_set`: VARCHAR
- `custom_weights`: JSONB
- `input_datasets`: JSONB
- `processing_params`: JSONB
- `processing_status`: VARCHAR (pending, processing, completed, failed)
- `processing_log`: TEXT
- `processing_error`: TEXT
- `suitability_raster`: VARCHAR
- `suitability_classes`: JSONB
- `output_geom`: GEOMETRY(MULTIPOLYGON, 4326)
- `statistics`: JSONB
- `constraints_applied`: JSONB
- `exclusion_masks`: JSONB
- `crs`: VARCHAR (default: EPSG:4326)
- `resolution_m`: NUMERIC(10,2)
- `metadata`: JSONB
- `is_public`: BOOLEAN (default: false)
- `is_archived`: BOOLEAN (default: false)

#### `app/models/audit_log.py`
**Table: `audit_log` (Append-only, Immutable)**
- `id`: BIGSERIAL PK
- `timestamp`: TIMESTAMPTZ (default: now())
- `user_id`: UUID FK → users
- `user_email`: VARCHAR
- `user_role`: VARCHAR
- `action_type`: VARCHAR (create, read, update, delete, login, logout, export, etc.)
- `resource_type`: VARCHAR (user, dataset_upload, analysis, report, etc.)
- `resource_id`: VARCHAR
- `detail`: JSONB
- `ip_address`: INET
- `session_id`: VARCHAR
- **Note**: Immutable trigger prevents UPDATE and DELETE operations

#### `app/models/report.py`
**Table: `reports`**
- `id`: UUID PK
- `report_name`: VARCHAR
- `report_type`: VARCHAR (suitability_assessment, qa_summary, executive_summary, detailed_analysis, custom)
- `analysis_id`: UUID FK → analyses
- `created_by`: UUID FK → users
- `created_at`: TIMESTAMPTZ (default: now())
- `updated_at`: TIMESTAMPTZ (default: now())
- `description`: TEXT
- `executive_summary`: TEXT
- `sections`: JSONB
- `findings`: JSONB
- `recommendations`: JSONB
- `limitations`: JSONB
- `statistics`: JSONB
- `visualizations`: JSONB
- `maps`: JSONB
- `tables`: JSONB
- `data_sources`: JSONB
- `methodology`: TEXT
- `crs`: VARCHAR (default: EPSG:4326)
- `study_area_geom`: GEOMETRY(MULTIPOLYGON, 4326)
- `status`: VARCHAR (draft, review, approved, published, archived)
- `is_public`: BOOLEAN (default: false)
- `distribution_list`: JSONB
- `access_level`: VARCHAR (private, internal, public)
- `report_file_path`: VARCHAR
- `attachments`: JSONB
- `tags`: JSONB
- `metadata`: JSONB

### 2. Alembic Configuration Files (`migrations/`)

#### `migrations/alembic.ini`
- Standard Alembic configuration file
- Points to `migrations/` directory for migration scripts
- Configurable for logging and naming conventions

#### `migrations/env.py`
- Alembic environment configuration
- Supports async SQLAlchemy
- Reads `DATABASE_URL` from environment variable
- Supports both offline and online migration modes

#### `migrations/versions/001_initial_schema.py`
**Complete initial migration with:**
- PostgreSQL extension setup (PostGIS, uuid-ossp)
- All 7 core tables
- Additional support tables:
  - `vanuatu_places`: Places with POINT geometry
  - `ahp_weights`: AHP weight configuration
- Audit log immutability trigger
- All foreign key constraints
- All indexes for performance
- Full downgrade support

### 3. Seeding Script

#### `app/seed_data.py`
**Idempotent seeding script that populates:**

**Dataset Slots (14 total)**
- DS-01 to DS-10: Phase 1 (compulsory)
  - DEM, Cyclone, Tsunami, Volcanic, Flood, Earthquake, Landslide, Protected Areas, Sea Level Rise, LULC
- DS-11 to DS-14: Phase 2 (optional)
  - Soil Capability, Cadastral, Administrative Boundaries, Infrastructure

**AHP Weights (11 total)**
- **Development assessment** (6 weights):
  - composite_hazard_index: 0.35
  - slope_degrees: 0.20
  - distance_from_coast_m: 0.15
  - soil_stability: 0.15
  - lulc_compatibility: 0.10
  - slr_1m_inundation: 0.05

- **Agriculture assessment** (5 weights):
  - soil_capability_class: 0.30
  - composite_hazard_index: 0.25
  - slope_degrees: 0.20
  - topographic_wetness_index: 0.15
  - lulc_current: 0.10

**Features:**
- Checks for existing data before seeding (idempotent)
- Handles database connections via environment variable
- Comprehensive error handling
- Detailed logging output

## Technology Stack

- **SQLAlchemy**: ORM with PostgreSQL dialect
- **GeoAlchemy2**: Spatial types (GEOMETRY, POINT, POLYGON, MULTIPOLYGON)
- **Alembic**: Database migration management
- **PostgreSQL**: Backend database with PostGIS extension

## Usage

### Running Migrations

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@localhost/vmhlss"

# Upgrade to latest migration
alembic upgrade head

# Downgrade all migrations
alembic downgrade base

# Create new migration
alembic revision --autogenerate -m "migration name"
```

### Running Seed Script

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@localhost/vmhlss"

# Run seed script
python -m app.seed_data
```

### Using Models in Application

```python
from app.models import (
    User,
    DatasetSlot,
    DatasetUpload,
    KnowledgeBaseRecord,
    Analysis,
    AuditLog,
    Report,
)
from sqlalchemy.orm import Session

# Query example
def get_user(session: Session, user_id: UUID):
    return session.query(User).filter(User.id == user_id).first()

# Create example
def create_analysis(session: Session, analysis_data: dict):
    analysis = Analysis(**analysis_data)
    session.add(analysis)
    session.commit()
    return analysis
```

## File Locations

```
/sessions/pensive-blissful-curie/mnt/Vanuatu DSS/vmhlss/backend/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── dataset_slot.py
│   │   ├── dataset_upload.py
│   │   ├── knowledge_base.py
│   │   ├── analysis.py
│   │   ├── audit_log.py
│   │   └── report.py
│   ├── seed_data.py
│   └── [other app files]
└── migrations/
    ├── __init__.py
    ├── alembic.ini
    ├── env.py
    └── versions/
        ├── __init__.py
        └── 001_initial_schema.py
```

## Key Features

1. **UUID Primary Keys**: All user-facing tables use UUID for distributed systems support
2. **Audit Logging**: Immutable audit log with timestamp and resource tracking
3. **GIS Support**: Geometry columns with SRID 4326 (WGS84) projection
4. **JSONB Storage**: Flexible storage for complex data structures
5. **Foreign Key Constraints**: Referential integrity across all tables
6. **Indexing**: Strategic indexes on frequently queried columns
7. **Timestamps**: Automatic created_at and updated_at tracking
8. **Role-Based Access**: User roles for RBAC implementation
9. **Idempotent Seeding**: Safe to run multiple times without duplicates
10. **Complete Downgrade Support**: All migrations are reversible

## Notes

- All timestamps use PostgreSQL's `DateTime(timezone=True)` for UTC awareness
- GeoAlchemy2 requires PostGIS extension enabled on database
- ARRAY and JSONB types provide flexible schema design
- Models use SQLAlchemy declarative base for clean definition
- Audit log uses BIGSERIAL for high-volume transaction support
