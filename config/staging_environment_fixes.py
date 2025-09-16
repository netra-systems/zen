"""
Staging Environment Configuration Fixes for Issue #1278

This module provides critical environment variable fixes and configuration
overrides specifically for the staging environment to address container
startup failures and import dependency issues.

Business Value: Ensures staging environment reliability and prevents $500K+ ARR impact.
"""

import os
import logging
from typing import Dict, Any, Optional
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


def get_staging_environment_fixes() -> Dict[str, Any]:
    """
    Get staging environment fixes for Issue #1278.

    Returns critical environment variables and timeout settings to resolve:
    1. Database connection timeout failures (15s -> 90s)
    2. Container startup issues with missing modules
    3. VPC connector capacity constraints
    4. WebSocket middleware import failures

    Returns:
        Dictionary with staging environment fixes
    """
    return {
        # Database timeout fixes
        "AUTH_DB_VALIDATION_TIMEOUT": "90.0",
        "AUTH_DB_ENGINE_TIMEOUT": "45.0",
        "AUTH_DB_URL_TIMEOUT": "15.0",

        # Backend database timeout alignment
        "BACKEND_DB_INITIALIZATION_TIMEOUT": "90.0",
        "BACKEND_DB_CONNECTION_TIMEOUT": "50.0",
        "BACKEND_DB_POOL_TIMEOUT": "60.0",

        # Container startup configuration
        "CONTAINER_STARTUP_TIMEOUT": "180",  # 3 minutes for complex dependencies
        "HEALTH_CHECK_TIMEOUT": "30",
        "GRACEFUL_SHUTDOWN_TIMEOUT": "60",

        # VPC connector capacity management
        "VPC_CONNECTOR_TIMEOUT_BUFFER": "30.0",
        "CLOUD_SQL_CONNECTION_POOL_SIZE": "10",  # Reduced for capacity
        "CLOUD_SQL_MAX_OVERFLOW": "15",

        # Import dependency fixes
        "PYTHONPATH_INCLUDE_AUTH_SERVICE": "true",
        "MODULE_IMPORT_TIMEOUT": "30.0",
        "MIDDLEWARE_SETUP_GRACEFUL_DEGRADATION": "true",

        # Environment detection fixes
        "ENVIRONMENT": "staging",
        "ENV": "staging",
        "DEPLOYMENT_ENVIRONMENT": "staging",
        "GCP_ENVIRONMENT": "staging",

        # Logging for debugging
        "LOG_LEVEL": "INFO",
        "DATABASE_CONNECTION_LOGGING": "true",
        "MIDDLEWARE_SETUP_LOGGING": "true",
    }


def apply_staging_environment_fixes() -> None:
    """
    Apply staging environment fixes for Issue #1278.

    This function sets critical environment variables if they're not already set,
    ensuring proper timeout configuration and dependency resolution.
    """
    fixes = get_staging_environment_fixes()
    env = get_env()
    applied_fixes = []

    for key, value in fixes.items():
        current_value = env.get(key)
        if not current_value:
            # Only set if not already configured
            os.environ[key] = str(value)
            applied_fixes.append(f"{key}={value}")
            logger.info(f"Applied staging fix: {key}={value}")
        else:
            logger.debug(f"Staging fix skipped (already set): {key}={current_value}")

    if applied_fixes:
        logger.info(f"Applied {len(applied_fixes)} staging environment fixes for Issue #1278")
        logger.debug(f"Applied fixes: {', '.join(applied_fixes)}")
    else:
        logger.info("No staging environment fixes needed - all variables already configured")


