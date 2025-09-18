"""Configuration Manager SSOT Compatibility Shim - Issue #667

BUSINESS IMPACT: Protects $500K+ ARR Golden Path functionality during SSOT migration
by providing backward compatibility for all existing configuration manager imports.

This shim ensures existing code continues to work while gradually migrating to
the Single Source of Truth configuration management pattern.

MIGRATION STRATEGY:
1. All duplicate configuration managers redirect to canonical SSOT
2. Method signature compatibility maintained across all interfaces
3. Import path compatibility preserved for zero-breakage migration
4. Deprecation warnings guide developers to SSOT patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Zero-Downtime Migration  
- Value Impact: Prevents breaking changes that could affect customer experience
- Revenue Impact: Protects $500K+ ARR by maintaining Golden Path reliability
"""

import warnings
from typing import Any

# Import the canonical SSOT configuration
from netra_backend.app.config import (
    UnifiedConfigManager as CanonicalConfigManager,
    config_manager as canonical_config_manager,
    get_config as get_unified_config,
    get_config,
    reload_config,
    validate_configuration
)

# Compatibility functions
def get_config_value(key: str, default: Any = None) -> Any:
    """Compatibility wrapper for get_config_value."""
    return canonical_config_manager.get_config_value(key, default)

def set_config_value(key: str, value: Any) -> None:
    """Compatibility wrapper for set_config_value (read-only in SSOT)."""
    warnings.warn("set_config_value is deprecated - configuration is read-only in SSOT pattern", DeprecationWarning, stacklevel=2)

def validate_config_value(key: str, value: Any) -> bool:
    """Compatibility wrapper for validate_config_value."""
    try:
        current_value = get_config_value(key)
        return current_value is not None
    except Exception:
        return False

# Configuration Manager Compatibility Classes
class ConfigurationManagerCompatibility:
    """
    Compatibility wrapper for netra_backend.app.services.configuration_service.ConfigurationManager
    
    Redirects all method calls to the canonical SSOT UnifiedConfigManager while
    maintaining exact method signature compatibility.
    """
    
    def __init__(self):
        warnings.warn(
            "ConfigurationManager from configuration_service is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.UnifiedConfigManager instead. "
            "This compatibility layer will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2
        )
        self._ssot_manager = canonical_config_manager
        self.validator = None  # Compatibility - not used in SSOT
        self._config_cache = {}  # Compatibility - not used in SSOT
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Compatibility method for ConfigurationManager.get_config()"""
        return self._ssot_manager.get_config_value(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Compatibility method for ConfigurationManager.set_config()"""
        self._ssot_manager.set_config_value(key, value)
    
    def validate_config(self) -> bool:
        """Compatibility method for ConfigurationManager.validate_config()"""
        return self._ssot_manager.validate_config_integrity()


