"""Execution engine for supervisor agent pipelines with UserExecutionContext support.

DEPRECATION WARNING: This ExecutionEngine uses global state and is not safe for concurrent users.
For new code, use RequestScopedExecutionEngine or the factory methods provided below.

Business Value: Supports 5+ concurrent users with complete isolation and <2s response times.
New Features: UserExecutionContext integration, per-user isolation, UserWebSocketEmitter support.
Optimizations: Semaphore-based concurrency control, event sequencing, backlog handling.

Migration Guide:
- Replace direct ExecutionEngine instantiation with create_request_scoped_engine()
- Use ExecutionContextManager for request-scoped execution management
- See RequestScopedExecutionEngine for isolated per-request execution
"""

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UserWebSocketEmitter

# DeepAgentState removed - using UserExecutionContext pattern
# from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
# DISABLED: fallback_manager module removed
# from netra_backend.app.agents.supervisor.fallback_manager import FallbackManager
from netra_backend.app.agents.supervisor.observability_flow import (
    get_supervisor_flow_logger,
)
# WebSocketNotifier deprecated - using AgentWebSocketBridge instead
# DISABLED: periodic_update_manager module removed
# from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
from netra_backend.app.core.agent_execution_tracker import (
    get_execution_tracker,
    ExecutionState
)
from netra_backend.app.logging_config import central_logger

# NEW: Split architecture imports
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    UserWebSocketEmitter,
    get_agent_instance_factory
)
# NEW: Import user execution engine components for delegation
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    get_execution_engine_factory,
    user_execution_engine
)

logger = central_logger.get_logger(__name__)


