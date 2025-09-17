"""
SSOT Staging Domain Configuration - Single Source of Truth for Staging Domains

This module provides the centralized domain configuration for staging environment
across the Netra Apex platform. This is the SINGLE SOURCE OF TRUTH for
all staging domain values.

Business Value: Platform/Critical - Ensures consistent staging domain configuration
preventing SSL certificate failures and service communication issues that affect
the Golden Path user flow protecting $500K+ ARR.

CRITICAL INFRASTRUCTURE UPDATE (Issue #1278):
Always use the current staging domains (*.netrasystems.ai):
- Backend/Auth: https://staging.netrasystems.ai
- Frontend: https://staging.netrasystems.ai
- WebSocket: wss://staging.netrasystems.ai

DEPRECATED - DO NOT USE: *.staging.netrasystems.ai URLs (causes SSL certificate failures)
NEVER USE: Direct Cloud Run URLs (bypasses load balancer and SSL)

Usage:
    from shared.constants.staging_domains import STAGING_DOMAINS, get_staging_domain

    # Get specific domain
    backend_url = STAGING_DOMAINS["BACKEND_URL"]
    frontend_url = STAGING_DOMAINS["FRONTEND_URL"]

    # Get domain with validation
    auth_url = get_staging_domain("AUTH_SERVICE_URL")

    # Use in configuration classes
    class StagingConfig(AppConfig):
        frontend_url: str = STAGING_DOMAINS["FRONTEND_URL"]
        api_base_url: str = STAGING_DOMAINS["BACKEND_URL"]
        auth_service_url: str = STAGING_DOMAINS["AUTH_SERVICE_URL"]
"""

from typing import Dict, Optional
from enum import Enum


class StagingDomainType(Enum):
    """Types of staging domains for validation."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    AUTH_SERVICE = "auth_service"
    WEBSOCKET = "websocket"
    API = "api"


# SSOT: Single Source of Truth for Staging Domains
# This is the ONLY place where staging domain URLs should be defined

# CRITICAL STAGING DOMAIN CONFIGURATION (Issue #1278)
# These domains MUST be used for all staging environment configurations
STAGING_DOMAINS = {
    # Core service domains using *.netrasystems.ai format
    "FRONTEND_URL": "https://staging.netrasystems.ai",
    "BACKEND_URL": "https://staging.netrasystems.ai",
    "AUTH_SERVICE_URL": "https://staging.netrasystems.ai",

    # API-specific domains (using main staging domain - api.staging.netrasystems.ai DNS not configured)
    "API_BASE_URL": "https://staging.netrasystems.ai",

    # WebSocket domains (using main staging domain - api.staging.netrasystems.ai DNS not configured)
    "WEBSOCKET_URL": "wss://staging.netrasystems.ai",
    "WEBSOCKET_BASE": "wss://staging.netrasystems.ai/ws",

    # Load balancer endpoints (preferred over direct Cloud Run)
    "LOAD_BALANCER_FRONTEND": "https://staging.netrasystems.ai",
    "LOAD_BALANCER_BACKEND": "https://staging.netrasystems.ai",
    "LOAD_BALANCER_AUTH": "https://staging.netrasystems.ai",
}

# DEPRECATED DOMAINS - DO NOT USE (Issue #1278)
# These cause SSL certificate failures and should not be used
DEPRECATED_STAGING_DOMAINS = {
    "OLD_FORMAT": [
        "*.staging.netrasystems.ai",  # Wrong subdomain format
        "https://app.staging.netrasystems.ai",
        "https://api.staging.netrasystems.ai",
        "https://auth-staging.netrasystems.ai",
    ],
    "CLOUD_RUN_DIRECT": [
        "https://netra-backend-staging-701982941522.us-central1.run.app",
        "https://netra-auth-service-701982941522.us-central1.run.app",
        "https://netra-frontend-staging-701982941522.us-central1.run.app",
    ]
}

# Service-specific domain mappings for easy access
STAGING_SERVICE_DOMAINS = {
    "frontend": STAGING_DOMAINS["FRONTEND_URL"],
    "backend": STAGING_DOMAINS["BACKEND_URL"],
    "auth_service": STAGING_DOMAINS["AUTH_SERVICE_URL"],
    "api": STAGING_DOMAINS["API_BASE_URL"],
    "websocket": STAGING_DOMAINS["WEBSOCKET_URL"],
}

# Domain validation patterns
VALID_STAGING_PATTERNS = [
    "*.netrasystems.ai",  # Correct format
    "staging.netrasystems.ai",  # Main staging domain
]

INVALID_STAGING_PATTERNS = [
    "*.staging.netrasystems.ai",  # Wrong format - deprecated
    "*.us-central1.run.app",  # Direct Cloud Run - bypasses load balancer
    "localhost",  # Development only
    "127.0.0.1",  # Development only
]


def get_staging_domain(domain_key: str) -> str:
    """
    Get a staging domain URL with validation.

    Args:
        domain_key: Key from STAGING_DOMAINS dict

    Returns:
        str: The staging domain URL

    Raises:
        KeyError: If domain_key is not found
        ValueError: If domain_key maps to deprecated domain
    """
    if domain_key not in STAGING_DOMAINS:
        raise KeyError(f"Unknown staging domain key: {domain_key}. Available keys: {list(STAGING_DOMAINS.keys())}")

    domain_url = STAGING_DOMAINS[domain_key]

    # Validate against deprecated patterns
    for deprecated_url in DEPRECATED_STAGING_DOMAINS["OLD_FORMAT"]:
        if deprecated_url in domain_url:
            raise ValueError(f"Domain {domain_url} uses deprecated format. Use *.netrasystems.ai instead.")

    for deprecated_url in DEPRECATED_STAGING_DOMAINS["CLOUD_RUN_DIRECT"]:
        if deprecated_url in domain_url:
            raise ValueError(f"Domain {domain_url} is direct Cloud Run URL. Use load balancer URL instead.")

    return domain_url


def get_staging_service_domain(service_name: str) -> str:
    """
    Get staging domain for a specific service.

    Args:
        service_name: Name of the service (frontend, backend, auth_service, api, websocket)

    Returns:
        str: The staging domain URL for the service

    Raises:
        KeyError: If service_name is not recognized
    """
    if service_name not in STAGING_SERVICE_DOMAINS:
        raise KeyError(f"Unknown service name: {service_name}. Available services: {list(STAGING_SERVICE_DOMAINS.keys())}")

    return STAGING_SERVICE_DOMAINS[service_name]


def validate_staging_domain(domain_url: str) -> tuple[bool, str]:
    """
    Validate if a domain URL follows staging domain conventions.

    Args:
        domain_url: The domain URL to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not domain_url:
        return False, "Domain URL cannot be empty"

    # Check against deprecated patterns
    for pattern in INVALID_STAGING_PATTERNS:
        if pattern in domain_url.lower():
            return False, f"Domain contains deprecated pattern '{pattern}'"

    # Check for valid patterns
    domain_lower = domain_url.lower()

    # Must be HTTPS (except WebSocket which uses WSS)
    if not (domain_url.startswith("https://") or domain_url.startswith("wss://")):
        return False, "Staging domains must use HTTPS or WSS protocols"

    # Must contain netrasystems.ai
    if "netrasystems.ai" not in domain_lower:
        return False, "Staging domains must use netrasystems.ai domain"

    # Must use correct format (not *.staging.netrasystems.ai)
    if ".staging.netrasystems.ai" in domain_lower:
        return False, "Use *.netrasystems.ai format instead of *.staging.netrasystems.ai"

    return True, ""


