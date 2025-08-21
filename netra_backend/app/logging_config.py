"""Unified logging configuration for Netra backend.

This module provides a single, consistent logging interface that:
- Filters sensitive data automatically
- Adds request/trace context
- Provides performance monitoring
- Supports structured logging
- Prevents circular dependencies
"""

# Import the unified logger and context variables
from netra_backend.app.core.logging_context import (
    request_id_context,
    trace_id_context,
    user_id_context,
)
from netra_backend.app.core.unified_logging import (
    UnifiedLogger,
    central_logger,
    get_central_logger,
    log_execution_time,
)

# Create alias for backward compatibility
CentralLogger = UnifiedLogger

# Re-export for backward compatibility
__all__ = [
    'central_logger',
    'get_central_logger',
    'log_execution_time',
    'request_id_context',
    'user_id_context',
    'trace_id_context',
    'CentralLogger',
    'UnifiedLogger',
]