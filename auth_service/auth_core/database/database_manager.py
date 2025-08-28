"""
Auth Service Database Manager - Service-Specific Extensions
Provides auth-specific database functionality while delegating core operations to canonical DatabaseManager

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: SSOT compliance with service-specific extensions
- Value Impact: Eliminates SSOT violations while preserving auth-specific functionality
- Strategic Impact: Maintains service independence through proper delegation patterns
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
    """Auth service database manager - delegates core operations to canonical DatabaseManager"""
    
    @staticmethod
    def convert_database_url(url: str) -> str:
        """Convert between database URL formats - auth service standalone implementation"""
        # Auth service must be completely independent - NEVER import from netra_backend
        if not url:
            return url
            
        # Use DatabaseURLBuilder directly for URL conversion
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Create a temporary environment dict for URL builder
        temp_env = get_env().get_all()
        temp_env['DATABASE_URL'] = url
        builder = DatabaseURLBuilder(temp_env)
        
        # Format for asyncpg driver
        return builder.format_url_for_driver(url, 'asyncpg')
    
    @classmethod
    def create_async_engine(
        cls,
        database_url: Optional[str] = None,
        **kwargs
    ) -> AsyncEngine:
        """Create an async SQLAlchemy engine for auth service"""
        
        # Auth service creates its own engine independently
        if not database_url:
            database_url = cls.get_auth_database_url_async()
        
        try:
            # Create engine with auth-specific configuration
            engine = create_async_engine(
                database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={
                    "server_settings": {"jit": "off"},
                    "command_timeout": 60,
                }
            )
            logger.info("Successfully created async engine for auth service")
            return engine
        except Exception as e:
            logger.error(f"Failed to create async engine for auth service: {e}")
            raise
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async URL for auth service"""
        # Get database URL from AuthSecretLoader
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        database_url = AuthSecretLoader.get_database_url()
        
        if not database_url:
            raise ValueError("Database URL not configured for auth service")
        
        # Ensure it's properly formatted for async
        return AuthDatabaseManager._normalize_database_url(database_url)
    
    @staticmethod
    def get_auth_database_url() -> str:
        """Get sync database URL for auth service"""
        # Get database URL from AuthSecretLoader in sync format
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        database_url = AuthSecretLoader.get_database_url()
        
        if not database_url:
            raise ValueError("Database URL not configured for auth service")
        
        # Convert to sync format and normalize
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return AuthDatabaseManager._normalize_database_url(sync_url)
    
    @staticmethod
    def get_auth_database_url_sync() -> str:
        """Get sync database URL for auth service (alias for compatibility)"""
        return AuthDatabaseManager.get_auth_database_url()
    
    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        """Normalize database URL format for auth service"""
        if not database_url:
            return database_url
        
        # Use DatabaseURLBuilder for consistent normalization
        from shared.database_url_builder import DatabaseURLBuilder
        return DatabaseURLBuilder.normalize_postgres_url(database_url)
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Validate auth URL"""
        if not url:
            return False
        
        # Basic validation
        return url.startswith(('postgresql://', 'postgresql+asyncpg://'))
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Check if running in Cloud SQL environment"""
        from auth_service.auth_core.isolated_environment import get_env
        env = get_env().get("ENVIRONMENT", "development").lower()
        return env in ["staging", "production"]
    
    @staticmethod
    def is_test_environment() -> bool:
        """Check if running in test environment"""
        from auth_service.auth_core.isolated_environment import get_env
        env = get_env().get("ENVIRONMENT", "development").lower()
        return env == "test" or get_env().get("AUTH_FAST_TEST_MODE") == "true"
    
    @staticmethod
    def get_connection_url() -> str:
        """Get normalized connection URL for auth service - delegates to canonical DatabaseManager"""
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
        """Get base database URL - auth service standalone implementation"""
        # Auth service must be completely independent
        return AuthDatabaseManager.get_auth_database_url()
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get sync URL for migrations - auth service standalone implementation"""
        # Auth service must be completely independent
        return AuthDatabaseManager.get_auth_database_url_sync()
    
    @staticmethod
    def validate_base_url() -> bool:
        """Validate base URL - auth service standalone implementation"""
        # Auth service must be completely independent
        url = AuthDatabaseManager.get_auth_database_url()
        return bool(url and url.startswith('postgresql'))
    
    @staticmethod
    def validate_migration_url_sync_format(url: str = None) -> bool:
        """Validate sync URL - auth service standalone implementation"""
        # Auth service must be completely independent
        if not url:
            url = AuthDatabaseManager.get_auth_database_url_sync()
        return bool(url and url.startswith('postgresql'))
    
    @staticmethod
    def is_local_development() -> bool:
        """Check if local development - auth service standalone implementation"""
        # Auth service must be completely independent
        from auth_service.auth_core.config import AuthConfig
        env = AuthConfig.get_environment()
        return env in ('local', 'development', 'test')
    
    @staticmethod
    def is_remote_environment() -> bool:
        """Check if remote environment - auth service standalone implementation"""
        # Auth service must be completely independent
        from auth_service.auth_core.config import AuthConfig
        env = AuthConfig.get_environment()
        return env in ('staging', 'production')
    
    @staticmethod
    def get_pool_status(engine) -> dict:
        """Get pool status - auth service standalone implementation"""
        # Auth service must be completely independent
        if hasattr(engine, 'pool'):
            pool = engine.pool
            return {
                'size': pool.size() if hasattr(pool, 'size') else 0,
                'checked_in_connections': pool.checkedin() if hasattr(pool, 'checkedin') else 0,
                'overflow': pool.overflow() if hasattr(pool, 'overflow') else 0,
                'total': pool.total() if hasattr(pool, 'total') else 0
            }
        return {'status': 'unknown'}
    
    def _handle_pool_exhaustion(self):
        """Handle database connection pool exhaustion scenarios.
        
        This method is intentionally designed to raise an exception to expose
        the lack of proper pool exhaustion handling in the current implementation.
        
        Raises:
            Exception: Always raises to indicate pool exhaustion scenario
        """
        logger.error("Connection pool exhaustion detected - no recovery mechanism implemented")
        raise Exception("Connection pool exhausted")