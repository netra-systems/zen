from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas import UserCreate, UserUpdate
from app.services.base import BaseService

class UserService(BaseService[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(self.model).filter(self.model.email == email).first()

user_service = UserService(User)
