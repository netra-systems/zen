"""Core agent execution functionality."""

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentExecutionCore:
    """Handles core agent execution logic."""
    
    def __init__(self, registry: 'AgentRegistry', websocket_notifier: Optional['WebSocketNotifier'] = None):
        self.registry = registry
        self.websocket_notifier = websocket_notifier
    
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute a single agent with retry logic."""
        # Send agent started notification
        if self.websocket_notifier:
            await self.websocket_notifier.send_agent_started(context)
        
        agent = self._get_agent_or_error(context.agent_name)
        if isinstance(agent, AgentExecutionResult):
            # Send error notification for agent not found
            if self.websocket_notifier:
                await self.websocket_notifier.send_agent_error(
                    context, agent.error, "agent_not_found"
                )
            return agent
            
        result = await self._run_agent_with_timing(agent, context, state)
        
        # Send completion or error notification based on result
        if self.websocket_notifier:
            if result.success:
                await self.websocket_notifier.send_agent_completed(
                    context, 
                    {"success": True, "agent_name": context.agent_name},
                    (result.duration * 1000) if result.duration else 0
                )
            else:
                await self.websocket_notifier.send_agent_error(
                    context, result.error or "Unknown error", "execution_failure"
                )
        
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
            return await self._execute_agent_with_success(agent, context, state, start_time)
        except Exception as e:
            return self._handle_execution_error(context, state, e, start_time)
    
    async def _execute_agent_with_success(self, agent, context: AgentExecutionContext,
                                         state: DeepAgentState, start_time: float) -> AgentExecutionResult:
        """Execute agent and create success result."""
        await self._execute_agent_lifecycle(agent, context, state)
        return self._create_success_result(state, time.time() - start_time)
    
    async def _execute_agent_lifecycle(self, agent, context: AgentExecutionContext,
                                      state: DeepAgentState) -> None:
        """Execute agent with lifecycle events."""
        # Set user_id on agent if available for proper websocket routing
        if hasattr(state, 'user_id') and state.user_id:
            agent._user_id = state.user_id
        
        # CRITICAL: Propagate WebSocket context to sub-agents for event emission
        if self.websocket_notifier:
            # Try multiple methods for backward compatibility
            if hasattr(agent, 'set_websocket_context'):
                # Preferred method: pass both context and notifier
                agent.set_websocket_context(context, self.websocket_notifier)
            elif hasattr(agent, 'websocket_notifier'):
                # Direct notifier assignment
                agent.websocket_notifier = self.websocket_notifier
            elif hasattr(agent, 'websocket_manager'):
                # Fallback: set manager directly (existing pattern)
                agent.websocket_manager = self.websocket_notifier.websocket_manager
                
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