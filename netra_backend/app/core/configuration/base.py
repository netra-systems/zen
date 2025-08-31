"""Unified Configuration Management - Core Orchestration

**CRITICAL: Single Source of Truth for All Configuration**

Business Value: Eliminates $12K MRR loss from configuration inconsistencies.
Enterprise customers require absolute configuration reliability.

This module orchestrates all configuration loading through a unified interface.
All configuration access MUST go through this system.

Each function ≤8 lines, file ≤300 lines.
"""

import threading
from datetime import datetime
from functools import lru_cache
from typing import Dict, Optional, Tuple, Union

from pydantic import ValidationError

from shared.isolated_environment import get_env
from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.schemas.config import AppConfig

from netra_backend.app.core.configuration.services import ServiceConfigManager as ActualServiceConfigManager
from netra_backend.app.core.configuration.database import DatabaseConfigManager as ActualDatabaseConfigManager
from netra_backend.app.core.configuration.secrets import SecretManager as ActualSecretManager
from netra_backend.app.core.configuration.validator import ConfigurationValidator


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
        # Lazy logger initialization to prevent circular dependency
        self._logger = None  # Will be initialized on first use
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
        
        CRITICAL: Bootstrap method for initial config load.
        All other access goes through unified config system.
        """
        # Bootstrap-only environment detection - required for initial config load
        if get_env().get("TESTING"):
            return "testing"
        env = get_env().get("ENVIRONMENT", "development").lower()
        # Handle empty string case - default to development
        return env if env else "development"
    
    def _check_hot_reload_enabled(self) -> bool:
        """Check if hot reload is enabled for this environment.
        
        CRITICAL: This is a bootstrap method for initial config setup.
        After bootstrap, use config.hot_reload_enabled instead.
        """
        # Bootstrap-only check - required before config is loaded
        return get_env().get("CONFIG_HOT_RELOAD", "false").lower() == "true"
    
    def _is_test_context(self) -> bool:
        """Check if running in test context."""
        return (self._check_pytest_active() or
                self._check_test_env_vars() or 
                self._check_environment_is_test())
    
    def _check_pytest_active(self) -> bool:
        """Check if pytest is actively running."""
        import sys
        if 'pytest' in sys.modules and hasattr(sys.modules['pytest'], 'main'):
            if hasattr(sys, '_pytest_running') or get_env().get('PYTEST_CURRENT_TEST'):
                return True
        return False
    
    def _check_test_env_vars(self) -> bool:
        """Check test environment variables."""
        test_indicators = ['PYTEST_CURRENT_TEST', 'TESTING', 'TEST_MODE']
        for indicator in test_indicators:
            value = get_env().get(indicator, '').lower()
            if value in ['true', '1', 'yes', 'on']:
                return True
        return False
    
    def _check_environment_is_test(self) -> bool:
        """Check if ENVIRONMENT is test/testing."""
        env_value = get_env().get('ENVIRONMENT', '').lower()
        return env_value in ['test', 'testing']
    
    def get_config(self) -> AppConfig:
        """Get the unified application configuration."""
        if self._is_test_context():
            return self._get_test_config()
        return self._get_cached_config()
    
    def _get_test_config(self) -> AppConfig:
        """Get config for test context with time-based cache."""
        if self._is_cache_stale():
            self._clear_all_caches()
            return self._load_complete_configuration()
        return self._config_cache
    
    def _is_cache_stale(self) -> bool:
        """Check if config cache is stale."""
        if self._config_cache is None or self._load_timestamp is None:
            return True
        return (datetime.now() - self._load_timestamp).total_seconds() > 30
    
    def _get_cached_config(self) -> AppConfig:
        """Get cached config for non-test environments."""
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
        from netra_backend.app.schemas.config import (
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
        # First validate mandatory services for staging/production
        if self._environment in ["staging", "production"]:
            if hasattr(config, 'validate_mandatory_services'):
                try:
                    config.validate_mandatory_services()
                except ValueError as e:
                    raise ConfigurationError(str(e))
        
        # Then run standard validation
        validation_result = self._validator.validate_complete_config(config)
        if not validation_result.is_valid:
            raise ConfigurationError(f"Configuration validation failed: {validation_result.errors}")
        # Skip logging during initial load to prevent recursion
    
    def _get_logger(self):
        """Get or initialize logger lazily to avoid circular dependency."""
        if self._logger is None:
            try:
                # Only import logger when actually needed, not during module import
                from netra_backend.app.logging_config import central_logger
                self._logger = central_logger
            except Exception:
                # If logger import fails, keep using print fallback
                pass
        return self._logger
    
    def _safe_log_error(self, message: str) -> None:
        """Safely log errors with fallback to print during bootstrap."""
        try:
            logger = self._get_logger()
            if logger is None:
                # During bootstrap, use print as fallback
                print(f"[CONFIG ERROR] {message}", flush=True)
            else:
                logger.error(message)
        except Exception:
            # Ultimate fallback if logger fails
            print(f"[CONFIG ERROR] {message}", flush=True)
    
    def _safe_log_warning(self, message: str) -> None:
        """Safely log warnings with fallback to print during bootstrap."""
        try:
            logger = self._get_logger()
            if logger is None:
                print(f"[CONFIG WARNING] {message}", flush=True)
            else:
                logger.warning(message)
        except Exception:
            print(f"[CONFIG WARNING] {message}", flush=True)
    
    def _safe_log_info(self, message: str) -> None:
        """Safely log info with fallback to print during bootstrap."""
        try:
            logger = self._get_logger()
            if logger is None:
                print(f"[CONFIG INFO] {message}", flush=True)
            else:
                logger.info(message)
        except Exception:
            print(f"[CONFIG INFO] {message}", flush=True)
    
    def _handle_configuration_error(self, error: Exception) -> None:
        """Handle configuration loading errors."""
        error_msg = f"CRITICAL: Configuration loading failed: {error}"
        # Safe logging with fallback to print for bootstrap phase
        if not isinstance(error, RecursionError):
            self._safe_log_error(error_msg)
        if isinstance(error, ValidationError):
            raise ConfigurationError(f"Configuration validation error: {error}")
        raise ConfigurationError(error_msg)
    
    def reload_config(self, force: bool = False) -> None:
        """Force reload configuration (hot-reload capability)."""
        if not self._hot_reload_enabled and not force:
            self._safe_log_warning("Hot reload disabled in this environment")
            return
        self._clear_configuration_cache()
        self._refresh_environment_detection()
        self._safe_log_info("Configuration reloaded")
    
    def _clear_all_caches(self) -> None:
        """Clear all configuration caches and reset singleton state for testing.
        
        CRITICAL TEST INTEGRATION: This method ensures that test environment
        changes are immediately reflected by clearing all cached configuration.
        """
        # Clear configuration cache
        self._clear_configuration_cache()
        
        # Reset database manager cache
        if hasattr(self._database_manager, '_postgres_url_cache'):
            self._database_manager._postgres_url_cache = None
        if hasattr(self._database_manager, '_clickhouse_config_cache'):
            self._database_manager._clickhouse_config_cache = None
        if hasattr(self._database_manager, '_redis_url_cache'):
            self._database_manager._redis_url_cache = None
        
        # Re-detect environment
        self._refresh_environment_detection()
        
        self._safe_log_info("All configuration caches cleared for test context")
    
    def _clear_configuration_cache(self) -> None:
        """Clear configuration cache for reload."""
        # Since get_config no longer uses @lru_cache, just clear the instance cache
        self._config_cache = None
        self._load_timestamp = datetime.now()
    
    def _refresh_environment_detection(self) -> None:
        """Refresh environment detection for testing scenarios."""
        old_env = self._environment
        self._environment = self._detect_environment()
        if old_env != self._environment:
            self._safe_log_info(f"Environment changed from {old_env} to {self._environment}")
        
        # Also refresh all component environments
        self._validator.refresh_environment()
        self._database_manager.refresh_environment()
        self._secrets_manager.refresh_environment()
    
    def get_config_summary(self) -> Dict[str, Union[str, int, bool, Optional[datetime]]]:
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
        return {var: get_env().get(var, "NOT_SET") for var in critical_vars}


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