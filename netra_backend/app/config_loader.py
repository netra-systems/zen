"""Configuration loader utilities - split from config.py for modularity.

DEPRECATED: This module is deprecated. Use app.core.configuration instead.
Will be removed in v2.0. Migration guide: /docs/configuration-migration.md
"""

import os
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.core.config import Settings
from netra_backend.app.logging_config import central_logger as logger

# Import from modular components to maintain backward compatibility
from netra_backend.app.config_exceptions import ConfigLoadError
from netra_backend.app.cloud_environment_detector import (
    detect_cloud_run_environment, 
    detect_app_engine_environment, 
    CloudEnvironmentDetector
)
from netra_backend.app.config_environment_loader import load_config_from_environment
from netra_backend.app.config_validation import validate_required_config


def load_env_var(env_var: str, config: 'Settings', field_name: str) -> bool:
    """Load a single environment variable into config."""
    value = os.environ.get(env_var)
    if value and hasattr(config, field_name):
        setattr(config, field_name, value)
        logger.debug(f"Set {field_name} from {env_var}")
        return True
    return False


def set_clickhouse_host(config: 'Settings', value: str) -> None:
    """Set ClickHouse host in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.host = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.host = value
    logger.debug(f"Set ClickHouse host: {value}")


def _validate_port_value(value: str) -> int:
    """Validate and convert port value to integer."""
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid CLICKHOUSE_PORT: {value}")
        raise

def _set_port_on_config(config: 'Settings', port: int) -> None:
    """Set port on ClickHouse configuration objects."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.port = port
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.port = port

def set_clickhouse_port(config: 'Settings', value: str) -> None:
    """Set ClickHouse port in config."""
    port = _validate_port_value(value)
    _set_port_on_config(config, port)
    logger.debug(f"Set ClickHouse port: {value}")


def set_clickhouse_password(config: 'Settings', value: str) -> None:
    """Set ClickHouse password in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.password = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.password = value
    logger.debug("Set ClickHouse password")


def set_clickhouse_user(config: 'Settings', value: str) -> None:
    """Set ClickHouse user in config."""
    if hasattr(config, 'clickhouse_native'):
        config.clickhouse_native.user = value
    if hasattr(config, 'clickhouse_https'):
        config.clickhouse_https.user = value
    logger.debug(f"Set ClickHouse user: {value}")


def set_gemini_api_key(config: 'Settings', value: str) -> None:
    """Set Gemini API key for LLM configs."""
    llm_names = ['default', 'analysis', 'triage', 'data',
                 'optimizations_core', 'actions_to_meet_goals',
                 'reporting', 'google']
    for name in llm_names:
        set_llm_api_key(config, name, value)
    logger.debug("Set Gemini API key for LLM configs")


def set_llm_api_key(config: 'Settings', llm_name: str, api_key: str) -> None:
    """Set API key for a specific LLM config."""
    if hasattr(config, 'llm_configs'):
        if llm_name in config.llm_configs:
            llm_config = config.llm_configs[llm_name]
            if hasattr(llm_config, 'api_key'):
                llm_config.api_key = api_key


def get_critical_vars_mapping() -> Dict[str, str]:
    """Get mapping of critical environment variables."""
    database_vars = _get_database_vars()
    auth_vars = _get_auth_vars()
    env_vars = _get_env_vars()
    return {**database_vars, **auth_vars, **env_vars}

def _get_database_vars() -> Dict[str, str]:
    """Get database-related environment variable mappings."""
    return {
        "DATABASE_URL": "database_url",
        "REDIS_URL": "redis_url",
        "CLICKHOUSE_URL": "clickhouse_url"
    }

def _get_auth_vars() -> Dict[str, str]:
    """Get authentication-related environment variable mappings."""
    return {
        "SECRET_KEY": "secret_key",
        "JWT_SECRET_KEY": "jwt_secret_key",
        "FERNET_KEY": "fernet_key"
    }

def _get_env_vars() -> Dict[str, str]:
    """Get general environment variable mappings."""
    return {
        "LOG_LEVEL": "log_level",
        "ENVIRONMENT": "environment"
    }


def _navigate_to_parent_object(config: 'Settings', path_parts: list) -> object:
    """Navigate to parent object in config path."""
    obj = config
    for part in path_parts[:-1]:
        obj = _get_attribute_or_none(obj, part)
        if obj is None:
            return None
    return obj

def _get_attribute_or_none(obj: object, attr: str) -> object:
    """Get attribute from object or return None if not found."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return None

def _set_field_on_target(parent_obj: object, target_name: str, field: str, value: str) -> None:
    """Set field on target object if it exists."""
    if hasattr(parent_obj, target_name):
        target = getattr(parent_obj, target_name)
        if hasattr(target, field):
            setattr(target, field, value)

def apply_single_secret(config: 'Settings', path: str, field: str, value: str) -> None:
    """Apply a single secret to config at the given path."""
    parts = path.split('.')
    parent_obj = _navigate_to_parent_object(config, parts)
    if parent_obj:
        _set_field_on_target(parent_obj, parts[-1], field, value)