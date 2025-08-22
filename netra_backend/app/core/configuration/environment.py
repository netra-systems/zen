"""Environment Detection Module

Handles environment detection for configuration loading.
Supports development, staging, production, and testing environments.

Business Value: Ensures correct configuration loading per environment,
preventing production incidents from misconfiguration.
"""

import os
from typing import Any, Dict, Optional

from netra_backend.app.core.environment_constants import (
    Environment,
    EnvironmentConfig,
    EnvironmentDetector,
    EnvironmentVariables,
    get_current_environment,
    get_current_project_id,
)
from netra_backend.app.logging_config import central_logger as logger


class EnvironmentDetector:
    """Detects and manages the current runtime environment.
    
    Provides comprehensive environment detection including
    cloud platforms and local development.
    """
    
    def __init__(self):
        """Initialize the environment detector."""
        self._logger = logger
        self._cached_environment: Optional[str] = None
        
    def detect(self) -> str:
        """Detect the current environment.
        
        Uses centralized environment detection logic.
        
        Returns:
            str: The detected environment name
        """
        if self._cached_environment:
            return self._cached_environment
            
        environment = EnvironmentDetector.get_environment()
        self._cached_environment = environment
        self._logger.info(f"Detected environment: {environment}")
        return environment
    
    def _detect_environment(self) -> str:
        """Internal environment detection logic (deprecated).
        
        This method is kept for backward compatibility but delegates to
        the centralized EnvironmentDetector.
        """
        return EnvironmentDetector.get_environment()
    
    def _is_testing(self) -> bool:
        """Check if running in test mode (deprecated).
        
        Uses centralized testing detection logic.
        
        Returns:
            bool: True if in testing mode
        """
        return EnvironmentDetector.is_testing_context()
    
    def _detect_cloud_environment(self) -> Optional[str]:
        """Detect cloud platform environment (deprecated).
        
        Uses centralized cloud environment detection.
        
        Returns:
            Optional[str]: Environment name if cloud platform detected
        """
        return EnvironmentDetector.detect_cloud_environment()
    
    def _is_cloud_run(self) -> bool:
        """Check if running on Google Cloud Run (deprecated).
        
        Uses centralized Cloud Run detection.
        
        Returns:
            bool: True if on Cloud Run
        """
        return EnvironmentDetector.is_cloud_run()
    
    def _get_cloud_run_environment(self) -> str:
        """Get environment for Cloud Run deployment (deprecated).
        
        Uses centralized Cloud Run environment detection.
        
        Returns:
            str: Environment based on service name
        """
        return EnvironmentDetector.get_cloud_run_environment()
    
    def _is_app_engine(self) -> bool:
        """Check if running on Google App Engine (deprecated).
        
        Uses centralized App Engine detection.
        
        Returns:
            bool: True if on App Engine
        """
        return EnvironmentDetector.is_app_engine()
    
    def _get_app_engine_environment(self) -> str:
        """Get environment for App Engine deployment (deprecated).
        
        Uses centralized App Engine environment detection.
        
        Returns:
            str: Environment based on GAE settings
        """
        return EnvironmentDetector.get_app_engine_environment()
    
    def _is_aws(self) -> bool:
        """Check if running on AWS (deprecated).
        
        Uses centralized AWS detection.
        
        Returns:
            bool: True if on AWS
        """
        return EnvironmentDetector.is_aws()
    
    def _get_aws_environment(self) -> str:
        """Get environment for AWS deployment (deprecated).
        
        Uses centralized AWS environment detection.
        
        Returns:
            str: Environment based on AWS settings
        """
        return EnvironmentDetector.get_aws_environment()
    
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
        """Get environment-specific configuration defaults.
        
        Uses centralized environment configuration.
        
        Returns:
            Dict with environment-specific settings
        """
        env = self.detect()
        return EnvironmentConfig.get_environment_defaults(env)
    
    def reset_cache(self):
        """Reset the cached environment detection."""
        self._cached_environment = None


# Global instance for easy access
_environment_detector = EnvironmentDetector()


def get_environment() -> str:
    """Get the current environment.
    
    Uses centralized environment detection.
    
    Returns:
        str: The detected environment name
    """
    return get_current_environment()


def is_production() -> bool:
    """Check if running in production.
    
    Uses centralized environment detection.
    
    Returns:
        bool: True if production environment
    """
    from netra_backend.app.core.environment_constants import (
        is_production as env_is_production,
    )
    return env_is_production()


def is_development() -> bool:
    """Check if running in development.
    
    Uses centralized environment detection.
    
    Returns:
        bool: True if development environment
    """
    from netra_backend.app.core.environment_constants import (
        is_development as env_is_development,
    )
    return env_is_development()