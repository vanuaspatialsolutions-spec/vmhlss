# VMHLSS Database Schema

## Entity Relationship Diagram (Text Format)

```
                            ┌──────────────────────┐
                            │      users           │
                            ├──────────────────────┤
                            │ id (UUID, PK)        │
                            │ email (VARCHAR, UNQ) │
                            │ password_hash        │
                            │ full_name            │
                            │ organisation         │
                            │ role                 │
                            │ is_active            │
                            │ two_factor_enabled   │
                            │ created_at           │
                            │ last_login           │
                            └──────────────────────┘
                                     △
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 │ created_by        │ created_by        │ created_by/uploaded_by
                 │                   │                   │
        ┌────────┴──────────┐  ┌─────┴──────────┐  ┌────┴──────────────────┐
        │                   │  │                │  │                       │
        │                   │  │                │  │                       │
    ┌───┴────────────────┐  │ ┌┴───────────────┐  │  ┌──────────────────────┐
    │ knowledge_base_    │  │ │   analyses     │  │  │  dataset_uploads     │
    │    records         │  │ │ (MULTIPOLYGON) │  │  │  (POLYGON geometry)  │
    ├───────────────────┤  │ ├────────────────┤  │  ├──────────────────────┤
    │ id (UUID, PK)     │  │ │ id (UUID, PK)  │  │  │ id (UUID, PK)        │
    │ category (FK)     │  │ │ analysis_name  │  │  │ slot_id (FK) ────┐   │
    │ subcategory       │  │ │ analysis_type  │  │  │ uploaded_by (FK)  │   │
    │ title             │  │ │ created_by (FK)│  │  │ organisation      │   │
    │ content           │  │ │ created_at     │  │  │ original_filename │   │
    │ source            │  │ │ updated_at     │  │  │ stored_filename   │   │
    │ source_url        │  │ │ description    │  │  │ file_path         │   │
    │ author            │  │ │ status         │  │  │ file_format       │   │
    │ created_by (FK)   │  │ │ study_area_    │  │  │ file_size_bytes   │   │
    │ created_at        │  │ │   geom (MULTI) │  │  │ upload_timestamp  │   │
    │ updated_at        │  │ │ ahp_weight_set │  │  │ qa_status         │   │
    │ is_published      │  │ │ custom_weights │  │  │ qa_report         │   │
    │ metadata          │  │ │ input_datasets │  │  │ fix_log           │   │
    │ tags              │  │ │ processing_*   │  │  │ geometry_type     │   │
    │ relevance_score   │  │ │ suitability_*  │  │  │ crs_detected      │   │
    │ is_active         │  │ │ output_geom    │  │  │ crs_assigned      │   │
    └───────────────────┘  │ │ constraints_*  │  │  │ coverage_pct      │   │
                           │ │ exclusion_*    │  │  │ data_date         │   │
                           │ │ resolution_m   │  │  │ is_active         │   │
                           │ │ metadata       │  │  │ geom_extent       │   │
                           │ │ is_public      │  │  └──────────────────────┘
                           │ │ is_archived    │  │            △
                           │ └────────────────┘  │            │
                           │         △           │            │
                           │         │           │   ┌────────┴────────┐
                           │         │           │   │                 │
                           │    has reports      └───┤ dataset_slots   │
                           │         │               │ (DS-01..DS-14)  │
                           │         │               ├─────────────────┤
                           │    ┌────┴──────────┐    │ id (UUID, PK)   │
                           │    │  reports      │    │ slot_code (UNQ) │
                           │    ├───────────────┤    │ slot_name       │
                           │    │ id (UUID, PK) │    │ description     │
                           │    │ report_name   │    │ required_for    │
                           │    │ report_type   │    │ phase           │
                           │    │ analysis_id   │◀───│ is_compulsory   │
                           │    │   (FK) ───────┤    │ minimum_std     │
                           │    │ created_by    │    │ fallback_src    │
                           │    │   (FK) ───────┼────│ accepted_fmt[]  │
                           │    │ created_at    │    │ required_attrs  │
                           │    │ updated_at    │    └─────────────────┘
                           │    │ description   │
                           │    │ exec_summary  │
                           │    │ sections      │
                           │    │ findings      │
                           │    │ recommend     │
                           │    │ limitations   │
                           │    │ statistics    │
                           │    │ visualiza'ns  │
                           │    │ maps          │
                           │    │ tables        │
                           │    │ data_sources  │
                           │    │ methodology   │
                           │    │ study_area_   │
                           │    │   geom        │
                           │    │ status        │
                           │    │ is_public     │
                           │    │ dist_list     │
                           │    │ access_level  │
                           │    │ report_path   │
                           │    │ attachments   │
                           │    │ tags          │
                           │    │ metadata      │
                           │    └───────────────┘
                           │
                           └─────────────────────────────────────┐
                                                                 │
                    ┌────────────────────────────────────────────┘
                    │
            ┌───────┴────────────┐
            │   audit_log        │◄────── IMMUTABLE (trigger prevents UPDATE/DELETE)
            │  (APPEND-ONLY)     │
            ├────────────────────┤
            │ id (BIGSERIAL, PK) │
            │ timestamp          │
            │ user_id (FK) ──────┼──┐
            │ user_email         │  │
            │ user_role          │  │
            │ action_type        │  │
            │ resource_type      │  │
            │ resource_id        │  │
            │ detail             │  │
            │ ip_address         │  │
            │ session_id         │  │
            └────────────────────┘  │
                                     │
                    ┌────────────────┘
                    │
            ┌───────┴────────────┐
            │    ahp_weights     │
            │  (Weight Config)   │
            ├────────────────────┤
            │ id (SERIAL, PK)    │
            │ weight_set_name    │
            │ assessment_type    │
            │ criteria_key       │
            │ weight             │
            │ updated_by (FK) ───┼──┐
            │ updated_at         │  │
            └────────────────────┘  │
                                     │
            ┌────────────────────────┤
            │                        │
            └─────────┬──────────────┘
                      │
            ┌─────────┴──────────┐
            │  vanuatu_places    │
            │  (Reference Data)  │
            ├────────────────────┤
            │ id (SERIAL, PK)    │
            │ name               │
            │ name_bi            │
            │ place_type         │
            │ island             │
            │ province           │
            │ geom (POINT)       │
            └────────────────────┘
```

