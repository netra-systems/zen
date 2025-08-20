"""Configuration Environment Variables Module

Handles loading and mapping environment variables to configuration.

DEPRECATED: This module is deprecated. Use app.core.configuration instead.
Will be removed in v2.0. Migration guide: /docs/configuration-migration.md
"""

import os
from typing import Dict, Any, Optional, Tuple, Callable
from app.schemas.Config import AppConfig
from app.config_loader import (
    load_env_var, set_clickhouse_host, set_clickhouse_port,
    set_clickhouse_password, set_clickhouse_user, set_gemini_api_key,
    get_critical_vars_mapping
)
from app.logging_config import central_logger as logger


class ConfigEnvVarsManager:
    """Handles environment variables loading and mapping"""
    
    def __init__(self):
        self._logger = logger
    
    def load_critical_env_vars(self, config: AppConfig):
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
    
    def load_from_environment_variables(self, config: AppConfig):
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