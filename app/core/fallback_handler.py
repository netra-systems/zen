"""
Context-Aware Fallback Handler for AI Slop Prevention
Compatibility wrapper for refactored fallback handling module
"""

from app.core.fallback import (
    FallbackHandler,
    FallbackContext,
    FallbackMetadata
)

__all__ = [
    'FallbackHandler',
    'FallbackContext',
    'FallbackMetadata'
]