def validate_staging_configuration() -> Dict[str, Any]:
    """
    Validate staging configuration for Issue #1278 remediation.

    Returns:
        Dictionary with validation results and recommendations
    """
    env = get_env()
    validation_results = {
        "status": "healthy",
        "issues": [],
        "warnings": [],
        "critical_values": {},
    }

    # Check database timeout configuration
    auth_validation_timeout = float(env.get("AUTH_DB_VALIDATION_TIMEOUT", "15.0"))
    if auth_validation_timeout < 60.0:
        validation_results["issues"].append(
            f"AUTH_DB_VALIDATION_TIMEOUT ({auth_validation_timeout}s) is below recommended 60s minimum"
        )
        validation_results["status"] = "degraded"

    # Check environment detection
    environment_indicators = [
        env.get("ENVIRONMENT"),
        env.get("ENV"),
        env.get("DEPLOYMENT_ENVIRONMENT"),
        env.get("GOOGLE_CLOUD_PROJECT"),
        env.get("K_SERVICE"),
    ]

    staging_detected = any(
        indicator and "staging" in str(indicator).lower()
        for indicator in environment_indicators
    )

    if not staging_detected:
        validation_results["warnings"].append(
            "Staging environment not clearly detected - may fall back to development timeouts"
        )

    # Check container configuration
    container_timeout = int(env.get("CONTAINER_STARTUP_TIMEOUT", "60"))
    if container_timeout < 120:
        validation_results["warnings"].append(
            f"Container startup timeout ({container_timeout}s) may be insufficient for complex dependencies"
        )

    # Record critical values for debugging
    validation_results["critical_values"] = {
        "auth_db_validation_timeout": auth_validation_timeout,
        "container_startup_timeout": container_timeout,
        "staging_detected": staging_detected,
        "environment_indicators": {
            "ENVIRONMENT": env.get("ENVIRONMENT"),
            "ENV": env.get("ENV"),
            "GOOGLE_CLOUD_PROJECT": env.get("GOOGLE_CLOUD_PROJECT"),
            "K_SERVICE": env.get("K_SERVICE"),
        }
    }

    logger.info(f"Staging configuration validation: {validation_results['status']}")
    if validation_results["issues"]:
        logger.warning(f"Configuration issues found: {validation_results['issues']}")
    if validation_results["warnings"]:
        logger.info(f"Configuration warnings: {validation_results['warnings']}")

    return validation_results


def log_staging_configuration_summary() -> None:
    """Log comprehensive staging configuration summary for debugging Issue #1278."""
    env = get_env()

    logger.info("=" * 80)
    logger.info("STAGING CONFIGURATION SUMMARY - Issue #1278 Remediation")
    logger.info("=" * 80)

    # Database configuration
    logger.info("DATABASE CONFIGURATION:")
    logger.info(f"  AUTH_DB_VALIDATION_TIMEOUT: {env.get('AUTH_DB_VALIDATION_TIMEOUT', 'NOT_SET')}")
    logger.info(f"  AUTH_DB_ENGINE_TIMEOUT: {env.get('AUTH_DB_ENGINE_TIMEOUT', 'NOT_SET')}")
    logger.info(f"  BACKEND_DB_INITIALIZATION_TIMEOUT: {env.get('BACKEND_DB_INITIALIZATION_TIMEOUT', 'NOT_SET')}")

    # Environment detection
    logger.info("ENVIRONMENT DETECTION:")
    logger.info(f"  ENVIRONMENT: {env.get('ENVIRONMENT', 'NOT_SET')}")
    logger.info(f"  ENV: {env.get('ENV', 'NOT_SET')}")
    logger.info(f"  GOOGLE_CLOUD_PROJECT: {env.get('GOOGLE_CLOUD_PROJECT', 'NOT_SET')}")
    logger.info(f"  K_SERVICE: {env.get('K_SERVICE', 'NOT_SET')}")

    # Container configuration
    logger.info("CONTAINER CONFIGURATION:")
    logger.info(f"  CONTAINER_STARTUP_TIMEOUT: {env.get('CONTAINER_STARTUP_TIMEOUT', 'NOT_SET')}")
    logger.info(f"  HEALTH_CHECK_TIMEOUT: {env.get('HEALTH_CHECK_TIMEOUT', 'NOT_SET')}")

    # Import configuration
    logger.info("IMPORT CONFIGURATION:")
    logger.info(f"  PYTHONPATH: {env.get('PYTHONPATH', 'NOT_SET')}")
    logger.info(f"  MODULE_IMPORT_TIMEOUT: {env.get('MODULE_IMPORT_TIMEOUT', 'NOT_SET')}")

    logger.info("=" * 80)


# Auto-apply fixes when module is imported in staging environment
def _auto_apply_staging_fixes():
    """Automatically apply staging fixes when module is imported."""
    env = get_env()

    # Only auto-apply in staging environments
    environment_name = env.get("ENVIRONMENT", "").lower()
    env_name = env.get("ENV", "").lower()
    is_staging = (
        "staging" in environment_name or
        "staging" in env_name or
        env.get("GOOGLE_CLOUD_PROJECT") and env.get("K_SERVICE")
    )

    if is_staging:
        logger.info("Staging environment detected - auto-applying Issue #1278 fixes")
        try:
            apply_staging_environment_fixes()
            validation_results = validate_staging_configuration()
            if validation_results["status"] != "healthy":
                logger.warning(f"Staging configuration validation: {validation_results['status']}")
        except Exception as e:
            logger.error(f"Failed to auto-apply staging fixes: {e}")
    else:
        logger.debug("Non-staging environment detected - skipping auto-fixes")


# Auto-apply on import (only in staging)
_auto_apply_staging_fixes()