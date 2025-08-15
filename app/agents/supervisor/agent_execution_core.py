"""Core agent execution functionality."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.supervisor.agent_registry import AgentRegistry

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult
)

logger = central_logger.get_logger(__name__)


class AgentExecutionCore:
    """Handles core agent execution logic."""
    
    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry
    
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single agent with retry logic."""
        agent = self._get_agent_or_error(context.agent_name)
        if isinstance(agent, AgentExecutionResult):
            return agent
        result = await self._run_agent_with_timing(agent, context, state)
        return result
    
    def _get_agent_or_error(self, agent_name: str):
        """Get agent from registry or return error result."""
        agent = self.registry.get(agent_name)
        if not agent:
            return self._create_error_result(f"Agent {agent_name} not found")
        return agent
    
    async def _run_agent_with_timing(self, agent, context: AgentExecutionContext,
                                    state: DeepAgentState) -> AgentExecutionResult:
        """Run agent and track timing."""
        start_time = time.time()
        try:
            await self._execute_agent_lifecycle(agent, context, state)
            return self._create_success_result(state, time.time() - start_time)
        except Exception as e:
            return self._handle_execution_error(context, state, e, start_time)
    
    async def _execute_agent_lifecycle(self, agent, context: AgentExecutionContext,
                                      state: DeepAgentState) -> None:
        """Execute agent with lifecycle events."""
        # Set user_id on agent if available for proper websocket routing
        if hasattr(state, 'user_id') and state.user_id:
            agent._user_id = state.user_id
        await agent.execute(state, context.run_id, True)
    
    def _handle_execution_error(self, context: AgentExecutionContext,
                               state: DeepAgentState, error: Exception,
                               start_time: float) -> AgentExecutionResult:
        """Handle execution errors."""
        self._log_error(context.agent_name, error)
        return self._create_failure_result(error, time.time() - start_time)
    
    def _log_error(self, agent_name: str, error: Exception) -> None:
        """Log execution error."""
        logger.error(f"Agent {agent_name} failed: {error}")
    
    def _create_error_result(self, error: str) -> AgentExecutionResult:
        """Create error result."""
        return AgentExecutionResult(success=False, error=error)
    
    def _create_success_result(self, state: DeepAgentState,
                              duration: float) -> AgentExecutionResult:
        """Create success result."""
        return AgentExecutionResult(
            success=True, state=state, duration=duration)
    
    def _create_failure_result(self, error: Exception, 
                              duration: float) -> AgentExecutionResult:
        """Create failure result."""
        return AgentExecutionResult(
            success=False, error=str(error), duration=duration)