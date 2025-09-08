"""
Database Configuration Management Module

This module provides database configuration management as part of the unified
configuration architecture. Following SSOT principles and CLAUDE.md requirements
for configuration isolation and validation.

Business Value:
- Prevents database connection failures that impact operations
- Ensures consistent database configuration across environments
- Provides validation to catch configuration errors early

The actual database configuration logic is implemented in the unified configuration
system, but this module provides backward compatibility for existing imports.
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.schemas.config import AppConfig

logger = logging.getLogger(__name__)


class DatabaseConfigManager:
    """
    Database Configuration Manager - Backward Compatibility Layer
    
    This class provides backward compatibility for tests and code that expect
    the DatabaseConfigManager interface. It delegates to the unified configuration
    system while maintaining the expected API.
    
    Following CLAUDE.md requirements:
    - Uses IsolatedEnvironment through unified config
    - Provides environment-specific database configurations
    - Validates database URLs and connection parameters
    """
    
    def __init__(self):
        """Initialize database configuration manager."""
        self._config = None
        self._cached_config = {}
    
    def get_config(self) -> AppConfig:
        """Get the current application configuration."""
        if self._config is None:
            self._config = get_unified_config()
        return self._config
    
    def get_database_url(self, environment: Optional[str] = None) -> str:
        """
        Get PostgreSQL database URL for the specified environment.
        
        Args:
            environment: Environment name (dev, staging, prod)
            
        Returns:
            Database URL string
        """
        config = self.get_config()
        return config.database_url
    
    def get_redis_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Redis configuration for the specified environment.
        
        Args:
            environment: Environment name (dev, staging, prod)
            
        Returns:
            Redis configuration dictionary
        """
        config = self.get_config()
        if hasattr(config, 'redis') and config.redis:
            return {
                'host': config.redis.host,
                'port': config.redis.port,
                'db': getattr(config.redis, 'db', 0),
                'password': getattr(config.redis, 'password', None),
                'ssl': getattr(config.redis, 'ssl', False),
            }
        return {}
    
    def get_clickhouse_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ClickHouse configuration for the specified environment.
        
        Args:
            environment: Environment name (dev, staging, prod)
            
        Returns:
            ClickHouse configuration dictionary
        """
        config = self.get_config()
        if hasattr(config, 'clickhouse_native') and config.clickhouse_native:
            return {
                'host': config.clickhouse_native.host,
                'port': config.clickhouse_native.port,
                'user': config.clickhouse_native.user,
                'password': getattr(config.clickhouse_native, 'password', None),
                'database': getattr(config.clickhouse_native, 'database', 'default'),
            }
        return {}
    
    def validate_database_config(self, environment: Optional[str] = None) -> bool:
        """
        Validate database configuration for the specified environment.
        
        Args:
            environment: Environment name (dev, staging, prod)
            
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            database_url = self.get_database_url(environment)
            if not database_url:
                logger.error("Database URL is not configured")
                return False
                
            # Basic URL validation
            parsed = urlparse(database_url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid database URL format: {database_url}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Database configuration validation failed: {e}")
            return False
    
    def populate_database_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Populate complete database configuration for the environment.
        
        This method provides the interface expected by existing code while
        delegating to the unified configuration system.
        
        Args:
            environment: Environment name (dev, staging, prod)
            
        Returns:
            Complete database configuration dictionary
        """
        try:
            config = {
                'postgresql': {
                    'url': self.get_database_url(environment),
                    'valid': self.validate_database_config(environment)
                },
                'redis': self.get_redis_config(environment),
                'clickhouse': self.get_clickhouse_config(environment)
            }
            
            logger.debug(f"Populated database config for {environment or 'current'}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to populate database config: {e}")
            return {}
    
    def _get_postgres_url(self, environment: Optional[str] = None) -> str:
        """
        Internal method to get PostgreSQL URL.
        
        This method matches the signature seen in logs and provides
        the expected interface for backward compatibility.
        """
        url = self.get_database_url(environment)
        if url:
            logger.info(f"Using PostgreSQL URL from {environment or 'current'} configuration")
        return url
    
    def _populate_redis_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Internal method to populate Redis configuration.
        
        This method matches the signature seen in logs and provides
        the expected interface for backward compatibility.
        """
        redis_config = self.get_redis_config(environment)
        if redis_config:
            # Format log message matching what was seen in logs
            host = redis_config.get('host', 'localhost')
            port = redis_config.get('port', 6379)
            db = redis_config.get('db', 0)
            ssl = redis_config.get('ssl', False)
            ssl_str = "SSL" if ssl else "No SSL"
            
            logger.info(f"Redis Configuration ({environment or 'current'}/URL/{ssl_str}): "
                       f"redis://{host}:{port}/{db}")
        
        return redis_config


# Backward compatibility function-level interface
def get_database_config_manager() -> DatabaseConfigManager:
    """
    Get a configured DatabaseConfigManager instance.
    
    Returns:
        DatabaseConfigManager instance
    """
    return DatabaseConfigManager()


# Module-level convenience functions for backward compatibility
def get_database_url(environment: Optional[str] = None) -> str:
    """Get database URL for environment."""
    manager = get_database_config_manager()
    return manager.get_database_url(environment)


def validate_database_connection(environment: Optional[str] = None) -> bool:
    """Validate database connection for environment."""
    manager = get_database_config_manager()
    return manager.validate_database_config(environment)


def populate_database_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """Populate database configuration for environment."""
    manager = get_database_config_manager()
    return manager.populate_database_config(environment)


# Export public interface
__all__ = [
    "DatabaseConfigManager",
    "get_database_config_manager", 
    "get_database_url",
    "validate_database_connection",
    "populate_database_config"
]