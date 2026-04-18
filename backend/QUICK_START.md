# VMHLSS Database Setup Quick Start

## Prerequisites

```bash
# Install required Python packages
pip install sqlalchemy alembic geoalchemy2 psycopg2-binary
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Create database
createdb vmhlss

# Enable PostGIS extension
psql vmhlss -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql vmhlss -c "CREATE EXTENSION IF NOT EXISTS uuid-ossp;"
```

### 2. Run Migrations

```bash
# Navigate to backend directory
cd /sessions/pensive-blissful-curie/mnt/Vanuatu\ DSS/vmhlss/backend

# Set database URL
export DATABASE_URL="postgresql://localhost/vmhlss"

# Run migrations
alembic upgrade head
```

### 3. Seed Initial Data

```bash
# Run seeding script
python -m app.seed_data
```

## Verification

```bash
# Connect to database
psql vmhlss

# List all tables
\dt

# Check dataset_slots were seeded
SELECT slot_code, slot_name, phase, is_compulsory FROM dataset_slots ORDER BY slot_code;

# Check AHP weights were seeded
SELECT weight_set_name, criteria_key, weight FROM ahp_weights ORDER BY weight_set_name, criteria_key;

# Check audit log trigger
SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'audit_log';
```

## Common Tasks

### Create a New User

```python
from app.models import User
from sqlalchemy.orm import Session
from uuid import uuid4

def create_user(session: Session, email: str, full_name: str, role: str):
    user = User(
        id=uuid4(),
        email=email,
        password_hash="hashed_password_here",
        full_name=full_name,
        role=role,  # 'admin', 'data_manager', 'analyst', 'reviewer', 'public'
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user
```

### Create an Analysis

```python
from app.models import Analysis
from uuid import uuid4
from datetime import datetime
from shapely.geometry import box
from geoalchemy2.elements import WKTElement

def create_analysis(session: Session, user_id, name: str):
    # Create a study area polygon (example: Efate island bounds)
    study_area = WKTElement(
        "POLYGON((168.3 -17.8, 168.5 -17.8, 168.5 -17.6, 168.3 -17.6, 168.3 -17.8))",
        srid=4326
    )

    analysis = Analysis(
        id=uuid4(),
        analysis_name=name,
        analysis_type="development",
        created_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        status="draft",
        study_area_geom=study_area,
        ahp_weight_set="development",
    )
    session.add(analysis)
    session.commit()
    return analysis
```

### Create a Dataset Upload

```python
from app.models import DatasetUpload
from uuid import uuid4
from datetime import datetime

def create_dataset_upload(session: Session, slot_id, user_id, filename: str):
    upload = DatasetUpload(
        id=uuid4(),
        slot_id=slot_id,
        uploaded_by=user_id,
        original_filename=filename,
        stored_filename=f"stored_{uuid4()}_{filename}",
        file_path=f"/uploads/datasets/{stored_filename}",
        file_format="GeoTIFF",
        upload_timestamp=datetime.utcnow(),
        qa_status="pending",
    )
    session.add(upload)
    session.commit()
    return upload
```

### Query Dataset Slots

```python
from app.models import DatasetSlot

def get_phase1_slots(session: Session):
    """Get all Phase 1 (compulsory) slots"""
    return session.query(DatasetSlot).filter(
        DatasetSlot.phase == "phase1"
    ).all()

def get_slot_by_code(session: Session, code: str):
    """Get slot by code (e.g., 'DS-01')"""
    return session.query(DatasetSlot).filter(
        DatasetSlot.slot_code == code
    ).first()
```

### Query Audit Log

```python
from app.models import AuditLog
from datetime import datetime, timedelta

def get_recent_actions(session: Session, hours: int = 24):
    """Get audit log entries from past N hours"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return session.query(AuditLog).filter(
        AuditLog.timestamp >= cutoff
    ).order_by(AuditLog.timestamp.desc()).all()

def get_user_actions(session: Session, user_id):
    """Get all actions by a specific user"""
    return session.query(AuditLog).filter(
        AuditLog.user_id == user_id
    ).order_by(AuditLog.timestamp.desc()).all()
```

### Create an Audit Log Entry

