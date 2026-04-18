from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from typing import Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to audit all API requests for compliance and security.
    Logs request details to audit_log table asynchronously.
    """

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        "/health",
        "/openapi.json",
        "/docs",
        "/redoc",
        "/favicon.ico"
    }

    # Paths to exclude for static files
    EXCLUDED_PREFIXES = {
        "/static/",
        "/.well-known/"
    }

    async def dispatch(self, request: Request, call_next):
        """
        Process request and log to audit trail.

        Args:
            request: FastAPI/Starlette request object
            call_next: Next middleware/handler

        Returns:
            Response from next handler
        """
        # Check if path should be excluded from logging
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # Extract audit information from request
        audit_data = await self._extract_audit_data(request)

        # Process the request
        response = await call_next(request)

        # Log audit information asynchronously
        await self._log_audit(audit_data, response.status_code)

        return response

    def _should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from audit logging.

        Args:
            path: Request path

        Returns:
            True if path should be excluded, False otherwise
        """
        if path in self.EXCLUDED_PATHS:
            return True

        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    async def _extract_audit_data(self, request: Request) -> dict:
        """
        Extract relevant audit information from request.

        Args:
            request: FastAPI/Starlette request object

        Returns:
            Dictionary containing audit data
        """
        # Get user info from JWT if available
        user_id: Optional[str] = None
        user_email: Optional[str] = None
        user_role: Optional[str] = None

        try:
            # Try to extract from authorization header
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from jose import jwt
                from app.config import settings

                token = auth_header[7:]  # Remove "Bearer " prefix
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm]
                )
                user_id = payload.get("sub")
                user_email = payload.get("email")
                user_role = payload.get("role")
        except Exception as e:
            logger.debug(f"Could not extract user info from token: {e}")

        # Get client IP address
        client_ip = self._get_client_ip(request)

        # Derive action type and resource from request
        action_type = self._derive_action_type(request.method, request.url.path)
        resource_type = self._derive_resource_type(request.url.path)
        resource_id = self._extract_resource_id(request.url.path)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "method": request.method,
            "path": request.url.path,
            "ip_address": client_ip,
            "query_params": dict(request.query_params) if request.query_params else {}
        }

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        Checks X-Forwarded-For header first (for proxied requests).

        Args:
            request: FastAPI/Starlette request object

        Returns:
            Client IP address
        """
        # Check for X-Forwarded-For header (proxy)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Return first IP if multiple are present
            return x_forwarded_for.split(",")[0].strip()

        # Fall back to direct client connection
        if request.client:
            return request.client.host

        return "unknown"

    def _derive_action_type(self, method: str, path: str) -> str:
        """
        Derive action type from HTTP method and path.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: Request path

        Returns:
            Action type string
        """
        method_map = {
            "GET": "READ",
            "POST": "CREATE",
            "PUT": "UPDATE",
            "PATCH": "UPDATE",
            "DELETE": "DELETE"
        }

        return method_map.get(method, method)

    def _derive_resource_type(self, path: str) -> str:
        """
        Derive resource type from request path.

        Args:
            path: Request path

        Returns:
            Resource type string
        """
        # Remove leading /api/
        if path.startswith("/api/"):
            path = path[5:]

        # Extract first segment
        segments = path.split("/")
        if segments:
            resource = segments[0]
            # Singularize common plural forms
            if resource.endswith("s"):
                return resource[:-1]
            return resource

        return "unknown"

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """
        Extract resource ID from request path.
        Assumes standard RESTful pattern: /api/resource/{id}

        Args:
            path: Request path

        Returns:
            Resource ID if found, None otherwise
        """
        segments = path.split("/")

        # Look for UUID or numeric ID pattern
        for i, segment in enumerate(segments):
            # Check if segment looks like an ID (UUID or number)
            if (
                len(segment) == 36 and segment.count("-") == 4  # UUID pattern
                or segment.isdigit()
            ):
                return segment

        return None

    async def _log_audit(self, audit_data: dict, status_code: int) -> None:
        """
        Log audit information to database.
        Uses background task to avoid blocking request.

        Args:
            audit_data: Dictionary containing audit information
            status_code: HTTP response status code
        """
        try:
            # Add response status
            audit_data["status_code"] = status_code

            # Log to standard logger
            logger.info(f"AUDIT: {json.dumps(audit_data)}")

            # TODO: In production, this should be written to database
            # Example:
            # from app.database import SessionLocal
            # from app.models import AuditLog
            #
            # db = SessionLocal()
            # try:
            #     audit_log = AuditLog(**audit_data)
            #     db.add(audit_log)
            #     db.commit()
            # finally:
            #     db.close()

        except Exception as e:
            logger.error(f"Error logging audit trail: {e}")
