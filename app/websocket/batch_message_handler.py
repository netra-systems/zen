"""WebSocket message batching for improved performance.

This module provides efficient message batching capabilities to reduce
the overhead of individual WebSocket message sends and improve throughput.
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum

from app.logging_config import central_logger
from app.schemas.websocket_message_types import ServerMessage
from app.websocket.connection import ConnectionInfo, ConnectionManager

logger = central_logger.get_logger(__name__)


class BatchingStrategy(Enum):
    """Message batching strategies."""
    TIME_BASED = "time_based"      # Batch by time interval
    SIZE_BASED = "size_based"      # Batch by message count
    ADAPTIVE = "adaptive"          # Adaptive batching based on load
    PRIORITY = "priority"          # Batch by message priority


@dataclass
class BatchConfig:
    """Configuration for message batching."""
    max_batch_size: int = 10
    max_wait_time: float = 0.1  # 100ms
    strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    priority_threshold: int = 3
    adaptive_min_batch: int = 2
    adaptive_max_batch: int = 50


@dataclass
class PendingMessage:
    """Message pending in batch queue."""
    content: Union[Dict[str, Any], ServerMessage]
    connection_id: str
    user_id: str
    priority: int = 1
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(json.dumps(self.content, default=str))


@dataclass
class BatchMetrics:
    """Metrics for batch processing."""
    total_batches: int = 0
    total_messages: int = 0
    avg_batch_size: float = 0.0
    avg_wait_time: float = 0.0
    compression_ratio: float = 0.0
    throughput_per_second: float = 0.0
    last_reset: float = field(default_factory=time.time)


class MessageBatcher:
    """Efficient WebSocket message batching system."""
    
    def __init__(self, config: BatchConfig, connection_manager: ConnectionManager):
        self.config = config
        self.connection_manager = connection_manager
        self._pending_messages: Dict[str, List[PendingMessage]] = {}
        self._batch_timers: Dict[str, asyncio.Handle] = {}
        self._metrics = BatchMetrics()
        self._lock = asyncio.Lock()
        self._load_monitor = LoadMonitor()
        self._shutdown = False
    
    async def queue_message(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                           priority: int = 1, connection_id: Optional[str] = None) -> bool:
        """Queue a message for batched delivery."""
        if self._shutdown:
            return False
        
        async with self._lock:
            # Get user connections
            connections = self.connection_manager.get_user_connections(user_id)
            if not connections:
                logger.debug(f"No connections for user {user_id}, dropping message")
                return False
            
            # If no specific connection, batch for all user connections
            target_connections = [connection_id] if connection_id else [conn.connection_id for conn in connections]
            
            for conn_id in target_connections:
                pending_msg = PendingMessage(
                    content=message,
                    connection_id=conn_id,
                    user_id=user_id,
                    priority=priority
                )
                
                # Initialize pending queue for connection
                if conn_id not in self._pending_messages:
                    self._pending_messages[conn_id] = []
                
                self._pending_messages[conn_id].append(pending_msg)
                
                # Check if batch should be flushed
                await self._check_flush_conditions(conn_id)
            
            return True
    
    async def _check_flush_conditions(self, connection_id: str) -> None:
        """Check if batch should be flushed based on strategy."""
        if connection_id not in self._pending_messages:
            return
        
        pending = self._pending_messages[connection_id]
        if not pending:
            return
        
        should_flush = False
        
        if self.config.strategy == BatchingStrategy.SIZE_BASED:
            should_flush = len(pending) >= self.config.max_batch_size
        
        elif self.config.strategy == BatchingStrategy.TIME_BASED:
            oldest_msg = min(pending, key=lambda m: m.timestamp)
            age = time.time() - oldest_msg.timestamp
            should_flush = age >= self.config.max_wait_time
        
        elif self.config.strategy == BatchingStrategy.PRIORITY:
            high_priority_count = sum(1 for msg in pending if msg.priority >= self.config.priority_threshold)
            should_flush = (high_priority_count > 0 and len(pending) >= self.config.adaptive_min_batch) or \
                          len(pending) >= self.config.max_batch_size
        
        elif self.config.strategy == BatchingStrategy.ADAPTIVE:
            current_load = self._load_monitor.get_current_load()
            dynamic_batch_size = self._calculate_adaptive_batch_size(current_load)
            should_flush = len(pending) >= dynamic_batch_size
            
            # Also check time-based condition for adaptive
            if not should_flush and pending:
                oldest_msg = min(pending, key=lambda m: m.timestamp)
                age = time.time() - oldest_msg.timestamp
                should_flush = age >= self.config.max_wait_time
        
        if should_flush:
            await self._flush_batch(connection_id)
        else:
            # Set timer if not already set
            await self._set_flush_timer(connection_id)
    
    def _calculate_adaptive_batch_size(self, load: float) -> int:
        """Calculate adaptive batch size based on current load."""
        # High load = larger batches for efficiency
        # Low load = smaller batches for responsiveness
        if load > 0.8:
            return self.config.adaptive_max_batch
        elif load > 0.5:
            return (self.config.adaptive_max_batch + self.config.adaptive_min_batch) // 2
        else:
            return self.config.adaptive_min_batch
    
    async def _set_flush_timer(self, connection_id: str) -> None:
        """Set a timer to flush the batch after max wait time."""
        # Cancel existing timer
        if connection_id in self._batch_timers:
            self._batch_timers[connection_id].cancel()
        
        # Set new timer
        loop = asyncio.get_event_loop()
        self._batch_timers[connection_id] = loop.call_later(
            self.config.max_wait_time,
            lambda: asyncio.create_task(self._flush_batch(connection_id))
        )
    
    async def _flush_batch(self, connection_id: str) -> None:
        """Flush pending messages for a connection."""
        async with self._lock:
            if connection_id not in self._pending_messages or not self._pending_messages[connection_id]:
                return
            
            batch = self._pending_messages[connection_id].copy()
            self._pending_messages[connection_id].clear()
            
            # Cancel timer
            if connection_id in self._batch_timers:
                self._batch_timers[connection_id].cancel()
                del self._batch_timers[connection_id]
        
        # Send batch outside of lock
        await self._send_batch(connection_id, batch)
    
    async def _send_batch(self, connection_id: str, batch: List[PendingMessage]) -> None:
        """Send a batch of messages to a connection."""
        if not batch:
            return
        
        connection_info = self.connection_manager.get_connection_by_id(connection_id)
        if not connection_info:
            logger.debug(f"Connection {connection_id} no longer exists")
            return
        
        start_time = time.time()
        
        try:
            # Create batched message
            batched_msg = self._create_batched_message(batch)
            
            # Send the batch
            await connection_info.websocket.send_json(batched_msg)
            
            # Update metrics
            wait_time = start_time - min(msg.timestamp for msg in batch)
            self._update_metrics(len(batch), wait_time)
            
            # Update connection stats
            connection_info.message_count += len(batch)
            
            logger.debug(f"Sent batch of {len(batch)} messages to {connection_id}")
            
        except Exception as e:
            logger.error(f"Error sending batch to {connection_id}: {e}")
            # Re-queue high priority messages
            high_priority_messages = [msg for msg in batch if msg.priority >= self.config.priority_threshold]
            if high_priority_messages:
                await self._requeue_messages(high_priority_messages)
    
    def _create_batched_message(self, batch: List[PendingMessage]) -> Dict[str, Any]:
        """Create a batched message structure."""
        messages = [msg.content for msg in batch]
        
        # Sort by priority (highest first)
        sorted_batch = sorted(batch, key=lambda m: m.priority, reverse=True)
        
        return {
            "type": "batch",
            "batch_id": f"batch_{int(time.time() * 1000)}",
            "messages": [msg.content for msg in sorted_batch],
            "message_count": len(batch),
            "timestamp": time.time(),
            "compression": "none",  # Could add compression here
            "metadata": {
                "batch_size": len(batch),
                "priority_distribution": self._get_priority_distribution(batch),
                "total_size_bytes": sum(msg.size_bytes for msg in batch)
            }
        }
    
    def _get_priority_distribution(self, batch: List[PendingMessage]) -> Dict[str, int]:
        """Get priority distribution for batch metadata."""
        distribution = {}
        for msg in batch:
            priority_key = f"priority_{msg.priority}"
            distribution[priority_key] = distribution.get(priority_key, 0) + 1
        return distribution
    
    async def _requeue_messages(self, messages: List[PendingMessage]) -> None:
        """Re-queue messages that failed to send."""
        async with self._lock:
            for msg in messages:
                if msg.connection_id not in self._pending_messages:
                    self._pending_messages[msg.connection_id] = []
                self._pending_messages[msg.connection_id].insert(0, msg)  # Insert at front
    
    def _update_metrics(self, batch_size: int, wait_time: float) -> None:
        """Update batching metrics."""
        self._metrics.total_batches += 1
        self._metrics.total_messages += batch_size
        
        # Update averages
        self._metrics.avg_batch_size = self._metrics.total_messages / self._metrics.total_batches
        
        # Update wait time (exponential moving average)
        alpha = 0.1
        self._metrics.avg_wait_time = alpha * wait_time + (1 - alpha) * self._metrics.avg_wait_time
        
        # Update throughput
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
        
        # Cancel all timers
        for timer in self._batch_timers.values():
            timer.cancel()
        self._batch_timers.clear()
        
        # Flush all pending messages
        await self.flush_all_pending()
        
        logger.info("Message batcher shut down")
    
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
            "active_timers": len(self._batch_timers)
        }
    
    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._metrics = BatchMetrics()


class LoadMonitor:
    """Monitor system load for adaptive batching."""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self._load_history: List[Tuple[float, float]] = []  # (timestamp, load)
        self._lock = asyncio.Lock()
    
    async def record_load(self, load: float) -> None:
        """Record current load measurement."""
        async with self._lock:
            now = time.time()
            self._load_history.append((now, load))
            
            # Trim old entries
            cutoff_time = now - self.window_size
            self._load_history = [(t, l) for t, l in self._load_history if t > cutoff_time]
    
    def get_current_load(self) -> float:
        """Get current system load estimate."""
        if not self._load_history:
            return 0.0
        
        # Return weighted average of recent load measurements
        now = time.time()
        total_weight = 0.0
        weighted_sum = 0.0
        
        for timestamp, load in self._load_history:
            age = now - timestamp
            weight = max(0, 1.0 - (age / self.window_size))  # Linear decay
            weighted_sum += load * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class BatchedBroadcastManager:
    """Enhanced broadcast manager with batching capabilities."""
    
    def __init__(self, connection_manager: ConnectionManager, batch_config: Optional[BatchConfig] = None):
        self.connection_manager = connection_manager
        self.batch_config = batch_config or BatchConfig()
        self.message_batcher = MessageBatcher(self.batch_config, connection_manager)
        self._stats = {
            "total_broadcasts": 0,
            "batched_broadcasts": 0,
            "direct_broadcasts": 0
        }
    
    async def broadcast_to_user(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                               priority: int = 1, use_batching: bool = True) -> bool:
        """Broadcast message to user with optional batching."""
        self._stats["total_broadcasts"] += 1
        
        if use_batching and priority < self.batch_config.priority_threshold:
            # Use batching for non-critical messages
            success = await self.message_batcher.queue_message(user_id, message, priority)
            if success:
                self._stats["batched_broadcasts"] += 1
            return success
        else:
            # Send immediately for high-priority messages
            self._stats["direct_broadcasts"] += 1
            return await self._send_direct(user_id, message)
    
    async def _send_direct(self, user_id: str, message: Union[Dict[str, Any], ServerMessage]) -> bool:
        """Send message directly without batching."""
        connections = self.connection_manager.get_user_connections(user_id)
        if not connections:
            return False
        
        success_count = 0
        for conn_info in connections:
            try:
                await conn_info.websocket.send_json(message)
                conn_info.message_count += 1
                success_count += 1
            except Exception as e:
                logger.error(f"Error sending direct message to {conn_info.connection_id}: {e}")
        
        return success_count > 0
    
    async def shutdown(self) -> None:
        """Shutdown broadcast manager."""
        await self.message_batcher.shutdown()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcast statistics."""
        batch_stats = self.message_batcher.get_metrics()
        return {
            **self._stats,
            "batching": batch_stats
        }