"""Environment Constants Module

Single source of truth for all environment-related constants and utilities.
Eliminates hardcoded environment strings throughout the codebase.

**UNIFIED CONFIGURATION INTEGRATION**: This module now integrates with the
unified configuration system while maintaining bootstrap functionality.

**BOOTSTRAP vs APPLICATION METHODS**:
- Bootstrap methods (marked BOOTSTRAP ONLY): Required for initial config system setup
- Application methods (marked APPLICATION METHOD): Use unified config when available
- Convenience functions: Automatically use unified config, fall back to bootstrap

**USAGE GUIDANCE**:
- Application code: Use convenience functions (get_current_environment(), is_production(), etc.)  
- Bootstrap/infrastructure: Use EnvironmentDetector bootstrap methods directly
- New code: Always prefer unified config integration

Business Value: Platform/Internal - Deployment Stability - Prevents deployment
errors and ensures consistent environment handling across all services.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from shared.isolated_environment import get_env

# Import unified config for non-bootstrap functionality
try:
    from netra_backend.app.core.configuration.base import get_unified_config
    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    UNIFIED_CONFIG_AVAILABLE = False


class Environment(Enum):
    """Standardized environment types.
    
    These are the ONLY valid environment types across the entire system.
    All services MUST use these constants instead of hardcoded strings.
    """
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    TESTING = "testing"

    @classmethod
    def values(cls) -> List[str]:
        """Get all environment values as a list."""
        return [e.value for e in cls]

    @classmethod
    def is_valid(cls, env: str) -> bool:
        """Check if environment string is valid."""
        return env.lower() in cls.values()


class EnvironmentVariables:
    """Standardized environment variable names.
    
    Centralized constants for all environment variable names to prevent typos
    and ensure consistency across the codebase.
    """
    # Core environment variables
    ENVIRONMENT = "ENVIRONMENT"
    TESTING = "TESTING"
    PYTEST_CURRENT_TEST = "PYTEST_CURRENT_TEST"
    
    # Service mode variables
    REDIS_MODE = "REDIS_MODE"
    CLICKHOUSE_MODE = "CLICKHOUSE_MODE"
    LLM_MODE = "LLM_MODE"
    AUTH_MODE = "AUTH_MODE"
    
    # Cloud platform variables
    K_SERVICE = "K_SERVICE"  # Google Cloud Run
    K_REVISION = "K_REVISION"  # Google Cloud Run
    GAE_ENV = "GAE_ENV"  # Google App Engine
    GAE_APPLICATION = "GAE_APPLICATION"  # Google App Engine
    GAE_VERSION = "GAE_VERSION"  # Google App Engine
    AWS_EXECUTION_ENV = "AWS_EXECUTION_ENV"  # AWS Lambda
    AWS_LAMBDA_FUNCTION_NAME = "AWS_LAMBDA_FUNCTION_NAME"  # AWS Lambda
    AWS_ENVIRONMENT = "AWS_ENVIRONMENT"  # AWS Environment tag
    KUBERNETES_SERVICE_HOST = "KUBERNETES_SERVICE_HOST"  # Kubernetes
    
    # Database environment variables
    CLICKHOUSE_HOST = "CLICKHOUSE_HOST"
    CLICKHOUSE_PORT = "CLICKHOUSE_PORT"
    CLICKHOUSE_USER = "CLICKHOUSE_USER"
    CLICKHOUSE_PASSWORD = "CLICKHOUSE_PASSWORD"
    CLICKHOUSE_DB = "CLICKHOUSE_DB"
    CLICKHOUSE_HTTP_PORT = "CLICKHOUSE_HTTP_PORT"
    CLICKHOUSE_NATIVE_PORT = "CLICKHOUSE_NATIVE_PORT"
    REDIS_URL = "REDIS_URL"
    REDIS_HOST = "REDIS_HOST"
    REDIS_PORT = "REDIS_PORT"
    REDIS_PASSWORD = "REDIS_PASSWORD"
    
    # ClickHouse password variable
    CLICKHOUSE_PASSWORD = "CLICKHOUSE_PASSWORD"
    
    # Project configuration
    GCP_PROJECT_ID_NUMERICAL_STAGING = "GCP_PROJECT_ID_NUMERICAL_STAGING"
    SECRET_MANAGER_PROJECT_ID = "SECRET_MANAGER_PROJECT_ID"
    GOOGLE_CLOUD_PROJECT = "GOOGLE_CLOUD_PROJECT"
    PR_NUMBER = "PR_NUMBER"  # For PR-based staging environments


class EnvironmentDetector:
    """Centralized environment detection logic.
    
    Provides consistent environment detection across all services.
    
    BOOTSTRAP METHODS: Static methods marked with BOOTSTRAP comments
    require direct os.environ access for initial configuration system setup.
    
    APPLICATION METHODS: Use unified config when available.
    """
    
    @staticmethod
    def get_environment() -> str:
        """Get the current environment using standardized detection logic.
        
        Priority order:
        1. Testing environment detection (TESTING variable takes highest priority)
        2. Explicit ENVIRONMENT variable
        3. Cloud platform detection
        4. Default to development
        
        Returns:
            str: The detected environment (guaranteed to be a valid Environment value)
        
        NOTE: This is a bootstrap method that requires direct os.environ access
        to initialize the configuration system. All other environment access
        should use the unified configuration system.
        """
        # BOOTSTRAP ONLY: Direct env access required for initial config loading
        # Check for testing environment first (highest priority)
        if bool(get_env().get(EnvironmentVariables.TESTING)) or bool(get_env().get(EnvironmentVariables.PYTEST_CURRENT_TEST)):
            return Environment.TESTING.value
        
        # Check explicit environment variable second
        env_var = get_env().get(EnvironmentVariables.ENVIRONMENT, "").strip().lower()
        if Environment.is_valid(env_var):
            return env_var
            
        # Check for cloud environments
        cloud_env = EnvironmentDetector.detect_cloud_environment()
        if cloud_env:
            return cloud_env
            
        # Default to development
        return Environment.DEVELOPMENT.value
    
    @staticmethod
    def is_testing_context() -> bool:
        """Check if running in test context.
        
        Returns:
            bool: True if in testing context
            
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for testing detection
        # If ENVIRONMENT is explicitly set to something other than testing, respect that
        explicit_env = get_env().get(EnvironmentVariables.ENVIRONMENT, "").lower()
        if explicit_env and explicit_env != Environment.TESTING.value:
            return False
            
        return (
            bool(get_env().get(EnvironmentVariables.TESTING)) or 
            bool(get_env().get(EnvironmentVariables.PYTEST_CURRENT_TEST))
        )
    
    @staticmethod
    def detect_cloud_environment() -> Optional[str]:
        """Detect cloud platform environment.
        
        Returns:
            Optional[str]: Environment name if cloud platform detected
        """
        # Google Cloud Run detection
        if EnvironmentDetector.is_cloud_run():
            return EnvironmentDetector.get_cloud_run_environment()
            
        # Google App Engine detection
        if EnvironmentDetector.is_app_engine():
            return EnvironmentDetector.get_app_engine_environment()
            
        # AWS detection
        if EnvironmentDetector.is_aws():
            return EnvironmentDetector.get_aws_environment()
            
        # Kubernetes detection
        if EnvironmentDetector.is_kubernetes():
            return Environment.PRODUCTION.value
            
        return None
    
    @staticmethod
    def is_cloud_run() -> bool:
        """Check if running on Google Cloud Run.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for cloud platform detection
        return bool(get_env().get(EnvironmentVariables.K_SERVICE))
    
    @staticmethod
    def get_cloud_run_environment() -> str:
        """Get environment for Cloud Run deployment.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for cloud environment detection
        service_name = get_env().get(EnvironmentVariables.K_SERVICE, "")
        if "prod" in service_name.lower():
            return Environment.PRODUCTION.value
        elif "staging" in service_name.lower():
            return Environment.STAGING.value
        
        # Check for PR-based staging
        if get_env().get(EnvironmentVariables.PR_NUMBER):
            return Environment.STAGING.value
            
        return Environment.DEVELOPMENT.value
    
    @staticmethod
    def is_app_engine() -> bool:
        """Check if running on Google App Engine.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for App Engine detection
        return bool(get_env().get(EnvironmentVariables.GAE_ENV))
    
    @staticmethod
    def get_app_engine_environment() -> str:
        """Get environment for App Engine deployment.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for App Engine environment detection
        gae_env = get_env().get(EnvironmentVariables.GAE_ENV, "")
        gae_app = get_env().get(EnvironmentVariables.GAE_APPLICATION, "")
        gae_version = get_env().get(EnvironmentVariables.GAE_VERSION, "")
        
        if "staging" in gae_app.lower() or "staging" in gae_version.lower():
            return Environment.STAGING.value
        elif gae_env == "standard":
            return Environment.PRODUCTION.value
            
        return Environment.STAGING.value
    
    @staticmethod
    def is_aws() -> bool:
        """Check if running on AWS.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for AWS detection
        return (
            bool(get_env().get(EnvironmentVariables.AWS_EXECUTION_ENV)) or 
            bool(get_env().get(EnvironmentVariables.AWS_LAMBDA_FUNCTION_NAME))
        )
    
    @staticmethod
    def get_aws_environment() -> str:
        """Get environment for AWS deployment.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for AWS environment detection
        # Check for explicit AWS environment tag
        aws_env = get_env().get(EnvironmentVariables.AWS_ENVIRONMENT, "").lower()
        if Environment.is_valid(aws_env):
            return aws_env
        
        # Check Lambda function name for hints
        function_name = get_env().get(EnvironmentVariables.AWS_LAMBDA_FUNCTION_NAME, "")
        if "prod" in function_name.lower():
            return Environment.PRODUCTION.value
        elif "staging" in function_name.lower():
            return Environment.STAGING.value
            
        return Environment.DEVELOPMENT.value
    
    @staticmethod
    def is_kubernetes() -> bool:
        """Check if running on Kubernetes.
        
        NOTE: Bootstrap method requiring direct environment access.
        """
        # BOOTSTRAP ONLY: Direct env access for Kubernetes detection
        return bool(get_env().get(EnvironmentVariables.KUBERNETES_SERVICE_HOST))
    
    # APPLICATION-FRIENDLY METHODS (Unified Config Aware)
    
    @staticmethod
    def get_environment_unified() -> str:
        """Get current environment using unified config when available.
        
        APPLICATION METHOD: Prefers unified config, falls back to bootstrap.
        Use this for application code instead of get_environment().
        """
        if UNIFIED_CONFIG_AVAILABLE:
            try:
                config = get_unified_config()
                return config.environment
            except Exception:
                # Fallback to bootstrap method if unified config fails
                pass
        
        # Bootstrap fallback
        return EnvironmentDetector.get_environment()
    
    @staticmethod
    def is_testing_context_unified() -> bool:
        """Check if running in test context using unified config when available.
        
        APPLICATION METHOD: Prefers unified config, falls back to bootstrap.
        """
        if UNIFIED_CONFIG_AVAILABLE:
            try:
                config = get_unified_config()
                # Check unified config fields first
                if config.testing or config.pytest_current_test:
                    return True
                # Check if environment is explicitly testing
                if config.environment == Environment.TESTING.value:
                    return True
                return False
            except Exception:
                # Fallback to bootstrap method if unified config fails
                pass
        
        # Bootstrap fallback
        return EnvironmentDetector.is_testing_context()
    
    @staticmethod
    def is_cloud_run_unified() -> bool:
        """Check if running on Google Cloud Run using unified config when available.
        
        APPLICATION METHOD: Prefers unified config, falls back to bootstrap.
        """
        if UNIFIED_CONFIG_AVAILABLE:
            try:
                config = get_unified_config()
                return bool(config.k_service)
            except Exception:
                # Fallback to bootstrap method if unified config fails
                pass
        
        # Bootstrap fallback
        return EnvironmentDetector.is_cloud_run()


