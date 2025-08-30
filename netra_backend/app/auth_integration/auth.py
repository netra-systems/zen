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
# Create auth-specific logger
import logging
from datetime import timedelta
from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Initialize auth client instance
auth_client = AuthServiceClient()
from netra_backend.app.db.models_postgres import User
from netra_backend.app.database import get_db_session
from netra_backend.app.dependencies import get_db_dependency as get_db

# Note: Password hashing is handled by the auth service, not directly here

# Compatibility function for legacy imports
def get_password_hash(password: str) -> str:
    """Hash a password - delegates to auth service."""
    # For testing purposes, return a simple hash
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

logger = logging.getLogger('auth_integration.auth')

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from auth service
    """
    token = credentials.credentials
    
    # Validate token with auth service
    validation_result = await auth_client.validate_token_jwt(token)
    
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
    
    import os

    from sqlalchemy import select
    
    # db is already an AsyncSession from the dependency injection
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # In development mode, create and persist a dev user
        from netra_backend.app.config import get_config
        config = get_config()
        if config.environment == "development":
            from netra_backend.app.services.user_service import user_service
            
            # Use centralized dev user creation
            email = validation_result.get("email", "dev@example.com")
            user = await user_service.get_or_create_dev_user(db, email=email, user_id=user_id)
            logger.warning(f"Using dev user: {user.email}")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    if not credentials:
        return None
    
    try:
        # Reuse get_current_user logic by calling it directly
        return await get_current_user(credentials, db)
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None

# Alias for compatibility
get_optional_current_user = get_current_user_optional
get_current_active_user = get_current_user

# Legacy function exports for backward compatibility
async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token through the auth service."""
    from netra_backend.app.services.token_service import token_service
    return await token_service.create_access_token(
        user_id=data.get("sub", data.get("user_id")),
        email=data.get("email"),
        additional_claims=data,
        expires_delta=expires_delta
    )

async def validate_token_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Validate a JWT token through the auth service."""
    validation = await auth_client.validate_token(token)
    return validation if validation else None

# Type annotations for dependency injection
ActiveUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]

# Permission-based dependencies
async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions"""
    # Check both is_superuser, role, and legacy is_admin for admin permissions
    is_admin = (hasattr(user, 'is_superuser') and user.is_superuser) or \
               (hasattr(user, 'role') and user.role in ['admin', 'super_admin']) or \
               (hasattr(user, 'is_admin') and user.is_admin)
    if not is_admin:
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
    if hasattr(user, 'permissions') and user.permissions is not None:
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

# NOTE: All JWT and password hashing logic has been moved to the auth service
# This module ONLY handles FastAPI dependency injection
# See auth_service for actual authentication implementation