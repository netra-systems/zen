"""PostgreSQL Cloud Run Configuration with Cloud SQL Connector

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Production reliability and security
- Value Impact: Secure, managed database connections for Cloud Run
- Strategic Impact: Zero-downtime deployments and automatic failover

Integration:
- Uses DatabaseManager for environment detection and URL handling consistency
- Preserves Cloud SQL specific connector logic and Unix socket connections
- Provides centralized status monitoring with database manager integration
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CloudSQLManager:
    """Cloud SQL async connection manager for Cloud Run"""
    
    def __init__(self):
        self.connector = None
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize_cloud_run(self):
        """Initialize for Cloud Run with Cloud SQL"""
        if self._initialized:
            logger.debug("Cloud SQL already initialized, skipping")
            return
        
        # Verify we're in a Cloud SQL environment
        if not DatabaseManager.is_cloud_sql_environment():
            raise RuntimeError("Cloud SQL initialization called but not in Cloud SQL environment")
        
        try:
            # Import connector only when needed
            from google.cloud.sql.connector import Connector
            
            # Initialize connector
            self.connector = Connector()
            
            # Cloud SQL configuration from environment
            db_user = os.environ.get("DB_USER", "")
            db_pass = os.environ.get("DB_PASS", "")
            db_name = os.environ.get("DB_NAME", "")
            instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME", "")
            
            if not all([db_user, db_pass, db_name, instance_connection_name]):
                raise ValueError("Missing required Cloud SQL environment variables")
            
            logger.info(f"Connecting to Cloud SQL instance: {instance_connection_name}")
            
            # Create connection function for Cloud SQL
            def getconn():
                return self.connector.connect(
                    instance_connection_name,
                    "asyncpg",
                    user=db_user,
                    password=db_pass,
                    db=db_name,
                    # Additional connection parameters for resilience
                    enable_iam_auth=os.getenv("ENABLE_IAM_AUTH", "false").lower() == "true",
                    ip_type=os.getenv("CLOUD_SQL_IP_TYPE", "PRIVATE"),  # Prefer private IP
                )
            
            # Create async engine with NullPool for serverless
            # Use DatabaseManager's async URL format as template, but override with custom connector
            template_url = DatabaseManager.get_application_url_async()
            
            self.engine = create_async_engine(
                "postgresql+asyncpg://",
                creator=getconn,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                echo_pool=os.getenv("SQL_ECHO_POOL", "false").lower() == "true",
                poolclass=NullPool,  # Required for Cloud Run serverless
                # Additional settings for Cloud Run
                connect_args={
                    "server_settings": {
                        "application_name": "netra_backend_cloud",
                        "tcp_keepalives_idle": "120",  # Shorter for serverless
                        "tcp_keepalives_interval": "10",
                        "tcp_keepalives_count": "3",
                    },
                    "command_timeout": 60,
                }
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            self._initialized = True
            logger.info("Cloud SQL async engine initialized successfully")
            
        except ImportError as e:
            logger.error(f"Cloud SQL connector not installed: {e}")
            logger.info("Install with: pip install cloud-sql-python-connector[asyncpg]")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Cloud SQL: {e}")
            raise RuntimeError(f"Cloud SQL initialization failed: {e}") from e
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic transaction management"""
        if not self._initialized:
            await self.initialize_cloud_run()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Cloud SQL transaction rolled back: {e}")
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Test Cloud SQL connectivity"""
        try:
            if not self._initialized:
                await self.initialize_cloud_run()
            
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar_one()
                logger.info(f"Cloud SQL connection test successful: {value}")
                return True
        except Exception as e:
            logger.error(f"Cloud SQL connection test failed: {e}")
            return False
    
    async def close(self):
        """Close all connections and cleanup"""
        if self.engine:
            await self.engine.dispose()
        
        if self.connector:
            self.connector.close()
        
        self._initialized = False
        logger.info("Cloud SQL connections closed")
    
    def get_connection_status(self) -> dict:
        """Get connection status for monitoring"""
        return {
            "status": "active" if self._initialized else "not_initialized",
            "type": "cloud_sql",
            "pooling": "disabled",  # NullPool for serverless
            "instance": os.environ.get("INSTANCE_CONNECTION_NAME", "not_configured"),
        }


# Global instance for Cloud Run
cloud_db = CloudSQLManager()


# FastAPI dependency
async def get_cloud_db_session():
    """Dependency for FastAPI routes in Cloud Run"""
    async with cloud_db.get_session() as session:
        yield session


# Utility functions for initialization
async def initialize_cloud_db():
    """Initialize the Cloud SQL connection"""
    await cloud_db.initialize_cloud_run()
    return cloud_db


async def close_cloud_db():
    """Close the Cloud SQL connection"""
    await cloud_db.close()


def should_use_cloud_sql() -> bool:
    """Check if Cloud SQL should be used based on environment detection.
    
    Returns:
        True if Cloud SQL connector should be used
    """
    return DatabaseManager.is_cloud_sql_environment()


def get_cloud_sql_status() -> dict:
    """Get comprehensive Cloud SQL status for monitoring.
    
    Returns:
        Status information including environment detection and connection state
    """
    return {
        "cloud_sql_environment": DatabaseManager.is_cloud_sql_environment(),
        "connection_status": cloud_db.get_connection_status(),
        "database_manager_integration": True,
    }