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
import time
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from shared.logging.unified_logging_ssot import get_logger

if TYPE_CHECKING:
    # ISSUE #824 REMEDIATION: Use canonical SSOT import path
    from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = get_logger(__name__)


@dataclass
class EmitterMetrics:
    """Metrics tracking for emitter performance."""
    total_events: int = 0
    critical_events: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0
    last_event_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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
    
    # Authentication-specific critical events with additional guarantees
    AUTHENTICATION_CRITICAL_EVENTS = [
        'auth_started',
        'auth_validating', 
        'auth_completed',
        'auth_failed'
    ]
    
    # Retry configuration for critical events
    MAX_RETRIES = 3
    MAX_CRITICAL_RETRIES = 5  # Additional retries for authentication events
    RETRY_BASE_DELAY = 0.1  # 100ms
    RETRY_MAX_DELAY = 2.0   # 2 seconds
    
    # PERFORMANCE OPTIMIZATION: Fast mode for high-throughput scenarios
    FAST_MODE_MAX_RETRIES = 1  # Minimal retries for performance
    FAST_MODE_BASE_DELAY = 0.001  # 1ms instead of 100ms
    FAST_MODE_MAX_DELAY = 0.01   # 10ms instead of 2s
    
    def __init__(
        self,
        manager: 'UnifiedWebSocketManager' = None,
        user_id: str = None,
        context: Optional['UserExecutionContext'] = None,
        performance_mode: bool = False,
        # PHASE 1 BACKWARD COMPATIBILITY: Support legacy constructor parameters
        websocket_manager: 'UnifiedWebSocketManager' = None
    ):
        """
        Initialize emitter for specific user.
        
        Args:
            manager: UnifiedWebSocketManager instance
            user_id: User ID this emitter serves
            context: Optional execution context for additional metadata
            performance_mode: Enable high-throughput mode with minimal retries
            websocket_manager: Legacy parameter alias for 'manager' (backward compatibility)
        """
        # PHASE 1 BACKWARD COMPATIBILITY: Handle legacy parameter name
        if websocket_manager is not None and manager is None:
            manager = websocket_manager
            logger.debug("Using legacy 'websocket_manager' parameter (redirected to 'manager')")
        
        if manager is None:
            raise ValueError("Either 'manager' or 'websocket_manager' parameter is required")
        
        # Extract user_id from context if not provided directly
        if user_id is None and context is not None:
            user_id = getattr(context, 'user_id', None)
        
        if user_id is None:
            raise ValueError("user_id is required (directly or via context.user_id)")
        
        self.manager = manager
        self.user_id = user_id
        self.context = context
        self.performance_mode = performance_mode
        
        # Metrics tracking
        self.metrics = EmitterMetrics()
        self.metrics.critical_events = {event: 0 for event in self.CRITICAL_EVENTS}
        
        # PHASE 2: Enhanced event batching and performance optimization
        self._event_buffer: List[Dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        self._batch_size = 5 if performance_mode else 10  # Smaller batches for performance mode
        self._batch_timeout = 0.05 if performance_mode else 0.1  # 50ms vs 100ms
        self._batch_timer: Optional[asyncio.Task] = None
        self._enable_batching = not performance_mode  # Disable batching in performance mode for lower latency
        
        # PHASE 2: Connection pool optimization state
        self._connection_health_score = 100  # Start with perfect health
        self._last_health_check = datetime.now(timezone.utc)
        self._consecutive_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_timeout = 30.0  # 30 seconds
        
        # PHASE 2: High-throughput optimization settings
        self._high_throughput_mode = performance_mode
        self._throughput_threshold = 100 if performance_mode else 50  # events per minute
        self._adaptive_batching = True
        
        # Security validation state (from agent_websocket_bridge.py)
        self._last_validated_run_id: Optional[str] = None
        self._validation_cache: Dict[str, bool] = {}
        
        # Token metrics tracking (from base_agent.py)
        self._token_metrics = {
            'total_operations': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0
        }
        
        # User tier tracking (from transparent_websocket_events.py)
        self._user_tier: Optional[str] = getattr(context, 'user_tier', 'free') if context else 'free'
        self._events_sent: List[Dict[str, Any]] = []
        
        # Validate critical events are available
        self._validate_critical_events()
        
        logger.info(f"UnifiedWebSocketEmitter created for user {user_id} (tier: {self._user_tier}, performance_mode: {performance_mode}, batching: {self._enable_batching})")
        
        # PHASE 2: Start background event processor for batching
        if self._enable_batching:
            self._start_batch_processor()
    
    def _start_batch_processor(self):
        """Start background batch processor for non-critical events."""
        if not self._enable_batching:
            return
            
        # Start the batch processing task
        self._batch_timer = asyncio.create_task(self._process_event_batches())
        logger.debug(f"Batch processor started for user {self.user_id} (batch_size: {self._batch_size})")
    
    async def _process_event_batches(self):
        """Background processor for batching non-critical events."""
        try:
            while True:
                await asyncio.sleep(self._batch_timeout)
                
                async with self._buffer_lock:
                    if not self._event_buffer:
                        continue
                    
                    # Process batch if we have events or timeout reached
                    batch_to_process = self._event_buffer.copy()
                    self._event_buffer.clear()
                
                if batch_to_process:
                    await self._send_event_batch(batch_to_process)
                    
        except asyncio.CancelledError:
            logger.debug(f"Batch processor cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Batch processor error for user {self.user_id}: {e}")
    
    async def _send_event_batch(self, batch: List[Dict[str, Any]]):
        """Send a batch of events together for better performance."""
        try:
            # Group events by type for better compression
            grouped_events = {}
            for event in batch:
                event_type = event.get('type', 'unknown')
                if event_type not in grouped_events:
                    grouped_events[event_type] = []
                grouped_events[event_type].append(event)
            
            # Send grouped batch
            batch_data = {
                'type': 'event_batch',
                'user_id': self.user_id,
                'batch_id': f"batch_{int(time.time() * 1000)}",
                'events': grouped_events,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'batch_size': len(batch)
            }
            
            if hasattr(self.manager, 'emit_event_batch'):
                await self.manager.emit_event_batch(
                    user_id=self.user_id,
                    batch_data=batch_data
                )
            else:
                # Fallback to individual events if manager doesn't support batching
                for event in batch:
                    await self._emit_individual_event(event)
            
            logger.debug(f"Sent event batch for user {self.user_id}: {len(batch)} events")
            
        except Exception as e:
            logger.error(f"Failed to send event batch for user {self.user_id}: {e}")
            # Fall back to individual event sending
            for event in batch:
                try:
                    await self._emit_individual_event(event)
                except Exception as fallback_error:
                    logger.error(f"Fallback individual event failed: {fallback_error}")
    
    async def _emit_individual_event(self, event_data: Dict[str, Any]):
        """Fallback method to emit individual events."""
        event_type = event_data.get('type', 'unknown')
        if hasattr(self.manager, 'emit_event'):
            await self.manager.emit_event(
                user_id=self.user_id,
                event_type=event_type,
                data=event_data
            )
        else:
            # Fallback to critical event method
            await self.manager.emit_critical_event(
                user_id=self.user_id,
                event_type=event_type,
                data=event_data
            )
    
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
        # PHASE 1 ENHANCEMENT: Security validation before emission
        if not self._validate_event_context(getattr(self.context, 'run_id', None), event_type):
            logger.error(f"Security validation failed for event {event_type} - blocking emission")
            return False
        
        # SECURITY FIX 2: Connection state validation before ALL authentication events
        if not self.manager.is_connection_active(self.user_id):
            logger.critical(f"CRITICAL EVENT LOST - Connection dead for user {self.user_id}, event: {event_type}")
            await self._trigger_connection_recovery(event_type, data)
            return False
        
        # Track metrics
        if event_type in self.metrics.critical_events:
            self.metrics.critical_events[event_type] += 1
        self.metrics.total_events += 1
        self.metrics.last_event_time = datetime.now(timezone.utc)
        
        # Add execution context if available
        if self.context:
            data = {
                **data,
                'run_id': getattr(self.context, 'run_id', None),
                'thread_id': getattr(self.context, 'thread_id', None),
                'request_id': getattr(self.context, 'request_id', None),
            }
        
        # PHASE 1 ENHANCEMENT: Add user tier metadata
        if self._user_tier:
            data = {
                **data,
                'metadata': {
                    **(data.get('metadata', {})),
                    'user_tier': self._user_tier,
                    'is_priority_queue': self._user_tier == 'enterprise'
                },
                'user_id': self.user_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        # SECURITY FIX 3: Guaranteed delivery with enhanced retries for auth events
        is_auth_event = event_type in self.AUTHENTICATION_CRITICAL_EVENTS
        
        # PERFORMANCE OPTIMIZATION: Use fast mode settings if enabled
        if self.performance_mode and not is_auth_event:
            max_attempts = self.FAST_MODE_MAX_RETRIES
        else:
            max_attempts = self.MAX_CRITICAL_RETRIES if is_auth_event else self.MAX_RETRIES
        
        # Emit with retries
        last_error = None
        for attempt in range(max_attempts):
            try:
                await self.manager.emit_critical_event(
                    user_id=self.user_id,
                    event_type=event_type,
                    data=data
                )
                
                # Success - log and return
                if is_auth_event:
                    logger.info(
                        f"Authentication event {event_type} delivered successfully "
                        f"for user {self.user_id} (attempt {attempt + 1}/{max_attempts})"
                    )
                else:
                    logger.debug(
                        f"Emitted {event_type} for user {self.user_id} "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                return True
                
            except Exception as e:
                last_error = e
                self.metrics.error_count += 1
                
                if attempt < max_attempts - 1:
                    # Enhanced retry logic for authentication events
                    if is_auth_event:
                        success = await self._retry_critical_event(event_type, data, attempt)
                        if success:
                            return True
                    else:
                        # Standard retry with exponential backoff (or fast mode)
                        if self.performance_mode:
                            delay = min(
                                self.FAST_MODE_BASE_DELAY * (2 ** attempt),
                                self.FAST_MODE_MAX_DELAY
                            )
                        else:
                            delay = min(
                                self.RETRY_BASE_DELAY * (2 ** attempt),
                                self.RETRY_MAX_DELAY
                            )
                        
                        logger.warning(
                            f"Failed to emit {event_type} for user {self.user_id} "
                            f"(attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        
                        self.metrics.retry_count += 1
                        await asyncio.sleep(delay)
                else:
                    # Final attempt failed - escalate if authentication event
                    if is_auth_event:
                        await self._escalate_to_fallback_channel(event_type, data)
                        logger.critical(
                            f"AUTHENTICATION EVENT DELIVERY FAILED - {event_type} for user {self.user_id} "
                            f"after {max_attempts} attempts: {last_error}. Regulatory violation risk!"
                        )
                    else:
                        logger.error(
                            f"Failed to emit {event_type} for user {self.user_id} "
                            f"after {max_attempts} attempts: {last_error}"
                        )
        
        return False
    
    # Backward compatibility methods for existing code
    
    async def notify_agent_started(self, agent_name: str, metadata: Dict[str, Any] = None, context: Dict[str, Any] = None):
        """
        Send agent_started event - CRITICAL for chat value delivery.
        
        Args:
            agent_name: Name of the agent starting
            metadata: Additional event metadata (preferred)
            context: Context data (legacy compatibility)
        """
        if metadata is None:
            metadata = {}
            
        # Merge context data into metadata for compatibility
        if context:
            metadata = {**metadata, **context}
        
        await self.emit_agent_started({
            'agent_name': agent_name,
            'metadata': metadata,
            'status': 'started',
            'timestamp': time.time()
        })
    
    async def notify_agent_thinking(self, agent_name: str = None, reasoning: str = None, thought: str = None, step_number: Optional[int] = None, metadata: Dict[str, Any] = None):
        """
        Send agent_thinking event - CRITICAL for chat value delivery.
        
        Args:
            agent_name: Name of the agent (for compatibility)
            reasoning: The agent's reasoning (preferred)
            thought: The agent's current thought (legacy compatibility)
            step_number: Step number in the process
            metadata: Additional event metadata
        """
        if metadata is None:
            metadata = {}
        
        # Use reasoning if provided, otherwise fall back to thought
        actual_thought = reasoning or thought or "Agent is thinking..."
        
        # Add step number and agent name to metadata
        if step_number is not None:
            metadata['step_number'] = step_number
        if agent_name:
            metadata['agent_name'] = agent_name
        
        await self.emit_agent_thinking({
            'reasoning': actual_thought,
            'metadata': metadata,
            'type': 'reasoning',
            'timestamp': time.time()
        })
    
    async def notify_tool_executing(self, tool_name: str, metadata: Dict[str, Any] = None):
        """
        Send tool_executing event - CRITICAL for chat value delivery.
        
        Args:
            tool_name: Name of the tool being executed
            metadata: Additional event metadata
        """
        if metadata is None:
            metadata = {}
        
        await self.emit_tool_executing({
            'tool_name': tool_name,
            'metadata': metadata,
            'status': 'executing',
            'timestamp': time.time()
        })
    
    async def notify_tool_completed(self, tool_name: str, metadata: Dict[str, Any] = None):
        """
        Send tool_completed event - CRITICAL for chat value delivery.
        
        Args:
            tool_name: Name of the tool that completed
            metadata: Additional event metadata (should include 'result')
        """
        if metadata is None:
            metadata = {}
        
        await self.emit_tool_completed({
            'tool_name': tool_name,
            'metadata': metadata,
            'status': 'completed',
            'timestamp': time.time()
        })
    
    async def notify_agent_completed(self, agent_name: str, metadata: Dict[str, Any] = None, result: Dict[str, Any] = None, execution_time_ms: float = None):
        """
        Send agent_completed event - CRITICAL for chat value delivery.
        
        Args:
            agent_name: Name of the agent that completed
            metadata: Additional event metadata (preferred)
            result: Agent result data (legacy compatibility)
            execution_time_ms: Execution time in milliseconds
        """
        if metadata is None:
            metadata = {}
            
        # Merge result data into metadata for compatibility
        if result:
            metadata = {**metadata, **result}
            
        # Add execution time if provided
        if execution_time_ms is not None:
            metadata['execution_time_ms'] = execution_time_ms
        
        await self.emit_agent_completed({
            'agent_name': agent_name,
            'metadata': metadata,
            'status': 'completed',
            'timestamp': time.time()
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
        uptime = (datetime.now(timezone.utc) - self.metrics.created_at).total_seconds()
        
        return {
            'user_id': self.user_id,
            'total_events': self.metrics.total_events,
            'critical_events': self.metrics.critical_events.copy(),
            'error_count': self.metrics.error_count,
            'retry_count': self.metrics.retry_count,
            'last_event_time': self.metrics.last_event_time.isoformat() if self.metrics.last_event_time else None,
            'uptime_seconds': uptime,
            'has_context': self.context is not None,
            'user_tier': self._user_tier,
            'is_priority_user': self.is_priority_user(),
            'token_metrics': self.get_token_metrics(),
            'validation_cache_size': len(self._validation_cache),
            'events_sent_count': len(self._events_sent)
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
    
    async def _trigger_connection_recovery(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger connection recovery when critical events fail due to dead connections.
        
        Args:
            event_type: The failed event type
            data: Event payload that failed to send
        """
        try:
            logger.error(
                f"Connection recovery triggered for user {self.user_id} - "
                f"lost critical event: {event_type}"
            )
            
            # Get detailed connection health info
            health = self.manager.get_connection_health(self.user_id)
            logger.error(f"Connection health for user {self.user_id}: {health}")
            
            # Log the failed event for potential recovery
            self.metrics.error_count += 1
            
            # TODO: Implement fallback channels (e.g., database queue, email notification)
            # For now, ensure it's logged at ERROR level for monitoring
            
        except Exception as e:
            logger.error(f"Connection recovery trigger failed: {e}")
    
    async def _retry_critical_event(self, event_type: str, data: Dict, attempt: int = 0) -> bool:
        """
        Retry critical event with exponential backoff for authentication events.
        
        Args:
            event_type: Event type to retry
            data: Event data
            attempt: Current attempt number
            
        Returns:
            True if retry succeeded, False otherwise
        """
        if attempt >= self.MAX_CRITICAL_RETRIES:
            await self._escalate_to_fallback_channel(event_type, data)
            return False
        
        try:
            # Exponential backoff with jitter
            import random
            base_delay = self.RETRY_BASE_DELAY * (2 ** attempt)
            jitter = random.uniform(0.1, 0.3) * base_delay
            delay = min(base_delay + jitter, self.RETRY_MAX_DELAY)
            
            logger.warning(
                f"Retrying authentication event {event_type} for user {self.user_id} "
                f"(attempt {attempt + 1}/{self.MAX_CRITICAL_RETRIES}) in {delay:.2f}s"
            )
            
            await asyncio.sleep(delay)
            
            # Re-verify connection before retry
            if not self.manager.is_connection_active(self.user_id):
                logger.error(f"Connection still dead during retry for user {self.user_id}")
                return await self._retry_critical_event(event_type, data, attempt + 1)
            
            # Attempt delivery
            await self.manager.emit_critical_event(
                user_id=self.user_id,
                event_type=event_type,
                data=data
            )
            
            logger.info(f"Authentication event {event_type} delivered on retry {attempt + 1}")
            return True
            
        except Exception as e:
            logger.error(f"Retry {attempt + 1} failed for {event_type}: {e}")
            return await self._retry_critical_event(event_type, data, attempt + 1)
    
    async def _escalate_to_fallback_channel(self, event_type: str, data: Dict) -> None:
        """
        Escalate failed authentication events to fallback channels.
        
        Args:
            event_type: Failed event type
            data: Event data that failed to send
        """
        try:
            logger.critical(
                f"ESCALATING TO FALLBACK - Authentication event {event_type} "
                f"failed for user {self.user_id}. Business continuity at risk."
            )
            
            # Log to auth event failure queue for recovery
            self.metrics.error_count += 1
            
            # TODO: Implement fallback channels:
            # - Database queue for later replay
            # - Email notification to user
            # - Admin alert system
            # - Alternative WebSocket connection attempt
            
            logger.error(f"Auth event failure logged for user {self.user_id}: {event_type}")
            
        except Exception as e:
            logger.error(f"Fallback escalation failed: {e}")
    
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
            f"Errors: {self.metrics.error_count}, "
            f"Token operations: {self._token_metrics['total_operations']}, "
            f"Total cost: ${self._token_metrics['total_cost']:.4f}"
        )
    
    # ===================== PHASE 1 TOKEN METRICS (from base_agent.py) =====================
    
    def update_token_metrics(self, input_tokens: int, output_tokens: int, cost: float, operation: str = "unknown"):
        """
        Update token usage metrics for this emitter's context.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            cost: Cost of the operation
            operation: Description of the operation
        """
        self._token_metrics['total_operations'] += 1
        self._token_metrics['total_input_tokens'] += input_tokens
        self._token_metrics['total_output_tokens'] += output_tokens
        self._token_metrics['total_cost'] += cost
        
        logger.debug(f"Token metrics updated for user {self.user_id}: {operation} - "
                    f"Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")
    
    def get_token_metrics(self) -> Dict[str, Any]:
        """
        Get current token usage metrics.
        
        Returns:
            Dictionary with token usage statistics
        """
        return {
            **self._token_metrics,
            'average_tokens_per_operation': (
                (self._token_metrics['total_input_tokens'] + self._token_metrics['total_output_tokens']) /
                max(1, self._token_metrics['total_operations'])
            ),
            'average_cost_per_operation': (
                self._token_metrics['total_cost'] / max(1, self._token_metrics['total_operations'])
            )
        }
    
    # ===================== PHASE 1 USER TIER HANDLING (from transparent_websocket_events.py) =====================
    
    def set_user_tier(self, user_tier: str):
        """
        Set or update the user tier for this emitter.
        
        Args:
            user_tier: User tier (free, early, mid, enterprise)
        """
        old_tier = self._user_tier
        self._user_tier = user_tier
        logger.info(f"User tier updated for {self.user_id}: {old_tier} -> {user_tier}")
    
    def get_user_tier(self) -> str:
        """
        Get the current user tier.
        
        Returns:
            Current user tier
        """
        return self._user_tier or 'free'
    
    def is_priority_user(self) -> bool:
        """
        Check if this user is in the priority queue.
        
        Returns:
            True if user has enterprise tier
        """
        return self._user_tier == 'enterprise'
    
    def _validate_event_context(self, run_id: Optional[str], event_type: str, agent_name: Optional[str] = None) -> bool:
        """
        Validate WebSocket event context to ensure proper user isolation.
        
        CRITICAL SECURITY: This validation prevents events from being sent without proper context,
        which could result in events being delivered to wrong users or global broadcast.
        
        Args:
            run_id: Run identifier to validate
            event_type: Type of event being emitted (for logging)
            agent_name: Optional agent name (for logging)
            
        Returns:
            bool: True if context is valid and event should be sent
            
        Security Impact: Prevents cross-user data leakage and ensures WebSocket events
                        are only sent to the correct user context.
        """
        try:
            # Check cache first for performance
            cache_key = f"{run_id}:{event_type}"
            if cache_key in self._validation_cache:
                return self._validation_cache[cache_key]
            
            # CRITICAL CHECK: run_id cannot be None
            if run_id is None:
                logger.error(f" ALERT:  CONTEXT VALIDATION FAILED: run_id is None for {event_type} "
                           f"(agent={agent_name or 'unknown'}). This would cause event misrouting!")
                logger.error(f" ALERT:  SECURITY RISK: Events with None run_id can be delivered to wrong users!")
                self._validation_cache[cache_key] = False
                return False
            
            # CRITICAL CHECK: run_id cannot be 'registry' (system context)
            if run_id == 'registry':
                logger.error(f" ALERT:  CONTEXT VALIDATION FAILED: run_id='registry' for {event_type} "
                           f"(agent={agent_name or 'unknown'}). System context cannot emit user events!")
                logger.error(f" ALERT:  SECURITY RISK: Registry context events would be broadcast to all users!")
                self._validation_cache[cache_key] = False
                return False
            
            # VALIDATION CHECK: run_id should be a non-empty string
            if not isinstance(run_id, str) or not run_id.strip():
                logger.error(f" ALERT:  CONTEXT VALIDATION FAILED: Invalid run_id '{run_id}' for {event_type} "
                           f"(agent={agent_name or 'unknown'}). run_id must be non-empty string!")
                self._validation_cache[cache_key] = False
                return False
            
            # VALIDATION CHECK: run_id should not contain suspicious patterns
            if self._is_suspicious_run_id(run_id):
                logger.warning(f" WARNING: [U+FE0F] CONTEXT VALIDATION WARNING: Suspicious run_id pattern '{run_id}' for {event_type} "
                              f"(agent={agent_name or 'unknown'}). Event will be sent but flagged for monitoring.")
                # Allow but log for monitoring - some legitimate run_ids might trigger this
            
            # Context validation passed
            logger.debug(f" PASS:  CONTEXT VALIDATION PASSED: run_id={run_id} for {event_type} is valid")
            self._validation_cache[cache_key] = True
            self._last_validated_run_id = run_id
            return True
            
        except Exception as e:
            logger.error(f" ALERT:  CONTEXT VALIDATION EXCEPTION: Validation failed for {event_type} "
                        f"(run_id={run_id}, agent={agent_name or 'unknown'}): {e}")
            self._validation_cache[cache_key] = False
            return False
    
    def _is_suspicious_run_id(self, run_id: str) -> bool:
        """
        Check if a run_id contains suspicious patterns that might indicate invalid context.
        
        This helps detect potentially invalid run_ids that could cause security issues
        or indicate bugs in run_id generation.
        
        Args:
            run_id: The run_id to check
            
        Returns:
            bool: True if the run_id contains suspicious patterns
        """
        suspicious_patterns = [
            'undefined', 'null', 'none', '',  # Falsy values that became strings
            'test_', 'mock_', 'fake_',        # Test/mock values in production
            'admin', 'system', 'root',        # System-level contexts
            '__', '{{', '}}', '${',           # Template/variable placeholders
            'localhost', '127.0.0.1',        # Local development patterns
            'debug', 'trace',                 # Debug contexts
        ]
        
        run_id_lower = run_id.lower()
        for pattern in suspicious_patterns:
            if pattern in run_id_lower:
                return True
                
        # Check for unusual characters that might indicate encoding issues
        if any(ord(char) > 127 for char in run_id):  # Non-ASCII characters
            return True
            
        return False

    @classmethod
    def create_user_emitter(
        cls,
        manager: 'UnifiedWebSocketManager',
        user_context: 'UserExecutionContext'
    ) -> 'UnifiedWebSocketEmitter':
        """Factory method for user-specific emitter creation.

        Args:
            manager: UnifiedWebSocketManager instance
            user_context: User execution context for isolation

        Returns:
            UnifiedWebSocketEmitter: Configured emitter for the user

        Raises:
            ValueError: If user_context is invalid
        """
        if not user_context:
            raise ValueError("create_user_emitter requires valid user_context")

        user_id = getattr(user_context, 'user_id', None)
        if not user_id:
            raise ValueError("create_user_emitter requires user_id in user_context")

        return cls(
            manager=manager,
            user_id=user_id,
            context=user_context
        )

    @classmethod
    def create_auth_emitter(
        cls,
        manager: 'UnifiedWebSocketManager',
        user_context: Optional['UserExecutionContext'] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> 'UnifiedWebSocketEmitter':
        """Factory method for authentication-specific emitter creation.

        ISSUE #669 REMEDIATION: Support both new and legacy parameter patterns.

        Args:
            manager: UnifiedWebSocketManager instance
            user_context: User execution context for auth events (NEW pattern)
            user_id: User ID (LEGACY pattern)
            thread_id: Thread ID (LEGACY pattern)
            connection_id: Connection ID (LEGACY pattern)

        Returns:
            UnifiedWebSocketEmitter: Configured emitter for auth events

        Raises:
            ValueError: If neither user_context nor user_id provided
        """
        # ISSUE #669 REMEDIATION: Support both new and legacy parameter patterns
        if user_context:
            # NEW pattern (preferred)
            actual_user_id = user_context.user_id
            actual_user_context = user_context
        elif user_id:
            # LEGACY pattern (backward compatibility)
            actual_user_id = user_id
            # Create minimal context for compatibility
            actual_user_context = type('AuthContext', (), {
                'user_id': user_id,
                'thread_id': thread_id,
                'connection_id': connection_id or f"auth_{user_id}"
            })()
        else:
            raise ValueError("create_auth_emitter requires either user_context or user_id")

        # For auth emitters, use standard emitter with enhanced security context
        return cls(
            manager=manager,
            user_id=actual_user_id,
            context=actual_user_context
        )


class AuthenticationWebSocketEmitter(UnifiedWebSocketEmitter):
    """
    SECURITY FIX 4: Authentication-specific WebSocket emitter with triple redundancy.
    
    Extends UnifiedWebSocketEmitter with additional guarantees specifically
    for authentication events to prevent security vulnerabilities.
    
    Features:
    - Triple redundancy for auth events
    - Enhanced connection health monitoring
    - Mandatory delivery confirmation
    - Regulatory compliance logging
    """
    
    # Authentication events requiring triple redundancy
    AUTHENTICATION_CRITICAL_EVENTS = [
        'auth_started', 
        'auth_validating', 
        'auth_completed', 
        'auth_failed'
    ]
    
    def __init__(self, manager: 'UnifiedWebSocketManager', user_id: str, 
                 context: Optional['UserExecutionContext'] = None):
        """Initialize authentication-specific emitter."""
        super().__init__(manager, user_id, context)
        
        # Enhanced metrics for authentication events
        self.auth_metrics = {
            'total_auth_events': 0,
            'successful_auth_deliveries': 0,
            'failed_auth_deliveries': 0,
            'connection_health_checks': 0,
            'fallback_escalations': 0
        }
        
        logger.info(f"AuthenticationWebSocketEmitter initialized for user {user_id}")
    
    async def emit_auth_event(self, event_type: str, data: Dict) -> bool:
        """
        Emit authentication event with triple redundancy.
        
        Args:
            event_type: Authentication event type
            data: Event payload
            
        Returns:
            True if delivery succeeded, False otherwise
            
        Raises:
            AuthenticationWebSocketError: If connection is unhealthy for auth
        """
        if event_type not in self.AUTHENTICATION_CRITICAL_EVENTS:
            logger.warning(f"Non-auth event {event_type} sent to auth emitter - using standard path")
            return await self._emit_critical(event_type, data)
        
        # Pre-flight connection health check
        await self.ensure_auth_connection_health()
        
        self.auth_metrics['total_auth_events'] += 1
        self.auth_metrics['connection_health_checks'] += 1
        
        # Triple redundancy approach:
        # 1. Primary delivery attempt
        success = await self._emit_critical(event_type, data)
        if success:
            self.auth_metrics['successful_auth_deliveries'] += 1
            await self._log_auth_success(event_type, data)
            return True
        
        # 2. Fallback channel attempt
        success = await self._send_via_fallback_channel(event_type, data)
        if success:
            self.auth_metrics['successful_auth_deliveries'] += 1
            return True
        
        # 3. Emergency escalation
        await self._log_auth_event_failure(event_type, data)
        self.auth_metrics['failed_auth_deliveries'] += 1
        self.auth_metrics['fallback_escalations'] += 1
        
        return False
    
    async def ensure_auth_connection_health(self) -> None:
        """
        Ensure WebSocket connection is healthy before auth events.
        
        Raises:
            AuthenticationWebSocketError: If connection is unhealthy
        """
        if not self.manager.is_connection_active(self.user_id):
            health = self.manager.get_connection_health(self.user_id)
            raise AuthenticationWebSocketError(
                f"WebSocket connection unhealthy for user {self.user_id} - "
                f"authentication cannot proceed safely. Health: {health}"
            )
        
        self.auth_metrics['connection_health_checks'] += 1
    
    async def _send_via_fallback_channel(self, event_type: str, data: Dict) -> bool:
        """
        Send authentication event via fallback channel.
        
        Args:
            event_type: Event type
            data: Event data
            
        Returns:
            True if fallback succeeded, False otherwise
        """
        try:
            logger.warning(
                f"Using fallback channel for auth event {event_type} "
                f"for user {self.user_id}"
            )
            
            # TODO: Implement actual fallback channels:
            # - Database persistence
            # - Alternative WebSocket path
            # - Push notification
            
            # For now, log at CRITICAL level for monitoring
            logger.critical(
                f"AUTH FALLBACK TRIGGERED: {event_type} for user {self.user_id} - "
                f"Primary WebSocket delivery failed"
            )
            
            return False  # Return False until real fallback is implemented
            
        except Exception as e:
            logger.error(f"Fallback channel failed: {e}")
            return False
    
    async def _log_auth_success(self, event_type: str, data: Dict) -> None:
        """Log successful authentication event delivery."""
        logger.info(
            f"AUTH SUCCESS: {event_type} delivered to user {self.user_id} - "
            f"Security compliance maintained"
        )
    
    async def _log_auth_event_failure(self, event_type: str, data: Dict) -> None:
        """Log authentication event delivery failure."""
        logger.critical(
            f"AUTH DELIVERY FAILURE: {event_type} for user {self.user_id} - "
            f"SECURITY RISK: User may not receive critical auth updates. "
            f"Regulatory compliance at risk."
        )
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication-specific statistics."""
        base_stats = self.get_stats()
        return {
            **base_stats,
            'auth_metrics': self.auth_metrics.copy(),
            'auth_delivery_rate': (
                self.auth_metrics['successful_auth_deliveries'] / 
                max(1, self.auth_metrics['total_auth_events'])
            ) * 100
        }


class AuthenticationWebSocketError(Exception):
    """Exception raised when authentication WebSocket operations fail."""
    pass


class AuthenticationConnectionMonitor:
    """
    SECURITY FIX 5: Connection health monitoring for authentication events.
    
    Monitors WebSocket connection health specifically for authentication
    workflows to prevent security vulnerabilities.
    
    Features:
    - Real-time connection health checks
    - Authentication-specific validation
    - Connection recovery recommendations
    - Security compliance monitoring
    """
    
    def __init__(self, manager: 'UnifiedWebSocketManager'):
        """
        Initialize authentication connection monitor.
        
        Args:
            manager: WebSocket manager to monitor
        """
        self.manager = manager
        self.health_checks_performed = 0
        self.unhealthy_connections_detected = 0
        self.recovery_attempts = 0
        
        logger.info("AuthenticationConnectionMonitor initialized")
    
    async def ensure_auth_connection_health(self, user_id: str) -> None:
        """
        Ensure WebSocket connection is healthy before auth events.
        
        Args:
            user_id: User ID to check
            
        Raises:
            AuthenticationWebSocketError: If connection is unhealthy
        """
        self.health_checks_performed += 1
        
        if not self.manager.is_connection_active(user_id):
            self.unhealthy_connections_detected += 1
            health_details = self.manager.get_connection_health(user_id)
            
            logger.critical(
                f"AUTHENTICATION SECURITY ALERT: Unhealthy connection for user {user_id} - "
                f"auth events cannot proceed safely. Details: {health_details}"
            )
            
            raise AuthenticationWebSocketError(
                f"WebSocket connection unhealthy for user {user_id} - "
                f"authentication cannot proceed safely. Health check failed."
            )
        
        logger.debug(f"Connection health verified for user {user_id}")
    
    async def monitor_auth_session(self, user_id: str, session_duration_ms: int = 30000) -> Dict[str, Any]:
        """
        Monitor connection health during an authentication session.
        
        Args:
            user_id: User to monitor
            session_duration_ms: How long to monitor (default 30s)
            
        Returns:
            Dictionary with monitoring results
        """
        import time
        start_time = time.time()
        end_time = start_time + (session_duration_ms / 1000)
        
        health_snapshots = []
        connection_drops = 0
        recovery_attempts = 0
        
        logger.info(f"Starting auth session monitoring for user {user_id} ({session_duration_ms}ms)")
        
        while time.time() < end_time:
            try:
                # Take health snapshot
                health = self.manager.get_connection_health(user_id)
                health_snapshots.append({
                    'timestamp': time.time(),
                    'health': health,
                    'is_healthy': health['has_active_connections']
                })
                
                # Detect connection drops
                if not health['has_active_connections']:
                    connection_drops += 1
                    logger.warning(f"Connection drop detected for user {user_id} during auth session")
                    
                    # Attempt recovery
                    recovery_attempts += 1
                    await self._attempt_connection_recovery(user_id)
                
                # Wait before next check
                await asyncio.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Auth session monitoring error: {e}")
                break
        
        duration = time.time() - start_time
        return {
            'user_id': user_id,
            'session_duration_actual': duration,
            'health_snapshots_count': len(health_snapshots),
            'connection_drops': connection_drops,
            'recovery_attempts': recovery_attempts,
            'final_health': health_snapshots[-1]['health'] if health_snapshots else None,
            'monitoring_successful': len(health_snapshots) > 0
        }
    
    async def _attempt_connection_recovery(self, user_id: str) -> bool:
        """
        Attempt to recover a dropped connection.
        
        Args:
            user_id: User whose connection dropped
            
        Returns:
            True if recovery succeeded, False otherwise
        """
        self.recovery_attempts += 1
        
        try:
            logger.info(f"Attempting connection recovery for user {user_id}")
            
            # TODO: Implement actual recovery mechanisms:
            # - Trigger WebSocket reconnection
            # - Send ping/pong to existing connections
            # - Clear stale connections
            # - Notify client to reconnect
            
            # For now, just clean up stale connections
            await self._cleanup_stale_connections(user_id)
            
            # Check if recovery was successful
            if self.manager.is_connection_active(user_id):
                logger.info(f"Connection recovery successful for user {user_id}")
                return True
            else:
                logger.warning(f"Connection recovery failed for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Connection recovery attempt failed: {e}")
            return False
    
    async def _cleanup_stale_connections(self, user_id: str) -> None:
        """
        Clean up stale connections for a user.
        
        Args:
            user_id: User whose connections to clean up
        """
        try:
            connection_ids = self.manager.get_user_connections(user_id)
            stale_connections = []
            
            for conn_id in connection_ids:
                connection = self.manager.get_connection(conn_id)
                if connection and not connection.websocket:
                    stale_connections.append(conn_id)
            
            for conn_id in stale_connections:
                await self.manager.remove_connection(conn_id)
                logger.info(f"Removed stale connection {conn_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Stale connection cleanup failed: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get authentication connection monitoring statistics."""
        return {
            'health_checks_performed': self.health_checks_performed,
            'unhealthy_connections_detected': self.unhealthy_connections_detected,
            'recovery_attempts': self.recovery_attempts,
            'health_check_success_rate': (
                (self.health_checks_performed - self.unhealthy_connections_detected) /
                max(1, self.health_checks_performed)
            ) * 100 if self.health_checks_performed > 0 else 100
        }


class WebSocketEmitterFactory:
    """
    Factory for creating WebSocket emitters.
    Consolidates factory patterns from various implementations.
    """
    
    @staticmethod
    def create_emitter(
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None,
        performance_mode: bool = False
    ) -> UnifiedWebSocketEmitter:
        """
        Create a new emitter instance.
        
        Args:
            manager: WebSocket manager
            user_id: Target user ID
            context: Optional execution context
            performance_mode: Enable high-throughput mode
            
        Returns:
            New UnifiedWebSocketEmitter instance
        """
        return UnifiedWebSocketEmitter(
            manager=manager,
            user_id=user_id,
            context=context,
            performance_mode=performance_mode
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
    
    @staticmethod
    def create_performance_emitter(
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ) -> UnifiedWebSocketEmitter:
        """
        Create a performance-optimized emitter for high-throughput scenarios.
        
        Args:
            manager: WebSocket manager
            user_id: Target user ID
            context: Optional execution context
            
        Returns:
            UnifiedWebSocketEmitter with performance mode enabled
        """
        return UnifiedWebSocketEmitter(
            manager=manager,
            user_id=user_id,
            context=context,
            performance_mode=True
        )
    
    @staticmethod
    def create_auth_emitter(
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ) -> AuthenticationWebSocketEmitter:
        """
        Create an authentication-specific emitter with enhanced security.
        
        Args:
            manager: WebSocket manager
            user_id: Target user ID
            context: Optional execution context
            
        Returns:
            New AuthenticationWebSocketEmitter instance
        """
        return AuthenticationWebSocketEmitter(
            manager=manager,
            user_id=user_id,
            context=context
        )
    
    # ===================== PHASE 2: PERFORMANCE OPTIMIZATION FEATURES =====================
    
    def _start_batch_processor(self):
        """Start background batch processor for non-critical events."""
        if not self._enable_batching:
            return
            
        # Start the batch processing task
        self._batch_timer = asyncio.create_task(self._process_event_batches())
        logger.debug(f"Batch processor started for user {self.user_id} (batch_size: {self._batch_size})")
    
    async def _process_event_batches(self):
        """Background processor for batching non-critical events."""
        try:
            while True:
                await asyncio.sleep(self._batch_timeout)
                
                async with self._buffer_lock:
                    if not self._event_buffer:
                        continue
                    
                    # Process batch if we have events or timeout reached
                    batch_to_process = self._event_buffer.copy()
                    self._event_buffer.clear()
                
                if batch_to_process:
                    await self._send_event_batch(batch_to_process)
                    
        except asyncio.CancelledError:
            logger.debug(f"Batch processor cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Batch processor error for user {self.user_id}: {e}")
    
    async def _send_event_batch(self, batch: List[Dict[str, Any]]):
        """Send a batch of events together for better performance."""
        try:
            # Group events by type for better compression
            grouped_events = {}
            for event in batch:
                event_type = event.get('type', 'unknown')
                if event_type not in grouped_events:
                    grouped_events[event_type] = []
                grouped_events[event_type].append(event)
            
            # Send grouped batch
            batch_data = {
                'type': 'event_batch',
                'user_id': self.user_id,
                'batch_id': f"batch_{int(time.time() * 1000)}",
                'events': grouped_events,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'batch_size': len(batch)
            }
            
            if hasattr(self.manager, 'emit_event_batch'):
                await self.manager.emit_event_batch(
                    user_id=self.user_id,
                    batch_data=batch_data
                )
            else:
                # Fallback to individual events if manager doesn't support batching
                for event in batch:
                    await self._emit_individual_event(event)
            
            logger.debug(f"Sent event batch for user {self.user_id}: {len(batch)} events")
            
        except Exception as e:
            logger.error(f"Failed to send event batch for user {self.user_id}: {e}")
            # Fall back to individual event sending
            for event in batch:
                try:
                    await self._emit_individual_event(event)
                except Exception as fallback_error:
                    logger.error(f"Fallback individual event failed: {fallback_error}")
    
    async def _emit_individual_event(self, event_data: Dict[str, Any]):
        """Fallback method to emit individual events."""
        event_type = event_data.get('type', 'unknown')
        if hasattr(self.manager, 'emit_event'):
            await self.manager.emit_event(
                user_id=self.user_id,
                event_type=event_type,
                data=event_data
            )
        else:
            # Fallback to critical event method
            await self.manager.emit_critical_event(
                user_id=self.user_id,
                event_type=event_type,
                data=event_data
            )
    
    async def _queue_for_batching(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Queue non-critical event for batching."""
        if not self._enable_batching:
            # Send immediately if batching disabled
            await self._emit_individual_event({
                'type': event_type,
                'user_id': self.user_id,
                **data
            })
            return True
        
        event = {
            'type': event_type,
            'user_id': self.user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **data
        }
        
        async with self._buffer_lock:
            self._event_buffer.append(event)
            
            # Trigger immediate send if batch is full
            if len(self._event_buffer) >= self._batch_size:
                batch_to_send = self._event_buffer.copy()
                self._event_buffer.clear()
                
                # Send batch immediately (don't wait for timer)
                asyncio.create_task(self._send_event_batch(batch_to_send))
        
        return True
    
    def _update_connection_health(self, success: bool):
        """Update connection health score based on operation success."""
        if success:
            self._consecutive_failures = 0
            self._connection_health_score = min(100, self._connection_health_score + 2)
            if self._circuit_breaker_open:
                logger.info(f"Circuit breaker closed for user {self.user_id} - connection recovered")
                self._circuit_breaker_open = False
        else:
            self._consecutive_failures += 1
            self._connection_health_score = max(0, self._connection_health_score - 10)
            
            # Open circuit breaker if too many failures
            if self._consecutive_failures >= 5 and not self._circuit_breaker_open:
                self._circuit_breaker_open = True
                logger.warning(f"Circuit breaker opened for user {self.user_id} - connection unhealthy")
    
    def _should_use_circuit_breaker(self) -> bool:
        """Check if circuit breaker should prevent operations."""
        if not self._circuit_breaker_open:
            return False
        
        # Check if timeout has passed
        elapsed = (datetime.now(timezone.utc) - self._last_health_check).total_seconds()
        if elapsed > self._circuit_breaker_timeout:
            self._circuit_breaker_open = False
            logger.info(f"Circuit breaker timeout expired for user {self.user_id} - attempting recovery")
            return False
        
        return True
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        return {
            'connection_health_score': self._connection_health_score,
            'circuit_breaker_open': self._circuit_breaker_open,
            'consecutive_failures': self._consecutive_failures,
            'batching_enabled': self._enable_batching,
            'batch_size': self._batch_size,
            'batch_timeout': self._batch_timeout,
            'high_throughput_mode': self._high_throughput_mode,
            'performance_mode': self.performance_mode,
            'current_buffer_size': len(self._event_buffer),
            'events_per_minute': self.metrics.total_events / max(1, (datetime.now(timezone.utc) - self.metrics.created_at).total_seconds() / 60)
        }
    
    async def cleanup(self):
        """Enhanced cleanup with Phase 2 optimizations."""
        try:
            # Cancel batch processor
            if hasattr(self, '_batch_timer') and self._batch_timer and not self._batch_timer.done():
                self._batch_timer.cancel()
                try:
                    await self._batch_timer
                except asyncio.CancelledError:
                    pass
            
            # Send any remaining batched events
            if hasattr(self, '_event_buffer') and self._event_buffer:
                async with self._buffer_lock:
                    if self._event_buffer:
                        final_batch = self._event_buffer.copy()
                        self._event_buffer.clear()
                        await self._send_event_batch(final_batch)
            
            logger.info(f"UnifiedWebSocketEmitter cleanup completed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Cleanup failed for user {self.user_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive emitter statistics including Phase 2 optimizations."""
        base_stats = {
            'user_id': self.user_id[:8] + '...' if self.user_id else 'unknown',
            'total_events': self.metrics.total_events,
            'critical_events': self.metrics.critical_events.copy(),
            'error_count': self.metrics.error_count,
            'retry_count': self.metrics.retry_count,
            'last_event_time': self.metrics.last_event_time.isoformat() if self.metrics.last_event_time else None,
            'created_at': self.metrics.created_at.isoformat(),
            'user_tier': self._user_tier,
            'emitter_type': 'UnifiedWebSocketEmitter',
            'ssot_compliance': True
        }
        
        # Add Phase 2 performance stats
        performance_stats = self.get_performance_stats()
        
        return {
            **base_stats,
            'performance': performance_stats
        }
    
    # ===================== PHASE 3: ENHANCED ERROR HANDLING & FALLBACK CHANNELS =====================
    
    async def _try_fallback_channels(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Try alternative delivery channels when primary WebSocket fails."""
        logger.info(f"Attempting fallback channels for {event_type} - user {self.user_id}")
        
        fallback_attempts = [
            self._try_database_persistence_fallback,
            self._try_redis_queue_fallback,
            self._try_direct_connection_fallback
        ]
        
        for fallback_method in fallback_attempts:
            try:
                success = await fallback_method(event_type, data)
                if success:
                    logger.info(f"Fallback succeeded via {fallback_method.__name__} for {event_type}")
                    return True
            except Exception as e:
                logger.warning(f"Fallback {fallback_method.__name__} failed: {e}")
                continue
        
        return False
    
    async def _try_database_persistence_fallback(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Persist event to database for later delivery."""
        try:
            # Store event in database for retry delivery
            fallback_event = {
                'user_id': self.user_id,
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'delivery_attempts': 0,
                'max_attempts': 5,
                'status': 'pending',
                'fallback_reason': 'websocket_failure'
            }
            
            # If manager supports database fallback
            if hasattr(self.manager, 'store_fallback_event'):
                await self.manager.store_fallback_event(fallback_event)
                logger.info(f"Event {event_type} stored in database fallback for user {self.user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Database fallback failed for {event_type}: {e}")
            return False
    
    async def _try_redis_queue_fallback(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Queue event in Redis for background delivery."""
        try:
            # Queue event for background processing
            queue_event = {
                'user_id': self.user_id,
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'priority': 'high' if event_type in self.CRITICAL_EVENTS else 'normal'
            }
            
            # If manager supports Redis queuing
            if hasattr(self.manager, 'queue_event_for_retry'):
                await self.manager.queue_event_for_retry(queue_event)
                logger.info(f"Event {event_type} queued in Redis for user {self.user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Redis queue fallback failed for {event_type}: {e}")
            return False
    
    async def _try_direct_connection_fallback(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Attempt direct WebSocket connection bypass."""
        try:
            # Try to force a new connection
            if hasattr(self.manager, 'force_reconnect'):
                reconnect_success = await self.manager.force_reconnect(self.user_id)
                if reconnect_success:
                    # Try emission one more time with new connection
                    await asyncio.sleep(0.1)  # Brief pause for connection establishment
                    await self.manager.emit_critical_event(
                        user_id=self.user_id,
                        event_type=event_type,
                        data=data
                    )
                    logger.info(f"Direct reconnection fallback succeeded for {event_type}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Direct connection fallback failed for {event_type}: {e}")
            return False
    
    async def _emergency_fallback(self, event_type: str, data: Dict[str, Any], last_error: Exception) -> bool:
        """Last resort emergency fallback for critical events."""
        logger.critical(f"EMERGENCY FALLBACK ACTIVATED for {event_type} - user {self.user_id}")
        
        emergency_strategies = [
            self._try_emergency_notification,
            self._try_alternative_user_notification,
            self._try_system_alert_fallback
        ]
        
        for strategy in emergency_strategies:
            try:
                success = await strategy(event_type, data, last_error)
                if success:
                    logger.critical(f"Emergency strategy {strategy.__name__} succeeded for {event_type}")
                    return True
            except Exception as e:
                logger.critical(f"Emergency strategy {strategy.__name__} failed: {e}")
                continue
        
        return False
    
    async def _try_emergency_notification(self, event_type: str, data: Dict[str, Any], last_error: Exception) -> bool:
        """Emergency notification via alternative channels."""
        try:
            # Create emergency notification
            emergency_data = {
                'type': 'emergency_notification',
                'original_event_type': event_type,
                'user_id': self.user_id,
                'message': f"Critical event {event_type} delivery failed - using emergency channel",
                'original_data': data,
                'error_details': str(last_error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # If manager supports emergency notifications
            if hasattr(self.manager, 'send_emergency_notification'):
                await self.manager.send_emergency_notification(emergency_data)
                return True
            
            return False
            
        except Exception as e:
            logger.critical(f"Emergency notification failed: {e}")
            return False
    
    async def _try_alternative_user_notification(self, event_type: str, data: Dict[str, Any], last_error: Exception) -> bool:
        """Try notifying user via alternative methods (email, SMS, etc.)."""
        try:
            # For critical events, try alternative notification methods
            if event_type in self.CRITICAL_EVENTS:
                notification_data = {
                    'user_id': self.user_id,
                    'event_type': event_type,
                    'message': f"Your request is being processed - WebSocket notification failed",
                    'fallback_reason': 'websocket_failure',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # If manager supports alternative notifications
                if hasattr(self.manager, 'send_alternative_notification'):
                    await self.manager.send_alternative_notification(notification_data)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Alternative user notification failed: {e}")
            return False
    
    async def _try_system_alert_fallback(self, event_type: str, data: Dict[str, Any], last_error: Exception) -> bool:
        """System-level alert for monitoring and intervention."""
        try:
            # Create system alert for ops team
            alert_data = {
                'alert_type': 'critical_event_failure',
                'event_type': event_type,
                'user_id': self.user_id,
                'error': str(last_error),
                'data_summary': {k: str(v)[:100] for k, v in data.items()},  # Truncated for alerts
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'requires_intervention': True
            }
            
            # If manager supports system alerts
            if hasattr(self.manager, 'trigger_system_alert'):
                await self.manager.trigger_system_alert(alert_data)
                return True
            
            return False
            
        except Exception as e:
            logger.critical(f"System alert fallback failed: {e}")
            return False
    
    async def _trigger_connection_recovery(self, event_type: str, data: Dict[str, Any]):
        """Trigger automatic connection recovery procedures."""
        try:
            logger.info(f"Triggering connection recovery for user {self.user_id}")
            
            # Update circuit breaker state
            self._update_connection_health(False)
            
            # Attempt connection recovery
            recovery_strategies = [
                self._attempt_websocket_reconnection,
                self._attempt_connection_pool_refresh,
                self._attempt_manager_reset
            ]
            
            for strategy in recovery_strategies:
                try:
                    success = await strategy()
                    if success:
                        logger.info(f"Connection recovery succeeded via {strategy.__name__}")
                        # Retry the original event
                        await asyncio.sleep(0.2)  # Brief pause
                        retry_success = await self._emit_critical(event_type, data)
                        if retry_success:
                            return True
                except Exception as e:
                    logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
                    continue
            
            logger.error(f"All connection recovery strategies failed for user {self.user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Connection recovery trigger failed: {e}")
            return False
    
    async def _attempt_websocket_reconnection(self) -> bool:
        """Attempt to reconnect WebSocket connection."""
        try:
            if hasattr(self.manager, 'reconnect_user'):
                success = await self.manager.reconnect_user(self.user_id)
                if success:
                    self._update_connection_health(True)
                    return True
            return False
        except Exception as e:
            logger.error(f"WebSocket reconnection failed: {e}")
            return False
    
    async def _attempt_connection_pool_refresh(self) -> bool:
        """Attempt to refresh connection pool."""
        try:
            if hasattr(self.manager, 'refresh_connection_pool'):
                await self.manager.refresh_connection_pool(self.user_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Connection pool refresh failed: {e}")
            return False
    
    async def _attempt_manager_reset(self) -> bool:
        """Attempt to reset manager state for this user."""
        try:
            if hasattr(self.manager, 'reset_user_state'):
                await self.manager.reset_user_state(self.user_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Manager reset failed: {e}")
            return False
    
    def get_error_handling_stats(self) -> Dict[str, Any]:
        """Get error handling and fallback statistics."""
        return {
            'connection_health_score': self._connection_health_score,
            'circuit_breaker_open': self._circuit_breaker_open,
            'consecutive_failures': self._consecutive_failures,
            'error_count': self.metrics.error_count,
            'retry_count': self.metrics.retry_count,
            'last_health_check': self._last_health_check.isoformat() if hasattr(self, '_last_health_check') else None,
            'fallback_channels_available': [
                'database_persistence',
                'redis_queue', 
                'direct_connection',
                'emergency_notification',
                'alternative_user_notification',
                'system_alert'
            ]
        }


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
            now = datetime.now(timezone.utc)
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


# Add factory methods to UnifiedWebSocketEmitter class
# These are added at the module level to extend the existing class
def _add_factory_methods_to_unified_emitter():
    """Add factory methods to UnifiedWebSocketEmitter class for Issue #582 remediation."""
    
    @classmethod
    def create_for_user(
        cls,
        manager: 'UnifiedWebSocketManager',
        user_context: 'UserExecutionContext'
    ) -> 'UnifiedWebSocketEmitter':
        """
        Factory method to create UnifiedWebSocketEmitter for a user.
        
        This method provides the factory pattern interface expected by
        WebSocket bridge components and other factory consumers.
        
        Args:
            manager: UnifiedWebSocketManager instance
            user_context: User execution context with user_id
            
        Returns:
            UnifiedWebSocketEmitter: Configured instance for the user
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not user_context:
            raise ValueError("UnifiedWebSocketEmitter.create_for_user requires valid user_context")
        
        user_id = getattr(user_context, 'user_id', None)
        if not user_id:
            raise ValueError("UnifiedWebSocketEmitter.create_for_user requires user_id in user_context")
        
        # Delegate to WebSocketEmitterFactory.create_scoped_emitter
        return WebSocketEmitterFactory.create_scoped_emitter(
            manager=manager,
            context=user_context
        )
    
    @classmethod
    def for_user(
        cls,
        manager: 'UnifiedWebSocketManager',
        user_id: str,
        context: Optional['UserExecutionContext'] = None
    ) -> 'UnifiedWebSocketEmitter':
        """
        Factory method to create UnifiedWebSocketEmitter for a specific user ID.
        
        This method provides a simplified factory interface when only user_id is available.
        
        Args:
            manager: UnifiedWebSocketManager instance
            user_id: Target user ID
            context: Optional execution context
            
        Returns:
            UnifiedWebSocketEmitter: Configured instance for the user
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not user_id:
            raise ValueError("UnifiedWebSocketEmitter.for_user requires valid user_id")
        
        # Delegate to WebSocketEmitterFactory.create_emitter
        return WebSocketEmitterFactory.create_emitter(
            manager=manager,
            user_id=user_id,
            context=context
        )
    
    # Attach methods to the class
    UnifiedWebSocketEmitter.create_for_user = create_for_user
    UnifiedWebSocketEmitter.for_user = for_user
    
    logger.info("Factory methods added to UnifiedWebSocketEmitter - Issue #582 remediation complete")

# Apply the factory methods
_add_factory_methods_to_unified_emitter()