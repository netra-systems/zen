"""SSOT CONSOLIDATION: WebSocketBridgeFactory wrapper classes → UnifiedWebSocketEmitter

This module provides backward compatibility by aliasing wrapper classes
to the SSOT UnifiedWebSocketEmitter implementation.

Business Value Justification:
- Segment: Platform/Internal (SSOT Migration)
- Business Goal: System Reliability & Code Consolidation  
- Value Impact: Eliminates duplicate WebSocket emitter implementations
- Strategic Impact: Single Source of Truth for all WebSocket functionality

## SSOT STATUS: COMPLETED
- All wrapper classes now alias to UnifiedWebSocketEmitter
- Full backward compatibility maintained
- Enhanced performance from SSOT implementation
- Consolidated error handling and event delivery

MIGRATION COMPLETE: All consumers should now import UnifiedWebSocketEmitter directly.
"""

# Import necessary dependencies for backward compatibility
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from typing import Dict, Any, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

logger = logging.getLogger(__name__)

# SSOT CONSOLIDATION: Backward compatibility aliases
UserWebSocketEmitter = UnifiedWebSocketEmitter

class WebSocketBridgeFactory:
    """Factory for creating WebSocket bridges and emitters (SSOT-compatible)."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
    
    async def create_user_emitter(self, user_id: str, context: UserExecutionContext) -> UnifiedWebSocketEmitter:
        """Create UnifiedWebSocketEmitter for user (SSOT implementation)."""
        return UnifiedWebSocketEmitter(
            manager=self.websocket_manager,
            user_id=user_id,
            context=context
        )
    
    async def create_bridge(self, user_id: str, context: UserExecutionContext) -> AgentWebSocketBridge:
        """Create AgentWebSocketBridge for user."""
        return AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_id=user_id,
            context=context
        )