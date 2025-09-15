"""
Shared logging module providing unified logging across all services.

This module eliminates duplicate logging patterns by providing a single
factory for all logger initialization needs.
"""

from shared.logging.unified_logging_ssot import (
    get_logger,
    get_ssot_logger,
    log_performance,
    request_context,
    reset_logging
)
# Import configure_service_logging from SSOT for compatibility
def configure_service_logging(service_config=None):
    """DEPRECATED: Use SSOT logging system - configuration is automatic."""
    pass

__all__ = [
    'get_logger',
    'get_ssot_logger',
    'log_performance',
    'request_context',
    'reset_logging',
    'configure_service_logging'
]