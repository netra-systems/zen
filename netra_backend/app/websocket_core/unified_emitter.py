"""
UnifiedWebSocketEmitter - THE ONLY emitter implementation

MISSION CRITICAL: Preserves ALL 5 critical events for chat value delivery.
Never remove or bypass these events as they enable the core business value.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Value Delivery & User Trust
- Value Impact: Ensures 100% critical event delivery to users
- Strategic Impact: Single emitter pattern reduces bugs and improves reliability

Consolidates:
- WebSocketEventEmitter
- IsolatedWebSocketEventEmitter  
- UserWebSocketEmitter (all variants)
- OptimizedUserWebSocketEmitter
- EmitterPool patterns

Critical Events (NEVER REMOVE):
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - Response ready notification
"""

import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from datetime import datetime
from dataclasses import dataclass, field
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.models.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


@dataclass
class EmitterMetrics:
    """Metrics tracking for emitter performance."""
    total_events: int = 0
    critical_events: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0
    last_event_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class UnifiedWebSocketEmitter:
    """
    THE ONLY emitter - preserves ALL critical events.
    
    Features:
    - Guaranteed delivery of 5 critical events
    - User isolation (events only go to intended user)
    - Retry logic with exponential backoff
    - Backward compatibility with all emitter variants
    - Performance metrics tracking
    - Pool integration support
    """
    
    # NEVER REMOVE THESE EVENTS - They enable chat business value
    CRITICAL_EVENTS = [
        'agent_started',
        'agent_thinking',
        'tool_executing',
        'tool_completed',
        'agent_completed'
    ]
    
    # Retry configuration for critical events
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 0.1  # 100ms
    RETRY_MAX_DELAY = 2.0   # 2 seconds
    
    def __init__(
        self,
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ):
        """
        Initialize emitter for specific user.
        
        Args:
            manager: UnifiedWebSocketManager instance
            user_id: User ID this emitter serves
            context: Optional execution context for additional metadata
        """
        self.manager = manager
        self.user_id = user_id
        self.context = context
        
        # Metrics tracking
        self.metrics = EmitterMetrics()
        self.metrics.critical_events = {event: 0 for event in self.CRITICAL_EVENTS}
        
        # Event buffer for batching (future optimization)
        self._event_buffer: List[Dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        
        # Validate critical events are available
        self._validate_critical_events()
        
        logger.info(f"UnifiedWebSocketEmitter created for user {user_id}")
    
    def _validate_critical_events(self):
        """
        Ensure critical event methods are NEVER removed.
        This is a safety net to prevent accidental removal.
        """
        for event in self.CRITICAL_EVENTS:
            method_name = f'emit_{event}'
            if not hasattr(self, method_name):
                # Auto-generate if missing (safety net)
                def make_emit_method(evt):
                    async def emit_method(data):
                        await self._emit_critical(evt, data)
                    return emit_method
                
                setattr(self, method_name, make_emit_method(event))
                logger.warning(f"Auto-generated missing critical method: {method_name}")
    
    async def emit_agent_started(self, data: Dict[str, Any]):
        """
        CRITICAL EVENT: Agent started processing.
        User must see that their request is being processed.
        
        Args:
            data: Event data including agent name, run_id, etc.
        """
        await self._emit_critical('agent_started', data)
    
    async def emit_agent_thinking(self, data: Dict[str, Any]):
        """
        CRITICAL EVENT: Agent reasoning visible.
        Shows the AI is actively working on the problem.
        
        Args:
            data: Event data including thought content
        """
        await self._emit_critical('agent_thinking', data)
    
    async def emit_tool_executing(self, data: Dict[str, Any]):
        """
        CRITICAL EVENT: Tool execution started.
        Shows what tools the AI is using to solve the problem.
        
        Args:
            data: Event data including tool name and parameters
        """
        await self._emit_critical('tool_executing', data)
    
    async def emit_tool_completed(self, data: Dict[str, Any]):
        """
        CRITICAL EVENT: Tool execution completed.
        Shows the results from tool execution.
        
        Args:
            data: Event data including tool name and results
        """
        await self._emit_critical('tool_completed', data)
    
    async def emit_agent_completed(self, data: Dict[str, Any]):
        """
        CRITICAL EVENT: Agent processing finished.
        User must know their request is complete.
        
        Args:
            data: Event data including final results
        """
        await self._emit_critical('agent_completed', data)
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Generic emit method for backward compatibility.
        Routes to appropriate emit method based on event type.
        
        Args:
            event_type: The event type to emit
            data: Event payload
        """
        # Route critical events to their specific methods
        if event_type == 'agent_started':
            await self.emit_agent_started(data)
        elif event_type == 'agent_thinking':
            await self.emit_agent_thinking(data)
        elif event_type == 'tool_executing':
            await self.emit_tool_executing(data)
        elif event_type == 'tool_completed':
            await self.emit_tool_completed(data)
        elif event_type == 'agent_completed':
            await self.emit_agent_completed(data)
        else:
            # Non-critical events go through notify_custom
            await self.notify_custom(event_type, data)
    
    async def _emit_critical(self, event_type: str, data: Dict[str, Any]):
        """
        Emit critical event with retry logic - NEVER bypass this.
        
        This method ensures critical events are delivered even under
        adverse conditions through retry logic and error handling.
        
        Args:
            event_type: One of the CRITICAL_EVENTS
            data: Event payload
        """
        # Track metrics
        if event_type in self.metrics.critical_events:
            self.metrics.critical_events[event_type] += 1
        self.metrics.total_events += 1
        self.metrics.last_event_time = datetime.utcnow()
        
        # Add execution context if available
        if self.context:
            data = {
                **data,
                'run_id': getattr(self.context, 'run_id', None),
                'thread_id': getattr(self.context, 'thread_id', None),
                'request_id': getattr(self.context, 'request_id', None),
            }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        # Emit with retries
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.manager.emit_critical_event(
                    user_id=self.user_id,
                    event_type=event_type,
                    data=data
                )
                
                # Success - log and return
                logger.debug(
                    f"Emitted {event_type} for user {self.user_id} "
                    f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                return
                
            except Exception as e:
                last_error = e
                self.metrics.error_count += 1
                
                if attempt < self.MAX_RETRIES - 1:
                    # Calculate retry delay with exponential backoff
                    delay = min(
                        self.RETRY_BASE_DELAY * (2 ** attempt),
                        self.RETRY_MAX_DELAY
                    )
                    
                    logger.warning(
                        f"Failed to emit {event_type} for user {self.user_id} "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    
                    self.metrics.retry_count += 1
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(
                        f"Failed to emit {event_type} for user {self.user_id} "
                        f"after {self.MAX_RETRIES} attempts: {last_error}"
                    )
    
    # Backward compatibility methods for existing code
    
    async def notify_agent_started(self, agent_name: str, **kwargs):
        """
        Backward compatibility wrapper for agent_started.
        
        Args:
            agent_name: Name of the agent starting
            **kwargs: Additional event data
        """
        await self.emit_agent_started({
            'agent': agent_name,
            'status': 'started',
            **kwargs
        })
    
    async def notify_agent_thinking(self, thought: str, **kwargs):
        """
        Backward compatibility wrapper for agent_thinking.
        
        Args:
            thought: The agent's current thought
            **kwargs: Additional event data
        """
        await self.emit_agent_thinking({
            'thought': thought,
            'type': 'reasoning',
            **kwargs
        })
    
    async def notify_tool_executing(self, tool_name: str, parameters: Optional[Dict] = None, **kwargs):
        """
        Backward compatibility wrapper for tool_executing.
        
        Args:
            tool_name: Name of the tool being executed
            parameters: Tool parameters
            **kwargs: Additional event data
        """
        await self.emit_tool_executing({
            'tool': tool_name,
            'parameters': parameters or {},
            'status': 'executing',
            **kwargs  
        })
    
    async def notify_tool_completed(self, tool_name: str, result: Any, **kwargs):
        """
        Backward compatibility wrapper for tool_completed.
        
        Args:
            tool_name: Name of the tool that completed
            result: Tool execution result
            **kwargs: Additional event data
        """
        await self.emit_tool_completed({
            'tool': tool_name,
            'result': result,
            'status': 'completed',
            **kwargs
        })
    
    async def notify_agent_completed(self, result: Any, **kwargs):
        """
        Backward compatibility wrapper for agent_completed.
        
        Args:
            result: Final agent result
            **kwargs: Additional event data
        """
        await self.emit_agent_completed({
            'result': result,
            'status': 'completed',
            **kwargs
        })
    
    async def notify_agent_error(self, error: str, **kwargs):
        """
        Error notification (non-critical but important).
        
        Args:
            error: Error message
            **kwargs: Additional error context
        """
        await self.manager.emit_critical_event(
            user_id=self.user_id,
            event_type='agent_error',
            data={
                'error': error,
                'status': 'error',
                **kwargs
            }
        )
        self.metrics.error_count += 1
    
    async def notify_progress_update(self, progress: float, message: str = "", **kwargs):
        """
        Progress update notification.
        
        Args:
            progress: Progress percentage (0-100)
            message: Progress message
            **kwargs: Additional data
        """
        await self.manager.emit_critical_event(
            user_id=self.user_id,
            event_type='progress_update',
            data={
                'progress': progress,
                'message': message,
                **kwargs
            }
        )
    
    async def notify_custom(self, event_type: str, data: Dict[str, Any]):
        """
        Custom event emission for non-critical events.
        
        Args:
            event_type: Custom event type
            data: Event payload
        """
        # Add context if available
        if self.context:
            data = {
                **data,
                'run_id': getattr(self.context, 'run_id', None),
                'thread_id': getattr(self.context, 'thread_id', None),
            }
        
        await self.manager.emit_critical_event(
            user_id=self.user_id,
            event_type=event_type,
            data=data
        )
        self.metrics.total_events += 1
    
    # Pool integration methods
    
    async def acquire(self):
        """
        Acquire this emitter from a pool.
        For EmitterPool integration.
        """
        # Reset metrics for new usage
        self.metrics = EmitterMetrics()
        self.metrics.critical_events = {event: 0 for event in self.CRITICAL_EVENTS}
        logger.debug(f"Emitter acquired for user {self.user_id}")
    
    async def release(self):
        """
        Release this emitter back to a pool.
        For EmitterPool integration.
        """
        # Clear buffers
        async with self._buffer_lock:
            self._event_buffer.clear()
        logger.debug(f"Emitter released for user {self.user_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get emitter statistics.
        
        Returns:
            Dictionary with metrics and statistics
        """
        uptime = (datetime.utcnow() - self.metrics.created_at).total_seconds()
        
        return {
            'user_id': self.user_id,
            'total_events': self.metrics.total_events,
            'critical_events': self.metrics.critical_events.copy(),
            'error_count': self.metrics.error_count,
            'retry_count': self.metrics.retry_count,
            'last_event_time': self.metrics.last_event_time.isoformat() if self.metrics.last_event_time else None,
            'uptime_seconds': uptime,
            'has_context': self.context is not None
        }
    
    def get_context(self) -> Optional['UserExecutionContext']:
        """
        Get the execution context.
        For backward compatibility.
        
        Returns:
            UserExecutionContext or None
        """
        return self.context
    
    def set_context(self, context: 'UserExecutionContext'):
        """
        Update the execution context.
        
        Args:
            context: New execution context
        """
        self.context = context
        logger.debug(f"Context updated for emitter (user: {self.user_id})")
    
    async def cleanup(self):
        """
        Cleanup emitter resources.
        Called when emitter is being destroyed.
        """
        # Flush any buffered events
        async with self._buffer_lock:
            if self._event_buffer:
                logger.warning(
                    f"Dropping {len(self._event_buffer)} buffered events "
                    f"for user {self.user_id}"
                )
                self._event_buffer.clear()
        
        logger.info(
            f"Emitter cleanup for user {self.user_id} - "
            f"Total events: {self.metrics.total_events}, "
            f"Errors: {self.metrics.error_count}"
        )


class WebSocketEmitterFactory:
    """
    Factory for creating WebSocket emitters.
    Consolidates factory patterns from various implementations.
    """
    
    @staticmethod
    def create_emitter(
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ) -> UnifiedWebSocketEmitter:
        """
        Create a new emitter instance.
        
        Args:
            manager: WebSocket manager
            user_id: Target user ID
            context: Optional execution context
            
        Returns:
            New UnifiedWebSocketEmitter instance
        """
        return UnifiedWebSocketEmitter(
            manager=manager,
            user_id=user_id,
            context=context
        )
    
    @staticmethod
    def create_scoped_emitter(
        manager: 'UnifiedWebSocketManager',
        context: 'UserExecutionContext'
    ) -> UnifiedWebSocketEmitter:
        """
        Create a context-scoped emitter.
        
        Args:
            manager: WebSocket manager
            context: Execution context (required)
            
        Returns:
            New UnifiedWebSocketEmitter with context
        """
        if not context or not hasattr(context, 'user_id'):
            raise ValueError("Valid UserExecutionContext required for scoped emitter")
        
        return UnifiedWebSocketEmitter(
            manager=manager,
            user_id=context.user_id,
            context=context
        )


class WebSocketEmitterPool:
    """
    Pool management for WebSocket emitters.
    Integrates EmitterPool patterns for efficient resource usage.
    """
    
    def __init__(self, manager: 'UnifiedWebSocketManager', max_size: int = 100):
        """
        Initialize emitter pool.
        
        Args:
            manager: WebSocket manager
            max_size: Maximum pool size
        """
        self.manager = manager
        self.max_size = max_size
        self._pool: Dict[str, UnifiedWebSocketEmitter] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            'acquisitions': 0,
            'releases': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info(f"WebSocketEmitterPool initialized (max_size: {max_size})")
    
    async def acquire(
        self,
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ) -> UnifiedWebSocketEmitter:
        """
        Acquire an emitter from the pool.
        
        Args:
            user_id: Target user ID
            context: Optional execution context
            
        Returns:
            UnifiedWebSocketEmitter instance
        """
        async with self._lock:
            self._stats['acquisitions'] += 1
            
            # Check if emitter exists in pool
            if user_id in self._pool:
                emitter = self._pool[user_id]
                if context:
                    emitter.set_context(context)
                await emitter.acquire()
                self._stats['cache_hits'] += 1
                return emitter
            
            # Create new emitter
            self._stats['cache_misses'] += 1
            
            # Check pool size limit
            if len(self._pool) >= self.max_size:
                # Evict oldest emitter (simple LRU)
                oldest_user = next(iter(self._pool))
                old_emitter = self._pool.pop(oldest_user)
                await old_emitter.cleanup()
                logger.debug(f"Evicted emitter for user {oldest_user} from pool")
            
            # Create and store new emitter
            emitter = UnifiedWebSocketEmitter(
                manager=self.manager,
                user_id=user_id,
                context=context
            )
            self._pool[user_id] = emitter
            
            return emitter
    
    async def release(self, emitter: UnifiedWebSocketEmitter):
        """
        Release an emitter back to the pool.
        
        Args:
            emitter: Emitter to release
        """
        async with self._lock:
            self._stats['releases'] += 1
            await emitter.release()
            # Emitter remains in pool for reuse
    
    async def cleanup_inactive_emitters(self, max_age_seconds: int = 300):
        """
        Clean up inactive emitters.
        
        Args:
            max_age_seconds: Maximum age for inactive emitters
        """
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []
            
            for user_id, emitter in self._pool.items():
                if emitter.metrics.last_event_time:
                    age = (now - emitter.metrics.last_event_time).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(user_id)
            
            for user_id in to_remove:
                emitter = self._pool.pop(user_id)
                await emitter.cleanup()
                logger.debug(f"Cleaned up inactive emitter for user {user_id}")
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} inactive emitters")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            'pool_size': len(self._pool),
            'max_size': self.max_size,
            **self._stats
        }
    
    async def shutdown(self):
        """
        Shutdown the pool and cleanup all emitters.
        """
        async with self._lock:
            for emitter in self._pool.values():
                await emitter.cleanup()
            self._pool.clear()
            logger.info("WebSocketEmitterPool shutdown complete")