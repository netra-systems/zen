"""Environment variable loading utilities.

Focused module for loading environment variables into configuration.
Includes specialized functions for different config types.
"""

import os
from typing import Dict, Any, Optional, Tuple, Callable
from netra_backend.app.configuration.schemas import AppConfig
from netra_backend.app.logging_config import central_logger as logger


def load_env_var(env_var: str, config: AppConfig, field_name: str) -> bool:
    """Load a single environment variable into config."""
    value = os.environ.get(env_var)
    if value and hasattr(config, field_name):
        setattr(config, field_name, value)
        logger.debug(f"Set {field_name} from {env_var}")
        return True
    return False


def get_critical_vars_mapping() -> Dict[str, str]:
    """Get mapping of critical environment variables."""
    return {
        "DATABASE_URL": "database_url",
        "REDIS_URL": "redis_url",
        "CLICKHOUSE_URL": "clickhouse_url",
        "SECRET_KEY": "secret_key",
        "JWT_SECRET_KEY": "jwt_secret_key",
        "FERNET_KEY": "fernet_key",
        "LOG_LEVEL": "log_level",
        "ENVIRONMENT": "environment",
    }


def load_critical_env_vars(config: AppConfig):
    """Load critical environment variables that are not secrets."""
    _load_standard_env_vars(config)
    _load_special_env_vars(config)
    _log_loaded_vars()


def _load_standard_env_vars(config: AppConfig) -> None:
    """Load standard environment variables."""
    critical_vars = get_critical_vars_mapping()
    for env_var, field in critical_vars.items():
        if field:
            load_env_var(env_var, config, field)


def _load_special_env_vars(config: AppConfig) -> None:
    """Load special environment variables requiring custom handling."""
    _handle_clickhouse_vars(config)
    _handle_gemini_var(config)


def _handle_clickhouse_vars(config: AppConfig) -> None:
    """Handle ClickHouse environment variables."""
    clickhouse_vars = _get_clickhouse_env_vars()
    _apply_clickhouse_vars(config, clickhouse_vars)


def _get_clickhouse_env_vars() -> Dict[str, Optional[str]]:
    """Get ClickHouse environment variables."""
    return {
        "host": os.environ.get("CLICKHOUSE_HOST"),
        "port": os.environ.get("CLICKHOUSE_PORT"),
        "password": os.environ.get("CLICKHOUSE_PASSWORD"),
        "user": os.environ.get("CLICKHOUSE_USER")
    }


def _get_clickhouse_setters() -> Dict[str, Callable]:
    """Get ClickHouse setter functions."""
    return {
        "host": set_clickhouse_host,
        "port": set_clickhouse_port,
        "password": set_clickhouse_password,
        "user": set_clickhouse_user
    }


def _apply_clickhouse_var(config: AppConfig, key: str, value: Optional[str]) -> None:
    """Apply single ClickHouse variable."""
    setters = _get_clickhouse_setters()
    if value and key in setters:
        setters[key](config, value)


def _apply_clickhouse_vars(config: AppConfig, vars_dict: Dict[str, Optional[str]]) -> None:
    """Apply ClickHouse variables to config."""
    for key, value in vars_dict.items():
        _apply_clickhouse_var(config, key, value)


def _handle_gemini_var(config: AppConfig) -> None:
    """Handle Gemini API key environment variable."""
    if key := os.environ.get("GEMINI_API_KEY"):
        set_gemini_api_key(config, key)


def _log_loaded_vars() -> None:
    """Log summary of loaded environment variables."""
    all_vars = list(get_critical_vars_mapping().keys())
    all_vars.extend(["CLICKHOUSE_HOST", "CLICKHOUSE_PORT", 
                    "CLICKHOUSE_PASSWORD", "CLICKHOUSE_USER", "GEMINI_API_KEY"])
    loaded = [v for v in all_vars if os.environ.get(v)]
    if loaded:
        logger.info(f"Loaded {len(loaded)} env vars")


# ClickHouse-specific setters
def set_clickhouse_host(config: AppConfig, value: str) -> None:
    """Set ClickHouse host in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.host = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.host = value
    logger.debug(f"Set ClickHouse host: {value}")


def set_clickhouse_port(config: AppConfig, value: str) -> None:
    """Set ClickHouse port in config."""
    port = _validate_port_value(value)
    _set_port_on_config(config, port)
    logger.debug(f"Set ClickHouse port: {value}")


def _validate_port_value(value: str) -> int:
    """Validate and convert port value to integer."""
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid CLICKHOUSE_PORT: {value}")
        raise


def _set_port_on_config(config: AppConfig, port: int) -> None:
    """Set port on ClickHouse configuration objects."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.port = port
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.port = port


def set_clickhouse_password(config: AppConfig, value: str) -> None:
    """Set ClickHouse password in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.password = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.password = value
    logger.debug("Set ClickHouse password")


def set_clickhouse_user(config: AppConfig, value: str) -> None:
    """Set ClickHouse user in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.user = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.user = value
    logger.debug(f"Set ClickHouse user: {value}")


# LLM-specific setters
def set_gemini_api_key(config: AppConfig, value: str) -> None:
    """Set Gemini API key for LLM configs."""
    llm_names = ['default', 'analysis', 'triage', 'data',
                 'optimizations_core', 'actions_to_meet_goals',
                 'reporting', 'google']
    for name in llm_names:
        set_llm_api_key(config, name, value)
    logger.debug("Set Gemini API key for LLM configs")


def set_llm_api_key(config: AppConfig, llm_name: str, api_key: str) -> None:
    """Set API key for a specific LLM config."""
    if hasattr(config, 'llm_configs'):
        if llm_name in config.llm_configs:
            llm_config = config.llm_configs[llm_name]
            if hasattr(llm_config, 'api_key'):
                llm_config.api_key = api_key


# Path-based config setters
def apply_single_secret(config: AppConfig, path: str, field: str, value: str) -> None:
    """Apply a single secret to config at the given path."""
    parts = path.split('.')
    parent_obj = _navigate_to_parent_object(config, parts)
    if parent_obj:
        _set_field_on_target(parent_obj, parts[-1], field, value)


def _navigate_to_parent_object(config: AppConfig, path_parts: list) -> object:
    """Navigate to parent object in config path."""
    obj = config
    for part in path_parts[:-1]:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return None
    return obj


def _set_field_on_target(parent_obj: object, target_name: str, field: str, value: str) -> None:
    """Set field on target object if it exists."""
    if hasattr(parent_obj, target_name):
        target = getattr(parent_obj, target_name)
        if hasattr(target, field):
            setattr(target, field, value)