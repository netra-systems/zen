"""
JWT Secret Cross-Service Validation

Ensures all services use the same JWT secret to prevent auth mismatches.
This module prevents WebSocket 1011 errors caused by JWT secret inconsistencies.

Business Value:
- Prevents $50K+ MRR loss from WebSocket authentication failures
- Ensures auth service and backend use identical JWT secrets
- Provides validation checks for staging/production deployments

CRITICAL: This validator must be used in startup checks to ensure
cross-service JWT secret consistency before accepting connections.
"""

import logging
from typing import Dict, List, Optional
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret

logger = logging.getLogger(__name__)


class JWTSecretValidator:
    """Validates JWT secret consistency across services."""
    
    def __init__(self):
        self.services_checked: Dict[str, str] = {}
        self.validation_errors: List[str] = []
    
    def validate_cross_service_consistency(self) -> Dict[str, any]:
        """
        Validate JWT secret consistency across all services.
        Returns validation report with any issues found.
        
        This method prevents the WebSocket 1011 error scenario by ensuring
        that auth service and backend service use the same JWT secret.
        """
        try:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            
            # Get the unified JWT secret (SSOT)
            unified_secret = get_unified_jwt_secret()
            
            # Validate against expected environment variables
            if environment == "staging":
                expected_vars = [
                    "JWT_SECRET_STAGING",
                    "JWT_SECRET_KEY",
                    "JWT_SECRET"
                ]
            else:
                expected_vars = [
                    f"JWT_SECRET_{environment.upper()}",
                    "JWT_SECRET_KEY",
                    "JWT_SECRET"
                ]
            
            issues = []
            available_secrets = {}
            
            # Check each environment variable for consistency
            for var_name in expected_vars:
                var_value = env.get(var_name)
                if var_value:
                    available_secrets[var_name] = len(var_value)  # Store length for logging
                    if var_value.strip() != unified_secret:
                        issues.append(f"JWT secret mismatch: {var_name} != unified secret")
                        logger.error(f"JWT SECRET MISMATCH: {var_name} does not match unified secret")
            
            # Additional staging-specific validation
            if environment == "staging":
                # Ensure JWT_SECRET_STAGING exists and is used
                staging_secret = env.get("JWT_SECRET_STAGING")
                if not staging_secret:
                    issues.append("JWT_SECRET_STAGING not configured for staging environment")
                elif len(staging_secret.strip()) < 32:
                    issues.append(f"JWT_SECRET_STAGING too short: {len(staging_secret.strip())} chars (need 32+)")
            
            return {
                "valid": len(issues) == 0,
                "environment": environment,
                "unified_secret_length": len(unified_secret),
                "variables_checked": expected_vars,
                "available_secrets": available_secrets,
                "issues": issues,
                "recommendation": "All JWT secrets must use the same value to prevent WebSocket 1011 errors" if issues else "JWT secret configuration is consistent"
            }
            
        except Exception as e:
            logger.error(f"JWT secret validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "recommendation": "Fix JWT secret configuration to prevent authentication failures"
            }
    
    def validate_staging_configuration(self) -> Dict[str, any]:
        """
        Staging-specific JWT secret validation.
        
        This addresses the specific staging issues identified in the 1011 bug report.
        """
        try:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            
            if environment != "staging":
                return {
                    "valid": True,
                    "message": f"Staging validation not applicable for {environment}"
                }
            
            issues = []
            warnings = []
            
            # Check for staging-specific secret
            staging_secret = env.get("JWT_SECRET_STAGING")
            if not staging_secret:
                issues.append("JWT_SECRET_STAGING not configured")
            elif len(staging_secret.strip()) < 32:
                issues.append(f"JWT_SECRET_STAGING too short: {len(staging_secret.strip())} chars")
            
            # Check for fallback secrets
            fallback_secret = env.get("JWT_SECRET_KEY")
            if not fallback_secret:
                warnings.append("JWT_SECRET_KEY not configured as fallback")
            
            # Verify unified resolution works
            try:
                unified_secret = get_unified_jwt_secret()
                if len(unified_secret) < 32:
                    issues.append(f"Unified JWT secret too short: {len(unified_secret)} chars")
            except Exception as e:
                issues.append(f"Unified JWT secret resolution failed: {str(e)}")
            
            return {
                "valid": len(issues) == 0,
                "environment": "staging",
                "issues": issues,
                "warnings": warnings,
                "recommendation": "Configure JWT_SECRET_STAGING with 32+ character secret" if issues else "Staging JWT configuration is valid"
            }
            
        except Exception as e:
            logger.error(f"Staging JWT validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "recommendation": "Fix staging JWT configuration immediately"
            }


def validate_jwt_secrets() -> bool:
    """
    Quick validation function for use in startup checks.
    
    Returns:
        True if JWT secrets are consistent, False otherwise
    """
    validator = JWTSecretValidator()
    result = validator.validate_cross_service_consistency()
    
    if not result["valid"]:
        logger.error("JWT secret validation failed!")
        logger.error(f"Issues: {result.get('issues', [])}")
        logger.error(f"Recommendation: {result.get('recommendation', 'Fix JWT configuration')}")
    
    return result["valid"]


def validate_staging_jwt_config() -> bool:
    """
    Staging-specific validation for JWT configuration.
    
    Returns:
        True if staging JWT config is valid, False otherwise
    """
    validator = JWTSecretValidator()
    result = validator.validate_staging_configuration()
    
    if not result["valid"]:
        logger.error("Staging JWT validation failed!")
        logger.error(f"Issues: {result.get('issues', [])}")
        logger.error(f"Recommendation: {result.get('recommendation', 'Fix staging JWT config')}")
    
    return result["valid"]


def get_jwt_validation_report() -> Dict[str, any]:
    """
    Get comprehensive JWT validation report for debugging.
    
    Returns:
        Dict with validation results and detailed diagnostics
    """
    validator = JWTSecretValidator()
    general_result = validator.validate_cross_service_consistency()
    staging_result = validator.validate_staging_configuration()
    
    return {
        "general_validation": general_result,
        "staging_validation": staging_result,
        "overall_valid": general_result["valid"] and staging_result["valid"],
        "timestamp": time.time(),
        "environment": get_env().get("ENVIRONMENT", "development").lower()
    }


# Ensure time import is available
import time


__all__ = [
    "JWTSecretValidator",
    "validate_jwt_secrets",
    "validate_staging_jwt_config", 
    "get_jwt_validation_report"
]