from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models_postgres import User as UserModel
from app.auth import schemas as auth_schemas

class SecurityService:
    async def get_user(self, db_session: AsyncSession, email: str) -> UserModel | None:
        result = await db_session.execute(select(UserModel).filter(UserModel.email == email))
        return result.scalars().first()

    async def get_or_create_user_from_oauth(
        self, db_session: AsyncSession, user_info: dict
    ) -> UserModel:
        user = await self.get_user(db_session, user_info["email"])
        if user:
            # Update user info if it has changed
            user.full_name = user_info.get("name", user.full_name)
            user.picture = user_info.get("picture", user.picture)
            await db_session.commit()
            await db_session.refresh(user)
            return user

        user_data = auth_schemas.User(
            id=user_info.get("sub"),
            email=user_info["email"],
            full_name=user_info.get("name"),
            picture=user_info.get("picture"),
        )
        
        user = UserModel(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


security_service = SecurityService()
