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
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.clients.auth_client import auth_client
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.dependencies import get_db_dependency as get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Create auth-specific logger
import logging
logger = logging.getLogger('auth_integration.auth')

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
    import os
    
    # Use async session properly with context manager
    async with db as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            # In development mode, create a mock user
            if os.getenv("ENVIRONMENT", "development") == "development":
                # Create a development user object (not persisted)
                user = User(
                    id=user_id,
                    email=validation_result.get("email", "dev@example.com"),
                    is_admin=validation_result.get("is_admin", True),
                    is_developer=True
                )
                logger.warning(f"Created mock user for development: {user.email}")
            else:
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

# NOTE: All JWT and password hashing logic has been moved to the auth service
# This module ONLY handles FastAPI dependency injection
# See auth_service for actual authentication implementation

# Compatibility aliases for deprecated dependencies
ActiveUserWsDep = Annotated[User, Depends(get_current_user)]

# Backward compatibility stubs - These are deprecated and should not be used
# They exist only to prevent import errors during migration
def get_password_hash(password: str) -> str:
    """DEPRECATED: Use auth service instead"""
    logger.warning("get_password_hash is deprecated - use auth service")
    return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """DEPRECATED: Use auth service instead"""
    logger.warning("verify_password is deprecated - use auth service")
    return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """DEPRECATED: Use auth service instead"""
    logger.warning("create_access_token is deprecated - use auth service")
    return ""

def validate_token_jwt(token: str) -> Optional[Dict]:
    """DEPRECATED: Use auth service instead"""
    logger.warning("validate_token_jwt is deprecated - use auth service")
    return None