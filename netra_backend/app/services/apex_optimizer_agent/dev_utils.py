from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.config import settings
from netra_backend.app.db.models_postgres import User
from netra_backend.app.services.user_service import user_service

DEV_USER_EMAIL = settings.dev_user_email

async def get_or_create_dev_user(db_session: AsyncSession) -> User:
    """Get or create a development user for local development environment setup."""
    user = await user_service.get_or_create_dev_user(db_session, email=DEV_USER_EMAIL)
    return user