"""Secret manager helper utilities for decomposed operations."""

from typing import Dict, Any, List, Optional, Tuple
from google.cloud import secretmanager
import os
from netra_backend.app.logging_config import central_logger as logger


def detect_environment_config() -> Tuple[str, bool]:
    """Detect environment and staging configuration."""
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    k_service = os.environ.get("K_SERVICE")
    is_staging = environment == "staging" or (k_service and "staging" in k_service.lower())
    return environment, is_staging


def get_secret_names_list() -> List[str]:
    """Get complete list of secret names to fetch."""
    return [
        "gemini-api-key", "anthropic-api-key", "openai-api-key",
        "cohere-api-key", "mistral-api-key", "google-client-id",
        "google-client-secret", "jwt-secret-key", "fernet-key",
        "langfuse-secret-key", "langfuse-public-key", "clickhouse-default-password",
        "clickhouse-development-password", "redis-default", "slack-webhook-url",
        "sendgrid-api-key", "sentry-dsn"
    ]


def determine_actual_secret_name(secret_name: str, is_staging: bool) -> str:
    """Determine actual secret name with staging suffix."""
    return f"{secret_name}-staging" if is_staging else secret_name


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