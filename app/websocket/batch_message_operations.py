"""
Batch Message Operations

Extracted from batch_message_core.py to maintain 300-line limit.
Handles batch sending, timer management, and message structure creation.
"""

import asyncio
import time
from typing import Dict, List, Any
from app.logging_config import central_logger
from app.websocket.connection import ConnectionInfo
from .batch_message_types import PendingMessage

logger = central_logger.get_logger(__name__)


async def send_batch_to_connection(
    connection_info: ConnectionInfo,
    batch: List[PendingMessage],
    connection_id: str,
    config
) -> None:
    """Send a batch of messages to a connection."""
    if not _validate_batch_not_empty(batch):
        return
    await _process_batch_send(connection_info, batch, connection_id, config)

def _validate_batch_not_empty(batch: List[PendingMessage]) -> bool:
    """Validate that batch is not empty."""
    return bool(batch)


async def _process_batch_send(
    connection_info: ConnectionInfo,
    batch: List[PendingMessage], 
    connection_id: str,
    config
) -> None:
    """Process batch send with error handling."""
    start_time = time.time()
    await _execute_batch_with_error_handling(connection_info, batch, start_time, connection_id, config)

async def _execute_batch_with_error_handling(
    connection_info: ConnectionInfo,
    batch: List[PendingMessage],
    start_time: float,
    connection_id: str,
    config
) -> None:
    """Execute batch with comprehensive error handling."""
    try:
        await _execute_batch_with_metrics(connection_info, batch, start_time, connection_id)
    except Exception as e:
        await _handle_batch_send_error(e, batch, connection_id, config)


async def _execute_batch_with_metrics(
    connection_info: ConnectionInfo,
    batch: List[PendingMessage],
    start_time: float,
    connection_id: str
) -> None:
    """Execute batch send and update metrics."""
    await execute_batch_send(connection_info, batch)
    _update_metrics_and_log(connection_info, batch, start_time, connection_id)

def _update_metrics_and_log(
    connection_info: ConnectionInfo,
    batch: List[PendingMessage],
    start_time: float,
    connection_id: str
) -> None:
    """Update metrics and log successful send."""
    update_connection_metrics(connection_info, batch, start_time)
    log_successful_send(batch, connection_id)


async def _handle_batch_send_error(
    error: Exception,
    batch: List[PendingMessage],
    connection_id: str,
    config
) -> None:
    """Handle error during batch send."""
    _log_batch_error(error, connection_id)
    await handle_send_error(batch, config)

def _log_batch_error(error: Exception, connection_id: str) -> None:
    """Log batch send error."""
    logger.error(f"Error sending batch to {connection_id}: {error}")


async def execute_batch_send(connection_info: ConnectionInfo, batch: List[PendingMessage]) -> None:
    """Execute the actual batch send operation."""
    batched_msg = create_batched_message(batch)
    await connection_info.websocket.send_json(batched_msg)


def update_connection_metrics(connection_info: ConnectionInfo, batch: List[PendingMessage], start_time: float) -> None:
    """Update connection metrics after successful send."""
    connection_info.message_count += len(batch)


def log_successful_send(batch: List[PendingMessage], connection_id: str) -> None:
    """Log successful batch send."""
    logger.debug(f"Sent batch of {len(batch)} messages to {connection_id}")


async def handle_send_error(batch: List[PendingMessage], config) -> None:
    """Handle error during batch send."""
    high_priority_messages = [msg for msg in batch if msg.priority >= config.priority_threshold]
    if high_priority_messages:
        # Note: This would need to be handled by the caller
        pass


def create_batched_message(batch: List[PendingMessage]) -> Dict[str, Any]:
    """Create a batched message structure."""
    sorted_batch = sorted(batch, key=lambda m: m.priority, reverse=True)
    return build_batch_structure(batch, sorted_batch)


def build_batch_structure(original_batch: List[PendingMessage], sorted_batch: List[PendingMessage]) -> Dict[str, Any]:
    """Build the batch message structure."""
    batch_core = _create_batch_core_structure(sorted_batch)
    batch_metadata = _create_batch_timing_metadata(original_batch)
    return {**batch_core, **batch_metadata}


def _create_batch_core_structure(sorted_batch: List[PendingMessage]) -> Dict[str, Any]:
    """Create core batch structure fields."""
    return {
        "type": "batch",
        "batch_id": f"batch_{int(time.time() * 1000)}",
        "messages": [msg.content for msg in sorted_batch],
        "compression": "none"
    }


def _create_batch_timing_metadata(original_batch: List[PendingMessage]) -> Dict[str, Any]:
    """Create batch timing and metadata fields."""
    return {
        "message_count": len(original_batch),
        "timestamp": time.time(),
        "metadata": create_batch_metadata(original_batch)
    }


def create_batch_metadata(batch: List[PendingMessage]) -> Dict[str, Any]:
    """Create metadata for batch message."""
    return {
        "batch_size": len(batch),
        "priority_distribution": get_priority_distribution(batch),
        "total_size_bytes": sum(msg.size_bytes for msg in batch)
    }


def get_priority_distribution(batch: List[PendingMessage]) -> Dict[str, int]:
    """Get priority distribution for batch metadata."""
    distribution = {}
    for msg in batch:
        priority_key = f"priority_{msg.priority}"
        distribution[priority_key] = distribution.get(priority_key, 0) + 1
    return distribution


class BatchTimerManager:
    """Manages batch flush timers."""
    
    def __init__(self):
        self._batch_timers: Dict[str, asyncio.Handle] = {}
    
    def set_flush_timer(self, connection_id: str, delay: float, flush_callback) -> None:
        """Set a timer to flush the batch after max wait time."""
        self.cancel_timer(connection_id)
        self._create_new_timer(connection_id, delay, flush_callback)
    
    def _create_new_timer(self, connection_id: str, delay: float, flush_callback) -> None:
        """Create new flush timer for connection."""
        self.create_timer(connection_id, delay, flush_callback)
    
    def cancel_timer(self, connection_id: str) -> None:
        """Cancel existing timer for connection."""
        if connection_id in self._batch_timers:
            self._batch_timers[connection_id].cancel()
    
    def create_timer(self, connection_id: str, delay: float, flush_callback) -> None:
        """Create new flush timer for connection."""
        loop = asyncio.get_event_loop()
        timer_callback = self._create_timer_callback(flush_callback, connection_id)
        self._batch_timers[connection_id] = loop.call_later(delay, timer_callback)
    
    def _create_timer_callback(self, flush_callback, connection_id: str):
        """Create timer callback function."""
        return lambda: asyncio.create_task(flush_callback(connection_id))
    
    def cleanup_timer(self, connection_id: str) -> None:
        """Clean up batch timer for connection."""
        if connection_id in self._batch_timers:
            self._cancel_and_remove_timer(connection_id)
    
    def _cancel_and_remove_timer(self, connection_id: str) -> None:
        """Cancel timer and remove from registry."""
        self._batch_timers[connection_id].cancel()
        del self._batch_timers[connection_id]
    
    def cancel_all_timers(self) -> None:
        """Cancel all active batch timers."""
        self._cancel_existing_timers()
        self._clear_timer_registry()
    
    def _cancel_existing_timers(self) -> None:
        """Cancel all existing timers."""
        for timer in self._batch_timers.values():
            timer.cancel()
    
    def _clear_timer_registry(self) -> None:
        """Clear the timer registry."""
        self._batch_timers.clear()
    
    def get_active_timer_count(self) -> int:
        """Get count of active timers."""
        return len(self._batch_timers)