class EnvironmentConfig:
    """Environment-specific configuration settings.
    
    Provides consistent configuration defaults across all environments.
    """
    
    @staticmethod
    def get_environment_defaults(environment: str) -> Dict[str, Any]:
        """Get environment-specific configuration defaults.
        
        Args:
            environment: The environment name
            
        Returns:
            Dict with environment-specific settings
        """
        configs = {
            Environment.PRODUCTION.value: {
                "debug": False,
                "log_level": "INFO",
                "cache_enabled": True,
                "hot_reload": False,
                "ssl_required": True,
                "secure_cookies": True
            },
            Environment.STAGING.value: {
                "debug": False,
                "log_level": "DEBUG",
                "cache_enabled": True,
                "hot_reload": False,
                "ssl_required": True,
                "secure_cookies": True
            },
            Environment.DEVELOPMENT.value: {
                "debug": True,
                "log_level": "DEBUG",
                "cache_enabled": False,
                "hot_reload": True,
                "ssl_required": False,
                "secure_cookies": False
            },
            Environment.TESTING.value: {
                "debug": True,
                "log_level": "DEBUG",
                "cache_enabled": False,
                "hot_reload": False,
                "ssl_required": False,
                "secure_cookies": False
            }
        }
        
        return configs.get(environment, configs[Environment.DEVELOPMENT.value])
    
    @staticmethod
    def get_project_id_for_environment(environment: str) -> str:
        """Get the appropriate GCP project ID for the environment.
        
        Args:
            environment: The environment name
            
        Returns:
            str: The GCP project ID
        """
        project_ids = {
            Environment.STAGING.value: "701982941522",
            Environment.PRODUCTION.value: "304612253870",
            Environment.DEVELOPMENT.value: "304612253870",  # Use prod project for dev
            Environment.TESTING.value: "304612253870"  # Use prod project for testing
        }
        
        return project_ids.get(environment, project_ids[Environment.DEVELOPMENT.value])
    
    @staticmethod
    def get_clickhouse_password_var(environment: str) -> str:
        """Get the appropriate ClickHouse password environment variable name.
        
        Args:
            environment: The environment name
            
        Returns:
            str: The environment variable name for ClickHouse password
        """
        # Use unified CLICKHOUSE_PASSWORD for all environments
        return EnvironmentVariables.CLICKHOUSE_PASSWORD