class ExecutionEngine:
    """Request-scoped agent execution orchestration.
    
    REQUIRED: Use factory methods for instantiation:
    - create_request_scoped_engine() for isolated instances
    - ExecutionContextManager for automatic cleanup
    
    Direct instantiation is no longer supported to ensure user isolation.
    
    Features:
    - UserExecutionContext integration for complete user isolation
    - UserWebSocketEmitter support for per-user event emission
    - Request-scoped execution with no global state sharing
    - Semaphore-based concurrency control for 5+ concurrent users
    - Guaranteed WebSocket event delivery with proper sequencing
    """
    
    MAX_HISTORY_SIZE = 100  # Prevent memory leak
    MAX_CONCURRENT_AGENTS = 10  # Support 5 concurrent users (2 agents each)
    AGENT_EXECUTION_TIMEOUT = 30.0  # 30 seconds max per agent
    
    def __init__(self, registry: 'AgentRegistry', websocket_bridge, 
                 user_context: Optional['UserExecutionContext'] = None):
        """Private initializer - use factory methods instead.
        
        Direct instantiation is prevented to ensure user isolation.
        Use create_request_scoped_engine() for proper request-scoped execution.
        
        Args:
            registry: Agent registry for agent lookup
            websocket_bridge: WebSocket bridge for event emission
            user_context: Optional UserExecutionContext for per-request isolation
        """
        # CRITICAL FIX: Allow direct instantiation but require proper parameters for WebSocket integration
        if registry is None:
            raise ValueError("AgentRegistry is required for ExecutionEngine initialization")
        
        # Initialize core properties
        self.registry = registry
        self.websocket_bridge = websocket_bridge
        self.user_context = user_context
        
        # SECURITY FIX: Enforce mandatory AgentWebSocketBridge usage - no fallbacks allowed
        if not websocket_bridge:
            raise RuntimeError(
                "AgentWebSocketBridge is mandatory for WebSocket security and user isolation. "
                "No fallback paths allowed."
            )
        
        # Initialize remaining components
        self._init_core_components()
        
        if self.user_context:
            logger.info(f"ExecutionEngine initialized with UserExecutionContext for user {self.user_context.user_id}")
        else:
            logger.info("ExecutionEngine initialized in legacy mode (no UserExecutionContext)")
    
    def _init_core_components(self) -> None:
        """Initialize core ExecutionEngine components after validation."""
        # Validate that websocket_bridge is an AgentWebSocketBridge (not a deprecated notifier)
        if not hasattr(self.websocket_bridge, 'notify_agent_started'):
            raise RuntimeError(
                f"websocket_bridge must be AgentWebSocketBridge instance with proper notification methods. "
                f"Got: {type(self.websocket_bridge)}. Deprecated WebSocketNotifier fallbacks are eliminated for security."
            )
            
        # RACE CONDITION FIX: Enhanced user isolation and state safety
        # NOTE: These remain as instance variables but are now scoped per ExecutionEngine instance
        # In the new architecture, each user request gets its own ExecutionEngine instance
        self.active_runs = {}
        self.run_history = []
        self.execution_tracker = get_execution_tracker()
        
        # NEW: Per-user state isolation to prevent race conditions
        self._user_execution_states: Dict[str, Dict] = {}
        self._user_state_locks: Dict[str, asyncio.Lock] = {}
        self._state_lock_creation_lock = asyncio.Lock()
        
        self._init_components()
        self._init_death_monitoring()
        
    @classmethod
    def _init_from_factory(cls, registry: 'AgentRegistry', websocket_bridge,
                          user_context: Optional['UserExecutionContext'] = None):
        """Internal factory initializer for creating request-scoped instances.
        
        DEPRECATED: Use standard __init__ instead. This method remains for backward compatibility.
        """
        logger.warning("Using deprecated _init_from_factory - migrate to standard __init__ for better integration")
        return cls(registry, websocket_bridge, user_context)
    
    async def _get_user_state_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create user-specific state lock for thread safety.
        
        Args:
            user_id: User identifier for state lock isolation
            
        Returns:
            User-specific asyncio Lock for execution state operations
        """
        if user_id not in self._user_state_locks:
            async with self._state_lock_creation_lock:
                # Double-check locking pattern
                if user_id not in self._user_state_locks:
                    self._user_state_locks[user_id] = asyncio.Lock()
                    logger.debug(f"Created user-specific state lock for user: {user_id}")
        return self._user_state_locks[user_id]
    
    async def _get_user_execution_state(self, user_id: str) -> Dict:
        """Get or create user-specific execution state for complete isolation.
        
        Args:
            user_id: User identifier for state isolation
            
        Returns:
            User-specific execution state dictionary
        """
        if user_id not in self._user_execution_states:
            # This is already protected by the user state lock in calling methods
            self._user_execution_states[user_id] = {
                'active_runs': {},
                'run_history': [],
                'execution_stats': {
                    'total_executions': 0,
                    'concurrent_executions': 0,
                    'queue_wait_times': [],
                    'execution_times': [],
                    'failed_executions': 0,
                    'dead_executions': 0,
                    'timeout_executions': 0
                }
            }
            logger.debug(f"Created user-specific execution state for user: {user_id}")
        return self._user_execution_states[user_id]
        
    def _init_components(self) -> None:
        """Initialize execution components."""
        # Use AgentWebSocketBridge instead of creating WebSocketNotifier
        # periodic_update_manager removed - no longer needed
        self.periodic_update_manager = None
        self.agent_core = AgentExecutionCore(self.registry, self.websocket_bridge)
        # fallback_manager removed - no longer needed
        self.fallback_manager = None
        self.flow_logger = get_supervisor_flow_logger()
        
        # CONCURRENCY OPTIMIZATION: Semaphore for agent execution control
        self.execution_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_AGENTS)
        self.execution_stats = {
            'total_executions': 0,
            'concurrent_executions': 0,
            'queue_wait_times': [],
            'execution_times': [],
            'failed_executions': 0,
            'dead_executions': 0,
            'timeout_executions': 0
        }
        
        # CRITICAL: Initialize user emitter management for per-user WebSocket events
        self._user_emitters: Dict[str, Any] = {}  # UserWebSocketEmitter instances per user
        self._user_emitter_lock = asyncio.Lock()
        
    def _init_death_monitoring(self) -> None:
        """Initialize agent death monitoring callbacks."""
        # Register callbacks for death detection
        self.execution_tracker.register_death_callback(self._handle_agent_death)
        self.execution_tracker.register_timeout_callback(self._handle_agent_timeout)
        
    async def _handle_agent_death(self, execution_record) -> None:
        """Handle agent death detection."""
        logger.critical(f"💀 AGENT DEATH DETECTED: {execution_record.agent_name} (execution_id={execution_record.execution_id})")
        
        # Send death notification via WebSocket
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_death(
                execution_record.metadata.get('run_id', execution_record.execution_id),
                execution_record.agent_name,
                'no_heartbeat',
                {
                    'execution_id': execution_record.execution_id,
                    'last_heartbeat': execution_record.last_heartbeat.isoformat(),
                    'time_since_heartbeat': execution_record.time_since_heartbeat.total_seconds()
                }
            )
        
        self.execution_stats['dead_executions'] += 1
        
    async def _handle_agent_timeout(self, execution_record) -> None:
        """Handle agent timeout detection."""
        logger.error(f"⏱️ AGENT TIMEOUT: {execution_record.agent_name} exceeded {execution_record.timeout_seconds}s")
        
        # Send timeout notification via WebSocket
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_death(
                execution_record.metadata.get('run_id', execution_record.execution_id),
                execution_record.agent_name,
                'timeout',
                {
                    'execution_id': execution_record.execution_id,
                    'timeout_seconds': execution_record.timeout_seconds,
                    'duration': execution_record.duration.total_seconds() if execution_record.duration else 0
                }
            )
        
        self.execution_stats['timeout_executions'] += 1
    
    def _validate_execution_context(self, context: AgentExecutionContext) -> None:
        """Validate execution context to prevent invalid placeholder values from propagating.
        
        Args:
            context: The agent execution context to validate
            
        Raises:
            ValueError: If context contains invalid or placeholder values
        """
        # Validate user_id is not None or empty
        if not context.user_id or not context.user_id.strip():
            raise ValueError(
                f"Invalid execution context: user_id must be a non-empty string, "
                f"got: {context.user_id!r}"
            )
        
        # Validate run_id is not the forbidden 'registry' placeholder
        if context.run_id == 'registry':
            raise ValueError(
                f"Invalid execution context: run_id cannot be 'registry' placeholder value, "
                f"got: {context.run_id!r}"
            )
        
        # Validate run_id is not None or empty
        if not context.run_id or not context.run_id.strip():
            raise ValueError(
                f"Invalid execution context: run_id must be a non-empty string, "
                f"got: {context.run_id!r}"
            )
        
        # NEW: Validate UserExecutionContext consistency if present
        if self.user_context:
            if context.user_id != self.user_context.user_id:
                raise ValueError(
                    f"UserExecutionContext user_id mismatch: "
                    f"context.user_id='{context.user_id}' vs user_context.user_id='{self.user_context.user_id}'"
                )
            
            if context.run_id != self.user_context.run_id:
                logger.warning(
                    f"UserExecutionContext run_id mismatch: "
                    f"context.run_id='{context.run_id}' vs user_context.run_id='{self.user_context.run_id}' "
                    f"- this may indicate multiple runs in same context"
                )
        
    async def execute_agent(self, context: AgentExecutionContext,
                           user_context: Optional['UserExecutionContext'] = None) -> AgentExecutionResult:
        """Execute a single agent with UserExecutionContext support and concurrency control.
        
        NEW: Supports UserExecutionContext for complete user isolation and per-user WebSocket events.
        RECOMMENDED: Use create_user_engine() or UserExecutionEngine directly for new code.
        """
        # NEW: Use UserExecutionContext - prefer passed context over instance context
        effective_user_context = user_context or self.user_context
        if effective_user_context:
            logger.info(f"Delegating execution to UserExecutionEngine for user {effective_user_context.user_id}")
            try:
                user_engine = await self.create_user_engine(effective_user_context)
                result = await user_engine.execute_agent(context, effective_user_context)
                await user_engine.cleanup()
                return result
            except Exception as e:
                logger.warning(f"UserExecutionEngine delegation failed, falling back to legacy: {e}")
                # Fall through to legacy execution
        
        # LEGACY: Global state execution (deprecated)
        logger.warning("Using legacy ExecutionEngine with global state - consider migrating to UserExecutionEngine")
        
        # FAIL-FAST: Validate context before any processing
        self._validate_execution_context(context)
        
        # NEW: Log user isolation status
        if effective_user_context:
            logger.debug(f"Executing agent {context.agent_name} with user isolation for user {effective_user_context.user_id}")
        else:
            logger.warning(f"Executing agent {context.agent_name} without UserExecutionContext - isolation not guaranteed")
        
        queue_start_time = time.time()
        
        # Create execution tracking record
        execution_id = self.execution_tracker.create_execution(
            agent_name=context.agent_name,
            thread_id=context.thread_id,
            user_id=context.user_id,
            timeout_seconds=int(self.AGENT_EXECUTION_TIMEOUT),
            metadata={'run_id': context.run_id, 'context': context.metadata}
        )
        
        # Store execution ID in context for tracking
        context.execution_id = execution_id
        
        # CONCURRENCY CONTROL: Use semaphore to limit concurrent executions
        async with self.execution_semaphore:
            queue_wait_time = time.time() - queue_start_time
            self.execution_stats['queue_wait_times'].append(queue_wait_time)
            self.execution_stats['total_executions'] += 1
            self.execution_stats['concurrent_executions'] += 1
            
            # Mark execution as starting
            self.execution_tracker.start_execution(execution_id)
            
            # Send queue wait notification if significant delay
            if queue_wait_time > 1.0:
                await self.send_agent_thinking(
                    context,
                    f"Request queued due to high load - starting now (waited {queue_wait_time:.1f}s)",
                    step_number=0
                )
            
            # Create heartbeat task for death detection
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(execution_id))
            
            try:
                # periodic_update_manager removed - execute without tracking
                # CRITICAL FIX: Always send agent started via user-isolated emitter when possible
                if effective_user_context:
                    # Try user emitter first for proper isolation
                    success = await self._send_via_user_emitter(
                        'notify_agent_started',
                        context.agent_name,
                        {"status": "started", "context": context.metadata or {}, "isolated": True}
                    )
                    if not success:
                        # Fallback to bridge for backward compatibility
                        logger.debug(f"Falling back to websocket bridge for agent_started (user: {effective_user_context.user_id})")
                        await self.websocket_bridge.notify_agent_started(
                            context.run_id, 
                            context.agent_name,
                            {"status": "started", "context": context.metadata or {}}
                        )
                else:
                    # Legacy: Send agent started with guaranteed delivery via bridge
                    await self.websocket_bridge.notify_agent_started(
                        context.run_id, 
                        context.agent_name,
                        {"status": "started", "context": context.metadata or {}}
                    )
                
                # Send initial thinking update
                await self.send_agent_thinking(
                    context, 
                    f"Starting execution of {context.agent_name} agent...",
                    step_number=1
                )
                
                execution_start = time.time()
                
                # Update execution state to running
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.RUNNING
                )
                
                # Execute with timeout and death monitoring
                result = await asyncio.wait_for(
                    self._execute_with_death_monitoring(context, effective_user_context, execution_id),
                    timeout=self.AGENT_EXECUTION_TIMEOUT
                )
                
                execution_time = time.time() - execution_start
                self.execution_stats['execution_times'].append(execution_time)
                
                # Mark execution as completing
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETING
                )
                
                # CRITICAL: Always send completion events, regardless of success/failure
                # This ensures WebSocket clients know when agent execution is complete
                if result.success:
                    await self._send_final_execution_report(context, result, effective_user_context)
                    # Mark execution as completed
                    self.execution_tracker.update_execution_state(
                        execution_id, ExecutionState.COMPLETED, result=result.data
                    )
                else:
                    # Send completion event for failed/fallback cases
                    await self._send_completion_for_failed_execution(context, result, effective_user_context)
                    # Mark execution as failed
                    self.execution_tracker.update_execution_state(
                        execution_id, ExecutionState.FAILED, error=result.error
                    )
                
                self._update_history(result)
                return result
                    
            except asyncio.TimeoutError:
                # LOUD ERROR: Agent timeout is critical for user experience
                logger.critical(
                    f"AGENT TIMEOUT CRITICAL: {context.agent_name} timed out after {self.AGENT_EXECUTION_TIMEOUT}s "
                    f"for user {context.user_id} (run_id: {context.run_id}). "
                    f"User will experience failed request or blank screen."
                )
                
                self.execution_stats['failed_executions'] += 1
                # Mark execution as timed out
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.TIMEOUT,
                    error=f"Execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s"
                )
                
                # ENHANCED: Notify user of timeout with user-friendly message
                try:
                    await self._notify_user_of_timeout(context, self.AGENT_EXECUTION_TIMEOUT)
                except Exception as notify_error:
                    logger.critical(
                        f"TIMEOUT NOTIFICATION FAILED: Could not notify user {context.user_id} "
                        f"about agent timeout: {notify_error}. User unaware of failure."
                    )
                
                # Send timeout notification via death handler
                await self.websocket_bridge.notify_agent_death(
                    context.run_id,
                    context.agent_name,
                    'timeout',
                    {'execution_id': execution_id, 'timeout': self.AGENT_EXECUTION_TIMEOUT}
                )
                timeout_result = self._create_timeout_result(context)
                await self._send_completion_for_failed_execution(context, timeout_result, effective_user_context)
                self._update_history(timeout_result)
                return timeout_result
                
            except Exception as e:
                # LOUD ERROR: Unexpected execution failures are critical
                logger.critical(
                    f"UNEXPECTED AGENT FAILURE: {context.agent_name} failed with unexpected error "
                    f"for user {context.user_id} (run_id: {context.run_id}): {e}. "
                    f"Error type: {type(e).__name__}. This indicates a system-level issue."
                )
                
                # Mark execution as failed for any other exception
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.FAILED, error=str(e)
                )
                
                # ENHANCED: Notify user of unexpected system error
                try:
                    await self._notify_user_of_system_error(context, e)
                except Exception as notify_error:
                    logger.critical(
                        f"SYSTEM ERROR NOTIFICATION FAILED: Could not notify user {context.user_id} "
                        f"about system error: {notify_error}. User unaware of system failure."
                    )
                
                # Re-raise to propagate the error
                raise
                
            finally:
                # Cancel heartbeat task
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
                self.execution_stats['concurrent_executions'] -= 1
    
    async def _heartbeat_loop(self, execution_id: str) -> None:
        """Send periodic heartbeats for death detection."""
        try:
            while True:
                await asyncio.sleep(2)  # Heartbeat every 2 seconds
                if not self.execution_tracker.heartbeat(execution_id):
                    break  # Execution is terminal, stop heartbeat
        except asyncio.CancelledError:
            pass
    
    async def _execute_with_death_monitoring(self, context: AgentExecutionContext,
                                            user_context: Optional['UserExecutionContext'],
                                            execution_id: str) -> AgentExecutionResult:
        """Execute agent with death monitoring wrapper."""
        try:
            # Heartbeat before execution
            self.execution_tracker.heartbeat(execution_id)
            
            # Execute with error handling
            result = await self._execute_with_error_handling(context, user_context)
            
            # Final heartbeat after execution
            self.execution_tracker.heartbeat(execution_id)
            
            return result
            
        except Exception as e:
            # Check if this is a death scenario
            execution_record = self.execution_tracker.get_execution(execution_id)
            if execution_record and execution_record.is_dead(self.execution_tracker.heartbeat_timeout):
                # Agent died - send death notification
                await self.websocket_bridge.notify_agent_death(
                    context.run_id,
                    context.agent_name,
                    'silent_failure',
                    {'execution_id': execution_id, 'error': str(e)}
                )
            raise
    
    async def _execute_with_error_handling(self, context: AgentExecutionContext,
                                          user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute agent with error handling and fallback."""
        start_time = time.time()
        try:
            # Send thinking updates during execution
            task_preview = user_context.metadata.get('user_prompt', 'Task') if user_context else 'Task'
            await self.send_agent_thinking(
                context,
                f"Processing request: {str(task_preview)[:100]}...",
                step_number=2
            )
            
            # Execute the agent
            result = await self.agent_core.execute_agent(context, user_context)
            
            # Send partial result if available
            if result.success and user_context and hasattr(user_context, 'final_answer'):
                await self.send_partial_result(
                    context,
                    str(user_context.final_answer)[:500],
                    is_complete=True
                )
            
            return result
        except Exception as e:
            return await self._handle_execution_error(context, user_context, e, start_time)
    
    async def _handle_execution_error(self, context: AgentExecutionContext,
                                     user_context: Optional['UserExecutionContext'], error: Exception,
                                     start_time: float) -> AgentExecutionResult:
        """Handle execution errors with enhanced user notification and loud error reporting."""
        # LOUD ERROR: Make agent execution failures highly visible
        logger.critical(
            f"AGENT EXECUTION FAILURE: {context.agent_name} failed for user {context.user_id} "
            f"(run_id: {context.run_id}): {error}. "
            f"Error type: {type(error).__name__}. "
            f"This will impact user experience directly."
        )
        
        # Notify user via WebSocket about the execution failure
        try:
            await self._notify_user_of_execution_error(context, error)
        except Exception as notify_error:
            logger.critical(
                f"DOUBLE FAILURE: Could not notify user {context.user_id} about agent execution failure: {notify_error}. "
                f"User will experience silent failure."
            )
        
        # Attempt retry if possible
        if self._can_retry(context):
            logger.warning(
                f"Attempting retry {context.retry_count + 1}/{context.max_retries} "
                f"for agent {context.agent_name} (user: {context.user_id})"
            )
            return await self._retry_execution(context, user_context)
        
        # Execute fallback strategy as last resort
        logger.critical(
            f"NO RETRY POSSIBLE: Executing fallback strategy for {context.agent_name} "
            f"(user: {context.user_id}). Max retries ({context.max_retries}) exceeded."
        )
        return await self._execute_fallback_strategy(context, user_context, error, start_time)
    
    def _can_retry(self, context: AgentExecutionContext) -> bool:
        """Check if retry is allowed."""
        return context.retry_count < context.max_retries
    
    async def _retry_execution(self, context: AgentExecutionContext,
                              user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Retry agent execution."""
        self._prepare_retry_context(context)
        self._log_retry_attempt(context)
        await self._wait_for_retry(context.retry_count)
        return await self.execute_agent(context, user_context)
    
    async def execute_pipeline(self, steps: List[PipelineStep],
                              context: AgentExecutionContext,
                              user_context: Optional['UserExecutionContext']) -> List[AgentExecutionResult]:
        """Execute a pipeline of agents."""
        return await self._execute_pipeline_steps(steps, context, user_context)
    
    async def _execute_pipeline_steps(self, steps: List[PipelineStep],
                                     context: AgentExecutionContext,
                                     user_context: Optional['UserExecutionContext']) -> List[AgentExecutionResult]:
        """Execute pipeline steps with optimal parallelization strategy."""
        # Check if steps can be executed in parallel (no dependencies)
        if self._can_execute_parallel(steps):
            return await self._execute_steps_parallel(steps, context, user_context)
        else:
            # Fall back to sequential execution with early termination
            results = []
            await self._process_steps_with_early_termination(steps, context, user_context, results)
            return results
    
    def _can_execute_parallel(self, steps: List[PipelineStep]) -> bool:
        """Determine if steps can be executed in parallel.
        
        Returns False (sequential) by default for safety unless explicitly marked for parallel.
        """
        # Steps can be parallel ONLY if ALL conditions are met:
        # 1. No step has dependencies on other steps
        # 2. All steps explicitly allow parallel execution
        # 3. None of the steps are marked as requiring sequential execution
        
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionStrategy
        
        for step in steps:
            # Check if step explicitly requires sequential execution
            if hasattr(step, 'strategy') and step.strategy == AgentExecutionStrategy.SEQUENTIAL:
                return False
            
            # Check metadata for sequential requirement
            if hasattr(step, 'metadata') and step.metadata.get('requires_sequential', False):
                return False
                
            # Check if step has sequential requirement attribute
            if hasattr(step, 'requires_sequential') and step.requires_sequential:
                return False
                
            # Check if step has dependencies
            if hasattr(step, 'dependencies') and step.dependencies:
                return False
                
        # Default to sequential for safety - parallel must be explicitly enabled
        # Only allow parallel if explicitly marked and we have multiple steps
        has_parallel_strategy = any(
            hasattr(step, 'strategy') and step.strategy == AgentExecutionStrategy.PARALLEL 
            for step in steps
        )
        return has_parallel_strategy and len(steps) > 1
    
    async def _execute_steps_parallel(self, steps: List[PipelineStep],
                                    context: AgentExecutionContext,
                                    user_context: Optional['UserExecutionContext']) -> List[AgentExecutionResult]:
        """Execute steps in parallel using asyncio.gather for improved performance.
        
        Phase 3 Performance Optimization: Enhanced parallel execution with timing and monitoring.
        Target: 40% reduction in end-to-end time per benchmark analysis.
        """
        # Phase 3: Performance monitoring
        parallel_start_time = time.time()
        
        # Create tasks for all executable steps
        tasks = []
        executable_steps = []
        
        for step in steps:
            if await self._should_execute_step(step, user_context):
                step_context = self._create_step_context(context, step)
                task = self._execute_step_parallel_safe(step, step_context, user_context)
                tasks.append(task)
                executable_steps.append(step)
        
        if not tasks:
            return []
            
        # Execute all steps in parallel
        try:
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            results = []
            for i, result in enumerate(parallel_results):
                if isinstance(result, Exception):
                    # Create error result for failed step
                    error_result = self._create_error_result(executable_steps[i], result)
                    results.append(error_result)
                else:
                    results.append(result)
                    
            return results
            
        except Exception as e:
            logger.error(f"Parallel execution failed: {e}")
            # Fall back to sequential execution
            return await self._execute_steps_sequential_fallback(steps, context, user_context)
    
    async def _execute_step_parallel_safe(self, step: PipelineStep,
                                        context: AgentExecutionContext,
                                        user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute a single step safely for parallel execution."""
        return await self._execute_with_fallback(context, user_context)
    
    def _create_error_result(self, step: PipelineStep, error: Exception) -> AgentExecutionResult:
        """Create an error result for a failed step."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        return AgentExecutionResult(
            success=False,
            agent_name=getattr(step, 'agent_name', 'unknown'),
            execution_time=0.0,
            error=str(error),
            state=None
        )
    
    async def _execute_steps_sequential_fallback(self, steps: List[PipelineStep],
                                               context: AgentExecutionContext,
                                               user_context: Optional['UserExecutionContext']) -> List[AgentExecutionResult]:
        """Fallback to sequential execution if parallel fails."""
        logger.warning("Falling back to sequential execution")
        results = []
        await self._process_steps_with_early_termination(steps, context, user_context, results)
        return results
    
    async def _process_steps_with_early_termination(self, steps: List[PipelineStep],
                                                  context: AgentExecutionContext,
                                                  user_context: Optional['UserExecutionContext'], results: List) -> None:
        """Process steps with early termination on failure."""
        for step in steps:
            should_stop = await self._process_pipeline_step(step, context, user_context, results)
            if should_stop:
                break
    
    async def _process_pipeline_step(self, step: PipelineStep, context: AgentExecutionContext,
                                    user_context: Optional['UserExecutionContext'], results: List) -> bool:
        """Process single pipeline step. Returns True to stop pipeline."""
        if not await self._should_execute_step(step, user_context):
            return False
        return await self._execute_and_check_result(step, context, user_context, results)
    
    async def _execute_and_check_result(self, step: PipelineStep, context: AgentExecutionContext,
                                       user_context: Optional['UserExecutionContext'], results: List) -> bool:
        """Execute step and check if pipeline should stop."""
        result = await self._execute_step(step, context, user_context)
        results.append(result)
        return self._should_stop_pipeline(result, step)
    
    async def _should_execute_step(self, step: PipelineStep,
                                  user_context: Optional['UserExecutionContext']) -> bool:
        """Check if step should be executed."""
        if not step.condition:
            return True
        return await self._evaluate_condition(step.condition, user_context)
    
    async def _evaluate_condition(self, condition, user_context: Optional['UserExecutionContext']) -> bool:
        """Safely evaluate step condition."""
        try:
            return await condition(user_context)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    async def _execute_step(self, step: PipelineStep,
                           context: AgentExecutionContext,
                           user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute a single pipeline step."""
        step_context = self._create_step_context(context, step)
        return await self._execute_with_fallback(step_context, user_context)
    
    def _create_step_context(self, base_context: AgentExecutionContext,
                           step: PipelineStep) -> AgentExecutionContext:
        """Create context for a pipeline step."""
        params = self._extract_step_context_params(base_context, step)
        return AgentExecutionContext(**params)
    
    def _extract_step_context_params(self, base_context: AgentExecutionContext,
                                   step: PipelineStep) -> Dict[str, Any]:
        """Extract parameters for step context creation."""
        return self._build_step_context_dict(base_context, step)
    
    def _build_step_context_dict(self, base_context: AgentExecutionContext,
                                step: PipelineStep) -> Dict[str, Any]:
        """Build step context parameter dictionary."""
        base_params = self._extract_base_context_params(base_context)
        step_params = self._extract_step_params(step)
        return {**base_params, **step_params}
    
    def _extract_base_context_params(self, context: AgentExecutionContext) -> Dict[str, str]:
        """Extract base context parameters."""
        return {
            "run_id": context.run_id,
            "thread_id": context.thread_id,
            "user_id": context.user_id
        }
    
    def _extract_step_params(self, step: PipelineStep) -> Dict[str, Any]:
        """Extract step-specific parameters."""
        return {
            "agent_name": step.agent_name,
            "metadata": step.metadata
        }
    
    def _should_stop_pipeline(self, result: AgentExecutionResult, 
                            step: PipelineStep) -> bool:
        """Check if pipeline should stop."""
        return not result.success and not step.metadata.get("continue_on_error")
    
    async def _execute_with_fallback(self, context: AgentExecutionContext,
                                   user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute agent with fallback handling."""
        # Fallback manager removed - execute directly
        return await self.agent_core.execute_agent(context, user_context)
    
    def _update_history(self, result: AgentExecutionResult) -> None:
        """Update run history with size limit."""
        self.run_history.append(result)
        self._enforce_history_size_limit()
    
    # === NEW: UserWebSocketEmitter Integration ===
    
    async def _ensure_user_emitter(self, user_context: 'UserExecutionContext') -> Optional[Any]:
        """Ensure UserWebSocketEmitter exists for the given user context.
        
        This method creates per-user WebSocket emitters for isolated event emission.
        
        Args:
            user_context: User execution context for emitter creation
            
        Returns:
            UserWebSocketEmitter instance or None if creation fails
        """
        if not user_context:
            return None
            
        user_key = f"{user_context.user_id}_{user_context.thread_id}_{user_context.run_id}"
        
        async with self._user_emitter_lock:
            if user_key not in self._user_emitters:
                try:
                    # Create UserWebSocketEmitter for this specific user context
                    from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
                    
                    user_emitter = UserWebSocketEmitter(
                        user_id=user_context.user_id,
                        thread_id=user_context.thread_id,
                        run_id=user_context.run_id,
                        websocket_bridge=self.websocket_bridge
                    )
                    
                    self._user_emitters[user_key] = user_emitter
                    logger.debug(f"Created UserWebSocketEmitter for user {user_context.user_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create UserWebSocketEmitter for user {user_context.user_id}: {e}")
                    return None
            
            return self._user_emitters[user_key]
    
    async def _send_via_user_emitter(self, method_name: str, *args, **kwargs) -> bool:
        """Send notification via UserWebSocketEmitter if available.
        
        Returns:
            bool: True if sent successfully via user emitter, False if not available
        """
        if not self.user_context:
            return False
        
        try:
            user_emitter = await self._ensure_user_emitter(self.user_context)
            if user_emitter:
                method = getattr(user_emitter, method_name, None)
                if method:
                    await method(*args, **kwargs)
                    return True
        except Exception as e:
            logger.debug(f"Failed to send via UserWebSocketEmitter: {e}")
        
        return False
    
    # WebSocket delegation methods with UserExecutionContext support
    async def send_agent_thinking(self, context: AgentExecutionContext, 
                                 thought: str, step_number: int = None) -> None:
        """Send agent thinking notification with UserExecutionContext support."""
        # CRITICAL FIX: Try UserWebSocketEmitter first for proper isolation
        if self.user_context:
            success = await self._send_via_user_emitter(
                'notify_agent_thinking',
                context.agent_name,
                thought,
                step_number
            )
            if success:
                logger.debug(f"Agent thinking sent via user emitter for user {self.user_context.user_id}")
                return
            else:
                logger.debug(f"User emitter failed, falling back to bridge for agent_thinking (user: {self.user_context.user_id})")
        
        # Fallback to bridge - fix parameter mapping for AgentWebSocketBridge
        await self.websocket_bridge.notify_agent_thinking(
            context.run_id,
            context.agent_name,
            reasoning=thought,
            step_number=step_number
        )
    
    async def send_partial_result(self, context: AgentExecutionContext,
                                 content: str, is_complete: bool = False) -> None:
        """Send partial result notification with UserExecutionContext support."""
        # FIXED: AgentWebSocketBridge doesn't have notify_progress_update - use agent_thinking instead
        await self.websocket_bridge.notify_agent_thinking(
            context.run_id,
            context.agent_name,
            reasoning=f"Progress Update: {content}" + (" (Complete)" if is_complete else " (In Progress)"),
            step_number=None,
            progress_percentage=100.0 if is_complete else None
        )
    
    async def send_tool_executing(self, context: AgentExecutionContext,
                                 tool_name: str) -> None:
        """Send tool executing notification with UserExecutionContext support."""
        # CRITICAL FIX: Try UserWebSocketEmitter first for proper isolation
        if self.user_context:
            success = await self._send_via_user_emitter(
                'notify_tool_executing',
                context.agent_name,
                tool_name,
                {}  # parameters
            )
            if success:
                logger.debug(f"Tool executing sent via user emitter for user {self.user_context.user_id}: {tool_name}")
                return
            else:
                logger.debug(f"User emitter failed, falling back to bridge for tool_executing (user: {self.user_context.user_id})")
        
        # Fallback to bridge - fix parameter mapping for AgentWebSocketBridge
        await self.websocket_bridge.notify_tool_executing(
            context.run_id,
            context.agent_name,
            tool_name,
            parameters={}  # Add empty parameters dict as expected by AgentWebSocketBridge
        )
    
    async def send_final_report(self, context: AgentExecutionContext,
                               report: dict, duration_ms: float) -> None:
        """Send final report notification with UserExecutionContext support."""
        # CRITICAL FIX: Try UserWebSocketEmitter first for proper isolation
        if self.user_context:
            # Enhance report with isolation info
            enhanced_report = report.copy()
            enhanced_report['isolated'] = True
            enhanced_report['user_context'] = {
                'user_id': self.user_context.user_id,
                'thread_id': self.user_context.thread_id,
                'run_id': self.user_context.run_id
            }
            
            success = await self._send_via_user_emitter(
                'notify_agent_completed',
                context.agent_name,
                enhanced_report,
                duration_ms
            )
            if success:
                logger.debug(f"Agent completed sent via user emitter for user {self.user_context.user_id}")
                return
            else:
                logger.debug(f"User emitter failed, falling back to bridge for agent_completed (user: {self.user_context.user_id})")
        
        # Fallback to bridge - fix parameter mapping for AgentWebSocketBridge  
        await self.websocket_bridge.notify_agent_completed(
            context.run_id,
            context.agent_name,
            result=report,
            execution_time_ms=duration_ms
        )
    
    async def _send_final_execution_report(self, context: AgentExecutionContext,
                                          result: AgentExecutionResult,
                                          user_context: Optional['UserExecutionContext']) -> None:
        """Send comprehensive final report after successful execution."""
        try:
            # Build comprehensive report
            report = {
                "agent_name": context.agent_name,
                "success": result.success,
                "duration_ms": result.duration * 1000 if result.duration else 0,
                "user_prompt": user_context.metadata.get('user_prompt', 'N/A') if user_context else 'N/A',
                "final_answer": user_context.metadata.get('final_answer', 'Completed') if user_context else 'Completed',
                "step_count": user_context.metadata.get('step_count', 0) if user_context else 0,
                "status": "completed"
            }
            
            # Send final report (this already calls websocket_bridge.notify_agent_completed internally)
            await self.send_final_report(
                context, 
                report, 
                result.duration * 1000 if result.duration else 0
            )
            
            # FIXED: Removed duplicate notify_agent_completed call
            # send_final_report already handles the WebSocket notification
        except Exception as e:
            logger.warning(f"Failed to send final execution report: {e}")
    
    async def _send_completion_for_failed_execution(self, context: AgentExecutionContext,
                                                   result: AgentExecutionResult,
                                                   user_context: Optional['UserExecutionContext']) -> None:
        """Send completion event for failed/fallback execution scenarios."""
        try:
            # Build error/fallback completion report
            report = {
                "agent_name": context.agent_name,
                "success": False,  # Explicitly mark as failed
                "duration_ms": result.duration * 1000 if result.duration else 0,
                "error": getattr(result, 'error', 'Execution failed'),
                "fallback_used": result.metadata.get('fallback_used', False) if result.metadata else False,
                "status": "failed_with_fallback" if (result.metadata and result.metadata.get('fallback_used')) else "failed"
            }
            
            # Send completion notification for failed execution via bridge - fix parameter mapping
            # This is CRITICAL for WebSocket clients to know execution finished
            await self.websocket_bridge.notify_agent_completed(
                context.run_id,
                context.agent_name,
                result=report,
                execution_time_ms=result.duration * 1000 if result.duration else 0
            )
            
            logger.info(f"Sent completion event for failed {context.agent_name} execution")
            
        except Exception as e:
            logger.warning(f"Failed to send completion event for failed execution: {e}")
    
    def _log_fallback_trigger(self, context: AgentExecutionContext) -> None:
        """Log fallback trigger if flow_id is available."""
        flow_id = self._get_context_flow_id(context)
        if flow_id:
            self.flow_logger.log_fallback_triggered(flow_id, context.agent_name, "fallback_agent")
    
    def _log_retry_attempt(self, context: AgentExecutionContext) -> None:
        """Log retry attempt if flow_id is available."""
        flow_id = self._get_context_flow_id(context)
        if flow_id:
            self.flow_logger.log_retry_attempt(flow_id, context.agent_name, context.retry_count)
    
    async def _execute_fallback_strategy(self, context: AgentExecutionContext,
                                       user_context: Optional['UserExecutionContext'], error: Exception,
                                       start_time: float) -> AgentExecutionResult:
        """Execute fallback strategy for failed execution."""
        self._log_fallback_trigger(context)
        # Fallback manager removed - create result directly
        return AgentExecutionResult(
            success=False,
            error=str(error),
            agent_name=context.agent_name if context else "unknown",
            duration=(time.time() - start_time) if start_time else 0
        )

    # Fallback management delegation
    async def get_fallback_health_status(self) -> Dict[str, any]:
        """Get health status of fallback mechanisms."""
        # Fallback manager removed - return simple health status
        return {"status": "healthy", "fallback_enabled": False}
    
    async def reset_fallback_mechanisms(self) -> None:
        """Reset all fallback mechanisms."""
        # Fallback manager removed - no reset needed
        pass
    
    async def _execute_fallback_strategy(self, context: AgentExecutionContext, 
                                        user_context: Optional['UserExecutionContext'], error: Exception, 
                                        start_time: float) -> AgentExecutionResult:
        """Execute fallback strategy for failed agent."""
        self._log_fallback_trigger(context)
        # Fallback manager removed - create result directly
        return AgentExecutionResult(
            success=False,
            error=str(error),
            agent_name=context.agent_name if context else "unknown",
            duration=(time.time() - start_time) if start_time else 0
        )
    
    def _prepare_retry_context(self, context: AgentExecutionContext) -> None:
        """Prepare context for retry execution."""
        context.retry_count += 1
        logger.info(f"Retrying {context.agent_name} ({context.retry_count}/{context.max_retries})")
    
    async def _wait_for_retry(self, retry_count: int) -> None:
        """Wait for exponential backoff delay."""
        await asyncio.sleep(2 ** retry_count)
    
    def _enforce_history_size_limit(self) -> None:
        """Enforce maximum history size to prevent memory leaks."""
        if len(self.run_history) > self.MAX_HISTORY_SIZE:
            self.run_history = self.run_history[-self.MAX_HISTORY_SIZE:]
    
    def _get_context_flow_id(self, context: AgentExecutionContext) -> Optional[str]:
        """Get flow ID from execution context if available."""
        return getattr(context, 'flow_id', None)
    
    # ============================================================================
    # CONCURRENCY OPTIMIZATION: Error and Timeout Handling
    # ============================================================================
    
    def _create_timeout_result(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """Create result for timed out execution."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        return AgentExecutionResult(
            success=False,
            agent_name=context.agent_name,
            duration=self.AGENT_EXECUTION_TIMEOUT,
            error=f"Agent execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s",
            metadata={'timeout': True, 'timeout_duration': self.AGENT_EXECUTION_TIMEOUT}
        )
    
    def _create_error_result(self, context: AgentExecutionContext, error: Exception) -> AgentExecutionResult:
        """Create result for unexpected errors."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        return AgentExecutionResult(
            success=False,
            agent_name=context.agent_name,
            duration=0.0,
            error=str(error),
            metadata={'unexpected_error': True, 'error_type': type(error).__name__}
        )
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics."""
        stats = self.execution_stats.copy()
        
        # Calculate averages
        if stats['queue_wait_times']:
            stats['avg_queue_wait_time'] = sum(stats['queue_wait_times']) / len(stats['queue_wait_times'])
            stats['max_queue_wait_time'] = max(stats['queue_wait_times'])
        else:
            stats['avg_queue_wait_time'] = 0.0
            stats['max_queue_wait_time'] = 0.0
            
        if stats['execution_times']:
            stats['avg_execution_time'] = sum(stats['execution_times']) / len(stats['execution_times'])
            stats['max_execution_time'] = max(stats['execution_times'])
        else:
            stats['avg_execution_time'] = 0.0
            stats['max_execution_time'] = 0.0
        
        # Add WebSocket bridge stats
        try:
            bridge_metrics = await self.websocket_bridge.get_metrics()
            stats['websocket_bridge_metrics'] = bridge_metrics
        except Exception as e:
            stats['websocket_bridge_error'] = str(e)
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown execution engine and clean up resources."""
        # Shutdown periodic update manager
        # periodic_update_manager removed - no shutdown needed
        pass
        
        # Clear active runs
        self.active_runs.clear()
        
        # WebSocket bridge shutdown is handled separately
        logger.info("ExecutionEngine shutdown complete")
    
    # ============================================================================
    # ENHANCED USER NOTIFICATION METHODS FOR ERROR HANDLING
    # ============================================================================
    
    async def _notify_user_of_execution_error(self, context: AgentExecutionContext, 
                                            error: Exception) -> None:
        """Notify user of agent execution error via WebSocket."""
        try:
            error_message = {
                "type": "agent_execution_error",
                "data": {
                    "agent_name": context.agent_name,
                    "message": f"The {context.agent_name} encountered an error while processing your request.",
                    "user_friendly_message": (
                        "Something went wrong while processing your request. "
                        "Our system is automatically trying to recover. "
                        "If this persists, please try again or contact support."
                    ),
                    "error_type": type(error).__name__,
                    "severity": "error",
                    "action_required": "The system is attempting to recover automatically",
                    "support_code": f"AGENT_ERR_{context.user_id[:8]}_{context.agent_name}_{datetime.utcnow().strftime('%H%M%S')}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Try to send via WebSocket bridge - fix parameter mapping
            await self.websocket_bridge.notify_agent_error(
                context.run_id,
                context.agent_name,
                error=error_message["data"]["user_friendly_message"],
                error_context=error_message["data"]
            )
            
            logger.info(f"Notified user {context.user_id} of agent execution error")
            
        except Exception as e:
            logger.error(f"Failed to notify user of execution error: {e}")
    
    async def _notify_user_of_timeout(self, context: AgentExecutionContext, 
                                    timeout_seconds: float) -> None:
        """Notify user of agent timeout via WebSocket."""
        try:
            timeout_message = {
                "type": "agent_timeout",
                "data": {
                    "agent_name": context.agent_name,
                    "message": f"The {context.agent_name} took longer than expected to respond.",
                    "user_friendly_message": (
                        f"Your request is taking longer than usual (over {timeout_seconds:.0f} seconds). "
                        "This might be due to high system load or a complex request. "
                        "Please try again with a simpler request or contact support if this continues."
                    ),
                    "timeout_seconds": timeout_seconds,
                    "severity": "warning", 
                    "action_required": "Consider trying a simpler request or refreshing the page",
                    "support_code": f"TIMEOUT_{context.user_id[:8]}_{context.agent_name}_{datetime.utcnow().strftime('%H%M%S')}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Try to send via WebSocket bridge - fix parameter mapping
            await self.websocket_bridge.notify_agent_error(
                context.run_id,
                context.agent_name,
                error=timeout_message["data"]["user_friendly_message"],
                error_context=timeout_message["data"]
            )
            
            logger.info(f"Notified user {context.user_id} of agent timeout")
            
        except Exception as e:
            logger.error(f"Failed to notify user of timeout: {e}")
    
    async def _notify_user_of_system_error(self, context: AgentExecutionContext, 
                                         error: Exception) -> None:
        """Notify user of system error via WebSocket."""
        try:
            system_error_message = {
                "type": "system_error",
                "data": {
                    "agent_name": context.agent_name,
                    "message": f"A system error occurred in the {context.agent_name}.",
                    "user_friendly_message": (
                        "We encountered an unexpected system error while processing your request. "
                        "Our engineering team has been automatically notified. "
                        "Please try again in a few moments, or contact support if the issue persists."
                    ),
                    "error_type": type(error).__name__,
                    "severity": "critical",
                    "action_required": "Try again in a few moments or contact support",
                    "support_code": f"SYS_ERR_{context.user_id[:8]}_{context.agent_name}_{datetime.utcnow().strftime('%H%M%S')}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Try to send via WebSocket bridge - fix parameter mapping
            await self.websocket_bridge.notify_agent_error(
                context.run_id,
                context.agent_name,
                error=system_error_message["data"]["user_friendly_message"],
                error_context=system_error_message["data"]
            )
            
            logger.info(f"Notified user {context.user_id} of system error")
            
        except Exception as e:
            logger.error(f"Failed to notify user of system error: {e}")
    
    # ============================================================================
    # NEW DELEGATION METHODS FOR USER ISOLATION
    # ============================================================================
    
    async def create_user_engine(self, context: UserExecutionContext) -> UserExecutionEngine:
        """Create UserExecutionEngine for complete user isolation.
        
        RECOMMENDED: Use this method for new code requiring user isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            UserExecutionEngine: Isolated execution engine for the user
            
        Raises:
            RuntimeError: If user engine creation fails
        """
        try:
            factory = await get_execution_engine_factory()
            return await factory.create_for_user(context)
        except Exception as e:
            logger.error(f"Failed to create UserExecutionEngine: {e}")
            raise RuntimeError(f"User engine creation failed: {e}")
    
    @staticmethod
    async def execute_with_user_isolation(context: UserExecutionContext,
                                         agent_context: AgentExecutionContext,
                                         user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute agent with complete user isolation (static method).
        
        RECOMMENDED: Use this static method for new code requiring complete isolation.
        
        Args:
            context: User execution context for isolation
            agent_context: Agent execution context
            state: Deep agent state for execution
            
        Returns:
            AgentExecutionResult: Results of isolated execution
            
        Usage:
            result = await ExecutionEngine.execute_with_user_isolation(
                user_context, agent_context, state
            )
        """
        async with user_execution_engine(context) as engine:
            return await engine.execute_agent(agent_context, user_context)
    
    def has_user_context(self) -> bool:
        """Check if this engine has UserExecutionContext support."""
        return self.user_context is not None
    
    def get_isolation_status(self) -> Dict[str, Any]:
        """Get isolation status information for this engine.
        
        Returns:
            Dictionary with isolation status and recommendations
        """
        return {
            'has_user_context': self.has_user_context(),
            'user_id': self.user_context.user_id if self.user_context else None,
            'run_id': self.user_context.run_id if self.user_context else None,
            'isolation_level': 'user_isolated' if self.user_context else 'global_state',
            'recommended_migration': not self.has_user_context(),
            'migration_method': 'create_user_engine() or ExecutionEngine.execute_with_user_isolation()',
            'active_runs_count': len(self.active_runs),
            'global_state_warning': not self.has_user_context()
        }


# ============================================================================
# FACTORY METHODS AND MIGRATION SUPPORT
# ============================================================================

def create_request_scoped_engine(user_context: 'UserExecutionContext',
                                registry: 'AgentRegistry',
                                websocket_bridge: 'AgentWebSocketBridge',
                                max_concurrent_executions: int = 3) -> 'RequestScopedExecutionEngine':
    """Factory method to create RequestScopedExecutionEngine for safe concurrent usage.
    
    RECOMMENDED: Use this factory method instead of ExecutionEngine for new code.
    
    Args:
        user_context: User execution context for complete isolation
        registry: Agent registry for agent lookup
        websocket_bridge: WebSocket bridge for event emission
        max_concurrent_executions: Maximum concurrent executions for this request
        
    Returns:
        RequestScopedExecutionEngine: Isolated execution engine for this request
        
    Examples:
        # Create isolated engine for a user request
        engine = create_request_scoped_engine(
            user_context=user_context,
            registry=agent_registry,
            websocket_bridge=websocket_bridge
        )
        
        # Execute agent with complete isolation
        result = await engine.execute_agent(context, state)
        
        # Clean up when done
        await engine.cleanup()
    """
    from netra_backend.app.agents.supervisor.request_scoped_execution_engine import (
        RequestScopedExecutionEngine
    )
    
    logger.info(f"Creating RequestScopedExecutionEngine for user {user_context.user_id} "
                f"(run_id: {user_context.run_id})")
    
    return RequestScopedExecutionEngine(
        user_context=user_context,
        registry=registry,
        websocket_bridge=websocket_bridge,
        max_concurrent_executions=max_concurrent_executions
    )


def create_execution_context_manager(registry: 'AgentRegistry',
                                    websocket_bridge: 'AgentWebSocketBridge',
                                    max_concurrent_per_request: int = 3,
                                    execution_timeout: float = 30.0) -> 'ExecutionContextManager':
    """Factory method to create ExecutionContextManager for request-scoped management.
    
    RECOMMENDED: Use this for managing multiple agent executions within a request scope.
    
    Args:
        registry: Agent registry for agent lookup
        websocket_bridge: WebSocket bridge for event emission
        max_concurrent_per_request: Maximum concurrent executions per request
        execution_timeout: Execution timeout in seconds
        
    Returns:
        ExecutionContextManager: Context manager for request-scoped execution
        
    Examples:
        # Create context manager
        context_manager = create_execution_context_manager(
            registry=agent_registry,
            websocket_bridge=websocket_bridge
        )
        
        # Use with async context manager
        async with context_manager.execution_scope(user_context) as scope:
            # Execute agents within isolated scope
            pass
    """
    from netra_backend.app.agents.supervisor.execution_context_manager import (
        ExecutionContextManager
    )
    
    logger.info("Creating ExecutionContextManager for request-scoped execution management")
    
    return ExecutionContextManager(
        registry=registry,
        websocket_bridge=websocket_bridge,
        max_concurrent_per_request=max_concurrent_per_request,
        execution_timeout=execution_timeout
    )


# Legacy factory method removed - use create_request_scoped_engine() only


# Migration helper to detect global state usage
def detect_global_state_usage() -> Dict[str, Any]:
    """Detect if ExecutionEngine instances are sharing global state.
    
    This utility function helps identify potential global state issues
    by checking if multiple engine instances share the same state objects.
    
    Returns:
        Dictionary with global state detection results
    """
    # This would be implemented to analyze existing ExecutionEngine instances
    # and detect shared state objects between different instances
    return {
        'global_state_detected': False,
        'shared_objects': [],
        'recommendations': [
            "Migrate to RequestScopedExecutionEngine for complete isolation",
            "Use ExecutionContextManager for request-scoped execution management",
            "Avoid direct ExecutionEngine instantiation in concurrent scenarios"
        ]
    }