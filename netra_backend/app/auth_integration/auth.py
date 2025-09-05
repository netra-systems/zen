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
from typing import Annotated, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Initialize auth client instance
auth_client = AuthServiceClient()
from netra_backend.app.db.models_postgres import User
from netra_backend.app.dependencies import get_request_scoped_db_session as get_db

# Note: Password hashing is handled by the auth service, not directly here


logger = logging.getLogger('auth_integration.auth')

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from auth service."""
    token = credentials.credentials
    validation_result = await _validate_token_with_auth_service(token)
    user = await _get_user_from_database(db, validation_result)
    return user

async def _validate_token_with_auth_service(token: str) -> Dict[str, str]:
    """Validate token with auth service."""
    validation_result = await auth_client.validate_token_jwt(token)
    if not validation_result or not validation_result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not validation_result.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return validation_result


async def _get_user_from_database(db: AsyncSession, validation_result: Dict[str, str]) -> User:
    """Get or create user from database."""
    from sqlalchemy import select
    from shared.database.session_validation import validate_db_session
    
    # Validate database session (handles both production and test scenarios)
    validate_db_session(db, "get_user_from_database")
    
    user_id = validation_result.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = await _auto_create_user_if_needed(db, validation_result)
    return user

async def _auto_create_user_if_needed(db: AsyncSession, validation_result: Dict[str, str]) -> User:
    """Auto-create user from JWT claims."""
    from netra_backend.app.services.user_service import user_service
    from netra_backend.app.config import get_config
    from shared.database.session_validation import validate_db_session
    
    # Validate database session (handles both production and test scenarios)
    validate_db_session(db, "auto_create_user_if_needed")
    
    user_id = validation_result.get("user_id")
    email = validation_result.get("email", f"user_{user_id}@example.com")
    user = await user_service.get_or_create_dev_user(db, email=email, user_id=user_id)
    
    config = get_config()
    logger.info(f"Auto-created user from JWT: {user.email} (env: {config.environment})")
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
    
    # Validate database session (handles both production and test scenarios)
    from shared.database.session_validation import validate_db_session
    logger.debug(f"get_current_user_optional - db type: {type(db)}")
    try:
        validate_db_session(db, "get_current_user_optional")
    except TypeError as e:
        logger.error(f"ERROR in get_current_user_optional: {e}")
    
    try:
        # Extract the token and validate it
        token = credentials.credentials
        validation_result = await _validate_token_with_auth_service(token)
        user = await _get_user_from_database(db, validation_result)
        return user
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None

# Alias for backward compatibility
get_current_active_user = get_current_user

async def get_current_user_with_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = None  # Will be injected separately
) -> User:
    """
    Get current authenticated user from auth service.
    This version is for use when db is already injected by another dependency.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not provided"
        )
    token = credentials.credentials
    validation_result = await _validate_token_with_auth_service(token)
    user = await _get_user_from_database(db, validation_result)
    return user


async def validate_token_jwt(token: str) -> Optional[Dict[str, str]]:
    """Validate a JWT token through the auth service."""
    validation = await auth_client.validate_token(token)
    return validation if validation else None

# Type annotations for dependency injection
ActiveUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]

# Permission-based dependencies
async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions."""
    if not _check_admin_permissions(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

def _check_admin_permissions(user: User) -> bool:
    """Check if user has admin permissions."""
    return ((hasattr(user, 'is_superuser') and user.is_superuser) or
            (hasattr(user, 'role') and user.role in ['admin', 'super_admin']) or
            (hasattr(user, 'is_admin') and user.is_admin))

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