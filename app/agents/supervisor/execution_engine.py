"""Execution engine for supervisor agent pipelines."""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager
    from app.agents.supervisor.agent_registry import AgentRegistry
from datetime import datetime, timezone
from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, 
    ExecutionStrategy, PipelineStep
)
from app.schemas import (
    SubAgentLifecycle, WebSocketMessage, AgentStarted,
    SubAgentUpdate, AgentCompleted, SubAgentState
)

logger = central_logger.get_logger(__name__)


class ExecutionEngine:
    """Handles agent execution logic."""
    
    def __init__(self, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager'):
        self.registry = registry
        self.websocket_manager = websocket_manager
        self.active_runs: Dict[str, AgentExecutionContext] = {}
        self.run_history: List[AgentExecutionResult] = []
        
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single agent with retry logic."""
        agent = self.registry.get(context.agent_name)
        if not agent:
            return self._create_error_result(f"Agent {context.agent_name} not found")
        return await self._run_agent_with_timing(agent, context, state)
    
    async def _run_agent_with_timing(self, agent, context: AgentExecutionContext,
                                    state: DeepAgentState) -> AgentExecutionResult:
        """Run agent and track timing."""
        start_time = time.time()
        try:
            await self._execute_agent_lifecycle(agent, context, state)
            return self._create_success_result(state, time.time() - start_time)
        except Exception as e:
            return await self._handle_execution_error(context, state, e, start_time)
    
    async def _execute_agent_lifecycle(self, agent, context: AgentExecutionContext,
                                      state: DeepAgentState) -> None:
        """Execute agent with lifecycle events."""
        await self._send_agent_started(context, state)
        await agent.execute(state, context.run_id, True)
    
    async def execute_pipeline(self, steps: List[PipelineStep],
                              context: AgentExecutionContext,
                              state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute a pipeline of agents."""
        results = []
        for step in steps:
            if await self._process_pipeline_step(step, context, state, results):
                break
        return results
    
    async def _process_pipeline_step(self, step: PipelineStep, context: AgentExecutionContext,
                                    state: DeepAgentState, results: List) -> bool:
        """Process single pipeline step. Returns True to stop pipeline."""
        if not await self._should_execute_step(step, state):
            return False
        result = await self._execute_and_append(step, context, state, results)
        return self._should_stop_pipeline(result, step)
    
    async def _execute_and_append(self, step: PipelineStep, context: AgentExecutionContext,
                                 state: DeepAgentState, results: List) -> AgentExecutionResult:
        """Execute step and append to results."""
        step_context = self._create_step_context(context, step)
        result = await self._execute_step(step, step_context, state)
        results.append(result)
        return result
    
    def _should_stop_pipeline(self, result: AgentExecutionResult, 
                            step: PipelineStep) -> bool:
        """Check if pipeline should stop."""
        return not result.success and not step.metadata.get("continue_on_error")
    
    async def _execute_step(self, step: PipelineStep,
                           context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single pipeline step."""
        if step.strategy == ExecutionStrategy.PARALLEL:
            return await self._execute_parallel(step, context, state)
        return await self.execute_agent(context, state)
    
    async def _execute_parallel(self, step: PipelineStep,
                               context: AgentExecutionContext,
                               state: DeepAgentState) -> AgentExecutionResult:
        """Execute agents in parallel."""
        tasks = []
        for agent_name in step.metadata.get("parallel_agents", []):
            ctx = self._create_agent_context(context, agent_name)
            tasks.append(self.execute_agent(ctx, state))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._merge_parallel_results(results)
    
    def _create_error_result(self, error: str) -> AgentExecutionResult:
        """Create error result."""
        return AgentExecutionResult(success=False, error=error)
    
    def _create_success_result(self, state: DeepAgentState,
                              duration: float) -> AgentExecutionResult:
        """Create success result."""
        return AgentExecutionResult(
            success=True, state=state, duration=duration)
    
    async def _handle_execution_error(self, context: AgentExecutionContext,
                                     state: DeepAgentState,
                                     error: Exception,
                                     start_time: float) -> AgentExecutionResult:
        """Handle execution errors with retry logic."""
        self._log_error(context.agent_name, error)
        if self._can_retry(context):
            return await self._retry_execution(context, state)
        return self._create_failure_result(error, time.time() - start_time)
    
    def _log_error(self, agent_name: str, error: Exception) -> None:
        """Log execution error."""
        logger.error(f"Agent {agent_name} failed: {error}")
    
    def _can_retry(self, context: AgentExecutionContext) -> bool:
        """Check if retry is allowed."""
        return context.retry_count < context.max_retries
    
    async def _retry_execution(self, context: AgentExecutionContext,
                              state: DeepAgentState) -> AgentExecutionResult:
        """Retry agent execution."""
        context.retry_count += 1
        logger.info(f"Retrying {context.agent_name} ({context.retry_count}/{context.max_retries})")
        await asyncio.sleep(2 ** context.retry_count)
        return await self.execute_agent(context, state)
    
    def _create_failure_result(self, error: Exception, duration: float) -> AgentExecutionResult:
        """Create failure result."""
        return AgentExecutionResult(
            success=False, error=str(error), duration=duration)
    
    async def _send_agent_started(self, context: AgentExecutionContext,
                                 state: DeepAgentState) -> None:
        """Send agent started notification."""
        if not self.websocket_manager:
            return
        message = self._build_started_message(context)
        await self._send_websocket_message(context.thread_id, message)
    
    def _build_started_message(self, context: AgentExecutionContext) -> WebSocketMessage:
        """Build agent started message."""
        return WebSocketMessage(
            type="agent_started",
            content=self._create_started_content(context)
        )
    
    def _create_started_content(self, context: AgentExecutionContext) -> AgentStarted:
        """Create agent started content."""
        return AgentStarted(
            agent_name=context.agent_name,
            run_id=context.run_id,
            thread_id=context.thread_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    async def _send_websocket_message(self, thread_id: str, 
                                     message: WebSocketMessage) -> None:
        """Send message via websocket."""
        await self.websocket_manager.send_to_thread(
            thread_id, message.model_dump())
    
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
    
    def _create_step_context(self, base_context: AgentExecutionContext,
                           step: PipelineStep) -> AgentExecutionContext:
        """Create context for a pipeline step."""
        context = self._copy_base_context(base_context)
        context.agent_name = step.agent_name
        context.metadata = step.metadata
        return context
    
    def _copy_base_context(self, base: AgentExecutionContext) -> AgentExecutionContext:
        """Copy base context fields."""
        return AgentExecutionContext(
            run_id=base.run_id,
            thread_id=base.thread_id,
            user_id=base.user_id,
            agent_name=""
        )
    
    def _create_agent_context(self, base: AgentExecutionContext,
                            agent_name: str) -> AgentExecutionContext:
        """Create context for an agent."""
        return AgentExecutionContext(
            run_id=base.run_id,
            thread_id=base.thread_id,
            user_id=base.user_id,
            agent_name=agent_name
        )
    
    def _merge_parallel_results(self, results: List) -> AgentExecutionResult:
        """Merge results from parallel execution."""
        valid_results = self._filter_valid_results(results)
        success = all(r.success for r in valid_results)
        errors = self._collect_errors(valid_results)
        duration = sum(r.duration for r in valid_results)
        return self._build_merged_result(success, errors, duration)
    
    def _filter_valid_results(self, results: List) -> List[AgentExecutionResult]:
        """Filter valid execution results."""
        return [r for r in results if isinstance(r, AgentExecutionResult)]
    
    def _collect_errors(self, results: List[AgentExecutionResult]) -> List[str]:
        """Collect error messages."""
        return [r.error for r in results if r.error]
    
    def _build_merged_result(self, success: bool, errors: List[str], 
                           duration: float) -> AgentExecutionResult:
        """Build merged execution result."""
        return AgentExecutionResult(
            success=success,
            error="; ".join(errors) if errors else None,
            duration=duration
        )