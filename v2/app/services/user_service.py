from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models_postgres import User
from app.schemas import UserCreate, UserUpdate
from app.services.base import BaseService
from fastapi.encoders import jsonable_encoder

class UserService(BaseService[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()

    async def create(self, db: Session, *, obj_in: UserCreate) -> User:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(
            email=obj_in_data["email"],
            full_name=obj_in_data.get("full_name"),
            picture=obj_in_data.get("picture"),
            is_active=obj_in_data.get("is_active", True),
            is_superuser=obj_in_data.get("is_superuser", False),
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

user_service = UserService(User)
