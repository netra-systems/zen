"""WebSocket Test Compatibility Mixin.

Provides test compatibility utilities for WebSocket manager.
This module was created to resolve import issues during testing.
"""

from typing import Any, Dict, Optional


class WebSocketTestCompatibilityMixin:
    """Mixin providing test compatibility methods for WebSocket manager."""
    
    def get_test_stats(self) -> Dict[str, Any]:
        """Get test statistics for debugging."""
        return {
            "active_connections": getattr(self, '_connections', {}),
            "test_mode": True,
            "compatibility_version": "1.0.0"
        }
    
    def reset_for_test(self) -> None:
        """Reset manager state for testing."""
        if hasattr(self, '_connections'):
            self._connections.clear()
        if hasattr(self, '_rooms'):
            self._rooms.clear()
    
    def is_test_mode(self) -> bool:
        """Check if running in test mode."""
        return True