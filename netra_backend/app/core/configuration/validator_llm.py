"""LLM Configuration Validation

**CRITICAL: Enterprise-Grade LLM Validation**

LLM-specific validation helpers for configuration validation.
Business Value: Prevents LLM integration failures that impact AI operations.

Each function  <= 8 lines, file  <= 300 lines.
"""

from typing import List

from netra_backend.app.schemas.config import AppConfig


class LLMValidator:
    """LLM configuration validation helpers."""
    
    def __init__(self, validation_rules: dict, environment: str):
        """Initialize LLM validator."""
        self._validation_rules = validation_rules
        self._environment = environment
    
    def validate_llm_config(self, config: AppConfig) -> List[str]:
        """Validate LLM configuration."""
        if not self._has_llm_configs(config):
            return ["LLM configurations are missing"]
        return self._collect_llm_validation_errors(config)
    
    def _has_llm_configs(self, config: AppConfig) -> bool:
        """Check if LLM configurations exist."""
        return hasattr(config, 'llm_configs') and config.llm_configs
    
    def _collect_llm_validation_errors(self, config: AppConfig) -> List[str]:
        """Collect all LLM validation errors."""
        errors = []
        errors.extend(self._validate_llm_api_keys(config))
        errors.extend(self._validate_llm_models(config))
        return errors
    
    def _validate_llm_api_keys(self, config: AppConfig) -> List[str]:
        """Validate LLM API key configuration."""
        rules = self._validation_rules.get(self._environment, {})
        if not rules.get("require_secrets", False):
            return []
        return self._check_missing_api_keys(config)
    
    def _check_missing_api_keys(self, config: AppConfig) -> List[str]:
        """Check for missing LLM API keys."""
        missing_keys = []
        for llm_name, llm_config in config.llm_configs.items():
            if not hasattr(llm_config, 'api_key') or not llm_config.api_key:
                missing_keys.append(llm_name)
        if missing_keys:
            return [f"LLM API keys missing for: {', '.join(missing_keys)}"]
        return []
    
    def _validate_llm_models(self, config: AppConfig) -> List[str]:
        """Validate LLM model configurations."""
        errors = []
        for llm_name, llm_config in config.llm_configs.items():
            errors.extend(self._validate_single_llm_model(llm_name, llm_config))
        return errors
    
    def _validate_single_llm_model(self, llm_name: str, llm_config) -> List[str]:
        """Validate a single LLM model configuration."""
        errors = []
        errors.extend(self._check_llm_model_name(llm_name, llm_config))
        errors.extend(self._check_llm_provider(llm_name, llm_config))
        return errors
    
    def _check_llm_model_name(self, llm_name: str, llm_config) -> List[str]:
        """Check LLM model name exists."""
        if not hasattr(llm_config, 'model_name') or not llm_config.model_name:
            return [f"Model name missing for LLM config: {llm_name}"]
        return []
    
    def _check_llm_provider(self, llm_name: str, llm_config) -> List[str]:
        """Check LLM provider exists."""
        if not hasattr(llm_config, 'provider'):
            return [f"Provider missing for LLM config: {llm_name}"]
        return []
    
    def validate_optional_features(self, config: AppConfig) -> List[str]:
        """Validate optional features (generates warnings)."""
        warnings = self._check_llm_cache_warning(config)
        warnings.extend(self._check_llm_heartbeat_warning(config))
        return warnings
    
    def _check_llm_cache_warning(self, config: AppConfig) -> List[str]:
        """Check for LLM cache warning."""
        if not getattr(config, 'llm_cache_enabled', True):
            return ["LLM caching is disabled - may impact performance"]
        return []
    
    def _check_llm_heartbeat_warning(self, config: AppConfig) -> List[str]:
        """Check for LLM heartbeat warning."""
        if not getattr(config, 'llm_heartbeat_enabled', True):
            return ["LLM heartbeat monitoring is disabled"]
        return []