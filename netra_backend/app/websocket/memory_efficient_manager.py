"""Memory-Efficient WebSocket Manager for High Load.

Business Value Justification (BVJ):
- Segment: Enterprise  
- Business Goal: Stability - Prevent memory leaks and ensure efficient resource usage
- Value Impact: Enables handling of 1000+ concurrent connections without memory issues
- Strategic Impact: $60K MRR - Memory efficiency for enterprise service reliability

This module provides:
- Memory-efficient connection tracking with weak references
- Automatic garbage collection and cleanup
- Memory usage monitoring and alerts
- Efficient message buffering with size limits
- Connection pooling with memory limits
- CPU usage optimization under high load
"""

import asyncio
import gc
import time
import weakref
import psutil
from typing import Dict, Any, List, Set, Optional, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import sys

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MemoryMetrics:
    """Memory usage metrics for monitoring."""
    
    process_memory_mb: float = 0.0
    websocket_memory_mb: float = 0.0
    buffer_memory_mb: float = 0.0
    total_connections: int = 0
    active_connections: int = 0
    memory_per_connection_kb: float = 0.0
    gc_collections: int = 0
    last_gc_time: float = 0.0
    
    def calculate_efficiency(self) -> Dict[str, float]:
        """Calculate memory efficiency metrics."""
        return {
            "memory_per_connection_kb": self.memory_per_connection_kb,
            "buffer_efficiency": (self.buffer_memory_mb / max(self.process_memory_mb, 1)) * 100,
            "websocket_efficiency": (self.websocket_memory_mb / max(self.process_memory_mb, 1)) * 100,
            "total_efficiency": ((self.websocket_memory_mb + self.buffer_memory_mb) / max(self.process_memory_mb, 1)) * 100
        }


class WeakConnectionRegistry:
    """Weak reference-based connection registry to prevent memory leaks."""
    
    def __init__(self):
        # Use WeakSet to automatically remove garbage collected connections
        from weakref import WeakSet
        self._connections: WeakSet = WeakSet()
        self._user_connections: Dict[str, WeakSet] = defaultdict(lambda: WeakSet())
        self._connection_metadata: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._cleanup_callbacks: List[Callable] = []
        
        # Metrics
        self.connection_count = 0
        self.user_count = 0
        self.last_cleanup = time.time()
    
    def add_connection(self, websocket: WebSocket, user_id: str = None, 
                      metadata: Dict[str, Any] = None) -> bool:
        """Add connection with weak reference tracking."""
        try:
            self._connections.add(websocket)
            
            if user_id:
                self._user_connections[user_id].add(websocket)
            
            if metadata:
                self._connection_metadata[websocket] = metadata.copy()
            
            self.connection_count = len(self._connections)
            self.user_count = len(self._user_connections)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add connection: {e}")
            return False
    
    def remove_connection(self, websocket: WebSocket, user_id: str = None) -> bool:
        """Remove connection and cleanup references."""
        try:
            self._connections.discard(websocket)
            
            if user_id and user_id in self._user_connections:
                self._user_connections[user_id].discard(websocket)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]
            
            # WeakKeyDictionary automatically removes entries when keys are garbage collected
            self._connection_metadata.pop(websocket, None)
            
            self.connection_count = len(self._connections)
            self.user_count = len(self._user_connections)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove connection: {e}")
            return False
    
    def get_connections(self) -> List[WebSocket]:
        """Get list of active connections."""
        # Filter out disconnected connections
        active = []
        for conn in list(self._connections):
            try:
                if conn.client_state == WebSocketState.CONNECTED:
                    active.append(conn)
                else:
                    self._connections.discard(conn)
            except Exception:
                self._connections.discard(conn)
        
        self.connection_count = len(active)
        return active
    
    def get_user_connections(self, user_id: str) -> List[WebSocket]:
        """Get connections for specific user."""
        if user_id not in self._user_connections:
            return []
        
        active = []
        user_conns = self._user_connections[user_id]
        
        for conn in list(user_conns):
            try:
                if conn.client_state == WebSocketState.CONNECTED:
                    active.append(conn)
                else:
                    user_conns.discard(conn)
            except Exception:
                user_conns.discard(conn)
        
        if not user_conns:
            del self._user_connections[user_id]
            self.user_count = len(self._user_connections)
        
        return active
    
    def cleanup_stale_connections(self) -> int:
        """Clean up stale and disconnected connections."""
        cleaned = 0
        current_time = time.time()
        
        # Clean up main connections
        stale_connections = []
        for conn in list(self._connections):
            try:
                if conn.client_state != WebSocketState.CONNECTED:
                    stale_connections.append(conn)
            except Exception:
                stale_connections.append(conn)
        
        for conn in stale_connections:
            self._connections.discard(conn)
            cleaned += 1
        
        # Clean up user connections
        empty_users = []
        for user_id, user_conns in list(self._user_connections.items()):
            stale_user_conns = []
            for conn in list(user_conns):
                try:
                    if conn.client_state != WebSocketState.CONNECTED:
                        stale_user_conns.append(conn)
                except Exception:
                    stale_user_conns.append(conn)
            
            for conn in stale_user_conns:
                user_conns.discard(conn)
                cleaned += 1
            
            if not user_conns:
                empty_users.append(user_id)
        
        for user_id in empty_users:
            del self._user_connections[user_id]
        
        self.connection_count = len(self._connections)
        self.user_count = len(self._user_connections)
        self.last_cleanup = current_time
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_connections": self.connection_count,
            "unique_users": self.user_count,
            "metadata_entries": len(self._connection_metadata),
            "last_cleanup": self.last_cleanup,
            "avg_connections_per_user": self.connection_count / max(self.user_count, 1)
        }


