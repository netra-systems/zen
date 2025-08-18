"""WebSocket Message Batching System.

Implements efficient message batching for high-throughput scenarios
with configurable batching strategies and automatic flush mechanisms.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage

logger = central_logger.get_logger(__name__)


class BatchStrategy(str, Enum):
    """Batching strategy options."""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"
    PRIORITY_BASED = "priority_based"


@dataclass
class BatchConfig:
    """Batching configuration."""
    strategy: BatchStrategy = BatchStrategy.HYBRID
    max_batch_size: int = 50
    max_wait_time_ms: int = 100
    max_batch_memory_kb: int = 500
    priority_threshold: int = 5
    flush_on_high_priority: bool = True


@dataclass
class BatchedMessage:
    """Container for batched message."""
    message: WebSocketMessage
    priority: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    size_bytes: int = 0
    _cached_data: Optional[Dict] = field(default=None, init=False)
    
    def __post_init__(self):
        """Calculate message size efficiently."""
        if self.size_bytes == 0:
            # Use a more efficient size estimation
            self.size_bytes = len(str(self.message)) * 2  # Conservative estimate


@dataclass
class BatchMetrics:
    """Batch processing metrics."""
    total_batches_sent: int = 0
    total_messages_batched: int = 0
    average_batch_size: float = 0.0
    average_wait_time_ms: float = 0.0
    total_bytes_sent: int = 0
    forced_flushes: int = 0
    time_based_flushes: int = 0
    size_based_flushes: int = 0


class MessageBatch:
    """Single message batch container."""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.messages: List[BatchedMessage] = []
        self.created_at = datetime.now(timezone.utc)
        self.total_size_bytes = 0
        self.highest_priority = 0
    
    def add_message(self, message: WebSocketMessage, priority: int = 0) -> bool:
        """Add message to batch if it fits."""
        batched_msg = BatchedMessage(message=message, priority=priority)
        if not self._can_add_message(batched_msg):
            return False
        self._add_batched_message(batched_msg, priority)
        return True

    def _add_batched_message(self, batched_msg: BatchedMessage, priority: int) -> None:
        """Add batched message and update batch stats."""
        self.messages.append(batched_msg)
        self.total_size_bytes += batched_msg.size_bytes
        self.highest_priority = max(self.highest_priority, priority)
    
    def _can_add_message(self, message: BatchedMessage) -> bool:
        """Check if message can be added to batch."""
        if self._exceeds_size_limit():
            return False
        if self._exceeds_memory_limit(message):
            return False
        return True

    def _exceeds_size_limit(self) -> bool:
        """Check if batch size limit is exceeded."""
        return len(self.messages) >= self.config.max_batch_size

    def _exceeds_memory_limit(self, message: BatchedMessage) -> bool:
        """Check if memory limit would be exceeded."""
        new_total_size = self.total_size_bytes + message.size_bytes
        return new_total_size > self.config.max_batch_memory_kb * 1024
    
    def should_flush(self) -> tuple[bool, str]:
        """Check if batch should be flushed."""
        age_ms = self._calculate_batch_age_ms()
        flush_checks = self._get_flush_checks(age_ms)
        return next(((True, reason) for should_flush, reason in flush_checks if should_flush), (False, ""))

    def _get_flush_checks(self, age_ms: float) -> List[Tuple[bool, str]]:
        """Get list of flush condition checks."""
        return [
            (self._should_flush_by_time(age_ms), "time_limit"),
            (self._should_flush_by_size(), "size_limit"),
            (self._should_flush_by_memory(), "memory_limit"),
            (self._should_flush_by_priority(), "high_priority")
        ]

    def _calculate_batch_age_ms(self) -> float:
        """Calculate batch age in milliseconds."""
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds() * 1000

    def _should_flush_by_time(self, age_ms: float) -> bool:
        """Check if batch should flush based on time."""
        return age_ms >= self.config.max_wait_time_ms

    def _should_flush_by_size(self) -> bool:
        """Check if batch should flush based on size."""
        return len(self.messages) >= self.config.max_batch_size

    def _should_flush_by_memory(self) -> bool:
        """Check if batch should flush based on memory usage."""
        return self.total_size_bytes >= self.config.max_batch_memory_kb * 1024

    def _should_flush_by_priority(self) -> bool:
        """Check if batch should flush based on priority."""
        return (self.config.flush_on_high_priority and 
               self.highest_priority >= self.config.priority_threshold)
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.messages) == 0
    
    def get_batch_data(self) -> Dict[str, Any]:
        """Get batch data for sending efficiently."""
        # Cache serialized messages to avoid repeated model_dump() calls
        messages_data = []
        for msg in self.messages:
            if msg._cached_data is None:
                msg._cached_data = msg.message.model_dump()
            messages_data.append(msg._cached_data)
        
        return {
            "type": "batch", "count": len(self.messages),
            "messages": messages_data,
            "total_size_bytes": self.total_size_bytes, "highest_priority": self.highest_priority,
            "created_at": self.created_at.isoformat()
        }


class WebSocketMessageBatcher:
    """High-throughput message batcher for WebSocket connections."""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self.batches: Dict[str, MessageBatch] = {}
        self.send_callback: Optional[Callable] = None
        self.metrics = BatchMetrics()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_flush_check = time.time()
        self._flush_check_interval = 0.05  # Check every 50ms instead of 10ms
    
    async def start(self, send_callback: Callable) -> None:
        """Start the message batcher."""
        if self._running:
            return
        self._initialize_batcher(send_callback)
        logger.info("Message batcher started")

    def _initialize_batcher(self, send_callback: Callable) -> None:
        """Initialize batcher with callback and start flush task."""
        self.send_callback = send_callback
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def stop(self) -> None:
        """Stop the message batcher and flush remaining messages."""
        self._running = False
        await self._cancel_flush_task()
        await self._flush_all_batches("shutdown")
        logger.info("Message batcher stopped")

    async def _cancel_flush_task(self) -> None:
        """Cancel the flush task gracefully."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
    
    async def add_message(self, connection_id: str, message: WebSocketMessage, 
                         priority: int = 0) -> bool:
        """Add message to batch for a connection."""
        if not self._running:
            return False
        batch = self._get_or_create_batch(connection_id)
        return await self._add_message_to_batch(connection_id, batch, message, priority)

    def _get_or_create_batch(self, connection_id: str) -> MessageBatch:
        """Get existing batch or create new one for connection."""
        if connection_id not in self.batches:
            self.batches[connection_id] = MessageBatch(self.config)
        return self.batches[connection_id]

    async def _add_message_to_batch(self, connection_id: str, batch: MessageBatch, 
                                  message: WebSocketMessage, priority: int) -> bool:
        """Add message to batch and handle flush if needed."""
        if batch.add_message(message, priority):
            return await self._check_and_flush_if_needed(connection_id, batch)
        await self._flush_and_recreate_batch(connection_id, message, priority)
        return True

    async def _check_and_flush_if_needed(self, connection_id: str, batch: MessageBatch) -> bool:
        """Check if batch should be flushed and flush if needed."""
        should_flush, reason = batch.should_flush()
        if should_flush:
            await self._flush_batch(connection_id, reason)
        return True

    async def _flush_and_recreate_batch(self, connection_id: str, message: WebSocketMessage, priority: int) -> None:
        """Flush current batch and create new one with message."""
        await self._flush_batch(connection_id, "batch_full")
        self.batches[connection_id] = MessageBatch(self.config)
        self.batches[connection_id].add_message(message, priority)
    
    async def flush_connection(self, connection_id: str) -> bool:
        """Force flush all messages for a connection."""
        if connection_id in self.batches:
            await self._flush_batch(connection_id, "forced")
            return True
        return False
    
    async def _flush_loop(self) -> None:
        """Main flush loop for time-based batching."""
        while self._running:
            await self._execute_flush_cycle_with_error_handling()

    async def _execute_flush_cycle_with_error_handling(self) -> None:
        """Execute flush cycle with exception handling."""
        try:
            await self._execute_flush_cycle()
        except asyncio.CancelledError:
            self._running = False  # Stop the loop
        except Exception as e:
            await self._handle_flush_loop_error(e)

    async def _execute_flush_cycle(self) -> None:
        """Execute one flush cycle efficiently."""
        current_time = time.time()
        if current_time - self._last_flush_check >= self._flush_check_interval:
            await self._check_and_flush_batches()
            self._last_flush_check = current_time
        await asyncio.sleep(0.01)  # Maintain responsiveness

    async def _handle_flush_loop_error(self, error: Exception) -> None:
        """Handle errors in flush loop."""
        logger.error(f"Flush loop error: {error}")
        await asyncio.sleep(0.1)
    
    async def _check_and_flush_batches(self) -> None:
        """Check all batches and flush those that should be flushed."""
        connections_to_flush = self._identify_batches_to_flush()
        for connection_id, reason in connections_to_flush:
            await self._flush_batch(connection_id, reason)

    def _identify_batches_to_flush(self) -> List[Tuple[str, str]]:
        """Identify which batches need flushing efficiently."""
        connections_to_flush = []
        # Only check non-empty batches to avoid unnecessary processing
        for connection_id, batch in self.batches.items():
            if not batch.is_empty():
                flush_info = self._check_batch_flush_needed(batch)
                if flush_info:
                    connections_to_flush.append((connection_id, flush_info))
        return connections_to_flush

    def _check_batch_flush_needed(self, batch: MessageBatch) -> Optional[str]:
        """Check if batch needs flushing and return reason."""
        if not batch.is_empty():
            should_flush, reason = batch.should_flush()
            return reason if should_flush else None
        return None
    
    async def _flush_batch(self, connection_id: str, reason: str) -> None:
        """Flush a specific batch."""
        if not self._can_flush_batch(connection_id):
            return
        batch = self.batches[connection_id]
        batch_data = batch.get_batch_data()
        await self._send_batch_data(connection_id, batch, batch_data, reason)
        self._create_new_batch(connection_id)

    def _can_flush_batch(self, connection_id: str) -> bool:
        """Check if batch can be flushed."""
        if connection_id not in self.batches:
            return False
        return not self.batches[connection_id].is_empty()

    async def _send_batch_data(self, connection_id: str, batch: MessageBatch, 
                             batch_data: Dict[str, Any], reason: str) -> None:
        """Send batch data using callback and update metrics."""
        try:
            await self._execute_send_callback(connection_id, batch_data)
            self._finalize_batch_send(batch, connection_id, reason)
        except Exception as e:
            logger.error(f"Error flushing batch for {connection_id}: {e}")

    def _finalize_batch_send(self, batch: MessageBatch, connection_id: str, reason: str) -> None:
        """Finalize batch send with metrics and logging."""
        self._update_metrics(batch, reason)
        self._log_batch_flush(connection_id, batch, reason)

    async def _execute_send_callback(self, connection_id: str, batch_data: Dict[str, Any]) -> None:
        """Execute send callback if available."""
        if self.send_callback:
            await self.send_callback(connection_id, batch_data)

    def _log_batch_flush(self, connection_id: str, batch: MessageBatch, reason: str) -> None:
        """Log successful batch flush."""
        logger.debug(f"Flushed batch for {connection_id}: {len(batch.messages)} messages ({reason})")

    def _create_new_batch(self, connection_id: str) -> None:
        """Create new empty batch for connection."""
        self.batches[connection_id] = MessageBatch(self.config)
    
    async def _flush_all_batches(self, reason: str) -> None:
        """Flush all batches."""
        for connection_id in list(self.batches.keys()):
            await self._flush_batch(connection_id, reason)
    
    def _update_metrics(self, batch: MessageBatch, reason: str) -> None:
        """Update batching metrics."""
        message_count = len(batch.messages)
        wait_time_ms = (datetime.now(timezone.utc) - batch.created_at).total_seconds() * 1000
        self._update_basic_metrics(message_count, batch.total_size_bytes)
        self._update_average_metrics(wait_time_ms)
        self._update_flush_reason_counters(reason)

    def _update_basic_metrics(self, message_count: int, total_size_bytes: int) -> None:
        """Update basic batch metrics."""
        self.metrics.total_batches_sent += 1
        self.metrics.total_messages_batched += message_count
        self.metrics.total_bytes_sent += total_size_bytes

    def _update_average_metrics(self, wait_time_ms: float) -> None:
        """Update average metrics calculations."""
        total_batches = self.metrics.total_batches_sent
        self.metrics.average_batch_size = self.metrics.total_messages_batched / total_batches
        self.metrics.average_wait_time_ms = (
            (self.metrics.average_wait_time_ms * (total_batches - 1) + wait_time_ms) / total_batches
        )

    def _update_flush_reason_counters(self, reason: str) -> None:
        """Update flush reason counters based on reason."""
        if reason == "forced":
            self.metrics.forced_flushes += 1
        elif reason in ["time_limit"]:
            self.metrics.time_based_flushes += 1
        elif reason in ["size_limit", "memory_limit", "batch_full"]:
            self.metrics.size_based_flushes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics."""
        batch_counts = self._calculate_batch_counts()
        return {
            "config": self.config.__dict__, "metrics": self.metrics.__dict__,
            **batch_counts, "connections_with_batches": len(self.batches), "running": self._running
        }

    def _calculate_batch_counts(self) -> Dict[str, int]:
        """Calculate active batch and message counts."""
        active_batches = sum(1 for batch in self.batches.values() if not batch.is_empty())
        total_pending_messages = sum(len(batch.messages) for batch in self.batches.values())
        return {"active_batches": active_batches, "total_pending_messages": total_pending_messages}
    
    def update_config(self, new_config: BatchConfig) -> None:
        """Update batching configuration."""
        self.config = new_config
        logger.info(f"Updated batch configuration: {new_config}")
    
    def get_connection_batch_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get batch information for a specific connection."""
        if connection_id not in self.batches:
            return None
        batch = self.batches[connection_id]
        should_flush, flush_reason = batch.should_flush()
        return self._build_connection_batch_info(connection_id, batch, should_flush, flush_reason)

    def _build_connection_batch_info(self, connection_id: str, batch: MessageBatch, 
                                   should_flush: bool, flush_reason: str) -> Dict[str, Any]:
        """Build connection batch information dictionary."""
        base_info = self._get_batch_base_info(connection_id, batch)
        flush_info = {"should_flush": should_flush, "flush_reason": flush_reason, "is_empty": batch.is_empty()}
        return {**base_info, **flush_info}

    def _get_batch_base_info(self, connection_id: str, batch: MessageBatch) -> Dict[str, Any]:
        """Get base batch information."""
        return {
            "connection_id": connection_id, "message_count": len(batch.messages),
            "total_size_bytes": batch.total_size_bytes, "highest_priority": batch.highest_priority,
            "created_at": batch.created_at.isoformat()
        }