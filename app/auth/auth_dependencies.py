from typing import Annotated, Optional, List
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.dependencies import get_db_session, get_security_service
from app.services.security_service import SecurityService
from app.services.permission_service import PermissionService
from app.db.models_postgres import User
from app.logging_config import central_logger
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

logger = central_logger.get_logger(__name__)

def _validate_token_presence(token: str) -> bool:
    """Validate token is present."""
    if not token:
        logger.error("Token not found")
        return False
    return True

async def _safe_process_user_token(token: str, db_session: AsyncSession, security_service: SecurityService) -> Optional[User]:
    """Safely process user token with error handling."""
    try:
        return await _process_user_token(token, db_session, security_service)
    except Exception as e:
        logger.error(f"Error decoding token or fetching user: {e}")
        return None

async def get_current_user(
    token: str,
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    if not _validate_token_presence(token):
        return None
    return await _safe_process_user_token(token, db_session, security_service)

async def get_current_user_ws(
    token: Annotated[str, Query()],
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    return await get_current_user(token, db_session, security_service)

async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    user = await get_current_user(token, db_session, security_service)
    _validate_user_authentication(user)
    _validate_user_is_active(user)
    # Auto-detect and update developer status skipped for async context
    return user

def _create_permission_error(permission: str) -> HTTPException:
    """Create permission denied error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied. Required permission: {permission}"
    )

def require_permission(permission: str):
    """Dependency to require a specific permission"""
    async def permission_checker(user: User = Depends(get_current_active_user)) -> User:
        if not PermissionService.has_permission(user, permission):
            raise _create_permission_error(permission)
        return user
    return permission_checker

def _create_any_permission_error(permissions: List[str]) -> HTTPException:
    """Create any permission denied error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied. Required one of: {', '.join(permissions)}"
    )

def require_any_permission(permissions: List[str]):
    """Dependency to require any of the specified permissions"""
    async def permission_checker(user: User = Depends(get_current_active_user)) -> User:
        if not PermissionService.has_any_permission(user, permissions):
            raise _create_any_permission_error(permissions)
        return user
    return permission_checker

def _create_developer_error() -> HTTPException:
    """Create developer access denied error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Developer access required"
    )

def require_developer():
    """Dependency to require developer role or higher"""
    async def developer_checker(user: User = Depends(get_current_active_user)) -> User:
        if not PermissionService.is_developer_or_higher(user):
            raise _create_developer_error()
        return user
    return developer_checker

def _create_admin_error() -> HTTPException:
    """Create admin access denied error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )

def require_admin():
    """Dependency to require admin role or higher"""
    async def admin_checker(user: User = Depends(get_current_active_user)) -> User:
        if not PermissionService.is_admin_or_higher(user):
            raise _create_admin_error()
        return user
    return admin_checker

def _handle_optional_auth_failure(error: Exception) -> None:
    """Handle optional authentication failure."""
    logger.warning(f"Optional user authentication failed: {error}")

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    """Get current user without raising exceptions if authentication fails"""
    if not token:
        return None
    try:
        return await get_current_user(token, db_session, security_service)
    except Exception as e:
        _handle_optional_auth_failure(e)
        return None

def _validate_token_payload(payload: Optional[dict]) -> Optional[dict]:
    """Validate token payload and return if valid."""
    if payload is None:
        logger.error("Token payload is invalid")
        return None
    return payload

async def _process_user_token(token: str, db_session: AsyncSession, security_service: SecurityService) -> Optional[User]:
    """Process user token and return user if valid."""
    payload = security_service.decode_access_token(token)
    validated_payload = _validate_token_payload(payload)
    if validated_payload is None:
        return None
    user_id = _extract_user_id_from_payload(validated_payload)
    if user_id is None:
        return None
    return await _fetch_user_by_id(db_session, security_service, user_id)

def _extract_user_id_from_payload(payload: dict) -> Optional[str]:
    """Extract user ID from token payload."""
    user_id = payload.get("sub")
    if user_id is None:
        logger.error("User ID not found in token payload")
    return user_id

async def _fetch_user_by_id(db_session: AsyncSession, security_service: SecurityService, user_id: str) -> Optional[User]:
    """Fetch user by ID."""
    user = await security_service.get_user_by_id(db_session, user_id)
    if user is None:
        logger.error(f"User with ID {user_id} not found")
    return user

def _create_unauthorized_error() -> HTTPException:
    """Create unauthorized access error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

def _validate_user_authentication(user: Optional[User]) -> None:
    """Validate user authentication."""
    if not user:
        raise _create_unauthorized_error()

def _validate_user_is_active(user: User) -> None:
    """Validate user is active."""
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

ActiveUserDep = Depends(get_current_active_user)
ActiveUserWsDep = Depends(get_current_user_ws)
DeveloperDep = Depends(require_developer())
AdminDep = Depends(require_admin())