class MemoryEfficientBuffer:
    """Memory-efficient message buffer with automatic cleanup."""
    
    def __init__(self, max_size_mb: int = 50, max_messages: int = 10000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_messages = max_messages
        
        # Use deque for efficient append/pop operations
        self.messages: deque = deque(maxlen=max_messages)
        self.message_sizes: deque = deque(maxlen=max_messages)
        
        # Current state
        self.current_size_bytes = 0
        self.total_messages_processed = 0
        self.messages_dropped = 0
        
        # Compression for large messages
        self.compression_threshold = 1024  # 1KB
        self.compression_enabled = True
    
    def add_message(self, message: Union[str, Dict[str, Any]], compress: bool = True) -> bool:
        """Add message to buffer with memory management."""
        # Serialize message
        if isinstance(message, dict):
            message_str = json.dumps(message, separators=(',', ':'))  # Compact JSON
        else:
            message_str = str(message)
        
        # Compress large messages if enabled
        if (compress and self.compression_enabled and 
            len(message_str) > self.compression_threshold):
            try:
                import gzip
                message_bytes = message_str.encode('utf-8')
                compressed_bytes = gzip.compress(message_bytes)
                if len(compressed_bytes) < len(message_bytes):
                    message_str = compressed_bytes.hex()  # Store as hex string
                    is_compressed = True
                else:
                    is_compressed = False
            except Exception:
                is_compressed = False
        else:
            is_compressed = False
        
        message_size = len(message_str.encode('utf-8'))
        
        # Check memory limits
        if self.current_size_bytes + message_size > self.max_size_bytes:
            # Try to make space by removing old messages
            space_freed = self._free_memory_space(message_size)
            if space_freed < message_size:
                self.messages_dropped += 1
                return False
        
        # Add message
        message_entry = {
            "content": message_str,
            "size": message_size,
            "timestamp": time.time(),
            "compressed": is_compressed
        }
        
        # Use maxlen feature of deque for automatic size management
        if len(self.messages) >= self.max_messages:
            # Remove oldest message
            oldest = self.messages[0]
            self.current_size_bytes -= oldest["size"]
        
        self.messages.append(message_entry)
        self.message_sizes.append(message_size)
        self.current_size_bytes += message_size
        self.total_messages_processed += 1
        
        return True
    
    def _free_memory_space(self, needed_size: int) -> int:
        """Free memory space by removing old messages."""
        freed = 0
        
        while self.messages and freed < needed_size:
            oldest = self.messages.popleft()
            self.message_sizes.popleft()
            freed += oldest["size"]
            self.current_size_bytes -= oldest["size"]
        
        return freed
    
    def get_messages(self, count: int = None, decompress: bool = True) -> List[str]:
        """Get messages from buffer."""
        if count is None:
            count = len(self.messages)
        
        messages = []
        for _ in range(min(count, len(self.messages))):
            if not self.messages:
                break
            
            entry = self.messages.popleft()
            self.message_sizes.popleft()
            self.current_size_bytes -= entry["size"]
            
            message_content = entry["content"]
            
            # Decompress if needed
            if decompress and entry.get("compressed", False):
                try:
                    import gzip
                    compressed_bytes = bytes.fromhex(message_content)
                    decompressed_bytes = gzip.decompress(compressed_bytes)
                    message_content = decompressed_bytes.decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to decompress message: {e}")
            
            messages.append(message_content)
        
        return messages
    
    def clear(self) -> None:
        """Clear all messages and reset state."""
        self.messages.clear()
        self.message_sizes.clear()
        self.current_size_bytes = 0
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage statistics."""
        return {
            "current_size_mb": self.current_size_bytes / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "utilization_percent": (self.current_size_bytes / self.max_size_bytes) * 100,
            "message_count": len(self.messages),
            "max_messages": self.max_messages,
            "average_message_size": (
                self.current_size_bytes / max(len(self.messages), 1)
            ),
            "total_processed": self.total_messages_processed,
            "messages_dropped": self.messages_dropped,
            "drop_rate": (self.messages_dropped / max(self.total_messages_processed, 1)) * 100
        }


class MemoryMonitor:
    """Monitor and manage memory usage."""
    
    def __init__(self, check_interval: int = 30, memory_limit_mb: int = 1000):
        self.check_interval = check_interval
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Memory tracking
        self.memory_history: deque = deque(maxlen=100)
        self.gc_history: deque = deque(maxlen=50)
        
        # Callbacks for memory pressure
        self.memory_pressure_callbacks: List[Callable] = []
        self.critical_memory_callbacks: List[Callable] = []
        
        # Thresholds
        self.warning_threshold = 0.8  # 80% of limit
        self.critical_threshold = 0.95  # 95% of limit
    
    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main memory monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_memory_usage()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _check_memory_usage(self) -> None:
        """Check current memory usage and take action if needed."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            current_memory = memory_info.rss
            memory_percent = (current_memory / self.memory_limit_bytes) * 100
            
            # Record memory usage
            memory_record = {
                "timestamp": time.time(),
                "memory_bytes": current_memory,
                "memory_mb": current_memory / (1024 * 1024),
                "memory_percent": memory_percent,
                "available_memory": psutil.virtual_memory().available
            }
            self.memory_history.append(memory_record)
            
            # Check thresholds
            if memory_percent >= self.critical_threshold * 100:
                await self._handle_critical_memory()
            elif memory_percent >= self.warning_threshold * 100:
                await self._handle_memory_pressure()
            
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
    
    async def _handle_memory_pressure(self) -> None:
        """Handle memory pressure situation."""
        logger.warning("Memory pressure detected, triggering cleanup")
        
        # Force garbage collection
        await self._force_garbage_collection()
        
        # Call registered callbacks
        for callback in self.memory_pressure_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Memory pressure callback failed: {e}")
    
    async def _handle_critical_memory(self) -> None:
        """Handle critical memory situation."""
        logger.error("Critical memory usage detected, aggressive cleanup")
        
        # Aggressive garbage collection
        await self._force_garbage_collection(aggressive=True)
        
        # Call critical callbacks
        for callback in self.critical_memory_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Critical memory callback failed: {e}")
    
    async def _force_garbage_collection(self, aggressive: bool = False) -> None:
        """Force garbage collection."""
        start_time = time.time()
        
        # Standard garbage collection
        collected = gc.collect()
        
        if aggressive:
            # Multiple rounds of collection
            for _ in range(3):
                collected += gc.collect()
        
        gc_time = time.time() - start_time
        
        # Record GC activity
        gc_record = {
            "timestamp": time.time(),
            "collected_objects": collected,
            "gc_time_ms": gc_time * 1000,
            "aggressive": aggressive
        }
        self.gc_history.append(gc_record)
        
        logger.info(f"Garbage collection completed: {collected} objects in {gc_time:.3f}s")
    
    def register_memory_pressure_callback(self, callback: Callable) -> None:
        """Register callback for memory pressure events."""
        self.memory_pressure_callbacks.append(callback)
    
    def register_critical_memory_callback(self, callback: Callable) -> None:
        """Register callback for critical memory events."""
        self.critical_memory_callbacks.append(callback)
    
    def get_memory_metrics(self) -> MemoryMetrics:
        """Get current memory metrics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            metrics = MemoryMetrics(
                process_memory_mb=memory_info.rss / (1024 * 1024),
                gc_collections=len(self.gc_history),
                last_gc_time=self.gc_history[-1]["timestamp"] if self.gc_history else 0.0
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get memory metrics: {e}")
            return MemoryMetrics()
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        current_metrics = self.get_memory_metrics()
        
        report = {
            "current_metrics": current_metrics.__dict__,
            "monitoring_active": self.monitoring_active,
            "memory_limit_mb": self.memory_limit_bytes / (1024 * 1024),
            "thresholds": {
                "warning_percent": self.warning_threshold * 100,
                "critical_percent": self.critical_threshold * 100
            }
        }
        
        # Recent memory history
        if self.memory_history:
            recent_memory = list(self.memory_history)[-10:]
            report["recent_memory"] = recent_memory
            
            # Calculate trends
            if len(recent_memory) >= 2:
                memory_trend = recent_memory[-1]["memory_mb"] - recent_memory[0]["memory_mb"]
                report["memory_trend_mb"] = memory_trend
        
        # Recent GC history
        if self.gc_history:
            report["recent_gc"] = list(self.gc_history)[-5:]
            total_collected = sum(gc["collected_objects"] for gc in self.gc_history)
            report["total_gc_collected"] = total_collected
        
        return report


class MemoryEfficientWebSocketManager:
    """Memory-efficient WebSocket manager for high load scenarios."""
    
    def __init__(self, memory_limit_mb: int = 1000):
        # Core components
        self.connection_registry = WeakConnectionRegistry()
        self.message_buffer = MemoryEfficientBuffer(max_size_mb=memory_limit_mb // 4)
        self.memory_monitor = MemoryMonitor(memory_limit_mb=memory_limit_mb)
        
        # Configuration
        self.memory_limit_mb = memory_limit_mb
        self.cleanup_interval = 60  # seconds
        
        # Performance tracking
        self.performance_metrics = {
            "connections_added": 0,
            "connections_removed": 0,
            "messages_processed": 0,
            "memory_cleanups": 0,
            "gc_triggered": 0
        }
        
        # Register memory callbacks
        self.memory_monitor.register_memory_pressure_callback(self._handle_memory_pressure)
        self.memory_monitor.register_critical_memory_callback(self._handle_critical_memory)
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self._start_background_tasks()
    
    def _start_background_tasks(self) -> None:
        """Start background cleanup and monitoring tasks."""
        self.memory_monitor.start_monitoring()
        
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def _perform_cleanup(self) -> None:
        """Perform regular cleanup operations."""
        # Clean up stale connections
        cleaned_connections = self.connection_registry.cleanup_stale_connections()
        
        # Force garbage collection if needed
        memory_metrics = self.memory_monitor.get_memory_metrics()
        if memory_metrics.process_memory_mb > self.memory_limit_mb * 0.7:
            await self.memory_monitor._force_garbage_collection()
            self.performance_metrics["gc_triggered"] += 1
        
        if cleaned_connections > 0:
            self.performance_metrics["memory_cleanups"] += 1
            logger.debug(f"Cleaned up {cleaned_connections} stale connections")
    
    async def _handle_memory_pressure(self) -> None:
        """Handle memory pressure by aggressive cleanup."""
        # Clear old messages from buffer
        self.message_buffer.clear()
        
        # Clean up stale connections
        self.connection_registry.cleanup_stale_connections()
        
        # Update metrics
        self.performance_metrics["memory_cleanups"] += 1
        
        logger.warning("Memory pressure cleanup completed")
    
    async def _handle_critical_memory(self) -> None:
        """Handle critical memory situation."""
        # Aggressive cleanup
        await self._handle_memory_pressure()
        
        # Force immediate garbage collection
        await self.memory_monitor._force_garbage_collection(aggressive=True)
        
        logger.error("Critical memory cleanup completed")
    
    async def add_connection(self, websocket: WebSocket, user_id: str = None) -> bool:
        """Add connection with memory-efficient tracking."""
        # Check memory limits before adding
        memory_metrics = self.memory_monitor.get_memory_metrics()
        if memory_metrics.process_memory_mb > self.memory_limit_mb * 0.9:
            logger.warning("Memory limit approaching, rejecting new connection")
            return False
        
        # Add to registry
        metadata = {
            "connected_at": time.time(),
            "last_activity": time.time(),
            "message_count": 0
        }
        
        success = self.connection_registry.add_connection(websocket, user_id, metadata)
        if success:
            self.performance_metrics["connections_added"] += 1
        
        return success
    
    async def remove_connection(self, websocket: WebSocket, user_id: str = None) -> bool:
        """Remove connection and cleanup resources."""
        success = self.connection_registry.remove_connection(websocket, user_id)
        if success:
            self.performance_metrics["connections_removed"] += 1
        
        return success
    
    async def broadcast_message(self, message: Union[str, Dict[str, Any]], 
                              target_users: List[str] = None) -> Dict[str, Any]:
        """Broadcast message with memory-efficient processing."""
        start_time = time.time()
        
        # Get target connections
        if target_users:
            connections = []
            for user_id in target_users:
                connections.extend(self.connection_registry.get_user_connections(user_id))
        else:
            connections = self.connection_registry.get_connections()
        
        if not connections:
            return {
                "sent": 0,
                "failed": 0,
                "duration_ms": 0,
                "memory_used_mb": 0
            }
        
        # Add to buffer for processing
        message_added = self.message_buffer.add_message(message)
        if not message_added:
            logger.warning("Failed to add message to buffer - memory limit reached")
            return {
                "sent": 0,
                "failed": len(connections),
                "duration_ms": (time.time() - start_time) * 1000,
                "memory_used_mb": 0,
                "error": "buffer_full"
            }
        
        # Process message broadcasting
        sent = 0
        failed = 0
        
        # Prepare message
        if isinstance(message, dict):
            message_str = json.dumps(message, separators=(',', ':'))
        else:
            message_str = str(message)
        
        # Send to connections in batches to control memory usage
        batch_size = 100
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]
            
            # Send batch concurrently
            tasks = []
            for conn in batch:
                task = self._send_to_connection(conn, message_str)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if result is True:
                    sent += 1
                else:
                    failed += 1
            
            # Small delay between batches to prevent overwhelming
            if i + batch_size < len(connections):
                await asyncio.sleep(0.001)
        
        # Update metrics
        self.performance_metrics["messages_processed"] += 1
        
        # Calculate memory usage
        buffer_stats = self.message_buffer.get_memory_usage()
        
        return {
            "sent": sent,
            "failed": failed,
            "duration_ms": (time.time() - start_time) * 1000,
            "memory_used_mb": buffer_stats["current_size_mb"],
            "total_recipients": len(connections)
        }
    
    async def _send_to_connection(self, websocket: WebSocket, message: str) -> bool:
        """Send message to individual connection."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
                return True
            else:
                return False
        except Exception as e:
            logger.debug(f"Failed to send message to connection: {e}")
            return False
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        registry_stats = self.connection_registry.get_stats()
        buffer_stats = self.message_buffer.get_memory_usage()
        memory_report = self.memory_monitor.get_memory_report()
        
        return {
            "connections": registry_stats,
            "message_buffer": buffer_stats,
            "memory": memory_report,
            "performance": self.performance_metrics.copy(),
            "configuration": {
                "memory_limit_mb": self.memory_limit_mb,
                "cleanup_interval": self.cleanup_interval,
                "monitoring_active": self.memory_monitor.monitoring_active
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown manager and cleanup resources."""
        # Stop monitoring
        await self.memory_monitor.stop_monitoring()
        
        # Cancel cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all buffers
        self.message_buffer.clear()
        
        # Final garbage collection
        gc.collect()
        
        logger.info("Memory-efficient WebSocket manager shutdown completed")