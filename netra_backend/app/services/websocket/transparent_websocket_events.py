"""Transparent WebSocket Events - SSOT Redirection to UnifiedWebSocketEmitter

SSOT CONSOLIDATION: This module now redirects all WebSocket event emissions
to the UnifiedWebSocketEmitter to eliminate race conditions and multiple emission sources.

Business Value Justification:
- Segment: Platform/Internal - Infrastructure Consolidation
- Business Goal: Eliminate race conditions, improve reliability 
- Value Impact: Single source of truth prevents event duplication and race conditions
- Revenue Impact: Protects $500K+ ARR by ensuring reliable chat functionality

Previous functionality:
- Transparent service status communication
- Real-time visibility into service status, initialization progress, degraded mode operations

CRITICAL: All actual WebSocket emissions now happen through UnifiedWebSocketEmitter only.
This eliminates the "transparent_emitter" source detected in tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventType(Enum):
    """WebSocket event types for transparent service communication."""
    # Original agent events (preserved for chat UX)
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"  
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    
    # New transparent service events
    SERVICE_INITIALIZING = "service_initializing"
    SERVICE_READY = "service_ready"
    SERVICE_DEGRADED = "service_degraded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    SERVICE_RECOVERED = "service_recovered"
    
    # System status events
    SYSTEM_STATUS = "system_status"
    USER_QUEUE_POSITION = "user_queue_position"
    ESTIMATED_WAIT_TIME = "estimated_wait_time"


# SSOT REDIRECTION: Import UnifiedWebSocketEmitter as the ONLY implementation
# This eliminates the duplicate emission source and ensures all calls go through unified_emitter.py
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as TransparentWebSocketEmitter

# SSOT REDIRECTION: Import WebSocketEmitterFactory for backward compatibility
from netra_backend.app.websocket_core.unified_emitter import WebSocketEmitterFactory

# SSOT REDIRECTION: Import enum aliases for backward compatibility
TransparentWebSocketEvents = TransparentWebSocketEmitter  # Alias for class name compatibility

# SSOT REDIRECTION: Create factory function for backward compatibility
async def create_transparent_emitter(context: 'UserExecutionContext') -> TransparentWebSocketEmitter:
    """
    SSOT Factory: Create transparent emitter using unified SSOT implementation.
    
    This factory function maintains backward compatibility while ensuring
    all emissions go through the unified emitter.
    
    Args:
        context: User execution context
        
    Returns:
        UnifiedWebSocketEmitter instance (aliased as TransparentWebSocketEmitter)
    """
    from netra_backend.app.websocket_core import create_websocket_manager
    
    # Get or create WebSocket manager
    manager = getattr(context, 'websocket_manager', None)
    if not manager:
        manager = await create_websocket_manager()
    
    # Create unified emitter with context
    emitter = WebSocketEmitterFactory.create_emitter(
        manager=manager,
        user_id=context.user_id,
        context=context
    )
    
    # Set user tier if available
    if hasattr(context, 'user_tier'):
        emitter.set_user_tier(context.user_tier)
    
    logger.info(f"SSOT transparent emitter created for user {context.user_id}")
    return emitter


# BACKWARD COMPATIBILITY: Keep the TransparentWebSocketEvents class name working
# Any imports of "TransparentWebSocketEvents" will get the unified emitter
__all__ = [
    'WebSocketEventType',
    'TransparentWebSocketEmitter', 
    'TransparentWebSocketEvents',
    'WebSocketEmitterFactory',
    'create_transparent_emitter'
]

# SSOT CONSOLIDATION COMPLETE: This module no longer contains duplicate emission logic.
# All WebSocket events now flow through unified_emitter.py only.