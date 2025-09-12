"""
 ALERT:  CRITICAL SSOT MIGRATION - FILE DEPRECATED  ALERT: 

This file has been DEPRECATED as part of ExecutionEngine SSOT consolidation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file will be REMOVED in the next release

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

"""
 ALERT:  CRITICAL SSOT MIGRATION - FILE DEPRECATED  ALERT: 

This file has been DEPRECATED as part of ExecutionEngine SSOT consolidation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file will be REMOVED in the next release

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

"""RequestScopedExecutionEngine for per-request isolated agent execution.

This module provides the RequestScopedExecutionEngine class that handles agent execution
with complete per-request isolation, eliminating global state issues.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Scalability
- Value Impact: Enables safe concurrent user handling with zero context leakage
- Strategic Impact: Foundation for multi-tenant production deployment
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from datetime import datetime, timezone

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.agents.supervisor.agent_execution_context_manager import (
    AgentExecutionContextManager as ExecutionContextManager,
    # RequestExecutionScope,  # This class doesn't exist, commenting out for now
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
# Legacy import removed - use SSOT from resilience
# from netra_backend.app.agents.supervisor.fallback_manager import FallbackManager
from netra_backend.app.core.resilience.fallback import FallbackManager
from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
from netra_backend.app.agents.supervisor.observability_flow import (
    get_supervisor_flow_logger,
)
from netra_backend.app.core.agent_execution_tracker import (
    get_execution_tracker,
    ExecutionState
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RequestScopedExecutionEngine:
    """Per-request execution engine with complete isolation.
    
    This engine is created per request and contains NO GLOBAL STATE.
    Each instance handles execution for a single user request with:
    - Request-scoped active_runs tracking
    - Local execution statistics
    - Per-request semaphore control
    - Isolated WebSocket notifications
    - Automatic resource cleanup
    
    Key Design Principles:
    - NO shared state between instances
    - Each request gets its own engine instance
    - All state is request-scoped and cleaned up
    - UserExecutionContext drives all isolation
    - Fail-fast on invalid contexts
    """
    
    # Constants (these are safe as they're immutable)
    MAX_HISTORY_SIZE = 100
    AGENT_EXECUTION_TIMEOUT = 30.0
    
    def __init__(self, 
                 user_context: UserExecutionContext,
                 registry: 'AgentRegistry',
                 websocket_bridge: 'AgentWebSocketBridge',
                 max_concurrent_executions: int = 3):
        """Initialize request-scoped execution engine.
        
        Args:
            user_context: User execution context for complete isolation
            registry: Agent registry for agent lookup
            websocket_bridge: WebSocket bridge for event emission
            max_concurrent_executions: Maximum concurrent executions for this request
            
        Raises:
            TypeError: If user_context is not a UserExecutionContext
            ValueError: If any required parameters are invalid
        """
        # DEPRECATION WARNING: This execution engine is being phased out in favor of UserExecutionEngine
        import warnings
        warnings.warn(
            "This execution engine is deprecated. Use UserExecutionEngine via ExecutionEngineFactory.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Validate user context immediately
        self.user_context = validate_user_context(user_context)
        
        if not registry:
            logger.error(
                f" FAIL:  VALIDATION FAILURE: AgentRegistry cannot be None for RequestScopedExecutionEngine. "
                f"User: {user_context.user_id[:8]}..., Engine initialization failed."
            )
            raise ValueError("AgentRegistry cannot be None")
        if not websocket_bridge:
            logger.error(
                f" FAIL:  VALIDATION FAILURE: AgentWebSocketBridge cannot be None for RequestScopedExecutionEngine. "
                f"User: {user_context.user_id[:8]}..., Engine initialization failed."
            )
            raise ValueError("AgentWebSocketBridge cannot be None")
        
        self.registry = registry
        self.websocket_bridge = websocket_bridge
        self.max_concurrent_executions = max_concurrent_executions
        
        # REQUEST-SCOPED STATE ONLY (no global state)
        self.active_runs: Dict[str, AgentExecutionContext] = {}
        self.run_history: List[AgentExecutionResult] = []
        self.execution_semaphore = asyncio.Semaphore(max_concurrent_executions)
        self.execution_stats = {
            'total_executions': 0,
            'concurrent_executions': 0,
            'queue_wait_times': [],
            'execution_times': [],
            'failed_executions': 0,
            'dead_executions': 0,
            'timeout_executions': 0
        }
        
        # Initialize components with request context
        self._init_components()
        
        # Engine metadata
        self.engine_id = f"{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
        self.created_at = datetime.now(timezone.utc)
        self._is_active = True
        
        logger.info(f" PASS:  Created RequestScopedExecutionEngine {self.engine_id} for user {user_context.user_id} "
                   f"(run_id: {user_context.run_id})")
    
    def _init_components(self) -> None:
        """Initialize execution components with request context."""
        # All components get request-scoped WebSocket bridge
        self.periodic_update_manager = PeriodicUpdateManager(self.websocket_bridge)
        self.agent_core = AgentExecutionCore(self.registry, self.websocket_bridge)
        self.fallback_manager = FallbackManager(self.websocket_bridge)
        self.flow_logger = get_supervisor_flow_logger()
        self.execution_tracker = get_execution_tracker()
        
        logger.debug(f"Initialized components for RequestScopedExecutionEngine {self.engine_id}")
    
    async def execute_agent(self, 
                           context: AgentExecutionContext,
                           state: UserExecutionContext) -> AgentExecutionResult:
        """Execute a single agent with complete request isolation.
        
        This method provides the same interface as the original ExecutionEngine
        but with complete per-request isolation.
        
        Args:
            context: Agent execution context
            state: Deep agent state for execution
            
        Returns:
            AgentExecutionResult: Results of agent execution
            
        Raises:
            ValueError: If context is invalid or engine is inactive
            RuntimeError: If execution fails
        """
        if not self._is_active:
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Attempted to execute agent on inactive ExecutionEngine. "
                f"Engine ID: {self.engine_id}, User: {self.user_context.user_id[:8]}..., "
                f"Agent: {context.agent_name}, This indicates improper engine lifecycle management."
            )
            raise ValueError("ExecutionEngine is no longer active")
        
        # Validate execution context
        self._validate_execution_context(context)
        
        # Ensure context matches our user context
        if context.user_id != self.user_context.user_id:
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Context user_id mismatch in agent execution. "
                f"Expected: {self.user_context.user_id}, Got: {context.user_id}, "
                f"Agent: {context.agent_name}, Engine: {self.engine_id}, "
                f"This is a critical security violation - user context isolation compromised."
            )
            raise ValueError(
                f"Context user_id mismatch: expected {self.user_context.user_id}, "
                f"got {context.user_id}"
            )
        
        queue_start_time = time.time()
        
        # Create execution tracking record
        execution_id = self.execution_tracker.create_execution(
            agent_name=context.agent_name,
            thread_id=context.thread_id,
            user_id=context.user_id,
            timeout_seconds=int(self.AGENT_EXECUTION_TIMEOUT),
            metadata={'run_id': context.run_id, 'context': context.metadata, 'engine_id': self.engine_id}
        )
        
        # Store execution ID in context
        context.execution_id = execution_id
        
        # Add to active runs (request-scoped)
        self.active_runs[execution_id] = context
        
        # Use request-scoped semaphore for concurrency control
        async with self.execution_semaphore:
            queue_wait_time = time.time() - queue_start_time
            self.execution_stats['queue_wait_times'].append(queue_wait_time)
            self.execution_stats['total_executions'] += 1
            self.execution_stats['concurrent_executions'] += 1
            
            # Mark execution as starting
            self.execution_tracker.start_execution(execution_id)
            
            # Send queue wait notification if significant delay
            if queue_wait_time > 1.0:
                await self._send_agent_thinking(
                    context,
                    f"Request queued due to load - starting now (waited {queue_wait_time:.1f}s)",
                    step_number=0
                )
            
            try:
                # Use periodic update manager for long-running operations
                async with self.periodic_update_manager.track_operation(
                    context,
                    f"{context.agent_name}_execution",
                    "agent_execution",
                    expected_duration_ms=int(self.AGENT_EXECUTION_TIMEOUT * 1000),
                    operation_description=f"Executing {context.agent_name} agent"
                ):
                    # Send agent started notification
                    await self._send_agent_started(context)
                    
                    # Send initial thinking update
                    await self._send_agent_thinking(
                        context,
                        f"Starting execution of {context.agent_name} agent...",
                        step_number=1
                    )
                    
                    execution_start = time.time()
                    
                    # Update execution state to running
                    self.execution_tracker.update_execution_state(
                        execution_id, ExecutionState.RUNNING
                    )
                    
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        self._execute_with_error_handling(context, state, execution_id),
                        timeout=self.AGENT_EXECUTION_TIMEOUT
                    )
                    
                    execution_time = time.time() - execution_start
                    self.execution_stats['execution_times'].append(execution_time)
                    
                    # Mark execution state based on result
                    if result.success:
                        self.execution_tracker.update_execution_state(
                            execution_id, ExecutionState.COMPLETED, result=result.data
                        )
                        await self._send_agent_completed(context, result)
                    else:
                        self.execution_tracker.update_execution_state(
                            execution_id, ExecutionState.FAILED, error=result.error
                        )
                        await self._send_agent_completed(context, result)
                    
                    # Update history (request-scoped)
                    self._update_history(result)
                    return result
                    
            except asyncio.TimeoutError:
                self.execution_stats['timeout_executions'] += 1
                self.execution_stats['failed_executions'] += 1
                
                # Mark execution as timed out
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.TIMEOUT,
                    error=f"Execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s"
                )
                
                # Create timeout result
                timeout_result = self._create_timeout_result(context)
                await self._send_agent_completed(context, timeout_result)
                
                self._update_history(timeout_result)
                return timeout_result
                
            except Exception as e:
                self.execution_stats['failed_executions'] += 1
                
                # Mark execution as failed
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.FAILED, error=str(e)
                )
                
                logger.error(f"Agent execution failed for {context.agent_name}: {e}")
                raise RuntimeError(f"Agent execution failed: {e}")
                
            finally:
                # Remove from active runs
                self.active_runs.pop(execution_id, None)
                self.execution_stats['concurrent_executions'] -= 1
    
    def _validate_execution_context(self, context: AgentExecutionContext) -> None:
        """Validate execution context for this request.
        
        Args:
            context: The agent execution context to validate
            
        Raises:
            ValueError: If context contains invalid values
        """
        if not context.user_id or not context.user_id.strip():
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Invalid execution context - user_id must be non-empty. "
                f"Got: {context.user_id!r}, Agent: {getattr(context, 'agent_name', 'unknown')}"
            )
            raise ValueError("Invalid execution context: user_id must be non-empty")
        
        if not context.run_id or not context.run_id.strip():
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Invalid execution context - run_id must be non-empty. "
                f"Got: {context.run_id!r}, User: {context.user_id[:8]}..., "
                f"Agent: {getattr(context, 'agent_name', 'unknown')}"
            )
            raise ValueError("Invalid execution context: run_id must be non-empty")
        
        if context.run_id == 'registry':
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Invalid execution context - run_id cannot be 'registry' placeholder. "
                f"User: {context.user_id[:8]}..., Agent: {getattr(context, 'agent_name', 'unknown')}, "
                f"This indicates improper context initialization."
            )
            raise ValueError("Invalid execution context: run_id cannot be 'registry' placeholder")
        
        # Validate consistency with user context
        if context.user_id != self.user_context.user_id:
            logger.error(
                f" FAIL:  VALIDATION FAILURE: Context user_id mismatch during validation. "
                f"Expected: {self.user_context.user_id}, Got: {context.user_id}, "
                f"Agent: {getattr(context, 'agent_name', 'unknown')}, "
                f"This is a critical security violation - user isolation compromised."
            )
            raise ValueError(
                f"Context user_id mismatch: expected {self.user_context.user_id}, got {context.user_id}"
            )
        
        if context.run_id != self.user_context.run_id:
            logger.warning(
                f"Context run_id mismatch: expected {self.user_context.run_id}, got {context.run_id} "
                f"- this may indicate multiple runs in same request"
            )
    
    async def _execute_with_error_handling(self, 
                                          context: AgentExecutionContext,
                                          state: UserExecutionContext,
                                          execution_id: str) -> AgentExecutionResult:
        """Execute agent with error handling and fallback.
        
        Args:
            context: Agent execution context
            state: Deep agent state
            execution_id: Execution tracking ID
            
        Returns:
            AgentExecutionResult: Results of execution
        """
        start_time = time.time()
        
        try:
            # Heartbeat for death monitoring
            self.execution_tracker.heartbeat(execution_id)
            
            # Send thinking updates during execution
            await self._send_agent_thinking(
                context,
                f"Processing request: {getattr(state, 'user_prompt', 'Task')[:100]}...",
                step_number=2
            )
            
            # Execute the agent
            result = await self.agent_core.execute_agent(context, state)
            
            # Final heartbeat
            self.execution_tracker.heartbeat(execution_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Agent {context.agent_name} failed: {e}")
            
            # Use fallback manager for error handling
            return await self.fallback_manager.create_fallback_result(
                context, state, e, start_time
            )
    
    async def _send_agent_started(self, context: AgentExecutionContext) -> None:
        """Send agent started notification."""
        try:
            await self.websocket_bridge.notify_agent_started(
                context.run_id,
                context.agent_name,
                {
                    "status": "started", 
                    "context": context.metadata or {},
                    "isolated": True,
                    "user_id": self.user_context.user_id,
                    "engine_id": self.engine_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to send agent started notification: {e}")
    
    async def _send_agent_thinking(self, 
                                  context: AgentExecutionContext,
                                  thought: str,
                                  step_number: Optional[int] = None) -> None:
        """Send agent thinking notification."""
        try:
            await self.websocket_bridge.notify_agent_thinking(
                context.run_id,
                context.agent_name,
                thought,
                step_number
            )
        except Exception as e:
            logger.error(f"Failed to send agent thinking notification: {e}")
    
    async def _send_agent_completed(self, 
                                   context: AgentExecutionContext,
                                   result: AgentExecutionResult) -> None:
        """Send agent completed notification."""
        try:
            report = {
                "agent_name": context.agent_name,
                "success": result.success,
                "duration_ms": result.execution_time * 1000 if result.execution_time else 0,
                "status": "completed" if result.success else "failed",
                "isolated": True,
                "user_id": self.user_context.user_id,
                "engine_id": self.engine_id
            }
            
            if not result.success and result.error:
                report["error"] = result.error
            
            await self.websocket_bridge.notify_agent_completed(
                context.run_id,
                context.agent_name,
                report,
                result.execution_time * 1000 if result.execution_time else 0
            )
        except Exception as e:
            logger.error(f"Failed to send agent completed notification: {e}")
    
    def _create_timeout_result(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """Create result for timed out execution."""
        return AgentExecutionResult(
            success=False,
            agent_name=context.agent_name,
            execution_time=self.AGENT_EXECUTION_TIMEOUT,
            error=f"Agent execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s",
            state=None,
            metadata={'timeout': True, 'engine_id': self.engine_id}
        )
    
    def _update_history(self, result: AgentExecutionResult) -> None:
        """Update run history with size limit."""
        self.run_history.append(result)
        if len(self.run_history) > self.MAX_HISTORY_SIZE:
            self.run_history = self.run_history[-self.MAX_HISTORY_SIZE:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this request.
        
        Returns:
            Dictionary with execution statistics
        """
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
        
        # Add engine metadata
        stats.update({
            'engine_id': self.engine_id,
            'user_id': self.user_context.user_id,
            'run_id': self.user_context.run_id,
            'active_runs_count': len(self.active_runs),
            'history_count': len(self.run_history),
            'created_at': self.created_at.isoformat(),
            'is_active': self._is_active,
            'max_concurrent_executions': self.max_concurrent_executions
        })
        
        return stats
    
    async def cleanup(self) -> None:
        """Clean up engine resources.
        
        This should be called when the request is complete to ensure
        proper resource cleanup.
        """
        if not self._is_active:
            return
        
        try:
            logger.info(f"Cleaning up RequestScopedExecutionEngine {self.engine_id}")
            
            # Cancel any remaining active runs
            if self.active_runs:
                logger.warning(f"Cancelling {len(self.active_runs)} active runs in engine {self.engine_id}")
                for execution_id, context in self.active_runs.items():
                    try:
                        self.execution_tracker.update_execution_state(
                            execution_id, ExecutionState.CANCELLED,
                            error="Engine cleanup"
                        )
                    except Exception as e:
                        logger.error(f"Error cancelling execution {execution_id}: {e}")
            
            # Shutdown components
            await self.periodic_update_manager.shutdown()
            
            # Clear all state
            self.active_runs.clear()
            self.run_history.clear()
            self.execution_stats.clear()
            
            # Mark as inactive
            self._is_active = False
            
            logger.info(f" PASS:  Cleaned up RequestScopedExecutionEngine {self.engine_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up RequestScopedExecutionEngine {self.engine_id}: {e}")
            raise
    
    def is_active(self) -> bool:
        """Check if this engine is still active."""
        return self._is_active


# Factory function for easy creation
def create_request_scoped_engine(user_context: UserExecutionContext,
                                registry: 'AgentRegistry',
                                websocket_bridge: 'AgentWebSocketBridge',
                                max_concurrent_executions: int = 3) -> RequestScopedExecutionEngine:
    """Factory function to create RequestScopedExecutionEngine.
    
    Args:
        user_context: User execution context for isolation
        registry: Agent registry
        websocket_bridge: WebSocket bridge
        max_concurrent_executions: Maximum concurrent executions
        
    Returns:
        RequestScopedExecutionEngine: New isolated execution engine
    """
    return RequestScopedExecutionEngine(
        user_context=user_context,
        registry=registry,
        websocket_bridge=websocket_bridge,
        max_concurrent_executions=max_concurrent_executions
    )