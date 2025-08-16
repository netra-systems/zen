"""Configuration Secrets Management Module

Handles loading, processing, and applying secrets to configuration.
"""

from typing import Dict, Any, List, Tuple
from app.schemas.Config import AppConfig
from app.core.secret_manager import SecretManager
from app.config_secrets import get_all_secret_mappings
from app.logging_config import central_logger as logger


class ConfigSecretsManager:
    """Handles secrets loading and application to configuration"""
    
    def __init__(self):
        self._secret_manager = SecretManager()
        self._logger = logger
    
    def load_secrets_into_config(self, config: AppConfig):
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
        applied_count = self._apply_all_secrets(config, secrets, mappings)
        self._logger.info(f"Applied {applied_count} secrets (from {len(secrets)} loaded)")
    
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
            self._logger.info(f"Critical secrets loaded: {len(applied)} ({', '.join(applied)})")
        if missing:
            self._logger.warning(f"Critical secrets not found in loaded secrets: {len(missing)} ({', '.join(missing)})")
    
    def _get_secret_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get the mapping of secrets to configuration fields."""
        return get_all_secret_mappings()
    
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
        except AttributeError as e:
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