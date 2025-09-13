"""
SSOT Redirect: UserWebSocketEmitter -> UnifiedWebSocketEmitter

Issue #765: WebSocket Processing SSOT Consolidation
- This file provides backward compatibility by redirecting imports
- UnifiedWebSocketEmitter is the SSOT implementation
- Maintains Golden Path functionality while consolidating implementations

Business Impact: Protects $500K+ ARR WebSocket functionality
"""

from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# SSOT Redirect: Alias for backward compatibility
UserWebSocketEmitter = UnifiedWebSocketEmitter

__all__ = ['UserWebSocketEmitter']