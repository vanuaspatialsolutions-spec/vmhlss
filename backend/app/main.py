from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
import time

from app.config import settings
from app.database import init_db
from app.middleware.audit_middleware import AuditMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """
    # Startup
    logger.info("Starting VMHLSS API")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down VMHLSS API")


# Create FastAPI app
app = FastAPI(
    title="VMHLSS API",
    description="Vanuatu Multi-Hazard Land Suitability System API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add audit middleware
app.add_middleware(AuditMiddleware)


# Add rate limiting middleware for public endpoints
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for public endpoints.
    Uses in-memory storage (should be replaced with Redis in production).
    """

    def __init__(self, app: FastAPI, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip_address: [(timestamp, count)]}

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get current timestamp
        current_time = time.time()

        # Initialize tracking for IP if needed
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Remove requests older than 1 minute
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]

        # Check rate limit (only for public endpoints)
        if request.url.path.startswith("/api/public/") or request.url.path == "/health":
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"}
                )

        # Record this request
        self.requests[client_ip].append(current_time)

        # Process request
        response = await call_next(request)
        return response


app.add_middleware(RateLimitMiddleware)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """
    Health check endpoint to verify API is running.

    Returns:
        Dictionary with status and version information
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.environment
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root() -> dict:
    """
    Root endpoint providing API information.

    Returns:
        Dictionary with API information
    """
    return {
        "name": "VMHLSS API",
        "version": "1.0.0",
        "description": "Vanuatu Multi-Hazard Land Suitability System API",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }


# TODO: Include routers with /api prefix
# Example router includes (to be implemented):
# from app.routers import auth, users, datasets, uploads, analysis, reports
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(users.router, prefix="/api/users", tags=["Users"])
# app.include_router(datasets.router, prefix="/api/datasets", tags=["Datasets"])
# app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
# app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
# app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions"""
    logger.error(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
