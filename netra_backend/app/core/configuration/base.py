"""Base Configuration Module - Unified Configuration Manager

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Developer Experience
- Value Impact: Prevents configuration import errors that block test execution
- Strategic Impact: Provides SSOT for configuration access across the system

This module serves as the central interface for configuration management,
consolidating all configuration access patterns into a unified system.
"""

from functools import lru_cache
from typing import Any, Dict, Optional

from netra_backend.app.core.environment_constants import EnvironmentDetector
from netra_backend.app.core.configuration.loader import ConfigurationLoader
from netra_backend.app.core.configuration.validator import ConfigurationValidator
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.config import (
    AppConfig,
    DevelopmentConfig,
    NetraTestingConfig,
    ProductionConfig,
    StagingConfig,
)


class UnifiedConfigManager:
    """Unified Configuration Manager - SSOT for all configuration access.
    
    This class serves as the single source of truth for configuration
    management throughout the application.
    """
    
    def __init__(self):
        """Initialize the unified configuration manager."""
        self._logger = logger
        self._loader = ConfigurationLoader()
        self._validator = ConfigurationValidator()
        self._config_cache: Optional[AppConfig] = None
        self._environment: Optional[str] = None
    
    @lru_cache(maxsize=1)
    def get_config(self) -> AppConfig:
        """Get the unified application configuration.
        
        Returns:
            AppConfig: The validated application configuration
        """
        if self._config_cache is None:
            self._logger.info("Loading unified configuration")
            environment = self._get_environment()
            config = self._create_config_for_environment(environment)
            
            # Validate the configuration
            validation_result = self._validator.validate_complete_config(config)
            if not validation_result.is_valid:
                self._logger.warning(f"Configuration validation issues: {validation_result.errors}")
            
            self._config_cache = config
            self._logger.info(f"Configuration loaded for environment: {environment}")
        
        return self._config_cache
    
    def _get_environment(self) -> str:
        """Get the current environment."""
        if self._environment is None:
            self._environment = EnvironmentDetector.get_environment()
        return self._environment
    
    def _create_config_for_environment(self, environment: str) -> AppConfig:
        """Create configuration instance for the specified environment.
        
        Args:
            environment: The environment name
            
        Returns:
            AppConfig: Environment-specific configuration
        """
        config_classes = {
            "development": DevelopmentConfig,
            "staging": StagingConfig,
            "production": ProductionConfig,
            "testing": NetraTestingConfig,
        }
        
        config_class = config_classes.get(environment, DevelopmentConfig)
        self._logger.info(f"Creating {config_class.__name__} for environment: {environment}")
        
        try:
            config = config_class()
            
            # CRITICAL FIX: Ensure service_secret is loaded from environment if not set
            # This handles cases where the config class doesn't properly load it
            if not config.service_secret:
                from shared.isolated_environment import get_env
                env = get_env()
                service_secret = env.get('SERVICE_SECRET')
                if service_secret:
                    config.service_secret = service_secret
                    self._logger.info("Loaded SERVICE_SECRET from environment as fallback")
                    
            return config
        except Exception as e:
            self._logger.error(f"Failed to create config for {environment}: {e}")
            # Fallback to basic config
            return AppConfig(environment=environment)
    
    def reload_config(self, force: bool = False) -> AppConfig:
        """Reload the configuration.
        
        Args:
            force: Force reload even if cached
            
        Returns:
            AppConfig: The reloaded configuration
        """
        if force:
            self._config_cache = None
            self._environment = None
            self.get_config.cache_clear()
        
        return self.get_config()
    
    def validate_config_integrity(self) -> bool:
        """Validate configuration integrity.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            config = self.get_config()
            validation_result = self._validator.validate_complete_config(config)
            return validation_result.is_valid
        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_environment_name(self) -> str:
        """Get the current environment name.
        
        Returns:
            str: The environment name
        """
        return self._get_environment()
    
    def is_production(self) -> bool:
        """Check if running in production environment.
        
        Returns:
            bool: True if production
        """
        return self._get_environment() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment.
        
        Returns:
            bool: True if development
        """
        return self._get_environment() == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment.
        
        Returns:
            bool: True if testing
        """
        return self._get_environment() == "testing"


# Global configuration manager instance
config_manager = UnifiedConfigManager()


def get_unified_config() -> AppConfig:
    """Get the unified application configuration.
    
    This is the primary function for accessing configuration throughout
    the application.
    
    Returns:
        AppConfig: The application configuration
    """
    return config_manager.get_config()


def reload_unified_config(force: bool = False) -> AppConfig:
    """Reload the unified configuration.
    
    Args:
        force: Force reload even if cached
        
    Returns:
        AppConfig: The reloaded configuration
    """
    return config_manager.reload_config(force=force)


def validate_config_integrity() -> tuple[bool, list]:
    """Validate configuration integrity for Enterprise customers.
    
    Returns:
        tuple: (is_valid, list_of_errors)
    """
    try:
        is_valid = config_manager.validate_config_integrity()
        return (is_valid, [])
    except Exception as e:
        return (False, [str(e)])


def validate_unified_config() -> bool:
    """Validate the unified configuration.
    
    Returns:
        bool: True if configuration is valid
    """
    return config_manager.validate_config_integrity()


def get_environment() -> str:
    """Get the current environment name.
    
    Returns:
        str: The environment name
    """
    return config_manager.get_environment_name()


def is_production() -> bool:
    """Check if running in production environment.
    
    Returns:
        bool: True if production
    """
    return config_manager.is_production()


def is_development() -> bool:
    """Check if running in development environment.
    
    Returns:
        bool: True if development
    """
    return config_manager.is_development()


def is_testing() -> bool:
    """Check if running in testing environment.
    
    Returns:
        bool: True if testing
    """
    return config_manager.is_testing()


# Export compatibility functions
__all__ = [
    "UnifiedConfigManager",
    "config_manager",
    "get_unified_config",
    "reload_unified_config", 
    "validate_unified_config",
    "get_environment",
    "is_production",
    "is_development",
    "is_testing",
]