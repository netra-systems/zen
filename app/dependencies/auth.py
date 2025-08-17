"""
Auth Dependencies - FastAPI dependency injection for authentication
Uses the standalone auth service for all auth operations
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.clients.auth_client import auth_client
from app.db.models_postgres import User
from app.db.postgres import get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
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
    
    user = db.query(User).filter(User.id == user_id).first()
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
        # Check user permissions
        if hasattr(user, 'permissions'):
            if permission not in user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
        return user
    return check_permission