# Convenience functions for common environment checks
def get_current_environment() -> str:
    """Get the current environment using standardized detection.
    
    PREFERRED: Uses unified config when available, falls back to bootstrap.
    """
    return EnvironmentDetector.get_environment_unified()


def is_production() -> bool:
    """Check if running in production environment."""
    return get_current_environment() == Environment.PRODUCTION.value


def is_staging() -> bool:
    """Check if running in staging environment."""
    return get_current_environment() == Environment.STAGING.value


def is_development() -> bool:
    """Check if running in development environment."""
    return get_current_environment() == Environment.DEVELOPMENT.value


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_current_environment() == Environment.TESTING.value


def get_environment_config() -> Dict[str, Any]:
    """Get configuration defaults for the current environment."""
    current_env = get_current_environment()
    return EnvironmentConfig.get_environment_defaults(current_env)


def get_current_project_id() -> str:
    """Get the appropriate GCP project ID for the current environment.
    
    PREFERRED: Uses unified config when available.
    NOTE: Bootstrap method for infrastructure setup.
    For application use, prefer config.google_cloud.project_id.
    """
    if UNIFIED_CONFIG_AVAILABLE:
        try:
            config = get_unified_config()
            if config.google_cloud.project_id:
                return config.google_cloud.project_id
        except Exception:
            # Fallback to bootstrap method if unified config fails
            pass
    
    # Bootstrap fallback for initial system setup
    current_env = EnvironmentDetector.get_environment()  # Use bootstrap method directly
    
    # BOOTSTRAP ONLY: Direct env access for project ID detection
    # Check for explicit override first
    explicit_project_id = get_env().get(EnvironmentVariables.GOOGLE_CLOUD_PROJECT)
    if explicit_project_id:
        return explicit_project_id
    
    return EnvironmentConfig.get_project_id_for_environment(current_env)


def get_clickhouse_password_var_name() -> str:
    """Get the ClickHouse password environment variable name for current environment."""
    current_env = get_current_environment()
    return EnvironmentConfig.get_clickhouse_password_var(current_env)


# Import specific cloud run detection function for compatibility
try:
    from netra_backend.app.cloud_environment_detector import detect_cloud_run_environment
except ImportError:
    # Fallback implementation if cloud_environment_detector is not available
    def detect_cloud_run_environment() -> Optional[str]:
        """Fallback implementation for detect_cloud_run_environment."""
        return EnvironmentDetector.get_cloud_run_environment() if EnvironmentDetector.is_cloud_run() else None