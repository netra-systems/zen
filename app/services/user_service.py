from .base import EnhancedCRUDService
from ..db.models_postgres import User
from ..schemas.User import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import bcrypt
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional

# Direct bcrypt usage for better compatibility

class CRUDUser(EnhancedCRUDService[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        obj_in_data = jsonable_encoder(obj_in)
        del obj_in_data['password']
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(obj_in.password.encode('utf-8'), salt).decode('utf-8')
        db_obj = User(**obj_in_data, hashed_password=hashed_password)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get_all_users(self, db: AsyncSession) -> List[User]:
        """Get all users from the system."""
        result = await db.execute(select(User))
        return result.scalars().all()
    
    async def update_user_role(self, user_id: str, role: str, db: AsyncSession) -> User:
        """Update user role in the system."""
        result = await db.execute(
            update(User).where(User.id == user_id).values(role=role)
        )
        await db.commit()
        user = await db.execute(select(User).filter(User.id == user_id))
        return user.scalars().first()
    
    async def _process_user_operation(self, operation: str, user_id: str, db: AsyncSession) -> bool:
        """Process single user operation."""
        try:
            if operation == "deactivate":
                await db.execute(update(User).where(User.id == user_id).values(is_active=False))
            elif operation == "activate":
                await db.execute(update(User).where(User.id == user_id).values(is_active=True))
            return True
        except Exception:
            return False
    
    async def _collect_operation_results(self, operation: str, user_ids: List[str], db: AsyncSession) -> tuple:
        """Collect results from bulk operations."""
        processed, failed, results = [], [], []
        for user_id in user_ids:
            success = await self._process_user_operation(operation, user_id, db)
            (processed.append(user_id) and results.append(user_id)) if success else failed.append(user_id)
        return processed, failed, results

    async def bulk_update_users(self, operation: str, user_ids: List[str], db: AsyncSession) -> Dict[str, Any]:
        """Perform bulk operations on multiple users."""
        processed, failed, results = await self._collect_operation_results(operation, user_ids, db)
        await db.commit()
        return {"processed": len(processed), "failed": len(failed), "results": results}

user_service = CRUDUser("user_service", User)

# Module-level wrapper functions for compatibility
async def get_all_users(db: AsyncSession) -> List[User]:
    """Get all users from the system."""
    return await user_service.get_all_users(db)

async def update_user_role(user_id: str, role: str, db: AsyncSession) -> User:
    """Update user role in the system."""
    return await user_service.update_user_role(user_id, role, db)

async def bulk_update_users(operation: str, user_ids: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Perform bulk operations on multiple users."""
    return await user_service.bulk_update_users(operation, user_ids, db)

# Export all public functions for proper module imports
__all__ = [
    'user_service',
    'CRUDUser',
    'get_all_users',
    'update_user_role',
    'bulk_update_users'
]
