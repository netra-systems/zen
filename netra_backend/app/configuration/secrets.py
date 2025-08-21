"""Secret management for configuration.

Focused module for handling secrets loading and application.
Integrates with the secret manager for secure configuration.
"""

from typing import Any, Dict, List, Tuple

from netra_backend.app.core.secret_manager import SecretManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.Config import SECRET_CONFIG, AppConfig


def get_all_secret_mappings() -> Dict[str, Dict[str, Any]]:
    """Get the mapping of secrets to configuration fields."""
    mappings = {}
    for secret_ref in SECRET_CONFIG:
        targets = secret_ref.target_models or []
        mappings[secret_ref.name] = {
            "field": secret_ref.target_field,
            "targets": targets
        }
    return mappings


def load_secrets_into_config(config: AppConfig):
    """Load secrets into the configuration object."""
    try:
        secrets = _load_secrets()
        _handle_loaded_secrets(config, secrets)
    except Exception as e:
        logger.error(f"Failed to load secrets: {e}")


def _handle_loaded_secrets(config: AppConfig, secrets: Dict[str, Any]) -> None:
    """Handle loaded secrets."""
    if secrets:
        _process_secrets(config, secrets)
    else:
        logger.warning("No secrets loaded")


def _load_secrets() -> Dict[str, Any]:
    """Load secrets from secret manager."""
    logger.info("Loading secrets...")
    secret_manager = SecretManager()
    return secret_manager.load_secrets()


def _process_secrets(config: AppConfig, secrets: Dict) -> None:
    """Process and apply loaded secrets."""
    logger.info(f"Applying {len(secrets)} secrets")
    _apply_secrets_to_config(config, secrets)
    _log_secret_status(secrets)


def _apply_secrets_to_config(config: AppConfig, secrets: Dict[str, Any]):
    """Apply loaded secrets to configuration object."""
    mappings = get_all_secret_mappings()
    applied_count = _apply_all_secrets(config, secrets, mappings)
    logger.info(f"Applied {applied_count} secrets (from {len(secrets)} loaded)")


def _apply_all_secrets(config: AppConfig, secrets: Dict, mappings: Dict) -> int:
    """Apply all secrets and return count."""
    count = 0
    for name, value in secrets.items():
        if value and name in mappings:
            _apply_secret_mapping(config, mappings[name], value)
            count += 1
    return count


def _log_secret_status(secrets: Dict) -> None:
    """Log status of critical secrets."""
    critical, applied, missing = _analyze_critical_secrets(secrets)
    _log_secret_analysis(applied, missing)


def _analyze_critical_secrets(secrets: Dict) -> Tuple[List[str], List[str], List[str]]:
    """Analyze critical secrets status."""
    critical = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
    applied = [s for s in critical if s in secrets]
    missing = [s for s in critical if s not in secrets]
    return critical, applied, missing


def _log_secret_analysis(applied: List[str], missing: List[str]) -> None:
    """Log secret analysis results."""
    if applied:
        logger.info(f"Critical secrets loaded: {len(applied)} ({', '.join(applied)})")
    if missing:
        logger.warning(f"Critical secrets not found in loaded secrets: {len(missing)} ({', '.join(missing)})")


def _apply_secret_mapping(config: AppConfig, mapping: Dict[str, Any], secret_value: str):
    """Apply a single secret mapping to the configuration."""
    if not mapping["targets"]:
        _apply_direct_mapping(config, mapping, secret_value)
    else:
        _apply_nested_mapping(config, mapping, secret_value)


def _apply_direct_mapping(config: AppConfig, mapping: Dict[str, Any], secret_value: str) -> None:
    """Apply direct field mapping."""
    setattr(config, mapping["field"], secret_value)


def _apply_nested_mapping(config: AppConfig, mapping: Dict[str, Any], secret_value: str) -> None:
    """Apply nested field mapping."""
    for target in mapping["targets"]:
        _set_nested_field(config, target, mapping["field"], secret_value)


def _set_nested_field(config: AppConfig, target_path: str, field: str, value: str):
    """Set a nested field in the configuration object."""
    try:
        _choose_field_setter(config, target_path, field, value)
    except AttributeError as e:
        _handle_nested_field_error(field, target_path, e)


def _handle_nested_field_error(field: str, target_path: str, error: AttributeError) -> None:
    """Handle nested field setting errors."""
    logger.warning(f"Failed to set field {field} on {target_path}: {error}")


def _choose_field_setter(config: AppConfig, target_path: str, field: str, value: str) -> None:
    """Choose appropriate field setter method."""
    if '.' in target_path:
        _set_deep_nested_field(config, target_path, field, value)
    else:
        _set_direct_field(config, target_path, field, value)


def _set_deep_nested_field(config: AppConfig, target_path: str, field: str, value: str) -> None:
    """Set deeply nested field value."""
    parts = target_path.split('.', 1)
    parent_attr = getattr(config, parts[0])
    if isinstance(parent_attr, dict) and parts[1] in parent_attr:
        target_obj = parent_attr[parts[1]]
        _set_field_if_valid(target_obj, field, value)


def _set_direct_field(config: AppConfig, target_path: str, field: str, value: str) -> None:
    """Set direct field value."""
    target_obj = getattr(config, target_path, None)
    _set_field_if_valid(target_obj, field, value)


def _set_field_if_valid(target_obj: Any, field: str, value: str) -> None:
    """Set field if target object is valid."""
    if target_obj and hasattr(target_obj, field):
        setattr(target_obj, field, value)