## Table Specifications

### 1. users
Primary user account table with role-based access control.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Distributed ID |
| email | VARCHAR | UNIQUE, NOT NULL | Login identifier |
| password_hash | VARCHAR | NOT NULL | Hashed password |
| full_name | VARCHAR | NOT NULL | User display name |
| organisation | VARCHAR | NULL | Optional org affiliation |
| role | VARCHAR | NOT NULL | admin, data_manager, analyst, reviewer, public |
| is_active | BOOLEAN | DEFAULT true | Account activation flag |
| two_factor_enabled | BOOLEAN | DEFAULT false | 2FA status |
| created_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| last_login | TIMESTAMPTZ | NULL | Last login timestamp |

**Indexes**: email (unique)

---

### 2. dataset_slots
Configuration of 14 data input slots (DS-01 through DS-14).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Slot ID |
| slot_code | VARCHAR | UNIQUE, NOT NULL | DS-01 to DS-14 |
| slot_name | VARCHAR | NOT NULL | Human-readable name |
| description | TEXT | NULL | Detailed description |
| required_for | TEXT | NULL | Use case |
| phase | VARCHAR | NOT NULL | phase1, phase2 |
| is_compulsory | BOOLEAN | NOT NULL | Requirement flag |
| minimum_standard | TEXT | NULL | Quality standard |
| fallback_source | VARCHAR | NULL | Alternative source |
| accepted_formats | VARCHAR[] | NULL | Array of acceptable formats |
| required_attributes | JSONB | NULL | Required field definitions |

**Indexes**: slot_code (unique)

---

### 3. dataset_uploads
Tracks all dataset uploads with QA status and processing history.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Upload ID |
| slot_id | UUID | FK → dataset_slots.id | Which slot |
| uploaded_by | UUID | FK → users.id | Uploader |
| organisation | VARCHAR | NULL | Uploader's org |
| original_filename | VARCHAR | NOT NULL | Original name |
| stored_filename | VARCHAR | NOT NULL | Stored as |
| file_path | VARCHAR | NOT NULL | Storage path |
| file_format | VARCHAR | NULL | GeoTIFF, Shapefile, etc. |
| file_size_bytes | BIGINT | NULL | File size |
| upload_timestamp | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| qa_status | VARCHAR | NULL | pending, pass, conditional, auto_fixed, failed |
| qa_report | JSONB | NULL | QA details |
| fix_log | JSONB[] | NULL | Applied fixes |
| geometry_type | VARCHAR | NULL | Point, LineString, Polygon |
| crs_detected | VARCHAR | NULL | Detected CRS |
| crs_assigned | VARCHAR | NULL | Assigned CRS |
| coverage_pct | NUMERIC(5,2) | NULL | Coverage percentage |
| data_date | DATE | NULL | Data production date |
| is_active | BOOLEAN | DEFAULT true | Active flag |
| geom_extent | GEOMETRY(POLYGON, 4326) | NULL | Bounding polygon |

