# Vanuatu Multi-Hazard Land Suitability System (VMHLSS)

**Architecture Reference:** VMHLSS / GoV / SYS-ARCH / 2026-001 v1.3  
**Version:** 1.0.0  
**Status:** Development Preview

> A production-ready, AI-powered geospatial decision support system for the Government of Vanuatu, enabling government planners, developers, farmers, engineers, and communities to make informed land use decisions based on multi-hazard risk analysis.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Suitability Classes](#suitability-classes)
- [Data Slots (DS-01 to DS-14)](#data-slots-ds-01-to-ds-14)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [User Roles & Permissions](#user-roles--permissions)
- [Deployment Guide (GitHub Actions + Render)](#deployment-guide-github-actions--render)
- [Migration to Government Server](#migration-to-government-server)
- [Testing](#testing)
- [Bislama Language Support](#bislama-language-support)
- [Architecture Notes](#architecture-notes)
- [Licence](#licence)

---

## Overview

The Vanuatu Multi-Hazard Land Suitability System (VMHLSS) is a government decision-support system designed to classify land across Vanuatu into six suitability classes (S1–NS) for two primary use cases: **urban and infrastructure development**, and **agricultural use**.

The system utilizes a **multi-hazard composite index** that integrates cyclone, tsunami, volcanic, flood, earthquake, and landslide hazards. It employs five AI expert personas—powered by the Claude API—who generate tailored recommendations based on the assessed land suitability:

1. **Developer** — Infrastructure and urban planning perspective
2. **Agriculture Expert** — Crop production and soil management perspective
3. **Farmer** — Practical field-level perspective
4. **GIS Analyst** — Technical spatial analysis perspective
5. **Civil Engineer** — Structural and geotechnical engineering perspective

The system combines automated data quality assurance, multi-criteria evaluation, and geospatial analysis to provide standardized, transparent, and auditable suitability classifications that support land-use planning and disaster risk reduction.

---

## Features

- **Multi-hazard composite index:** Integrates cyclone, tsunami, volcanic, flood, earthquake, and landslide hazard data with automated weighting
- **Six-stage automated data QA pipeline:** Validates format, geospatial readability, CRS consistency, spatial validity, attribute completeness, and statistical plausibility with automatic fixes where possible
- **Document intelligence:** Claude API extracts hazard maps, soil data, and engineering reports from PDF uploads
- **Map georeferencing and digitisation:** Automated extraction of geospatial features from scanned historical maps
- **Five AI expert personas:** Context-aware recommendations in both English and Bislama
- **Bilingual interface:** Full English / Bislama language support
- **PDF report generation:** Government-branded suitability assessments with maps and recommendations
- **Web-based access:** No GIS software required—works via any modern web browser
- **Starlink-compatible:** Optimised for low-bandwidth, high-latency satellite connections
- **Role-based access control:** Five granular permission levels (Admin, Uploader, Analyst, Reviewer, Public)
- **Complete audit trail:** Immutable append-only log of all operations for compliance and transparency

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend - Language & Framework** | Python 3.11 | Runtime |
| | FastAPI | REST API framework |
| **Backend - Data & ORM** | PostgreSQL 15 | Primary database |
| | PostGIS 3.4 | Geospatial database extension |
| | SQLAlchemy | ORM |
| | GeoAlchemy2 | Geospatial SQLAlchemy support |
| **Backend - Async & Queuing** | Celery | Asynchronous task queue |
| | Redis | Message broker and caching |
| **Backend - Geospatial** | GDAL/OGR | Format conversion and processing |
| | Rasterio | Raster data I/O |
| | Fiona | Vector format I/O |
| | Shapely | Geometric operations |
| **Backend - AI & Integration** | Claude API (Anthropic) | Document intelligence and AI personas |
| | Alembic | Database schema migrations |
| **Frontend - Language & Framework** | React 18 | UI framework |
| | TypeScript | Type-safe JavaScript |
| | Vite | Build tool and dev server |
| **Frontend - Mapping & Visualization** | MapLibre GL JS | Interactive vector maps |
| | Tailwind CSS | Utility-first CSS framework |
| **Frontend - State & Logic** | Zustand | Client state management |
| | Recharts | Data visualization charts |
| **Infrastructure - Containerization** | Docker | Container runtime |
| | Docker Compose | Multi-container orchestration |
| **Infrastructure - Web Server** | Nginx | Reverse proxy and static asset serving |
| **Infrastructure - CI/CD & Deployment** | GitHub Actions | Continuous integration and deployment |
| | Render.com | Managed backend deployment |
| | Railway / Government Server | Alternative deployment targets |

---

## Suitability Classes

Standardized land suitability classification following FAO guidelines:

| Class | Name | Colour | Development | Agriculture | Description |
|-------|------|--------|-------------|-------------|-------------|
| **S1** | Highly Suitable | #1a5c30 | Build | Farm | Few/minor limitations; suitable for wide range of uses |
| **S2** | Suitable with Conditions | #4aa040 | Build with conditions | Farm with care | Some limitations; suitable with management and mitigation |
| **S3** | Marginally Suitable | #c8a000 | Engineering required | Limited farming | Significant limitations; specialized use and engineering required |
| **S4** | Currently Not Suitable | #c85000 | Do not build | Do not farm | Very significant limitations; not recommended for intended use |
| **S5** | Permanently Unsuitable | #8b2000 | Do not build | Do not farm | Extreme limitations; unsuitable and hazardous |
| **NS** | No-Go / Legally Protected | #1a1a1a | Prohibited | Prohibited | Boolean exclusion (protected areas, strict hazard zones, legal constraints) |

---

## Data Slots (DS-01 to DS-14)

14 standardized dataset slots supporting multi-use assessment:

| Code | Name | Phase | Required | Accepted Formats | Purpose |
|------|------|-------|----------|-----------------|---------|
| **DS-01** | Seismic Hazard (PGA) | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Peak ground acceleration raster; critical for development and agriculture |
| **DS-02** | Volcanic Hazard | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Volcanic zones, lava flow, pyroclastic flow risk; excludes NS zones |
| **DS-03** | Cyclone Wind Speed | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Maximum wind speed raster (km/h); primary hazard in region |
| **DS-04** | Tsunami Inundation | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Tsunami inundation depth and extent; coastal hazard |
| **DS-05** | Flood Depth | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Riverine and flash flood depth projections; hydrology-based |
| **DS-06** | DEM / Slope | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Digital elevation model (30m) and derived slope; affects drainage and stability |
| **DS-07** | Soil Type & Stability | Pre-Assessment | Yes | Shapefile, GeoPackage, CSV with geometry | Soil classification (FAO), bearing capacity, erosion risk; agriculture-critical |
| **DS-08** | Land Cover / LULC | Pre-Assessment | Yes | GeoTIFF, Shapefile, GeoPackage | Land use / land cover classification; existing use and conversion potential |
| **DS-09** | Ecosystem Biodiversity Index | Optional | No | GeoTIFF, Shapefile, GeoPackage | Species richness, endemism, habitat value; conservation consideration |
| **DS-10** | Protected Areas Boundaries | Pre-Assessment | Yes | Shapefile, GeoPackage, KML | National parks, marine reserves, sacred sites; strict exclusion layer |
| **DS-11** | Population Density | Optional | No | GeoTIFF, Shapefile, GeoPackage | People per km²; development pressure and accessibility |
| **DS-12** | Infrastructure Distance | Optional | No | Shapefile, GeoPackage | Distance to roads, ports, hospitals, schools; development enablers |
| **DS-13** | Sea-Level Rise Projection (1m) | Optional | No | GeoTIFF, Shapefile, GeoPackage | 1m sea-level rise inundation; long-term climate risk |
| **DS-14** | Coastal/Mangrove Ecosystems | Optional | No | Shapefile, GeoPackage, KML | Mangrove and coral ecosystem boundaries; biodiversity and hazard mitigation |

**Format Notes:**
- Raster formats (GeoTIFF) must include valid GeoTIFF header, CRS, and geotransform
- Vector formats (Shapefile, GeoPackage) must include valid geometry and projection
- CSV uploads must include WKT geometry column or latitude/longitude columns
- All data must reference WGS84 (EPSG:4326); system auto-converts on ingest

---

## Quick Start (Local Development)

### Prerequisites

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Git**
- **Node.js** (v20+) for frontend build
- **Python** (v3.11+) for backend testing (optional; Docker provides runtime)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/GovVanuatu/vmhlss.git
   cd vmhlss
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set the following:
   ```env
   # Database
   POSTGRES_USER=vmhlss_user
   POSTGRES_PASSWORD=<your-secure-password>
   POSTGRES_DB=vmhlss
   DATABASE_URL=postgresql://vmhlss_user:<password>@postgres:5432/vmhlss

   # JWT & Auth
   SECRET_KEY=<generate-with: openssl rand -hex 32>
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_HOURS=24

   # API
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
   API_URL=http://localhost:8000
   VITE_API_URL=http://localhost:8000

   # AI Services (required for document intelligence and personas)
   ANTHROPIC_API_KEY=<your-anthropic-api-key>
   
   # Optional
   LOG_LEVEL=INFO
   DEBUG=true
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   Verify all services are running:
   ```bash
   docker-compose ps
   ```

4. **Wait for database to be ready**, then run migrations
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Seed reference data** (optional; populates test users and default criteria)
   ```bash
   docker-compose exec backend python -m app.seed_data
   ```

6. **Access the system**
   - **Frontend:** http://localhost:3000
   - **Backend API docs (Swagger UI):** http://localhost:8000/docs
   - **ReDoc:** http://localhost:8000/redoc
   - **pgAdmin** (if added to compose): http://localhost:5050

### Default Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@vmhlss.gov.vu | testpassword123 |
| Data Manager | uploader@vmhlss.gov.vu | testpassword123 |
| Analyst | analyst@vmhlss.gov.vu | testpassword123 |
| Reviewer | viewer@vmhlss.gov.vu | testpassword123 |
| Public | (no login) | (public endpoint) |

---

## Project Structure

```
vmhlss/
├── backend/                              # FastAPI backend application
│   ├── app/
│   │   ├── main.py                       # FastAPI app initialization & route mounting
│   │   ├── config.py                     # Environment & settings (Pydantic v2)
│   │   ├── database.py                   # SQLAlchemy session, engine, declarative base
│   │   ├── security.py                   # Password hashing, JWT token utilities
│   │   ├── models/                       # SQLAlchemy ORM models
│   │   │   ├── __init__.py               # Model exports
│   │   │   ├── user.py                   # User model with roles and permissions
│   │   │   ├── dataset.py                # Dataset metadata and versioning
│   │   │   ├── upload.py                 # Upload tracking and QA pipeline state
│   │   │   ├── qa_result.py              # QA stage results and fixes applied
│   │   │   ├── analysis.py               # Analysis run metadata and results
│   │   │   ├── audit_log.py              # Append-only immutable audit trail
│   │   │   ├── ahp_weight.py             # AHP (Analytic Hierarchy Process) weights
│   │   │   ├── vanuatu_place.py          # Place names, locations, administrative boundaries
│   │   │   └── share_link.py             # Shareable report links with expiry tokens
│   │   ├── schemas/                      # Pydantic request/response models
│   │   │   ├── user.py                   # User create, update, response schemas
│   │   │   ├── dataset.py                # Dataset metadata schemas
│   │   │   ├── analysis.py               # Analysis request and result schemas
│   │   │   ├── auth.py                   # Login, token, refresh schemas
│   │   │   └── suitability.py            # Suitability class and scoring schemas
│   │   ├── routes/                       # API endpoint groups
│   │   │   ├── auth.py                   # /api/auth/* (login, token refresh, logout)
│   │   │   ├── datasets.py               # /api/datasets/* (upload, QA, list, delete)
│   │   │   ├── analysis.py               # /api/analysis/* (run, results, export)
│   │   │   ├── documents.py              # /api/documents/* (PDF intelligence)
│   │   │   ├── knowledge_base.py         # /api/knowledge-base/* (KB confirmation)
│   │   │   ├── georeferencing.py         # /api/georef/* (map digitisation)
│   │   │   ├── reports.py                # /api/reports/* (PDF generation)
│   │   │   ├── admin.py                  # /api/admin/* (user, role, audit management)
│   │   │   ├── health.py                 # /api/health/* (liveness, readiness checks)
│   │   │   └── shares.py                 # /api/shares/* (share link generation)
│   │   ├── services/                     # Business logic layer
│   │   │   ├── __init__.py               # Service exports
│   │   │   ├── qa_engine.py              # 5-stage QA pipeline (format, readability, CRS, validity, completeness, statistics)
│   │   │   ├── criteria_engine.py        # WLC and AHP scoring, suitability classification
│   │   │   ├── format_converter.py       # Geospatial format conversion (Shapefile, GeoPackage, GeoTIFF, KML)
│   │   │   ├── auth_service.py           # JWT & session handling, token refresh
│   │   │   ├── document_service.py       # Claude API document intelligence integration
│   │   │   ├── ai_persona_service.py     # AI expert persona prompt engineering and response generation
│   │   │   ├── report_generator.py       # PDF report generation with government branding
│   │   │   ├── georeferencing_service.py # Map georeferencing and feature extraction
│   │   │   └── cache_service.py          # Redis caching for analysis results
│   │   ├── utils/                        # Utility functions
│   │   │   ├── auth.py                   # Password hashing, JWT token creation/verification
│   │   │   ├── geometry.py               # Spatial operations, geometry validation
│   │   │   ├── crs_utils.py              # CRS detection, projection transformation
│   │   │   ├── validators.py             # Pydantic validators, custom validation rules
│   │   │   ├── logger.py                 # Structured logging configuration
│   │   │   └── exceptions.py             # Custom exception classes
│   │   ├── middleware/                   # FastAPI middleware
│   │   │   ├── auth_middleware.py        # JWT token extraction and validation
│   │   │   ├── audit_middleware.py       # Request/response logging to audit_log
│   │   │   ├── cors_middleware.py        # CORS configuration from ALLOWED_ORIGINS
│   │   │   └── error_handler.py          # Global error handling and response formatting
│   │   └── tasks/                        # Celery background tasks
│   │       ├── qa_pipeline.py            # Asynchronous QA pipeline execution
│   │       └── report_generation.py      # Asynchronous PDF generation
│   ├── tests/                            # Pytest test suite
│   │   ├── conftest.py                   # Shared fixtures (DB, auth, sample data)
│   │   ├── test_qa_engine.py             # QA pipeline tests (all 5 stages)
│   │   ├── test_criteria_engine.py       # WLC and AHP scoring tests
│   │   ├── test_auth.py                  # Authentication and RBAC tests
│   │   ├── test_api_endpoints.py         # Integration tests for all endpoints
│   │   └── test_audit_log.py             # Audit trail immutability tests
│   ├── alembic/                          # Database schema migrations
│   │   ├── versions/                     # Individual migration scripts (auto-generated)
│   │   ├── env.py                        # Alembic environment configuration
│   │   └── alembic.ini                   # Alembic settings
│   ├── requirements.txt                  # Python package dependencies (pip format)
│   ├── Dockerfile                        # Backend container image definition
│   └── .dockerignore                     # Files to exclude from Docker build context
│
├── frontend/                             # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx                      # React entry point
│   │   ├── App.tsx                       # Root application component
│   │   ├── components/                   # Reusable React components
│   │   │   ├── MapViewer.tsx             # MapLibre GL JS interactive map viewer
│   │   │   ├── DatasetUpload.tsx         # File upload interface with drag-and-drop
│   │   │   ├── AnalysisPanel.tsx         # Assessment configuration and run UI
│   │   │   ├── ResultsTable.tsx          # Suitability results display and filtering
│   │   │   ├── AHPWeightEditor.tsx       # AHP weight configuration (admin only)
│   │   │   ├── ReportViewer.tsx          # PDF report viewer and download
│   │   │   └── LanguageToggle.tsx        # English/Bislama language switcher
│   │   ├── views/                        # Page-level components
│   │   │   ├── LoginView.tsx             # Authentication page
│   │   │   ├── DashboardView.tsx         # Main dashboard with quick-access panels
│   │   │   ├── AnalysisView.tsx          # Analysis interface (dataset selection, run)
│   │   │   ├── DatasetView.tsx           # Dataset management (upload, QA results, delete)
│   │   │   ├── AdminView.tsx             # Admin panel (users, audit log, weights)
│   │   │   └── ResultsView.tsx           # Suitability results with map and export
│   │   ├── stores/                       # Zustand state management
│   │   │   ├── auth.ts                   # Authentication state (user, token, permissions)
│   │   │   ├── analysis.ts               # Analysis state (results, filters, selected areas)
│   │   │   ├── datasets.ts               # Dataset state (uploads, QA progress)
│   │   │   └── ui.ts                     # UI state (theme, language, sidebar)
│   │   ├── services/                     # API client services
│   │   │   ├── api.ts                    # Base HTTP client with auth headers
│   │   │   ├── auth.ts                   # Authentication API (login, logout, token refresh)
│   │   │   ├── analysis.ts               # Analysis API (run, fetch results)
│   │   │   ├── datasets.ts               # Dataset API (upload, delete, QA status)
│   │   │   ├── reports.ts                # Report API (generate, download PDF)
│   │   │   └── admin.ts                  # Admin API (users, audit log)
│   │   ├── hooks/                        # Custom React hooks
│   │   │   ├── useAuth.ts                # Authentication state management
│   │   │   ├── useAnalysis.ts            # Analysis execution and polling
│   │   │   └── useGeometry.ts            # Geometry/map utilities
│   │   ├── locales/                      # i18n translations
│   │   │   ├── en.json                   # English translations (all UI strings)
│   │   │   └── bi.json                   # Bislama translations (Vanuatu's national language)
│   │   ├── styles/                       # Global CSS
│   │   │   ├── globals.css               # Global styles, Tailwind directives
│   │   │   ├── variables.css             # CSS custom properties (colors, spacing)
│   │   │   └── typography.css            # Font definitions and styles
│   │   ├── utils/                        # Utility functions
│   │   │   ├── format.ts                 # Number, date, and string formatting
│   │   │   ├── geometry.ts               # Geometry calculations and projections
│   │   │   └── validators.ts             # Form and input validation
│   │   └── types/                        # TypeScript type definitions
│   │       ├── api.ts                    # API request/response types
│   │       ├── analysis.ts               # Analysis and suitability types
│   │       └── user.ts                   # User and permission types
│   ├── public/                           # Static assets
│   │   ├── logo.svg                      # Government of Vanuatu logo
│   │   ├── favicon.ico                   # Browser favicon
│   │   └── locales/                      # Static locale files (if not bundled)
│   ├── vite.config.ts                    # Vite build and dev server configuration
│   ├── tsconfig.json                     # TypeScript compiler options
│   ├── tailwind.config.js                # Tailwind CSS configuration
│   ├── package.json                      # Node.js dependencies and scripts
│   ├── package-lock.json                 # Dependency lock file
│   └── Dockerfile                        # Frontend container image definition
│
├── docker-compose.yml                    # Development multi-container environment
├── docker-compose.prod.yml               # Production multi-container environment (hardened)
├── .env.example                          # Template for environment variables
├── .github/
│   └── workflows/
│       ├── ci.yml                        # CI pipeline (lint, test, build)
│       └── deploy.yml                    # CD pipeline (build, push, deploy to Render)
├── .gitignore                            # Git ignore rules
├── render.yaml                           # Render.com deployment configuration
├── pytest.ini                            # Pytest configuration and test discovery
├── LICENSE                               # Open source or proprietary license
└── README.md                             # This file
```

---

## Environment Variables

All variables can be set in `.env` file or container environment:

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `POSTGRES_USER` | String | Yes | — | PostgreSQL database username |
| `POSTGRES_PASSWORD` | String | Yes | — | PostgreSQL database password (min 16 chars for production) |
| `POSTGRES_DB` | String | No | vmhlss | PostgreSQL database name |
| `DATABASE_URL` | String | Yes | — | Full PostgreSQL connection string (format: `postgresql://user:password@host:port/dbname`) |
| `SECRET_KEY` | String | Yes | — | JWT signing key; generate with `openssl rand -hex 32` |
| `JWT_ALGORITHM` | String | No | HS256 | JWT algorithm (HS256 for development; RS256 for production) |
| `JWT_EXPIRATION_HOURS` | Integer | No | 24 | Access token lifetime in hours |
| `ALLOWED_ORIGINS` | String | No | http://localhost:3000 | Comma-separated CORS origins (e.g., `https://vmhlss.gov.vu,https://www.vmhlss.gov.vu`) |
| `API_URL` | String | No | http://localhost:8000 | Public backend API URL (used in error messages, docs) |
| `VITE_API_URL` | String | No | http://localhost:8000 | Frontend API URL (used during build for client requests) |
| `ANTHROPIC_API_KEY` | String | No | — | Anthropic API key for Claude (required for document intelligence and AI personas) |
| `LOG_LEVEL` | String | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DEBUG` | Boolean | No | false | Enable debug mode (detailed error messages, auto-reload) |
| `REDIS_URL` | String | No | redis://redis:6379 | Redis connection URL for caching and Celery broker |
| `CELERY_BROKER_URL` | String | No | redis://redis:6379 | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | String | No | redis://redis:6379 | Celery result backend URL |
| `MAX_UPLOAD_SIZE_MB` | Integer | No | 100 | Maximum file upload size in megabytes |
| `UPLOAD_DIR` | String | No | /app/uploads | Directory for storing uploaded files |
| `PDF_REPORT_LOGO_URL` | String | No | — | URL to government logo for PDF reports |

---

## API Documentation

The system provides a comprehensive REST API with multiple endpoint groups. Interactive documentation is available at:

- **Swagger UI (OpenAPI 3.0):** http://localhost:8000/docs
- **ReDoc (alternative documentation):** http://localhost:8000/redoc

### Authentication (`/api/auth/*`)

```
POST   /api/auth/login                    - User login, returns JWT access token
POST   /api/auth/refresh                  - Refresh expiring access token
POST   /api/auth/logout                   - Logout (invalidate token session)
GET    /api/auth/me                       - Get current user profile and permissions
POST   /api/auth/change-password          - Change password (authenticated user)
```

### Datasets (`/api/datasets/*`)

```
POST   /api/datasets/upload/{slot_code}   - Upload dataset to data slot (triggers QA pipeline)
GET    /api/datasets/{slot_code}          - Get dataset metadata and current version
GET    /api/datasets/{slot_code}/qa       - Get QA pipeline results for dataset
DELETE /api/datasets/{slot_code}          - Delete dataset and all versions (UPLOADER+ role)
GET    /api/datasets/list                 - List all datasets by slot
GET    /api/datasets/summary              - Summary of all uploaded datasets
```

### Analysis (`/api/analysis/*`)

```
POST   /api/analysis/run                  - Run suitability assessment with given parameters
GET    /api/analysis/results              - List all analysis results (paginated)
GET    /api/analysis/{analysis_id}        - Get specific analysis result with statistics
GET    /api/analysis/{analysis_id}/map    - Get GeoJSON results for map visualization
GET    /api/analysis/{analysis_id}/export - Export results as Shapefile or GeoPackage
```

### Documents (`/api/documents/*`)

```
POST   /api/documents/upload              - Upload PDF for intelligent extraction
GET    /api/documents/{doc_id}/status     - Get extraction status and results
POST   /api/documents/{doc_id}/confirm    - Confirm extracted data for knowledge base
```

### Knowledge Base (`/api/knowledge-base/*`)

```
GET    /api/knowledge-base/entries        - List confirmed knowledge base entries
POST   /api/knowledge-base/entries        - Add new entry (admin or data manager)
DELETE /api/knowledge-base/{entry_id}     - Delete knowledge base entry (admin)
```

### Georeferencing (`/api/georef/*`)

```
POST   /api/georef/upload                 - Upload scanned map for georeferencing
POST   /api/georef/{doc_id}/reference     - Define reference points (GCPs)
POST   /api/georef/{doc_id}/digitize      - Extract features from map
GET    /api/georef/{doc_id}/result        - Get georeferenced and digitized output
```

### Reports (`/api/reports/*`)

```
POST   /api/reports/generate              - Generate PDF report for analysis
GET    /api/reports/{report_id}           - Download generated PDF report
POST   /api/reports/{analysis_id}/email   - Email report to recipients
```

### Admin (`/api/admin/*`)

```
GET    /api/admin/users                   - List all users with roles (ADMIN role)
POST   /api/admin/users                   - Create new user (ADMIN role)
PUT    /api/admin/users/{user_id}         - Update user profile or role (ADMIN role)
DELETE /api/admin/users/{user_id}         - Delete user account (ADMIN role)
GET    /api/admin/audit-log               - View immutable audit trail (ADMIN role)
PUT    /api/admin/ahp-weights             - Update AHP weighting matrix (ADMIN role)
GET    /api/admin/health                  - System health and dependency status
```

### Health (`/api/health/*`)

```
GET    /api/health                        - Liveness probe (system running)
GET    /api/health/ready                  - Readiness probe (dependencies available)
GET    /api/health/db                     - Database connectivity check
GET    /api/health/redis                  - Redis/cache connectivity check
GET    /api/health/storage                - File storage accessibility check
```

### Share Links (`/api/shares/*`)

```
POST   /api/shares/create                 - Create shareable link for report (30-day expiry)
GET    /api/shares/{share_token}          - Access shared report (no auth required)
DELETE /api/shares/{share_token}          - Revoke shared link early (owner only)
```

---

## User Roles & Permissions

The system implements five role-based access levels with granular permissions:

| Role | Permissions | Typical User | API Access |
|------|-------------|--------------|-----------|
| **ADMIN** | Create/delete users; modify system weights; view audit logs; configure AI personas | Ministry Director, System Administrator | All endpoints |
| **DATA_MANAGER** | Upload datasets; trigger QA pipeline; view QA results; confirm knowledge base entries; delete own uploads | Data Technician, GIS Technician | Upload, QA, KB confirm, report view |
| **ANALYST** | Run analyses on uploaded datasets; export results; generate reports; create share links | Spatial Planner, Environmental Analyst | Analysis run, results export, report generate |
| **REVIEWER** | View-only access to results, reports, and audit history; download reports; create share links | Stakeholder, Public Official | Results view, report download |
| **PUBLIC** | Public-facing analyses (rate-limited); no persistent login; download own reports | Community members, external stakeholders | Analysis run (limited), report download |

**Permission Matrix:**

| Action | ADMIN | DATA_MANAGER | ANALYST | REVIEWER | PUBLIC |
|--------|-------|--------------|---------|----------|--------|
| Create/manage users | ✓ | — | — | — | — |
| Upload datasets | ✓ | ✓ | — | — | — |
| View QA results | ✓ | ✓ | ✓ | ✓ | — |
| Delete datasets | ✓ | ✓ (own) | — | — | — |
| Run analysis | ✓ | ✓ | ✓ | — | ✓ (rate-limited) |
| Export results | ✓ | ✓ | ✓ | ✓ | ✓ |
| Generate reports | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create share links | ✓ | ✓ | ✓ | ✓ | ✓ (own only) |
| View audit log | ✓ | — | — | — | — |
| Modify AHP weights | ✓ | — | — | — | — |
| Manage system settings | ✓ | — | — | — | — |

---

## Deployment Guide (GitHub Actions + Render)

### Automatic Deployment with GitHub Actions

#### 1. Prerequisites

- GitHub repository (public or private)
- Render.com account with API key
- Anthropic API key for Claude API access

#### 2. Add GitHub Secrets

Navigate to **Settings > Secrets and variables > Actions** and add:

| Secret | Value | Description |
|--------|-------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required for document intelligence and AI personas |
| `RENDER_API_KEY` | Your Render.com API key | Authenticate with Render deployment API |
| `RENDER_SERVICE_ID` | Backend service ID from Render dashboard | Identifies which service to deploy to |
| `POSTGRES_PASSWORD` | Secure database password (min 16 chars) | Used during CI/CD database setup |
| `VITE_API_URL` | https://vmhlss-api.onrender.com | Frontend API URL for build-time configuration |

#### 3. GitHub Actions Workflow

The system includes two workflows in `.github/workflows/`:

**`ci.yml` — Continuous Integration**
- Triggers on: push to any branch, pull requests
- Steps:
  1. Run `pytest tests/ -v` (backend unit tests)
  2. Run `npm run lint` (frontend code linting)
  3. Run `npm run build` (frontend production build)
- Fails if any step fails; blocks merge to main

**`deploy.yml` — Continuous Deployment**
- Triggers on: push to main branch AND ci.yml passes
- Steps:
  1. Build backend Docker image
  2. Push to Render container registry
  3. Deploy to Render Web Service (auto-scales)
  4. Run database migrations on deployed instance
  5. Health check to verify deployment
- Only runs if CI passes

#### 4. First-Time Render Setup

1. **Create Render Web Services:**
   - Backend: https://render.com/docs/deploy-service
     - Build Command: `pip install -r backend/requirements.txt`
     - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8080`
   - Database: PostgreSQL 15 instance (managed Postgres)
   - Disk: 50 GB for uploads (`/app/uploads`)

2. **Connect GitHub Repository:**
   - Link Render service to GitHub repository
   - Set auto-deploy on push to main

3. **Populate GitHub Secrets** (see step 2 above)

4. **Push to main:**
   ```bash
   git add .
   git commit -m "Initial deployment setup"
   git push origin main
   ```
   GitHub Actions triggers automatically; monitor at **Actions** tab.

#### 5. Deployment Targets

- **Backend:** Render Web Service (auto-scales based on traffic)
- **Frontend:** Render Static Site OR GitHub Pages (static assets only)
- **Database:** Render PostgreSQL (managed, auto-backups) OR government server

#### 6. Monitor Deployments

- GitHub Actions: https://github.com/GovVanuatu/vmhlss/actions
- Render Dashboard: https://dashboard.render.com
- Logs: `docker-compose logs backend` (local); Render dashboard (deployed)

### Manual Render Deployment

**Step-by-step for first-time Render setup without CI/CD:**

1. **Create Render account** (https://render.com)

2. **Create PostgreSQL database:**
   - Service Type: PostgreSQL
   - Region: Closest to Vanuatu (Singapore or Australia)
   - Plan: Standard (production) or Starter (development)
   - Note database credentials

3. **Create Web Service for backend:**
   - Connect GitHub repository
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8080`
   - Environment Variables:
     ```
     DATABASE_URL=postgresql://...
     SECRET_KEY=<generate: openssl rand -hex 32>
     ANTHROPIC_API_KEY=<your-api-key>
     ALLOWED_ORIGINS=https://vmhlss.gov.vu
     API_URL=https://vmhlss-api.onrender.com
     ```

4. **Deploy:**
   - Push to main branch
   - Render auto-deploys on push
   - Verify at service URL

### GitHub Secrets Required

| Secret | Purpose | Example |
|--------|---------|---------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key for document intelligence and AI persona generation | `sk-ant-...` |
| `RENDER_API_KEY` | API key for Render authentication | From Render dashboard → Account → API Keys |
| `RENDER_SERVICE_ID` | Unique ID of backend Web Service | Found in Render dashboard → Service → Settings |
| `POSTGRES_PASSWORD` | PostgreSQL password (for CI/CD and production) | Min 16 characters, no special shell chars |
| `VITE_API_URL` | Frontend build-time API URL | `https://vmhlss-api.onrender.com` |

---

## Migration to Government Server

Complete guide for hosting VMHLSS on government infrastructure:

### Prerequisites

- Linux server (Ubuntu 22.04 LTS recommended) with sudo access
- Docker and Docker Compose installed
- Domain name (DNS configured to server IP)
- SSL/TLS certificates (Let's Encrypt or self-signed)
- Minimum: 4 CPU cores, 8 GB RAM, 50 GB storage

### Step 1: Clone Repository

```bash
sudo mkdir -p /opt/vmhlss
cd /opt/vmhlss
sudo git clone https://github.com/GovVanuatu/vmhlss.git .
```

### Step 2: Use Production Docker Compose

```bash
sudo cp docker-compose.prod.yml docker-compose.yml
```

### Step 3: Configure Production Environment

```bash
sudo cp .env.example .env
sudo nano .env
```

Update for production (replace placeholders):

```env
# Database
POSTGRES_USER=vmhlss_prod
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=vmhlss_prod
DATABASE_URL=postgresql://vmhlss_prod:<password>@postgres:5432/vmhlss_prod

# API Configuration
ALLOWED_ORIGINS=https://vmhlss.gov.vu,https://www.vmhlss.gov.vu
API_URL=https://vmhlss.gov.vu
VITE_API_URL=https://vmhlss.gov.vu

# Security
SECRET_KEY=<generate: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# AI Services
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# Production Settings
DEBUG=false
LOG_LEVEL=WARNING
ENVIRONMENT=production
```

### Step 4: Start Services

```bash
sudo docker-compose up -d
```

Verify all services running:

```bash
sudo docker-compose ps
```

Expected output:
```
NAME        STATUS
postgres    Up (healthy)
backend     Up (healthy)
frontend    Up (healthy)
redis       Up (healthy)
```

### Step 5: Run Migrations

```bash
sudo docker-compose exec backend alembic upgrade head
sudo docker-compose exec backend python -m app.seed_data
```

This initializes the database schema and loads default users/data.

### Step 6: Configure DNS

Point domain to server IP in DNS records:

```
vmhlss.gov.vu             A     <server-public-ip>
www.vmhlss.gov.vu        CNAME vmhlss.gov.vu
vmhlss-api.gov.vu        A     <server-public-ip>  (optional, for API subdomain)
```

Wait for DNS propagation (5-30 minutes).

### Step 7: Configure Reverse Proxy (Nginx)

Install Nginx:

```bash
sudo apt update && sudo apt install nginx -y
```

Create Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/vmhlss
```

Paste configuration:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name vmhlss.gov.vu www.vmhlss.gov.vu vmhlss-api.gov.vu;
    return 301 https://$server_name$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name vmhlss.gov.vu www.vmhlss.gov.vu;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/vmhlss.gov.vu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vmhlss.gov.vu/privkey.pem;

    # SSL hardening
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client upload size limit
    client_max_body_size 100M;

    # Frontend (React app)
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Swagger UI
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
    }

    # ReDoc
    location /redoc {
        proxy_pass http://localhost:8000/redoc;
        proxy_set_header Host $host;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/vmhlss /etc/nginx/sites-enabled/
```

Test Nginx configuration:

```bash
sudo nginx -t
```

Reload Nginx:

```bash
sudo systemctl reload nginx
```

### Step 8: Set Up SSL Certificates (Let's Encrypt)

Install Certbot:

```bash
sudo apt install certbot python3-certbot-nginx -y
```

Obtain certificate:

```bash
sudo certbot certonly --webroot -w /var/www/html -d vmhlss.gov.vu -d www.vmhlss.gov.vu
```

Set auto-renewal:

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Step 9: Verify Deployment

```bash
# Check system status
sudo docker-compose ps

# View logs
sudo docker-compose logs -f backend

# Test API
curl https://vmhlss.gov.vu/api/health

# Visit in browser
# https://vmhlss.gov.vu
```

### No Code Changes Required

The same Docker images and environment variables work across all environments (local, Render, government server). No code modifications necessary for government deployment.

### Troubleshooting Government Server Deployment

**Services not starting:**
```bash
sudo docker-compose down
sudo docker-compose up -d
sudo docker-compose logs backend  # Check error messages
```

**Database connection error:**
```bash
sudo docker-compose exec postgres psql -U vmhlss_prod -d vmhlss_prod -c "SELECT 1"
```

**Nginx not proxying correctly:**
```bash
sudo nginx -t
sudo systemctl reload nginx
curl -vvv http://localhost:8000/api/health  # Test backend directly
```

**SSL certificate issues:**
```bash
sudo certbot renew --dry-run
sudo certbot renew
```

---

## Testing

### Run All Tests

```bash
# From project root
docker-compose exec backend pytest tests/ -v
```

### Run Specific Test File

```bash
docker-compose exec backend pytest tests/test_qa_engine.py -v
```

### Run Specific Test Class

```bash
docker-compose exec backend pytest tests/test_qa_engine.py::TestStage1FormatReadability -v
```

### Run with Coverage Report

```bash
docker-compose exec backend pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser to view detailed coverage
```

### Test Categories

**Unit Tests:**
- QA pipeline stages (format, readability, CRS, validity, completeness, statistics)
- Criteria engine WLC/AHP scoring
- JWT token generation and validation
- Password hashing and verification

**Integration Tests:**
- API endpoint authentication and authorization
- Database transactions and rollback
- File upload and processing
- Report generation

**System Tests:**
- End-to-end analysis workflow
- Multi-dataset analysis
- Audit log immutability

### Test Database

Tests use isolated PostgreSQL database (created fresh for each test run). No test data affects production.

### CI/CD Testing

GitHub Actions runs full test suite on every push:
```bash
pytest tests/ -v --tb=short
```

Deployment only proceeds if all tests pass.

### Test Coverage Targets

Minimum 80% code coverage required for main branch:
- QA engine: 90%+
- Criteria engine: 90%+
- Auth service: 85%+
- API endpoints: 75%+

---

## Bislama Language Support

The system provides full bilingual support for English and Bislama (Vanuatu's national creole language).

### Language Toggle

Users can switch between English (EN) and Bislama (BI) via a toggle button in the top navigation bar. The choice is persisted in browser localStorage and applies globally across the interface.

### Translation Files

Translation files are located in `frontend/src/locales/`:

- **`en.json`** — English UI strings (primary language)
- **`bi.json`** — Bislama translations

### Key Bislama Translations

| English | Bislama |
|---------|---------|
| "Dashboard" | "Blong Dashboard" |
| "Upload Data" | "Aploadim Data" |
| "Run Analysis" | "Ronit Analysis" |
| "Good to farm" | "Ples ya i gud blong planem" |
| "Not suitable" | "No i gud" |
| "Results" | "Ol Resultem" |

### AI Persona Language Support

The **Farmer** AI persona generates recommendations in both English and Bislama automatically, based on the user's language preference.

### Adding New Translations

1. Add new key-value pair to both JSON files:
   ```json
   // en.json
   {
     "new.feature": "New Feature Label"
   }

   // bi.json
   {
     "new.feature": "Ol Nao Wan Famoa Lanem"
   }
   ```

2. Use in Vue/React component:
   ```tsx
   // React
   <h1>{t('new.feature')}</h1>
   
   // Vue
   <h1>{{ $t('new.feature') }}</h1>
   ```

3. Strings automatically update when language toggled.

### Translation Guidelines

- Keep translations concise and clear
- Maintain consistent terminology across both languages
- Test in both languages for UI layout (Bislama may be longer)
- Use native speaker review for accuracy

---

## Architecture Notes

### Core Design Principles

1. **Separation of Concerns**
   - All spatial queries go through the FastAPI service layer — raw database queries are never exposed to the frontend
   - Business logic (QA, criteria scoring) is isolated in services
   - API layer is thin and stateless

2. **Data Immutability & Audit**
   - The `audit_log` table is append-only (enforced by PostgreSQL trigger)
   - No UPDATE or DELETE permitted on audit records
   - Every user action generates an immutable log entry with timestamp, user ID, action, and result

3. **API Key Security**
   - The Anthropic API key is **never exposed to the frontend**
   - All Claude API calls happen server-side in dedicated services
   - Environment variables are injected at container startup, not bundled

4. **Asynchronous Processing**
   - QA pipeline runs asynchronously via Celery
   - Upload endpoint returns immediately with `job_id` for client polling
   - Long-running operations (PDF generation, document analysis) are non-blocking

5. **Geospatial Data Storage**
   - Suitability results are stored as PostGIS geometries (POLYGON, MULTIPOLYGON)
   - Geometries are indexed for fast spatial queries
   - Results are exportable as Shapefile, GeoPackage, or GeoJSON

6. **Share Links & Public Access**
   - Share links use 30-day expiry tokens (JWT-based)
   - Public users can access shared reports without authentication
   - Each share generates a unique, revocable token

### Database Schema Highlights

**PostGIS Extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
```

**Key Tables:**
- `users` — user accounts with roles and permissions
- `datasets` — dataset metadata and versioning
- `uploads` — upload tracking and QA pipeline state
- `qa_results` — QA stage results (format, readability, CRS, validity, completeness)
- `analysis_runs` — analysis execution metadata
- `analysis_results` — suitability classifications and scores (PostGIS geometries)
- `audit_log` — immutable append-only transaction log
- `ahp_weights` — Analytic Hierarchy Process weighting matrix
- `vanuatu_places` — place names and administrative boundaries

### Performance Optimizations

- Spatial indexing on geometries (GIST, BRIN)
- Result caching via Redis for repeated analyses
- Pagination on large result sets
- Database connection pooling
- Frontend map tile caching

### Error Handling

- Custom exception classes for domain-specific errors
- Structured logging with correlation IDs for request tracing
- User-friendly error messages (no stack traces in API responses)
- Graceful degradation when optional services unavailable (Redis, Anthropic API)

---

## Licence

**© 2026 Government of Vanuatu. All rights reserved.**

This system is owned and operated by the Government of Vanuatu. Unauthorized reproduction, distribution, or modification is prohibited.

The system is developed for the Vanuatu Department of Strategic Policy, Planning and Aid Coordination and the Vanuatu Disaster Management Office.

For licensing inquiries, contact: **dlo@vanuatu.gov.vu**

---

**Last Updated:** 2026-04-18  
**Architecture Reference:** VMHLSS / GoV / SYS-ARCH / 2026-001 v1.3
