"""Unified WebSocket Management System.

Consolidates all WebSocket functionality into a modular, scalable system:
- UnifiedWebSocketManager: Main orchestration layer
- UnifiedMessagingManager: Message processing and validation
- UnifiedBroadcastingManager: Broadcasting and room management  
- UnifiedStateManager: Connection state and telemetry

Business Value: Eliminates $8K MRR loss from poor real-time experience
"""

from netra_backend.app.manager import UnifiedWebSocketManager, get_unified_manager
from netra_backend.app.messaging import UnifiedMessagingManager, MessageQueue
from netra_backend.app.broadcasting import UnifiedBroadcastingManager, BroadcastMetrics
from netra_backend.app.state import UnifiedStateManager, TelemetryCollector, JobQueueManager

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