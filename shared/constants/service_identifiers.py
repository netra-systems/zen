"""
SSOT Service Identifiers - Single Source of Truth for Service Constants

This module provides the centralized constants for service identification
across the Netra Apex platform. This is the SINGLE SOURCE OF TRUTH for
all service identifier values.

Business Value: Platform/Critical - Ensures consistent service identification
preventing authentication failures that affect $500K+ ARR.

CRITICAL: This constant MUST be imported by all services requiring SERVICE_ID.
No hardcoded service identifier strings should exist elsewhere in the codebase.

Usage:
    from shared.constants.service_identifiers import SERVICE_ID
    
    # Use in authentication headers
    headers = {"X-Service-ID": SERVICE_ID}
    
    # Use in service validation
    if received_service_id == SERVICE_ID:
        # Validation logic
"""

# SSOT: Single Source of Truth for Service Identifiers
# This is the ONLY place where service identifiers should be defined

# Backend Service Identifier
# Used for cross-service authentication and identification
SERVICE_ID = "netra-backend"

# Service Metadata
SERVICE_IDENTIFIERS = {
    "backend": SERVICE_ID,
    "primary_service": SERVICE_ID,
    "auth_service_expected": SERVICE_ID
}

# Validation Constants
VALID_SERVICE_IDS = {SERVICE_ID}

# Export Control - Only export what should be used
__all__ = [
    "SERVICE_ID",
    "SERVICE_IDENTIFIERS", 
    "VALID_SERVICE_IDS"
]