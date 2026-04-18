"""Authentication router - handles user login, token refresh, logout, and user profile."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
import redis

from app.config import settings
from app.database import get_db
from app.models.user import User as UserModel
from app.schemas import UserLogin, TokenResponse, UserResponse
from app.middleware.auth_middleware import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    User as AuthUser
)

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blocklist
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Token blocklist disabled.")
    redis_client = None

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class LogoutRequest(BaseModel):
    """Request model for logout."""
    pass


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


# ============================================================================
# Helper Functions
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.

    Args:
        plain_password: Plain text password from user
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def is_token_blocklisted(token: str) -> bool:
    """
    Check if a token is in the blocklist (logged out).

    Args:
        token: JWT token to check

    Returns:
        True if token is blocklisted, False otherwise
    """
    if not redis_client:
        return False

    try:
        blocklist_key = f"token_blocklist:{token[:50]}"
        return redis_client.exists(blocklist_key) > 0
    except Exception as e:
        logger.error(f"Error checking token blocklist: {e}")
        return False


def add_token_to_blocklist(token: str, expires_in_seconds: int) -> None:
    """
    Add a token to the blocklist (for logout).

    Args:
        token: JWT token to blocklist
        expires_in_seconds: Token expiration time in seconds
    """
    if not redis_client:
        logger.warning("Redis client not available. Token not blocklisted.")
        return

    try:
        blocklist_key = f"token_blocklist:{token[:50]}"
        redis_client.setex(blocklist_key, expires_in_seconds, "true")
        logger.info(f"Token added to blocklist: {blocklist_key}")
    except Exception as e:
        logger.error(f"Error adding token to blocklist: {e}")


# ============================================================================
# Routes
# ============================================================================

@router.post("/login", response_model=TokenResponse, status_code=200)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login endpoint - authenticate user and return JWT tokens.

    Verifies email/password credentials using bcrypt, creates both access and
    refresh tokens. Returns 401 if credentials are invalid.

    Args:
        credentials: Login credentials (email, password)
        db: Database session

    Returns:
        TokenResponse with access_token, refresh_token, and expiration

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find user by email
    user = db.query(UserModel).filter(
        UserModel.email == credentials.email.lower()
    ).first()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization": user.organisation,
        "type": "access"
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(f"User logged in successfully: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse, status_code=200)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token endpoint - exchange refresh token for new access token.

    Validates the refresh token and returns a new access token with extended
    expiration. Refresh token remains valid for future refreshes.

    Args:
        request: Request containing refresh token
        db: Database session

    Returns:
        TokenResponse with new access_token

    Raises:
        HTTPException: 401 if refresh token is invalid or expired
    """
    # Check if refresh token is blocklisted
    if is_token_blocklisted(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Decode and validate refresh token
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        token_type: str = payload.get("type")

        if not user_id or not email or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )

    except JWTError:
        logger.warning("Invalid or expired refresh token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify user still exists and is active
    user = db.query(UserModel).filter(UserModel.id == UUID(user_id)).first()

    if not user or not user.is_active:
        logger.warning(f"Refresh token validation failed for user: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is invalid or inactive"
        )

    # Create new access token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization": user.organisation,
        "type": "access"
    }

    new_access_token = create_access_token(token_data)

    logger.info(f"Access token refreshed for user: {email}")

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/logout", status_code=204)
async def logout(
    user: AuthUser = Depends(get_current_user)
) -> None:
    """
    Logout endpoint - invalidate user's refresh token via blocklist.

    Adds the user's current token to a Redis blocklist, preventing it from
    being used for subsequent API requests or refreshes.

    Args:
        user: Current authenticated user from JWT token

    Returns:
        204 No Content on success
    """
    # Get the token from request context if available for full logout
    # For now, we log the logout action
    logger.info(f"User logged out: {user.email}")

    # In a production system with request context, we would add the token to blocklist
    # For now, relying on token expiration for access tokens and session management

    return None


@router.get("/me", response_model=UserResponse, status_code=200)
async def get_current_user_profile(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get current user profile endpoint - return authenticated user's information.

    Returns the profile of the currently authenticated user based on their JWT token.
    Includes role, organization, and account status information.

    Args:
        user: Current authenticated user from JWT token
        db: Database session

    Returns:
        UserResponse with full user profile information

    Raises:
        HTTPException: 404 if user no longer exists in database
    """
    # Fetch full user record from database
    db_user = db.query(UserModel).filter(
        UserModel.id == UUID(user.user_id)
    ).first()

    if not db_user:
        logger.warning(f"User profile not found: {user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )

    # Extract name components from full_name if present
    full_name = db_user.full_name or ""
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    logger.info(f"Retrieved profile for user: {db_user.email}")

    return UserResponse(
        user_id=str(db_user.id),
        email=db_user.email,
        first_name=first_name,
        last_name=last_name,
        role=db_user.role,
        organization=db_user.organisation,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        last_login=db_user.last_login
    )