class UnifiedConfigurationManagerCompatibility:
    """
    Compatibility wrapper for netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager
    
    Redirects all method calls to the canonical SSOT UnifiedConfigManager while
    maintaining the complex interface of the deprecated MEGA CLASS.
    """
    
    def __init__(self, user_id=None, environment=None, service_name=None, **kwargs):
        warnings.warn(
            "UnifiedConfigurationManager from core.managers.unified_configuration_manager is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.UnifiedConfigManager instead. "
            "This compatibility layer will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2
        )
        self._ssot_manager = canonical_config_manager
        self.user_id = user_id
        self.service_name = service_name
        self.environment = environment
    
    # Core interface methods
    def get(self, key: str, default: Any = None) -> Any:
        """Compatibility method for UnifiedConfigurationManager.get()"""
        return self._ssot_manager.get_config_value(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Compatibility method for UnifiedConfigurationManager.set()"""
        self._ssot_manager.set_config_value(key, value)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Compatibility method for get_config interface"""
        return self._ssot_manager.get_config_value(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Compatibility method for set_config interface"""
        self._ssot_manager.set_config_value(key, value)
    
    def validate_config(self) -> bool:
        """Compatibility method for validate_config interface"""
        return self._ssot_manager.validate_config_integrity()
    
    def get_unified_config(self):
        """Compatibility method for get_unified_config interface"""
        return get_unified_config()
    
    def reload_config(self, force: bool = False):
        """Compatibility method for reload_config interface"""
        return self._ssot_manager.reload_config(force)
    
    def validate_config_integrity(self) -> bool:
        """Compatibility method for validate_config_integrity interface"""
        return self._ssot_manager.validate_config_integrity()
    
    def get_environment_name(self) -> str:
        """Compatibility method for get_environment_name interface"""
        return self._ssot_manager.get_environment_name()
    
    def is_production(self) -> bool:
        """Compatibility method for is_production interface"""
        return self._ssot_manager.is_production()
    
    def is_development(self) -> bool:
        """Compatibility method for is_development interface"""
        return self._ssot_manager.is_development()
    
    def is_testing(self) -> bool:
        """Compatibility method for is_testing interface"""
        return self._ssot_manager.is_testing()
    
    # Service-specific config methods
    def get_database_config(self):
        """Compatibility method for get_database_config"""
        config = get_unified_config()
        return {
            'url': getattr(config, 'database_url', None),
            'pool_size': getattr(config, 'database_pool_size', 10)
        }
    
    def get_redis_config(self):
        """Compatibility method for get_redis_config"""
        config = get_unified_config()
        return {
            'url': getattr(config, 'redis_url', None)
        }
    
    def get_security_config(self):
        """Compatibility method for get_security_config"""
        config = get_unified_config()
        return {
            'jwt_secret': getattr(config, 'service_secret', None),
            'jwt_algorithm': 'HS256'
        }
    
    # Status and monitoring methods
    def get_status(self):
        """Compatibility method for get_status"""
        return {
            'user_id': self.user_id,
            'environment': self.environment,
            'service_name': self.service_name,
            'validation_enabled': True,
            'caching_enabled': True,
            'validation_status': {
                'is_valid': self._ssot_manager.validate_config_integrity()
            }
        }
    
    def get_health_status(self):
        """Compatibility method for get_health_status"""
        is_valid = self._ssot_manager.validate_config_integrity()
        return {
            'status': 'healthy' if is_valid else 'unhealthy',
            'validation_result': is_valid
        }


# Environment Config Loader Compatibility
class EnvironmentConfigLoaderCompatibility:
    """
    Compatibility wrapper for netra_backend.app.services.configuration_service.EnvironmentConfigLoader
    """
    
    def __init__(self):
        warnings.warn(
            "EnvironmentConfigLoader from configuration_service is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.get_unified_config instead. "
            "This compatibility layer will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2
        )
        self.config = {}
    
    def load_config(self):
        """Compatibility method for load_config"""
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        return env.get_all()
    
    def get_database_config(self):
        """Compatibility method for get_database_config"""
        config = get_unified_config()
        return {
            'DATABASE_URL': getattr(config, 'database_url', None),
            'DATABASE_POOL_SIZE': 10
        }
    
    def get_redis_config(self):
        """Compatibility method for get_redis_config"""
        return {
            'REDIS_URL': 'redis://localhost:6379/0'
        }


# Configuration Validator Compatibility
class ConfigurationValidatorCompatibility:
    """
    Compatibility wrapper for netra_backend.app.services.configuration_service.ConfigurationValidator
    """
    
    @staticmethod
    def validate_database_config(config):
        """Compatibility method for validate_database_config"""
        return 'DATABASE_URL' in config and bool(config.get('DATABASE_URL'))
    
    @staticmethod
    def validate_redis_config(config):
        """Compatibility method for validate_redis_config"""
        return 'REDIS_URL' in config


# Factory Pattern Compatibility
class ConfigurationManagerFactoryCompatibility:
    """
    Compatibility wrapper for factory pattern from the deprecated MEGA CLASS
    """
    
    @classmethod
    def get_global_manager(cls):
        """Compatibility method for get_global_manager"""
        warnings.warn(
            "ConfigurationManagerFactory is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.config_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return UnifiedConfigurationManagerCompatibility()
    
    @classmethod
    def get_user_manager(cls, user_id: str):
        """Compatibility method for get_user_manager"""
        warnings.warn(
            "ConfigurationManagerFactory is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.config_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return UnifiedConfigurationManagerCompatibility(user_id=user_id)
    
    @classmethod
    def get_service_manager(cls, service_name: str):
        """Compatibility method for get_service_manager"""
        warnings.warn(
            "ConfigurationManagerFactory is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.config_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return UnifiedConfigurationManagerCompatibility(service_name=service_name)
    
    @classmethod
    def get_manager(cls, user_id=None, service_name=None):
        """Compatibility method for get_manager"""
        warnings.warn(
            "ConfigurationManagerFactory is deprecated (Issue #667). "
            "Use netra_backend.app.core.configuration.base.config_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return UnifiedConfigurationManagerCompatibility(user_id=user_id, service_name=service_name)


# Export compatibility classes as standard names
ConfigurationManager = ConfigurationManagerCompatibility
UnifiedConfigurationManager = UnifiedConfigurationManagerCompatibility
EnvironmentConfigLoader = EnvironmentConfigLoaderCompatibility
ConfigurationValidator = ConfigurationValidatorCompatibility
ConfigurationManagerFactory = ConfigurationManagerFactoryCompatibility

# Export convenience functions
def get_configuration_manager(user_id=None, service_name=None):
    """Compatibility function for get_configuration_manager"""
    warnings.warn(
        "get_configuration_manager is deprecated (Issue #667). "
        "Use netra_backend.app.core.configuration.base.config_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return UnifiedConfigurationManagerCompatibility(user_id=user_id, service_name=service_name)

# Legacy compatibility factory functions
def get_dashboard_config_manager():
    """Legacy compatibility for DashboardConfigManager."""
    warnings.warn(
        "get_dashboard_config_manager is deprecated (Issue #667). "
        "Use netra_backend.app.core.configuration.base.config_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return UnifiedConfigurationManagerCompatibility(service_name="dashboard")

def get_data_agent_config_manager():
    """Legacy compatibility for DataSubAgentConfigurationManager.""" 
    warnings.warn(
        "get_data_agent_config_manager is deprecated (Issue #667). "
        "Use netra_backend.app.core.configuration.base.config_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return UnifiedConfigurationManagerCompatibility(service_name="data_agent")

def get_llm_config_manager():
    """Legacy compatibility for LLMManagerConfig."""
    warnings.warn(
        "get_llm_config_manager is deprecated (Issue #667). "
        "Use netra_backend.app.core.configuration.base.config_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return UnifiedConfigurationManagerCompatibility(service_name="llm")

# Export all compatibility aliases
__all__ = [
    'ConfigurationManager',
    'UnifiedConfigurationManager', 
    'EnvironmentConfigLoader',
    'ConfigurationValidator',
    'ConfigurationManagerFactory',
    'get_configuration_manager',
    'get_dashboard_config_manager',
    'get_data_agent_config_manager',
    'get_llm_config_manager'
]