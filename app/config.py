"""Simplified configuration management with validation and reduced circular dependencies."""

import os
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import ValidationError

# Import the schemas without circular dependency
from app.schemas.Config import AppConfig, DevelopmentConfig, ProductionConfig, NetraTestingConfig

from app.core.secret_manager import SecretManager
from app.core.config_validator import ConfigValidator


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """Simplified configuration manager with clear separation of concerns."""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._secret_manager = SecretManager()
        self._validator = ConfigValidator()
        self._logger = logging.getLogger(__name__)
        
    @lru_cache(maxsize=1)
    def get_config(self) -> AppConfig:
        """Get the application configuration (cached)."""
        if self._config is None:
            self._config = self._load_configuration()
        return self._config
    
    def _load_configuration(self) -> AppConfig:
        """Load and validate configuration from environment."""
        try:
            environment = self._get_environment()
            self._logger.info(f"Loading configuration for: {environment}")
            
            # Create base config
            config = self._create_base_config(environment)
            
            # Load secrets
            self._load_secrets_into_config(config)
            
            # Validate configuration
            self._validator.validate_config(config)
            
            return config
            
        except ValidationError as e:
            self._logger.error(f"Configuration loading failed: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
        except Exception as e:
            self._logger.error(f"Configuration loading failed: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _get_environment(self) -> str:
        """Determine the current environment."""
        if os.environ.get("TESTING"):
            return "testing"
        return os.environ.get("ENVIRONMENT", "development").lower()
    
    def _create_base_config(self, environment: str) -> AppConfig:
        """Create the base configuration object for the environment."""
        config_classes = {
            "production": ProductionConfig,
            "testing": NetraTestingConfig,
            "development": DevelopmentConfig
        }
        
        config_class = config_classes.get(environment, DevelopmentConfig)
        config = config_class()
        
        # Update WebSocket URL with actual server port if available
        server_port = os.environ.get('SERVER_PORT')
        if server_port:
            config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
            self._logger.info(f"Updated WebSocket URL to use port {server_port}")
        
        return config
    
    def _load_secrets_into_config(self, config: AppConfig):
        """Load secrets into the configuration object."""
        try:
            secrets = self._secret_manager.load_secrets()
            self._apply_secrets_to_config(config, secrets)
        except Exception as e:
            self._logger.warning(f"Failed to load secrets: {e}. Using environment variables.")
            self._load_from_environment_variables(config)
    
    def _apply_secrets_to_config(self, config: AppConfig, secrets: Dict[str, Any]):
        """Apply loaded secrets to configuration object."""
        # Apply secrets based on predefined mapping
        secret_mappings = self._get_secret_mappings()
        
        for secret_name, secret_value in secrets.items():
            if secret_value and secret_name in secret_mappings:
                mapping = secret_mappings[secret_name]
                self._apply_secret_mapping(config, mapping, secret_value)
    
    def _get_secret_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get the mapping of secrets to configuration fields."""
        return {
            "gemini-api-key": {
                "targets": ["llm_configs.default", "llm_configs.triage", "llm_configs.data", 
                          "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals", 
                          "llm_configs.reporting", "llm_configs.google", "llm_configs.analysis"],
                "field": "api_key"
            },
            "google-client-id": {
                "targets": ["google_cloud", "oauth_config"],
                "field": "client_id"
            },
            "google-client-secret": {
                "targets": ["google_cloud", "oauth_config"],
                "field": "client_secret"
            },
            "langfuse-secret-key": {
                "targets": ["langfuse"],
                "field": "secret_key"
            },
            "langfuse-public-key": {
                "targets": ["langfuse"],
                "field": "public_key"
            },
            "clickhouse-default-password": {
                "targets": ["clickhouse_native", "clickhouse_https"],
                "field": "password"
            },
            "clickhouse-development-password": {
                "targets": ["clickhouse_https_dev"],
                "field": "password"
            },
            "jwt-secret-key": {
                "targets": [],
                "field": "jwt_secret_key"
            },
            "fernet-key": {
                "targets": [],
                "field": "fernet_key"
            },
            "redis-default": {
                "targets": ["redis"],
                "field": "password"
            }
        }
    
    def _apply_secret_mapping(self, config: AppConfig, mapping: Dict[str, Any], secret_value: str):
        """Apply a single secret mapping to the configuration."""
        if not mapping["targets"]:
            # Direct field assignment
            setattr(config, mapping["field"], secret_value)
        else:
            # Nested field assignment
            for target in mapping["targets"]:
                self._set_nested_field(config, target, mapping["field"], secret_value)
    
    def _set_nested_field(self, config: AppConfig, target_path: str, field: str, value: str):
        """Set a nested field in the configuration object."""
        try:
            if '.' in target_path:
                parts = target_path.split('.', 1)
                parent_attr = getattr(config, parts[0])
                if isinstance(parent_attr, dict) and parts[1] in parent_attr:
                    target_obj = parent_attr[parts[1]]
                    if target_obj and hasattr(target_obj, field):
                        setattr(target_obj, field, value)
            else:
                target_obj = getattr(config, target_path, None)
                if target_obj and hasattr(target_obj, field):
                    setattr(target_obj, field, value)
        except AttributeError as e:
            self._logger.warning(f"Failed to set field {field} on {target_path}: {e}")
    
    def _load_from_environment_variables(self, config: AppConfig):
        """Fallback method to load configuration from environment variables."""
        env_mappings = {
            "GOOGLE_CLIENT_ID": ("oauth_config", "client_id"),
            "GOOGLE_CLIENT_SECRET": ("oauth_config", "client_secret"),
            "GEMINI_API_KEY": ("llm_configs.default", "api_key"),
            "JWT_SECRET_KEY": (None, "jwt_secret_key"),
            "FERNET_KEY": (None, "fernet_key"),
            "DATABASE_URL": (None, "database_url"),
            "LOG_LEVEL": (None, "log_level"),
        }
        
        for env_var, (target_path, field) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                if target_path:
                    if target_path.startswith("llm_configs."):
                        # Handle LLM config specifically
                        llm_name = target_path.split(".")[1]
                        if llm_name in config.llm_configs:
                            setattr(config.llm_configs[llm_name], field, value)
                    else:
                        target_obj = getattr(config, target_path, None)
                        if target_obj:
                            setattr(target_obj, field, value)
                else:
                    setattr(config, field, value)
    
    def reload_config(self):
        """Force reload the configuration (clears cache)."""
        self.get_config.cache_clear()
        self._config = None


# Global configuration manager instance
_config_manager = ConfigManager()

# Convenient access functions
def get_config() -> AppConfig:
    """Get the current application configuration."""
    return _config_manager.get_config()

def reload_config():
    """Reload the configuration from environment."""
    _config_manager.reload_config()

# For backward compatibility
settings = get_config()