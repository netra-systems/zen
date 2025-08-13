from .base import CRUDBase
from ..db.models_postgres import User
from ..schemas.User import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from passlib.context import CryptContext
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        obj_in_data = jsonable_encoder(obj_in)
        del obj_in_data['password']
        hashed_password = pwd_context.hash(obj_in.password)
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

user_service = CRUDUser(User)

# Note: Module-level functions removed - use user_service instance with proper db session
