"""Agent Routing Helper for Supervisor Agent

Handles agent routing and execution context creation.
All methods kept under 8 lines.

Business Value: Standardized agent routing patterns.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.execution_context import (
        AgentExecutionContext,
        AgentExecutionResult,
    )

from netra_backend.app.services.user_execution_context import UserExecutionContext


class SupervisorAgentRouter:
    """Helper class for supervisor agent routing."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def route_to_agent(self, user_context: UserExecutionContext, 
                           context: 'AgentExecutionContext', 
                           agent_name: str) -> 'AgentExecutionResult':
        """Route request to specific agent with basic execution."""
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext,
        )
        exec_context = self._create_agent_execution_context(context, agent_name)
        return await self.supervisor.engine.execute_agent(exec_context, user_context)
    
    async def route_to_agent_with_retry(self, user_context: UserExecutionContext,
                                      context: 'AgentExecutionContext',
                                      agent_name: str) -> 'AgentExecutionResult':
        """Route request to agent with retry logic."""
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext,
        )
        exec_context = self._create_agent_execution_context(context, agent_name)
        exec_context.max_retries = context.max_retries
        return await self.supervisor.engine.execute_agent(exec_context, user_context)
    
    async def route_to_agent_with_circuit_breaker(self, state: DeepAgentState,
                                                 context: 'AgentExecutionContext',
                                                 agent_name: str) -> 'AgentExecutionResult':
        """Route request to agent with circuit breaker protection."""
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext,
        )
        exec_context = self._create_agent_execution_context(context, agent_name)
        return await self.supervisor.engine._execute_with_fallback(exec_context, state)
    
    def _create_agent_execution_context(self, base_context, agent_name: str):
        """Create AgentExecutionContext from base context."""
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext,
        )
        return AgentExecutionContext(
            run_id=base_context.run_id, thread_id=base_context.thread_id,
            user_id=base_context.user_id, agent_name=agent_name,
            max_retries=getattr(base_context, 'max_retries', 3)
        )