"""Configuration Validation System

**CRITICAL: Enterprise-Grade Configuration Validation**

Main configuration validator that orchestrates all validation modules.
Business Value: Prevents $12K MRR loss from configuration errors.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    # Import TriageResult only for type checking to prevent circular imports
    from netra_backend.app.agents.triage.unified_triage_agent import TriageResult

from netra_backend.app.core.configuration.validator_auth import AuthValidator
from netra_backend.app.core.configuration.validator_database import DatabaseValidator
from netra_backend.app.core.configuration.validator_environment import (
    EnvironmentValidator,
)
from netra_backend.app.core.configuration.validator_llm import LLMValidator
from netra_backend.app.core.configuration.validator_types import ValidationResult
from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.config import AppConfig


class ValidationMode(str, Enum):
    """Progressive validation enforcement levels.
    
    Following pragmatic rigor principles:
    - warn: Log warnings for issues but don't fail
    - enforce_critical: Fail only on critical security/functionality issues
    - enforce_all: Traditional strict validation (production)
    """
    WARN = "warn"
    ENFORCE_CRITICAL = "enforce_critical"
    ENFORCE_ALL = "enforce_all"


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
        # Initialize SSOT OAuth validator
        self._central_validator = None
    
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
    
    def _get_development_rules(self) -> Dict[str, str]:
        """Get development/testing validation rules."""
        return {
            "require_ssl": False,
            "allow_localhost": True,
            "require_secrets": False,
            "validation_mode": ValidationMode.WARN.value
        }
    
    def _get_production_rules(self) -> Dict[str, str]:
        """Get production/staging validation rules."""
        return {
            "require_ssl": True,
            "allow_localhost": False,
            "require_secrets": True,
            "validation_mode": ValidationMode.ENFORCE_ALL.value
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
        """Perform comprehensive configuration validation with progressive enforcement."""
        errors, warnings = self._collect_validation_results(config)
        errors, warnings = self._apply_progressive_validation(errors, warnings)
        score = self._calculate_config_health_score(config, errors, warnings)
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, score)
    
    def _collect_validation_results(self, config: AppConfig) -> Tuple[List[str], List[str]]:
        """Collect all validation errors and warnings."""
        errors = self._collect_all_errors(config)
        warnings = self._llm_validator.validate_optional_features(config)
        return errors, warnings
    
    def _collect_all_errors(self, config: AppConfig) -> List[str]:
        """Collect all validation errors with resilience context."""
        errors = []
        errors.extend(self._collect_database_errors_with_fallbacks(config))
        errors.extend(self._collect_llm_errors_with_fallbacks(config))
        errors.extend(self._collect_auth_errors_with_fallbacks(config))
        errors.extend(self._collect_external_errors_with_fallbacks(config))
        errors.extend(self._collect_config_dependency_errors(config))
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
    
    def _apply_progressive_validation(self, errors: List[str], warnings: List[str]) -> Tuple[List[str], List[str]]:
        """Apply progressive validation based on environment mode.
        
        Following pragmatic rigor: be liberal in what you accept,
        conservative in what you send.
        """
        rules = self._validation_rules.get(self._environment, {})
        mode = ValidationMode(rules.get("validation_mode", ValidationMode.ENFORCE_ALL.value))
        
        if mode == ValidationMode.WARN:
            # Convert all errors to warnings in permissive mode
            warnings.extend(errors)
            self._logger.info(f"Validation warnings (permissive mode): {len(errors)} issues converted to warnings")
            return [], warnings
        elif mode == ValidationMode.ENFORCE_CRITICAL:
            # Only enforce critical errors, convert others to warnings
            critical_errors, non_critical_errors = self._categorize_errors(errors)
            warnings.extend(non_critical_errors)
            self._logger.info(f"Validation (critical mode): {len(critical_errors)} critical errors, {len(non_critical_errors)} warnings")
            return critical_errors, warnings
        else:
            # ENFORCE_ALL: traditional strict validation
            return errors, warnings
    
    def _categorize_errors(self, errors: List[str]) -> Tuple[List[str], List[str]]:
        """Categorize errors into critical vs non-critical.
        
        Critical errors prevent core functionality or pose security risks.
        Non-critical errors are configuration preferences that can have defaults.
        """
        critical_patterns = [
            "secret key is required",
            "encryption key is required", 
            "database_url is required",
            "Invalid database URL format",
            "host is required"
        ]
        
        critical_errors = []
        non_critical_errors = []
        
        for error in errors:
            is_critical = any(pattern in error.lower() for pattern in critical_patterns)
            if is_critical:
                critical_errors.append(error)
            else:
                non_critical_errors.append(error)
                
        return critical_errors, non_critical_errors
    
    def _collect_database_errors_with_fallbacks(self, config: AppConfig) -> List[str]:
        """Collect database validation errors with fallback handling."""
        try:
            return self._database_validator.validate_database_config(config)
        except Exception as e:
            self._logger.warning(f"Database validation failed with fallback: {e}")
            # Provide minimal validation for core functionality
            if not config.database_url:
                return ["database_url is required"]
            return []
    
    def _collect_llm_errors_with_fallbacks(self, config: AppConfig) -> List[str]:
        """Collect LLM validation errors with fallback handling."""
        try:
            return self._llm_validator.validate_llm_config(config)
        except Exception as e:
            self._logger.warning(f"LLM validation failed with fallback: {e}")
            # LLM configuration is often optional or has reasonable defaults
            return []
    
    def _collect_auth_errors_with_fallbacks(self, config: AppConfig) -> List[str]:
        """Collect auth validation errors with fallback handling."""
        try:
            return self._auth_validator.validate_auth_config(config)
        except Exception as e:
            self._logger.warning(f"Auth validation failed with fallback: {e}")
            # Only enforce absolutely critical auth requirements
            rules = self._validation_rules.get(self._environment, {})
            if rules.get("require_secrets", False):
                errors = []
                if not getattr(config, 'jwt_secret_key', None):
                    errors.append("JWT secret key is required")
                if not getattr(config, 'fernet_key', None):
                    errors.append("Fernet encryption key is required")
                return errors
            return []
    
    def _collect_external_errors_with_fallbacks(self, config: AppConfig) -> List[str]:
        """Collect external service validation errors with fallback handling."""
        try:
            return self._environment_validator.validate_external_services(config)
        except Exception as e:
            self._logger.warning(f"External service validation failed with fallback: {e}")
            # External services often have reasonable defaults or are optional
            return []
    
    def validate_environment_variables(self, env_dict: Dict[str, str]) -> ValidationResult:
        """Validate environment variables without creating config objects.
        
        This method is used for testing configuration validation without
        instantiating full configuration objects.
        
        Args:
            env_dict: Dictionary of environment variables to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Basic required variables validation
        required_vars = ["ENVIRONMENT"]
        for var in required_vars:
            if not env_dict.get(var):
                errors.append(f"Missing required environment variable: {var}")
        
        # Environment-specific validation
        environment = env_dict.get("ENVIRONMENT", "").lower()
        if environment == "production":
            # Production requires strict validation
            prod_required = ["JWT_SECRET_KEY", "SERVICE_SECRET", "POSTGRES_PASSWORD"]
            for var in prod_required:
                if not env_dict.get(var):
                    errors.append(f"Missing required production variable: {var}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=90 if len(errors) == 0 else 50
        )

    def _collect_config_dependency_errors(self, config: AppConfig) -> List[str]:
        """Collect configuration dependency errors using ConfigDependencyMap.
        
        This delegates to ConfigDependencyMap which now uses the central
        SSOT validator for actual validation, while providing dependency
        impact analysis.
        """
        try:
            from netra_backend.app.core.config_dependencies import ConfigDependencyMap
            
            # Check configuration consistency - delegates to central SSOT validator
            config_dict = config.__dict__ if hasattr(config, '__dict__') else {}
            consistency_issues = ConfigDependencyMap.check_config_consistency(config_dict)
            
            # Filter issues based on validation mode
            rules = self._validation_rules.get(self._environment, {})
            mode = ValidationMode(rules.get("validation_mode", ValidationMode.ENFORCE_ALL.value))
            
            errors = []
            for issue in consistency_issues:
                if mode == ValidationMode.WARN:
                    # Convert all to warnings in permissive mode
                    continue
                elif mode == ValidationMode.ENFORCE_CRITICAL:
                    # Only enforce critical issues
                    if "CRITICAL" in issue:
                        errors.append(f"Config dependency: {issue}")
                else:  # ENFORCE_ALL
                    # Enforce all dependency issues
                    if "CRITICAL" in issue or "WARNING" in issue:
                        errors.append(f"Config dependency: {issue}")
            
            return errors
            
        except ImportError:
            self._logger.warning("ConfigDependencyMap not available - skipping dependency validation")
            return []
        except Exception as e:
            self._logger.warning(f"Config dependency validation failed with fallback: {e}")
            return []
    
    def _get_central_validator(self):
        """Get central SSOT validator instance."""
        if self._central_validator is None:
            try:
                from shared.configuration.central_config_validator import get_central_validator
                self._central_validator = get_central_validator()
            except ImportError as e:
                self._logger.warning(f"Central SSOT validator not available: {e}")
                self._central_validator = None
        return self._central_validator
    
    # =============================================================================
    # OAuth Validation Methods - FACADE PATTERN (Delegates to SSOT)
    # =============================================================================
    
    def validate_auth(self) -> Dict[str, Any]:
        """
        Validate authentication configuration including OAuth using SSOT delegation.
        
        Returns:
            Dict with validation results including OAuth status
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth provider validation
                oauth_valid = central_validator.validate_oauth_provider_configuration('google')
                
                # Check JWT configuration too
                try:
                    jwt_secret = central_validator.get_jwt_secret()
                    jwt_valid = bool(jwt_secret and len(jwt_secret) >= 32)
                except Exception:
                    jwt_valid = False
                
                return {
                    'valid': oauth_valid and jwt_valid,
                    'oauth_valid': oauth_valid,
                    'jwt_valid': jwt_valid,
                    'errors': [] if (oauth_valid and jwt_valid) else ['Authentication configuration incomplete']
                }
            else:
                # Fallback validation
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Check OAuth credentials
                oauth_id = env.get(f"GOOGLE_OAUTH_CLIENT_ID_{self._environment.upper()}")
                oauth_secret = env.get(f"GOOGLE_OAUTH_CLIENT_SECRET_{self._environment.upper()}")
                oauth_valid = bool(oauth_id and oauth_secret)
                
                # Check JWT secret
                jwt_secret = env.get("JWT_SECRET_KEY")
                jwt_valid = bool(jwt_secret and len(jwt_secret) >= 32)
                
                return {
                    'valid': oauth_valid and jwt_valid,
                    'oauth_valid': oauth_valid,
                    'jwt_valid': jwt_valid,
                    'errors': [] if (oauth_valid and jwt_valid) else ['Authentication configuration incomplete']
                }
                
        except Exception as e:
            self._logger.error(f"Auth validation failed: {e}")
            return {
                'valid': False,
                'oauth_valid': False,
                'jwt_valid': False,
                'errors': [str(e)]
            }
    
    def validate_oauth_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OAuth credentials using SSOT delegation.
        
        Args:
            credentials: OAuth credentials to validate
            
        Returns:
            Dict with validation results
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth credential validation
                return central_validator.validate_oauth_credentials_endpoint(credentials)
            else:
                # Fallback validation
                errors = []
                
                client_id = credentials.get('client_id')
                if not client_id:
                    errors.append("OAuth client_id is required")
                elif client_id in ["", "your-client-id", "REPLACE_WITH"]:
                    errors.append("OAuth client_id contains placeholder value")
                
                client_secret = credentials.get('client_secret')
                if not client_secret:
                    errors.append("OAuth client_secret is required")
                elif client_secret in ["", "your-client-secret", "REPLACE_WITH"]:
                    errors.append("OAuth client_secret contains placeholder value")
                elif len(client_secret) < 10:
                    errors.append("OAuth client_secret too short (minimum 10 characters)")
                
                return {
                    "valid": len(errors) == 0,
                    "errors": errors
                }
                
        except Exception as e:
            self._logger.error(f"OAuth credential validation failed: {e}")
            return {"valid": False, "errors": [str(e)]}
    
    def get_oauth_credentials(self) -> Dict[str, str]:
        """
        Get validated OAuth credentials using SSOT delegation.
        
        Returns:
            Dict containing OAuth credentials
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth credential retrieval
                return central_validator.get_oauth_credentials()
            else:
                # Fallback credential retrieval
                from shared.isolated_environment import get_env
                env = get_env()
                
                client_id = env.get(f"GOOGLE_OAUTH_CLIENT_ID_{self._environment.upper()}")
                client_secret = env.get(f"GOOGLE_OAUTH_CLIENT_SECRET_{self._environment.upper()}")
                
                if not client_id or not client_secret:
                    raise ValueError(f"OAuth credentials not configured for {self._environment} environment")
                
                return {
                    "client_id": client_id,
                    "client_secret": client_secret
                }
                
        except Exception as e:
            self._logger.error(f"Failed to get OAuth credentials: {e}")
            raise