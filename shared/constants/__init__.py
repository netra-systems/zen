"""
Shared Constants Package - SSOT for Platform Constants

This package provides centralized constants used across the Netra Apex platform.
All constants should be defined here to maintain Single Source of Truth (SSOT).

Key Modules:
- service_identifiers: Service identification constants (SERVICE_ID, etc.)

Business Value: Platform/Critical - Centralizes constants to prevent
configuration drift and inconsistencies that cause system failures.
"""

# Import key constants for easy access
from .service_identifiers import SERVICE_ID, SERVICE_IDENTIFIERS, VALID_SERVICE_IDS

__all__ = [
    "SERVICE_ID",
    "SERVICE_IDENTIFIERS", 
    "VALID_SERVICE_IDS"
]