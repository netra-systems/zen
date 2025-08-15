"""WebSocket Message Batching - Modular Implementation.

Backward-compatible interface using optimized micro-function modules.
"""

# Import from modular implementation for backward compatibility
from .batch_message_types import (
    BatchingStrategy, BatchConfig, PendingMessage, BatchMetrics
)
from .batch_message_core import MessageBatcher
from .batch_load_monitor import LoadMonitor
from .batch_broadcast_manager import BatchedBroadcastManager

# Maintain backward compatibility by exposing all classes at module level
__all__ = [
    'BatchingStrategy', 'BatchConfig', 'PendingMessage', 'BatchMetrics',
    'MessageBatcher', 'LoadMonitor', 'BatchedBroadcastManager'
]