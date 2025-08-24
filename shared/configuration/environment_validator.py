"""
Environment Configuration Validator - Staging Deployment Critical Fix

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures due to localhost configurations
- Value Impact: Eliminates deployment errors that block staging releases
- Strategic Impact: Ensures reliable deployment pipeline for enterprise readiness

This module provides comprehensive validation to prevent localhost configurations
from reaching staging/production environments, which was a root cause of deployment failures.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EnvironmentConfigurationValidator:
    """Validates environment-specific configuration requirements."""
    
    def __init__(self):
        self.environment = self._detect_environment()
        self.validation_rules = self._load_validation_rules()
    
    def _detect_environment(self) -> str:
        """Detect current environment from multiple sources."""
        # Check explicit ENVIRONMENT variable
        env = os.getenv("ENVIRONMENT", "").lower()
        if env:
            return env
        
        # Check Cloud Run indicator
        if os.getenv("K_SERVICE"):
            return "staging"  # Cloud Run typically indicates staging
        
        # Check testing indicators
        if os.getenv("TESTING", "false").lower() == "true":
            return "test"
        
        # Check pytest
        import sys
        if 'pytest' in sys.modules:
            return "test"
        
        # Default to development
        return "development"
    
    def _load_validation_rules(self) -> Dict[str, Dict[str, any]]:
        """Load environment-specific validation rules."""
        return {
            "development": {
                "allow_localhost": True,
                "require_ssl": False,
                "require_external_services": False
            },
            "test": {
                "allow_localhost": True,
                "require_ssl": False,
                "require_external_services": False
            },
            "staging": {
                "allow_localhost": False,
                "require_ssl": True,
                "require_external_services": True
            },
            "production": {
                "allow_localhost": False,
                "require_ssl": True,
                "require_external_services": True
            }
        }
    
    def validate_configuration(self, config_vars: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate configuration variables for current environment.
        
        Args:
            config_vars: Dictionary of configuration variable names to values
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        rules = self.validation_rules.get(self.environment, {})
        
        # Check localhost restrictions
        if not rules.get("allow_localhost", True):
            errors.extend(self._check_localhost_violations(config_vars))
        
        # Check SSL requirements
        if rules.get("require_ssl", False):
            errors.extend(self._check_ssl_requirements(config_vars))
        
        # Check external service requirements
        if rules.get("require_external_services", False):
            errors.extend(self._check_external_service_requirements(config_vars))
        
        is_valid = len(errors) == 0
        
        if errors:
            logger.error(f"Configuration validation failed for {self.environment}: {errors}")
        else:
            logger.debug(f"Configuration validation passed for {self.environment}")
        
        return is_valid, errors
    
    def _check_localhost_violations(self, config_vars: Dict[str, str]) -> List[str]:
        """Check for localhost violations in configuration."""
        errors = []
        localhost_patterns = ["localhost", "127.0.0.1", "0.0.0.0"]
        
        # URL variables that should not contain localhost in non-dev environments
        url_vars = [
            "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL",
            "API_BASE_URL", "FRONTEND_URL", "AUTH_SERVICE_URL"
        ]
        
        for var_name, var_value in config_vars.items():
            if var_name in url_vars and var_value:
                if any(pattern in var_value for pattern in localhost_patterns):
                    errors.append(
                        f"{var_name} contains localhost/127.0.0.1 in {self.environment} environment: {var_value[:50]}..."
                    )
        
        return errors
    
    def _check_ssl_requirements(self, config_vars: Dict[str, str]) -> List[str]:
        """Check SSL parameter requirements for database connections."""
        errors = []
        
        database_url = config_vars.get("DATABASE_URL", "")
        if database_url:
            # Check if SSL is properly configured
            if not self._has_ssl_parameter(database_url):
                errors.append(f"DATABASE_URL missing SSL configuration in {self.environment} environment")
            
            # Check for mixed SSL parameters (critical staging issue)
            if self._has_mixed_ssl_parameters(database_url):
                errors.append(f"DATABASE_URL has conflicting SSL parameters: {database_url[:50]}...")
        
        return errors
    
    def _check_external_service_requirements(self, config_vars: Dict[str, str]) -> List[str]:
        """Check that external services are properly configured."""
        errors = []
        
        # Required external services for staging/production
        required_services = {
            "REDIS_URL": "Redis cache service",
            "CLICKHOUSE_HOST": "ClickHouse analytics service",
            "GEMINI_API_KEY": "Gemini AI service",
            "GOOGLE_CLIENT_ID": "Google OAuth service"
        }
        
        for var_name, service_name in required_services.items():
            if not config_vars.get(var_name):
                errors.append(f"Missing {service_name} configuration: {var_name} not set")
        
        return errors
    
    def _has_ssl_parameter(self, url: str) -> bool:
        """Check if URL has SSL configuration."""
        return "ssl=" in url or "sslmode=" in url
    
    def _has_mixed_ssl_parameters(self, url: str) -> bool:
        """Check if URL has both ssl and sslmode parameters (critical issue)."""
        return "ssl=" in url and "sslmode=" in url
    
    def get_staging_deployment_recommendations(self) -> List[str]:
        """Get specific recommendations for staging deployment issues."""
        recommendations = []
        
        if self.environment in ["staging", "production"]:
            recommendations.extend([
                "Ensure DATABASE_URL points to Cloud SQL instance",
                "Verify REDIS_URL points to Cloud Memory Store",
                "Confirm CLICKHOUSE_HOST is set to external ClickHouse instance",
                "Check that all OAuth secrets are configured in Secret Manager",
                "Validate SSL parameters: use sslmode=require for Cloud SQL"
            ])
        
        return recommendations
    
    def validate_staging_deployment_config(self) -> Tuple[bool, List[str], List[str]]:
        """Validate configuration specifically for staging deployment.
        
        Returns:
            Tuple of (is_valid, errors, recommendations)
        """
        # Get current environment variables
        config_vars = dict(os.environ)
        
        # Validate configuration
        is_valid, errors = self.validate_configuration(config_vars)
        
        # Get staging-specific recommendations
        recommendations = self.get_staging_deployment_recommendations()
        
        return is_valid, errors, recommendations


# Convenience function for easy import
def validate_staging_deployment() -> Tuple[bool, List[str], List[str]]:
    """Convenience function to validate staging deployment configuration."""
    validator = EnvironmentConfigurationValidator()
    return validator.validate_staging_deployment_config()


# Export main classes
__all__ = ["EnvironmentConfigurationValidator", "validate_staging_deployment"]