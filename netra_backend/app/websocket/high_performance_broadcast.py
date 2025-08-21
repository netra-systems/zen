"""High-Performance WebSocket Broadcasting System.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Scalability - Handle enterprise-scale broadcasts efficiently
- Value Impact: Enables real-time features for large teams and workspaces
- Strategic Impact: $60K MRR - Enterprise broadcast capability for collaboration

This module provides:
- Optimized broadcasting for 1000+ concurrent connections
- Batch message processing with asyncio tasks
- Memory-efficient message buffering
- Connection pooling with proper limits
- Sub-100ms broadcast latency for 100 clients
- Graceful degradation under high load
"""

import asyncio
import gc
import json
import time
import weakref
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Union

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.websocket_message_types import (
    BroadcastResult,
    ServerMessage,
)

logger = central_logger.get_logger(__name__)


@dataclass
class BroadcastPerformanceConfig:
    """Configuration for high-performance broadcasting."""
    
    # Batch processing settings
    max_batch_size: int = 100
    batch_timeout_ms: int = 50  # Maximum time to wait for batch
    
    # Connection pool settings
    max_connections_per_pool: int = 1000
    pool_timeout_seconds: int = 30
    
    # Memory management
    max_memory_buffer_mb: int = 100
    message_compression_threshold: int = 1024  # bytes
    
    # Performance targets
    target_latency_ms: int = 100
    max_concurrent_broadcasts: int = 10
    
    # Backpressure settings
    slow_client_threshold_ms: int = 500
    disconnect_threshold_failures: int = 5


@dataclass
class ConnectionPool:
    """Pool of WebSocket connections for efficient broadcasting."""
    
    connections: Set[WebSocket] = field(default_factory=set)
    active_connections: Set[WebSocket] = field(default_factory=set)
    slow_connections: Set[WebSocket] = field(default_factory=set)
    failed_counts: Dict[WebSocket, int] = field(default_factory=dict)
    last_activity: Dict[WebSocket, float] = field(default_factory=dict)
    
    def add_connection(self, websocket: WebSocket) -> bool:
        """Add connection to pool."""
        if len(self.connections) >= 1000:  # Pool limit
            return False
        
        self.connections.add(websocket)
        self.active_connections.add(websocket)
        self.last_activity[websocket] = time.time()
        self.failed_counts[websocket] = 0
        return True
    
    def remove_connection(self, websocket: WebSocket) -> None:
        """Remove connection from pool."""
        self.connections.discard(websocket)
        self.active_connections.discard(websocket)
        self.slow_connections.discard(websocket)
        self.failed_counts.pop(websocket, None)
        self.last_activity.pop(websocket, None)
    
    def mark_slow(self, websocket: WebSocket) -> None:
        """Mark connection as slow."""
        self.slow_connections.add(websocket)
        self.active_connections.discard(websocket)
    
    def mark_failed(self, websocket: WebSocket) -> bool:
        """Mark connection as failed, return if should disconnect."""
        self.failed_counts[websocket] = self.failed_counts.get(websocket, 0) + 1
        return self.failed_counts[websocket] >= 5
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            "total": len(self.connections),
            "active": len(self.active_connections),
            "slow": len(self.slow_connections),
            "with_failures": len([c for c in self.failed_counts.values() if c > 0])
        }


class MessageBuffer:
    """Memory-efficient message buffering system."""
    
    def __init__(self, max_size_mb: int = 100):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.messages: deque = deque()
        self.message_sizes: deque = deque()
        
    def add_message(self, message: Union[str, Dict[str, Any]]) -> bool:
        """Add message to buffer if within memory limits."""
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = message
        
        message_size = len(message_str.encode('utf-8'))
        
        # Check if adding this message would exceed limit
        if self.current_size + message_size > self.max_size_bytes:
            self._evict_old_messages(message_size)
        
        # If still too large, reject
        if self.current_size + message_size > self.max_size_bytes:
            return False
        
        self.messages.append(message_str)
        self.message_sizes.append(message_size)
        self.current_size += message_size
        return True
    
    def _evict_old_messages(self, needed_size: int) -> None:
        """Evict old messages to make space."""
        while self.messages and self.current_size + needed_size > self.max_size_bytes:
            self.messages.popleft()
            size = self.message_sizes.popleft()
            self.current_size -= size
    
    def get_messages(self, max_count: int = None) -> List[str]:
        """Get messages from buffer."""
        if max_count is None:
            result = list(self.messages)
            self.clear()
            return result
        
        result = []
        for _ in range(min(max_count, len(self.messages))):
            if self.messages:
                message = self.messages.popleft()
                size = self.message_sizes.popleft()
                self.current_size -= size
                result.append(message)
        
        return result
    
    def clear(self) -> None:
        """Clear all messages from buffer."""
        self.messages.clear()
        self.message_sizes.clear()
        self.current_size = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            "message_count": len(self.messages),
            "size_bytes": self.current_size,
            "size_mb": self.current_size / (1024 * 1024),
            "utilization": self.current_size / self.max_size_bytes
        }


