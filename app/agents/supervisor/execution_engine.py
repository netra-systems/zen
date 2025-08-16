"""Execution engine for supervisor agent pipelines."""

import asyncio
import time
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager
    from app.agents.supervisor.agent_registry import AgentRegistry

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from app.agents.supervisor.agent_execution_core import AgentExecutionCore
from app.agents.supervisor.websocket_notifier import WebSocketNotifier
from app.agents.supervisor.fallback_manager import FallbackManager

logger = central_logger.get_logger(__name__)


class ExecutionEngine:
    """Handles agent execution orchestration."""
    
    MAX_HISTORY_SIZE = 100  # Prevent memory leak
    
    def __init__(self, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager'):
        self.registry = registry
        self.websocket_manager = websocket_manager
        self.active_runs: Dict[str, AgentExecutionContext] = {}
        self.run_history: List[AgentExecutionResult] = []
        self._init_components()
        
    def _init_components(self) -> None:
        """Initialize execution components."""
        self.agent_core = AgentExecutionCore(self.registry)
        self.websocket_notifier = WebSocketNotifier(self.websocket_manager)
        self.fallback_manager = FallbackManager(self.websocket_notifier)
        
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single agent with retry logic."""
        await self.websocket_notifier.send_agent_started(context)
        result = await self._execute_with_error_handling(context, state)
        self._update_history(result)
        return result
    
    async def _execute_with_error_handling(self, context: AgentExecutionContext,
                                          state: DeepAgentState) -> AgentExecutionResult:
        """Execute agent with error handling and fallback."""
        start_time = time.time()
        try:
            return await self.agent_core.execute_agent(context, state)
        except Exception as e:
            return await self._handle_execution_error(context, state, e, start_time)
    
    async def _handle_execution_error(self, context: AgentExecutionContext,
                                     state: DeepAgentState, error: Exception,
                                     start_time: float) -> AgentExecutionResult:
        """Handle execution errors with retry and fallback."""
        logger.error(f"Agent {context.agent_name} failed: {error}")
        if self._can_retry(context):
            return await self._retry_execution(context, state)
        return await self.fallback_manager.create_fallback_result(context, state, error, start_time)
    
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
    
    async def execute_pipeline(self, steps: List[PipelineStep],
                              context: AgentExecutionContext,
                              state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute a pipeline of agents."""
        return await self._execute_pipeline_steps(steps, context, state)
    
    async def _execute_pipeline_steps(self, steps: List[PipelineStep],
                                     context: AgentExecutionContext,
                                     state: DeepAgentState) -> List[AgentExecutionResult]:
        """Execute pipeline steps sequentially."""
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
        if len(self.run_history) > self.MAX_HISTORY_SIZE:
            self.run_history = self.run_history[-self.MAX_HISTORY_SIZE:]
    
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
    
    # Fallback management delegation
    def get_fallback_health_status(self) -> Dict[str, any]:
        """Get health status of fallback mechanisms."""
        return self.fallback_manager.get_fallback_health_status()
    
    def reset_fallback_mechanisms(self) -> None:
        """Reset all fallback mechanisms."""
        self.fallback_manager.reset_fallback_mechanisms()