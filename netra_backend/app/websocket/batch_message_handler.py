"""WebSocket Message Batching - Modular Implementation.

Backward-compatible interface using optimized micro-function modules.
"""

# Import from modular implementation for backward compatibility
from netra_backend.app.batch_broadcast_manager import BatchedBroadcastManager
from netra_backend.app.batch_load_monitor import LoadMonitor
from netra_backend.app.batch_message_core import MessageBatcher
from netra_backend.app.batch_message_types import (
    BatchConfig,
    BatchingStrategy,
    BatchMetrics,
    PendingMessage,
)

# Maintain backward compatibility by exposing all classes at module level
__all__ = [
    'BatchingStrategy', 'BatchConfig', 'PendingMessage', 'BatchMetrics',
    'MessageBatcher', 'LoadMonitor', 'BatchedBroadcastManager'
]