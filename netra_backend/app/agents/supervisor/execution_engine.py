"""Execution engine for supervisor agent pipelines with concurrency optimization.

Business Value: Supports 5+ concurrent users with <2s response times and proper event ordering.
Optimizations: Semaphore-based concurrency control, event sequencing, backlog handling.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.agents.supervisor.fallback_manager import FallbackManager
from netra_backend.app.agents.supervisor.observability_flow import (
    get_supervisor_flow_logger,
)
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngine:
    """Handles agent execution orchestration with concurrency optimization.
    
    Features:
    - Semaphore-based concurrency control for 5+ concurrent users
    - Guaranteed WebSocket event delivery with proper sequencing
    - Backlog handling with user feedback
    - Periodic updates for long-running operations
    - Resource management and cleanup
    """
    
    MAX_HISTORY_SIZE = 100  # Prevent memory leak
    MAX_CONCURRENT_AGENTS = 10  # Support 5 concurrent users (2 agents each)
    AGENT_EXECUTION_TIMEOUT = 30.0  # 30 seconds max per agent
    
    def __init__(self, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager'):
        self.registry = registry
        self.websocket_manager = websocket_manager
        self.active_runs: Dict[str, AgentExecutionContext] = {}
        self.run_history: List[AgentExecutionResult] = []
        self._init_components()
        
    def _init_components(self) -> None:
        """Initialize execution components."""
        self.websocket_notifier = WebSocketNotifier(self.websocket_manager)
        self.periodic_update_manager = PeriodicUpdateManager(self.websocket_notifier)
        self.agent_core = AgentExecutionCore(self.registry, self.websocket_notifier)
        self.fallback_manager = FallbackManager(self.websocket_notifier)
        self.flow_logger = get_supervisor_flow_logger()
        
        # CONCURRENCY OPTIMIZATION: Semaphore for agent execution control
        self.execution_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_AGENTS)
        self.execution_stats = {
            'total_executions': 0,
            'concurrent_executions': 0,
            'queue_wait_times': [],
            'execution_times': [],
            'failed_executions': 0
        }
        
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single agent with concurrency control and guaranteed event delivery."""
        queue_start_time = time.time()
        
        # CONCURRENCY CONTROL: Use semaphore to limit concurrent executions
        async with self.execution_semaphore:
            queue_wait_time = time.time() - queue_start_time
            self.execution_stats['queue_wait_times'].append(queue_wait_time)
            self.execution_stats['total_executions'] += 1
            self.execution_stats['concurrent_executions'] += 1
            
            # Send queue wait notification if significant delay
            if queue_wait_time > 1.0:
                await self.send_agent_thinking(
                    context,
                    f"Request queued due to high load - starting now (waited {queue_wait_time:.1f}s)",
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
                    # Send agent started with guaranteed delivery
                    await self.websocket_notifier.send_agent_started(context)
                    
                    # Send initial thinking update
                    await self.send_agent_thinking(
                        context, 
                        f"Starting execution of {context.agent_name} agent...",
                        step_number=1
                    )
                    
                    execution_start = time.time()
                    
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        self._execute_with_error_handling(context, state),
                        timeout=self.AGENT_EXECUTION_TIMEOUT
                    )
                    
                    execution_time = time.time() - execution_start
                    self.execution_stats['execution_times'].append(execution_time)
                    
                    # CRITICAL: Always send completion events, regardless of success/failure
                    # This ensures WebSocket clients know when agent execution is complete
                    if result.success:
                        await self._send_final_execution_report(context, result, state)
                    else:
                        # Send completion event for failed/fallback cases
                        await self._send_completion_for_failed_execution(context, result, state)
                    
                    self._update_history(result)
                    return result
                    
            except asyncio.TimeoutError:
                self.execution_stats['failed_executions'] += 1
                # Send timeout notification
                await self.send_agent_thinking(
                    context,
                    f"Agent execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s",
                    step_number=-1
                )
                timeout_result = self._create_timeout_result(context)
                await self._send_completion_for_failed_execution(context, timeout_result, state)
                self._update_history(timeout_result)
                return timeout_result
                
            except Exception as e:
                self.execution_stats['failed_executions'] += 1
                logger.error(f"Unexpected error in agent execution: {e}")
                error_result = self._create_error_result(context, e)
                await self._send_completion_for_failed_execution(context, error_result, state)
                self._update_history(error_result)
                return error_result
                
            finally:
                self.execution_stats['concurrent_executions'] -= 1
    
    async def _execute_with_error_handling(self, context: AgentExecutionContext,
                                          state: DeepAgentState) -> AgentExecutionResult:
        """Execute agent with error handling and fallback."""
        start_time = time.time()
        try:
            # Send thinking updates during execution
            await self.send_agent_thinking(
                context,
                f"Processing request: {getattr(state, 'user_prompt', 'Task')[:100]}...",
                step_number=2
            )
            
            # Execute the agent
            result = await self.agent_core.execute_agent(context, state)
            
            # Send partial result if available
            if result.success and hasattr(state, 'final_answer'):
                await self.send_partial_result(
                    context,
                    str(state.final_answer)[:500],
                    is_complete=True
                )
            
            return result
        except Exception as e:
            return await self._handle_execution_error(context, state, e, start_time)
    
    async def _handle_execution_error(self, context: AgentExecutionContext,
                                     state: DeepAgentState, error: Exception,
                                     start_time: float) -> AgentExecutionResult:
        """Handle execution errors with retry and fallback."""
        logger.error(f"Agent {context.agent_name} failed: {error}")
        if self._can_retry(context):
            return await self._retry_execution(context, state)
        return await self._execute_fallback_strategy(context, state, error, start_time)
    
    def _can_retry(self, context: AgentExecutionContext) -> bool:
        """Check if retry is allowed."""
        return context.retry_count < context.max_retries
    
    async def _retry_execution(self, context: AgentExecutionContext,
                              state: DeepAgentState) -> AgentExecutionResult:
        """Retry agent execution."""
        self._prepare_retry_context(context)
        self._log_retry_attempt(context)
        await self._wait_for_retry(context.retry_count)
        return await self.execute_agent(context, state)
    
    async def execute_pipeline(self, steps: List[PipelineStep],
                              context: AgentExecutionContext,
                              state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute a pipeline of agents."""
        return await self._execute_pipeline_steps(steps, context, state)
    
    async def _execute_pipeline_steps(self, steps: List[PipelineStep],
                                     context: AgentExecutionContext,
                                     state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute pipeline steps with optimal parallelization strategy."""
        # Check if steps can be executed in parallel (no dependencies)
        if self._can_execute_parallel(steps):
            return await self._execute_steps_parallel(steps, context, state)
        else:
            # Fall back to sequential execution with early termination
            results = []
            await self._process_steps_with_early_termination(steps, context, state, results)
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
                                    state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute steps in parallel using asyncio.gather for improved performance."""
        # Create tasks for all executable steps
        tasks = []
        executable_steps = []
        
        for step in steps:
            if await self._should_execute_step(step, state):
                step_context = self._create_step_context(context, step)
                task = self._execute_step_parallel_safe(step, step_context, state)
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
            return await self._execute_steps_sequential_fallback(steps, context, state)
    
    async def _execute_step_parallel_safe(self, step: PipelineStep,
                                        context: AgentExecutionContext,
                                        state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single step safely for parallel execution."""
        return await self._execute_with_fallback(context, state)
    
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
                                               state: DeepAgentState) -> List[AgentExecutionResult]:
        """Fallback to sequential execution if parallel fails."""
        logger.warning("Falling back to sequential execution")
        results = []
        await self._process_steps_with_early_termination(steps, context, state, results)
        return results
    
    async def _process_steps_with_early_termination(self, steps: List[PipelineStep],
                                                  context: AgentExecutionContext,
                                                  state: DeepAgentState, results: List) -> None:
        """Process steps with early termination on failure."""
        for step in steps:
            should_stop = await self._process_pipeline_step(step, context, state, results)
            if should_stop:
                break
    
    async def _process_pipeline_step(self, step: PipelineStep, context: AgentExecutionContext,
                                    state: DeepAgentState, results: List) -> bool:
        """Process single pipeline step. Returns True to stop pipeline."""
        if not await self._should_execute_step(step, state):
            return False
        return await self._execute_and_check_result(step, context, state, results)
    
    async def _execute_and_check_result(self, step: PipelineStep, context: AgentExecutionContext,
                                       state: DeepAgentState, results: List) -> bool:
        """Execute step and check if pipeline should stop."""
        result = await self._execute_step(step, context, state)
        results.append(result)
        return self._should_stop_pipeline(result, step)
    
    async def _should_execute_step(self, step: PipelineStep,
                                  state: DeepAgentState) -> bool:
        """Check if step should be executed."""
        if not step.condition:
            return True
        return await self._evaluate_condition(step.condition, state)
    
    async def _evaluate_condition(self, condition, state: DeepAgentState) -> bool:
        """Safely evaluate step condition."""
        try:
            return await condition(state)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    async def _execute_step(self, step: PipelineStep,
                           context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single pipeline step."""
        step_context = self._create_step_context(context, step)
        return await self._execute_with_fallback(step_context, state)
    
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
                                   state: DeepAgentState) -> AgentExecutionResult:
        """Execute agent with fallback handling."""
        execute_func = lambda: self.agent_core.execute_agent(context, state)
        return await self.fallback_manager.execute_with_fallback(context, state, execute_func)
    
    def _update_history(self, result: AgentExecutionResult) -> None:
        """Update run history with size limit."""
        self.run_history.append(result)
        self._enforce_history_size_limit()
    
    # WebSocket delegation methods
    async def send_agent_thinking(self, context: AgentExecutionContext, 
                                 thought: str, step_number: int = None) -> None:
        """Send agent thinking notification."""
        await self.websocket_notifier.send_agent_thinking(context, thought, step_number)
    
    async def send_partial_result(self, context: AgentExecutionContext,
                                 content: str, is_complete: bool = False) -> None:
        """Send partial result notification."""
        await self.websocket_notifier.send_partial_result(context, content, is_complete)
    
    async def send_tool_executing(self, context: AgentExecutionContext,
                                 tool_name: str) -> None:
        """Send tool executing notification."""
        await self.websocket_notifier.send_tool_executing(context, tool_name)
    
    async def send_final_report(self, context: AgentExecutionContext,
                               report: dict, duration_ms: float) -> None:
        """Send final report notification."""
        await self.websocket_notifier.send_final_report(context, report, duration_ms)
    
    async def _send_final_execution_report(self, context: AgentExecutionContext,
                                          result: AgentExecutionResult,
                                          state: DeepAgentState) -> None:
        """Send comprehensive final report after successful execution."""
        try:
            # Build comprehensive report
            report = {
                "agent_name": context.agent_name,
                "success": result.success,
                "duration_ms": result.duration * 1000 if result.duration else 0,
                "user_prompt": getattr(state, 'user_prompt', 'N/A'),
                "final_answer": getattr(state, 'final_answer', 'Completed'),
                "step_count": getattr(state, 'step_count', 0),
                "status": "completed"
            }
            
            # Send final report
            await self.send_final_report(
                context, 
                report, 
                result.duration * 1000 if result.duration else 0
            )
            
            # Send completion notification
            await self.websocket_notifier.send_agent_completed(
                context,
                report,
                result.duration * 1000 if result.duration else 0
            )
        except Exception as e:
            logger.warning(f"Failed to send final execution report: {e}")
    
    async def _send_completion_for_failed_execution(self, context: AgentExecutionContext,
                                                   result: AgentExecutionResult,
                                                   state: DeepAgentState) -> None:
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
            
            # Send completion notification for failed execution
            # This is CRITICAL for WebSocket clients to know execution finished
            await self.websocket_notifier.send_agent_completed(
                context,
                report,
                result.duration * 1000 if result.duration else 0
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
                                       state: DeepAgentState, error: Exception,
                                       start_time: float) -> AgentExecutionResult:
        """Execute fallback strategy for failed execution."""
        self._log_fallback_trigger(context)
        return await self.fallback_manager.create_fallback_result(context, state, error, start_time)

    # Fallback management delegation
    async def get_fallback_health_status(self) -> Dict[str, any]:
        """Get health status of fallback mechanisms."""
        return await self.fallback_manager.get_fallback_health_status()
    
    async def reset_fallback_mechanisms(self) -> None:
        """Reset all fallback mechanisms."""
        await self.fallback_manager.reset_fallback_mechanisms()
    
    async def _execute_fallback_strategy(self, context: AgentExecutionContext, 
                                        state: DeepAgentState, error: Exception, 
                                        start_time: float) -> AgentExecutionResult:
        """Execute fallback strategy for failed agent."""
        self._log_fallback_trigger(context)
        return await self.fallback_manager.create_fallback_result(context, state, error, start_time)
    
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
            execution_time=self.AGENT_EXECUTION_TIMEOUT,
            error=f"Agent execution timed out after {self.AGENT_EXECUTION_TIMEOUT}s",
            state=None,
            metadata={'timeout': True, 'timeout_duration': self.AGENT_EXECUTION_TIMEOUT}
        )
    
    def _create_error_result(self, context: AgentExecutionContext, error: Exception) -> AgentExecutionResult:
        """Create result for unexpected errors."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        return AgentExecutionResult(
            success=False,
            agent_name=context.agent_name,
            execution_time=0.0,
            error=str(error),
            state=None,
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
        
        # Add WebSocket stats
        delivery_stats = await self.websocket_notifier.get_delivery_stats()
        stats.update(delivery_stats)
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown execution engine and clean up resources."""
        # Shutdown WebSocket notifier
        await self.websocket_notifier.shutdown()
        
        # Shutdown periodic update manager
        await self.periodic_update_manager.shutdown()
        
        # Clear active runs
        self.active_runs.clear()
        
        logger.info("ExecutionEngine shutdown complete")