**Indexes**: slot_id, uploaded_by

---

### 4. knowledge_base_records
Searchable knowledge base for hazards, methodology, policies, best practices.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Record ID |
| category | VARCHAR | NOT NULL, INDEX | hazard, methodology, policy, best_practice |
| subcategory | VARCHAR | NULL, INDEX | Finer classification |
| title | VARCHAR | NOT NULL | Record title |
| content | TEXT | NOT NULL | Full content |
| source | VARCHAR | NULL | Information source |
| source_url | VARCHAR | NULL | Reference URL |
| author | VARCHAR | NULL | Content author |
| created_by | UUID | FK → users.id | Creator |
| created_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| is_published | BOOLEAN | DEFAULT false | Publication flag |
| metadata | JSONB | NULL | Flexible metadata |
| tags | JSONB | NULL | Array of tags |
| relevance_score | VARCHAR | NULL | Relevance rating |
| is_active | BOOLEAN | DEFAULT true | Active flag |

**Indexes**: category, subcategory

---

### 5. analyses
Main analysis and suitability assessment table.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Analysis ID |
| analysis_name | VARCHAR | NOT NULL | User-given name |
| analysis_type | VARCHAR | NOT NULL | development, agriculture, infrastructure, custom |
| created_by | UUID | FK → users.id | Analysis creator |
| created_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| description | TEXT | NULL | Analysis description |
| status | VARCHAR | NOT NULL | draft, in_progress, completed, archived |
| study_area_geom | GEOMETRY(MULTIPOLYGON, 4326) | NOT NULL | Study area boundary |
| ahp_weight_set | VARCHAR | NULL | Reference weight set |
| custom_weights | JSONB | NULL | Custom weights JSON |
| input_datasets | JSONB | NULL | Array of dataset_upload IDs |
| processing_params | JSONB | NULL | Processing configuration |
| processing_status | VARCHAR | NULL | pending, processing, completed, failed |
| processing_log | TEXT | NULL | Processing history |
| processing_error | TEXT | NULL | Error message if failed |
| suitability_raster | VARCHAR | NULL | Output raster path |
| suitability_classes | JSONB | NULL | Class definitions and areas |
| output_geom | GEOMETRY(MULTIPOLYGON, 4326) | NULL | Classified output geometry |
| statistics | JSONB | NULL | Summary statistics |
| constraints_applied | JSONB | NULL | Applied constraints |
| exclusion_masks | JSONB | NULL | Exclusion areas |
| crs | VARCHAR | DEFAULT 'EPSG:4326' | Coordinate reference system |
| resolution_m | NUMERIC(10,2) | NULL | Grid resolution in meters |
| metadata | JSONB | NULL | Additional metadata |
| is_public | BOOLEAN | DEFAULT false | Public visibility |
| is_archived | BOOLEAN | DEFAULT false | Archive flag |

**Notes**: Core analytical output table; supports progress tracking

---

### 6. audit_log
Immutable append-only audit trail of all system actions.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | BIGSERIAL | PK, AUTOINCREMENT | Log entry ID |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Action time (UTC) |
| user_id | UUID | FK → users.id, NULL | User who acted |
| user_email | VARCHAR | NULL | User email snapshot |
| user_role | VARCHAR | NULL | User role snapshot |
| action_type | VARCHAR | NOT NULL, INDEX | create, read, update, delete, login, export |
| resource_type | VARCHAR | NULL, INDEX | user, dataset_upload, analysis, report |
| resource_id | VARCHAR | NULL, INDEX | ID of affected resource |
| detail | JSONB | NULL | Action details |
| ip_address | INET | NULL | Source IP address |
| session_id | VARCHAR | NULL, INDEX | Session identifier |

**Trigger**: prevent_audit_modification() blocks UPDATE and DELETE
**Indexes**: action_type, resource_type, resource_id, user_id, session_id

