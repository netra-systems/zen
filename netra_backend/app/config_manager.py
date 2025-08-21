"""Configuration Manager Module

Main configuration manager that orchestrates all configuration loading.

DEPRECATED: This module is deprecated. Use app.core.configuration instead.
Will be removed in v2.0. Migration guide: /docs/configuration-migration.md
"""

from functools import lru_cache
from typing import Optional, Dict, Any, List, Tuple
from pydantic import ValidationError
from datetime import datetime

from app.schemas.Config import AppConfig
from app.schemas.config_types import ConfigurationSummary, ConfigurationStatus, Environment
from app.logging_config import central_logger as logger
from app.core.config_validator import ConfigValidator
from app.core.exceptions_config import ConfigurationError

# Import modular components
from app.config_environment import ConfigEnvironment
from app.config_secrets_manager import ConfigSecretsManager
from app.config_envvars import ConfigEnvVarsManager


class ConfigManager:
    """Main configuration manager orchestrating all configuration loading"""
    
    def _initialize_components(self):
        """Initialize modular configuration components."""
        self._environment = ConfigEnvironment()
        self._secrets_manager = ConfigSecretsManager()
        self._envvars_manager = ConfigEnvVarsManager()

    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._validator = ConfigValidator()
        self._logger = logger
        self._initialize_components()
        
    @lru_cache(maxsize=1)
    def get_config(self) -> AppConfig:
        """Get the application configuration (cached)."""
        if self._config is None:
            self._config = self._load_configuration()
        return self._config
    
    def _load_configuration(self) -> AppConfig:
        """Load and validate configuration from environment."""
        try:
            return self._create_validated_config()
        except ValidationError as e:
            return self._handle_validation_error(e)
        except Exception as e:
            return self._handle_general_error(e)
            
    def _setup_config_base(self) -> Tuple[str, AppConfig]:
        """Setup configuration base."""
        environment = self._environment.get_environment()
        self._logger.info(f"Loading configuration for: {environment}")
        config = self._environment.create_base_config(environment)
        return environment, config
        
    def _populate_config(self, config: AppConfig) -> None:
        """Populate configuration with data."""
        self._envvars_manager.load_critical_env_vars(config)
        self._secrets_manager.load_secrets_into_config(config)
        
    def _create_validated_config(self) -> AppConfig:
        """Create and validate configuration."""
        environment, config = self._setup_config_base()
        self._populate_config(config)
        self._validator.validate_config(config)
        return config
        
    def _handle_validation_error(self, error: ValidationError) -> None:
        """Handle validation errors."""
        self._logger.error(f"Configuration loading failed: {error}")
        raise ConfigurationError(f"Failed to load configuration: {error}")
        
    def _handle_general_error(self, error: Exception) -> None:
        """Handle general configuration errors."""
        self._logger.error(f"Configuration loading failed: {error}")
        raise ConfigurationError(f"Failed to load configuration: {error}")
    
    def get_configuration_summary(self) -> ConfigurationSummary:
        """Get a summary of the current configuration status."""
        config = self.get_config()
        secret_info = self._analyze_secrets()
        return self._build_configuration_summary(config, secret_info)
        
    def _analyze_secrets(self) -> Tuple[int, List[str]]:
        """Analyze secrets configuration."""
        secret_mappings = self._secrets_manager._get_secret_mappings()
        total_secrets = len(secret_mappings)
        required_secrets = [name for name, mapping in secret_mappings.items() if mapping.get("required", False)]
        return total_secrets, required_secrets
        
    def _get_basic_fields(self, config: AppConfig) -> Dict[str, Any]:
        """Get basic configuration fields."""
        return {
            "environment": Environment(config.environment),
            "status": ConfigurationStatus.LOADED,
            "loaded_at": datetime.now()
        }
        
    def _get_secret_counts(self, secret_info: Tuple[int, List[str]]) -> Dict[str, int]:
        """Get secret count fields."""
        total_secrets, required_secrets = secret_info
        return {
            "secrets_loaded": total_secrets,
            "secrets_total": total_secrets
        }
        
    def _get_secret_status_fields(self) -> Dict[str, List]:
        """Get secret status fields."""
        return {
            "critical_secrets_missing": [],
            "warnings": [],
            "errors": []
        }
        
    def _get_secret_fields(self, secret_info: Tuple[int, List[str]]) -> Dict[str, Any]:
        """Get secret-related fields."""
        counts = self._get_secret_counts(secret_info)
        status = self._get_secret_status_fields()
        return {**counts, **status}
        
    def _create_summary_fields(self, config: AppConfig, secret_info: Tuple[int, List[str]]) -> Dict[str, Any]:
        """Create summary fields dictionary."""
        basic_fields = self._get_basic_fields(config)
        secret_fields = self._get_secret_fields(secret_info)
        return {**basic_fields, **secret_fields}
        
    def _build_configuration_summary(self, config: AppConfig, secret_info: Tuple[int, List[str]]) -> ConfigurationSummary:
        """Build configuration summary object."""
        fields = self._create_summary_fields(config, secret_info)
        return ConfigurationSummary(**fields)

    def reload_config(self):
        """Force reload the configuration (clears cache)."""
        self.get_config.cache_clear()
        self._config = None