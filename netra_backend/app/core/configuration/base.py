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
            from shared.logging.unified_logging_ssot import get_logger
            self._logger = get_logger(__name__)
        return self._logger
    
    def get_config(self, key: str = None, default: Any = None) -> AppConfig:
        """Get the unified application configuration.
        
        COMPATIBILITY FIX: Support both get_config() and get_config(key, default) patterns
        for backward compatibility during SSOT migration.
        
        CRITICAL FIX: Removed @lru_cache decorator to prevent test configuration caching issues.
        Test environments need fresh configuration loading to properly reflect environment variables.
        
        Args:
            key: Optional configuration key for backward compatibility
            default: Default value if key not found
        
        Returns:
            AppConfig or Any: The validated application configuration, or specific value if key provided
        """
        # Handle backward compatibility for get_config(key, default) pattern
        if key is not None:
            return self.get_config_value(key, default)
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
                    service_secret = env.get('SERVICE_SECRET')  # JWT fallback removed - SSOT compliance

                    # STAGING LENIENT MODE: For staging environments, use lenient secret validation
                    validation_mode = env.get('SERVICE_SECRET_VALIDATION_MODE', 'strict').lower()
                    if environment == "staging" and validation_mode == "lenient":
                        # Allow weaker secrets in staging for development purposes
                        if not service_secret:
                            service_secret = 'staging-development-service-secret-2025'  # Use service secret, not JWT
                            self._get_logger().info(f"Using lenient staging service secret for environment: {environment}")

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
            
            # CRITICAL FIX: Issue #938 - Validate URLs after successful configuration creation
            # This prevents localhost URLs from being used in staging/production environments
            url_validation_errors = []
            urls_to_validate = [
                ('frontend_url', config.frontend_url),
                ('api_base_url', config.api_base_url), 
                ('auth_service_url', config.auth_service_url)
            ]
            
            for url_type, url_value in urls_to_validate:
                if hasattr(config, url_type):
                    is_valid, error_msg = self._validate_url_for_environment(url_value, url_type, environment)
                    if not is_valid:
                        url_validation_errors.append(error_msg)
            
            # If URL validation fails, log warnings but allow configuration to proceed
            # This provides diagnostic information without blocking system startup
            if url_validation_errors:
                for error in url_validation_errors:
                    self._get_logger().warning(f"URL Validation Issue: {error}")
                
                self._get_logger().warning(
                    f"Configuration for '{environment}' has URL validation issues but will proceed. "
                    f"Issues: {'; '.join(url_validation_errors)}"
                )
                    
            return config
        except Exception as e:
            self._get_logger().error(
                f" FAIL:  VALIDATION FAILURE: Failed to create configuration for environment '{environment}'. "
                f"Error: {e}. Attempting graceful recovery with environment-specific defaults."
            )
            
            # CRITICAL FIX: Issue #938 - Environment-specific fallback instead of localhost AppConfig
            # When StagingConfig fails, provide staging-appropriate defaults rather than localhost defaults
            return self._create_fallback_config_for_environment(environment, str(e))
    
    def _create_fallback_config_for_environment(self, environment: str, error_context: str) -> AppConfig:
        """Create fallback configuration with environment-appropriate defaults.
        
        CRITICAL FIX: Issue #938 - Environment URL Configuration Using Localhost Block Staging
        This method prevents localhost URLs from being used as defaults in staging/production
        environments when primary configuration loading fails.
        
        Args:
            environment: The target environment name
            error_context: Original error that caused fallback
            
        Returns:
            AppConfig: Fallback configuration with environment-appropriate defaults
        """
        logger = self._get_logger()
        logger.warning(f"Creating fallback configuration for environment '{environment}' due to: {error_context}")
        
        # Create base AppConfig with proper environment
        fallback_config = AppConfig(environment=environment)
        
        # CRITICAL FIX: Apply environment-specific URL defaults instead of localhost
        if environment == "staging":
            # Override localhost defaults with staging-appropriate URLs (Issue #1278 fix)
            fallback_config.frontend_url = "https://staging.netrasystems.ai"
            fallback_config.api_base_url = "https://api.staging.netrasystems.ai"
            fallback_config.auth_service_url = "https://staging.netrasystems.ai"
            logger.info("Applied staging URL defaults to prevent localhost in staging environment")
            
        elif environment == "production":
            # Override localhost defaults with production URLs
            fallback_config.frontend_url = "https://app.netrasystems.ai"
            fallback_config.api_base_url = "https://api.netrasystems.ai"
            fallback_config.auth_service_url = "https://auth.netrasystems.ai"
            logger.info("Applied production URL defaults to prevent localhost in production environment")
            
        elif environment == "testing":
            # For testing, localhost is acceptable, but use test-specific ports
            fallback_config.frontend_url = "http://localhost:3001"  # Different from dev
            fallback_config.api_base_url = "http://localhost:8001"   # Different from dev
            fallback_config.auth_service_url = "http://localhost:8082" # Different from dev
            logger.info("Applied testing URL defaults with test-specific ports")
            
        # For development, keep localhost defaults (they are appropriate)
        
        # Load critical environment variables that might be available
        try:
            from shared.isolated_environment import IsolatedEnvironment
            env = IsolatedEnvironment()
            
            # Try to load critical configuration from environment
            critical_vars = {
                'JWT_SECRET_KEY': 'jwt_secret_key',
                'SERVICE_SECRET': 'service_secret', 
                'FERNET_KEY': 'fernet_key',
                'SECRET_KEY': 'secret_key',
                'REDIS_URL': 'redis_url',
                'CLICKHOUSE_URL': 'clickhouse_url'
            }
            
            for env_var, config_attr in critical_vars.items():
                value = env.get(env_var)
                if value and hasattr(fallback_config, config_attr):
                    setattr(fallback_config, config_attr, value)
                    logger.debug(f"Loaded {env_var} from environment into fallback config")
                    
        except Exception as env_error:
            logger.warning(f"Failed to load environment variables into fallback config: {env_error}")
        
        logger.warning(
            f"Using fallback configuration for '{environment}' environment. "
            f"Some features may not work correctly. "
            f"Original error: {error_context}"
        )
        
        return fallback_config
    
    def _validate_url_for_environment(self, url: str, url_type: str, environment: str) -> tuple[bool, str]:
        """Validate URL appropriateness for the given environment.
        
        CRITICAL FIX: Issue #938 - URL validation prevents localhost in staging/production
        
        Args:
            url: The URL to validate
            url_type: Type of URL (e.g., 'frontend_url', 'api_base_url') 
            environment: Target environment name
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not url:
            return False, f"{url_type} is required"
            
        url_lower = url.lower()
        
        # Check for localhost in staging/production
        if environment in ["staging", "production"]:
            localhost_patterns = ['localhost', '127.0.0.1', '0.0.0.0']
            for pattern in localhost_patterns:
                if pattern in url_lower:
                    return False, f"{url_type} contains '{pattern}' which is invalid for {environment} environment"
        
        # Basic URL format validation
        if not url.startswith(('http://', 'https://')):
            return False, f"{url_type} must start with http:// or https://"
            
        # Environment-specific pattern validation
        if environment == "staging":
            expected_patterns = ['staging', 'netra', 'run.app', 'gcp']
            if not any(pattern in url_lower for pattern in expected_patterns):
                return False, f"{url_type} should contain staging-appropriate patterns like: {expected_patterns}"
                
        elif environment == "production":
            # Production should not have 'staging', 'dev', or 'test' in URLs
            prohibited_patterns = ['staging', 'dev', 'test', 'localhost']  
            for pattern in prohibited_patterns:
                if pattern in url_lower:
                    return False, f"{url_type} contains '{pattern}' which is inappropriate for production"
        
        return True, ""
    
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

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.

        COMPATIBILITY METHOD: Supports UnifiedConfigurationManager.get(key, default) pattern
        for backward compatibility during SSOT migration.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Any: The configuration value or default
        """
        return self.get_config_value(key, default)

    # GOLDEN PATH REQUIRED METHODS: These methods are required by Golden Path tests
    # for $500K+ ARR protection
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration.
        
        GOLDEN PATH REQUIREMENT: Tests require this method for database connectivity validation.
        
        Returns:
            Dict[str, Any]: Database configuration dictionary
        """
        try:
            config = self.get_config()
            return {
                'database_url': getattr(config, 'database_url', None),
                'postgres_url': getattr(config, 'postgres_url', None),
                'clickhouse_url': getattr(config, 'clickhouse_url', None),
                'redis_url': getattr(config, 'redis_url', None),
            }
        except Exception as e:
            self._get_logger().error(f"Error getting database config: {e}")
            return {}
    
    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration.
        
        GOLDEN PATH REQUIREMENT: Tests require this method for auth service integration.
        
        Returns:
            Dict[str, Any]: Authentication configuration dictionary
        """
        try:
            config = self.get_config()
            return {
                'jwt_secret_key': getattr(config, 'service_secret', None) or getattr(config, 'jwt_secret_key', None),
                'auth_service_url': getattr(config, 'auth_service_url', None),
                'service_secret': getattr(config, 'service_secret', None),
            }
        except Exception as e:
            self._get_logger().error(f"Error getting auth config: {e}")
            return {}
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration.
        
        GOLDEN PATH REQUIREMENT: Tests require this method for cache connectivity validation.
        
        Returns:
            Dict[str, Any]: Redis configuration dictionary
        """
        try:
            config = self.get_config()
            return {
                'redis_url': getattr(config, 'redis_url', None),
                'cache_ttl': getattr(config, 'cache_ttl', 3600),
            }
        except Exception as e:
            self._get_logger().error(f"Error getting redis config: {e}")
            return {}
    
    def get_environment(self) -> str:
        """Get current environment name.
        
        GOLDEN PATH REQUIREMENT: Tests require this method for environment detection.
        
        Returns:
            str: Environment name (development, staging, production, testing)
        """
        return self._get_environment()


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


def get(key: str, default: Any = None) -> Any:
    """Get configuration value by key.

    COMPATIBILITY FUNCTION: Supports UnifiedConfigurationManager.get(key, default) pattern
    for backward compatibility during SSOT migration.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Any: The configuration value or default
    """
    return config_manager.get(key, default)


# GOLDEN PATH REQUIRED MODULE FUNCTIONS
def get_database_config():
    """Get database configuration.
    
    GOLDEN PATH REQUIREMENT: Module-level function for database connectivity validation.
    
    Returns:
        Dict[str, Any]: Database configuration dictionary
    """
    return config_manager.get_database_config()


def get_auth_config():
    """Get authentication configuration.
    
    GOLDEN PATH REQUIREMENT: Module-level function for auth service integration.
    
    Returns:
        Dict[str, Any]: Authentication configuration dictionary
    """
    return config_manager.get_auth_config()


def get_redis_config():
    """Get Redis configuration.
    
    GOLDEN PATH REQUIREMENT: Module-level function for cache connectivity validation.
    
    Returns:
        Dict[str, Any]: Redis configuration dictionary
    """
    return config_manager.get_redis_config()


# Export compatibility functions
__all__ = [
    "UnifiedConfigManager",
    "config_manager",
    "get_unified_config",
    "get_config",  # Golden Path compatibility
    "get_config_value",  # ConfigurationManager compatibility
    "set_config_value",  # ConfigurationManager compatibility
    "validate_config_value",  # ConfigurationManager compatibility
    "get",  # UnifiedConfigurationManager compatibility
    "reload_unified_config",
    "validate_unified_config",
    "get_environment",
    "is_production",
    "is_development",
    "is_testing",
    # Golden Path required accessors
    "get_database_config",
    "get_auth_config", 
    "get_redis_config",
]