---

### 7. reports
Generated reports from analyses with multiple export formats.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Report ID |
| report_name | VARCHAR | NOT NULL | Report title |
| report_type | VARCHAR | NOT NULL, INDEX | suitability_assessment, qa_summary, etc. |
| analysis_id | UUID | FK → analyses.id, NULL | Linked analysis |
| created_by | UUID | FK → users.id | Report creator |
| created_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |
| description | TEXT | NULL | Report description |
| executive_summary | TEXT | NULL | Executive summary |
| sections | JSONB | NULL | Report sections array |
| findings | JSONB | NULL | Key findings |
| recommendations | JSONB | NULL | Recommendations array |
| limitations | JSONB | NULL | Known limitations |
| statistics | JSONB | NULL | Numerical summaries |
| visualizations | JSONB | NULL | Chart/graph references |
| maps | JSONB | NULL | Map references |
| tables | JSONB | NULL | Embedded tables |
| data_sources | JSONB | NULL | Data source list |
| methodology | TEXT | NULL | Methodology description |
| crs | VARCHAR | DEFAULT 'EPSG:4326' | Coordinate system |
| study_area_geom | GEOMETRY(MULTIPOLYGON, 4326) | NULL | Study area boundary |
| status | VARCHAR | NOT NULL | draft, review, approved, published, archived |
| is_public | BOOLEAN | DEFAULT false | Public visibility |
| distribution_list | JSONB | NULL | Recipients array |
| access_level | VARCHAR | NULL | private, internal, public |
| report_file_path | VARCHAR | NULL | PDF/DOCX export path |
| attachments | JSONB | NULL | Attached files |
| tags | JSONB | NULL | Tag array |
| metadata | JSONB | NULL | Additional metadata |

**Indexes**: report_type, analysis_id

---

### 8. vanuatu_places
Reference table of Vanuatu places (islands, provinces, towns, villages).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PK, AUTOINCREMENT | Place ID |
| name | VARCHAR | NOT NULL | Place name (English) |
| name_bi | VARCHAR | NULL | Bilingual name |
| place_type | VARCHAR | NULL | island, province, municipality, village, etc. |
| island | VARCHAR | NULL | Island name |
| province | VARCHAR | NULL | Province name |
| geom | GEOMETRY(POINT, 4326) | NULL | Point location |

---

### 9. ahp_weights
Analytic Hierarchy Process (AHP) weight configurations.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PK, AUTOINCREMENT | Weight ID |
| weight_set_name | VARCHAR | DEFAULT 'default' | development, agriculture, custom |
| assessment_type | VARCHAR | NULL | Type of assessment |
| criteria_key | VARCHAR | NULL | Criteria identifier |
| weight | NUMERIC(5,4) | NULL | Weight value (0.0000-1.0000) |
| updated_by | UUID | FK → users.id, NULL | Last updater |
| updated_at | TIMESTAMPTZ | DEFAULT now() | UTC timestamp |

---

## Key Design Patterns

### 1. UUID Primary Keys
All user-facing tables use UUID for:
- Distributed system support
- Non-sequential IDs
- Better privacy/security

### 2. JSONB for Flexibility
Used for:
- Variable configuration data
- Processing parameters
- Statistics and results
- Tags and metadata

### 3. Geometry Support
Using GeoAlchemy2 GEOMETRY type with:
- SRID 4326 (WGS84 - global standard)
- POLYGON for extent/bounds
- MULTIPOLYGON for study areas and classified zones
- POINT for place locations

### 4. Audit Trail
- BIGSERIAL IDs for high-volume append-only table
- Immutable trigger prevents modification
- Timestamp tracking for all changes
- Resource type/ID linking for traceability

### 5. Timestamps
- All timestamps use `DateTime(timezone=True)` (UTC)
- Automatic `created_at` and `updated_at`
- Audit entries timestamped for every action

### 6. Foreign Keys
- Referential integrity enforced
- Cascading not used (preserve audit trail)
- Users as root reference entity

## Constraints and Triggers

### Audit Log Immutability Trigger

```sql
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log is immutable. Records cannot be modified or deleted.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

This ensures audit records are write-once and tamper-proof.

## Extensions Required

- **PostGIS**: Spatial database support (GEOMETRY types)
- **uuid-ossp**: UUID generation functions

Both are enabled in the initial migration.
