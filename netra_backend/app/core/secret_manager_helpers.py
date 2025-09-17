"""Secret manager helper utilities for decomposed operations."""

import os
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import secretmanager

from netra_backend.app.config import get_config
from netra_backend.app.logging_config import central_logger as logger
from shared.secret_mappings import get_secret_mappings, get_secret_name_for_env_var


def detect_environment_config() -> Tuple[str, bool]:
    """Detect environment and staging configuration."""
    config = get_config()
    environment = getattr(config, 'environment', 'development').lower()
    k_service = getattr(config, 'k_service', None)
    is_staging = environment == "staging" or (k_service and "staging" in k_service.lower())
    return environment, is_staging


def get_secret_names_list() -> List[str]:
    """Get complete list of secret names to fetch based on current environment."""
    config = get_config()
    environment = getattr(config, 'environment', 'development').lower()
    
    # Use shared secret mappings to get the proper secret names for the environment
    secret_mappings = get_secret_mappings(environment)
    
    # Return the Google secret names (keys) from the mappings
    if secret_mappings:
        logger.debug(f"Using environment-specific secret mappings for {environment}: {len(secret_mappings)} secrets")
        return list(secret_mappings.keys())
    
    # Fallback to hardcoded list for development/local environments
    logger.debug("Using fallback hardcoded secret list for local development")
    return [
        "gemini-api-key", "anthropic-api-key", "openai-api-key",
        "cohere-api-key", "mistral-api-key", "google-client-id",
        "google-client-secret", "jwt-secret-key", "fernet-key",
        "langfuse-secret-key", "langfuse-public-key", "clickhouse-password",
        "redis-default", "slack-webhook-url", "sendgrid-api-key", "sentry-dsn"
    ]


def determine_actual_secret_name(secret_name: str, is_staging: bool) -> str:
    """Determine actual secret name with environment-specific handling."""
    # Use shared mappings to determine if the secret name already has environment suffix
    config = get_config()
    environment = getattr(config, 'environment', 'development').lower()
    secret_mappings = get_secret_mappings(environment)
    
    # If secret name is already in the mappings, use it as-is (already has correct suffix)
    if secret_name in secret_mappings:
        logger.debug(f"Using exact secret name from mappings: {secret_name}")
        return secret_name
    
    # Legacy fallback behavior for backwards compatibility
    result = f"{secret_name}-staging" if is_staging else secret_name
    logger.debug(f"Using legacy suffix logic: {secret_name} -> {result}")
    return result


def initialize_fetch_tracking() -> Tuple[List[str], List[str]]:
    """Initialize tracking lists for secret fetching."""
    return [], []


def track_secret_result(secret_name: str, secret_value: Optional[str], 
                       successful: List[str], failed: List[str]) -> None:
    """Track individual secret fetch result."""
    if secret_value:
        successful.append(secret_name)
    else:
        failed.append(secret_name)


def prepare_secrets_dict(successful_secrets: List[str], failed_secrets: List[str]) -> Dict[str, Any]:
    """Prepare final secrets dictionary with logging."""
    logger.info(f"Google Secret Manager loading complete:")
    logger.info(f"  - Successfully loaded: {len(successful_secrets)} secrets")
    
    if successful_secrets:
        display_count = min(5, len(successful_secrets))
        display_list = successful_secrets[:display_count]
        suffix = '...' if len(successful_secrets) > 5 else ''
        logger.info(f"  - Loaded secrets: {', '.join(display_list)}{suffix}")
    
    log_critical_failures(failed_secrets)
    return {}


def log_critical_failures(failed_secrets: List[str]) -> None:
    """Log critical secret failures with proper categorization."""
    if not failed_secrets:
        return
    
    critical_secrets = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
    critical_failed = [s for s in failed_secrets if s in critical_secrets]
    
    if critical_failed:
        logger.warning(f"  - CRITICAL secrets not found: {', '.join(critical_failed)}")
    
    optional_failed = [s for s in failed_secrets if s not in critical_secrets]
    if optional_failed:
        logger.debug(f"  - Optional secrets not found: {', '.join(optional_failed)}")