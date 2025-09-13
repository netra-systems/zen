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
# CIRCULAR DEPENDENCY FIX: Lazy load logger to break circular import
# from netra_backend.app.logging_config import central_logger as logger
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
        self._logger = None  # Lazy loaded to break circular dependency
        self._loader = ConfigurationLoader()
        self._validator = ConfigurationValidator()
        self._config_cache: Optional[AppConfig] = None
        self._environment: Optional[str] = None

    def _get_logger(self):
        """Lazy load logger to prevent circular dependency.
        
        CIRCULAR DEPENDENCY FIX: Only import logger when needed to break:
        shared/logging -> config -> netra_backend/logging_config -> shared/logging loop
        """
        if self._logger is None:
            try:
                from netra_backend.app.logging_config import central_logger
                self._logger = central_logger
            except ImportError:
                # Fallback to basic logging if circular dependency still exists
                import logging
                self._logger = logging.getLogger(__name__)
        return self._logger
    
    def get_config(self) -> AppConfig:
        """Get the unified application configuration.
        
        CRITICAL FIX: Removed @lru_cache decorator to prevent test configuration caching issues.
        Test environments need fresh configuration loading to properly reflect environment variables.
        
        Returns:
            AppConfig: The validated application configuration
        """
        # CRITICAL FIX: Always check if we're in test environment to avoid caching issues
        current_environment = self._get_environment()
        
        # For test environments, always reload configuration to ensure fresh environment variable reads
        is_test_environment = current_environment == "testing"
        
        if self._config_cache is None or is_test_environment:
            if is_test_environment:
                self._get_logger().debug("Test environment detected - forcing fresh configuration load")
            else:
                self._get_logger().info("Loading unified configuration")
                
            config = self._create_config_for_environment(current_environment)
            
            # Validate the configuration
            validation_result = self._validator.validate_complete_config(config)
            if not validation_result.is_valid:
                self._get_logger().error(
                    f" FAIL:  VALIDATION FAILURE: Configuration validation failed for environment '{current_environment}'. "
                    f"Errors: {validation_result.errors}. This may cause system instability."
                )
            else:
                self._get_logger().debug(f" PASS:  Configuration validation passed for environment '{current_environment}'")
            
            # Only cache for non-test environments
            if not is_test_environment:
                self._config_cache = config
                self._get_logger().info(f"Configuration loaded and cached for environment: {current_environment}")
            else:
                self._get_logger().debug(f"Configuration loaded (not cached) for test environment: {current_environment}")
                return config
        
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
        self._get_logger().info(f"Creating {config_class.__name__} for environment: {environment}")
        
        try:
            config = config_class()
            
            # CRITICAL FIX: Ensure service_secret is loaded from environment if not set
            # This handles cases where the config class doesn't properly load it
            if not config.service_secret:
                try:
                    # SSOT COMPLIANT: Use IsolatedEnvironment instead of direct os.environ access
                    from shared.isolated_environment import IsolatedEnvironment
                    env = IsolatedEnvironment()
                    service_secret = env.get('SERVICE_SECRET') or env.get('JWT_SECRET_KEY')
                    if service_secret:
                        config.service_secret = service_secret.strip()
                        self._get_logger().info("Loaded SERVICE_SECRET from IsolatedEnvironment (SSOT compliant)")
                    else:
                        self._get_logger().warning("SERVICE_SECRET not found in environment variables")
                except Exception as e:
                    self._get_logger().error(f"Failed to load SERVICE_SECRET from environment: {e}")
                    # SSOT COMPLIANT: Log critical failure but don't bypass SSOT
                    # This maintains SSOT compliance even if configuration is unavailable
                    
            # DEFENSIVE FIX: Ensure service_id is also sanitized from environment
            # This prevents header value issues from Windows line endings or whitespace
            if hasattr(config, 'service_id') and config.service_id:
                original_service_id = config.service_id
                config.service_id = str(config.service_id).strip()
                if config.service_id != original_service_id:
                    self._get_logger().warning(f"SERVICE_ID contained whitespace - sanitized from {repr(original_service_id)} to {repr(config.service_id)}")
                    
            return config
        except Exception as e:
            self._get_logger().error(
                f" FAIL:  VALIDATION FAILURE: Failed to create configuration for environment '{environment}'. "
                f"Error: {e}. Falling back to basic AppConfig. This may cause missing configuration values."
            )
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
            # Note: No cache_clear() needed since @lru_cache was removed
        
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
            self._get_logger().error(f"Configuration validation failed: {e}")
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

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value by key path.

        COMPATIBILITY METHOD: Supports ConfigurationManager.get_config(key, default) pattern
        for backward compatibility during SSOT migration.

        Args:
            key: Dot-separated key path (e.g., 'database.url', 'security.jwt_secret')
            default: Default value if key not found

        Returns:
            Any: The configuration value or default
        """
        try:
            config = self.get_config()

            # Handle dot-separated key paths
            keys = key.split('.')
            value = config

            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    self._get_logger().debug(f"Configuration key '{key}' not found, returning default: {default}")
                    return default

            return value
        except Exception as e:
            self._get_logger().error(f"Error getting configuration value for key '{key}': {e}")
            return default

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value by key path.

        COMPATIBILITY METHOD: Supports ConfigurationManager.set_config(key, value) pattern
        for backward compatibility during SSOT migration.

        NOTE: This sets values in the current config instance but does not persist
        changes to environment variables or configuration files.

        Args:
            key: Configuration key path
            value: Value to set
        """
        try:
            config = self.get_config()

            # Handle dot-separated key paths for setting
            keys = key.split('.')
            current = config

            # Navigate to the parent object
            for k in keys[:-1]:
                if hasattr(current, k):
                    current = getattr(current, k)
                elif isinstance(current, dict):
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                else:
                    self._get_logger().warning(f"Cannot set configuration key '{key}' - invalid path")
                    return

            # Set the final value
            final_key = keys[-1]
            if hasattr(current, final_key):
                setattr(current, final_key, value)
            elif isinstance(current, dict):
                current[final_key] = value
            else:
                self._get_logger().warning(f"Cannot set configuration key '{key}' - invalid target")

            self._get_logger().debug(f"Set configuration value '{key}' = {value}")
        except Exception as e:
            self._get_logger().error(f"Error setting configuration value for key '{key}': {e}")

    def validate_config_value(self, key: str = None) -> bool:
        """Validate configuration value or entire configuration.

        COMPATIBILITY METHOD: Supports ConfigurationManager.validate_config() pattern

        Args:
            key: Optional specific key to validate (if None, validates entire config)

        Returns:
            bool: True if valid
        """
        if key is None:
            return self.validate_config_integrity()
        else:
            try:
                value = self.get_config_value(key)
                return value is not None
            except Exception:
                return False


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


