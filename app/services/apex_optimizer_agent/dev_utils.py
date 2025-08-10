from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User

from app.config import settings

DEV_USER_EMAIL = settings.dev_user_email

async def get_or_create_dev_user(db_session: AsyncSession) -> User:
    """Get or create a dummy user for development purposes."""
    result = await db_session.execute(select(User).where(User.email == DEV_USER_EMAIL))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=DEV_USER_EMAIL, full_name="Development User", is_active=True)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user