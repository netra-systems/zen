"""Unified Database Manager - Handles Sync and Async Connections

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management for migrations and runtime
- Value Impact: Eliminates sync/async conflicts, centralizes URL transformation logic
- Strategic Impact: Single source of truth for all database connection patterns

This module provides the unified interface for both sync (Alembic migrations) and
async (FastAPI application) database connections. It handles URL transformations,
SSL parameter management, and environment detection.

Each function ≤15 lines, class ≤200 lines total.
"""

import os
import re
import asyncio
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger as logger


class DatabaseManager:
    """Unified database manager for sync and async connections."""
    
    @staticmethod
    def get_base_database_url() -> str:
        """Get clean base URL without driver-specific elements.
        
        Returns:
            Clean database URL with driver prefixes and SSL params stripped
        """
        # First check direct environment variable (for tests that patch os.environ)
        import os
        raw_url = os.environ.get("DATABASE_URL", "")
        
        # Skip configuration loading during test collection to prevent hanging
        if os.environ.get('TEST_COLLECTION_MODE') == '1':
            return raw_url or "sqlite:///:memory:"
        
        # If not found, try unified config
        if not raw_url:
            try:
                config = get_unified_config()
                raw_url = config.database_url or ""
            except Exception:
                pass  # Will use default URL below
        
        if not raw_url:
            return DatabaseManager._get_default_database_url()
        
        # Strip async driver prefixes
        clean_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres://", "postgresql://")
        
        # Handle SSL parameters - remove for Cloud SQL, normalize for others
        if "/cloudsql/" in clean_url:
            # Cloud SQL Unix socket - remove all SSL parameters
            clean_url = re.sub(r'[&?]sslmode=[^&]*', '', clean_url)
            clean_url = re.sub(r'[&?]ssl=[^&]*', '', clean_url)
        
        return clean_url
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get sync URL for migrations (psycopg2/pg8000).
        
        Returns:
            Database URL compatible with synchronous drivers
        """
        base_url = DatabaseManager.get_base_database_url()
        
        # Ensure synchronous driver
        if base_url.startswith("postgresql+asyncpg://"):
            base_url = base_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Convert asyncpg SSL params to psycopg2 format
        if "ssl=" in base_url and "/cloudsql/" not in base_url:
            base_url = base_url.replace("ssl=", "sslmode=")
        
        return base_url
    
    @staticmethod
    def get_application_url_async() -> str:
        """Get async URL for application (asyncpg).
        
        Returns:
            Database URL compatible with asyncpg driver
        """
        base_url = DatabaseManager.get_base_database_url()
        
        # Ensure async driver
        if base_url.startswith("postgresql://"):
            base_url = base_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Handle SSL parameters based on connection type
        if "/cloudsql/" in base_url:
            # Cloud SQL Unix socket - remove all SSL parameters
            base_url = re.sub(r'[&?]sslmode=[^&]*', '', base_url)
            base_url = re.sub(r'[&?]ssl=[^&]*', '', base_url)
        else:
            # CRITICAL FIX: For ALL non-Cloud SQL async connections,
            # convert psycopg2 'sslmode=' to asyncpg 'ssl=' format
            # This is REQUIRED because asyncpg doesn't understand 'sslmode'
            if "sslmode=" in base_url:
                base_url = base_url.replace("sslmode=", "ssl=")
        
        return base_url
    
    @staticmethod
    def validate_base_url() -> bool:
        """Ensure no driver-specific elements remain.
        
        Returns:
            True if base URL is clean, False otherwise
        """
        base_url = DatabaseManager.get_base_database_url()
        
        # Check for driver-specific elements
        has_async_driver = "asyncpg" in base_url
        has_mixed_ssl = ("ssl=" in base_url and "sslmode=" in base_url)
        
        return not (has_async_driver or has_mixed_ssl)
    
    @staticmethod
    def validate_migration_url_sync_format(url: str = None) -> bool:
        """Confirm sync driver compatibility.
        
        Args:
            url: Optional URL to validate, uses migration URL if None
            
        Returns:
            True if URL is sync-compatible
        """
        target_url = url or DatabaseManager.get_migration_url_sync_format()
        
        # Must NOT have async drivers
        if "asyncpg" in target_url:
            return False
        
        # Should use sslmode (not ssl) unless Cloud SQL
        if "/cloudsql/" not in target_url and "ssl=" in target_url:
            return False
        
        return target_url.startswith("postgresql://")
    
    @staticmethod
    def validate_application_url(url: str = None) -> bool:
        """Confirm async driver compatibility.
        
        Args:
            url: Optional URL to validate, uses application URL if None
            
        Returns:
            True if URL is async-compatible
        """
        target_url = url or DatabaseManager.get_application_url_async()
        
        # Must have async driver
        if not target_url.startswith("postgresql+asyncpg://"):
            return False
        
        # Should use ssl (not sslmode) unless Cloud SQL
        if "/cloudsql/" not in target_url and "sslmode=" in target_url:
            return False
        
        return True
    
    @staticmethod
    def create_migration_engine():
        """Return sync SQLAlchemy engine for Alembic.
        
        Returns:
            Synchronous SQLAlchemy engine configured for migrations
        """
        migration_url = DatabaseManager.get_migration_url_sync_format()
        
        # Check SQL_ECHO environment variable directly since unified config doesn't support it
        import os
        sql_echo = os.environ.get("SQL_ECHO", "false").lower() in ("true", "1", "yes", "on")
        
        return create_engine(
            migration_url,
            echo=sql_echo,
            pool_pre_ping=True,
            pool_recycle=3600,
            # Smaller pool for migration engine to avoid conflicts with main app pool
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_reset_on_return='rollback',
        )
    
    @staticmethod
    def create_application_engine():
        """Return async SQLAlchemy engine for FastAPI.
        
        Returns:
            Async SQLAlchemy engine configured for application runtime
        """
        app_url = DatabaseManager.get_application_url_async()
        
        connect_args = {}
        if "/cloudsql/" not in app_url:
            # Standard connection settings
            connect_args = {
                "server_settings": {
                    "application_name": "netra_backend_async",
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30", 
                    "tcp_keepalives_count": "3",
                }
            }
        
        # Check SQL_ECHO environment variable directly since unified config doesn't support it
        import os
        sql_echo = os.environ.get("SQL_ECHO", "false").lower() in ("true", "1", "yes", "on")
        
        return create_async_engine(
            app_url,
            echo=sql_echo,
            pool_pre_ping=True,
            pool_recycle=3600,
            # Increased pool sizes to handle concurrent startup operations and health checks
            pool_size=20,  # Base pool size increased from 10 to 20
            max_overflow=30,  # Max overflow increased from 20 to 30 (total max: 50 connections)
            pool_timeout=30,  # Timeout for getting connection from pool
            pool_reset_on_return='rollback',  # Reset connections properly
            connect_args=connect_args
        )
    
    @staticmethod
    def get_migration_session():
        """Return sync session factory for migrations.
        
        Returns:
            Synchronous session factory for Alembic operations
        """
        engine = DatabaseManager.create_migration_engine()
        return sessionmaker(bind=engine)
    
    @staticmethod
    def get_application_session():
        """Return async session factory for app runtime.
        
        Returns:
            Async session factory for FastAPI operations
        """
        engine = DatabaseManager.create_application_engine()
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Detect if running in Cloud SQL environment.
        
        Returns:
            True if using Cloud SQL Unix socket connections
        """
        # First check direct environment variable (for tests that patch os.environ)
        import os
        database_url = os.environ.get("DATABASE_URL", "")
        
        # If not found, try unified config
        if not database_url:
            try:
                config = get_unified_config()
                database_url = config.database_url or ""
            except Exception:
                pass  # Will return False below
        
        return "/cloudsql/" in database_url
    
    @staticmethod
    def is_local_development() -> bool:
        """Detect if running in local development.
        
        Returns:
            True if running in local development environment
        """
        current_env = get_current_environment()
        return current_env == "development"
    
    @staticmethod
    def is_remote_environment() -> bool:
        """Detect if running in staging/production.
        
        Returns:
            True if running in staging or production environment
        """
        current_env = get_current_environment()
        return current_env in ["staging", "production"]
    
    @staticmethod
    async def test_connection_with_retry(engine, max_retries: int = 3, delay: float = 1.0) -> bool:
        """Test database connection with retry logic and connection pool awareness.
        
        Args:
            engine: SQLAlchemy async engine
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Use a timeout to avoid hanging indefinitely
                async with asyncio.wait_for(engine.begin(), timeout=10.0) as conn:
                    await conn.execute("SELECT 1")
                    logger.debug(f"Database connection test successful on attempt {attempt + 1}")
                    return True
            except (OperationalError, DisconnectionError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} connection attempts failed: {e}")
        return False
    
    @staticmethod
    def get_pool_status(engine) -> dict:
        """Get connection pool status for monitoring.
        
        Args:
            engine: SQLAlchemy engine
            
        Returns:
            Dictionary with pool statistics
        """
        if hasattr(engine.pool, 'size'):
            return {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "invalid": engine.pool.invalid(),
            }
        return {"status": "Pool status unavailable"}
    
    @staticmethod
    async def create_user_with_rollback(user_data: dict) -> dict:
        """Create user with proper transaction rollback handling.
        
        FIX: Ensures complete rollback on failure to prevent partial user records.
        
        Args:
            user_data: User data dictionary with email, name, etc.
            
        Returns:
            Created user data or raises exception with cleanup
        """
        # Create async session from application engine
        async_session = DatabaseManager.get_application_session()
        
        async with async_session() as session:
            async with session.begin():
                try:
                    # Create user record using SQLAlchemy core
                    from sqlalchemy import text
                    user_result = await session.execute(
                        text("INSERT INTO users (email, name, created_at) VALUES (:email, :name, NOW()) RETURNING id"),
                        {"email": user_data.get("email"), "name": user_data.get("name")}
                    )
                    user_id = user_result.scalar()
                    
                    # Create associated profile if data provided
                    if user_data.get("profile_data"):
                        await session.execute(
                            text("INSERT INTO user_profiles (user_id, data, created_at) VALUES (:user_id, :data, NOW())"),
                            {"user_id": user_id, "data": user_data["profile_data"]}
                        )
                    
                    # Return complete user data
                    return {
                        "id": user_id,
                        "email": user_data.get("email"),
                        "name": user_data.get("name"),
                        "created_at": "now"
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to create user: {str(e)}")
                    # Transaction will be rolled back automatically
                    raise
    
    @staticmethod
    def _get_default_database_url() -> str:
        """Get default database URL for current environment.
        
        Returns:
            Default PostgreSQL URL based on environment
        """
        current_env = get_current_environment()
        
        if current_env == "development":
            return "postgresql://postgres:password@localhost:5432/netra"
        elif current_env == "testing":
            return "postgresql://postgres:password@localhost:5432/netra_test"
        else:
            # Staging/production should always have DATABASE_URL set
            logger.warning(f"No DATABASE_URL found for {current_env} environment")
            return "postgresql://postgres:password@localhost:5432/netra"
    
    # AUTH SERVICE COMPATIBILITY METHODS
    # These methods provide auth service compatibility without duplication
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async URL for auth service application (asyncpg).
        Alias for get_application_url_async() for auth service compatibility.
        
        Returns:
            Database URL compatible with asyncpg driver for auth service
        """
        return DatabaseManager.get_application_url_async()
    
    @staticmethod
    def get_auth_database_url() -> str:
        """Get base URL for auth service compatibility.
        Alias for get_base_database_url() for auth service compatibility.
        
        Returns:
            Clean database URL for auth service
        """
        return DatabaseManager.get_base_database_url()
    
    @staticmethod
    def get_auth_database_url_sync() -> str:
        """Get sync URL for auth service migrations.
        Alias for get_migration_url_sync_format() for auth service compatibility.
        
        Returns:
            Database URL compatible with synchronous drivers for auth service
        """
        return DatabaseManager.get_migration_url_sync_format()
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Confirm async driver compatibility for auth service.
        Alias for validate_application_url() for auth service compatibility.
        
        Args:
            url: Optional URL to validate, uses auth URL if None
            
        Returns:
            True if URL is async-compatible
        """
        target_url = url or DatabaseManager.get_auth_database_url_async()
        return DatabaseManager.validate_application_url(target_url)
    
    @staticmethod
    def validate_sync_url(url: str = None) -> bool:
        """Confirm sync driver compatibility for auth service.
        Alias for validate_migration_url_sync_format() for auth service compatibility.
        
        Args:
            url: Optional URL to validate, uses migration URL if None
            
        Returns:
            True if URL is sync-compatible
        """
        target_url = url or DatabaseManager.get_auth_database_url_sync()
        return DatabaseManager.validate_migration_url_sync_format(target_url)
    
    @staticmethod
    def is_test_environment() -> bool:
        """Detect if running in test environment.
        Auth service compatibility method.
        
        Returns:
            True if running in test environment
        """
        current_env = get_current_environment()
        is_test_mode = os.environ.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        
        # Check if we're in a pytest environment
        import sys
        is_pytest = 'pytest' in sys.modules or 'pytest' in ' '.join(sys.argv)
        
        return current_env in ["testing", "test"] or is_test_mode or is_pytest
    
    @staticmethod
    def create_auth_application_engine():
        """Return async SQLAlchemy engine for auth service.
        Alias for create_application_engine() for auth service compatibility.
        
        Returns:
            Async SQLAlchemy engine configured for auth service runtime
        """
        return DatabaseManager.create_application_engine()
    
    @staticmethod
    def get_auth_application_session():
        """Return async session factory for auth service runtime.
        Alias for get_application_session() for auth service compatibility.
        
        Returns:
            Async session factory for auth service operations
        """
        return DatabaseManager.get_application_session()
    
    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL format for consistency.
        Auth service compatibility method.
        
        Args:
            url: Database URL to normalize
            
        Returns:
            Normalized PostgreSQL URL
        """
        # Convert postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://")
        
        # Strip async driver prefixes for base URL
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        
        return url
    
    @staticmethod
    def _convert_sslmode_to_ssl(url: str) -> str:
        """Convert sslmode parameter to ssl parameter for asyncpg.
        Auth service compatibility method.
        
        Args:
            url: Database URL with sslmode parameter
            
        Returns:
            URL with ssl parameter for asyncpg compatibility
        """
        # Skip conversion for Cloud SQL connections
        if "/cloudsql/" in url:
            return url
        
        # Convert sslmode= to ssl= for asyncpg
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        
        return url
    
    @staticmethod
    def _get_default_auth_url() -> str:
        """Get default database URL for auth service.
        Auth service compatibility method.
        
        Returns:
            Default database URL for auth service based on environment
        """
        current_env = get_current_environment()
        
        if current_env == "development":
            return "postgresql://postgres:password@localhost:5432/netra"
        elif current_env in ["testing", "test"]:
            return "sqlite:///:memory:"
        else:
            # Staging/production should always have DATABASE_URL set
            logger.warning(f"No DATABASE_URL found for auth service in {current_env} environment")
            return "postgresql://postgres:password@localhost:5432/netra"


# Export the main class
__all__ = ["DatabaseManager"]