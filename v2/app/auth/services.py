from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app import schemas

class SecurityService:
    async def get_user(self, db_session: AsyncSession, email: str) -> User | None:
        return await db_session.get(User, email)

    async def get_or_create_user_from_oauth(
        self, db_session: AsyncSession, user_info: dict
    ) -> User:
        user = await self.get_user(db_session, user_info["email"])
        if user:
            return user

        user_data = schemas.UserCreate(
            email=user_info["email"],
            full_name=user_info.get("name"),
            picture=user_info.get("picture"),
            password="",  # Not used for OAuth
        )
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


security_service = SecurityService()