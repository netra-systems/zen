"""
Extension methods for SupervisorAgent testing.
These methods are monkey-patched onto the SupervisorAgent for testing purposes.
"""

import asyncio

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult


async def _route_to_agent(self, state, context, agent_name):
    """Route to specific agent."""
    agent = self.agents.get(agent_name)
    if not agent:
        return AgentExecutionResult(success=False, error=f"Agent {agent_name} not found")
    
    try:
        result_state = await agent.execute(state, context.run_id, True)
        return AgentExecutionResult(success=True, state=result_state)
    except Exception as e:
        return AgentExecutionResult(success=False, error=str(e))


async def _route_to_agent_with_retry(self, state, context, agent_name):
    """Route with retry logic."""
    max_retries = getattr(context, 'max_retries', 3)
    
    for attempt in range(max_retries):
        result = await self._route_to_agent(state, context, agent_name)
        if result.success:
            return result
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
    
    return result


async def _route_to_agent_with_circuit_breaker(self, state, context, agent_name):
    """Route with circuit breaker."""
    if not hasattr(self, 'circuit_breaker_failures'):
        self.circuit_breaker_failures = {}
    
    failures = self.circuit_breaker_failures.get(agent_name, 0)
    
    if failures >= self.circuit_breaker_threshold:
        return AgentExecutionResult(
            success=False,
            error=f"Circuit breaker open for {agent_name}"
        )
    
    result = await self._route_to_agent(state, context, agent_name)
    
    if not result.success:
        self.circuit_breaker_failures[agent_name] = failures + 1
    else:
        self.circuit_breaker_failures[agent_name] = 0
    
    return result


def install_supervisor_extensions():
    """Install extension methods on SupervisorAgent for testing."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    
    SupervisorAgent._route_to_agent = _route_to_agent
    SupervisorAgent._route_to_agent_with_retry = _route_to_agent_with_retry
    SupervisorAgent._route_to_agent_with_circuit_breaker = _route_to_agent_with_circuit_breaker