
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from sqlalchemy.future import select
import uuid
from app.services.key_manager import KeyManager

class SecurityService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
    async def get_user_by_id(self, db_session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """
        Retrieves a user by their ID.
        """
        result = await db_session.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def get_or_create_user_from_oauth(self, db_session: AsyncSession, user_info: dict) -> User:
        """
        Retrieves a user by email from OAuth info, or creates a new user if they don't exist.
        """
        email = user_info.get("email")
        if not email:
            raise ValueError("Email not found in user info")

        result = await db_session.execute(select(User).filter(User.email == email))
        user = result.scalars().first()

        if not user:
            user = User(
                email=email,
                full_name=user_info.get("name"),
                picture=user_info.get("picture"),
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
        
        return user
