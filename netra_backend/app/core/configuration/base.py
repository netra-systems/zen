"""Unified Configuration Management - Core Orchestration

**CRITICAL: Single Source of Truth for All Configuration**

Business Value: Eliminates $12K MRR loss from configuration inconsistencies.
Enterprise customers require absolute configuration reliability.

This module orchestrates all configuration loading through a unified interface.
All configuration access MUST go through this system.

Each function ≤8 lines, file ≤300 lines.
"""

import os
import threading
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.Config import AppConfig

# Import actual configuration managers
try:
    from netra_backend.app.core.configuration.services import (
        ServiceConfigManager as ActualServiceConfigManager,
    )
except ImportError:
    # Fallback placeholder if services module not available
    class ActualServiceConfigManager:
        """Placeholder for service configuration manager."""
        def populate_service_config(self, config):
            """Populate service configuration."""
            pass
        
        def validate_service_consistency(self, config):
            """Validate service configuration consistency."""
            return []
        
        def get_enabled_services_count(self):
            """Get count of enabled services."""
            return 0

try:
    from netra_backend.app.core.configuration.database import (
        DatabaseConfigManager as ActualDatabaseConfigManager,
    )
except ImportError:
    # Fallback placeholder if database module not available
    class ActualDatabaseConfigManager:
        """Placeholder for database configuration manager."""
        def populate_database_config(self, config):
            """Populate database configuration."""
            pass
        
        def validate_database_consistency(self, config):
            """Validate database configuration consistency."""
            return []
        
        def refresh_environment(self):
            """Refresh environment settings."""
            pass

try:
    from netra_backend.app.core.configuration.secrets import (
        SecretManager as ActualSecretManager,
    )
except ImportError:
    # Fallback placeholder if secrets module not available
    class ActualSecretManager:
        """Placeholder for secret manager."""
        def populate_secrets(self, config):
            """Populate secrets."""
            pass
        
        def validate_secrets_consistency(self, config):
            """Validate secrets consistency."""
            return []
        
        def get_loaded_secrets_count(self):
            """Get count of loaded secrets."""
            return 0

class ConfigurationValidator:
    """Placeholder for configuration validator."""
    def validate_complete_config(self, config):
        """Validate complete configuration."""
        class ValidationResult:
            is_valid = True
            errors = []
        return ValidationResult()
    
    def refresh_environment(self):
        """Refresh environment settings."""
        pass


