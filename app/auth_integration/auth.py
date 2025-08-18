"""
🔴 CRITICAL: Auth Integration Module - DO NOT IMPLEMENT AUTH LOGIC HERE

This module ONLY provides FastAPI dependency injection for authentication.
It connects to an EXTERNAL auth service via auth_client.

ARCHITECTURE:
- Auth Service: Separate microservice at AUTH_SERVICE_URL (e.g., http://localhost:8001)
- This Module: ONLY integration point - NO auth logic
- auth_client: HTTP client that calls the external auth service

⚠️ NEVER IMPLEMENT HERE:
- Token generation/validation logic
- Password hashing/verification (except legacy compatibility)
- OAuth provider integration
- User authentication logic

✅ ONLY DO HERE:
- Call auth_client methods
- FastAPI dependency injection
- Convert auth service responses to User objects

See: CRITICAL_AUTH_ARCHITECTURE.md for full details
"""
from typing import Optional, Annotated, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.clients.auth_client import auth_client
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.dependencies import get_db_dependency as get_db
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from auth service
    """
    token = credentials.credentials
    
    # Validate token with auth service
    validation_result = await auth_client.validate_token(token)
    
    if not validation_result or not validation_result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_id = validation_result.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    from sqlalchemy import select
    
    # Use async session properly with context manager
    async with db as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

# Alias for compatibility
get_optional_current_user = get_current_user_optional
get_current_active_user = get_current_user

# Type annotations for dependency injection
ActiveUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]

# Permission-based dependencies
async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions"""
    if not hasattr(user, 'is_admin') or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_developer(user: User = Depends(get_current_user)) -> User:
    """Require developer permissions"""
    if not hasattr(user, 'is_developer') or not user.is_developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer access required"
        )
    return user

AdminDep = Annotated[User, Depends(require_admin)]
DeveloperDep = Annotated[User, Depends(require_developer)]

def require_permission(permission: str):
    """Create a dependency that requires a specific permission"""
    async def check_permission(user: User = Depends(get_current_user)) -> User:
        _validate_user_permission(user, permission)
        return user
    return check_permission

def _validate_user_permission(user: User, permission: str) -> None:
    """Validate that user has the required permission."""
    if hasattr(user, 'permissions'):
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

# Password hashing utilities
# Initialize Argon2 hasher with recommended settings
ph = PasswordHasher()

def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id"""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        ph.verify(hashed_password, plain_password)
        return _check_password_rehash_needed(hashed_password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def _check_password_rehash_needed(hashed_password: str) -> bool:
    """Check if password needs rehashing and return True."""
    if ph.check_needs_rehash(hashed_password):
        return True
    return True

# JWT token utilities
def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = _get_token_expiry(expires_delta)
    to_encode.update({"exp": expire})
    
    secret_key = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
    return jwt.encode(to_encode, secret_key, algorithm="HS256")

def _get_token_expiry(expires_delta: Optional[timedelta]) -> datetime:
    """Get token expiry datetime."""
    if expires_delta:
        return datetime.utcnow() + expires_delta
    return datetime.utcnow() + timedelta(minutes=15)

def validate_token_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Validate and decode a JWT token (local validation)"""
    try:
        secret_key = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return _handle_expired_token()
    except jwt.JWTError as e:
        return _handle_jwt_error(e)

def _handle_expired_token() -> None:
    """Handle expired token scenario."""
    logger.warning("Token has expired")
    return None

def _handle_jwt_error(error: Exception) -> None:
    """Handle JWT validation error."""
    logger.warning(f"Token validation failed: {error}")
    return None

# Compatibility aliases for deprecated dependencies
ActiveUserWsDep = Annotated[User, Depends(get_current_user)]