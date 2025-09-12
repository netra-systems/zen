"""
Authentication Configuration Management

Business Value Justification:
- Segment: Platform/Infrastructure - Configuration Management
- Business Goal: Centralized auth configuration for WebSocket 1011 remediation
- Value Impact: Provides unified configuration management for permissive auth system
- Revenue Impact: Ensures consistent auth behavior across environments protecting $500K+ ARR

CRITICAL MISSION:
Provide centralized configuration management for the authentication permissiveness and 
circuit breaker systems, enabling environment-specific auth behavior while maintaining
security boundaries and operational flexibility.

ARCHITECTURE:
- AuthPermissivenessConfig: Configuration data class for auth settings
- AuthConfigLoader: Loads configuration from environment and app config
- Environment-aware defaults: Production strict, staging/dev permissive
- Circuit breaker configuration: Failure thresholds and recovery settings
- Runtime configuration validation and updates

INTEGRATION POINTS:
- netra_backend.app.schemas.config.AppConfig: Main config integration
- Environment variables: Override defaults per environment
- Auth permissiveness system: Runtime configuration consumption
- Circuit breaker: Dynamic threshold and timeout configuration
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.configuration.base import get_unified_config
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


@dataclass
class AuthPermissivenessConfig:
    """Configuration for authentication permissiveness system."""
    
    # System-wide toggles
    permissiveness_enabled: bool = True
    circuit_breaker_enabled: bool = True
    
    # Authentication modes
    strict_mode: Optional[bool] = None  # None = auto-detect
    demo_mode: Optional[bool] = None    # None = auto-detect
    emergency_mode: bool = False
    
    # Circuit breaker settings
    failure_threshold: int = 5
    failure_rate_threshold: float = 0.5  # 50%
    failure_window_seconds: int = 60
    open_timeout_seconds: int = 30
    half_open_max_requests: int = 3
    success_threshold: int = 3
    degradation_timeout: int = 300  # 5 minutes
    
    # Fallback settings
    relaxed_fallback_enabled: bool = True
    demo_fallback_enabled: bool = True
    emergency_fallback_enabled: bool = True
    
    # Environment detection
    environment: str = "development"
    is_production: bool = False
    is_cloud_run: bool = False
    
    # Runtime configuration
    _runtime_overrides: Dict[str, Any] = field(default_factory=dict)
    
    def get_effective_strict_mode(self) -> bool:
        """Get effective strict mode considering environment and overrides."""
        if "strict_mode" in self._runtime_overrides:
            return self._runtime_overrides["strict_mode"]
        
        if self.strict_mode is not None:
            return self.strict_mode
        
        # Auto-detect: production is always strict
        return self.is_production
    
    def get_effective_demo_mode(self) -> bool:
        """Get effective demo mode considering environment and overrides."""
        if "demo_mode" in self._runtime_overrides:
            return self._runtime_overrides["demo_mode"]
        
        if self.demo_mode is not None:
            return self.demo_mode
        
        # Auto-detect from environment
        env = get_env()
        return env.get("DEMO_MODE", "1") == "1" and not self.is_production
    
    def get_effective_emergency_mode(self) -> bool:
        """Get effective emergency mode considering overrides."""
        if "emergency_mode" in self._runtime_overrides:
            return self._runtime_overrides["emergency_mode"]
        
        return self.emergency_mode or get_env().get("EMERGENCY_MODE", "0") == "1"
    
    def update_runtime_setting(self, key: str, value: Any):
        """Update runtime configuration setting."""
        old_value = self._runtime_overrides.get(key)
        self._runtime_overrides[key] = value
        
        logger.info(f"AUTH CONFIG: Runtime setting updated - {key}: {old_value} -> {value}")
    
    def clear_runtime_overrides(self):
        """Clear all runtime configuration overrides."""
        if self._runtime_overrides:
            logger.info(f"AUTH CONFIG: Clearing {len(self._runtime_overrides)} runtime overrides")
            self._runtime_overrides.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            # System settings
            "permissiveness_enabled": self.permissiveness_enabled,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            
            # Mode settings (effective values)
            "strict_mode": self.get_effective_strict_mode(),
            "demo_mode": self.get_effective_demo_mode(),
            "emergency_mode": self.get_effective_emergency_mode(),
            
            # Circuit breaker settings
            "failure_threshold": self.failure_threshold,
            "failure_rate_threshold": self.failure_rate_threshold,
            "failure_window_seconds": self.failure_window_seconds,
            "open_timeout_seconds": self.open_timeout_seconds,
            "half_open_max_requests": self.half_open_max_requests,
            "success_threshold": self.success_threshold,
            "degradation_timeout": self.degradation_timeout,
            
            # Fallback settings
            "relaxed_fallback_enabled": self.relaxed_fallback_enabled,
            "demo_fallback_enabled": self.demo_fallback_enabled,
            "emergency_fallback_enabled": self.emergency_fallback_enabled,
            
            # Environment info
            "environment": self.environment,
            "is_production": self.is_production,
            "is_cloud_run": self.is_cloud_run,
            
            # Runtime overrides
            "runtime_overrides": dict(self._runtime_overrides)
        }


class AuthConfigLoader:
    """Loads authentication configuration from unified config and environment."""
    
    def __init__(self):
        self._cached_config: Optional[AuthPermissivenessConfig] = None
        self._config_version = 0
    
    def load_config(self, force_reload: bool = False) -> AuthPermissivenessConfig:
        """
        Load authentication configuration from unified config system.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            AuthPermissivenessConfig: Loaded configuration
        """
        if self._cached_config is not None and not force_reload:
            return self._cached_config
        
        try:
            # Load from unified config system
            app_config = get_unified_config()
            env = get_env()
            
            # Build configuration
            config = AuthPermissivenessConfig(
                # System toggles from app config
                permissiveness_enabled=getattr(app_config, 'auth_permissiveness_enabled', True),
                circuit_breaker_enabled=getattr(app_config, 'auth_circuit_breaker_enabled', True),
                
                # Mode settings from app config (None = auto-detect)
                strict_mode=getattr(app_config, 'auth_strict_mode', None),
                demo_mode=getattr(app_config, 'auth_demo_mode', None),
                emergency_mode=getattr(app_config, 'auth_emergency_mode', False),
                
                # Circuit breaker settings from app config
                failure_threshold=getattr(app_config, 'auth_failure_threshold', 5),
                failure_rate_threshold=getattr(app_config, 'auth_failure_rate_threshold', 0.5),
                open_timeout_seconds=getattr(app_config, 'auth_circuit_open_timeout', 30),
                
                # Fallback settings from app config
                relaxed_fallback_enabled=getattr(app_config, 'auth_relaxed_fallback_enabled', True),
                demo_fallback_enabled=getattr(app_config, 'auth_demo_fallback_enabled', True),
                emergency_fallback_enabled=getattr(app_config, 'auth_emergency_fallback_enabled', True),
                
                # Environment detection
                environment=getattr(app_config, 'environment', 'development'),
                is_production=getattr(app_config, 'environment', 'development').lower() in ['production', 'prod'],
                is_cloud_run=bool(env.get('K_SERVICE'))
            )
            
            # Apply environment variable overrides
            self._apply_env_overrides(config, env)
            
            # Cache configuration
            self._cached_config = config
            self._config_version += 1
            
            logger.info(f"AUTH CONFIG: Configuration loaded (version {self._config_version}) - "
                       f"permissive={config.permissiveness_enabled}, "
                       f"circuit_breaker={config.circuit_breaker_enabled}, "
                       f"environment={config.environment}")
            
            return config
            
        except Exception as e:
            logger.error(f"AUTH CONFIG: Failed to load configuration: {e}")
            
            # Return safe defaults on failure
            return AuthPermissivenessConfig(
                environment="unknown",
                is_production=True,  # Safe default - be strict
                strict_mode=True,    # Safe default - no bypass
                demo_mode=False,     # Safe default - no demo mode
                emergency_mode=False # Safe default - no emergency bypass
            )
    
    def _apply_env_overrides(self, config: AuthPermissivenessConfig, env: Any):
        """Apply environment variable overrides to configuration."""
        
        # System toggles
        if env.get("AUTH_PERMISSIVENESS_ENABLED") is not None:
            config.permissiveness_enabled = env.get("AUTH_PERMISSIVENESS_ENABLED") == "1"
        
        if env.get("AUTH_CIRCUIT_BREAKER_ENABLED") is not None:
            config.circuit_breaker_enabled = env.get("AUTH_CIRCUIT_BREAKER_ENABLED") == "1"
        
        # Mode overrides
        if env.get("AUTH_STRICT_MODE") is not None:
            config.strict_mode = env.get("AUTH_STRICT_MODE") == "1"
        
        if env.get("DEMO_MODE") is not None:
            config.demo_mode = env.get("DEMO_MODE") == "1"
        
        if env.get("EMERGENCY_MODE") is not None:
            config.emergency_mode = env.get("EMERGENCY_MODE") == "1"
        
        # Circuit breaker thresholds
        if env.get("AUTH_FAILURE_THRESHOLD"):
            try:
                config.failure_threshold = int(env.get("AUTH_FAILURE_THRESHOLD"))
            except ValueError:
                logger.warning("AUTH CONFIG: Invalid AUTH_FAILURE_THRESHOLD, using default")
        
        if env.get("AUTH_FAILURE_RATE_THRESHOLD"):
            try:
                config.failure_rate_threshold = float(env.get("AUTH_FAILURE_RATE_THRESHOLD"))
            except ValueError:
                logger.warning("AUTH CONFIG: Invalid AUTH_FAILURE_RATE_THRESHOLD, using default")
        
        if env.get("AUTH_CIRCUIT_OPEN_TIMEOUT"):
            try:
                config.open_timeout_seconds = int(env.get("AUTH_CIRCUIT_OPEN_TIMEOUT"))
            except ValueError:
                logger.warning("AUTH CONFIG: Invalid AUTH_CIRCUIT_OPEN_TIMEOUT, using default")
        
        # Fallback toggles
        if env.get("AUTH_RELAXED_FALLBACK_ENABLED") is not None:
            config.relaxed_fallback_enabled = env.get("AUTH_RELAXED_FALLBACK_ENABLED") == "1"
        
        if env.get("AUTH_DEMO_FALLBACK_ENABLED") is not None:
            config.demo_fallback_enabled = env.get("AUTH_DEMO_FALLBACK_ENABLED") == "1"
        
        if env.get("AUTH_EMERGENCY_FALLBACK_ENABLED") is not None:
            config.emergency_fallback_enabled = env.get("AUTH_EMERGENCY_FALLBACK_ENABLED") == "1"
    
    def reload_config(self) -> AuthPermissivenessConfig:
        """Force reload configuration from sources."""
        return self.load_config(force_reload=True)
    
    def get_config_version(self) -> int:
        """Get current configuration version for change detection."""
        return self._config_version


# Global configuration loader instance
_auth_config_loader: Optional[AuthConfigLoader] = None


def get_auth_config_loader() -> AuthConfigLoader:
    """Get the global auth configuration loader instance."""
    global _auth_config_loader
    if _auth_config_loader is None:
        _auth_config_loader = AuthConfigLoader()
        logger.info("AUTH CONFIG: Configuration loader instance created")
    return _auth_config_loader


def get_auth_permissiveness_config() -> AuthPermissivenessConfig:
    """
    Get the current authentication permissiveness configuration.
    
    This is the main entry point for accessing auth configuration throughout
    the authentication permissiveness system.
    
    Returns:
        AuthPermissivenessConfig: Current configuration
    """
    loader = get_auth_config_loader()
    return loader.load_config()


def reload_auth_config() -> AuthPermissivenessConfig:
    """
    Force reload authentication configuration from sources.
    
    Returns:
        AuthPermissivenessConfig: Reloaded configuration
    """
    loader = get_auth_config_loader()
    return loader.reload_config()


def update_auth_runtime_setting(key: str, value: Any) -> bool:
    """
    Update a runtime authentication setting.
    
    Args:
        key: Setting key to update
        value: New value
        
    Returns:
        bool: True if successful
    """
    try:
        config = get_auth_permissiveness_config()
        config.update_runtime_setting(key, value)
        logger.info(f"AUTH CONFIG: Runtime setting updated - {key}: {value}")
        return True
    except Exception as e:
        logger.error(f"AUTH CONFIG: Failed to update runtime setting {key}: {e}")
        return False


def get_auth_config_status() -> Dict[str, Any]:
    """Get authentication configuration status for monitoring."""
    try:
        config = get_auth_permissiveness_config()
        loader = get_auth_config_loader()
        
        return {
            "auth_config": config.to_dict(),
            "config_version": loader.get_config_version(),
            "loader_status": "operational",
            "timestamp": logger.info.__defaults__[0] if hasattr(logger.info, '__defaults__') else "unknown"
        }
    except Exception as e:
        logger.error(f"AUTH CONFIG: Failed to get status: {e}")
        return {
            "auth_config": None,
            "config_version": 0,
            "loader_status": "error",
            "error": str(e)
        }


# Configuration validation functions
def validate_auth_config(config: AuthPermissivenessConfig) -> Dict[str, Any]:
    """
    Validate authentication configuration for consistency and security.
    
    Args:
        config: Configuration to validate
        
    Returns:
        Dict with validation results
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "security_issues": []
    }
    
    # Validate circuit breaker thresholds
    if config.failure_threshold <= 0:
        validation_result["errors"].append("failure_threshold must be positive")
        validation_result["valid"] = False
    
    if not (0.0 <= config.failure_rate_threshold <= 1.0):
        validation_result["errors"].append("failure_rate_threshold must be between 0.0 and 1.0")
        validation_result["valid"] = False
    
    if config.open_timeout_seconds <= 0:
        validation_result["errors"].append("open_timeout_seconds must be positive")
        validation_result["valid"] = False
    
    # Security validations
    if config.is_production and config.get_effective_demo_mode():
        validation_result["security_issues"].append("Demo mode enabled in production environment")
        validation_result["valid"] = False
    
    if config.is_production and config.get_effective_emergency_mode():
        validation_result["warnings"].append("Emergency mode enabled in production - review immediately")
    
    if not config.get_effective_strict_mode() and config.is_production:
        validation_result["security_issues"].append("Non-strict mode in production environment")
        validation_result["warnings"].append("Production should use strict authentication")
    
    # Operational validations
    if not config.permissiveness_enabled:
        validation_result["warnings"].append("Auth permissiveness disabled - WebSocket 1011 errors may occur")
    
    if not config.circuit_breaker_enabled:
        validation_result["warnings"].append("Auth circuit breaker disabled - no graceful degradation")
    
    return validation_result


# Export public interface
__all__ = [
    "AuthPermissivenessConfig",
    "AuthConfigLoader",
    "get_auth_config_loader",
    "get_auth_permissiveness_config",
    "reload_auth_config", 
    "update_auth_runtime_setting",
    "get_auth_config_status",
    "validate_auth_config"
]