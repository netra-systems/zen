"""Database Retry Handler Module - Compatibility Layer

This module provides backward compatibility for database retry handling.
Aliases existing retry functionality from core and services modules.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from netra_backend.app.services.error_handling.retry_handler import RetryHandler

# Create alias for backward compatibility
DatabaseRetryHandler = UnifiedRetryHandler

# Re-export all functionality
__all__ = [
    'DatabaseRetryHandler',
    'UnifiedRetryHandler',
    'RetryHandler'
]