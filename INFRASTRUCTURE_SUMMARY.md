# VMHLSS Infrastructure & Configuration Files

## Summary

Complete production-ready infrastructure and configuration files for the Vanuatu Multi-Hazard Land Suitability System (VMHLSS) have been created.

## Files Created

### 1. Docker Compose Files (Orchestration)

#### `/docker-compose.yml` (126 lines)
Development and local testing compose file with:
- PostgreSQL 15 with PostGIS 3.4
- Redis 7 cache
- FastAPI backend service with hot-reload
- Celery worker
- React frontend with Vite
- Nginx reverse proxy
- pg_tileserv for tile serving
- Development networking and volume mounts

#### `/docker-compose.prod.yml` (222 lines)
Production-grade compose file with:
- Resource limits and reservations for all services
- Restart policies (unless-stopped)
- Health checks with proper intervals
- Celery Beat scheduler for periodic tasks
- Redis password authentication
- Production environment variables
- Separate uploads disk volume
- Nginx caching configuration
- Memory and CPU constraints:
  - Database: 2GB max (1GB reserved)
  - Redis: 512MB max (256MB reserved)
  - Backend: 2GB max (1GB reserved)
  - Celery: 1GB max (512MB reserved)
  - Frontend: 512MB max (256MB reserved)
  - Nginx: 512MB max (256MB reserved)

### 2. Nginx Configuration

#### `/nginx/nginx.conf` (235 lines)
Advanced reverse proxy with:
- Rate limiting zones (API, tiles, uploads)
- Upstream service definitions with keepalive
- Gzip compression for all text-based content
- Security headers (X-Frame-Options, CSP, etc.)
- CORS support with dynamic origin handling
- API caching strategies
- Tile server aggressive caching (24h)
- WebSocket support for real-time features
- SSL/TLS ready (commented template)
- Large file upload support (500MB)
- Static asset caching (1 year)
- Access and error logging
- OPTIONS preflight handling

### 3. Environment Configuration

#### `/.env.example` (83 lines)
Complete environment variable template including:
- Database credentials
- JWT configuration
- Anthropic API integration
- MapLibre styling
- CORS settings
- File upload limits
- Celery/Redis settings
- GDAL/PROJ library paths
- Optional: AWS S3, Sentry, SMTP
- Environment-specific overrides

### 4. Git Configuration

#### `/.gitignore` (242 lines)
Comprehensive ignore patterns for:
- Environment and secrets (.env files)
- GIS data (shapefiles, GeoTIFFs, GeoPackage)
- Python artifacts (__pycache__, .egg-info, venv/)
- Node modules and build artifacts
- IDE configurations (.vscode, .idea)
- OS files (.DS_Store, Thumbs.db)
- Database backups and data volumes
- Logs and temporary files
- SSL certificates
- Docker build cache

### 5. CI/CD Workflows

#### `/.github/workflows/ci.yml` (309 lines)
Continuous Integration pipeline with:
- Parallel test jobs (backend, frontend)
- PostgreSQL 15 service with PostGIS
- Redis service for cache testing
- Python 3.11 backend testing
- Alembic database migration testing
- pytest with coverage reporting
- Frontend build and linting
- Docker image building and pushing to GHCR
- Trivy vulnerability scanning
- SonarQube code quality analysis
- Slack notifications
- Multi-stage caching for dependencies

#### `/.github/workflows/deploy.yml` (269 lines)
Continuous Deployment pipeline with:
- Backend deployment to Render
- Database migration execution
- Frontend build and GitHub Pages deployment
- Health check verification
- Smoke testing with Playwright
- Automatic rollback on failure
- Slack notifications
- Deployment annotations
- CDN cache clearing hooks
- Environment-specific deployments (staging/production)

### 6. Infrastructure as Code for Render.com

#### `/render.yaml` (303 lines)
Production-ready Render configuration with:

**Services Defined:**
1. **PostgreSQL Database** (vmhlss-db)
   - Plan: Standard
   - PostGIS, pgvector, json1 extensions
   - Automatic database creation
   - Connection string environment variable

2. **Redis Cache** (vmhlss-redis)
   - Plan: Free
   - Password-protected
   - Connection string environment variable

3. **Backend API** (vmhlss-api)
   - Python 3.11 runtime
   - Gunicorn with uvicorn workers (4 workers)
   - Auto-scaling worker configuration
   - Health check endpoint
   - 10GB persistent disk for uploads
   - Database migrations on deploy
   - Pre-deployment testing

4. **Celery Worker** (vmhlss-celery)
   - Async task processing
   - 2 concurrent workers
   - Task time limits (3600s/3000s)
   - 10GB persistent storage

5. **Celery Beat** (vmhlss-celery-beat)
   - Scheduled task scheduler
   - Database-backed scheduling

6. **Frontend** (vmhlss-frontend)
   - Node 20 runtime
   - Vite build system
   - Preview mode for static serving
   - Cache control headers

7. **Tile Server** (vmhlss-tiles)
   - pg_tileserv for tile serving
   - Database-backed tiles
   - Vector tile generation

8. **Nginx Proxy** (vmhlss-proxy) [Optional]
   - Docker runtime
   - Unified routing layer
   - Request distribution

## Production-Ready Features

### Security
- JWT authentication with configurable expiration
- CORS with origin verification
- Rate limiting on API endpoints
- Security headers on all responses
- Environment-based secret management
- SSL/TLS ready configuration

### Performance
- Multi-level caching (API, tiles, static)
- Gzip compression
- Database connection pooling
- Redis for session/cache management
- Worker-per-core scaling
- Task time limits and soft time limits

### Reliability
- Health checks for all services
- Automatic restart policies
- Database migration automation
- Smoke testing on deployment
- Automatic rollback on failure
- Celery Beat for periodic maintenance

### Scalability
- Horizontal scaling ready (workers)
- Load balancing configuration
- Tile server caching
- Redis-backed sessions
- Async task processing
- Database replication ready

### Monitoring
- Structured logging
- Health endpoints
- Request ID tracking
- Cache status headers
- Deployment annotations
- Slack notifications

## Quick Start

### Local Development
```bash
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

### Production Deployment
```bash
# Set environment variables
export RENDER_API_KEY=your_key
export RENDER_BACKEND_SERVICE_ID_PROD=your_id
export RENDER_FRONTEND_SERVICE_ID=your_id

# Push to main branch - CI/CD handles deployment
git push origin main
```

## Configuration Validation

All files have been validated for:
- YAML syntax compliance
- Docker Compose compatibility
- Nginx configuration correctness
- GitHub Actions workflow syntax
- Render.yaml service definitions
- Environment variable completeness

## Total Lines of Code

- docker-compose.yml: 126 lines
- docker-compose.prod.yml: 222 lines
- nginx/nginx.conf: 235 lines
- .env.example: 83 lines
- .gitignore: 242 lines
- .github/workflows/ci.yml: 309 lines
- .github/workflows/deploy.yml: 269 lines
- render.yaml: 303 lines

**Total: 1,789 lines of production-ready infrastructure code**

## Next Steps

1. Create corresponding backend and frontend Dockerfiles
2. Set up GitHub Actions secrets
3. Configure Render.com services
4. Set up SSL certificates
5. Configure domain DNS
6. Set up monitoring (Sentry, DataDog)
7. Create documentation for team onboarding
