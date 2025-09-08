"""
Auth Database Manager
Simple implementation to support auth service database operations
Uses shared DatabaseURLBuilder for consistent URL construction
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Simple database manager for auth service"""
    
    @staticmethod
    def create_async_engine(**kwargs) -> AsyncEngine:
        """Create async database engine using shared URL builder"""
        database_url = AuthDatabaseManager.get_database_url()
        
        if not database_url:
            raise ValueError("No database URL available - check configuration")
        
        logger.info(f"Creating async database engine for auth service")
        logger.info(f"Database URL: {DatabaseURLBuilder.mask_url_for_logging(database_url)}")
        
        # Create engine with simple configuration
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=False,
            **kwargs
        )
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL for auth service using shared URL builder"""
        env = get_env()
        
        # Check for fast test mode - use in-memory SQLite
        fast_test_mode = env.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        environment = env.get("ENVIRONMENT", "development").lower()
        
        if fast_test_mode:
            logger.info("AUTH_FAST_TEST_MODE enabled - using file-based SQLite database for test isolation")
            # Use a temporary file-based SQLite database to ensure shared state across sessions
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            db_file = os.path.join(temp_dir, f"auth_service_test_{os.getpid()}.db")
            return f"sqlite+aiosqlite:///{db_file}"
        
        logger.debug(f"AUTH_FAST_TEST_MODE={fast_test_mode}, ENVIRONMENT={environment}")
        
        # Build environment variables dict for DatabaseURLBuilder
        env_vars = {
            "ENVIRONMENT": environment,
            "POSTGRES_HOST": env.get("POSTGRES_HOST"),
            "POSTGRES_PORT": env.get("POSTGRES_PORT"),
            "POSTGRES_DB": env.get("POSTGRES_DB"),
            "POSTGRES_USER": env.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD")
        }
        
        # Create URL builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            logger.error(f"Database configuration validation failed: {error_msg}")
            # NO MANUAL FALLBACKS - DatabaseURLBuilder is the SINGLE SOURCE OF TRUTH
            environment = env_vars.get("ENVIRONMENT", "development")
            raise ValueError(
                f"Database configuration error in {environment} environment: {error_msg}. "
                f"DatabaseURLBuilder must be able to construct a valid URL. "
                f"Check your environment variables."
            )
        
        # Get URL for current environment
        database_url = builder.get_url_for_environment(sync=False)
        
        if not database_url:
            # NO MANUAL FALLBACKS - DatabaseURLBuilder is the SINGLE SOURCE OF TRUTH
            environment = env_vars.get("ENVIRONMENT", "development")
            debug_info = builder.debug_info()
            logger.error(f"No database URL generated for {environment} environment. Debug info: {debug_info}")
            raise ValueError(
                f"DatabaseURLBuilder failed to generate URL for {environment} environment. "
                f"Ensure proper POSTGRES_* environment variables are configured. "
                f"Debug info: {debug_info}"
            )
        
        # Log safe connection info
        logger.info(builder.get_safe_log_message())
        return database_url