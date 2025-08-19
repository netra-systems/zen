"""
Main Database Sync Module
Handles syncing auth users to main application database
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from typing import Optional

logger = logging.getLogger(__name__)

class MainDatabaseSync:
    """Singleton for main database sync operations"""
    
    _instance = None
    _engine = None
    _session_maker = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize single engine for main database"""
        main_db_url = os.getenv(
            "DATABASE_URL", 
            "postgresql+asyncpg://postgres:postgres@localhost:5432/apex_development"
        )
        
        self._engine = create_async_engine(main_db_url, echo=False)
        self._session_maker = async_sessionmaker(
            self._engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        logger.info("Main database sync engine initialized")
    
    async def sync_user(self, auth_user) -> bool:
        """Sync auth user to main database"""
        try:
            async with self._session_maker() as session:
                # Import main app User model
                import sys
                from pathlib import Path
                
                # Add main app to path
                auth_dir = Path(__file__).resolve().parent.parent.parent
                app_dir = auth_dir.parent / "app"
                if str(app_dir) not in sys.path:
                    sys.path.insert(0, str(app_dir.parent))
                
                from app.db.models_postgres import User
                
                # Check if user exists
                result = await session.execute(
                    select(User).filter(User.id == auth_user.id)
                )
                existing_user = result.scalars().first()
                
                if not existing_user:
                    # Create new user
                    new_user = User(
                        id=auth_user.id,
                        email=auth_user.email,
                        full_name=auth_user.full_name or auth_user.email,
                        is_active=auth_user.is_active,
                        is_superuser=False,
                        is_developer=False,
                        role="user"
                    )
                    session.add(new_user)
                    await session.commit()
                    logger.info(f"Created user {auth_user.email} in main DB")
                else:
                    # Update existing user
                    existing_user.email = auth_user.email
                    existing_user.full_name = auth_user.full_name or existing_user.full_name
                    existing_user.updated_at = auth_user.updated_at
                    await session.commit()
                    logger.info(f"Updated user {auth_user.email} in main DB")
                
                return True
        except Exception as e:
            logger.error(f"Failed to sync user: {e}")
            return False
    
    async def close(self):
        """Close the engine connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Main database sync engine closed")

# Global instance
main_db_sync = MainDatabaseSync()