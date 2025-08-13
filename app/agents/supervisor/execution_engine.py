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
        
        start_time = time.time()
        try:
            await self._send_agent_started(context, state)
            await agent.execute(state, context.run_id, True)
            duration = time.time() - start_time
            return self._create_success_result(state, duration)
        except Exception as e:
            return await self._handle_execution_error(context, state, e, start_time)
    
    async def execute_pipeline(self, steps: List[PipelineStep],
                              context: AgentExecutionContext,
                              state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute a pipeline of agents."""
        results = []
        for step in steps:
            if not await self._should_execute_step(step, state):
                continue
            step_context = self._create_step_context(context, step)
            result = await self._execute_step(step, step_context, state)
            results.append(result)
            if not result.success and not step.metadata.get("continue_on_error"):
                break
        return results
    
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
        duration = time.time() - start_time
        logger.error(f"Agent {context.agent_name} failed: {error}")
        
        if context.retry_count < context.max_retries:
            context.retry_count += 1
            logger.info(f"Retrying {context.agent_name} ({context.retry_count}/{context.max_retries})")
            await asyncio.sleep(2 ** context.retry_count)
            return await self.execute_agent(context, state)
        
        return AgentExecutionResult(
            success=False, error=str(error), duration=duration)
    
    async def _send_agent_started(self, context: AgentExecutionContext,
                                 state: DeepAgentState) -> None:
        """Send agent started notification."""
        if not self.websocket_manager:
            return
        message = WebSocketMessage(
            type="agent_started",
            content=AgentStarted(
                agent_name=context.agent_name,
                run_id=context.run_id,
                thread_id=context.thread_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        )
        await self.websocket_manager.send_to_thread(
            context.thread_id, message.model_dump())
    
    async def _should_execute_step(self, step: PipelineStep,
                                  state: DeepAgentState) -> bool:
        """Check if step should be executed."""
        if not step.condition:
            return True
        try:
            return await step.condition(state)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _create_step_context(self, base_context: AgentExecutionContext,
                           step: PipelineStep) -> AgentExecutionContext:
        """Create context for a pipeline step."""
        return AgentExecutionContext(
            run_id=base_context.run_id,
            thread_id=base_context.thread_id,
            user_id=base_context.user_id,
            agent_name=step.agent_name,
            metadata=step.metadata
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
        success = all(r.success for r in results if isinstance(r, AgentExecutionResult))
        errors = [r.error for r in results if isinstance(r, AgentExecutionResult) and r.error]
        duration = sum(r.duration for r in results if isinstance(r, AgentExecutionResult))
        return AgentExecutionResult(
            success=success,
            error="; ".join(errors) if errors else None,
            duration=duration
        )