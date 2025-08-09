from .base import CRUDBase
from ..db.models_postgres import User
from ..schemas.User import UserCreate, UserUpdate
from sqlalchemy.orm import Session

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> User:
        return db.query(User).filter(User.email == email).first()

user_service = CRUDUser(User)
