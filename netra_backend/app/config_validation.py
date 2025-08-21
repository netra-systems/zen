"""Configuration validation utilities - part of modular config_loader split."""

from typing import Dict, Any, List, Optional, Callable

from netra_backend.app.config_exceptions import ConfigLoadError


def validate_required_config(
    config: Dict[str, Any], 
    required_keys: List[str],
    validators: Optional[Dict[str, Callable]] = None
) -> None:
    """Validate required configuration keys and values."""
    validators = validators or {}
    
    # Check missing keys
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ConfigLoadError(
            f"Missing required configuration keys: {missing_keys}",
            missing_keys=missing_keys
        )
    
    # Check empty values
    empty_keys = _check_empty_values(config, required_keys)
    if empty_keys:
        raise ConfigLoadError(
            f"Empty values for required keys: {empty_keys}",
            missing_keys=empty_keys
        )
    
    # Run custom validators
    validation_errors = _run_custom_validators(config, validators)
    if validation_errors:
        raise ConfigLoadError(
            f"Validation failed: {validation_errors}",
            invalid_values=validation_errors
        )


def _check_empty_values(config: Dict[str, Any], required_keys: List[str]) -> List[str]:
    """Check for empty values in required keys."""
    return [key for key in required_keys 
            if key in config and 
            (not config[key] or str(config[key]).strip() == "")]


def _run_custom_validators(config: Dict[str, Any], validators: Dict[str, Callable]) -> Dict[str, str]:
    """Run custom validation functions."""
    validation_errors = {}
    for key, validator in validators.items():
        if key in config:
            try:
                validator(config[key])
            except Exception as e:
                validation_errors[key] = str(e)
    return validation_errors