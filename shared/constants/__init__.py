"""
Shared Constants Package - SSOT for Platform Constants

This package provides centralized constants used across the Netra Apex platform.
All constants should be defined here to maintain Single Source of Truth (SSOT).

Key Modules:
- service_identifiers: Service identification constants (SERVICE_ID, etc.)
- staging_domains: Staging domain configuration (STAGING_DOMAINS, etc.)

Business Value: Platform/Critical - Centralizes constants to prevent
configuration drift and inconsistencies that cause system failures.
"""

# Import key constants for easy access
from .service_identifiers import SERVICE_ID, SERVICE_IDENTIFIERS, VALID_SERVICE_IDS
from .staging_domains import (
    STAGING_DOMAINS,
    STAGING_SERVICE_DOMAINS,
    get_staging_domain,
    get_staging_service_domain,
    validate_staging_domain,
    is_deprecated_staging_domain,
)

__all__ = [
    # Service identifiers
    "SERVICE_ID",
    "SERVICE_IDENTIFIERS",
    "VALID_SERVICE_IDS",

    # Staging domains
    "STAGING_DOMAINS",
    "STAGING_SERVICE_DOMAINS",
    "get_staging_domain",
    "get_staging_service_domain",
    "validate_staging_domain",
    "is_deprecated_staging_domain",
]