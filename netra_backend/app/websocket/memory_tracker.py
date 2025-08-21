"""WebSocket Connection Memory Tracker.

Tracks memory usage per connection with buffer limits.
"""

import sys
import weakref
from typing import Any, Dict, List, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class ConnectionMemoryTracker:
    """Tracks memory usage per connection."""
    
    def __init__(self):
        self.connection_refs: weakref.WeakSet[ConnectionInfo] = weakref.WeakSet()
        self.message_buffers: Dict[str, List[Any]] = {}
        self.buffer_sizes: Dict[str, float] = {}  # Cache buffer sizes
        self.buffer_limits = self._init_buffer_limits()
    
    def _init_buffer_limits(self) -> Dict[str, float]:
        """Initialize buffer limit configuration."""
        return {
            "max_messages_per_connection": 1000,
            "max_buffer_size_mb": 10.0,
            "max_connection_age_hours": 24
        }

    def track_connection(self, conn_info: ConnectionInfo) -> None:
        """Track connection memory usage."""
        self.connection_refs.add(conn_info)
        self.message_buffers[conn_info.connection_id] = []
        self.buffer_sizes[conn_info.connection_id] = 0.0
        logger.debug(f"Started tracking memory for connection {conn_info.connection_id}")
    
    def untrack_connection(self, connection_id: str) -> None:
        """Stop tracking connection and cleanup buffers."""
        self.message_buffers.pop(connection_id, None)
        self.buffer_sizes.pop(connection_id, None)
        logger.debug(f"Stopped tracking memory for connection {connection_id}")
    
    def add_message_to_buffer(self, connection_id: str, message: Any) -> bool:
        """Add message to connection buffer with size limits."""
        if not self._validate_connection_exists(connection_id):
            return False
        buffer = self.message_buffers[connection_id]
        message_size = self._calculate_message_size(message)
        self._enforce_message_count_limit(connection_id, buffer)
        self._add_message_and_update_size(connection_id, buffer, message, message_size)
        return True
    
    def _validate_connection_exists(self, connection_id: str) -> bool:
        """Validate that connection exists in tracked buffers."""
        return connection_id in self.message_buffers
    
    def _calculate_message_size(self, message: Any) -> float:
        """Calculate message size in MB."""
        return sys.getsizeof(message) / (1024 * 1024)
    
    def _enforce_message_count_limit(self, connection_id: str, buffer: List[Any]) -> None:
        """Enforce message count limit by removing oldest if needed."""
        if len(buffer) >= self.buffer_limits["max_messages_per_connection"]:
            removed_msg = buffer.pop(0)
            self.buffer_sizes[connection_id] -= sys.getsizeof(removed_msg) / (1024 * 1024)
    
    def _add_message_and_update_size(self, connection_id: str, buffer: List[Any], message: Any, message_size: float) -> None:
        """Add message and update buffer size, checking limits."""
        buffer.append(message)
        self.buffer_sizes[connection_id] += message_size
        
        if self.buffer_sizes[connection_id] > self.buffer_limits["max_buffer_size_mb"]:
            self._reduce_buffer_size(connection_id)
    
    def _reduce_buffer_size(self, connection_id: str) -> None:
        """Reduce buffer size efficiently when over limit."""
        buffer = self.message_buffers[connection_id]
        target_size = len(buffer) // 2
        self._remove_half_messages(buffer, target_size)
        self._recalculate_buffer_size(connection_id, buffer)
        logger.warning(f"Reduced buffer size for {connection_id} to {len(buffer)} messages")
    
    def _remove_half_messages(self, buffer: List[Any], target_size: int) -> None:
        """Remove first half of messages from buffer."""
        buffer[:] = buffer[target_size:]
    
    def _recalculate_buffer_size(self, connection_id: str, buffer: List[Any]) -> None:
        """Recalculate cached buffer size after bulk removal."""
        self.buffer_sizes[connection_id] = sum(sys.getsizeof(msg) for msg in buffer) / (1024 * 1024)
    
    def get_connection_memory_info(self, connection_id: str) -> Dict[str, Any]:
        """Get memory information for a specific connection."""
        buffer = self.message_buffers.get(connection_id, [])
        buffer_size_mb = self.buffer_sizes.get(connection_id, 0.0)
        return self._build_connection_info_dict(connection_id, buffer, buffer_size_mb)
    
    def _build_connection_info_dict(self, connection_id: str, buffer: List[Any], buffer_size_mb: float) -> Dict[str, Any]:
        """Build connection memory information dictionary."""
        return {
            "connection_id": connection_id,
            "message_count": len(buffer),
            "buffer_size_mb": buffer_size_mb,
            "is_tracked": connection_id in self.message_buffers
        }