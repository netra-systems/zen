"""Configuration loader utilities - split from config.py for modularity."""

import os
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings
from app.logging_config import central_logger as logger


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


def set_clickhouse_port(config: 'Settings', value: str) -> None:
    """Set ClickHouse port in config."""
    try:
        port = int(value)
        if hasattr(config, 'clickhouse_native'):
            config.clickhouse_native.port = port
        if hasattr(config, 'clickhouse_https'):
            config.clickhouse_https.port = port
        logger.debug(f"Set ClickHouse port: {value}")
    except ValueError:
        logger.warning(f"Invalid CLICKHOUSE_PORT: {value}")


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


def apply_single_secret(config: 'Settings', path: str, field: str, value: str) -> None:
    """Apply a single secret to config at the given path."""
    parts = path.split('.')
    obj = config
    for part in parts[:-1]:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return
    if hasattr(obj, parts[-1]):
        target = getattr(obj, parts[-1])
        if hasattr(target, field):
            setattr(target, field, value)


def detect_cloud_run_environment() -> str:
    """Detect if running in Cloud Run and determine environment."""
    k_service = os.environ.get("K_SERVICE")
    k_revision = os.environ.get("K_REVISION")
    
    if k_service and "staging" in k_service.lower():
        logger.debug(f"Staging from K_SERVICE: {k_service}")
        return "staging"
    if os.environ.get("PR_NUMBER"):
        logger.debug(f"Staging from PR_NUMBER")
        return "staging"
    return ""