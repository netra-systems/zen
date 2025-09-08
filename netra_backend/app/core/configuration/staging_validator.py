"""Staging Configuration Validator

Ensures all required configuration is present and valid for staging deployment.
Prevents deployment with missing or placeholder values.

Business Value: Platform/Internal - System Stability
Prevents staging deployment failures due to configuration issues.
"""

from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger as logger


@dataclass
class ValidationResult:
    """Result of staging configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_critical: List[str]
    placeholders_found: Dict[str, str]


class StagingConfigurationValidator:
    """Validates staging environment configuration."""
    
    # Critical variables that MUST be present for staging
    CRITICAL_VARIABLES = [
        'ENVIRONMENT',
        # #removed-legacyremoved - now built from individual POSTGRES_* variables via DatabaseURLBuilder
        'POSTGRES_HOST',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'JWT_SECRET_KEY',
        'FERNET_KEY',
        'GCP_PROJECT_ID',
        'SERVICE_SECRET',
        'SERVICE_ID',
        'CLICKHOUSE_URL',  # CRITICAL: Remote ClickHouse Cloud URL from Google Secret Manager
    ]
    
    # Important variables that should be present
    IMPORTANT_VARIABLES = [
        'REDIS_URL',
        'REDIS_HOST',
        'CLICKHOUSE_HOST',
        'CLICKHOUSE_PASSWORD',
        # OAuth handled by auth service, not backend
        # 'GOOGLE_CLIENT_ID',
        # 'GOOGLE_CLIENT_SECRET',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'GEMINI_API_KEY',
    ]
    
    # Placeholder patterns that indicate incomplete configuration
    PLACEHOLDER_PATTERNS = [
        r'^$',  # Empty string
        r'placeholder',
        r'REPLACE',
        r'should-be-replaced',
        r'will-be-set',
        r'change-me',
        r'update-in-production',
        r'staging-.*-should-be-replaced',
        r'your-.*-here',
        r'TODO',
        r'FIXME',
        r'XXX',
    ]
    
    def __init__(self):
        """Initialize the validator."""
        self._env = get_env()
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._missing_critical: List[str] = []
        self._placeholders: Dict[str, str] = {}
    
    def validate(self) -> ValidationResult:
        """Validate staging configuration completeness."""
        self._reset_state()
        
        # Check environment is set to staging
        self._validate_environment()
        
        # Validate critical variables
        self._validate_critical_variables()
        
        # Validate important variables
        self._validate_important_variables()
        
        # Check for localhost references
        self._check_localhost_references()
        
        # Validate database connectivity
        self._validate_database_config()
        
        # Validate authentication config
        self._validate_auth_config()
        
        # Check GCP-specific configuration
        self._validate_gcp_config()
        
        return ValidationResult(
            is_valid=len(self._errors) == 0 and len(self._missing_critical) == 0,
            errors=self._errors,
            warnings=self._warnings,
            missing_critical=self._missing_critical,
            placeholders_found=self._placeholders
        )
    
    def _reset_state(self) -> None:
        """Reset validation state."""
        self._errors = []
        self._warnings = []
        self._missing_critical = []
        self._placeholders = {}
    
    def _validate_environment(self) -> None:
        """Validate ENVIRONMENT is set to staging."""
        env = self._env.get('ENVIRONMENT', '').lower()
        if not env:
            self._errors.append("ENVIRONMENT variable is not set")
        elif env != 'staging':
            self._errors.append(f"ENVIRONMENT is '{env}' but should be 'staging'")
    
    def _validate_critical_variables(self) -> None:
        """Validate all critical variables are present and not placeholders."""
        for var in self.CRITICAL_VARIABLES:
            value = self._env.get(var)
            
            if value is None:
                self._missing_critical.append(var)
                self._errors.append(f"Critical variable {var} is missing")
            elif self._is_placeholder(value):
                self._placeholders[var] = value
                self._errors.append(f"Critical variable {var} contains placeholder: '{value[:50]}'")
    
    def _validate_important_variables(self) -> None:
        """Validate important variables and warn about issues."""
        for var in self.IMPORTANT_VARIABLES:
            value = self._env.get(var)
            
            if value is None:
                self._warnings.append(f"Important variable {var} is missing")
            elif self._is_placeholder(value):
                self._placeholders[var] = value
                self._warnings.append(f"Important variable {var} contains placeholder: '{value[:50]}'")
    
    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is a placeholder."""
        if not value:
            return True
        
        value_lower = value.lower()
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, value_lower):
                return True
        
        return False
    
    def _check_localhost_references(self) -> None:
        """Check for localhost references in staging configuration."""
        localhost_patterns = ['localhost', '127.0.0.1', '0.0.0.0']
        
        vars_to_check = [
            # #removed-legacyno longer checked directly - built from POSTGRES_* variables
            'POSTGRES_HOST',
            'REDIS_URL',
            'REDIS_HOST',
            'CLICKHOUSE_HOST',
            'API_BASE_URL',
            'FRONTEND_URL',
            'AUTH_SERVICE_URL',
        ]
        
        for var in vars_to_check:
            value = self._env.get(var, '').lower()
            if value:
                for pattern in localhost_patterns:
                    if pattern in value:
                        self._errors.append(
                            f"{var} contains localhost reference '{pattern}' which is invalid for staging"
                        )
    
    def _validate_database_config(self) -> None:
        """Validate database configuration is complete."""
        # #removed-legacyis now built from individual POSTGRES_* variables via DatabaseURLBuilder
        # Check individual postgres vars instead
        postgres_host = self._env.get('POSTGRES_HOST', '')
        postgres_user = self._env.get('POSTGRES_USER', '')
        postgres_password = self._env.get('POSTGRES_PASSWORD', '')
        postgres_db = self._env.get('POSTGRES_DB', '')
        
        if postgres_host and postgres_user:
            if not postgres_password:
                self._errors.append("POSTGRES_PASSWORD is required when POSTGRES_HOST is set")
            
            # Check for proper staging database host format
            if postgres_host and 'staging' not in postgres_host and '/cloudsql/' not in postgres_host:
                self._warnings.append("POSTGRES_HOST doesn't appear to be a staging database")
            
            # For Cloud SQL Unix socket paths, SSL is not needed
            if postgres_host and '/cloudsql/' not in postgres_host:
                # For TCP connections, we should have SSL configured (handled by DatabaseURLBuilder)
                self._warnings.append("Ensure SSL is configured for TCP database connections (handled by DatabaseURLBuilder)")
        
        # Check that database name is specified
        if not postgres_db:
            self._warnings.append("POSTGRES_DB not specified, will use default database name")
    
    def _validate_auth_config(self) -> None:
        """Validate authentication configuration."""
        jwt_secret = self._env.get('JWT_SECRET_KEY', '')
        service_secret = self._env.get('SERVICE_SECRET', '')
        
        # Check JWT secret strength
        if jwt_secret and len(jwt_secret) < 32:
            self._errors.append(f"JWT_SECRET_KEY is too short ({len(jwt_secret)} chars), minimum 32 required")
        
        # Check service secret strength  
        if service_secret and len(service_secret) < 32:
            self._errors.append(f"SERVICE_SECRET is too short ({len(service_secret)} chars), minimum 32 required")
        
        # Ensure secrets are different
        if jwt_secret and service_secret and jwt_secret == service_secret:
            self._errors.append("JWT_SECRET_KEY and SERVICE_SECRET must be different")
    
    def _validate_gcp_config(self) -> None:
        """Validate GCP-specific configuration."""
        project_id = self._env.get('GCP_PROJECT_ID', '')
        
        if not project_id:
            self._errors.append("GCP_PROJECT_ID is required for staging deployment")
        elif project_id not in ['netra-staging', 'netra-staging-v2', '701982941522']:
            self._warnings.append(f"GCP_PROJECT_ID '{project_id}' doesn't match known staging projects")
        
        # Check for K_SERVICE (indicates Cloud Run environment)
        if self._env.get('K_SERVICE'):
            # In Cloud Run, these should be set
            required_cloud_run = ['K_REVISION', 'K_CONFIGURATION']
            for var in required_cloud_run:
                if not self._env.get(var):
                    self._warnings.append(f"Cloud Run variable {var} is missing")


