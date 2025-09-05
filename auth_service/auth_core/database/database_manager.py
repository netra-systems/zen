"""
Auth Database Manager
Simple implementation to support auth service database operations
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Simple database manager for auth service"""
    
    @staticmethod
    def create_async_engine(**kwargs) -> AsyncEngine:
        """Create async database engine"""
        env = get_env()
        
        # Build database URL
        database_url = (
            f"postgresql+asyncpg://"
            f"{env.get('POSTGRES_USER', 'netra')}:"
            f"{env.get('POSTGRES_PASSWORD', 'netra123')}@"
            f"{env.get('POSTGRES_HOST', 'postgres')}:"
            f"{env.get('POSTGRES_PORT', '5432')}/"
            f"{env.get('POSTGRES_DB', 'netra_dev')}"
        )
        
        logger.info(f"Creating async database engine for auth service")
        
        # Create engine with simple configuration
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=False,
            **kwargs
        )
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL for auth service"""
        env = get_env()
        return (
            f"postgresql+asyncpg://"
            f"{env.get('POSTGRES_USER', 'netra')}:"
            f"{env.get('POSTGRES_PASSWORD', 'netra123')}@"
            f"{env.get('POSTGRES_HOST', 'postgres')}:"
            f"{env.get('POSTGRES_PORT', '5432')}/"
            f"{env.get('POSTGRES_DB', 'netra_dev')}"
        )