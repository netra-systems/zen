"""Environment Detection Module

Handles environment detection for configuration loading.
Supports development, staging, production, and testing environments.

Business Value: Ensures correct configuration loading per environment,
preventing production incidents from misconfiguration.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from app.logging_config import central_logger as logger


class Environment(Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


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
        
        Priority order:
        1. TESTING environment variable (for tests)
        2. Cloud Run/App Engine detection
        3. ENVIRONMENT variable
        4. Default to development
        
        Returns:
            str: The detected environment name
        """
        if self._cached_environment:
            return self._cached_environment
            
        environment = self._detect_environment()
        self._cached_environment = environment
        self._logger.info(f"Detected environment: {environment}")
        return environment
    
    def _detect_environment(self) -> str:
        """Internal environment detection logic."""
        # Check for testing environment first
        if self._is_testing():
            return Environment.TESTING.value
            
        # Check for cloud environments
        cloud_env = self._detect_cloud_environment()
        if cloud_env:
            return cloud_env
            
        # Check explicit environment variable
        env_var = os.environ.get("ENVIRONMENT", "").lower()
        if env_var in [e.value for e in Environment]:
            return env_var
            
        # Default to development
        return Environment.DEVELOPMENT.value
    
    def _is_testing(self) -> bool:
        """Check if running in test mode.
        
        Returns:
            bool: True if in testing mode
        """
        return bool(os.environ.get("TESTING")) or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    
    def _detect_cloud_environment(self) -> Optional[str]:
        """Detect cloud platform environment.
        
        Returns:
            Optional[str]: Environment name if cloud platform detected
        """
        # Google Cloud Run detection
        if self._is_cloud_run():
            return self._get_cloud_run_environment()
            
        # Google App Engine detection
        if self._is_app_engine():
            return self._get_app_engine_environment()
            
        # AWS detection
        if self._is_aws():
            return self._get_aws_environment()
            
        return None
    
    def _is_cloud_run(self) -> bool:
        """Check if running on Google Cloud Run.
        
        Returns:
            bool: True if on Cloud Run
        """
        return bool(os.environ.get("K_SERVICE"))
    
    def _get_cloud_run_environment(self) -> str:
        """Get environment for Cloud Run deployment.
        
        Returns:
            str: Environment based on service name
        """
        service_name = os.environ.get("K_SERVICE", "")
        if "prod" in service_name.lower():
            return Environment.PRODUCTION.value
        elif "staging" in service_name.lower():
            return Environment.STAGING.value
        return Environment.DEVELOPMENT.value
    
    def _is_app_engine(self) -> bool:
        """Check if running on Google App Engine.
        
        Returns:
            bool: True if on App Engine
        """
        return bool(os.environ.get("GAE_ENV"))
    
    def _get_app_engine_environment(self) -> str:
        """Get environment for App Engine deployment.
        
        Returns:
            str: Environment based on GAE settings
        """
        gae_env = os.environ.get("GAE_ENV", "")
        if gae_env == "standard":
            return Environment.PRODUCTION.value
        return Environment.STAGING.value
    
    def _is_aws(self) -> bool:
        """Check if running on AWS.
        
        Returns:
            bool: True if on AWS
        """
        return bool(os.environ.get("AWS_EXECUTION_ENV")) or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    
    def _get_aws_environment(self) -> str:
        """Get environment for AWS deployment.
        
        Returns:
            str: Environment based on AWS settings
        """
        # Check for explicit AWS environment tag
        aws_env = os.environ.get("AWS_ENVIRONMENT", "").lower()
        if aws_env in [e.value for e in Environment]:
            return aws_env
        
        # Check Lambda function name for hints
        function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
        if "prod" in function_name.lower():
            return Environment.PRODUCTION.value
        elif "staging" in function_name.lower():
            return Environment.STAGING.value
            
        return Environment.DEVELOPMENT.value
    
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
        
        Returns:
            Dict with environment-specific settings
        """
        env = self.detect()
        
        configs = {
            Environment.PRODUCTION.value: {
                "debug": False,
                "log_level": "INFO",
                "cache_enabled": True,
                "hot_reload": False
            },
            Environment.STAGING.value: {
                "debug": False,
                "log_level": "DEBUG",
                "cache_enabled": True,
                "hot_reload": False
            },
            Environment.DEVELOPMENT.value: {
                "debug": True,
                "log_level": "DEBUG",
                "cache_enabled": False,
                "hot_reload": True
            },
            Environment.TESTING.value: {
                "debug": True,
                "log_level": "DEBUG",
                "cache_enabled": False,
                "hot_reload": False
            }
        }
        
        return configs.get(env, configs[Environment.DEVELOPMENT.value])
    
    def reset_cache(self):
        """Reset the cached environment detection."""
        self._cached_environment = None


# Global instance for easy access
_environment_detector = EnvironmentDetector()


def get_environment() -> str:
    """Get the current environment.
    
    Returns:
        str: The detected environment name
    """
    return _environment_detector.detect()


def is_production() -> bool:
    """Check if running in production.
    
    Returns:
        bool: True if production environment
    """
    return _environment_detector.is_production()


def is_development() -> bool:
    """Check if running in development.
    
    Returns:
        bool: True if development environment
    """
    return _environment_detector.is_development()