def validate_staging_config() -> Tuple[bool, ValidationResult]:
    """Validate staging configuration and return results.
    
    Returns:
        Tuple of (is_valid, ValidationResult)
    """
    validator = StagingConfigurationValidator()
    result = validator.validate()
    
    # Log results
    if result.is_valid:
        logger.info("Staging configuration validation passed")
    else:
        logger.error(f"Staging configuration validation failed with {len(result.errors)} errors")
        for error in result.errors:
            logger.error(f"  - {error}")
    
    if result.warnings:
        logger.warning(f"Staging configuration has {len(result.warnings)} warnings")
        for warning in result.warnings:
            logger.warning(f"  - {warning}")
    
    return result.is_valid, result


def ensure_staging_ready() -> None:
    """Ensure staging configuration is ready, raise exception if not.
    
    Raises:
        ValueError: If staging configuration is invalid
    """
    is_valid, result = validate_staging_config()
    
    if not is_valid:
        error_msg = "Staging configuration is invalid:\n"
        error_msg += "\n".join(f"  - {e}" for e in result.errors)
        
        if result.missing_critical:
            error_msg += f"\n\nMissing critical variables: {', '.join(result.missing_critical)}"
        
        if result.placeholders_found:
            error_msg += f"\n\nPlaceholder values found in: {', '.join(result.placeholders_found.keys())}"
        
        raise ValueError(error_msg)