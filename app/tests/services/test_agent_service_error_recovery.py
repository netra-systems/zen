"""
Agent error recovery and resilience tests.

Tests agent failure recovery, timeout handling, resource cleanup,
and circuit breaker patterns.
"""

import pytest
import asyncio

from app.core.exceptions_base import NetraException
from app.tests.helpers.test_agent_orchestration_pytest_fixtures import resilient_orchestrator
from app.tests.helpers.test_agent_orchestration_assertions import (
    assert_agent_run_completed, assert_circuit_breaker_state,
    assert_retry_mechanism_worked, setup_failing_agent,
    setup_slow_agent, verify_cleanup_completed
)


class TestAgentErrorRecovery:
    """Test agent error recovery and resilience."""
    
    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self, resilient_orchestrator):
        """Test recovery from agent failures."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        setup_failing_agent(agent, "Temporary failure")
        
        result = await self._execute_with_retry(resilient_orchestrator, "user1", "retry request", "run_retry")
        
        assert_retry_mechanism_worked(result)
    
    async def _execute_with_retry(self, orchestrator, user_id, request, run_id):
        """Execute task with retry mechanism."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await orchestrator.execute_agent_task(user_id, request, run_id)
            except NetraException:
                if attempt == max_retries - 1:
                    raise
                
                await self._handle_retry_attempt(orchestrator, user_id, attempt)
    
    async def _handle_retry_attempt(self, orchestrator, user_id, attempt):
        """Handle retry attempt logic."""
        agent = orchestrator.agents[user_id]
        if attempt == 1:  # Second attempt succeeds
            agent.should_fail = False
        
        await asyncio.sleep(orchestrator.retry_delay)
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, resilient_orchestrator):
        """Test handling of agent timeouts."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        setup_slow_agent(agent, 1.0)
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                resilient_orchestrator.execute_agent_task("user1", "slow request", "run_slow"),
                timeout=0.1
            )
    
    @pytest.mark.asyncio
    async def test_agent_resource_cleanup_on_error(self, resilient_orchestrator):
        """Test resource cleanup when agent encounters errors."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        setup_failing_agent(agent)
        
        initial_active = resilient_orchestrator.active_agents
        
        with pytest.raises(NetraException):
            await resilient_orchestrator.execute_agent_task("user1", "failing request", "run_cleanup")
        
        await resilient_orchestrator.release_agent("user1")
        
        assert resilient_orchestrator.active_agents == initial_active - 1
        verify_cleanup_completed(resilient_orchestrator, "user1")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, resilient_orchestrator):
        """Test circuit breaker pattern for failing agents."""
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        setup_failing_agent(agent)
        
        await self._trigger_circuit_breaker(circuit_breaker, resilient_orchestrator)
        await self._verify_circuit_breaker_open(circuit_breaker, resilient_orchestrator)
    
    async def _trigger_circuit_breaker(self, circuit_breaker, orchestrator):
        """Trigger circuit breaker by causing failures."""
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(NetraException):
                await circuit_breaker.execute(
                    orchestrator, "user1", f"request_{i}", f"run_{i}"
                )
    
    async def _verify_circuit_breaker_open(self, circuit_breaker, orchestrator):
        """Verify circuit breaker is open and blocks requests."""
        assert_circuit_breaker_state(
            circuit_breaker.circuit_open, 
            circuit_breaker.failure_count,
            True, 
            circuit_breaker.failure_threshold
        )
        
        with pytest.raises(NetraException) as exc_info:
            await circuit_breaker.execute(orchestrator, "user1", "circuit_test", "run_circuit")
        
        assert "Circuit breaker open" in str(exc_info.value)


class CircuitBreaker:
    """Circuit breaker implementation for testing."""
    
    def __init__(self, failure_threshold=3):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.circuit_open = False
    
    async def execute(self, orchestrator, user_id, request, run_id):
        """Execute with circuit breaker logic."""
        if self.circuit_open:
            raise NetraException("Circuit breaker open")
        
        return await self._execute_with_failure_tracking(orchestrator, user_id, request, run_id)
    
    async def _execute_with_failure_tracking(self, orchestrator, user_id, request, run_id):
        """Execute and track failures."""
        try:
            return await orchestrator.execute_agent_task(user_id, request, run_id)
        except NetraException:
            self._handle_failure()
            raise
    
    def _handle_failure(self):
        """Handle failure and update circuit breaker state."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True