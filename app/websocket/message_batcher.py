"""WebSocket Message Batching System.

Implements efficient message batching for high-throughput scenarios
with configurable batching strategies and automatic flush mechanisms.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Union
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
    
    def __post_init__(self):
        """Calculate message size after initialization."""
        if self.size_bytes == 0:
            # Estimate message size
            import json
            self.size_bytes = len(json.dumps(self.message.model_dump(), default=str))


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
        
        # Check if batch can accommodate this message
        if not self._can_add_message(batched_msg):
            return False
        
        self.messages.append(batched_msg)
        self.total_size_bytes += batched_msg.size_bytes
        self.highest_priority = max(self.highest_priority, priority)
        
        return True
    
    def _can_add_message(self, message: BatchedMessage) -> bool:
        """Check if message can be added to batch."""
        # Check batch size limit
        if len(self.messages) >= self.config.max_batch_size:
            return False
        
        # Check memory limit
        new_total_size = self.total_size_bytes + message.size_bytes
        if new_total_size > self.config.max_batch_memory_kb * 1024:
            return False
        
        return True
    
    def should_flush(self) -> tuple[bool, str]:
        """Check if batch should be flushed."""
        now = datetime.now(timezone.utc)
        age_ms = (now - self.created_at).total_seconds() * 1000
        
        # Time-based flush
        if age_ms >= self.config.max_wait_time_ms:
            return True, "time_limit"
        
        # Size-based flush
        if len(self.messages) >= self.config.max_batch_size:
            return True, "size_limit"
        
        # Memory-based flush
        if self.total_size_bytes >= self.config.max_batch_memory_kb * 1024:
            return True, "memory_limit"
        
        # Priority-based flush
        if (self.config.flush_on_high_priority and 
            self.highest_priority >= self.config.priority_threshold):
            return True, "high_priority"
        
        return False, ""
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.messages) == 0
    
    def get_batch_data(self) -> Dict[str, Any]:
        """Get batch data for sending."""
        return {
            "type": "batch",
            "count": len(self.messages),
            "messages": [msg.message.model_dump() for msg in self.messages],
            "total_size_bytes": self.total_size_bytes,
            "highest_priority": self.highest_priority,
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
    
    async def start(self, send_callback: Callable) -> None:
        """Start the message batcher."""
        if self._running:
            return
        
        self.send_callback = send_callback
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Message batcher started")
    
    async def stop(self) -> None:
        """Stop the message batcher and flush remaining messages."""
        self._running = False
        
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush all remaining batches
        await self._flush_all_batches("shutdown")
        logger.info("Message batcher stopped")
    
    async def add_message(self, connection_id: str, message: WebSocketMessage, 
                         priority: int = 0) -> bool:
        """Add message to batch for a connection."""
        if not self._running:
            return False
        
        # Get or create batch for connection
        if connection_id not in self.batches:
            self.batches[connection_id] = MessageBatch(self.config)
        
        batch = self.batches[connection_id]
        
        # Try to add message to existing batch
        if batch.add_message(message, priority):
            # Check if batch should be flushed immediately
            should_flush, reason = batch.should_flush()
            if should_flush:
                await self._flush_batch(connection_id, reason)
            return True
        
        # Current batch is full, flush it and create new one
        await self._flush_batch(connection_id, "batch_full")
        
        # Create new batch and add message
        self.batches[connection_id] = MessageBatch(self.config)
        return self.batches[connection_id].add_message(message, priority)
    
    async def flush_connection(self, connection_id: str) -> bool:
        """Force flush all messages for a connection."""
        if connection_id in self.batches:
            await self._flush_batch(connection_id, "forced")
            return True
        return False
    
    async def _flush_loop(self) -> None:
        """Main flush loop for time-based batching."""
        while self._running:
            try:
                await self._check_and_flush_batches()
                await asyncio.sleep(0.01)  # Check every 10ms
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
                await asyncio.sleep(0.1)
    
    async def _check_and_flush_batches(self) -> None:
        """Check all batches and flush those that should be flushed."""
        connections_to_flush = []
        
        for connection_id, batch in self.batches.items():
            if batch.is_empty():
                continue
                
            should_flush, reason = batch.should_flush()
            if should_flush:
                connections_to_flush.append((connection_id, reason))
        
        for connection_id, reason in connections_to_flush:
            await self._flush_batch(connection_id, reason)
    
    async def _flush_batch(self, connection_id: str, reason: str) -> None:
        """Flush a specific batch."""
        if connection_id not in self.batches:
            return
        
        batch = self.batches[connection_id]
        if batch.is_empty():
            return
        
        batch_data = batch.get_batch_data()
        
        try:
            # Send batch using callback
            if self.send_callback:
                await self.send_callback(connection_id, batch_data)
            
            # Update metrics
            self._update_metrics(batch, reason)
            
            logger.debug(f"Flushed batch for {connection_id}: {len(batch.messages)} messages ({reason})")
            
        except Exception as e:
            logger.error(f"Error flushing batch for {connection_id}: {e}")
        
        # Create new empty batch
        self.batches[connection_id] = MessageBatch(self.config)
    
    async def _flush_all_batches(self, reason: str) -> None:
        """Flush all batches."""
        for connection_id in list(self.batches.keys()):
            await self._flush_batch(connection_id, reason)
    
    def _update_metrics(self, batch: MessageBatch, reason: str) -> None:
        """Update batching metrics."""
        message_count = len(batch.messages)
        wait_time_ms = (datetime.now(timezone.utc) - batch.created_at).total_seconds() * 1000
        
        self.metrics.total_batches_sent += 1
        self.metrics.total_messages_batched += message_count
        self.metrics.total_bytes_sent += batch.total_size_bytes
        
        # Update averages
        total_batches = self.metrics.total_batches_sent
        self.metrics.average_batch_size = self.metrics.total_messages_batched / total_batches
        self.metrics.average_wait_time_ms = (
            (self.metrics.average_wait_time_ms * (total_batches - 1) + wait_time_ms) / total_batches
        )
        
        # Update flush reason counters
        if reason == "forced":
            self.metrics.forced_flushes += 1
        elif reason in ["time_limit"]:
            self.metrics.time_based_flushes += 1
        elif reason in ["size_limit", "memory_limit", "batch_full"]:
            self.metrics.size_based_flushes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics."""
        active_batches = sum(1 for batch in self.batches.values() if not batch.is_empty())
        total_pending_messages = sum(len(batch.messages) for batch in self.batches.values())
        
        return {
            "config": self.config.__dict__,
            "metrics": self.metrics.__dict__,
            "active_batches": active_batches,
            "total_pending_messages": total_pending_messages,
            "connections_with_batches": len(self.batches),
            "running": self._running
        }
    
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
        
        return {
            "connection_id": connection_id,
            "message_count": len(batch.messages),
            "total_size_bytes": batch.total_size_bytes,
            "highest_priority": batch.highest_priority,
            "created_at": batch.created_at.isoformat(),
            "should_flush": should_flush,
            "flush_reason": flush_reason,
            "is_empty": batch.is_empty()
        }