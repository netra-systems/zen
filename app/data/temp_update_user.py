import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import get_db_session
from app.db.models_postgres import User
from sqlalchemy import update
from app.logging_config import central_logger as logger

async def update_development_user():
    # get_db_session is an async generator
    async for session in get_db_session():
        async with session.begin():
            result = await session.execute(
                update(User)
                .where(User.email == settings.dev_user_email)
                .values(is_superuser=True)
            )
            if result.rowcount > 0:
                logger.info("Development user updated successfully.")
            else:
                logger.info("Development user not found.")

if __name__ == "__main__":
    # This is the critical change
    # We need to be in the right directory for the imports to work
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    asyncio.run(update_development_user())