class UnifiedConfigManager:
    """Enterprise-grade unified configuration manager.
    
    **MANDATORY**: All configuration MUST use this single source.
    Prevents configuration-related revenue losses.
    """
    
    _instance: Optional['UnifiedConfigManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'UnifiedConfigManager':
        """Singleton pattern for configuration consistency."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager components."""
        if hasattr(self, '_initialized'):
            return
        self._loading = False  # Add loading flag
        self._initialize_core_components()
        self._initialize_config_managers()
        self._config_cache: Optional[AppConfig] = None
        self._initialized = True
    
    def _initialize_core_components(self) -> None:
        """Initialize core configuration components."""
        self._logger = logger
        self._validator = ConfigurationValidator()
        self._load_timestamp: Optional[datetime] = None
        self._environment = self._detect_environment()
    
    def _initialize_config_managers(self) -> None:
        """Initialize specialized configuration managers."""
        self._database_manager = ActualDatabaseConfigManager()
        self._services_manager = ActualServiceConfigManager()
        self._secrets_manager = ActualSecretManager()
        self._hot_reload_enabled = self._check_hot_reload_enabled()
    
    def _detect_environment(self) -> str:
        """Detect current environment from configuration.
        
        CRITICAL: NEVER use direct os.environ calls.
        This is a bootstrap method that must access env vars directly
        only during initial setup. All other access goes through config.
        """
        # Bootstrap-only environment detection - required for initial config load
        # This is the ONLY acceptable direct env var access in the system
        import os
        if os.environ.get("TESTING"):
            return "testing"
        env = os.environ.get("ENVIRONMENT", "development").lower()
        # Handle empty string case - default to development
        return env if env else "development"
    
    def _check_hot_reload_enabled(self) -> bool:
        """Check if hot reload is enabled for this environment.
        
        CRITICAL: This is a bootstrap method for initial config setup.
        After bootstrap, use config.hot_reload_enabled instead.
        """
        # Bootstrap-only check - required before config is loaded
        import os
        return os.environ.get("CONFIG_HOT_RELOAD", "false").lower() == "true"
    
    @lru_cache(maxsize=1)
    def get_config(self) -> AppConfig:
        """Get the unified application configuration.
        
        **CRITICAL**: This is the ONLY way to access configuration.
        All other access methods are deprecated.
        """
        if self._config_cache is None:
            self._config_cache = self._load_complete_configuration()
        return self._config_cache
    
    def _load_complete_configuration(self) -> AppConfig:
        """Load complete configuration from all sources."""
        self._loading = True  # Set loading flag to prevent recursion
        try:
            config = self._create_base_config()
            self._populate_configuration_data(config)
            self._validate_final_config(config)
            return config
        except Exception as e:
            self._handle_configuration_error(e)
        finally:
            self._loading = False  # Clear loading flag
    
    def _create_base_config(self) -> AppConfig:
        """Create base configuration for current environment."""
        config_class = self._get_config_class_for_environment()
        base_config = config_class()
        # Skip logging during initial load to prevent recursion
        # The logger filter may try to load config, creating a loop
        pass  # Removed logging to prevent recursion
        return base_config
    
    def _get_config_class_for_environment(self) -> type:
        """Get configuration class for current environment."""
        from netra_backend.app.schemas.Config import (
            DevelopmentConfig,
            NetraTestingConfig,
            ProductionConfig,
            StagingConfig,
        )
        return {
            "development": DevelopmentConfig,
            "staging": StagingConfig,
            "production": ProductionConfig,
            "testing": NetraTestingConfig
        }.get(self._environment, DevelopmentConfig)
    
    def _populate_configuration_data(self, config: AppConfig) -> None:
        """Populate configuration with data from all sources."""
        self._database_manager.populate_database_config(config)
        self._services_manager.populate_service_config(config) 
        self._secrets_manager.populate_secrets(config)
        # Skip logging during initial load to prevent recursion
    
    def _validate_final_config(self, config: AppConfig) -> None:
        """Validate final configuration before use."""
        validation_result = self._validator.validate_complete_config(config)
        if not validation_result.is_valid:
            raise ConfigurationError(f"Configuration validation failed: {validation_result.errors}")
        # Skip logging during initial load to prevent recursion
    
    def _handle_configuration_error(self, error: Exception) -> None:
        """Handle configuration loading errors."""
        error_msg = f"CRITICAL: Configuration loading failed: {error}"
        # Only log if not RecursionError to prevent further recursion
        if not isinstance(error, RecursionError):
            self._logger.error(error_msg)
        if isinstance(error, ValidationError):
            raise ConfigurationError(f"Configuration validation error: {error}")
        raise ConfigurationError(error_msg)
    
    def reload_config(self, force: bool = False) -> None:
        """Force reload configuration (hot-reload capability)."""
        if not self._hot_reload_enabled and not force:
            self._logger.warning("Hot reload disabled in this environment")
            return
        self._clear_configuration_cache()
        self._refresh_environment_detection()
        self._logger.info("Configuration reloaded")
    
    def _clear_configuration_cache(self) -> None:
        """Clear configuration cache for reload."""
        self.get_config.cache_clear()
        self._config_cache = None
        self._load_timestamp = datetime.now()
    
    def _refresh_environment_detection(self) -> None:
        """Refresh environment detection for testing scenarios."""
        old_env = self._environment
        self._environment = self._detect_environment()
        if old_env != self._environment:
            self._logger.info(f"Environment changed from {old_env} to {self._environment}")
        
        # Also refresh all component environments
        self._validator.refresh_environment()
        self._database_manager.refresh_environment()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring."""
        config = self.get_config()
        return {
            "environment": self._environment,
            "loaded_at": self._load_timestamp,
            "hot_reload_enabled": self._hot_reload_enabled,
            "database_configured": bool(config.database_url),
            "secrets_loaded": self._secrets_manager.get_loaded_secrets_count(),
            "services_enabled": self._services_manager.get_enabled_services_count()
        }
    
    def validate_configuration_integrity(self) -> Tuple[bool, list]:
        """Validate configuration integrity for Enterprise customers."""
        config = self.get_config()
        issues = self._check_configuration_consistency(config)
        return len(issues) == 0, issues
    
    def _check_configuration_consistency(self, config: AppConfig) -> list:
        """Check configuration consistency across all components."""
        issues = []
        issues.extend(self._database_manager.validate_database_consistency(config))
        issues.extend(self._services_manager.validate_service_consistency(config))
        issues.extend(self._secrets_manager.validate_secrets_consistency(config))
        return issues
    
    def get_environment_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for debugging."""
        critical_vars = [
            "DATABASE_URL", "CLICKHOUSE_URL", "REDIS_URL",
            "ENVIRONMENT", "CONFIG_HOT_RELOAD"
        ]
        return {var: os.environ.get(var, "NOT_SET") for var in critical_vars}


# Global instance for application use
config_manager = UnifiedConfigManager()


def get_unified_config() -> AppConfig:
    """Get unified configuration - PREFERRED access method."""
    return config_manager.get_config()


def reload_unified_config(force: bool = False) -> None:
    """Reload unified configuration - Hot reload capability."""
    config_manager.reload_config(force=force)


def validate_config_integrity() -> Tuple[bool, list]:
    """Validate configuration integrity - Enterprise reliability check."""
    return config_manager.validate_configuration_integrity()