"""Configuration Service

Provides configuration management services.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentConfigLoader:
    """Loads configuration from environment variables."""
    
    def __init__(self):
        self.config = {}
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment."""
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        return env.get_all()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration using DatabaseURLBuilder SSOT."""
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        
        env = get_env()
        builder = DatabaseURLBuilder(env.get_all())
        
        # Get database URL using SSOT pattern
        database_url = builder.get_url_for_environment()
        if not database_url:
            # Fallback for development/test environments
            database_url = builder.development.default_url
        
        return {
            'DATABASE_URL': database_url,
            'DATABASE_POOL_SIZE': 10
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        return {
            'REDIS_URL': 'redis://localhost:6379/0'
        }


class ConfigurationValidator:
    """Validates configuration settings."""
    
    @staticmethod
    def validate_database_config(config: Dict[str, Any]) -> bool:
        """Validate database configuration using DatabaseURLBuilder SSOT."""
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        
        # First check if DATABASE_URL key exists in config
        if 'DATABASE_URL' not in config:
            return False
        
        # Validate using DatabaseURLBuilder if environment is available
        try:
            env = get_env()
            builder = DatabaseURLBuilder(env.get_all())
            is_valid, error = builder.validate()
            return is_valid
        except Exception:
            # Fallback to basic validation if DatabaseURLBuilder fails
            database_url = config.get('DATABASE_URL', '')
            return bool(database_url and len(database_url) > 0)
    
    @staticmethod
    def validate_redis_config(config: Dict[str, Any]) -> bool:
        """Validate Redis configuration."""
        required_keys = ['REDIS_URL']
        for key in required_keys:
            if key not in config:
                return False
        return True


class ConfigurationManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.validator = ConfigurationValidator()
        self._config_cache: Dict[str, Any] = {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config_cache.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config_cache[key] = value
    
    def validate_config(self) -> bool:
        """Validate current configuration."""
        try:
            db_valid = self.validator.validate_database_config(self._config_cache)
            redis_valid = self.validator.validate_redis_config(self._config_cache)
            return db_valid and redis_valid
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Alias for backward compatibility
ConfigurationService = ConfigurationManager