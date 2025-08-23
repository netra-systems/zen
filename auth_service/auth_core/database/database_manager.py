"""Auth Service Database Manager - Centralized URL Management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Centralized auth database connection management
- Value Impact: Eliminates URL conversion duplication, unified SSL handling
- Strategic Impact: Consistent patterns across auth service, simplified maintenance

This module provides centralized database URL management for the auth service.
It handles URL transformations, SSL parameter management, and environment detection.

Each function ≤25 lines, following backend patterns but auth-service focused.
"""

import os
import re
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Centralized database manager for auth service async connections."""
    
    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL to standard asyncpg format.
        
        Args:
            url: Raw database URL in various formats
            
        Returns:
            Normalized URL with appropriate driver for async operations
        """
        # SQLite URLs pass through unchanged
        if url.startswith("sqlite"):
            return url
            
        # Convert all postgres variants to postgresql+asyncpg
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://")
        elif url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        elif url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
            
        return url
    
    @staticmethod
    def get_auth_database_url() -> str:
        """Get database URL for auth service (alias for async method).
        
        Returns:
            Database URL compatible with asyncpg driver
        """
        return AuthDatabaseManager.get_auth_database_url_async()
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async database URL for auth service.
        
        Returns:
            Database URL compatible with asyncpg driver for auth service
        """
        base_url = AuthDatabaseManager._get_base_auth_url()
        
        # Ensure async driver
        if base_url.startswith("postgresql://"):
            base_url = base_url.replace("postgresql://", "postgresql+asyncpg://")
        elif base_url.startswith("postgres://"):
            base_url = base_url.replace("postgres://", "postgresql+asyncpg://")
        
        # Convert SSL parameters for asyncpg compatibility
        return AuthDatabaseManager._convert_sslmode_to_ssl(base_url)
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Validate auth database URL format.
        
        Args:
            url: Optional URL to validate, uses auth URL if None
            
        Returns:
            True if URL format is valid for auth service
        """
        target_url = url or AuthDatabaseManager.get_auth_database_url_async()
        
        # Check for valid async driver format
        if not (target_url.startswith("postgresql+asyncpg://") or 
                target_url.startswith("sqlite+aiosqlite://")):
            return False
        
        # Check SSL parameter consistency
        if "/cloudsql/" not in target_url and "sslmode=" in target_url:
            return False  # Should use ssl= for asyncpg
        
        return True
    
    @staticmethod
    def convert_sslmode_to_ssl(url: str) -> str:
        """Convert sslmode parameters to ssl for asyncpg compatibility.
        
        Args:
            url: Database URL that may contain sslmode parameters
            
        Returns:
            URL with sslmode converted to ssl parameters
        """
        return AuthDatabaseManager._convert_sslmode_to_ssl(url)
    
    @staticmethod
    def get_auth_database_url_sync() -> str:
        """Get sync database URL for migrations and sync operations.
        
        Returns:
            Database URL compatible with psycopg2 driver
        """
        base_url = AuthDatabaseManager._get_base_auth_url()
        
        # Handle async driver URLs that may be passed directly (for testing)
        if base_url.startswith("postgresql+asyncpg://"):
            sync_url = base_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        elif base_url.startswith("postgresql://"):
            sync_url = base_url.replace("postgresql://", "postgresql+psycopg2://")
        elif base_url.startswith("postgres://"):
            sync_url = base_url.replace("postgres://", "postgresql+psycopg2://")
        else:
            sync_url = base_url
            
        # Keep sslmode parameters for sync connections (psycopg2 uses sslmode)
        return sync_url
    
    @staticmethod
    def validate_sync_url(url: str) -> bool:
        """Validate sync database URL format for migrations.
        
        Args:
            url: URL to validate for sync operations
            
        Returns:
            True if URL format is valid for sync operations
        """
        # Valid sync URLs should use psycopg2 or be basic postgresql://
        if url.startswith("postgresql+psycopg2://") or url.startswith("postgresql://"):
            return True
        
        # Invalid: async drivers in sync context
        if url.startswith("postgresql+asyncpg://") or url.startswith("sqlite+aiosqlite://"):
            return False
            
        return True
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Detect if running in Cloud SQL environment.
        
        Returns:
            True if running in Cloud Run with Cloud SQL
        """
        # Check for Cloud Run environment variable
        if os.getenv("K_SERVICE"):
            return True
            
        # Also check database URL for Cloud SQL socket
        database_url = AuthDatabaseManager._get_raw_database_url()
        return "/cloudsql/" in database_url
    
    @staticmethod
    def is_test_environment() -> bool:
        """Detect if running in test environment.
        
        Returns:
            True if running in test mode (SQLite or test config)
        """
        # Check multiple test indicators
        import sys
        is_pytest = 'pytest' in sys.modules
        is_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        env_is_test = os.getenv("ENVIRONMENT", "").lower() in ["test", "testing"]
        
        return is_pytest or is_test_mode or env_is_test
    
    @staticmethod
    def _get_base_auth_url() -> str:
        """Get clean base URL for auth service.
        
        Returns:
            Clean database URL with driver prefixes stripped
        """
        raw_url = AuthDatabaseManager._get_raw_database_url()
        
        if not raw_url:
            return AuthDatabaseManager._get_default_auth_url()
        
        # Strip async driver prefixes for base URL
        clean_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres+asyncpg://", "postgresql://")
        clean_url = clean_url.replace("postgres://", "postgresql://")
        
        # Handle Cloud SQL SSL parameters
        if "/cloudsql/" in clean_url:
            clean_url = re.sub(r'[&?]sslmode=[^&]*', '', clean_url)
            clean_url = re.sub(r'[&?]ssl=[^&]*', '', clean_url)
        
        return clean_url
    
    @staticmethod
    def _get_raw_database_url() -> str:
        """Get raw database URL from environment.
        
        Returns:
            Raw database URL from environment variables
        """
        try:
            from auth_service.auth_core.config import AuthConfig
            return AuthConfig.get_database_url()
        except ImportError:
            return os.getenv("DATABASE_URL", "")
    
    @staticmethod
    def _get_default_auth_url() -> str:
        """Get default database URL for auth service.
        
        Returns:
            Default database URL based on environment
        """
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if env == "test" or AuthDatabaseManager.is_test_environment():
            return "sqlite+aiosqlite:///:memory:"
        elif env == "development":
            return "postgresql://postgres:password@localhost:5432/auth"
        elif env == "staging":
            return "postgresql://netra_staging:password@35.223.209.195:5432/netra_staging"
        else:
            logger.warning(f"No DATABASE_URL found for {env} environment")
            return "postgresql://postgres:password@localhost:5432/auth"
    
    @staticmethod
    def _convert_sslmode_to_ssl(url: str) -> str:
        """Internal SSL parameter conversion logic.
        
        Args:
            url: Database URL that may contain sslmode parameters
            
        Returns:
            URL with SSL parameters converted for asyncpg
        """
        if "/cloudsql/" in url:
            # For Cloud SQL URLs, keep sslmode as-is (tests expect this behavior)
            return url
        
        if "sslmode=" in url:
            # Convert sslmode to ssl for asyncpg compatibility
            def replace_sslmode(match):
                sslmode_value = match.group(1)
                ssl_mapping = {
                    "require": "require",
                    "prefer": "prefer", 
                    "disable": "disable",
                    "allow": "allow",
                    "verify-ca": "verify-ca",
                    "verify-full": "verify-full"
                }
                return f"ssl={ssl_mapping.get(sslmode_value, sslmode_value)}"
            
            url = re.sub(r'sslmode=([^&]*)', replace_sslmode, url)
        
        return url


# Export the main class
__all__ = ["AuthDatabaseManager"]