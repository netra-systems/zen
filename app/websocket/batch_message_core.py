"""WebSocket Message Batcher Core.

Core message batching functionality with micro-functions.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union

from app.logging_config import central_logger
from app.schemas.websocket_message_types import ServerMessage
from app.websocket.connection import ConnectionInfo, ConnectionManager

from .batch_message_types import BatchConfig, PendingMessage, BatchMetrics
from .batch_message_strategies import BatchingStrategyManager
from .batch_load_monitor import LoadMonitor
from .batch_message_operations import (
    send_batch_to_connection, BatchTimerManager, create_batched_message
)

logger = central_logger.get_logger(__name__)


class MessageBatcher:
    """Efficient WebSocket message batching system with micro-functions."""
    
    def __init__(self, config: BatchConfig, connection_manager: ConnectionManager):
        self.config = config
        self.connection_manager = connection_manager
        self._init_batcher_state()
        self._init_strategy_manager()
    
    def _init_batcher_state(self) -> None:
        """Initialize batcher state variables."""
        self._pending_messages: Dict[str, List[PendingMessage]] = {}
        self._timer_manager = BatchTimerManager()
        self._metrics = BatchMetrics()
        self._lock = asyncio.Lock()
        self._shutdown = False
    
    def _init_strategy_manager(self) -> None:
        """Initialize strategy manager and load monitor."""
        self._load_monitor = LoadMonitor()
        self._strategy_manager = BatchingStrategyManager(self.config, self._load_monitor)
    
    async def queue_message(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                           priority: int = 1, connection_id: Optional[str] = None) -> bool:
        """Queue a message for batched delivery."""
        if self._shutdown:
            return False
        
        async with self._lock:
            connections = self.connection_manager.get_user_connections(user_id)
            if not connections:
                self._log_no_connections(user_id)
                return False
            
            target_connections = self._get_target_connections(connection_id, connections)
            await self._queue_to_connections(message, user_id, priority, target_connections)
            return True
    
    def _log_no_connections(self, user_id: str) -> None:
        """Log when no connections exist for user."""
        logger.debug(f"No connections for user {user_id}, dropping message")
    
    def _get_target_connections(self, connection_id: Optional[str], connections: List[ConnectionInfo]) -> List[str]:
        """Get target connection IDs for message."""
        if connection_id:
            return [connection_id]
        return [conn.connection_id for conn in connections]
    
    async def _queue_to_connections(self, message: Union[Dict[str, Any], ServerMessage], 
                                   user_id: str, priority: int, target_connections: List[str]) -> None:
        """Queue message to target connections."""
        for conn_id in target_connections:
            pending_msg = self._create_pending_message(message, conn_id, user_id, priority)
            self._add_to_pending_queue(conn_id, pending_msg)
            await self._check_flush_conditions(conn_id)
    
    def _create_pending_message(self, message: Union[Dict[str, Any], ServerMessage], 
                               conn_id: str, user_id: str, priority: int) -> PendingMessage:
        """Create pending message instance."""
        return PendingMessage(
            content=message,
            connection_id=conn_id,
            user_id=user_id,
            priority=priority
        )
    
    def _add_to_pending_queue(self, conn_id: str, pending_msg: PendingMessage) -> None:
        """Add message to pending queue for connection."""
        if conn_id not in self._pending_messages:
            self._pending_messages[conn_id] = []
        self._pending_messages[conn_id].append(pending_msg)
    
    async def _check_flush_conditions(self, connection_id: str) -> None:
        """Check if batch should be flushed based on strategy."""
        if connection_id not in self._pending_messages:
            return
        
        pending = self._pending_messages[connection_id]
        should_flush = self._strategy_manager.should_flush_batch(pending)
        
        if should_flush:
            await self._flush_batch(connection_id)
        else:
            await self._set_flush_timer(connection_id)
    
    async def _set_flush_timer(self, connection_id: str) -> None:
        """Set a timer to flush the batch after max wait time."""
        self._timer_manager.set_flush_timer(connection_id, self.config.max_wait_time, self._flush_batch)
    
    
    
    async def _flush_batch(self, connection_id: str) -> None:
        """Flush pending messages for a connection."""
        async with self._lock:
            batch = self._extract_pending_batch(connection_id)
            if not batch:
                return
        
        await self._send_batch(connection_id, batch)
    
    def _extract_pending_batch(self, connection_id: str) -> List[PendingMessage]:
        """Extract pending batch and clear queue."""
        if connection_id not in self._pending_messages or not self._pending_messages[connection_id]:
            return []
        
        batch = self._pending_messages[connection_id].copy()
        self._pending_messages[connection_id].clear()
        self._cleanup_timer(connection_id)
        return batch
    
    def _cleanup_timer(self, connection_id: str) -> None:
        """Clean up batch timer for connection."""
        self._timer_manager.cleanup_timer(connection_id)
    
    async def _send_batch(self, connection_id: str, batch: List[PendingMessage]) -> None:
        """Send a batch of messages to a connection."""
        if not batch:
            return
        
        connection_info = self.connection_manager.get_connection_by_id(connection_id)
        if not connection_info:
            self._log_connection_not_found(connection_id)
            return
        
        await send_batch_to_connection(connection_info, batch, connection_id, self.config)
        self._update_send_metrics(batch)
    
    def _log_connection_not_found(self, connection_id: str) -> None:
        """Log when connection is not found."""
        logger.debug(f"Connection {connection_id} no longer exists")
    
    
    
    def _update_send_metrics(self, batch: List[PendingMessage]) -> None:
        """Update metrics after successful send."""
        self._update_metrics(len(batch), 0.0)
    
    
    
    
    
    
    
    async def _requeue_messages(self, messages: List[PendingMessage]) -> None:
        """Re-queue messages that failed to send."""
        async with self._lock:
            for msg in messages:
                self._requeue_single_message(msg)
    
    def _requeue_single_message(self, msg: PendingMessage) -> None:
        """Re-queue single message at front of queue."""
        if msg.connection_id not in self._pending_messages:
            self._pending_messages[msg.connection_id] = []
        self._pending_messages[msg.connection_id].insert(0, msg)
    
    def _update_metrics(self, batch_size: int, wait_time: float) -> None:
        """Update batching metrics."""
        self._update_basic_metrics(batch_size)
        self._update_advanced_metrics(wait_time)
    
    def _update_basic_metrics(self, batch_size: int) -> None:
        """Update basic batch metrics."""
        self._metrics.total_batches += 1
        self._metrics.total_messages += batch_size
        self._metrics.avg_batch_size = self._metrics.total_messages / self._metrics.total_batches
    
    def _update_advanced_metrics(self, wait_time: float) -> None:
        """Update advanced metrics with moving averages."""
        alpha = 0.1
        self._metrics.avg_wait_time = alpha * wait_time + (1 - alpha) * self._metrics.avg_wait_time
        self._update_throughput_metric()
    
    def _update_throughput_metric(self) -> None:
        """Update throughput metric."""
        time_elapsed = time.time() - self._metrics.last_reset
        if time_elapsed > 0:
            self._metrics.throughput_per_second = self._metrics.total_messages / time_elapsed
    
    async def flush_all_pending(self) -> None:
        """Flush all pending messages immediately."""
        connection_ids = list(self._pending_messages.keys())
        for connection_id in connection_ids:
            await self._flush_batch(connection_id)
    
    async def shutdown(self) -> None:
        """Shutdown the batcher and flush all pending messages."""
        self._shutdown = True
        self._cancel_all_timers()
        await self.flush_all_pending()
        logger.info("Message batcher shut down")
    
    def _cancel_all_timers(self) -> None:
        """Cancel all active batch timers."""
        self._timer_manager.cancel_all_timers()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get batching metrics."""
        return {
            "total_batches": self._metrics.total_batches,
            "total_messages": self._metrics.total_messages,
            "avg_batch_size": self._metrics.avg_batch_size,
            "avg_wait_time": self._metrics.avg_wait_time,
            "throughput_per_second": self._metrics.throughput_per_second,
            "pending_queues": len(self._pending_messages),
            "pending_messages": sum(len(msgs) for msgs in self._pending_messages.values()),
            "active_timers": self._timer_manager.get_active_timer_count()
        }
    
    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._metrics = BatchMetrics()