"""
Core Database Manager - Shared Database Utilities

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Single Source of Truth for database URL handling and SSL configuration
- Value Impact: Eliminates triple duplication, reduces maintenance burden, ensures consistency
- Strategic Impact: Enables microservice independence while sharing common database logic

This module provides the core database URL parsing, SSL handling, and environment detection
functionality that is shared across all services in the Netra platform.

Key functionality:
- Database URL normalization and conversion
- SSL parameter handling (asyncpg vs psycopg2 differences)
- Cloud SQL Unix socket detection
- Environment-specific URL generation
- Driver-specific URL formatting

Each function ≤25 lines, class ≤200 lines total.
"""

import os
import re
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class CoreDatabaseManager:
    """Shared core database utilities for URL handling and SSL configuration."""
    
    @staticmethod
    def normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL format for consistency.
        
        Converts postgres:// to postgresql:// and removes async driver prefixes.
        
        Args:
            url: Database URL to normalize
            
        Returns:
            Normalized PostgreSQL URL
        """
        if not url:
            return url
            
        # Convert postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://")
        
        # Strip async driver prefixes for base URL
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        
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
    def convert_ssl_params_for_asyncpg(url: str) -> str:
        """Convert SSL parameters for asyncpg compatibility.
        
        Converts sslmode= to ssl= for asyncpg driver.
        Removes SSL parameters entirely for Cloud SQL connections.
        
        Args:
            url: Database URL with SSL parameters
            
        Returns:
            URL with SSL parameters converted for asyncpg
        """
        if not url:
            return url
            
        # For Cloud SQL Unix socket connections, remove ALL SSL parameters
        if CoreDatabaseManager.is_cloud_sql_connection(url):
            # Remove both sslmode and ssl parameters
            url = re.sub(r'[&?]sslmode=[^&]*', '', url)
            url = re.sub(r'[&?]ssl=[^&]*', '', url)
            # Clean up any double ampersands or trailing ampersands
            url = re.sub(r'&&+', '&', url)
            url = re.sub(r'[&?]$', '', url)
        else:
            # For non-Cloud SQL connections, convert sslmode to ssl
            if "sslmode=require" in url:
                url = url.replace("sslmode=require", "ssl=require")
            elif "sslmode=" in url:
                # Remove other sslmode parameters that asyncpg doesn't understand
                url = re.sub(r'[&?]sslmode=[^&]*', '', url)
        
        return url
    
    @staticmethod
    def convert_ssl_params_for_psycopg2(url: str) -> str:
        """Convert SSL parameters for psycopg2 compatibility.
        
        Converts ssl= to sslmode= for psycopg2 driver.
        Removes SSL parameters entirely for Cloud SQL connections.
        
        Args:
            url: Database URL with SSL parameters
            
        Returns:
            URL with SSL parameters converted for psycopg2
        """
        if not url:
            return url
            
        # For Cloud SQL Unix socket connections, remove ALL SSL parameters
        if CoreDatabaseManager.is_cloud_sql_connection(url):
            # Remove both sslmode and ssl parameters
            url = re.sub(r'[&?]sslmode=[^&]*', '', url)
            url = re.sub(r'[&?]ssl=[^&]*', '', url)
        else:
            # For non-Cloud SQL connections, convert ssl to sslmode
            if "ssl=" in url:
                url = url.replace("ssl=", "sslmode=")
        
        return url
    
    @staticmethod
    def format_url_for_async_driver(url: str) -> str:
        """Format URL for async database driver (asyncpg).
        
        Args:
            url: Base database URL
            
        Returns:
            URL formatted for asyncpg with postgresql+asyncpg:// prefix
        """
        if not url:
            return url
        
        # Normalize first
        clean_url = CoreDatabaseManager.normalize_postgres_url(url)
        
        # Add async driver prefix
        if clean_url.startswith("postgresql://"):
            clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Convert SSL parameters for asyncpg
        clean_url = CoreDatabaseManager.convert_ssl_params_for_asyncpg(clean_url)
        
        return clean_url
    
    @staticmethod
    def format_url_for_sync_driver(url: str) -> str:
        """Format URL for sync database driver (psycopg2).
        
        Args:
            url: Base database URL
            
        Returns:
            URL formatted for psycopg2 with postgresql:// prefix
        """
        if not url:
            return url
        
        # Normalize and ensure sync driver
        clean_url = CoreDatabaseManager.normalize_postgres_url(url)
        
        # Convert SSL parameters for psycopg2
        clean_url = CoreDatabaseManager.convert_ssl_params_for_psycopg2(clean_url)
        
        return clean_url
    
    @staticmethod
    def get_database_url_from_env(var_name: str = "DATABASE_URL") -> str:
        """Get database URL from environment variable.
        
        Args:
            var_name: Environment variable name to check
            
        Returns:
            Database URL from environment
            
        Raises:
            ValueError: If environment variable is not set
        """
        url = os.getenv(var_name)
        if not url:
            raise ValueError(f"{var_name} environment variable not set")
        return url
    
    @staticmethod
    def validate_database_url(url: str) -> bool:
        """Validate database URL format.
        
        Args:
            url: Database URL to validate
            
        Returns:
            True if URL has valid PostgreSQL format
        """
        if not url:
            return False
        
        try:
            # Accept multiple PostgreSQL schemes
            valid_schemes = ["postgresql://", "postgres://", "postgresql+asyncpg://"]
            is_valid_scheme = any(url.startswith(scheme) for scheme in valid_schemes)
            
            if not is_valid_scheme:
                return False
            
            # Basic URL parsing validation
            parsed = urlparse(url)
            if not parsed.netloc:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_environment_type() -> str:
        """Get current environment type.
        
        Returns:
            Environment type: development, test, staging, or production
        """
        # Check multiple environment indicators
        env = os.getenv("ENVIRONMENT", "").lower()
        if env:
            return env
        
        # Check testing indicators
        if os.getenv("TESTING", "false").lower() == "true":
            return "test"
        
        # Check pytest in modules
        import sys
        if 'pytest' in sys.modules:
            return "test"
        
        # Check Cloud Run indicator
        if os.getenv("K_SERVICE"):
            return "staging"  # or production, depending on service name
        
        # Default to development
        return "development"
    
    @staticmethod
    def get_default_url_for_environment(environment: str = None) -> str:
        """Get default database URL for specified environment.
        
        Args:
            environment: Environment type, defaults to current environment
            
        Returns:
            Default database URL for the environment
        """
        if environment is None:
            environment = CoreDatabaseManager.get_environment_type()
        
        environment = environment.lower()
        
        if environment == "development":
            return "postgresql://postgres:password@localhost:5432/netra"
        elif environment in ["test", "testing"]:
            return "sqlite:///:memory:"
        elif environment == "staging":
            return "postgresql://postgres:password@35.223.92.123:5432/netra_staging"
        elif environment == "production":
            return "postgresql://postgres:password@35.223.92.123:5432/netra_production"
        else:
            logger.warning(f"Unknown environment '{environment}', using development default")
            return "postgresql://postgres:password@localhost:5432/netra"
    
    @staticmethod
    def strip_driver_prefixes(url: str) -> str:
        """Strip all driver-specific prefixes from URL.
        
        Args:
            url: Database URL with potential driver prefixes
            
        Returns:
            Clean URL without driver prefixes
        """
        if not url:
            return url
        
        # Remove async driver prefixes
        clean_url = url.replace("postgresql+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres://", "postgresql://")
        
        return clean_url
    
    @staticmethod
    def has_mixed_ssl_params(url: str) -> bool:
        """Check if URL has both ssl and sslmode parameters.
        
        Args:
            url: Database URL to check
            
        Returns:
            True if URL contains both ssl= and sslmode= parameters
        """
        if not url:
            return False
        return "ssl=" in url and "sslmode=" in url
    
    @staticmethod
    def resolve_ssl_parameter_conflicts(url: str, target_driver: str = "asyncpg") -> str:
        """Resolve SSL parameter conflicts for staging deployment.
        
        This function handles the critical staging deployment issue where
        services have mixed ssl/sslmode parameters that cause connection failures.
        
        Args:
            url: Database URL that may have conflicting SSL parameters
            target_driver: Target driver ('asyncpg' or 'psycopg2')
            
        Returns:
            URL with SSL parameters normalized for the target driver
        """
        if not url:
            return url
        
        logger.debug(f"Resolving SSL conflicts for {target_driver}: {url[:50]}...")
        
        # Check for mixed parameters (critical staging issue)
        if CoreDatabaseManager.has_mixed_ssl_params(url):
            logger.warning(f"Found mixed SSL parameters in URL, resolving for {target_driver}")
            
            # Remove all SSL parameters first
            clean_url = re.sub(r'[&?]sslmode=[^&]*', '', url)
            clean_url = re.sub(r'[&?]ssl=[^&]*', '', clean_url)
            
            # Add the correct parameter for target driver
            if target_driver == "asyncpg":
                # Add ssl=require for asyncpg
                separator = "&" if "?" in clean_url else "?"
                clean_url += f"{separator}ssl=require"
            else:
                # Add sslmode=require for psycopg2
                separator = "&" if "?" in clean_url else "?"
                clean_url += f"{separator}sslmode=require"
            
            logger.debug(f"Resolved SSL conflicts: {clean_url[:50]}...")
            return clean_url
        
        # No conflicts, use existing conversion functions
        if target_driver == "asyncpg":
            return CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)
        else:
            return CoreDatabaseManager.convert_ssl_params_for_psycopg2(url)


# Export the main class for backward compatibility
__all__ = ["CoreDatabaseManager"]