"""
Extension methods for SupervisorAgent testing.
These methods are monkey-patched onto the SupervisorAgent for testing purposes.
"""

import asyncio
import time

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
    """Route with circuit breaker and recovery logic."""
    if not hasattr(self, 'circuit_breaker_failures'):
        self.circuit_breaker_failures = {}
    if not hasattr(self, 'circuit_breaker_open_time'):
        self.circuit_breaker_open_time = {}
    
    failures = self.circuit_breaker_failures.get(agent_name, 0)
    cooldown_period = getattr(self, 'circuit_breaker_cooldown', 0.1)  # Default 100ms
    
    # Check if circuit breaker is open
    if failures >= self.circuit_breaker_threshold:
        open_time = self.circuit_breaker_open_time.get(agent_name)
        
        # If this is the first time hitting the threshold, record the time
        if open_time is None:
            self.circuit_breaker_open_time[agent_name] = time.time()
            return AgentExecutionResult(
                success=False,
                error=f"Circuit breaker open for {agent_name}"
            )
        
        # Check if cooldown period has passed
        if time.time() - open_time < cooldown_period:
            return AgentExecutionResult(
                success=False,
                error=f"Circuit breaker open for {agent_name}"
            )
        
        # Cooldown period has passed, attempt to reset (half-open state)
        # Try the request - if it succeeds, reset failures
        result = await self._route_to_agent(state, context, agent_name)
        
        if result.success:
            # Success! Reset circuit breaker
            self.circuit_breaker_failures[agent_name] = 0
            self.circuit_breaker_open_time.pop(agent_name, None)
        else:
            # Still failing, increment failure count and reset open time
            self.circuit_breaker_failures[agent_name] = failures + 1
            self.circuit_breaker_open_time[agent_name] = time.time()
        
        return result
    
    # Circuit breaker is closed, proceed normally
    result = await self._route_to_agent(state, context, agent_name)
    
    if not result.success:
        self.circuit_breaker_failures[agent_name] = failures + 1
    else:
        self.circuit_breaker_failures[agent_name] = 0
        # Also clear open time if it was set
        self.circuit_breaker_open_time.pop(agent_name, None)
    
    return result

def install_supervisor_extensions():
    """Install extension methods on SupervisorAgent for testing."""
    from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
    
    SupervisorAgent._route_to_agent = _route_to_agent
    SupervisorAgent._route_to_agent_with_retry = _route_to_agent_with_retry
    SupervisorAgent._route_to_agent_with_circuit_breaker = _route_to_agent_with_circuit_breaker