"""WebSocket Message Batching System.

Main entry point for message batching functionality.
"""

# Re-export key components for backward compatibility
from netra_backend.app.websocket.batch_message_batch import MessageBatch
from netra_backend.app.websocket.batch_message_config import (
    BatchConfig,
    BatchedMessage,
    BatchMetrics,
    BatchStrategy,
)
from netra_backend.app.websocket.batch_message_manager import WebSocketMessageBatcher

__all__ = [
    "BatchStrategy",
    "BatchConfig", 
    "BatchedMessage",
    "BatchMetrics",
    "MessageBatch",
    "WebSocketMessageBatcher"
]