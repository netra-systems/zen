"""
WebSocketEmitterPool - Object pooling for optimized UserWebSocketEmitter instances.

Business Value Justification:
- Segment: Platform Performance
- Business Goal: Real-time chat responsiveness (<20ms overhead)
- Value Impact: Eliminates object creation overhead for WebSocket emitters
- Strategic Impact: Support 100+ concurrent users without degradation

This pool maintains reusable OptimizedUserWebSocketEmitter instances to minimize
object creation overhead during high-frequency agent-user interactions.
The pool supports configurable sizing and automatic cleanup of idle objects.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Deque
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.factory_performance_config import FactoryPerformanceConfig
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.models.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


@dataclass
class PoolStatistics:
    """Statistics for WebSocket emitter pool performance tracking."""
    total_acquired: int = 0
    total_released: int = 0
    total_created: int = 0
    total_reset: int = 0
    current_active: int = 0
    current_pooled: int = 0
    peak_active: int = 0
    average_acquisition_time_ms: float = 0.0
    cache_hit_rate: float = 0.0


class WebSocketEmitterPool:
    """
    Object pool for OptimizedUserWebSocketEmitter instances.
    
    Manages a pool of reusable emitter objects to minimize allocation overhead
    during high-frequency WebSocket event emission. Uses __slots__ optimization
    and efficient FIFO pooling for maximum performance.
    """
    
    class OptimizedUserWebSocketEmitter:
        """
        Optimized WebSocket emitter with __slots__ and object reuse support.
        
        This class implements the same interface as UserWebSocketEmitter but
        with memory and performance optimizations suitable for high-frequency
        object reuse in a pool.
        """
        
        __slots__ = (
            'user_id', 'thread_id', 'run_id', 'websocket_bridge', 'created_at',
            '_event_count', '_last_event_time', '_is_active', 'request_id',
            'connection_id', 'router', '_acquisition_time'
        )
        
        def __init__(self):
            """Initialize empty emitter for pool use."""
            self.user_id: Optional[str] = None
            self.thread_id: Optional[str] = None
            self.run_id: Optional[str] = None
            self.request_id: Optional[str] = None
            self.connection_id: Optional[str] = None
            self.router: Optional[WebSocketEventRouter] = None
            self.websocket_bridge = None  # Maintained for compatibility
            self.created_at: Optional[datetime] = None
            self._event_count: int = 0
            self._last_event_time: Optional[datetime] = None
            self._is_active: bool = False
            self._acquisition_time: Optional[float] = None
        
        def initialize(self, context: UserExecutionContext, router: WebSocketEventRouter, 
                      connection_id: Optional[str] = None) -> None:
            """Initialize emitter with user context and router.
            
            Args:
                context: User execution context with validated IDs
                router: WebSocket event router for infrastructure
                connection_id: Optional specific connection ID to target
            """
            self.user_id = context.user_id
            self.thread_id = context.thread_id
            self.run_id = context.run_id
            self.request_id = context.request_id
            self.connection_id = connection_id
            self.router = router
            self.created_at = datetime.now(timezone.utc)
            self._event_count = 0
            self._last_event_time = None
            self._is_active = True
            self._acquisition_time = time.perf_counter()
            
            logger.debug(f"OptimizedUserWebSocketEmitter initialized for user {self.user_id[:8]}... "
                        f"(run_id: {self.run_id})")
        
        def reset(self) -> None:
            """Reset emitter state for reuse in pool."""
            self.user_id = None
            self.thread_id = None
            self.run_id = None
            self.request_id = None
            self.connection_id = None
            self.router = None
            self.websocket_bridge = None
            self.created_at = None
            self._event_count = 0
            self._last_event_time = None
            self._is_active = False
            self._acquisition_time = None
        
        async def notify_agent_started(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
            """Send agent started event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": "agent_started",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "started",
                    "metadata": metadata or {},
                    "message": f"{agent_name} has started processing your request"
                }
            }
            
            return await self._send_event(event, "agent_started")
        
        async def notify_agent_thinking(self, agent_name: str, thought: str, 
                                      step: Optional[str] = None) -> bool:
            """Send thinking event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": "agent_thinking",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "thought": thought,
                    "step": step,
                    "message": f"{agent_name} is analyzing: {thought[:100]}..."
                }
            }
            
            return await self._send_event(event, "agent_thinking")
        
        async def notify_tool_executing(self, agent_name: str, tool_name: str, 
                                      tool_input: Optional[Dict[str, Any]] = None) -> bool:
            """Send tool execution event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            # Sanitize tool input for security
            safe_input = self._sanitize_tool_input(tool_input) if tool_input else {}
            
            event = {
                "type": "tool_executing",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tool_name": tool_name,
                    "tool_input": safe_input,
                    "message": f"{agent_name} is using {tool_name}"
                }
            }
            
            return await self._send_event(event, "tool_executing")
        
        async def notify_tool_completed(self, agent_name: str, tool_name: str, 
                                      success: bool, result_summary: Optional[str] = None) -> bool:
            """Send tool completion event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": "tool_completed",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tool_name": tool_name,
                    "success": success,
                    "result_summary": result_summary,
                    "message": f"{agent_name} {'completed' if success else 'failed to complete'} {tool_name}"
                }
            }
            
            return await self._send_event(event, "tool_completed")
        
        async def notify_agent_completed(self, agent_name: str, result: Dict[str, Any], 
                                       success: bool = True) -> bool:
            """Send agent completion event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            # Sanitize result for user consumption
            safe_result = self._sanitize_agent_result(result)
            
            event = {
                "type": "agent_completed",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "success": success,
                    "result": safe_result,
                    "message": f"{agent_name} has {'completed' if success else 'failed'} processing your request"
                }
            }
            
            return await self._send_event(event, "agent_completed")
        
        async def notify_agent_error(self, agent_name: str, error_type: str, 
                                   error_message: str, recoverable: bool = False) -> bool:
            """Send agent error event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": "agent_error",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "error_type": error_type,
                    "error_message": error_message,
                    "recoverable": recoverable,
                    "message": f"{agent_name} encountered an error: {error_message}"
                }
            }
            
            return await self._send_event(event, "agent_error")
        
        async def notify_progress_update(self, agent_name: str, progress_percentage: float, 
                                       current_step: str, estimated_completion: Optional[str] = None) -> bool:
            """Send progress update event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": "progress_update",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "progress_percentage": min(100, max(0, progress_percentage)),
                    "current_step": current_step,
                    "estimated_completion": estimated_completion,
                    "message": f"{agent_name}: {current_step} ({progress_percentage:.1f}% complete)"
                }
            }
            
            return await self._send_event(event, "progress_update")
        
        async def notify_custom(self, event_type: str, payload: Dict[str, Any], 
                              agent_name: Optional[str] = None) -> bool:
            """Send custom event to this user only."""
            if not self._is_active or not self.router:
                return False
                
            event = {
                "type": event_type,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload
            }
            
            return await self._send_event(event, event_type)
        
        def get_stats(self) -> Dict[str, Any]:
            """Get emitter statistics."""
            uptime = 0.0
            if self.created_at:
                uptime = (datetime.now(timezone.utc) - self.created_at).total_seconds()
            
            return {
                "user_id": self.user_id[:8] + "..." if self.user_id else None,
                "run_id": self.run_id,
                "events_sent": self._event_count,
                "uptime_seconds": uptime,
                "is_active": self._is_active,
                "connection_id": self.connection_id
            }
        
        def __str__(self) -> str:
            """String representation for debugging."""
            user_display = self.user_id[:8] + "..." if self.user_id else "None"
            return f"OptimizedUserWebSocketEmitter(user={user_display}, run_id={self.run_id})"
        
        # Private helper methods
        
        async def _send_event(self, event: Dict[str, Any], event_type: str) -> bool:
            """Send event through the router with proper error handling."""
            if not self.router or not self._is_active:
                return False
                
            try:
                # Add request_id for complete traceability
                event["request_id"] = self.request_id
                
                if self.connection_id:
                    # Send to specific connection
                    success = await self.router.route_event(self.user_id, self.connection_id, event)
                else:
                    # Broadcast to all user connections
                    sent_count = await self.router.broadcast_to_user(self.user_id, event)
                    success = sent_count > 0
                
                if success:
                    self._event_count += 1
                    self._last_event_time = datetime.now(timezone.utc)
                    logger.debug(f"Sent {event_type} event to user {self.user_id[:8]}... (run_id: {self.run_id})")
                else:
                    logger.warning(f"Failed to send {event_type} event to user {self.user_id[:8]}... (run_id: {self.run_id})")
                
                return success
                
            except Exception as e:
                logger.error(f"Error sending {event_type} event to user {self.user_id[:8]}...: {e}")
                return False
        
        def _sanitize_tool_input(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
            """Sanitize tool input for user-facing events."""
            sensitive_keys = {'password', 'token', 'key', 'secret', 'api_key', 'auth'}
            sanitized = {}
            
            for key, value in tool_input.items():
                if key.lower() in sensitive_keys:
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, str) and len(value) > 200:
                    sanitized[key] = value[:200] + "..."
                elif isinstance(value, (dict, list)) and len(str(value)) > 500:
                    sanitized[key] = "[LARGE_DATA]"
                else:
                    sanitized[key] = value
            
            return sanitized
        
        def _sanitize_agent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
            """Sanitize agent results for user consumption."""
            # Remove internal keys
            internal_keys = {'_internal', 'debug_info', 'system_context', 'raw_response'}
            
            sanitized = {}
            for key, value in result.items():
                if key not in internal_keys:
                    if isinstance(value, str) and len(value) > 1000:
                        sanitized[key] = value[:1000] + "..."
                    else:
                        sanitized[key] = value
            
            return sanitized
    
    def __init__(self, config: Optional[FactoryPerformanceConfig] = None):
        """Initialize WebSocket emitter pool with configuration.
        
        Args:
            config: Optional factory performance configuration
        """
        self.config = config or FactoryPerformanceConfig()
        
        # Pool configuration from config
        self.initial_size = self.config.pool_initial_size
        self.max_size = self.config.pool_max_size
        self.cleanup_interval = self.config.pool_cleanup_interval
        self.reuse_timeout = self.config.pool_reuse_timeout
        
        # Pool state
        self._pool: Deque[WebSocketEmitterPool.OptimizedUserWebSocketEmitter] = deque()
        self._active_emitters: Dict[str, WebSocketEmitterPool.OptimizedUserWebSocketEmitter] = {}
        self._lock = asyncio.Lock()
        self._stats = PoolStatistics()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Initialize pool with empty emitters
        self._create_initial_pool()
        
        # Start cleanup task
        if self.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"WebSocketEmitterPool initialized with {self.initial_size} emitters "
                   f"(max_size: {self.max_size})")
    
    async def acquire(self, context: UserExecutionContext, router: WebSocketEventRouter,
                     connection_id: Optional[str] = None) -> OptimizedUserWebSocketEmitter:
        """Acquire an emitter from the pool.
        
        Args:
            context: User execution context
            router: WebSocket event router
            connection_id: Optional specific connection ID
            
        Returns:
            Initialized OptimizedUserWebSocketEmitter instance
        """
        start_time = time.perf_counter()
        
        async with self._lock:
            emitter = None
            
            # Try to get from pool
            if self._pool:
                emitter = self._pool.popleft()
                self._stats.cache_hit_rate = (
                    (self._stats.cache_hit_rate * self._stats.total_acquired + 1.0) /
                    (self._stats.total_acquired + 1)
                )
            else:
                # Create new if pool is empty and under max size
                if len(self._active_emitters) < self.max_size:
                    emitter = self.OptimizedUserWebSocketEmitter()
                    self._stats.total_created += 1
                else:
                    # Pool exhausted - create temporary emitter (will not be pooled)
                    logger.warning(f"WebSocket emitter pool exhausted (max_size: {self.max_size}), "
                                 "creating temporary emitter")
                    emitter = self.OptimizedUserWebSocketEmitter()
            
            if emitter:
                # Initialize emitter
                emitter.initialize(context, router, connection_id)
                
                # Track active emitter
                emitter_key = f"{context.user_id}:{context.run_id}"
                self._active_emitters[emitter_key] = emitter
                
                # Update statistics
                self._stats.total_acquired += 1
                self._stats.current_active = len(self._active_emitters)
                self._stats.current_pooled = len(self._pool)
                if self._stats.current_active > self._stats.peak_active:
                    self._stats.peak_active = self._stats.current_active
                
                acquisition_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
                self._stats.average_acquisition_time_ms = (
                    (self._stats.average_acquisition_time_ms * (self._stats.total_acquired - 1) + acquisition_time) /
                    self._stats.total_acquired
                )
                
                logger.debug(f"Acquired WebSocket emitter for user {context.user_id[:8]}... "
                           f"(run_id: {context.run_id}, acquisition_time: {acquisition_time:.2f}ms)")
                
                return emitter
            else:
                raise RuntimeError("Failed to acquire WebSocket emitter from pool")
    
    async def release(self, emitter: OptimizedUserWebSocketEmitter) -> None:
        """Release an emitter back to the pool.
        
        Args:
            emitter: The emitter to release
        """
        if not emitter or not emitter.user_id:
            return
        
        async with self._lock:
            # Remove from active tracking
            emitter_key = f"{emitter.user_id}:{emitter.run_id}"
            if emitter_key in self._active_emitters:
                del self._active_emitters[emitter_key]
            
            # Reset emitter state
            emitter.reset()
            self._stats.total_reset += 1
            
            # Return to pool if there's space
            if len(self._pool) < self.max_size:
                self._pool.append(emitter)
                logger.debug(f"Released WebSocket emitter back to pool")
            else:
                # Pool is full, let emitter be garbage collected
                logger.debug(f"WebSocket emitter pool full, emitter will be garbage collected")
            
            # Update statistics
            self._stats.total_released += 1
            self._stats.current_active = len(self._active_emitters)
            self._stats.current_pooled = len(self._pool)
    
    def get_statistics(self) -> PoolStatistics:
        """Get current pool statistics.
        
        Returns:
            Current pool statistics
        """
        return self._stats
    
    async def cleanup_inactive_emitters(self) -> int:
        """Clean up inactive emitters and return count cleaned.
        
        Returns:
            Number of emitters cleaned up
        """
        if not self.reuse_timeout:
            return 0
        
        cleaned_count = 0
        current_time = time.perf_counter()
        
        async with self._lock:
            # Check active emitters for timeout
            expired_keys = []
            for key, emitter in self._active_emitters.items():
                if (emitter._acquisition_time and 
                    current_time - emitter._acquisition_time > self.reuse_timeout):
                    expired_keys.append(key)
            
            # Clean up expired emitters
            for key in expired_keys:
                emitter = self._active_emitters.pop(key, None)
                if emitter:
                    emitter.reset()
                    # Don't return to pool - let it be GC'd
                    cleaned_count += 1
            
            # Update statistics
            self._stats.current_active = len(self._active_emitters)
            self._stats.current_pooled = len(self._pool)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} inactive WebSocket emitters")
        
        return cleaned_count
    
    async def shutdown(self) -> None:
        """Shutdown the pool and cleanup resources."""
        logger.info("Shutting down WebSocketEmitterPool...")
        
        self._shutdown = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            # Reset all active emitters
            for emitter in self._active_emitters.values():
                emitter.reset()
            
            # Clear all pools
            while self._pool:
                emitter = self._pool.popleft()
                emitter.reset()
            
            self._active_emitters.clear()
            self._stats.current_active = 0
            self._stats.current_pooled = 0
        
        logger.info("WebSocketEmitterPool shutdown complete")
    
    def _create_initial_pool(self) -> None:
        """Create initial pool of empty emitters."""
        for _ in range(self.initial_size):
            emitter = self.OptimizedUserWebSocketEmitter()
            self._pool.append(emitter)
            self._stats.total_created += 1
        
        self._stats.current_pooled = len(self._pool)
        logger.debug(f"Created initial pool of {self.initial_size} WebSocket emitters")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for inactive emitters."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._shutdown:
                    await self.cleanup_inactive_emitters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket emitter pool cleanup loop: {e}")
                # Continue the loop despite errors
                await asyncio.sleep(10)  # Short delay before retrying
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"WebSocketEmitterPool(active: {self._stats.current_active}, "
                f"pooled: {self._stats.current_pooled}, "
                f"max_size: {self.max_size})")


# Module-level pool instance for global use
_global_pool: Optional[WebSocketEmitterPool] = None


async def get_websocket_emitter_pool(config: Optional[FactoryPerformanceConfig] = None) -> WebSocketEmitterPool:
    """Get the global WebSocket emitter pool instance.
    
    Args:
        config: Optional factory performance configuration
        
    Returns:
        Global WebSocketEmitterPool instance
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = WebSocketEmitterPool(config)
    return _global_pool


async def shutdown_websocket_emitter_pool() -> None:
    """Shutdown the global WebSocket emitter pool."""
    global _global_pool
    if _global_pool:
        await _global_pool.shutdown()
        _global_pool = None