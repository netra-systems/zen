"""Simplified configuration management with validation and reduced circular dependencies."""

import os
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import ValidationError
from datetime import datetime

# Import the schemas without circular dependency
from app.schemas.Config import AppConfig, DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig
from app.schemas.config_types import ConfigurationSummary, ConfigurationStatus, Environment
from app.logging_config import central_logger as logger
from app.core.secret_manager import SecretManager
from app.core.config_validator import ConfigValidator
from app.config_loader import (
    load_env_var, set_clickhouse_host, set_clickhouse_port,
    set_clickhouse_password, set_clickhouse_user, set_gemini_api_key,
    get_critical_vars_mapping, apply_single_secret, detect_cloud_run_environment
)
from app.config_secrets import get_all_secret_mappings


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """Simplified configuration manager with clear separation of concerns."""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._secret_manager = SecretManager()
        self._validator = ConfigValidator()
        self._logger = logger
        
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
            
            # Load critical environment variables (non-secrets like DATABASE_URL, REDIS_URL, etc)
            self._load_critical_env_vars(config)
            
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
        cloud_env = detect_cloud_run_environment()
        if cloud_env:
            return cloud_env
        env = os.environ.get("ENVIRONMENT", "development").lower()
        self._logger.debug(f"Environment determined as: {env}")
        return env
    
    def _create_base_config(self, environment: str) -> AppConfig:
        """Create the base configuration object for the environment."""
        config_classes = {
            "production": ProductionConfig,
            "staging": StagingConfig,
            "testing": NetraTestingConfig,
            "development": DevelopmentConfig
        }
        return self._init_config(config_classes, environment)
    
    def _init_config(self, config_classes: dict, env: str) -> AppConfig:
        """Initialize config with appropriate class."""
        config_class = config_classes.get(env, DevelopmentConfig)
        config = config_class()
        self._update_websocket_url(config)
        return config
    
    def _update_websocket_url(self, config: AppConfig) -> None:
        """Update WebSocket URL if server port is set."""
        server_port = os.environ.get('SERVER_PORT')
        if server_port:
            config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
            self._logger.info(f"Updated WebSocket URL to port {server_port}")
    
    def _load_critical_env_vars(self, config: AppConfig):
        """Load critical environment variables that are not secrets."""
        self._load_standard_env_vars(config)
        self._load_special_env_vars(config)
        self._log_loaded_vars()
    
    def _load_standard_env_vars(self, config: AppConfig) -> None:
        """Load standard environment variables."""
        critical_vars = get_critical_vars_mapping()
        for env_var, field in critical_vars.items():
            if field:
                load_env_var(env_var, config, field)
    
    def _load_special_env_vars(self, config: AppConfig) -> None:
        """Load special environment variables requiring custom handling."""
        self._handle_clickhouse_vars(config)
        self._handle_gemini_var(config)
    
    def _handle_clickhouse_vars(self, config: AppConfig) -> None:
        """Handle ClickHouse environment variables."""
        if host := os.environ.get("CLICKHOUSE_HOST"):
            set_clickhouse_host(config, host)
        if port := os.environ.get("CLICKHOUSE_PORT"):
            set_clickhouse_port(config, port)
        if pwd := os.environ.get("CLICKHOUSE_PASSWORD"):
            set_clickhouse_password(config, pwd)
        if user := os.environ.get("CLICKHOUSE_USER"):
            set_clickhouse_user(config, user)
    
    def _handle_gemini_var(self, config: AppConfig) -> None:
        """Handle Gemini API key environment variable."""
        if key := os.environ.get("GEMINI_API_KEY"):
            set_gemini_api_key(config, key)
    
    def _log_loaded_vars(self) -> None:
        """Log summary of loaded environment variables."""
        all_vars = list(get_critical_vars_mapping().keys())
        all_vars.extend(["CLICKHOUSE_HOST", "CLICKHOUSE_PORT", 
                        "CLICKHOUSE_PASSWORD", "CLICKHOUSE_USER", "GEMINI_API_KEY"])
        loaded = [v for v in all_vars if os.environ.get(v)]
        if loaded:
            self._logger.info(f"Loaded {len(loaded)} env vars")
    
    def _load_secrets_into_config(self, config: AppConfig):
        """Load secrets into the configuration object."""
        try:
            secrets = self._load_secrets()
            if secrets:
                self._process_secrets(config, secrets)
            else:
                self._logger.warning("No secrets loaded")
        except Exception as e:
            self._logger.error(f"Failed to load secrets: {e}")
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load secrets from secret manager."""
        self._logger.info("Loading secrets...")
        return self._secret_manager.load_secrets()
    
    def _process_secrets(self, config: AppConfig, secrets: Dict) -> None:
        """Process and apply loaded secrets."""
        self._logger.info(f"Applying {len(secrets)} secrets")
        self._apply_secrets_to_config(config, secrets)
        self._log_secret_status(secrets)
    
    def _apply_secrets_to_config(self, config: AppConfig, secrets: Dict[str, Any]):
        """Apply loaded secrets to configuration object."""
        mappings = self._get_secret_mappings()
        count = self._apply_all_secrets(config, secrets, mappings)
        self._logger.info(f"Applied {count} secrets")
    
    def _apply_all_secrets(self, config: AppConfig, secrets: Dict, mappings: Dict) -> int:
        """Apply all secrets and return count."""
        count = 0
        for name, value in secrets.items():
            if value and name in mappings:
                self._apply_secret_mapping(config, mappings[name], value)
                count += 1
        return count
    
    def _log_secret_status(self, secrets: Dict) -> None:
        """Log status of critical secrets."""
        critical = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
        applied = [s for s in critical if s in secrets]
        missing = [s for s in critical if s not in secrets]
        if applied:
            self._logger.info(f"Critical secrets applied: {len(applied)}")
        if missing:
            self._logger.warning(f"Critical secrets missing: {len(missing)}")
    
    def _get_secret_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get the mapping of secrets to configuration fields."""
        return get_all_secret_mappings()
    
    def get_configuration_summary(self) -> ConfigurationSummary:
        """Get a summary of the current configuration status."""
        config = self.get_config()
        
        # Count secrets
        secret_mappings = self._get_secret_mappings()
        total_secrets = len(secret_mappings)
        required_secrets = [name for name, mapping in secret_mappings.items() if mapping.required]
        
        return ConfigurationSummary(
            environment=Environment(config.environment),
            status=ConfigurationStatus.LOADED,
            loaded_at=datetime.now(),
            secrets_loaded=total_secrets,
            secrets_total=total_secrets,
            critical_secrets_missing=[],
            warnings=[],
            errors=[]
        )
    
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
config_manager = _config_manager  # Export for backward compatibility

# Convenient access functions
def get_config() -> AppConfig:
    """Get the current application configuration."""
    return _config_manager.get_config()

def reload_config():
    """Reload the configuration from environment."""
    _config_manager.reload_config()

# For backward compatibility
settings = get_config()