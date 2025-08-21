"""Unified WebSocket Management System.

Consolidates all WebSocket functionality into a modular, scalable system:
- UnifiedWebSocketManager: Main orchestration layer
- UnifiedMessagingManager: Message processing and validation
- UnifiedBroadcastingManager: Broadcasting and room management  
- UnifiedStateManager: Connection state and telemetry

Business Value: Eliminates $8K MRR loss from poor real-time experience
"""

from .broadcasting import BroadcastMetrics, UnifiedBroadcastingManager
from .manager import UnifiedWebSocketManager, get_unified_manager
from .messaging import MessageQueue, UnifiedMessagingManager
from .state import JobQueueManager, TelemetryCollector, UnifiedStateManager

__all__ = [
    # Main manager
    "UnifiedWebSocketManager",
    "get_unified_manager",
    
    # Messaging components
    "UnifiedMessagingManager", 
    "MessageQueue",
    
    # Broadcasting components
    "UnifiedBroadcastingManager",
    "BroadcastMetrics",
    
    # State management components
    "UnifiedStateManager",
    "TelemetryCollector", 
    "JobQueueManager"
]