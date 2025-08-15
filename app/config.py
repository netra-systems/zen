"""Simplified configuration management with validation and reduced circular dependencies."""

import os
from functools import lru_cache
from typing import Optional, Dict, Any, Callable, Tuple, List
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
# Import ConfigurationError from single source of truth
from app.core.exceptions_config import ConfigurationError


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
            return self._create_validated_config()
        except ValidationError as e:
            return self._handle_validation_error(e)
        except Exception as e:
            return self._handle_general_error(e)
            
    def _setup_config_base(self) -> Tuple[str, AppConfig]:
        """Setup configuration base."""
        environment = self._get_environment()
        self._logger.info(f"Loading configuration for: {environment}")
        config = self._create_base_config(environment)
        return environment, config
        
    def _populate_config(self, config: AppConfig) -> None:
        """Populate configuration with data."""
        self._load_critical_env_vars(config)
        self._load_secrets_into_config(config)
        
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
    
    def _get_environment(self) -> str:
        """Determine the current environment."""
        if os.environ.get("TESTING"):
            return "testing"
        cloud_env = detect_cloud_run_environment()
        if cloud_env:
            return cloud_env
        return self._get_default_environment()
        
    def _get_default_environment(self) -> str:
        """Get default environment from env vars."""
        env = os.environ.get("ENVIRONMENT", "development").lower()
        self._logger.debug(f"Environment determined as: {env}")
        return env
    
    def _create_base_config(self, environment: str) -> AppConfig:
        """Create the base configuration object for the environment."""
        config_classes = self._get_config_classes()
        return self._init_config(config_classes, environment)
        
    def _get_config_classes(self) -> Dict[str, type]:
        """Get configuration classes mapping."""
        return {
            "production": ProductionConfig,
            "staging": StagingConfig,
            "testing": NetraTestingConfig,
            "development": DevelopmentConfig
        }
    
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
        clickhouse_vars = self._get_clickhouse_env_vars()
        self._apply_clickhouse_vars(config, clickhouse_vars)
        
    def _get_clickhouse_env_vars(self) -> Dict[str, Optional[str]]:
        """Get ClickHouse environment variables."""
        return {
            "host": os.environ.get("CLICKHOUSE_HOST"),
            "port": os.environ.get("CLICKHOUSE_PORT"),
            "password": os.environ.get("CLICKHOUSE_PASSWORD"),
            "user": os.environ.get("CLICKHOUSE_USER")
        }
        
    def _get_clickhouse_setters(self) -> Dict[str, Callable]:
        """Get ClickHouse setter functions."""
        return {
            "host": set_clickhouse_host,
            "port": set_clickhouse_port,
            "password": set_clickhouse_password,
            "user": set_clickhouse_user
        }
        
    def _apply_clickhouse_var(self, config: AppConfig, key: str, value: Optional[str]) -> None:
        """Apply single ClickHouse variable."""
        setters = self._get_clickhouse_setters()
        if value and key in setters:
            setters[key](config, value)
            
    def _apply_clickhouse_vars(self, config: AppConfig, vars_dict: Dict[str, Optional[str]]) -> None:
        """Apply ClickHouse variables to config."""
        for key, value in vars_dict.items():
            self._apply_clickhouse_var(config, key, value)
    
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
            self._handle_loaded_secrets(config, secrets)
        except Exception as e:
            self._logger.error(f"Failed to load secrets: {e}")
            
    def _handle_loaded_secrets(self, config: AppConfig, secrets: Dict[str, Any]) -> None:
        """Handle loaded secrets."""
        if secrets:
            self._process_secrets(config, secrets)
        else:
            self._logger.warning("No secrets loaded")
    
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
                self._logger.debug(f"Applying secret '{name}' to config")
                self._apply_secret_mapping(config, mappings[name], value)
                count += 1
        return count
    
    def _log_secret_status(self, secrets: Dict) -> None:
        """Log status of critical secrets."""
        critical, applied, missing = self._analyze_critical_secrets(secrets)
        self._log_secret_analysis(applied, missing)
        
    def _analyze_critical_secrets(self, secrets: Dict) -> Tuple[List[str], List[str], List[str]]:
        """Analyze critical secrets status."""
        critical = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
        applied = [s for s in critical if s in secrets]
        missing = [s for s in critical if s not in secrets]
        return critical, applied, missing
        
    def _log_secret_analysis(self, applied: List[str], missing: List[str]) -> None:
        """Log secret analysis results."""
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
        secret_info = self._analyze_secrets()
        return self._build_configuration_summary(config, secret_info)
        
    def _analyze_secrets(self) -> Tuple[int, List[str]]:
        """Analyze secrets configuration."""
        secret_mappings = self._get_secret_mappings()
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
    
    def _apply_secret_mapping(self, config: AppConfig, mapping: Dict[str, Any], secret_value: str):
        """Apply a single secret mapping to the configuration."""
        if not mapping["targets"]:
            self._apply_direct_mapping(config, mapping, secret_value)
        else:
            self._apply_nested_mapping(config, mapping, secret_value)
            
    def _apply_direct_mapping(self, config: AppConfig, mapping: Dict[str, Any], secret_value: str) -> None:
        """Apply direct field mapping."""
        setattr(config, mapping["field"], secret_value)
        
    def _apply_nested_mapping(self, config: AppConfig, mapping: Dict[str, Any], secret_value: str) -> None:
        """Apply nested field mapping."""
        for target in mapping["targets"]:
            self._set_nested_field(config, target, mapping["field"], secret_value)
    
    def _handle_nested_field_error(self, field: str, target_path: str, error: AttributeError) -> None:
        """Handle nested field setting errors."""
        self._logger.warning(f"Failed to set field {field} on {target_path}: {error}")
        
    def _choose_field_setter(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Choose appropriate field setter method."""
        if '.' in target_path:
            self._set_deep_nested_field(config, target_path, field, value)
        else:
            self._set_direct_field(config, target_path, field, value)
            
    def _set_nested_field(self, config: AppConfig, target_path: str, field: str, value: str):
        """Set a nested field in the configuration object."""
        try:
            self._choose_field_setter(config, target_path, field, value)
            self._logger.debug(f"Successfully set {target_path}.{field}")
        except AttributeError as e:
            self._logger.debug(f"Failed to set {target_path}.{field}: {e}")
            self._handle_nested_field_error(field, target_path, e)
            
    def _set_deep_nested_field(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Set deeply nested field value."""
        parts = target_path.split('.', 1)
        parent_attr = getattr(config, parts[0])
        if isinstance(parent_attr, dict) and parts[1] in parent_attr:
            target_obj = parent_attr[parts[1]]
            self._set_field_if_valid(target_obj, field, value)
            
    def _set_direct_field(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Set direct field value."""
        target_obj = getattr(config, target_path, None)
        self._set_field_if_valid(target_obj, field, value)
        
    def _set_field_if_valid(self, target_obj: Any, field: str, value: str) -> None:
        """Set field if target object is valid."""
        if target_obj and hasattr(target_obj, field):
            setattr(target_obj, field, value)
            # Verify the field was actually set
            actual_value = getattr(target_obj, field, None)
            if actual_value != value:
                self._logger.warning(f"Field {field} not properly set. Expected: {value[:10]}..., Got: {actual_value}")
            else:
                self._logger.debug(f"Successfully set {field} on {type(target_obj).__name__}")
    
    def _load_from_environment_variables(self, config: AppConfig):
        """Fallback method to load configuration from environment variables."""
        env_mappings = self._get_env_mappings()
        for env_var, (target_path, field) in env_mappings.items():
            self._apply_env_var_if_present(config, env_var, target_path, field)
            
    def _get_oauth_mappings(self) -> Dict[str, Tuple[str, str]]:
        """Get OAuth environment mappings."""
        return {
            "GOOGLE_CLIENT_ID": ("oauth_config", "client_id"),
            "GOOGLE_CLIENT_SECRET": ("oauth_config", "client_secret"),
        }
        
    def _get_llm_mappings(self) -> Dict[str, Tuple[str, str]]:
        """Get LLM-related mappings."""
        return {"GEMINI_API_KEY": ("llm_configs.default", "api_key")}
        
    def _get_security_mappings(self) -> Dict[str, Tuple[None, str]]:
        """Get security-related mappings."""
        return {
            "JWT_SECRET_KEY": (None, "jwt_secret_key"),
            "FERNET_KEY": (None, "fernet_key"),
            "DATABASE_URL": (None, "database_url"),
            "LOG_LEVEL": (None, "log_level"),
        }
        
    def _get_core_mappings(self) -> Dict[str, Tuple[Optional[str], str]]:
        """Get core environment mappings."""
        llm_mappings = self._get_llm_mappings()
        security_mappings = self._get_security_mappings()
        return {**llm_mappings, **security_mappings}
        
    def _get_env_mappings(self) -> Dict[str, Tuple[Optional[str], str]]:
        """Get environment variable mappings."""
        oauth_mappings = self._get_oauth_mappings()
        core_mappings = self._get_core_mappings()
        return {**oauth_mappings, **core_mappings}
        
    def _apply_env_var_if_present(self, config: AppConfig, env_var: str, target_path: Optional[str], field: str) -> None:
        """Apply environment variable if present."""
        value = os.environ.get(env_var)
        if value:
            self._set_config_value(config, target_path, field, value)
            
    def _set_config_value(self, config: AppConfig, target_path: Optional[str], field: str, value: str) -> None:
        """Set configuration value based on target path."""
        if target_path:
            self._set_nested_config_value(config, target_path, field, value)
        else:
            setattr(config, field, value)
            
    def _set_nested_config_value(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Set nested configuration value."""
        if target_path.startswith("llm_configs."):
            self._set_llm_config_value(config, target_path, field, value)
        else:
            self._set_object_attribute(config, target_path, field, value)
            
    def _set_llm_config_value(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Set LLM configuration value."""
        llm_name = target_path.split(".")[1]
        if llm_name in config.llm_configs:
            setattr(config.llm_configs[llm_name], field, value)
            
    def _set_object_attribute(self, config: AppConfig, target_path: str, field: str, value: str) -> None:
        """Set object attribute value."""
        target_obj = getattr(config, target_path, None)
        if target_obj:
            setattr(target_obj, field, value)
    
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