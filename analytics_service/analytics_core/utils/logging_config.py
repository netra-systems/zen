"""
DEPRECATED - Backward Compatibility Wrapper for Analytics Logging
SSOT_COMPATIBILITY_WRAPPER = True

This module is DEPRECATED and maintained only for backward compatibility.
NEW CODE SHOULD IMPORT FROM: shared.logging.unified_logging_ssot

SSOT REMEDIATION: Analytics-specific logging is now integrated into the unified 
SSOT logging system, eliminating service-specific configuration fragmentation.

Business Value: Prevents $500K+ ARR Golden Path failures caused by analytics
logging configuration conflicts during SSOT migration process.

Original BVJ maintained through SSOT system:
- Segment: Platform/Internal
- Business Goal: Operational Excellence and Debug Capability  
- Value Impact: Enables effective monitoring and debugging of analytics data flow
- Strategic Impact: Critical for maintaining service reliability and performance visibility
"""

import logging
import sys
import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Union
from pathlib import Path

# Import SSOT logging
from shared.logging.unified_logging_ssot import (
    get_logger as ssot_get_logger,
    get_ssot_logger,
    request_context as ssot_request_context,
    log_performance as ssot_log_performance,
    SensitiveDataFilter as SSOTSensitiveDataFilter,
)

from shared.isolated_environment import get_env

# Issue deprecation warning
warnings.warn(
    "analytics_service.analytics_core.utils.logging_config is deprecated. "
    "Use 'from shared.logging.unified_logging_ssot import get_logger' instead.",
    DeprecationWarning,
    stacklevel=2
)


# DEPRECATED: Import context variables from SSOT
from shared.logging.unified_logging_ssot import (
    request_id_context,
    user_id_context,
    trace_id_context,
    event_type_context,
)


class SensitiveDataFilter:
    """DEPRECATED: Wrapper for SSOT SensitiveDataFilter."""
    
    # Backward compatibility - delegate to SSOT
    SENSITIVE_FIELDS = SSOTSensitiveDataFilter.SENSITIVE_FIELDS
    
    @classmethod
    def filter_sensitive_data(cls, data: Any) -> Any:
        """DEPRECATED: Use shared.logging.unified_logging_ssot.SensitiveDataFilter instead."""
        return SSOTSensitiveDataFilter._filter_recursive(data)


class AnalyticsLogger:
    """DEPRECATED: Wrapper for SSOT logging system - Analytics Service compatibility."""
    
    def __init__(self):
        self._initialized = True  # SSOT handles initialization
        self._ssot_logger = get_ssot_logger()
    
    def get_logger(self, name: Optional[str] = None):
        """DEPRECATED: Get logger from SSOT system."""
        return self._ssot_logger.get_logger(name or 'analytics_service')
    
    @contextmanager
    def request_context(self, request_id: str, user_id: Optional[str] = None, 
                       event_type: Optional[str] = None):
        """DEPRECATED: Use SSOT request context."""
        with ssot_request_context(
            request_id=request_id,
            user_id=user_id,
            event_type=event_type
        ):
            yield


# Global logger instance - delegates to SSOT
analytics_logger = AnalyticsLogger()


def get_logger(name: Optional[str] = None):
    """DEPRECATED: Get logger from SSOT system for Analytics Service."""
    return ssot_get_logger(name or 'analytics_service')


def log_performance(operation: str):
    """DEPRECATED: Use SSOT performance logging decorator."""
    return ssot_log_performance(operation)


# Context manager for request tracing - delegates to SSOT
request_context = analytics_logger.request_context


# Export main interfaces - maintain backward compatibility
__all__ = [
    'get_logger',
    'log_performance', 
    'request_context',
    'analytics_logger',
    'SensitiveDataFilter'
]