```python
from app.models import AuditLog
from datetime import datetime

def log_action(session: Session, user_id, action: str, resource_type: str, resource_id: str, detail: dict = None):
    """Log user action"""
    log_entry = AuditLog(
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action_type=action,  # 'create', 'read', 'update', 'delete', 'export', etc.
        resource_type=resource_type,  # 'analysis', 'dataset_upload', 'report', etc.
        resource_id=resource_id,
        detail=detail,
    )
    session.add(log_entry)
    session.commit()
```

## Migration Management

### Create a New Migration

```bash
# Navigate to backend directory
cd /sessions/pensive-blissful-curie/mnt/Vanuatu\ DSS/vmhlss/backend

# Set database URL
export DATABASE_URL="postgresql://localhost/vmhlss"

# Create new migration with autogenerate (if using autogenerate)
alembic revision --autogenerate -m "Add new column to users table"

# Or create empty migration
alembic revision -m "Custom migration name"
```

### View Migration History

```bash
# Show current migration version
alembic current

# Show all migrations
alembic branches

# Show migration heads
alembic heads
```

### Rollback Migrations

```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 001

# Downgrade all (back to initial state)
alembic downgrade base
```

## Database Backup & Restore

```bash
# Backup database
pg_dump vmhlss > vmhlss_backup.sql

# Restore database
createdb vmhlss_restored
psql vmhlss_restored < vmhlss_backup.sql

# Backup with geometry data
pg_dump -Fc vmhlss > vmhlss_backup.dump
pg_restore -d vmhlss_restored vmhlss_backup.dump
```

## Troubleshooting

### PostGIS Extension Not Found

```sql
-- Check if PostGIS is installed
SELECT version();

-- If not installed, you may need to install PostGIS extension package
-- Then create extension
CREATE EXTENSION postgis;
CREATE EXTENSION uuid-ossp;
```

### Migration Failed

```bash
# Check current alembic version
alembic current

# Check database state
alembic history --verbose

# Reset to base (use with caution!)
alembic downgrade base

# Re-run migration
alembic upgrade head
```

### UUID Column Issues

Ensure your PostgreSQL version supports `gen_random_uuid()` (PostgreSQL 13+), or use:

```sql
-- Alternative for older PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Then in models: server_default=func.uuid_generate_v4()
```

## Performance Optimization

### Create Additional Indexes

```sql
-- Index for faster dataset upload queries
CREATE INDEX idx_dataset_uploads_qa_status ON dataset_uploads(qa_status);
CREATE INDEX idx_dataset_uploads_is_active ON dataset_uploads(is_active);

-- Index for analysis queries
CREATE INDEX idx_analyses_created_by ON analyses(created_by);
CREATE INDEX idx_analyses_status ON analyses(status);

-- Index for report queries
CREATE INDEX idx_reports_created_by ON reports(created_by);
CREATE INDEX idx_reports_status ON reports(status);
```

### Vacuum and Analyze

```bash
# Optimize database after large data operations
psql vmhlss -c "VACUUM ANALYZE;"
```

## File Locations Reference

| File | Path |
|------|------|
| User Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/user.py` |
| Dataset Slot Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/dataset_slot.py` |
| Dataset Upload Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/dataset_upload.py` |
| Knowledge Base Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/knowledge_base.py` |
| Analysis Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/analysis.py` |
| Audit Log Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/audit_log.py` |
| Report Model | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/report.py` |
| Models Init | `/mnt/Vanuatu DSS/vmhlss/backend/app/models/__init__.py` |
| Alembic Config | `/mnt/Vanuatu DSS/vmhlss/backend/migrations/alembic.ini` |
| Alembic Env | `/mnt/Vanuatu DSS/vmhlss/backend/migrations/env.py` |
| Initial Migration | `/mnt/Vanuatu DSS/vmhlss/backend/migrations/versions/001_initial_schema.py` |
| Seed Script | `/mnt/Vanuatu DSS/vmhlss/backend/app/seed_data.py` |

## Support

For detailed information on:
- Model schemas: See `MODELS_AND_MIGRATIONS_SUMMARY.md`
- Migration details: See `migrations/versions/001_initial_schema.py`
- Seeding logic: See `app/seed_data.py`
