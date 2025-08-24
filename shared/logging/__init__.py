"""
Shared logging module providing unified logging across all services.

This module eliminates duplicate logging patterns by providing a single
factory for all logger initialization needs.
"""

from .unified_logger_factory import (
    get_logger,
    configure_service_logging,
    reset_logging,
    UnifiedLoggerFactory
)

__all__ = [
    'get_logger',
    'configure_service_logging', 
    'reset_logging',
    'UnifiedLoggerFactory'
]