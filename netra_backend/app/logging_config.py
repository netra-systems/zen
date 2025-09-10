"""
DEPRECATED - Backward Compatibility Wrapper for SSOT Logging
SSOT_COMPATIBILITY_WRAPPER = True

This module is DEPRECATED and maintained only for backward compatibility.
NEW CODE SHOULD IMPORT FROM: shared.logging.unified_logging_ssot

SSOT REMEDIATION: This wrapper routes all calls to the unified SSOT logging system,
eliminating logging fragmentation while maintaining compatibility.

Business Value: Prevents $500K+ ARR Golden Path debugging failures caused by
logging inconsistencies during the SSOT migration process.
"""

import warnings

# Import from SSOT module
from shared.logging.unified_logging_ssot import (
    get_logger as ssot_get_logger,
    get_ssot_logger,
    log_performance as ssot_log_performance,
    request_context as ssot_request_context,
)

# Issue deprecation warning
warnings.warn(
    "netra_backend.app.logging_config is deprecated. "
    "Use 'from shared.logging.unified_logging_ssot import get_logger' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Get SSOT logger instance for compatibility
_ssot_instance = get_ssot_logger()

# Backward compatibility aliases
central_logger = _ssot_instance
CentralLogger = type(_ssot_instance)
UnifiedLogger = type(_ssot_instance)

# Backward compatibility functions
def get_central_logger():
    """DEPRECATED: Use shared.logging.unified_logging_ssot.get_logger instead."""
    return _ssot_instance

def get_logger(name=None):
    """DEPRECATED: Use shared.logging.unified_logging_ssot.get_logger instead."""
    return ssot_get_logger(name)

def log_execution_time(operation_name=None):
    """DEPRECATED: Use shared.logging.unified_logging_ssot.log_performance instead."""
    return ssot_log_performance(operation_name or "unknown_operation")

# Context variables for backward compatibility
from shared.logging.unified_logging_ssot import (
    request_id_context,
    user_id_context,
    trace_id_context,
)

# Re-export for backward compatibility
__all__ = [
    'central_logger',
    'get_central_logger', 
    'get_logger',
    'log_execution_time',
    'request_id_context',
    'user_id_context',
    'trace_id_context',
    'CentralLogger',
    'UnifiedLogger',
]