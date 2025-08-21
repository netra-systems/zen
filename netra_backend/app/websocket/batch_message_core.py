"""WebSocket Message Batcher Core.

Core message batching functionality with micro-functions.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union

from app.logging_config import central_logger
from app.schemas.websocket_message_types import ServerMessage
from app.websocket.connection import ConnectionInfo, ConnectionManager

from netra_backend.app.batch_message_types import BatchConfig, PendingMessage, BatchMetrics, MessageState
from netra_backend.app.batch_message_strategies import BatchingStrategyManager
from netra_backend.app.batch_load_monitor import LoadMonitor
from netra_backend.app.batch_message_operations import (
    send_batch_to_connection, BatchTimerManager, create_batched_message
)
from netra_backend.app.batch_message_transactional import (
    TransactionalBatchProcessor, RetryManager, MessageStateManager
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
        """Initialize strategy manager and transactional components."""
        self._load_monitor = LoadMonitor()
        self._strategy_manager = BatchingStrategyManager(self.config, self._load_monitor)
        self._transactional_processor = TransactionalBatchProcessor(self.config)
        self._retry_manager = RetryManager()
        self._state_manager = MessageStateManager()
    
    async def queue_message(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                           priority: int = 1, connection_id: Optional[str] = None) -> bool:
        """Queue a message for batched delivery."""
        if self._shutdown:
            return False
        return await self._process_message_queue(user_id, message, priority, connection_id)


    async def _process_message_queue(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                                   priority: int, connection_id: Optional[str]) -> bool:
        """Process message queueing with lock."""
        async with self._lock:
            return await self._queue_message_to_connections(user_id, message, priority, connection_id)


    async def _queue_message_to_connections(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                                          priority: int, connection_id: Optional[str]) -> bool:
        """Queue message to target connections."""
        connections = self.connection_manager.get_user_connections(user_id)
        if not self._validate_connections_exist(user_id, connections):
            return False
        
        target_connections = self._get_target_connections(connection_id, connections)
        await self._queue_to_connections(message, user_id, priority, target_connections)
        return True
    
    def _validate_connections_exist(self, user_id: str, connections: List[ConnectionInfo]) -> bool:
        """Validate that connections exist for user."""
        if not connections:
            self._log_no_connections(user_id)
            return False
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
        params = self._prepare_message_params(message, conn_id, user_id, priority)
        return PendingMessage(**params)
    
    def _prepare_message_params(self, message: Union[Dict[str, Any], ServerMessage], 
                               conn_id: str, user_id: str, priority: int) -> Dict[str, Any]:
        """Prepare parameters for pending message creation."""
        return {
            "content": message,
            "connection_id": conn_id,
            "user_id": user_id,
            "priority": priority
        }
    
    def _add_to_pending_queue(self, conn_id: str, pending_msg: PendingMessage) -> None:
        """Add message to pending queue for connection."""
        if conn_id not in self._pending_messages:
            self._pending_messages[conn_id] = []
        self._pending_messages[conn_id].append(pending_msg)
    
    async def _check_flush_conditions(self, connection_id: str) -> None:
        """Check if batch should be flushed based on strategy."""
        if connection_id not in self._pending_messages:
            return
        await self._evaluate_and_flush_batch(connection_id)


    async def _evaluate_and_flush_batch(self, connection_id: str) -> None:
        """Evaluate batch and decide whether to flush."""
        pending = self._pending_messages[connection_id]
        should_flush = self._strategy_manager.should_flush_batch(pending)
        await self._execute_flush_decision(connection_id, should_flush)
    
    async def _execute_flush_decision(self, connection_id: str, should_flush: bool) -> None:
        """Execute the flush decision for a connection."""
        if should_flush:
            await self._flush_batch(connection_id)
        else:
            await self._set_flush_timer(connection_id)
    
    async def _set_flush_timer(self, connection_id: str) -> None:
        """Set a timer to flush the batch after max wait time."""
        self._timer_manager.set_flush_timer(connection_id, self.config.max_wait_time, self._flush_batch)
    
    
    
    async def _flush_batch(self, connection_id: str) -> None:
        """Flush pending messages using transactional pattern."""
        async with self._lock:
            batch = self._mark_batch_sending(connection_id)
            if not batch:
                return
        
        await self._send_batch_transactionally(connection_id, batch)
    
    def _mark_batch_sending(self, connection_id: str) -> List[PendingMessage]:
        """Mark batch as SENDING without removing from queue (transactional)."""
        if not self._has_pending_messages(connection_id):
            return []
        
        return self._mark_pending_as_sending(connection_id)
    
    def _has_pending_messages(self, connection_id: str) -> bool:
        """Check if connection has pending messages."""
        return (connection_id in self._pending_messages and 
                bool(self._pending_messages[connection_id]))
    
    def _mark_pending_as_sending(self, connection_id: str) -> List[PendingMessage]:
        """Mark PENDING messages as SENDING and return batch."""
        all_messages = self._pending_messages[connection_id]
        pending_messages = self._state_manager.get_pending_messages(all_messages)
        
        if pending_messages:
            self._cleanup_timer(connection_id)
            return self._transactional_processor.mark_batch_sending(pending_messages)
        return []
    
    def _cleanup_timer(self, connection_id: str) -> None:
        """Clean up batch timer for connection."""
        self._timer_manager.cleanup_timer(connection_id)
    
    async def _send_batch_transactionally(self, connection_id: str, batch: List[PendingMessage]) -> None:
        """Send batch with transactional guarantees."""
        if not batch:
            return
        
        try:
            await self._attempt_send_with_retry(connection_id, batch)
            await self._handle_successful_send(connection_id, batch)
        except Exception as e:
            await self._handle_send_failure(connection_id, batch, e)


    async def _attempt_send_with_retry(self, connection_id: str, batch: List[PendingMessage]) -> None:
        """Attempt to send batch with connection validation."""
        connection_info = self.connection_manager.get_connection_by_id(connection_id)
        if not self._validate_connection_exists(connection_id, connection_info):
            raise ConnectionError(f"Connection {connection_id} no longer exists")
        
        await send_batch_to_connection(connection_info, batch, connection_id, self.config)
    
    def _validate_connection_exists(self, connection_id: str, connection_info) -> bool:
        """Validate connection exists for batch send."""
        if not connection_info:
            self._log_connection_not_found(connection_id)
            return False
        return True
    
    def _log_connection_not_found(self, connection_id: str) -> None:
        """Log when connection is not found."""
        logger.debug(f"Connection {connection_id} no longer exists")
    
    async def _handle_successful_send(self, connection_id: str, batch: List[PendingMessage]) -> None:
        """Handle successful batch send (mark as SENT and remove)."""
        async with self._lock:
            self._transactional_processor.mark_batch_sent(batch)
            self._remove_sent_messages(connection_id)
            self._update_send_metrics(batch)
    
    async def _handle_send_failure(self, connection_id: str, batch: List[PendingMessage], error: Exception) -> None:
        """Handle send failure (revert to PENDING or mark FAILED)."""
        logger.error(f"Failed to send batch to {connection_id}: {error}")
        async with self._lock:
            self._transactional_processor.revert_batch_to_pending(batch)
            self._schedule_retry_if_applicable(connection_id)
    
    
    
    def _remove_sent_messages(self, connection_id: str) -> None:
        """Remove SENT messages from queue."""
        if connection_id in self._pending_messages:
            self._pending_messages[connection_id] = self._state_manager.remove_sent_messages(
                self._pending_messages[connection_id]
            )
    
    def _schedule_retry_if_applicable(self, connection_id: str) -> None:
        """Schedule retry for failed messages if applicable."""
        if connection_id in self._pending_messages:
            failed_messages = self._state_manager.get_failed_messages(
                self._pending_messages[connection_id]
            )
            retryable = self._retry_manager.filter_retryable_messages(failed_messages)
            if retryable:
                self._timer_manager.set_flush_timer(
                    connection_id, 
                    self.config.max_wait_time,
                    self._flush_batch
                )
    
    def _update_send_metrics(self, batch: List[PendingMessage]) -> None:
        """Update metrics after successful send."""
        self._update_metrics(len(batch), 0.0)
    
    
    
    
    
    
    
    async def _requeue_messages(self, messages: List[PendingMessage]) -> None:
        """Re-queue messages that failed to send."""
        async with self._lock:
            for msg in messages:
                self._requeue_single_message_with_state(msg)
    
    def _requeue_single_message_with_state(self, msg: PendingMessage) -> None:
        """Re-queue single message with proper state management."""
        msg.state = MessageState.PENDING
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
        await self._flush_all_connection_batches(connection_ids)


    async def _flush_all_connection_batches(self, connection_ids: List[str]) -> None:
        """Flush batches for all connection IDs."""
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
        core_metrics = self._get_core_metrics()
        queue_metrics = self._get_queue_metrics()
        return {**core_metrics, **queue_metrics}


    def _get_core_metrics(self) -> Dict[str, Any]:
        """Get core batching metrics."""
        metric_fields = self._collect_metric_fields()
        return {field: getattr(self._metrics, field) for field in metric_fields}
    
    def _collect_metric_fields(self) -> List[str]:
        """Collect core metric field names."""
        return [
            "total_batches", "total_messages", "avg_batch_size",
            "avg_wait_time", "throughput_per_second"
        ]


    def _get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue and timer metrics with state information."""
        all_messages = [msg for msgs in self._pending_messages.values() for msg in msgs]
        state_counts = self._state_manager.count_by_state(all_messages)
        
        return {
            "pending_queues": len(self._pending_messages),
            "total_messages": len(all_messages),
            "pending_messages": state_counts[MessageState.PENDING],
            "sending_messages": state_counts[MessageState.SENDING], 
            "failed_messages": state_counts[MessageState.FAILED],
            "active_timers": self._timer_manager.get_active_timer_count()
        }
    
    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._metrics = BatchMetrics()