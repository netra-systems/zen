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
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
from datetime import datetime
from pydantic import ValidationError

from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.core.exceptions_config import ConfigurationError

from netra_backend.app.database import DatabaseConfigManager
from netra_backend.app.services import ServiceConfigManager  
from netra_backend.app.secrets import SecretManager
from netra_backend.app.validator import ConfigurationValidator


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
        self._database_manager = DatabaseConfigManager()
        self._services_manager = ServiceConfigManager()
        self._secrets_manager = SecretManager()
        self._hot_reload_enabled = self._check_hot_reload_enabled()
    
    def _detect_environment(self) -> str:
        """Detect current environment from environment variables."""
        # Check TESTING first for test environments
        if os.environ.get("TESTING"):
            return "testing"
        return os.environ.get("ENVIRONMENT", "development").lower()
    
    def _check_hot_reload_enabled(self) -> bool:
        """Check if hot reload is enabled for this environment."""
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
        try:
            config = self._create_base_config()
            self._populate_configuration_data(config)
            self._validate_final_config(config)
            return config
        except Exception as e:
            self._handle_configuration_error(e)
    
    def _create_base_config(self) -> AppConfig:
        """Create base configuration for current environment."""
        config_class = self._get_config_class_for_environment()
        base_config = config_class()
        self._logger.info(f"Created {self._environment} configuration")
        return base_config
    
    def _get_config_class_for_environment(self) -> type:
        """Get configuration class for current environment."""
        from netra_backend.app.configuration.schemas import (
            DevelopmentConfig, StagingConfig, 
            ProductionConfig, NetraTestingConfig
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
        self._logger.info("Populated configuration from all sources")
    
    def _validate_final_config(self, config: AppConfig) -> None:
        """Validate final configuration before use."""
        validation_result = self._validator.validate_complete_config(config)
        if not validation_result.is_valid:
            raise ConfigurationError(f"Configuration validation failed: {validation_result.errors}")
        self._logger.info("Configuration validation passed")
    
    def _handle_configuration_error(self, error: Exception) -> None:
        """Handle configuration loading errors."""
        error_msg = f"CRITICAL: Configuration loading failed: {error}"
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