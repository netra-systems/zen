from netra_backend.app.core.isolated_environment import IsolatedEnvironment, get_env

# Always export IsolatedEnvironment for imports
__all__ = ['IsolatedEnvironment', 'get_env', 'EnvironmentDetector']

"""Environment Detection Module (DEPRECATED)

Handles environment detection for configuration loading.
Supports development, staging, production, and testing environments.

**DEPRECATION NOTICE**: This module is being phased out in favor of the unified
environment management system. New code should import from environment_constants.

Business Value: Ensures correct configuration loading per environment,
preventing production incidents from misconfiguration.
"""

import warnings
from typing import Any, Dict, Optional, Type

from netra_backend.app.core.environment_constants import (
    Environment,
    EnvironmentConfig as EnvConstants_EnvironmentConfig,
    EnvironmentDetector as Constants_EnvironmentDetector,
    EnvironmentVariables,
    get_current_environment,
    get_current_project_id,
)
from netra_backend.app.logging_config import central_logger as logger

# Issue deprecation warning for this module
warnings.warn(
    "netra_backend.app.core.configuration.environment is deprecated. "
    "Please use netra_backend.app.core.environment_constants instead.",
    DeprecationWarning,
    stacklevel=2
)


class EnvironmentDetector:
    """Detects and manages the current runtime environment.
    
    Provides comprehensive environment detection including
    cloud platforms and local development.
    """
    
    def __init__(self):
        """Initialize the environment detector (DEPRECATED).
        
        DEPRECATED: Use environment_constants.EnvironmentDetector static methods instead.
        """
        warnings.warn(
            "EnvironmentDetector class is deprecated. Use static methods from "
            "netra_backend.app.core.environment_constants.EnvironmentDetector instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._logger = logger
        self._cached_environment: Optional[str] = None
        
    def detect(self) -> str:
        """Detect the current environment (DEPRECATED).
        
        Uses centralized environment detection logic.
        
        DEPRECATED: Use get_current_environment() from environment_constants instead.
        
        Returns:
            str: The detected environment name
        """
        warnings.warn(
            "EnvironmentDetector.detect() is deprecated. Use get_current_environment() "
            "from netra_backend.app.core.environment_constants instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        if self._cached_environment:
            return self._cached_environment
            
        environment = get_environment()
        self._cached_environment = environment
        self._logger.info(f"Detected environment: {environment}")
        return environment
    
    def _detect_environment(self) -> str:
        """Internal environment detection logic (deprecated).
        
        This method is kept for backward compatibility but delegates to
        the centralized EnvironmentDetector.
        """
        return Constants_EnvironmentDetector.get_environment()
    
    def _is_testing(self) -> bool:
        """Check if running in test mode (deprecated).
        
        Uses centralized testing detection logic.
        
        Returns:
            bool: True if in testing mode
        """
        return Constants_EnvironmentDetector.is_testing_context()
    
    def _detect_cloud_environment(self) -> Optional[str]:
        """Detect cloud platform environment (deprecated).
        
        Uses centralized cloud environment detection.
        
        Returns:
            Optional[str]: Environment name if cloud platform detected
        """
        return Constants_EnvironmentDetector.detect_cloud_environment()
    
    def _is_cloud_run(self) -> bool:
        """Check if running on Google Cloud Run (deprecated).
        
        Uses centralized Cloud Run detection.
        
        Returns:
            bool: True if on Cloud Run
        """
        return Constants_EnvironmentDetector.is_cloud_run()
    
    def _get_cloud_run_environment(self) -> str:
        """Get environment for Cloud Run deployment (deprecated).
        
        Uses centralized Cloud Run environment detection.
        
        Returns:
            str: Environment based on service name
        """
        return Constants_EnvironmentDetector.get_cloud_run_environment()
    
    def _is_app_engine(self) -> bool:
        """Check if running on Google App Engine (deprecated).
        
        Uses centralized App Engine detection.
        
        Returns:
            bool: True if on App Engine
        """
        return Constants_EnvironmentDetector.is_app_engine()
    
    def _get_app_engine_environment(self) -> str:
        """Get environment for App Engine deployment (deprecated).
        
        Uses centralized App Engine environment detection.
        
        Returns:
            str: Environment based on GAE settings
        """
        return Constants_EnvironmentDetector.get_app_engine_environment()
    
    def _is_aws(self) -> bool:
        """Check if running on AWS (deprecated).
        
        Uses centralized AWS detection.
        
        Returns:
            bool: True if on AWS
        """
        return Constants_EnvironmentDetector.is_aws()
    
    def _get_aws_environment(self) -> str:
        """Get environment for AWS deployment (deprecated).
        
        Uses centralized AWS environment detection.
        
        Returns:
            str: Environment based on AWS settings
        """
        return Constants_EnvironmentDetector.get_aws_environment()
    
    def is_production(self) -> bool:
        """Check if current environment is production.
        
        Returns:
            bool: True if production
        """
        return self.detect() == Environment.PRODUCTION.value
    
    def is_staging(self) -> bool:
        """Check if current environment is staging.
        
        Returns:
            bool: True if staging
        """
        return self.detect() == Environment.STAGING.value
    
    def is_development(self) -> bool:
        """Check if current environment is development.
        
        Returns:
            bool: True if development
        """
        return self.detect() == Environment.DEVELOPMENT.value
    
    def is_testing(self) -> bool:
        """Check if current environment is testing.
        
        Returns:
            bool: True if testing
        """
        return self.detect() == Environment.TESTING.value
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration defaults (DEPRECATED).
        
        Uses centralized environment configuration.
        
        DEPRECATED: Use EnvironmentConfig.get_environment_defaults() from environment_constants.
        
        Returns:
            Dict with environment-specific settings
        """
        warnings.warn(
            "EnvironmentDetector.get_environment_config() is deprecated. Use "
            "EnvironmentConfig.get_environment_defaults() from environment_constants instead.",
            DeprecationWarning,
            stacklevel=2
        )
        env = self.detect()
        return EnvConstants_EnvironmentConfig.get_environment_defaults(env)
    
    def reset_cache(self):
        """Reset the cached environment detection."""
        self._cached_environment = None


# Global instance for easy access
_environment_detector = EnvironmentDetector()


def get_environment() -> str:
    """Get the current environment (DEPRECATED).
    
    Uses centralized environment detection.
    
    DEPRECATED: Use get_current_environment() from environment_constants instead.
    
    Returns:
        str: The detected environment name
    """
    warnings.warn(
        "get_environment() from configuration.environment is deprecated. Use "
        "get_current_environment() from environment_constants instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_current_environment()


def is_production() -> bool:
    """Check if running in production (DEPRECATED).
    
    Uses centralized environment detection.
    
    DEPRECATED: Use is_production() from environment_constants instead.
    
    Returns:
        bool: True if production environment
    """
    warnings.warn(
        "is_production() from configuration.environment is deprecated. Use "
        "is_production() from environment_constants instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from netra_backend.app.core.environment_constants import (
        is_production as env_is_production,
    )
    return env_is_production()


def is_development() -> bool:
    """Check if running in development (DEPRECATED).
    
    Uses centralized environment detection.
    
    DEPRECATED: Use is_development() from environment_constants instead.
    
    Returns:
        bool: True if development environment
    """
    warnings.warn(
        "is_development() from configuration.environment is deprecated. Use "
        "is_development() from environment_constants instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from netra_backend.app.core.environment_constants import (
        is_development as env_is_development,
    )
    return env_is_development()


class ConfigEnvironment:
    """Configuration environment manager for creating environment-specific configs.
    
    Provides methods to detect environment and create appropriate configuration
    objects based on the detected environment.
    
    Business Value: Ensures correct configuration instantiation per environment,
    preventing misconfiguration-related incidents.
    """
    
    def __init__(self):
        """Initialize the configuration environment manager."""
        self._logger = logger
    
    def get_environment(self) -> str:
        """Get the current environment.
        
        Returns:
            str: The detected environment name
        """
        return get_current_environment()
    
    def create_base_config(self, environment: str) -> 'AppConfig':
        """Create the appropriate configuration object for the given environment.
        
        Args:
            environment: The environment name
            
        Returns:
            AppConfig: The configuration object for the environment
        """
        from netra_backend.app.schemas.config import (
            AppConfig,
            DevelopmentConfig,
            NetraTestingConfig,
            ProductionConfig,
            StagingConfig,
        )
        
        config_classes = self._get_config_classes()
        config = self._init_config(config_classes, environment)
        
        # Handle WebSocket URL updates if SERVER_PORT is set
        self._update_websocket_url_if_needed(config)
        
        return config
    
    def _get_config_classes(self) -> Dict[str, Type['AppConfig']]:
        """Get the mapping of environment names to configuration classes.
        
        Returns:
            Dict mapping environment names to config classes
        """
        from netra_backend.app.schemas.config import (
            DevelopmentConfig,
            NetraTestingConfig,
            ProductionConfig,
            StagingConfig,
        )
        
        return {
            Environment.PRODUCTION.value: ProductionConfig,
            Environment.STAGING.value: StagingConfig,
            Environment.TESTING.value: NetraTestingConfig,
            Environment.DEVELOPMENT.value: DevelopmentConfig,
        }
    
    def _init_config(self, config_classes: Dict[str, Type['AppConfig']], environment: str) -> 'AppConfig':
        """Initialize the configuration object for the given environment.
        
        Args:
            config_classes: Mapping of environment names to config classes
            environment: The environment name
            
        Returns:
            AppConfig: The initialized configuration object
        """
        from netra_backend.app.schemas.config import DevelopmentConfig
        
        # Get the appropriate config class, fallback to DevelopmentConfig
        config_class = config_classes.get(environment, DevelopmentConfig)
        
        # Initialize the configuration object
        return config_class()
    
    def _update_websocket_url_if_needed(self, config: 'AppConfig') -> None:
        """Update WebSocket URL if SERVER_PORT is set in environment.
        
        Args:
            config: The configuration object to update
        """
        server_port = get_env().get("SERVER_PORT")
        if server_port and hasattr(config, 'ws_config'):
            old_url = config.ws_config.ws_url
            config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
            self._logger.info(f"WebSocket URL updated from {old_url} to {config.ws_config.ws_url} for port {server_port}")
        elif server_port:
            self._logger.debug(f"SERVER_PORT={server_port} set but config has no ws_config attribute")