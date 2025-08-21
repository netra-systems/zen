"""Environment configuration loading utilities - part of modular config_loader split."""

import os
from typing import Dict, Any, Optional, List

from netra_backend.app.config_exceptions import ConfigLoadError
from netra_backend.app.logging_config import central_logger as logger


def load_config_from_environment(
    env_mapping: Dict[str, str],
    required_vars: Optional[List[str]] = None,
    default_values: Optional[Dict[str, Any]] = None,
    type_mapping: Optional[Dict[str, type]] = None,
    fallback_config: Optional[Dict[str, Any]] = None,
    allow_partial: bool = False,
    strict_types: bool = False
) -> Dict[str, Any]:
    """Load configuration from environment variables."""
    result = _initialize_config_result(default_values, fallback_config)
    
    required_vars = required_vars or []
    type_mapping = type_mapping or {}
    
    # Load from environment
    _load_environment_values(result, env_mapping, type_mapping, strict_types)
    
    # Check required variables
    _validate_required_variables(required_vars, allow_partial)
    
    return result


def _initialize_config_result(
    default_values: Optional[Dict[str, Any]], 
    fallback_config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Initialize configuration result with defaults and fallbacks."""
    result = {}
    
    # Apply defaults first
    if default_values:
        result.update(default_values)
    
    # Apply fallback config
    if fallback_config:
        result.update(fallback_config)
    
    return result


def _load_environment_values(
    result: Dict[str, Any], 
    env_mapping: Dict[str, str], 
    type_mapping: Dict[str, type], 
    strict_types: bool
) -> None:
    """Load values from environment variables with type conversion."""
    for env_var, config_key in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            converted_value = _convert_value_type(env_var, value, type_mapping, strict_types)
            if converted_value is not None:
                result[config_key] = converted_value


def _convert_value_type(
    env_var: str, 
    value: str, 
    type_mapping: Dict[str, type], 
    strict_types: bool
) -> Any:
    """Convert environment variable value to specified type."""
    if env_var not in type_mapping:
        return value
    
    try:
        target_type = type_mapping[env_var]
        if target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            return target_type(value)
    except (ValueError, TypeError) as e:
        if strict_types:
            raise ConfigLoadError(f"Type conversion failed for {env_var}: {e}")
        logger.warning(f"Type conversion failed for {env_var}: {e}")
        return None


def _validate_required_variables(required_vars: List[str], allow_partial: bool) -> None:
    """Validate that required environment variables are present."""
    if required_vars and not allow_partial:
        missing = [var for var in required_vars if var not in os.environ]
        if missing:
            raise ConfigLoadError(
                f"Missing required environment variables: {missing}",
                missing_keys=missing
            )