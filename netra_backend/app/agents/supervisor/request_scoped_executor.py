"""RequestScopedAgentExecutor - Per-Request Agent Execution with User Isolation

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: User Privacy & System Stability
- Value Impact: Eliminates user data leakage and concurrency issues in agent execution
- Strategic Impact: Enables scalable multi-user agent execution without global state conflicts

This module provides a request-scoped agent executor that replaces the singleton 
ExecutionEngine pattern to ensure complete user isolation and prevent global state issues.

Key Architecture Principles:
- Per-request isolation (NOT singleton)
- Bound to specific UserExecutionContext  
- No shared global state or collections
- Uses WebSocketEventEmitter for user-scoped notifications
- Comprehensive error handling and cleanup
- Compatible with existing agent interfaces

The RequestScopedAgentExecutor follows SSOT principles and provides proper request-scoped
execution while maintaining compatibility with existing agent execution patterns.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

# DeepAgentState import removed - using UserExecutionContext pattern only
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.agent_execution_tracker import (
    get_execution_tracker,
    ExecutionState
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter

logger = central_logger.get_logger(__name__)


class AgentExecutorError(Exception):
    """Base exception for RequestScopedAgentExecutor errors."""
    pass


class RequestScopedAgentExecutor:
    """
    Per-request agent executor with complete user isolation.
    
    This class provides agent execution scoped to a specific user execution context,
    ensuring complete isolation between users and eliminating the singleton pattern
    issues found in the global ExecutionEngine.
    
    Key Features:
    - Bound to UserExecutionContext for complete isolation
    - Uses WebSocketEventEmitter for user-scoped notifications
    - No global state or shared collections between users
    - Per-request execution tracking and metrics
    - Comprehensive error handling and cleanup
    - Compatible interface with existing ExecutionEngine usage
    - Async context manager support for proper lifecycle
    
    Business Value:
    - Prevents cross-user execution state leakage
    - Enables reliable per-user agent execution
    - Maintains chat functionality while ensuring user privacy
    - Eliminates race conditions from singleton pattern
    - Supports horizontal scaling without state conflicts
    """
    
    # Configuration constants
    AGENT_EXECUTION_TIMEOUT = 30.0  # 30 seconds max per agent
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Base delay in seconds for exponential backoff
    
    def __init__(
        self,
        user_context: UserExecutionContext,
        event_emitter: WebSocketEventEmitter,
        agent_registry: 'AgentRegistry'
    ):
        """
        Initialize per-request agent executor.
        
        Args:
            user_context: Immutable user execution context for this request
            event_emitter: WebSocket event emitter bound to the same user context
            agent_registry: Agent registry for retrieving agent instances
            
        Raises:
            ValueError: If parameters are invalid or contexts don't match
        """
        # Validate inputs with comprehensive error handling
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError(f"user_context must be UserExecutionContext, got {type(user_context)}")
        
        if not isinstance(event_emitter, WebSocketEventEmitter):
            raise ValueError(f"event_emitter must be WebSocketEventEmitter, got {type(event_emitter)}")
        
        if not agent_registry:
            raise ValueError("agent_registry cannot be None")
        
        # Verify contexts match for security
        emitter_context = event_emitter.get_context()
        if (user_context.user_id != emitter_context.user_id or 
            user_context.thread_id != emitter_context.thread_id or
            user_context.run_id != emitter_context.run_id):
            raise ValueError(
                f"Context mismatch: user_context {user_context.get_correlation_id()} "
                f"!= emitter_context {emitter_context.get_correlation_id()}"
            )
        
        # Store immutable references 
        self._user_context = user_context
        self._event_emitter = event_emitter
        self._agent_registry = agent_registry
        self._created_at = datetime.now(timezone.utc)
        self._disposed = False
        
        # Per-request execution tracking (no global state)
        self._execution_tracker = get_execution_tracker()
        self._request_executions: Dict[str, str] = {}  # execution_context_id -> tracker_execution_id
        
        # Per-request metrics (isolated from other users)
        self._metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'timeout_executions': 0,
            'execution_times': [],
            'created_at': self._created_at,
            'context_id': user_context.get_correlation_id()
        }
        
        # Create agent execution core for this request
        self._agent_core = AgentExecutionCore(
            registry=agent_registry,
            websocket_bridge=event_emitter  # EventEmitter implements the same interface
        )
        
        logger.debug(f" TARGET:  EXECUTOR CREATED: {self._get_log_prefix()} - per-request isolation")
        
        # Verify user context integrity
        try:
            user_context.verify_isolation()
            logger.debug(f" PASS:  ISOLATION VERIFIED: {self._get_log_prefix()}")
        except Exception as e:
            logger.error(f" ALERT:  ISOLATION VIOLATION: {self._get_log_prefix()} - {e}")
            raise AgentExecutorError(f"User context failed isolation verification: {e}")
    
    def _get_log_prefix(self) -> str:
        """Get consistent logging prefix for this executor instance."""
        return f"[{self._user_context.get_correlation_id()}]"
    
    def _ensure_not_disposed(self) -> None:
        """Ensure executor hasn't been disposed."""
        if self._disposed:
            raise RuntimeError(f"RequestScopedAgentExecutor {self._get_log_prefix()} has been disposed")
    
    def _create_execution_context(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> AgentExecutionContext:
        """
        Create AgentExecutionContext from UserExecutionContext.
        
        Args:
            agent_name: Name of the agent to execute
            metadata: Optional metadata for the execution
            
        Returns:
            AgentExecutionContext for the agent execution
        """
        return AgentExecutionContext(
            run_id=self._user_context.run_id,
            thread_id=self._user_context.thread_id,
            user_id=self._user_context.user_id,
            agent_name=agent_name,
            retry_count=0,
            max_retries=self.MAX_RETRIES,
            timeout=int(self.AGENT_EXECUTION_TIMEOUT),
            metadata=metadata or {},
            started_at=datetime.now(timezone.utc)
        )
    
    async def execute_agent(
        self,
        agent_name: str,
        user_context: Optional[UserExecutionContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> AgentExecutionResult:
        """
        Execute a single agent with complete user isolation.
        
        This is the primary method for executing agents within the user's context.
        All execution is isolated to this user and tracked separately from other users.
        
        Args:
            agent_name: Name of the agent to execute
            user_context: Optional override user context (defaults to executor's context)
            metadata: Optional metadata for the execution
            timeout: Optional timeout override
            
        Returns:
            AgentExecutionResult with execution results
            
        Raises:
            AgentExecutorError: If execution fails or validation errors occur
        """
        self._ensure_not_disposed()
        
        # Use user_context override or executor's context
        effective_user_context = user_context or self._user_context
        
        # Create execution context from user context
        execution_context = self._create_execution_context(agent_name, metadata)
        
        # Validate execution context
        self._validate_execution_context(execution_context)
        
        execution_start = time.time()
        execution_timeout = timeout or self.AGENT_EXECUTION_TIMEOUT
        
        try:
            # Update metrics
            self._metrics['total_executions'] += 1
            
            # Create execution tracking record for this request
            execution_id = self._execution_tracker.create_execution(
                agent_name=agent_name,
                thread_id=execution_context.thread_id,
                user_id=execution_context.user_id,
                timeout_seconds=int(execution_timeout),
                metadata={'run_id': execution_context.run_id, 'context': metadata or {}}
            )
            
            # Store execution mapping for cleanup
            context_key = f"{agent_name}_{execution_context.run_id}_{time.time()}"
            self._request_executions[context_key] = execution_id
            
            # Mark execution as starting
            self._execution_tracker.start_execution(execution_id)
            
            # Send agent started notification via user-scoped emitter
            await self._event_emitter.notify_agent_started(
                execution_context.run_id,
                agent_name,
                {"status": "started", "context": metadata or {}}
            )
            
            # Send initial thinking update
            await self._event_emitter.notify_agent_thinking(
                execution_context.run_id,
                agent_name,
                f"Starting execution of {agent_name} agent...",
                step_number=1
            )
            
            # Create heartbeat task for death detection
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(execution_id))
            
            try:
                # Execute with timeout and monitoring
                result = await asyncio.wait_for(
                    self._execute_with_monitoring(execution_context, effective_user_context, execution_id),
                    timeout=execution_timeout
                )
                
                # Calculate execution time
                execution_time = time.time() - execution_start
                result.duration = execution_time
                self._metrics['execution_times'].append(execution_time)
                
                # Update success metrics
                if result.success:
                    self._metrics['successful_executions'] += 1
                    # Mark execution as completed
                    self._execution_tracker.update_execution_state(
                        execution_id, ExecutionState.COMPLETED, result=result.state
                    )
                    
                    # Send completion notification
                    await self._send_success_completion(execution_context, result, effective_user_context)
                else:
                    self._metrics['failed_executions'] += 1
                    # Mark execution as failed
                    self._execution_tracker.update_execution_state(
                        execution_id, ExecutionState.FAILED, error=result.error
                    )
                    
                    # Send failure completion notification
                    await self._send_failure_completion(execution_context, result, effective_user_context)
                
                return result
                
            except asyncio.TimeoutError:
                self._metrics['timeout_executions'] += 1
                self._metrics['failed_executions'] += 1
                
                # Mark execution as timed out
                self._execution_tracker.update_execution_state(
                    execution_id, ExecutionState.TIMEOUT,
                    error=f"Execution timed out after {execution_timeout}s"
                )
                
                # Send timeout notification
                await self._event_emitter.notify_agent_error(
                    execution_context.run_id,
                    agent_name,
                    f"Agent execution timed out after {execution_timeout}s"
                )
                
                # Create timeout result
                timeout_result = self._create_timeout_result(execution_context, execution_timeout)
                await self._send_failure_completion(execution_context, timeout_result, effective_user_context)
                
                return timeout_result
                
            finally:
                # Cancel heartbeat task
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
                # Clean up execution tracking
                if context_key in self._request_executions:
                    del self._request_executions[context_key]
                    
        except Exception as e:
            self._metrics['failed_executions'] += 1
            logger.error(f" ALERT:  EXECUTION ERROR: {self._get_log_prefix()} {agent_name} failed: {e}")
            
            # Create error result
            error_result = self._create_error_result(execution_context, e)
            await self._send_failure_completion(execution_context, error_result, effective_user_context)
            
            return error_result
    
    async def _execute_with_monitoring(
        self,
        context: AgentExecutionContext,
        user_context: UserExecutionContext,
        execution_id: str
    ) -> AgentExecutionResult:
        """Execute agent with monitoring and error handling."""
        try:
            # Send progress update  
            user_request = user_context.get_metadata('user_request', 'Task')
            await self._event_emitter.notify_agent_thinking(
                context.run_id,
                context.agent_name,
                f"Processing request: {str(user_request)[:100]}...",
                step_number=2
            )
            
            # Heartbeat before execution
            self._execution_tracker.heartbeat(execution_id)
            
            # Execute via agent core with user context
            result = await self._agent_core.execute_agent(context, user_context)
            
            # Final heartbeat after execution
            self._execution_tracker.heartbeat(execution_id)
            
            return result
            
        except Exception as e:
            # Check if this is a death scenario
            execution_record = self._execution_tracker.get_execution(execution_id)
            if execution_record and execution_record.is_dead(self._execution_tracker.heartbeat_timeout):
                # Agent died - send death notification
                await self._event_emitter.notify_agent_error(
                    context.run_id,
                    context.agent_name,
                    f"Agent died during execution: {str(e)}"
                )
            raise
    
    async def _heartbeat_loop(self, execution_id: str) -> None:
        """Send periodic heartbeats for death detection."""
        try:
            while True:
                await asyncio.sleep(2)  # Heartbeat every 2 seconds
                if not self._execution_tracker.heartbeat(execution_id):
                    break  # Execution is terminal, stop heartbeat
        except asyncio.CancelledError:
            pass
    
    def _validate_execution_context(self, context: AgentExecutionContext) -> None:
        """
        Validate execution context to prevent invalid values from propagating.
        
        Args:
            context: The agent execution context to validate
            
        Raises:
            AgentExecutorError: If context contains invalid values
        """
        # Validate user_id is not None or empty
        if not context.user_id or not context.user_id.strip():
            raise AgentExecutorError(
                f"Invalid execution context: user_id must be a non-empty string, "
                f"got: {context.user_id!r}"
            )
        
        # Validate run_id is not forbidden placeholder values
        forbidden_values = {'registry', 'placeholder', 'default', 'temp'}
        if context.run_id.lower() in forbidden_values:
            raise AgentExecutorError(
                f"Invalid execution context: run_id cannot be placeholder value, "
                f"got: {context.run_id!r}"
            )
        
        # Validate run_id is not None or empty
        if not context.run_id or not context.run_id.strip():
            raise AgentExecutorError(
                f"Invalid execution context: run_id must be a non-empty string, "
                f"got: {context.run_id!r}"
            )
        
        # Validate agent_name
        if not context.agent_name or not context.agent_name.strip():
            raise AgentExecutorError(
                f"Invalid execution context: agent_name must be a non-empty string, "
                f"got: {context.agent_name!r}"
            )
        
        # Validate context matches our user context
        if (context.user_id != self._user_context.user_id or
            context.thread_id != self._user_context.thread_id or
            context.run_id != self._user_context.run_id):
            raise AgentExecutorError(
                f"Context mismatch: execution context {context.user_id}:{context.thread_id}:{context.run_id} "
                f"does not match user context {self._user_context.get_correlation_id()}"
            )
    
    async def _send_success_completion(
        self,
        context: AgentExecutionContext,
        result: AgentExecutionResult,
        user_context: UserExecutionContext
    ) -> None:
        """Send completion notification for successful execution."""
        try:
            # Build comprehensive success report using user context
            user_request = user_context.get_metadata('user_request', 'N/A')
            final_report = user_context.get_state('final_report', 'Completed')
            step_count = user_context.get_metadata('step_count', 0)
            
            report = {
                "agent_name": context.agent_name,
                "success": True,
                "duration_ms": result.duration * 1000 if result.duration else 0,
                "user_request": str(user_request),
                "final_report": str(final_report),
                "step_count": int(step_count) if isinstance(step_count, (int, float)) else 0,
                "status": "completed"
            }
            
            # Send completion notification
            await self._event_emitter.notify_agent_completed(
                context.run_id,
                context.agent_name,
                report,
                result.duration * 1000 if result.duration else 0
            )
            
            logger.info(f" PASS:  AGENT SUCCESS: {self._get_log_prefix()} {context.agent_name} completed")
            
        except Exception as e:
            logger.warning(f"Failed to send success completion notification: {e}")
    
    async def _send_failure_completion(
        self,
        context: AgentExecutionContext,
        result: AgentExecutionResult,
        user_context: UserExecutionContext
    ) -> None:
        """Send completion notification for failed execution."""
        try:
            # Build failure completion report
            report = {
                "agent_name": context.agent_name,
                "success": False,
                "duration_ms": result.duration * 1000 if result.duration else 0,
                "error": getattr(result, 'error', 'Execution failed'),
                "status": "failed"
            }
            
            # Send completion notification for failed execution
            await self._event_emitter.notify_agent_completed(
                context.run_id,
                context.agent_name,
                report,
                result.duration * 1000 if result.duration else 0
            )
            
            logger.warning(f" FAIL:  AGENT FAILURE: {self._get_log_prefix()} {context.agent_name} failed")
            
        except Exception as e:
            logger.warning(f"Failed to send failure completion notification: {e}")
    
    def _create_timeout_result(self, context: AgentExecutionContext, timeout: float) -> AgentExecutionResult:
        """Create result for timed out execution."""
        return AgentExecutionResult(
            success=False,
            state=None,
            error=f"Agent execution timed out after {timeout}s",
            duration=timeout,
            metadata={'timeout': True, 'timeout_duration': timeout}
        )
    
    def _create_error_result(self, context: AgentExecutionContext, error: Exception) -> AgentExecutionResult:
        """Create result for unexpected errors."""
        return AgentExecutionResult(
            success=False,
            state=None,
            error=str(error),
            duration=0.0,
            metadata={'unexpected_error': True, 'error_type': type(error).__name__}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get executor metrics for monitoring.
        
        Returns:
            Dictionary with execution metrics for this request only
        """
        self._ensure_not_disposed()
        
        now = datetime.now(timezone.utc)
        uptime = (now - self._created_at).total_seconds()
        
        metrics = self._metrics.copy()
        
        # Calculate averages
        if metrics['execution_times']:
            metrics['avg_execution_time'] = sum(metrics['execution_times']) / len(metrics['execution_times'])
            metrics['max_execution_time'] = max(metrics['execution_times'])
        else:
            metrics['avg_execution_time'] = 0.0
            metrics['max_execution_time'] = 0.0
        
        # Add runtime information
        metrics.update({
            'uptime_seconds': uptime,
            'success_rate': (
                metrics['successful_executions'] / 
                max(1, metrics['total_executions'])
            ),
            'active_executions': len(self._request_executions),
            'user_context': self._user_context.to_dict(),
            'disposed': self._disposed
        })
        
        return metrics
    
    def get_user_context(self) -> UserExecutionContext:
        """Get the bound user execution context."""
        return self._user_context
    
    def get_event_emitter(self) -> WebSocketEventEmitter:
        """Get the bound WebSocket event emitter."""
        return self._event_emitter
    
    async def dispose(self) -> None:
        """
        Dispose of the executor and clean up resources.
        
        This method should be called when the executor is no longer needed
        to ensure proper cleanup and prevent memory leaks.
        """
        if self._disposed:
            return
        
        logger.debug(f"[U+1F5D1][U+FE0F] EXECUTOR DISPOSING: {self._get_log_prefix()}")
        
        # Cancel any active executions
        for context_key, execution_id in self._request_executions.items():
            try:
                self._execution_tracker.update_execution_state(
                    execution_id, ExecutionState.FAILED, 
                    error="Executor disposed before completion"
                )
            except Exception as e:
                logger.warning(f"Error cleaning up execution {execution_id}: {e}")
        
        # Clear request-specific state
        self._request_executions.clear()
        
        # Mark as disposed to prevent further usage
        self._disposed = True
        
        # Clear references
        self._agent_registry = None
        self._agent_core = None
        
        logger.debug(f" PASS:  EXECUTOR DISPOSED: {self._get_log_prefix()}")
    
    async def __aenter__(self) -> 'RequestScopedAgentExecutor':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.dispose()


class RequestScopedExecutorFactory:
    """
    Factory for creating RequestScopedAgentExecutor instances with proper dependencies.
    
    This factory handles the creation of RequestScopedAgentExecutor instances with
    proper dependency injection and validation, ensuring consistent creation patterns
    across the application.
    
    Business Value:
    - Ensures consistent RequestScopedAgentExecutor creation
    - Handles dependency validation and injection
    - Provides clear factory pattern for better testing
    - Enables easier mocking and test isolation
    """
    
    @staticmethod
    async def create_executor(
        user_context: UserExecutionContext,
        event_emitter: WebSocketEventEmitter,
        agent_registry: Optional['AgentRegistry'] = None
    ) -> RequestScopedAgentExecutor:
        """
        Create a RequestScopedAgentExecutor for the given user context.
        
        Args:
            user_context: User execution context to bind executor to
            event_emitter: WebSocket event emitter bound to same context
            agent_registry: Optional agent registry (uses default if None)
            
        Returns:
            Configured RequestScopedAgentExecutor instance
            
        Raises:
            ValueError: If dependencies are invalid or unavailable
        """
        # Get agent registry if not provided
        if agent_registry is None:
            try:
                # Import here to avoid circular imports
                from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry
                agent_registry = get_agent_registry()
            except Exception as e:
                logger.error(f" ALERT:  FACTORY ERROR: Failed to get agent registry: {e}")
                raise ValueError(f"Failed to get agent registry: {e}")
        
        # Create executor
        try:
            executor = RequestScopedAgentExecutor(
                user_context, event_emitter, agent_registry
            )
            logger.info(f"[U+1F3ED] EXECUTOR CREATED: {executor._get_log_prefix()} via factory")
            return executor
        except Exception as e:
            logger.error(f" ALERT:  FACTORY ERROR: Failed to create executor: {e}")
            raise ValueError(f"Failed to create RequestScopedAgentExecutor: {e}")
    
    @staticmethod
    async def create_scoped_executor(
        user_context: UserExecutionContext,
        event_emitter: WebSocketEventEmitter,
        agent_registry: Optional['AgentRegistry'] = None
    ) -> 'RequestScopedAgentExecutor':
        """
        Create a scoped RequestScopedAgentExecutor with automatic cleanup.
        
        This is the recommended way to create executors as it ensures proper
        resource cleanup even if exceptions occur.
        
        Args:
            user_context: User execution context to bind executor to
            event_emitter: WebSocket event emitter bound to same context
            agent_registry: Optional agent registry
            
        Returns:
            RequestScopedAgentExecutor: Configured executor with automatic cleanup
            
        Example:
            async with RequestScopedExecutorFactory.create_scoped_executor(
                context, emitter
            ) as executor:
                result = await executor.execute_agent("MyAgent", state)
                # Automatic cleanup happens here
        """
        executor = await RequestScopedExecutorFactory.create_executor(
            user_context, event_emitter, agent_registry
        )
        logger.debug(f"[U+1F4E6] SCOPED EXECUTOR: {executor._get_log_prefix()} created with auto-cleanup")
        return executor


# ===================== CONVENIENCE FUNCTIONS =====================

async def create_request_scoped_executor(
    user_context: UserExecutionContext,
    event_emitter: WebSocketEventEmitter,
    agent_registry: Optional['AgentRegistry'] = None
) -> RequestScopedAgentExecutor:
    """
    Convenience function to create a RequestScopedAgentExecutor.
    
    Args:
        user_context: User execution context
        event_emitter: WebSocket event emitter
        agent_registry: Optional agent registry
        
    Returns:
        RequestScopedAgentExecutor instance
    """
    return await RequestScopedExecutorFactory.create_executor(
        user_context, event_emitter, agent_registry
    )


async def create_full_request_execution_stack(
    user_context: UserExecutionContext,
    websocket_manager: Optional[Any] = None,
    agent_registry: Optional['AgentRegistry'] = None
) -> RequestScopedAgentExecutor:
    """
    Convenience function to create a complete request execution stack.
    
    This creates both the WebSocketEventEmitter and RequestScopedAgentExecutor
    bound to the same user context, providing a complete isolated execution environment.
    
    Args:
        user_context: User execution context
        websocket_manager: Optional WebSocket manager for event emitter
        agent_registry: Optional agent registry
        
    Returns:
        RequestScopedAgentExecutor with embedded event emitter
        
    Example:
        executor = await create_full_request_execution_stack(user_context)
        result = await executor.execute_agent("MyAgent", state)
    """
    # Create event emitter
    from netra_backend.app.websocket_core.unified_emitter import WebSocketEmitterFactory
    event_emitter = WebSocketEmitterFactory.create_emitter(
        manager=websocket_manager,
        user_id=user_context.user_id,
        context=user_context
    )
    
    # Create executor with event emitter
    return await RequestScopedExecutorFactory.create_executor(
        user_context, event_emitter, agent_registry
    )