class HighPerformanceBroadcaster:
    """High-performance WebSocket broadcaster for 1000+ connections."""
    
    def __init__(self, config: BroadcastPerformanceConfig = None):
        self.config = config or BroadcastPerformanceConfig()
        
        # Connection management
        self.connection_pools: Dict[str, ConnectionPool] = defaultdict(ConnectionPool)
        self.user_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # Message buffering
        self.message_buffer = MessageBuffer(self.config.max_memory_buffer_mb)
        
        # Performance tracking
        self.broadcast_metrics = {
            "total_broadcasts": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "slow_deliveries": 0,
            "average_latency_ms": 0.0,
            "peak_concurrent_connections": 0,
            "memory_usage_mb": 0.0
        }
        
        # Async management
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="broadcast")
        self.active_broadcasts = set()
        self.broadcast_semaphore = asyncio.Semaphore(self.config.max_concurrent_broadcasts)
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup of stale connections and memory."""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                await self._cleanup_stale_connections()
                self._update_memory_metrics()
                gc.collect()  # Force garbage collection
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast cleanup error: {e}")
    
    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale and closed connections."""
        current_time = time.time()
        stale_threshold = 300  # 5 minutes
        
        for pool_id, pool in list(self.connection_pools.items()):
            stale_connections = []
            
            for websocket in list(pool.connections):
                # Check if connection is closed
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    stale_connections.append(websocket)
                    continue
                
                # Check if connection is stale
                last_activity = pool.last_activity.get(websocket, current_time)
                if current_time - last_activity > stale_threshold:
                    stale_connections.append(websocket)
            
            # Remove stale connections
            for websocket in stale_connections:
                await self.remove_connection(websocket, pool_id)
            
            # Remove empty pools
            if not pool.connections:
                del self.connection_pools[pool_id]
    
    def _update_memory_metrics(self) -> None:
        """Update memory usage metrics."""
        buffer_stats = self.message_buffer.get_stats()
        self.broadcast_metrics["memory_usage_mb"] = buffer_stats["size_mb"]
    
    async def add_connection(self, websocket: WebSocket, pool_id: str = "default", 
                           user_id: str = None) -> bool:
        """Add connection to broadcast pool."""
        pool = self.connection_pools[pool_id]
        
        if not pool.add_connection(websocket):
            logger.warning(f"Failed to add connection to pool {pool_id} - pool full")
            return False
        
        if user_id:
            self.user_connections[user_id].add(websocket)
        
        # Update peak connections metric
        total_connections = sum(len(p.connections) for p in self.connection_pools.values())
        if total_connections > self.broadcast_metrics["peak_concurrent_connections"]:
            self.broadcast_metrics["peak_concurrent_connections"] = total_connections
        
        logger.debug(f"Added connection to pool {pool_id}, total: {len(pool.connections)}")
        return True
    
    async def remove_connection(self, websocket: WebSocket, pool_id: str = "default", 
                              user_id: str = None) -> None:
        """Remove connection from broadcast pool."""
        if pool_id in self.connection_pools:
            self.connection_pools[pool_id].remove_connection(websocket)
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def broadcast_to_pool(self, pool_id: str, message: Union[str, Dict[str, Any]], 
                               priority: int = 0) -> BroadcastResult:
        """Broadcast message to all connections in pool."""
        async with self.broadcast_semaphore:
            return await self._execute_broadcast(pool_id, message, priority)
    
    async def _execute_broadcast(self, pool_id: str, message: Union[str, Dict[str, Any]], 
                               priority: int) -> BroadcastResult:
        """Execute broadcast with performance optimization."""
        start_time = time.time()
        self.broadcast_metrics["total_broadcasts"] += 1
        
        # Get target pool
        if pool_id not in self.connection_pools:
            return BroadcastResult(
                total_recipients=0,
                successful_deliveries=0,
                failed_deliveries=0,
                duration_ms=0.0
            )
        
        pool = self.connection_pools[pool_id]
        connections = list(pool.active_connections)  # Copy to avoid modification during iteration
        
        if not connections:
            return BroadcastResult(
                total_recipients=0,
                successful_deliveries=0,
                failed_deliveries=0,
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Prepare message
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = message
        
        # Use batched sending for large recipient lists
        if len(connections) > self.config.max_batch_size:
            result = await self._batched_broadcast(pool, connections, message_str)
        else:
            result = await self._direct_broadcast(pool, connections, message_str)
        
        # Update metrics
        duration_ms = (time.time() - start_time) * 1000
        self._update_broadcast_metrics(result, duration_ms)
        
        result.duration_ms = duration_ms
        return result
    
    async def _batched_broadcast(self, pool: ConnectionPool, connections: List[WebSocket], 
                               message: str) -> BroadcastResult:
        """Broadcast using batched approach for large recipient lists."""
        total_recipients = len(connections)
        successful = 0
        failed = 0
        
        # Split into batches
        batch_size = self.config.max_batch_size
        batches = [connections[i:i + batch_size] for i in range(0, len(connections), batch_size)]
        
        # Process batches concurrently
        batch_tasks = []
        for batch in batches:
            task = self._send_to_batch(pool, batch, message)
            batch_tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Aggregate results
        for result in batch_results:
            if isinstance(result, dict):
                successful += result.get("successful", 0)
                failed += result.get("failed", 0)
            else:
                # Exception occurred
                failed += batch_size
        
        return BroadcastResult(
            total_recipients=total_recipients,
            successful_deliveries=successful,
            failed_deliveries=failed,
            duration_ms=0.0  # Will be set by caller
        )
    
    async def _send_to_batch(self, pool: ConnectionPool, batch: List[WebSocket], 
                           message: str) -> Dict[str, int]:
        """Send message to a batch of connections."""
        successful = 0
        failed = 0
        
        # Create tasks for concurrent sending within batch
        send_tasks = []
        for websocket in batch:
            task = self._send_to_connection(pool, websocket, message)
            send_tasks.append(task)
        
        # Wait for batch to complete with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*send_tasks, return_exceptions=True),
                timeout=self.config.batch_timeout_ms / 1000
            )
            
            for result in results:
                if result is True:
                    successful += 1
                else:
                    failed += 1
                    
        except asyncio.TimeoutError:
            # Timeout - count all as failed
            failed = len(batch)
        
        return {"successful": successful, "failed": failed}
    
    async def _direct_broadcast(self, pool: ConnectionPool, connections: List[WebSocket], 
                              message: str) -> BroadcastResult:
        """Direct broadcast for smaller recipient lists."""
        total_recipients = len(connections)
        
        # Send to all connections concurrently
        send_tasks = []
        for websocket in connections:
            task = self._send_to_connection(pool, websocket, message)
            send_tasks.append(task)
        
        # Wait for all sends to complete
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # Count results
        successful = sum(1 for result in results if result is True)
        failed = total_recipients - successful
        
        return BroadcastResult(
            total_recipients=total_recipients,
            successful_deliveries=successful,
            failed_deliveries=failed,
            duration_ms=0.0  # Will be set by caller
        )
    
    async def _send_to_connection(self, pool: ConnectionPool, websocket: WebSocket, 
                                message: str) -> bool:
        """Send message to individual connection with error handling."""
        try:
            # Check connection state
            if websocket.client_state != WebSocketState.CONNECTED:
                pool.remove_connection(websocket)
                return False
            
            # Send with timeout
            send_start = time.time()
            await asyncio.wait_for(websocket.send_text(message), timeout=1.0)
            send_duration = (time.time() - send_start) * 1000
            
            # Track slow connections
            if send_duration > self.config.slow_client_threshold_ms:
                pool.mark_slow(websocket)
                self.broadcast_metrics["slow_deliveries"] += 1
            
            # Update activity
            pool.last_activity[websocket] = time.time()
            return True
            
        except asyncio.TimeoutError:
            # Slow connection
            pool.mark_slow(websocket)
            self.broadcast_metrics["slow_deliveries"] += 1
            return False
            
        except Exception as e:
            # Connection error
            should_disconnect = pool.mark_failed(websocket)
            if should_disconnect:
                pool.remove_connection(websocket)
                logger.debug(f"Removed failed connection after {pool.failed_counts.get(websocket, 0)} failures")
            
            return False
    
    def _update_broadcast_metrics(self, result: BroadcastResult, duration_ms: float) -> None:
        """Update broadcast performance metrics."""
        self.broadcast_metrics["successful_deliveries"] += result.successful_deliveries
        self.broadcast_metrics["failed_deliveries"] += result.failed_deliveries
        
        # Update average latency (running average)
        current_avg = self.broadcast_metrics["average_latency_ms"]
        total_broadcasts = self.broadcast_metrics["total_broadcasts"]
        
        if total_broadcasts == 1:
            self.broadcast_metrics["average_latency_ms"] = duration_ms
        else:
            self.broadcast_metrics["average_latency_ms"] = (
                (current_avg * (total_broadcasts - 1) + duration_ms) / total_broadcasts
            )
    
    async def broadcast_to_user(self, user_id: str, message: Union[str, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast message to all connections for a specific user."""
        connections = list(self.user_connections.get(user_id, set()))
        
        if not connections:
            return BroadcastResult(
                total_recipients=0,
                successful_deliveries=0,
                failed_deliveries=0,
                duration_ms=0.0
            )
        
        # Create temporary pool for user connections
        temp_pool = ConnectionPool()
        for conn in connections:
            temp_pool.connections.add(conn)
            temp_pool.active_connections.add(conn)
        
        # Prepare message
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = message
        
        # Execute broadcast
        start_time = time.time()
        if len(connections) > self.config.max_batch_size:
            result = await self._batched_broadcast(temp_pool, connections, message_str)
        else:
            result = await self._direct_broadcast(temp_pool, connections, message_str)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def broadcast_to_all(self, message: Union[str, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast message to all connected clients across all pools."""
        start_time = time.time()
        
        # Collect all connections
        all_connections = []
        for pool in self.connection_pools.values():
            all_connections.extend(pool.active_connections)
        
        if not all_connections:
            return BroadcastResult(
                total_recipients=0,
                successful_deliveries=0,
                failed_deliveries=0,
                duration_ms=0.0
            )
        
        # Create temporary pool
        temp_pool = ConnectionPool()
        for conn in all_connections:
            temp_pool.connections.add(conn)
            temp_pool.active_connections.add(conn)
        
        # Prepare message
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = message
        
        # Execute broadcast
        result = await self._batched_broadcast(temp_pool, all_connections, message_str)
        result.duration_ms = (time.time() - start_time) * 1000
        
        # Update global metrics
        self._update_broadcast_metrics(result, result.duration_ms)
        
        return result
    
    def get_pool_stats(self, pool_id: str = None) -> Dict[str, Any]:
        """Get statistics for specific pool or all pools."""
        if pool_id:
            if pool_id in self.connection_pools:
                pool = self.connection_pools[pool_id]
                return {
                    "pool_id": pool_id,
                    **pool.get_stats()
                }
            return {"pool_id": pool_id, "error": "Pool not found"}
        
        # Return stats for all pools
        stats = {}
        for pid, pool in self.connection_pools.items():
            stats[pid] = pool.get_stats()
        
        return stats
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        total_connections = sum(len(p.connections) for p in self.connection_pools.values())
        
        return {
            "broadcast_metrics": self.broadcast_metrics.copy(),
            "connection_stats": {
                "total_connections": total_connections,
                "total_pools": len(self.connection_pools),
                "unique_users": len(self.user_connections)
            },
            "memory_stats": self.message_buffer.get_stats(),
            "performance_targets": {
                "target_latency_ms": self.config.target_latency_ms,
                "current_latency_ms": self.broadcast_metrics["average_latency_ms"],
                "latency_target_met": self.broadcast_metrics["average_latency_ms"] <= self.config.target_latency_ms
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown broadcaster and cleanup resources."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown executor
        self.executor.shutdown(wait=False)
        
        # Clear all data structures
        self.connection_pools.clear()
        self.user_connections.clear()
        self.message_buffer.clear()
        self.active_broadcasts.clear()
        
        logger.info("High-performance broadcaster shutdown completed")


# Global broadcaster instance
_global_broadcaster: Optional[HighPerformanceBroadcaster] = None

def get_global_broadcaster() -> HighPerformanceBroadcaster:
    """Get global broadcaster instance."""
    global _global_broadcaster
    if _global_broadcaster is None:
        _global_broadcaster = HighPerformanceBroadcaster()
    return _global_broadcaster