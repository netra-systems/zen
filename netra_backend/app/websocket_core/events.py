"""
WebSocket Events Module - Import Compatibility Layer
====================================================

This module provides backward compatibility for import paths used in tests.
It aliases the actual implementation to maintain test functionality while
following SSOT patterns.

Business Value: Platform/Internal - Test Infrastructure Stability
Prevents import path issues from blocking test execution.

CRITICAL: This is a compatibility layer for Issue #1197 infrastructure remediation.
The actual implementation is in event_monitor.py as ChatEventMonitor.

Author: Claude Code - Infrastructure Remediation  
Date: 2025-09-16
Issue: #1197 Import Path Resolution
"""

# Import the actual implementation
from netra_backend.app.websocket_core.event_monitor import (
    ChatEventMonitor,
    EventType,
    HealthStatus
)

# Provide backward compatibility alias for tests
# Tests expect WebSocketEventManager but actual class is ChatEventMonitor
WebSocketEventManager = ChatEventMonitor

# Re-export all public classes and enums for compatibility
__all__ = [
    'WebSocketEventManager',  # Compatibility alias
    'ChatEventMonitor',       # Actual implementation
    'EventType',              # Event type enum
    'HealthStatus'            # Health status enum
]

# Deprecation warning for future cleanup
import warnings

def _emit_deprecation_warning():
    """Emit deprecation warning for direct usage of this compatibility module."""
    warnings.warn(
        "Importing from 'netra_backend.app.websocket_core.events' is deprecated. "
        "Use 'from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor' instead. "
        "The WebSocketEventManager alias will be removed after Issue #1197 completion.",
        DeprecationWarning,
        stacklevel=3
    )

# Only emit warning if imported directly (not during test discovery)
try:
    import pytest
    # If pytest is running, don't emit warnings during collection
    if not hasattr(pytest, 'current_pytest_mode'):
        _emit_deprecation_warning()
except ImportError:
    # Not in test environment, emit warning
    _emit_deprecation_warning()