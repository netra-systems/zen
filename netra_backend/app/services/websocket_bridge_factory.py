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
from dataclasses import dataclass
import logging
import os

if TYPE_CHECKING:
    from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

logger = logging.getLogger(__name__)

@dataclass
class WebSocketFactoryConfig:
    """Configuration for WebSocketBridgeFactory."""
    max_events_per_user: int = 1000
    event_timeout_seconds: float = 30.0
    heartbeat_interval_seconds: float = 30.0
    max_reconnect_attempts: int = 3
    delivery_retries: int = 3
    delivery_timeout_seconds: float = 5.0
    enable_event_compression: bool = True
    enable_event_batching: bool = True
    
    @classmethod
    def from_env(cls) -> 'WebSocketFactoryConfig':
        """Create config from environment variables."""
        return cls(
            max_events_per_user=int(os.getenv('WEBSOCKET_MAX_EVENTS_PER_USER', 1000)),
            event_timeout_seconds=float(os.getenv('WEBSOCKET_EVENT_TIMEOUT', 30.0)),
            heartbeat_interval_seconds=float(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', 30.0)),
            max_reconnect_attempts=int(os.getenv('WEBSOCKET_MAX_RECONNECT_ATTEMPTS', 3)),
            delivery_retries=int(os.getenv('WEBSOCKET_DELIVERY_RETRIES', 3)),
            delivery_timeout_seconds=float(os.getenv('WEBSOCKET_DELIVERY_TIMEOUT', 5.0)),
            enable_event_compression=os.getenv('WEBSOCKET_ENABLE_COMPRESSION', 'true').lower() == 'true',
            enable_event_batching=os.getenv('WEBSOCKET_ENABLE_BATCHING', 'true').lower() == 'true',
        )

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