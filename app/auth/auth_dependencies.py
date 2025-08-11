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

async def get_current_user(
    token: str,
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    if not token:
        logger.error("Token not found")
        return None
    try:
        payload = security_service.decode_access_token(token)
        if payload is None:
            logger.error("Token payload is invalid")
            return None
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("User ID not found in token payload")
            return None
        user = await security_service.get_user_by_id(db_session, user_id)
        if user is None:
            logger.error(f"User with ID {user_id} not found")
            return None
        return user
    except Exception as e:
        logger.error(f"Error decoding token or fetching user: {e}")
        return None

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
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Auto-detect and update developer status
    # Note: This is using sync Session, may need adjustment for async
    # For now, we'll skip auto-update in async context and rely on login-time detection
    
    return user

def require_permission(permission: str):
    """Dependency to require a specific permission"""
    async def permission_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if not PermissionService.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission}"
            )
        return user
    return permission_checker

def require_any_permission(permissions: List[str]):
    """Dependency to require any of the specified permissions"""
    async def permission_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if not PermissionService.has_any_permission(user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required one of: {', '.join(permissions)}"
            )
        return user
    return permission_checker

def require_developer():
    """Dependency to require developer role or higher"""
    async def developer_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if not PermissionService.is_developer_or_higher(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Developer access required"
            )
        return user
    return developer_checker

def require_admin():
    """Dependency to require admin role or higher"""
    async def admin_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if not PermissionService.is_admin_or_higher(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return user
    return admin_checker

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
        logger.warning(f"Optional user authentication failed: {e}")
        return None

ActiveUserDep = Depends(get_current_active_user)
ActiveUserWsDep = Depends(get_current_user_ws)
DeveloperDep = Depends(require_developer())
AdminDep = Depends(require_admin())