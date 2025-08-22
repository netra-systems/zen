"""Unified PostgreSQL Async Configuration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database management across environments
- Value Impact: Single interface for all environments, reducing complexity
- Strategic Impact: Faster development and deployment cycles
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedPostgresDB:
    """Unified async PostgreSQL manager that auto-detects environment"""
    
    def __init__(self):
        # Detect environment from unified config
        config = get_unified_config()
        self.is_cloud_run = config.deployment.is_cloud_run
        self.is_staging = config.environment == "staging"
        self.is_production = config.environment == "production"
        self.is_test = config.environment == "test"
        
        # Manager will be initialized on first use
        self.manager = None
        self._initialized = False
        
        logger.info(f"Unified DB initialized - Cloud Run: {self.is_cloud_run}, "
                   f"Staging: {self.is_staging}, Production: {self.is_production}, "
                   f"Test: {self.is_test}")
    
    async def initialize(self):
        """Initialize appropriate manager based on environment"""
        if self._initialized:
            return
        
        try:
            if self.is_cloud_run or self.is_staging or self.is_production:
                # Use Cloud SQL for Cloud Run, staging, and production
                logger.info("Initializing Cloud SQL manager for cloud environment")
                from netra_backend.app.db.postgres_cloud import cloud_db
                self.manager = cloud_db
                await self.manager.initialize_cloud_run()
            else:
                # Use local async for development and testing
                logger.info("Initializing async manager for local environment")
                from netra_backend.app.db.postgres_async import async_db
                self.manager = async_db
                await self.manager.initialize_local()
            
            self._initialized = True
            logger.info("Unified database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize unified database manager: {e}")
            raise RuntimeError(f"Database initialization failed: {e}") from e
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session from appropriate manager"""
        if not self._initialized:
            await self.initialize()
        
        async with self.manager.get_session() as session:
            yield session
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            if not self._initialized:
                await self.initialize()
            
            return await self.manager.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def close(self):
        """Close connections"""
        if self.manager:
            await self.manager.close()
            self._initialized = False
            logger.info("Unified database connections closed")
    
    def get_status(self) -> dict:
        """Get current database status"""
        if not self._initialized or not self.manager:
            return {
                "status": "not_initialized",
                "environment": self._get_environment_name(),
            }
        
        base_status = {
            "status": "active",
            "environment": self._get_environment_name(),
            "manager_type": "cloud_sql" if (self.is_cloud_run or self.is_staging or self.is_production) else "local_async",
        }
        
        # Get manager-specific status
        if hasattr(self.manager, 'get_pool_status'):
            base_status.update(self.manager.get_pool_status())
        elif hasattr(self.manager, 'get_connection_status'):
            base_status.update(self.manager.get_connection_status())
        
        return base_status
    
    def _get_environment_name(self) -> str:
        """Get human-readable environment name"""
        if self.is_production:
            return "production"
        elif self.is_staging:
            return "staging"
        elif self.is_cloud_run:
            return "cloud_run"
        elif self.is_test:
            return "test"
        else:
            return "development"


# Global unified instance
unified_db = UnifiedPostgresDB()


# Single FastAPI dependency for all environments
async def get_db():
    """Universal database session dependency for FastAPI"""
    async with unified_db.get_session() as session:
        yield session


# Backward compatibility alias
get_async_db = get_db


# Utility functions for lifecycle management
async def initialize_database():
    """Initialize the database connection"""
    await unified_db.initialize()
    return unified_db


async def close_database():
    """Close the database connection"""
    await unified_db.close()


async def check_database_health() -> dict:
    """Check database health and return status"""
    is_healthy = await unified_db.test_connection()
    status = unified_db.get_status()
    status["healthy"] = is_healthy
    return status


# FastAPI lifespan events integration
async def on_startup():
    """FastAPI startup event handler"""
    logger.info("Starting database initialization on app startup")
    await initialize_database()
    
    # Test connection
    health = await check_database_health()
    if health.get("healthy"):
        logger.info(f"Database healthy on startup: {health}")
    else:
        logger.error(f"Database unhealthy on startup: {health}")
        # Don't fail startup, allow app to run in degraded mode


async def on_shutdown():
    """FastAPI shutdown event handler"""
    logger.info("Closing database connections on app shutdown")
    await close_database()