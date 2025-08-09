from .base import CRUDBase
from ..db.models_postgres import User
from ..schemas.User import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

user_service = CRUDUser(User)