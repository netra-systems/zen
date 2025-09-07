"""Environment Detection and Configuration Consistency (DEPRECATED)

DEPRECATION NOTICE: This module is deprecated in favor of environment_constants.py
which provides the unified environment management system. New code should use
environment_constants instead.

Provides unified environment detection and ensures configuration consistency
across all services and components. Prevents environment-specific health check failures.

Business Value: Eliminates configuration drift between environments.
Ensures staging mirrors production behavior for reliable deployments.
"""

import os
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Issue deprecation warning for this entire module
warnings.warn(
    "netra_backend.app.core.configuration.environment_detector is deprecated. "
    "Use netra_backend.app.core.environment_constants instead for unified "
    "environment management.",
    DeprecationWarning,
    stacklevel=2
)


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration parameters."""
    environment: Environment
    debug_mode: bool
    log_level: str
    health_check_timeout: float
    circuit_breaker_aggressive: bool
    external_service_timeout: float
    database_pool_size: int
    redis_enabled: bool
    clickhouse_required: bool
    ssl_required: bool
    
    @classmethod
    def create_for_environment(cls, env: Environment) -> 'EnvironmentConfig':
        """Create configuration for specific environment."""
        configs = {
            Environment.DEVELOPMENT: cls(
                environment=env,
                debug_mode=True,
                log_level="DEBUG",
                health_check_timeout=10.0,
                circuit_breaker_aggressive=False,
                external_service_timeout=30.0,
                database_pool_size=5,
                redis_enabled=False,  # Optional in dev
                clickhouse_required=False,  # Optional in dev
                ssl_required=False
            ),
            Environment.STAGING: cls(
                environment=env,
                debug_mode=False,
                log_level="INFO",
                health_check_timeout=8.0,
                circuit_breaker_aggressive=True,
                external_service_timeout=15.0,
                database_pool_size=10,
                redis_enabled=True,
                clickhouse_required=False,  # Optional in staging
                ssl_required=True
            ),
            Environment.PRODUCTION: cls(
                environment=env,
                debug_mode=False,
                log_level="INFO",
                health_check_timeout=5.0,
                circuit_breaker_aggressive=True,
                external_service_timeout=10.0,
                database_pool_size=20,
                redis_enabled=True,
                clickhouse_required=True,  # Required in production
                ssl_required=True
            ),
            Environment.TESTING: cls(
                environment=env,
                debug_mode=True,
                log_level="WARNING",
                health_check_timeout=30.0,
                circuit_breaker_aggressive=False,
                external_service_timeout=60.0,
                database_pool_size=2,
                redis_enabled=False,
                clickhouse_required=False,
                ssl_required=False
            )
        }
        return configs.get(env, configs[Environment.PRODUCTION])


class EnvironmentDetector:
    """Detects and validates current deployment environment."""
    
    def __init__(self):
        """Initialize environment detector."""
        self._detected_environment: Optional[Environment] = None
        self._environment_config: Optional[EnvironmentConfig] = None
        self._detection_cache: Dict[str, Any] = {}
    
    def detect_environment(self) -> Environment:
        """Detect current environment from multiple sources."""
        if self._detected_environment is not None:
            return self._detected_environment
        
        # Priority order for environment detection
        env_sources = [
            self._detect_from_env_var,
            self._detect_from_hostname,
            self._detect_from_database_url,
            self._detect_from_service_context
        ]
        
        for detector in env_sources:
            try:
                env = detector()
                if env:
                    logger.info(f"Environment detected as '{env.value}' via {detector.__name__}")
                    self._detected_environment = env
                    return env
            except Exception as e:
                logger.debug(f"Environment detection failed for {detector.__name__}: {e}")
        
        # Default fallback
        logger.warning("Environment detection failed, defaulting to production")
        self._detected_environment = Environment.PRODUCTION
        return self._detected_environment
    
    def _detect_from_env_var(self) -> Optional[Environment]:
        """Detect environment from ENVIRONMENT variable."""
        env_var = get_env().get("ENVIRONMENT", "").lower()
        if not env_var:
            return None
        
        env_mapping = {
            "dev": Environment.DEVELOPMENT,
            "development": Environment.DEVELOPMENT,
            "stage": Environment.STAGING,
            "staging": Environment.STAGING,
            "prod": Environment.PRODUCTION,
            "production": Environment.PRODUCTION,
            "test": Environment.TESTING,
            "testing": Environment.TESTING
        }
        
        return env_mapping.get(env_var)
    
    def _detect_from_hostname(self) -> Optional[Environment]:
        """Detect environment from hostname patterns."""
        import socket
        
        try:
            hostname = socket.gethostname().lower()
            
            if any(pattern in hostname for pattern in ["dev", "development", "local"]):
                return Environment.DEVELOPMENT
            elif any(pattern in hostname for pattern in ["stage", "staging"]):
                return Environment.STAGING
            elif any(pattern in hostname for pattern in ["prod", "production"]):
                return Environment.PRODUCTION
            elif any(pattern in hostname for pattern in ["test", "testing"]):
                return Environment.TESTING
                
        except Exception:
            pass
        
        return None
    
    def _detect_from_database_url(self) -> Optional[Environment]:
        """Detect environment from database URL patterns."""
        db_url = get_env().get("DATABASE_URL", "").lower()
        if not db_url:
            return None
        
        if any(pattern in db_url for pattern in ["localhost", "127.0.0.1", "dev"]):
            return Environment.DEVELOPMENT
        elif "staging" in db_url:
            return Environment.STAGING
        elif any(pattern in db_url for pattern in ["prod", "production"]):
            return Environment.PRODUCTION
        elif "test" in db_url:
            return Environment.TESTING
        
        return None
    
    def _detect_from_service_context(self) -> Optional[Environment]:
        """Detect environment from service context (GCP, AWS, etc.)."""
        # Check for GCP metadata
        gcp_project = get_env().get("GOOGLE_CLOUD_PROJECT", "").lower()
        if gcp_project:
            if "staging" in gcp_project:
                return Environment.STAGING
            elif "prod" in gcp_project:
                return Environment.PRODUCTION
        
        # Check for Kubernetes context
        k8s_namespace = get_env().get("K8S_NAMESPACE", "").lower()
        if k8s_namespace:
            if "staging" in k8s_namespace:
                return Environment.STAGING
            elif "prod" in k8s_namespace:
                return Environment.PRODUCTION
        
        return None
    
    def get_environment_config(self) -> EnvironmentConfig:
        """Get configuration for detected environment."""
        if self._environment_config is None:
            env = self.detect_environment()
            self._environment_config = EnvironmentConfig.create_for_environment(env)
        return self._environment_config
    
    def validate_environment_consistency(self) -> Tuple[bool, List[str]]:
        """Validate that current configuration is consistent with detected environment."""
        issues = []
        env_config = self.get_environment_config()
        
        # Validate SSL requirements
        if env_config.ssl_required:
            db_url = get_env().get("DATABASE_URL", "")
            if db_url and "sslmode=" not in db_url and "ssl=" not in db_url:
                issues.append(f"SSL required for {env_config.environment.value} but #removed-legacyhas no SSL config")
        
        # Validate service requirements
        if env_config.clickhouse_required:
            clickhouse_url = get_env().get("CLICKHOUSE_URL", "")
            if not clickhouse_url:
                issues.append(f"ClickHouse required for {env_config.environment.value} but CLICKHOUSE_URL not set")
        
        if env_config.redis_enabled:
            redis_url = get_env().get("REDIS_URL", "")
            if not redis_url:
                issues.append(f"Redis enabled for {env_config.environment.value} but REDIS_URL not set")
        
        # Validate debug mode consistency
        debug_env = get_env().get("DEBUG", "false").lower() == "true"
        if debug_env != env_config.debug_mode:
            issues.append(f"DEBUG environment variable ({debug_env}) inconsistent with environment ({env_config.debug_mode})")
        
        return len(issues) == 0, issues
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get comprehensive environment information for debugging."""
        env = self.detect_environment()
        config = self.get_environment_config()
        is_consistent, issues = self.validate_environment_consistency()
        
        return {
            "detected_environment": env.value,
            "configuration": {
                "debug_mode": config.debug_mode,
                "log_level": config.log_level,
                "health_check_timeout": config.health_check_timeout,
                "circuit_breaker_aggressive": config.circuit_breaker_aggressive,
                "ssl_required": config.ssl_required
            },
            "consistency_check": {
                "is_consistent": is_consistent,
                "issues": issues
            },
            "environment_variables": {
                "ENVIRONMENT": get_env().get("ENVIRONMENT"),
                "DATABASE_URL": self._mask_sensitive_url(get_env().get("DATABASE_URL", "")),
                "CLICKHOUSE_URL": self._mask_sensitive_url(get_env().get("CLICKHOUSE_URL", "")),
                "REDIS_URL": self._mask_sensitive_url(get_env().get("REDIS_URL", "")),
                "DEBUG": get_env().get("DEBUG")
            }
        }
    
    def _mask_sensitive_url(self, url: str) -> str:
        """Mask sensitive information in URLs for logging."""
        if not url:
            return ""
        
        # Mask password in URL if present
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
    
    def should_require_service(self, service_name: str) -> bool:
        """Check if a service should be required in current environment."""
        config = self.get_environment_config()
        
        service_requirements = {
            "clickhouse": config.clickhouse_required,
            "redis": config.redis_enabled,
            "ssl": config.ssl_required
        }
        
        return service_requirements.get(service_name.lower(), False)
    
    def get_health_check_timeout(self) -> float:
        """Get appropriate health check timeout for current environment."""
        config = self.get_environment_config()
        return config.health_check_timeout


# Global instance
_environment_detector: Optional[EnvironmentDetector] = None


def get_environment_detector() -> EnvironmentDetector:
    """Get global environment detector instance."""
    global _environment_detector
    if _environment_detector is None:
        _environment_detector = EnvironmentDetector()
    return _environment_detector


def get_current_environment() -> Environment:
    """Get current detected environment (DEPRECATED).
    
    DEPRECATED: Use get_current_environment() from environment_constants instead.
    """
    warnings.warn(
        "get_current_environment() from environment_detector is deprecated. Use "
        "get_current_environment() from environment_constants instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_environment_detector().detect_environment()


def get_environment_config() -> EnvironmentConfig:
    """Get configuration for current environment."""
    return get_environment_detector().get_environment_config()


def validate_environment() -> Tuple[bool, List[str]]:
    """Validate current environment configuration."""
    return get_environment_detector().validate_environment_consistency()