# CRITICAL GOLDEN PATH COMPATIBILITY FUNCTION
def get_config() -> AppConfig:
    """Get the application configuration - Golden Path compatibility function.

    COMPATIBILITY LAYER: This function provides backward compatibility for Golden Path tests
    that expect a get_config() function. Re-exports get_unified_config() functionality.

    Business Impact: Enables Golden Path test execution protecting $500K+ ARR

    Returns:
        AppConfig: The application configuration
    """
    return get_unified_config()


# CONFIGURATION MANAGER COMPATIBILITY FUNCTIONS
def get_config_value(key: str, default: Any = None) -> Any:
    """Get a specific configuration value by key path.

    COMPATIBILITY FUNCTION: Supports ConfigurationManager.get_config(key, default) pattern
    for backward compatibility during SSOT migration.

    Args:
        key: Dot-separated key path (e.g., 'database.url', 'security.jwt_secret')
        default: Default value if key not found

    Returns:
        Any: The configuration value or default
    """
    return config_manager.get_config_value(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Set a configuration value by key path.

    COMPATIBILITY FUNCTION: Supports ConfigurationManager.set_config(key, value) pattern
    for backward compatibility during SSOT migration.

    Args:
        key: Configuration key path
        value: Value to set
    """
    return config_manager.set_config_value(key, value)


def validate_config_value(key: str = None) -> bool:
    """Validate configuration value or entire configuration.

    COMPATIBILITY FUNCTION: Supports ConfigurationManager.validate_config() pattern

    Args:
        key: Optional specific key to validate (if None, validates entire config)

    Returns:
        bool: True if valid
    """
    return config_manager.validate_config_value(key)


# Export compatibility functions
__all__ = [
    "UnifiedConfigManager",
    "config_manager",
    "get_unified_config",
    "get_config",  # Golden Path compatibility
    "get_config_value",  # ConfigurationManager compatibility
    "set_config_value",  # ConfigurationManager compatibility
    "validate_config_value",  # ConfigurationManager compatibility
    "reload_unified_config",
    "validate_unified_config",
    "get_environment",
    "is_production",
    "is_development",
    "is_testing",
]