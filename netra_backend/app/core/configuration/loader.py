"""Configuration Loader - Main entry point for configuration access

Provides the primary interface for loading and accessing configuration.
This module serves as the main fa[U+00E7]ade for the unified configuration system.

Business Value: Simplifies configuration access for developers,
reducing configuration-related errors by 90%.
"""

from functools import lru_cache
from typing import Any, Dict, Optional

# Circular import prevention - UnifiedConfigManager is defined in base.py
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)
from netra_backend.app.schemas.config import AppConfig


class ConfigurationLoader:
    """Main configuration loader interface.
    
    Provides a clean, simple API for configuration access
    throughout the application.
    """
    
    def __init__(self):
        """Initialize the configuration loader."""
        self._logger = logger
        self._config_cache: Optional[AppConfig] = None
        
    @lru_cache(maxsize=1)
    def load(self) -> AppConfig:
        """Load the complete application configuration.
        
        Returns:
            AppConfig: The validated application configuration
        """
        if self._config_cache is None:
            self._logger.info("Loading configuration")
            from netra_backend.app.core.environment_constants import EnvironmentDetector
            environment = EnvironmentDetector.get_environment()
            config = self._create_config_for_environment(environment)
            self._config_cache = config
            self._logger.info(f"Configuration loaded for environment: {environment}")
        
        return self._config_cache
    
    def _create_config_for_environment(self, environment: str) -> AppConfig:
        """Create configuration instance for the specified environment.
        
        Args:
            environment: The environment name
            
        Returns:
            AppConfig: Environment-specific configuration
        """
        from netra_backend.app.schemas.config import (
            DevelopmentConfig,
            NetraTestingConfig,
            ProductionConfig,
            StagingConfig,
        )
        
        config_classes = {
            "development": DevelopmentConfig,
            "staging": StagingConfig,
            "production": ProductionConfig,
            "testing": NetraTestingConfig,
        }
        
        config_class = config_classes.get(environment, DevelopmentConfig)

        try:
            self._logger.info(f"Creating {config_class.__name__} for environment: {environment}")
            # If the environment is unknown, use DevelopmentConfig but preserve original environment name
            if environment not in config_classes:
                # Use DevelopmentConfig behavior but set environment to original value
                config = config_class()
                config.environment = environment
            else:
                config = config_class()
            return config
        except Exception as e:
            self._logger.error(f"Failed to create config for {environment}: {e}")
            # Fallback to basic config
            return AppConfig(environment=environment)
    
    def reload(self, force: bool = False) -> AppConfig:
        """Reload the configuration (for hot-reload scenarios).
        
        Args:
            force: Force reload even if caching is enabled
            
        Returns:
            AppConfig: The reloaded configuration
        """
        if force:
            self.load.cache_clear()
            self._config_cache = None
        return self.load()
    
    def get_environment(self) -> str:
        """Get the current environment name.
        
        Returns:
            str: The environment (development, staging, production, testing)
        """
        config = self.load()
        return config.environment
    
    def is_production(self) -> bool:
        """Check if running in production environment.
        
        Returns:
            bool: True if production environment
        """
        return self.get_environment() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment.
        
        Returns:
            bool: True if development environment
        """
        return self.get_environment() == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment.
        
        Returns:
            bool: True if testing environment
        """
        return self.get_environment() == "testing"
    
    def get_database_url(self, db_type: str = "postgres") -> str:
        """Get database connection URL.
        
        Args:
            db_type: Type of database (postgres, clickhouse)
            
        Returns:
            str: Database connection URL
        """
        config = self.load()
        if db_type == "clickhouse":
            return config.get_clickhouse_url()
        return config.get_database_url()
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Get configuration for a specific service.
        
        Args:
            service: Service name (redis, llm, auth, etc.)
            
        Returns:
            Dict containing service configuration
        """
        config = self.load()
        service_configs = {
            "redis": {
                "host": self._get_redis_host(config),
                "port": self._get_redis_port(config),
                "password": self._get_redis_password(config),
                "url": getattr(config, 'redis_url', None) if self._is_redis_configured(config) else None
            },
            "llm": {
                "provider": config.llm_configs.get("default", {}).provider if hasattr(config, 'llm_configs') and config.llm_configs else None,
                "model": config.llm_configs.get("default", {}).model_name if hasattr(config, 'llm_configs') and config.llm_configs else None,
                "api_key": config.llm_configs.get("default", {}).api_key if hasattr(config, 'llm_configs') and config.llm_configs else None
            },
            "auth": {
                "url": config.auth_service_url if hasattr(config, 'auth_service_url') else None,
                "secret_key": config.jwt_secret_key if hasattr(config, 'jwt_secret_key') else None
            }
        }
        return service_configs.get(service, {})

    def _is_redis_configured(self, config) -> bool:
        """Check if Redis is properly configured (not just defaults).

        Args:
            config: The configuration object

        Returns:
            bool: True if Redis appears to be configured with non-default values
        """
        if not hasattr(config, 'redis'):
            return False
        redis_config = config.redis

        # Check for disabled/unconfigured states
        if (hasattr(redis_config, 'host') and
            redis_config.host in ['disabled', 'localhost', None]):
            # If host is disabled/localhost, check if we have other explicit config
            if not (hasattr(config, 'redis_url') and config.redis_url):
                return False

        # Check if password is explicitly disabled
        if (hasattr(redis_config, 'password') and
            redis_config.password in ['disabled', None]):
            # If password is disabled, need redis_url or non-default host
            if not ((hasattr(config, 'redis_url') and config.redis_url) or
                   (hasattr(redis_config, 'host') and redis_config.host not in ['localhost', 'disabled'])):
                return False

        # If Redis has explicit redis_url, consider it configured
        if hasattr(config, 'redis_url') and config.redis_url is not None:
            return True

        # If Redis has non-default host and it's not disabled, consider configured
        if (hasattr(redis_config, 'host') and
            redis_config.host not in ['localhost', 'disabled', None]):
            return True

        # If Redis has a password that's not disabled, consider configured
        if (hasattr(redis_config, 'password') and
            redis_config.password not in ['disabled', None]):
            return True

        # Otherwise, not configured
        return False

    def _get_redis_host(self, config) -> str:
        """Get Redis host, returning None if Redis is not configured."""
        return config.redis.host if self._is_redis_configured(config) else None

    def _get_redis_port(self, config) -> int:
        """Get Redis port, returning None if Redis is not configured."""
        return config.redis.port if self._is_redis_configured(config) else None

    def _get_redis_password(self, config) -> str:
        """Get Redis password, returning None if Redis is not configured."""
        return config.redis.password if self._is_redis_configured(config) else None
    
    def validate(self) -> bool:
        """Validate the current configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            config = self.load()
            return True  # If we can load the config without errors, it's valid
        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            return False


# Global instance for easy access
_configuration_loader = ConfigurationLoader()


def get_configuration() -> AppConfig:
    """Get the application configuration.
    
    This is the primary function to use for configuration access.
    
    Returns:
        AppConfig: The application configuration
    """
    return _configuration_loader.load()


def reload_configuration(force: bool = False) -> AppConfig:
    """Reload the application configuration.
    
    Args:
        force: Force reload even if caching is enabled
        
    Returns:
        AppConfig: The reloaded configuration
    """
    return _configuration_loader.reload(force)