def get_all_staging_domains() -> Dict[str, str]:
    """
    Get all staging domains for comprehensive validation.

    Returns:
        Dict[str, str]: Complete mapping of staging domains
    """
    return STAGING_DOMAINS.copy()


def is_deprecated_staging_domain(domain_url: str) -> bool:
    """
    Check if a domain URL is deprecated and should not be used.

    Args:
        domain_url: The domain URL to check

    Returns:
        bool: True if domain is deprecated
    """
    domain_lower = domain_url.lower()

    # Check old format patterns
    for deprecated in DEPRECATED_STAGING_DOMAINS["OLD_FORMAT"]:
        if deprecated.lower() in domain_lower:
            return True

    # Check cloud run direct patterns
    for deprecated in DEPRECATED_STAGING_DOMAINS["CLOUD_RUN_DIRECT"]:
        if deprecated.lower() in domain_lower:
            return True

    return False


# Legacy compatibility mapping for gradual migration
LEGACY_DOMAIN_MAPPING = {
    # Map old domain patterns to new ones
    "https://app.staging.netrasystems.ai": STAGING_DOMAINS["FRONTEND_URL"],
    "https://api-staging.netrasystems.ai": STAGING_DOMAINS["API_BASE_URL"],
    "https://auth-staging.netrasystems.ai": STAGING_DOMAINS["AUTH_SERVICE_URL"],
    "wss://api-staging.netrasystems.ai": STAGING_DOMAINS["WEBSOCKET_URL"],
    "wss://api-staging.netrasystems.ai": STAGING_DOMAINS["WEBSOCKET_URL"],
}


def migrate_legacy_domain(old_domain: str) -> Optional[str]:
    """
    Migrate a legacy domain to the new format.

    Args:
        old_domain: The legacy domain URL

    Returns:
        Optional[str]: New domain URL if mapping exists, None otherwise
    """
    return LEGACY_DOMAIN_MAPPING.get(old_domain)


# Export Control - Only export what should be used
__all__ = [
    # Core domain constants
    "STAGING_DOMAINS",
    "STAGING_SERVICE_DOMAINS",

    # Access functions
    "get_staging_domain",
    "get_staging_service_domain",
    "get_all_staging_domains",

    # Validation functions
    "validate_staging_domain",
    "is_deprecated_staging_domain",

    # Migration utilities
    "migrate_legacy_domain",
    "LEGACY_DOMAIN_MAPPING",

    # Enums
    "StagingDomainType",
]