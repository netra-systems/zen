"""
Environment Validator Module

Business Value Justification:
- Segment: Enterprise/Security
- Business Goal: Security & Compliance
- Value Impact: Prevents production security breaches from test configurations
- Strategic Impact: Zero-tolerance policy for test flags in production

This module validates the runtime environment to ensure test configurations
never leak into staging or production environments. It fails fast at startup
if dangerous test variables are detected.
"""

import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class EnvironmentViolation:
    """Represents an environment configuration violation."""
    variable_name: str
    current_value: str
    environment: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str


class EnvironmentValidator:
    """Validates environment configuration for security and consistency."""
    
    # Test-only variables that must NEVER appear in staging/production
    FORBIDDEN_TEST_VARS = [
        "TESTING",
        "E2E_TESTING", 
        "AUTH_FAST_TEST_MODE",
        "PYTEST_CURRENT_TEST",
        "ALLOW_DEV_OAUTH_SIMULATION",
        "WEBSOCKET_AUTH_BYPASS",
        "SKIP_AUTH_VALIDATION",
        "TEST_MODE",
        "CI_TEST_RUN"
    ]
    
    # Variables that should not have localhost in staging/production
    LOCALHOST_SENSITIVE_VARS = [
        "AUTH_SERVICE_URL",
        "POSTGRES_HOST",  # Check POSTGRES_HOST instead of DATABASE_URL
        "CLICKHOUSE_HOST",
        "REDIS_URL",
        "WEBSOCKET_URL",
        "API_BASE_URL",
        "BACKEND_URL"
    ]
    
    # Required variables for each environment
    # Note: #removed-legacyis constructed from POSTGRES_* variables in staging/production
    REQUIRED_VARS = {
        "production": [
            "JWT_SECRET_PRODUCTION",  # Production uses JWT_SECRET_PRODUCTION
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "AUTH_SERVICE_URL",
            "ENVIRONMENT"
        ],
        "staging": [
            "JWT_SECRET_STAGING",  # Staging uses JWT_SECRET_STAGING per jwt_secret_standardization_hard_requirements.xml
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "AUTH_SERVICE_URL",
            "ENVIRONMENT"
        ],
        "development": [
            "ENVIRONMENT"
        ]
    }
    
    def __init__(self):
        """Initialize the environment validator."""
        self.violations: List[EnvironmentViolation] = []
        self.warnings: List[str] = []
    
    def validate_environment_at_startup(self) -> None:
        """
        Validate environment at application startup.
        Raises EnvironmentError if critical violations are found.
        """
        environment = self._get_current_environment()
        logger.info(f"Validating environment configuration for: {environment}")
        
        # Run all validation checks
        self._check_forbidden_test_variables(environment)
        self._check_localhost_references(environment)
        self._check_required_variables(environment)
        self._check_environment_consistency()
        
        # Process violations
        self._process_violations()
    
    def _get_current_environment(self) -> str:
        """Get the current environment name."""
        # Use unified environment management
        try:
            from shared.isolated_environment import get_env
            env = get_env()
            
            # Check multiple possible environment indicators
            environment = env.get("ENVIRONMENT", "").lower()
            if not environment:
                environment = env.get("NETRA_ENV", "").lower()
            if not environment:
                environment = "development"  # Default to development
        except ImportError:
            # Should never happen as IsolatedEnvironment is a core dependency
            logger.error("Failed to import IsolatedEnvironment - critical configuration error")
            environment = "development"  # Default to development for safety
        
        # Normalize environment names
        if environment in ["prod", "production"]:
            return "production"
        elif environment in ["stage", "staging"]:
            return "staging"
        elif environment in ["dev", "development", "local"]:
            return "development"
        elif environment in ["test", "testing", "e2e", "e2e_testing"]:
            return "testing"
        else:
            logger.warning(f"Unknown environment: {environment}, treating as development")
            return "development"
    
    def _check_forbidden_test_variables(self, environment: str) -> None:
        """Check for test variables in non-test environments."""
        if environment in ["staging", "production"]:
            env = get_env()
            for var in self.FORBIDDEN_TEST_VARS:
                value = env.get(var)
                if value:
                    # Any non-empty value is a violation
                    self.violations.append(EnvironmentViolation(
                        variable_name=var,
                        current_value=value[:50],  # Truncate for safety
                        environment=environment,
                        severity="CRITICAL",
                        description=f"Test variable {var} detected in {environment} environment"
                    ))
    
    def _check_localhost_references(self, environment: str) -> None:
        """Check for localhost references in staging/production."""
        if environment in ["staging", "production"]:
            env = get_env()
            for var in self.LOCALHOST_SENSITIVE_VARS:
                value = env.get(var, "").lower()
                if value and ("localhost" in value or "127.0.0.1" in value or "0.0.0.0" in value):
                    self.violations.append(EnvironmentViolation(
                        variable_name=var,
                        current_value=value[:50],  # Truncate for safety
                        environment=environment,
                        severity="HIGH" if environment == "staging" else "CRITICAL",
                        description=f"Localhost reference in {var} for {environment} environment"
                    ))
    
    def _check_required_variables(self, environment: str) -> None:
        """Check that required variables are present."""
        required = self.REQUIRED_VARS.get(environment, [])
        env = get_env()
        for var in required:
            value = env.get(var)
            if not value:
                self.violations.append(EnvironmentViolation(
                    variable_name=var,
                    current_value="<not set>",
                    environment=environment,
                    severity="HIGH",
                    description=f"Required variable {var} is missing in {environment}"
                ))
    
    def _check_environment_consistency(self) -> None:
        """Check for environment configuration consistency."""
        # Check if ENVIRONMENT and NETRA_ENV match (if both are set)
        env = get_env()
        env1 = env.get("ENVIRONMENT", "").lower()
        env2 = env.get("NETRA_ENV", "").lower()
        
        if env1 and env2:
            # Normalize and compare
            normalized_env1 = self._normalize_environment_name(env1)
            normalized_env2 = self._normalize_environment_name(env2)
            
            if normalized_env1 != normalized_env2:
                self.warnings.append(
                    f"Environment mismatch: ENVIRONMENT={env1}, NETRA_ENV={env2}"
                )
    
    def _normalize_environment_name(self, env: str) -> str:
        """Normalize environment name for comparison."""
        env = env.lower()
        if env in ["prod", "production"]:
            return "production"
        elif env in ["stage", "staging"]:
            return "staging"
        elif env in ["dev", "development", "local"]:
            return "development"
        elif env in ["test", "testing", "e2e", "e2e_testing"]:
            return "testing"
        return env
    
    def _process_violations(self) -> None:
        """Process violations and decide whether to fail or warn."""
        critical_violations = [v for v in self.violations if v.severity == "CRITICAL"]
        high_violations = [v for v in self.violations if v.severity == "HIGH"]
        
        # Log all violations
        for violation in self.violations:
            logger.error(
                f"Environment violation [{violation.severity}]: {violation.description} "
                f"(var={violation.variable_name}, value={violation.current_value})"
            )
        
        # Log warnings
        for warning in self.warnings:
            logger.warning(f"Environment warning: {warning}")
        
        # Fail fast on critical violations
        if critical_violations:
            error_msg = self._format_critical_error(critical_violations)
            logger.critical(error_msg)
            raise EnvironmentError(error_msg)
        
        # Warn on high severity violations but don't fail
        if high_violations:
            logger.warning(
                f"Found {len(high_violations)} HIGH severity environment violations. "
                "Application will continue but may have issues."
            )
    
    def _format_critical_error(self, violations: List[EnvironmentViolation]) -> str:
        """Format critical violations into an error message."""
        environment = violations[0].environment if violations else "unknown"
        var_list = [v.variable_name for v in violations]
        
        return (
            f"CRITICAL: Forbidden test variables detected in {environment} environment!\n"
            f"Variables: {', '.join(var_list)}\n"
            f"These variables must be removed before deploying to {environment}.\n"
            f"This is a security violation that could expose the system to attacks."
        )
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get a detailed validation report."""
        environment = self._get_current_environment()
        
        return {
            "environment": environment,
            "violations": [
                {
                    "variable": v.variable_name,
                    "value": v.current_value,
                    "severity": v.severity,
                    "description": v.description
                }
                for v in self.violations
            ],
            "warnings": self.warnings,
            "critical_count": len([v for v in self.violations if v.severity == "CRITICAL"]),
            "high_count": len([v for v in self.violations if v.severity == "HIGH"]),
            "is_valid": len([v for v in self.violations if v.severity == "CRITICAL"]) == 0
        }
    
    def validate_for_environment(self, target_environment: str) -> bool:
        """
        Validate current configuration for a specific target environment.
        Returns True if configuration is valid for target environment.
        """
        # Temporarily override environment for validation
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        env.set("ENVIRONMENT", target_environment, "environment_validator")
        
        try:
            # Create a new validator instance for clean state
            validator = EnvironmentValidator()
            validator._check_forbidden_test_variables(target_environment)
            validator._check_localhost_references(target_environment)
            validator._check_required_variables(target_environment)
            
            # Check if there are critical violations
            critical_violations = [v for v in validator.violations if v.severity == "CRITICAL"]
            return len(critical_violations) == 0
            
        finally:
            # Restore original environment
            if original_env is not None:
                env.set("ENVIRONMENT", original_env, "environment_validator")
            else:
                env.delete("ENVIRONMENT")


# Global validator instance
_validator: Optional[EnvironmentValidator] = None


def get_environment_validator() -> EnvironmentValidator:
    """Get or create the global environment validator instance."""
    global _validator
    if _validator is None:
        _validator = EnvironmentValidator()
    return _validator


def validate_environment_at_startup() -> None:
    """
    Convenience function to validate environment at startup.
    This should be called early in the application initialization.
    """
    validator = get_environment_validator()
    validator.validate_environment_at_startup()


def is_safe_for_production() -> bool:
    """
    Check if current configuration is safe for production.
    Returns True if no critical violations would occur in production.
    """
    validator = EnvironmentValidator()
    return validator.validate_for_environment("production")


def is_safe_for_staging() -> bool:
    """
    Check if current configuration is safe for staging.
    Returns True if no critical violations would occur in staging.
    """
    validator = EnvironmentValidator()
    return validator.validate_for_environment("staging")


def get_environment_report() -> Dict[str, Any]:
    """Get a detailed environment validation report."""
    validator = get_environment_validator()
    return validator.get_validation_report()