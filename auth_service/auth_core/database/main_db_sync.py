"""
Main Database Sync Module
Handles syncing auth users to main application database
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class MainDatabaseSync:
    """Manages main database sync operations with Cloud Run compatibility"""
    
    def __init__(self):
        self._engine = None
        self._session_maker = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection (public method)"""
        await self._initialize_engine()
    
    async def _ensure_initialized(self):
        """Lazy initialization for Cloud Run compatibility"""
        if not self._initialized:
            await self._initialize_engine()
    
    async def _initialize_engine(self):
        """Initialize engine with Cloud Run optimizations"""
        if self._initialized:
            return
            
        # Check multiple environment variables for database URL
        # Priority: MAIN_DATABASE_URL > DATABASE_URL > default
        main_db_url = (
            os.getenv("MAIN_DATABASE_URL") or 
            os.getenv("DATABASE_URL") or
            "postgresql+asyncpg://postgres:postgres@localhost:5432/apex_development"
        )
        
        # Convert postgres:// to postgresql+asyncpg:// if needed
        if main_db_url.startswith("postgres://"):
            main_db_url = main_db_url.replace("postgres://", "postgresql+asyncpg://")
        elif main_db_url.startswith("postgresql://"):
            main_db_url = main_db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        logger.info(f"Initializing main DB sync with URL pattern: {main_db_url.split('@')[1] if '@' in main_db_url else 'local'}")
        
        # Use NullPool for serverless environments
        self._engine = create_async_engine(
            main_db_url, 
            echo=False,
            poolclass=NullPool  # Important for Cloud Run
        )
        self._session_maker = async_sessionmaker(
            self._engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        self._initialized = True
        logger.info("Main database sync engine initialized")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with proper cleanup"""
        await self._ensure_initialized()
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def sync_user(self, auth_user) -> Optional[str]:
        """
        Sync auth user to main database
        Returns: user_id if successful, None if failed
        """
        try:
            async with self.get_session() as session:
                # Import main app User model
                import sys
                from pathlib import Path
                import uuid
                
                # Add main app to path
                auth_dir = Path(__file__).resolve().parent.parent.parent
                app_dir = auth_dir.parent / "app"
                if str(app_dir) not in sys.path:
                    sys.path.insert(0, str(app_dir.parent))
                
                from app.db.models_postgres import User
                
                # First check by email to avoid duplicate conflicts
                email_result = await session.execute(
                    select(User).filter(User.email == auth_user.email)
                )
                existing_by_email = email_result.scalars().first()
                
                if existing_by_email:
                    # User exists, update and return existing ID
                    existing_by_email.full_name = auth_user.full_name or existing_by_email.full_name
                    existing_by_email.updated_at = auth_user.updated_at
                    logger.info(f"Found existing user {auth_user.email} with ID {existing_by_email.id}")
                    return existing_by_email.id
                
                # No user with this email, create new one
                # Generate a proper unique ID if the provided one might conflict
                new_id = auth_user.id
                
                # Check if this ID already exists
                id_result = await session.execute(
                    select(User).filter(User.id == new_id)
                )
                if id_result.scalars().first():
                    # ID conflict, generate new one
                    new_id = f"dev-{uuid.uuid4().hex[:8]}"
                    logger.info(f"ID conflict detected, using new ID: {new_id}")
                
                # Create new user
                new_user = User(
                    id=new_id,
                    email=auth_user.email,
                    full_name=auth_user.full_name or auth_user.email,
                    is_active=auth_user.is_active,
                    is_superuser=False,
                    is_developer=False,
                    role="user"
                )
                session.add(new_user)
                logger.info(f"Created new user {auth_user.email} with ID {new_id}")
                return new_id
                
        except Exception as e:
            logger.error(f"Failed to sync user: {e}")
            return None
    
    async def close(self):
        """Close the engine connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Main database sync engine closed")

# Global instance
main_db_sync = MainDatabaseSync()