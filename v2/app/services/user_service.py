
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.auth.schemas import UserCreate, UserUpdate
from sqlalchemy.future import select

class UserService:
    async def get_user_by_email(self, db_session: AsyncSession, email: str) -> User | None:
        result = await db_session.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create_user(self, db_session: AsyncSession, user_create: UserCreate) -> User:
        # In a real application, you would hash the password here
        db_user = User(**user_create.model_dump())
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        return db_user

    async def update_user(
        self, db_session: AsyncSession, user: User, user_update: UserUpdate
    ) -> User:
        user_data = user_update.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user, key, value)
        await db_session.commit()
        await db_session.refresh(user)
        return user
