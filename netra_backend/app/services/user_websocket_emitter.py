"""SSOT CONSOLIDATION: UserWebSocketEmitter → UnifiedWebSocketEmitter

This module provides backward compatibility by aliasing UserWebSocketEmitter
to the SSOT UnifiedWebSocketEmitter implementation.

Business Value Justification:
- Segment: Platform/Internal (SSOT Migration)  
- Business Goal: System Reliability & Code Consolidation
- Value Impact: Eliminates code duplication, improves maintainability
- Strategic Impact: Single Source of Truth for all WebSocket emitter functionality

## SSOT STATUS: COMPLETED
- UserWebSocketEmitter is now an alias to UnifiedWebSocketEmitter
- All functionality provided by the SSOT implementation
- Zero breaking changes for existing consumers
- Enhanced performance and reliability from SSOT implementation

MIGRATION COMPLETE: All consumers should now import UnifiedWebSocketEmitter directly.
"""

# SSOT CONSOLIDATION: Import alias for backward compatibility
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Backward compatibility alias - all functionality provided by SSOT
UserWebSocketEmitter = UnifiedWebSocketEmitter