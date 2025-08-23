"""
Unified WebSocket Manager - Central Export Point

This file provides backward compatibility and a central import point for the 
UnifiedWebSocketManager. It exports the proper modular implementation from 
the unified package.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability & Development Velocity  
- Value Impact: Fixes critical import errors, prevents system downtime
- Strategic Impact: Provides clean architecture, reduces technical debt

CRITICAL FIX: This file resolves the multiple UnifiedWebSocketManager 
implementations by providing a single source of truth.
"""

# Import the correct modular implementation
from netra_backend.app.websocket.unified.manager import (
    UnifiedWebSocketManager,
    get_unified_manager
)

# Export for backward compatibility
__all__ = [
    'UnifiedWebSocketManager',
    'get_unified_manager'
]

# Legacy compatibility - ensure we're using the singleton pattern correctly
def get_websocket_manager() -> UnifiedWebSocketManager:
    """Get the unified WebSocket manager instance - legacy compatibility."""
    return get_unified_manager()

# For tests and other modules that need a fresh instance
def create_websocket_manager() -> UnifiedWebSocketManager:
    """Create a new WebSocket manager instance - primarily for testing."""
    return UnifiedWebSocketManager.create_test_instance()