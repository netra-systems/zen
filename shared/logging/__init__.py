"""
Shared logging module providing unified logging across all services.

This module eliminates duplicate logging patterns by providing a single
factory for all logger initialization needs.
"""

from shared.logging.unified_logging_ssot import get_logger
try:
    from shared.logging.unified_logger_factory import (
        configure_service_logging,
        reset_logging,
        UnifiedLoggerFactory
    )
except ImportError:
    # Fallback for missing functions
    configure_service_logging = None
    reset_logging = None
    UnifiedLoggerFactory = None

__all__ = [
    'get_logger',
    'configure_service_logging', 
    'reset_logging',
    'UnifiedLoggerFactory'
]