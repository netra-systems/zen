from shared.isolated_environment import get_env
"""
Core Database Manager - Universal database connectivity
Handles driver compatibility and SSL parameter resolution across all services

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational Excellence and Reliability
- Value Impact: 100% database connectivity success rate
- Strategic Impact: Zero SSL parameter conflicts across all environments
"""
import re
import os
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class CoreDatabaseManager:
    """Centralized database URL management and driver compatibility"""
    
    @staticmethod
    def resolve_ssl_parameter_conflicts(url: str, target_driver: str = "auto") -> str:
        """Resolve SSL parameter conflicts between database drivers.
        
        Args:
            url: Database URL with potential SSL parameter conflicts
            target_driver: Target driver (asyncpg, psycopg2, or auto)
            
        Returns:
            URL with resolved SSL parameters for the target driver
        """
        if not url:
            return url
        
        # Unix socket connections - no SSL parameters needed
        if '/cloudsql/' in url:
            url = re.sub(r'[?&]ssl(mode)?=[^&]*', '', url)
            # Clean up any resulting double ampersands or trailing ? or &
            url = re.sub(r'[?&]$', '', url)
            url = re.sub(r'&&+', '&', url)
            logger.debug(f"Removed SSL parameters for Cloud SQL connection")
            return url
        
        # Auto-detect driver from URL
        if target_driver == "auto":
            if 'asyncpg' in url:
                target_driver = "asyncpg"
            elif 'psycopg2' in url or url.startswith('postgresql://'):
                target_driver = "psycopg2"
            else:
                target_driver = "asyncpg"  # Default for async operations
        
        # Driver-specific SSL parameter handling
        if target_driver == "asyncpg":
            # asyncpg uses ssl= parameter
            url = url.replace('sslmode=', 'ssl=')
        elif target_driver == "psycopg2":
            # psycopg2 uses sslmode= parameter
            url = url.replace('ssl=', 'sslmode=')
        
        logger.debug(f"Resolved SSL parameters for {target_driver} driver")
        return url
    
    @staticmethod
    def format_url_for_async_driver(url: str) -> str:
        """Format URL for async (asyncpg) driver.
        
        Args:
            url: Base database URL
            
        Returns:
            URL formatted for asyncpg driver
        """
        if not url:
            return url
        
        # Normalize the URL first
        normalized = CoreDatabaseManager.normalize_postgres_url(url)
        
        # Add asyncpg driver if not present
        if normalized.startswith("postgresql://") and "+asyncpg" not in normalized:
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://")
        
        # Apply SSL parameter resolution
        return CoreDatabaseManager.resolve_ssl_parameter_conflicts(normalized, "asyncpg")
    
    @staticmethod
    def format_url_for_sync_driver(url: str) -> str:
        """Format URL for sync (psycopg2) driver.
        
        Args:
            url: Base database URL
            
        Returns:
            URL formatted for psycopg2 driver
        """
        if not url:
            return url
        
        # Normalize the URL first
        normalized = CoreDatabaseManager.normalize_postgres_url(url)
        
        # Remove async driver if present
        normalized = normalized.replace("+asyncpg", "")
        
        # Ensure it starts with postgresql://
        if not normalized.startswith("postgresql://"):
            if normalized.startswith("postgres://"):
                normalized = normalized.replace("postgres://", "postgresql://")
        
        # Apply SSL parameter resolution
        return CoreDatabaseManager.resolve_ssl_parameter_conflicts(normalized, "psycopg2")
    
    @staticmethod
    def normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL format.
        
        Args:
            url: Raw database URL
            
        Returns:
            Normalized PostgreSQL URL
        """
        if not url:
            return url
        
        # Convert postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://")
        
        return url
    
    @staticmethod
    def is_cloud_sql_connection(url: str) -> bool:
        """Check if URL is a Cloud SQL Unix socket connection.
        
        Args:
            url: Database URL to check
            
        Returns:
            True if URL contains Cloud SQL Unix socket path
        """
        return "/cloudsql/" in url if url else False
    
    @staticmethod
    def validate_database_url(url: str) -> bool:
        """Validate database URL format.
        
        Args:
            url: Database URL to validate
            
        Returns:
            True if URL is valid PostgreSQL format
        """
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            valid_schemes = [
                "postgresql", "postgres", 
                "postgresql+asyncpg", "postgres+asyncpg",
                "postgresql+psycopg2", "postgres+psycopg2",
                "sqlite", "sqlite+aiosqlite"
            ]
            
            if parsed.scheme not in valid_schemes:
                return False
            
            # For PostgreSQL, check basic structure
            if parsed.scheme.startswith(("postgresql", "postgres")):
                # Host is optional for Unix socket connections
                if not CoreDatabaseManager.is_cloud_sql_connection(url):
                    if not parsed.hostname and not parsed.path.startswith("/"):
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"URL validation error: {e}")
            return False
    
    @staticmethod
    def get_environment_type() -> str:
        """Get current environment type.
        
        Returns:
            Environment type (development, staging, production)
        """
        # Check various environment indicators
        env_var = get_env().get("ENVIRONMENT", "").lower()
        if env_var:
            return env_var
        
        netra_env = get_env().get("NETRA_ENVIRONMENT", "").lower()
        if netra_env:
            return netra_env
        
        # Check if running in Cloud Run (indicates staging/production)
        if get_env().get("K_SERVICE"):
            return "production"  # Default for Cloud Run
        
        # Check Cloud SQL indicators
        database_url = get_env().get("DATABASE_URL", "")
        if CoreDatabaseManager.is_cloud_sql_connection(database_url):
            return "staging"  # Likely staging if using Cloud SQL
        
        # Default to development
        return "development"
    
    @staticmethod
    def get_default_url_for_environment(environment: str) -> str:
        """Get default database URL for environment.
        
        Args:
            environment: Environment type
            
        Returns:
            Default database URL for the environment
        """
        if environment == "production":
            return "postgresql://netra:password@/netra?host=/cloudsql/netra-production:us-central1:netra-db"
        elif environment == "staging":
            return "postgresql://netra:password@/netra?host=/cloudsql/netra-staging:us-central1:netra-db"
        else:  # development
            return "postgresql://netra:netra123@localhost:5433/netra_dev"
    
    @staticmethod
    def convert_ssl_params_for_asyncpg(url: str) -> str:
        """Convert SSL parameters for asyncpg compatibility.
        
        Args:
            url: Database URL with SSL parameters
            
        Returns:
            URL with SSL parameters converted for asyncpg
        """
        return CoreDatabaseManager.resolve_ssl_parameter_conflicts(url, "asyncpg")
    
    @staticmethod
    def get_migration_compatible_url(url: str) -> str:
        """Get migration-compatible (sync) version of URL.
        
        Args:
            url: Base database URL
            
        Returns:
            URL compatible with Alembic migrations
        """
        return CoreDatabaseManager.format_url_for_sync_driver(url)
    
    @staticmethod
    def get_application_compatible_url(url: str) -> str:
        """Get application-compatible (async) version of URL.
        
        Args:
            url: Base database URL
            
        Returns:
            URL compatible with async operations
        """
        return CoreDatabaseManager.format_url_for_async_driver(url)


# Export main class
__all__ = ["CoreDatabaseManager"]
