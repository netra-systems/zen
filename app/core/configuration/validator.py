"""Configuration Validation System

**CRITICAL: Enterprise-Grade Configuration Validation**

Main configuration validator that orchestrates all validation modules.
Business Value: Prevents $12K MRR loss from configuration errors.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from typing import Dict, List, Tuple

from app.schemas.Config import AppConfig
from app.logging_config import central_logger as logger
from app.core.environment_constants import get_current_environment

from .validator_types import ValidationResult
from .validator_database import DatabaseValidator
from .validator_llm import LLMValidator
from .validator_auth import AuthValidator
from .validator_environment import EnvironmentValidator


class ConfigurationValidator:
    """Enterprise-grade configuration validation system.
    
    **CRITICAL**: All configuration MUST pass validation.
    Prevents configuration errors that cause revenue loss.
    """
    
    def __init__(self):
        """Initialize configuration validator."""
        self._logger = logger
        self._environment = self._get_environment()
        self._validation_rules = self._load_validation_rules()
        self._critical_fields = self._load_critical_fields()
        self._init_validators()
    
    def _get_environment(self) -> str:
        """Get current environment for validation rules."""
        return get_current_environment()
    
    def _init_validators(self) -> None:
        """Initialize all validation helper modules."""
        self._database_validator = DatabaseValidator(self._validation_rules, self._environment)
        self._llm_validator = LLMValidator(self._validation_rules, self._environment)
        self._auth_validator = AuthValidator(self._validation_rules, self._environment)
        self._environment_validator = EnvironmentValidator(self._validation_rules, self._environment)
    
    def refresh_environment(self) -> None:
        """Refresh environment detection for testing scenarios."""
        old_env = self._environment
        self._environment = self._get_environment()
        if old_env != self._environment:
            self._logger.info(f"Validator environment changed from {old_env} to {self._environment}")
            self._init_validators()
    
    def _load_validation_rules(self) -> Dict[str, dict]:
        """Load validation rules per environment."""
        return {
            "development": self._get_development_rules(),
            "staging": self._get_production_rules(),
            "production": self._get_production_rules(),
            "testing": self._get_development_rules()
        }
    
    def _get_development_rules(self) -> Dict[str, bool]:
        """Get development/testing validation rules."""
        return {
            "require_ssl": False,
            "allow_localhost": True,
            "require_secrets": False,
            "strict_validation": False
        }
    
    def _get_production_rules(self) -> Dict[str, bool]:
        """Get production/staging validation rules."""
        return {
            "require_ssl": True,
            "allow_localhost": False,
            "require_secrets": True,
            "strict_validation": True
        }
    
    def _load_critical_fields(self) -> Dict[str, List[str]]:
        """Load critical configuration fields per component."""
        return {
            "database": ["database_url"],
            "llm": ["llm_configs"],
            "auth": ["jwt_secret_key", "fernet_key"],
            "external": ["frontend_url", "api_base_url"],
            "secrets": ["jwt_secret_key", "fernet_key"]
        }
    
    def validate_complete_config(self, config: AppConfig) -> ValidationResult:
        """Perform comprehensive configuration validation."""
        errors, warnings = self._collect_validation_results(config)
        score = self._calculate_config_health_score(config, errors, warnings)
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, score)
    
    def _collect_validation_results(self, config: AppConfig) -> Tuple[List[str], List[str]]:
        """Collect all validation errors and warnings."""
        errors = self._collect_all_errors(config)
        warnings = self._llm_validator.validate_optional_features(config)
        return errors, warnings
    
    def _collect_all_errors(self, config: AppConfig) -> List[str]:
        """Collect all validation errors."""
        errors = []
        errors.extend(self._database_validator.validate_database_config(config))
        errors.extend(self._llm_validator.validate_llm_config(config))
        errors.extend(self._auth_validator.validate_auth_config(config))
        errors.extend(self._environment_validator.validate_external_services(config))
        return errors
    
    def _calculate_config_health_score(self, config: AppConfig, errors: List[str], warnings: List[str]) -> int:
        """Calculate configuration health score (0-100)."""
        base_score = 100
        penalties = self._calculate_score_penalties(errors, warnings)
        bonus = self._calculate_completeness_bonus(config)
        return self._compute_final_score(base_score, penalties, bonus)
    
    def _calculate_score_penalties(self, errors: List[str], warnings: List[str]) -> int:
        """Calculate score penalties for errors and warnings."""
        error_penalty = len(errors) * 15
        warning_penalty = len(warnings) * 5
        return error_penalty + warning_penalty
    
    def _compute_final_score(self, base_score: int, penalties: int, bonus: int) -> int:
        """Compute final configuration health score."""
        score = max(0, base_score - penalties + bonus)
        return min(100, score)
    
    def _calculate_completeness_bonus(self, config: AppConfig) -> int:
        """Calculate bonus points for configuration completeness."""
        present, total = self._count_critical_fields(config)
        if total > 0:
            completeness_ratio = present / total
            return int(completeness_ratio * 10)
        return 0
    
    def _count_critical_fields(self, config: AppConfig) -> Tuple[int, int]:
        """Count present and total critical fields."""
        present, total = 0, 0
        for component, fields in self._critical_fields.items():
            component_present, component_total = self._count_component_fields(config, fields)
            present += component_present
            total += component_total
        return present, total
    
    def _count_component_fields(self, config: AppConfig, fields: List[str]) -> Tuple[int, int]:
        """Count present and total fields for a component."""
        present, total = 0, 0
        for field in fields:
            total += 1
            if hasattr(config, field) and getattr(config, field):
                present += 1
        return present, total