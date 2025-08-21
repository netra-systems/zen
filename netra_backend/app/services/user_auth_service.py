"""
User Authentication Service
Provides service layer abstraction for user model operations in routes
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.db.models_postgres import User
from netra_backend.app.services.user_service import user_service


class UserAuthService:
    """Service layer for user authentication operations in routes."""
    
    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID - service layer abstraction for routes."""
        return await user_service.get(db, id=user_id)
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email - service layer abstraction for routes."""
        return await user_service.get_by_email(db, email=email)
    
    async def validate_user_active(self, user: User) -> bool:
        """Validate user is active."""
        if not user:
            return False
        return getattr(user, 'is_active', True)


# Singleton instance
user_auth_service = UserAuthService()