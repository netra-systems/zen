from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models_postgres import User
from app.schemas import UserCreate, UserUpdate
from app.services.base import BaseService

class UserService(BaseService[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()

user_service = UserService(User)