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
from auth_service.auth_core.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Independent database manager for auth service"""
    
    @staticmethod
    def convert_database_url(url: str) -> str:
        """Convert between database URL formats if needed"""
        if not url:
            return url
        
        # ONLY use centralized DatabaseURLBuilder - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        # Normalize URL first, then format for asyncpg
        url = DatabaseURLBuilder.normalize_postgres_url(url)
        url = DatabaseURLBuilder.format_url_for_driver(url, 'asyncpg')
        return url
    
    @classmethod
    def create_async_engine(
        cls,
        database_url: Optional[str] = None,
        **kwargs
    ) -> AsyncEngine:
        """Create an async SQLAlchemy engine with auth-specific configuration"""
        
        # Get database URL from environment if not provided
        if not database_url:
            database_url = get_env().get("DATABASE_URL")
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
        if get_env().get("TESTING") == "true":
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
        database_url = get_env().get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        logger.debug(f"Converting database URL for async: {database_url[:20]}...")
        
        # ONLY use centralized DatabaseURLBuilder - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        # Normalize and format for asyncpg in one step
        converted_url = DatabaseURLBuilder.format_url_for_driver(database_url, 'asyncpg')
        
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
            url = get_env().get("DATABASE_URL")
        
        if not url:
            logger.warning("No database URL to validate")
            return False
        
        # First check if this is a test environment URL (SQLite)
        if url.startswith("sqlite"):
            logger.debug("SQLite URL detected - not valid for production auth service")
            return False
        
        # ONLY use DatabaseURLBuilder for validation - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        is_valid, error_msg = DatabaseURLBuilder.validate_url_for_driver(url, 'asyncpg')
        
        if is_valid:
            logger.debug(f"Database URL validation passed: {url[:20]}...")
        else:
            logger.warning(f"Invalid database URL: {error_msg}")
        
        return is_valid
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Check if running in Cloud SQL environment.
        
        Returns:
            True if using Cloud SQL or running in Cloud Run
        """
        # Check if DATABASE_URL contains Cloud SQL Unix socket path
        database_url = get_env().get("DATABASE_URL", "")
        try:
            from shared.database.core_database_manager import CoreDatabaseManager
            if CoreDatabaseManager.is_cloud_sql_connection(database_url):
                logger.debug("Detected Cloud SQL environment from DATABASE_URL")
                return True
        except ImportError:
            # Fallback check
            if "/cloudsql/" in database_url:
                logger.debug("Detected Cloud SQL environment from DATABASE_URL (fallback)")
                return True
        
        # Check if running in Cloud Run (K_SERVICE is set by Cloud Run)
        k_service = get_env().get("K_SERVICE")
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
        environment = get_env().get("ENVIRONMENT", "").lower()
        if environment == "test":
            return True
        
        testing_flag = get_env().get("TESTING", "false").lower()
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
        try:
            from shared.database.core_database_manager import CoreDatabaseManager
            environment = CoreDatabaseManager.get_environment_type()
            return CoreDatabaseManager.get_default_url_for_environment(environment)
        except ImportError:
            # Fallback default URL
            return "postgresql://postgres:password@localhost:5432/netra_auth"
    
    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL using shared DatabaseURLBuilder."""
        # ONLY use centralized DatabaseURLBuilder - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        # Normalize and format for asyncpg driver (auth service needs async URLs)
        normalized = DatabaseURLBuilder.normalize_postgres_url(url)
        return DatabaseURLBuilder.format_url_for_driver(normalized, 'asyncpg')
    
    @staticmethod
    def _convert_sslmode_to_ssl(url: str) -> str:
        """Convert sslmode parameter using shared CoreDatabaseManager."""
        try:
            from shared.database.core_database_manager import CoreDatabaseManager
            return CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)
        except ImportError:
            # Fallback SSL parameter conversion with proper asyncpg handling
            if "sslmode=" in url:
                # Convert common sslmode values to asyncpg-compatible ssl parameter
                ssl_conversions = {
                    "sslmode=require": "ssl=require",
                    "sslmode=prefer": "ssl=prefer", 
                    "sslmode=allow": "ssl=allow",
                    "sslmode=disable": "ssl=disable"
                }
                for sslmode, ssl_param in ssl_conversions.items():
                    if sslmode in url:
                        url = url.replace(sslmode, ssl_param)
                        break
                # Remove any remaining sslmode parameters that weren't converted
                import re
                url = re.sub(r'[?&]sslmode=[^&]*', '', url)
            return url
    
    @staticmethod
    def _normalize_database_url(url: str) -> str:
        """Normalize database URL using shared CoreDatabaseManager."""
        try:
            from shared.database.core_database_manager import CoreDatabaseManager
            resolved_url = CoreDatabaseManager.resolve_ssl_parameter_conflicts(url, "asyncpg")
            return CoreDatabaseManager.format_url_for_async_driver(resolved_url)
        except ImportError:
            # Fallback normalization
            return AuthDatabaseManager.convert_database_url(url)
    
    @staticmethod
    def get_connection_url() -> str:
        """Get normalized connection URL for auth service.
        
        Returns:
            Database URL ready for asyncpg connection
        """
        return AuthDatabaseManager.get_auth_database_url_async()
    
    @staticmethod
    def validate_staging_readiness() -> bool:
        """Validate auth service database configuration for staging deployment.
        
        Performs comprehensive validation including:
        - Database URL format and SSL parameter handling
        - Credential validation through IsolatedEnvironment
        - Cloud SQL compatibility checks
        
        Returns:
            True if ready for staging deployment
        """
        try:
            from auth_service.auth_core.database.staging_validation import StagingDatabaseValidator
            from auth_service.auth_core.isolated_environment import get_env
            
            logger.info("Validating auth service for staging deployment...")
            
            # First validate credentials through IsolatedEnvironment
            env_manager = get_env()
            credential_validation = env_manager.validate_staging_database_credentials()
            
            if not credential_validation["valid"]:
                logger.error("Staging credential validation failed:")
                for issue in credential_validation.get("issues", []):
                    logger.error(f"  - {issue}")
                return False
            
            # Log any warnings from credential validation
            for warning in credential_validation.get("warnings", []):
                logger.warning(f"  - {warning}")
            
            # Then validate URL format and deployment readiness
            report = StagingDatabaseValidator.pre_deployment_validation()
            
            if report["overall_status"] == "failed":
                logger.error("Staging URL/deployment validation failed:")
                for issue in report.get("critical_issues", []):
                    logger.error(f"  - {issue}")
                return False
            elif report["overall_status"] == "warning":
                logger.warning("Staging validation passed with warnings:")
                for warning in report.get("warnings", []):
                    logger.warning(f"  - {warning}")
            else:
                logger.info("Staging validation passed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Staging validation failed with error: {e}")
            return False
    
    @staticmethod
    def validate_database_credentials_for_environment(environment: str = None) -> dict:
        """Validate database credentials for the specified environment.
        
        Args:
            environment: Target environment (staging, production, development)
            
        Returns:
            Dictionary with validation results
        """
        from auth_service.auth_core.isolated_environment import get_env
        
        env_manager = get_env()
        current_env = environment or env_manager.get("ENVIRONMENT", "development").lower()
        
        if current_env == "staging":
            return env_manager.validate_staging_database_credentials()
        else:
            # Basic validation for non-staging environments
            validation_result = {
                "valid": True,
                "issues": [],
                "warnings": []
            }
            
            # Check basic database variables are present
            required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
            missing_vars = []
            
            for var in required_vars:
                if not env_manager.get(var):
                    missing_vars.append(var)
            
            if missing_vars:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Missing required database variables for {current_env}: {missing_vars}")
            
            return validation_result
    
    @staticmethod
    def get_base_database_url() -> str:
        """Get base PostgreSQL URL without driver prefixes.
        
        Returns:
            Clean PostgreSQL URL without asyncpg/psycopg2 drivers
        """
        database_url = get_env().get("DATABASE_URL", "")
        if not database_url:
            return AuthDatabaseManager._get_default_auth_url()
        
        # ONLY use centralized DatabaseURLBuilder - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        # Normalize the URL
        normalized = DatabaseURLBuilder.normalize_postgres_url(database_url)
        # Format for base driver (removes driver prefixes)
        normalized = DatabaseURLBuilder.format_url_for_driver(normalized, 'base')
        
        return normalized
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get synchronous URL for migrations (Alembic).
        
        Returns:
            Database URL compatible with psycopg2 driver
        """
        base_url = AuthDatabaseManager.get_base_database_url()
        
        # ONLY use DatabaseURLBuilder - NO FALLBACKS
        from shared.database_url_builder import DatabaseURLBuilder
        # Format for psycopg2 driver (used by Alembic)
        base_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'psycopg2')
        
        return base_url
    
    @staticmethod
    def validate_base_url() -> bool:
        """Validate base database URL is clean.
        
        Returns:
            True if base URL is properly formatted
        """
        base_url = AuthDatabaseManager.get_base_database_url()
        
        # Should not contain driver prefixes
        if "+asyncpg" in base_url or "+psycopg" in base_url:
            return False
            
        # Should be valid PostgreSQL URL
        return base_url.startswith("postgresql://") or base_url.startswith("sqlite://")
    
    @staticmethod
    def validate_migration_url_sync_format(url: str = None) -> bool:
        """Validate migration URL is synchronous.
        
        Args:
            url: Optional URL to validate, uses migration URL if None
            
        Returns:
            True if URL is compatible with synchronous drivers
        """
        if url is None:
            url = AuthDatabaseManager.get_migration_url_sync_format()
        
        # Should not contain async drivers
        if "+asyncpg" in url:
            return False
            
        # Should be PostgreSQL URL (plain or with psycopg2 driver)
        return url.startswith("postgresql://") or url.startswith("postgresql+psycopg2://")
    
    @staticmethod
    def is_local_development() -> bool:
        """Check if running in local development environment.
        
        Returns:
            True if running in local development
        """
        # Direct environment check - no fallbacks
        environment = get_env().get("ENVIRONMENT", "development").lower()
        return environment == "development"
    
    @staticmethod
    def is_remote_environment() -> bool:
        """Check if running in remote environment (staging/production).
        
        Returns:
            True if running in staging or production
        """
        # Direct environment check - no fallbacks
        environment = get_env().get("ENVIRONMENT", "development").lower()
        return environment in ["staging", "production"]
    
    @staticmethod
    def get_pool_status(engine) -> dict:
        """Get database connection pool status.
        
        Args:
            engine: SQLAlchemy engine
            
        Returns:
            Dictionary with pool statistics
        """
        if not engine or not hasattr(engine, 'pool'):
            return {
                "pool_size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "invalid": 0
            }
        
        pool = engine.pool
        return {
            "pool_size": getattr(pool, 'size', lambda: 0)(),
            "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
            "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
            "overflow": getattr(pool, 'overflow', lambda: 0)(),
            "invalid": getattr(pool, 'invalid', lambda: 0)()
        }
    
    def _handle_pool_exhaustion(self):
        """Handle database connection pool exhaustion scenarios.
        
        This method is intentionally designed to raise an exception to expose
        the lack of proper pool exhaustion handling in the current implementation.
        
        Raises:
            Exception: Always raises to indicate pool exhaustion scenario
        """
        logger.error("Connection pool exhaustion detected - no recovery mechanism implemented")
        raise Exception("Connection pool exhausted")