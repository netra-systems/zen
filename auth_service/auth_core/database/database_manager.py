"""
Auth Service Database Manager - Independent Implementation
Manages database connections for auth service without external dependencies

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Microservice independence and reliability
- Value Impact: Isolated auth service, reduced coupling, improved stability
- Strategic Impact: Enables independent scaling and deployment of auth service
"""
import os
import sys
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from shared.database.core_database_manager import CoreDatabaseManager

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Independent database manager for auth service"""
    
    @staticmethod
    def convert_database_url(url: str) -> str:
        """Convert between database URL formats if needed"""
        if not url:
            return url
        
        # Use shared core database manager for URL conversion
        return CoreDatabaseManager.format_url_for_async_driver(url)
    
    @classmethod
    def create_async_engine(
        cls,
        database_url: Optional[str] = None,
        **kwargs
    ) -> AsyncEngine:
        """Create an async SQLAlchemy engine with auth-specific configuration"""
        
        # Get database URL from environment if not provided
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not configured")
        
        # Convert URL format if needed
        async_url = cls.convert_database_url(database_url)
        
        # Default configuration for auth service
        default_config = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": False,
            "future": True,
            "poolclass": AsyncAdaptedQueuePool,
        }
        
        # Testing environment uses NullPool
        if os.getenv("TESTING") == "true":
            default_config["poolclass"] = NullPool
            default_config.pop("pool_size", None)
            default_config.pop("max_overflow", None)
        
        # Merge with provided kwargs
        config = {**default_config, **kwargs}
        
        # Remove pool settings if using NullPool
        if config.get("poolclass") == NullPool:
            for key in ["pool_size", "max_overflow", "pool_timeout", "pool_recycle"]:
                config.pop(key, None)
        
        logger.info(f"Creating async engine for auth service with config: {config}")
        
        try:
            engine = create_async_engine(async_url, **config)
            logger.info("Successfully created async engine for auth service")
            return engine
        except Exception as e:
            logger.error(f"Failed to create async engine: {e}")
            raise
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async URL for auth service application (asyncpg).
        
        Returns:
            Database URL compatible with asyncpg driver
        """
        # Get DATABASE_URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        logger.debug(f"Converting database URL for async: {database_url[:20]}...")
        
        # CRITICAL FIX: Resolve SSL parameter conflicts first (staging deployment issue)
        resolved_url = CoreDatabaseManager.resolve_ssl_parameter_conflicts(database_url, "asyncpg")
        
        # Use shared core database manager for URL conversion
        converted_url = CoreDatabaseManager.format_url_for_async_driver(resolved_url)
        
        logger.debug(f"Converted async database URL: {converted_url[:20]}...")
        return converted_url
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Validate the database URL for auth service.
        
        Args:
            url: Optional URL to validate, uses DATABASE_URL if None
            
        Returns:
            True if URL is valid PostgreSQL URL, False otherwise
        """
        if url is None:
            url = os.getenv("DATABASE_URL")
        
        if not url:
            logger.warning("No database URL to validate")
            return False
        
        try:
            # Use shared core database manager for validation
            is_valid = CoreDatabaseManager.validate_database_url(url)
            
            if is_valid:
                logger.debug(f"Database URL validation passed: {url[:20]}...")
            else:
                logger.warning(f"Invalid database URL: {url[:20]}...")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return False
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Check if running in Cloud SQL environment.
        
        Returns:
            True if using Cloud SQL or running in Cloud Run
        """
        # Check if DATABASE_URL contains Cloud SQL Unix socket path
        database_url = os.getenv("DATABASE_URL", "")
        if CoreDatabaseManager.is_cloud_sql_connection(database_url):
            logger.debug("Detected Cloud SQL environment from DATABASE_URL")
            return True
        
        # Check if running in Cloud Run (K_SERVICE is set by Cloud Run)
        k_service = os.getenv("K_SERVICE")
        if k_service:
            logger.debug(f"Detected Cloud Run environment: {k_service}")
            return True
        
        return False
    
    @staticmethod
    def is_test_environment() -> bool:
        """Check if running in test environment.
        
        Returns:
            True if running in test environment
        """
        # Check environment variables
        environment = os.getenv("ENVIRONMENT", "").lower()
        if environment == "test":
            return True
        
        testing_flag = os.getenv("TESTING", "false").lower()
        if testing_flag == "true":
            return True
        
        # Check if pytest is in sys.modules
        if 'pytest' in sys.modules:
            logger.debug("Detected pytest in sys.modules")
            return True
        
        return False
    
    @staticmethod
    def _get_default_auth_url() -> str:
        """Get default database URL for auth service based on environment.
        
        Returns:
            Default database URL for the current environment
        """
        environment = CoreDatabaseManager.get_environment_type()
        return CoreDatabaseManager.get_default_url_for_environment(environment)
    
    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL format for consistency.
        
        Args:
            url: Database URL to normalize
            
        Returns:
            Normalized PostgreSQL URL
        """
        return CoreDatabaseManager.normalize_postgres_url(url)
    
    @staticmethod
    def _convert_sslmode_to_ssl(url: str) -> str:
        """Convert sslmode parameter to ssl parameter for asyncpg.
        
        Args:
            url: Database URL with sslmode parameter
            
        Returns:
            URL with ssl parameter for asyncpg compatibility
        """
        return CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)