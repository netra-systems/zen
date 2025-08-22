"""
Agent service error recovery and resilience tests.

MODULE PURPOSE:
Tests agent error recovery mechanisms, timeout handling, circuit breaker patterns,
and resource cleanup during failure scenarios. Ensures system stability under
adverse conditions.

TEST CATEGORIES:
- Agent failure recovery with retry mechanisms
- Timeout handling and graceful degradation
- Resource cleanup on errors
- Circuit breaker pattern implementation
- Resilient orchestrator behavior

PERFORMANCE REQUIREMENTS:
- Error recovery tests: < 500ms each
- Timeout tests: Must respect configured timeouts
- Circuit breaker tests: < 1s for full cycle
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from unittest.mock import MagicMock

import pytest

# Add project root to path
from netra_backend.app.core.exceptions_base import NetraException
from .test_agent_service_fixtures import resilient_orchestrator
from .test_agent_service_mock_classes import AgentState

# Add project root to path


class TestAgentErrorRecovery:
    """Test agent error recovery and resilience mechanisms."""
    async def test_agent_failure_recovery(self, resilient_orchestrator):
        """Test recovery from agent failures with retry mechanism."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        agent.failure_message = "Temporary failure"
        
        result = await self._execute_with_retry_mechanism(resilient_orchestrator)
        
        assert result['status'] == 'completed'
    
    async def _execute_with_retry_mechanism(self, resilient_orchestrator):
        """Execute task with retry mechanism for recovery testing."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await resilient_orchestrator.execute_agent_task(
                    "user1", "retry request", "run_retry"
                )
            except NetraException:
                if attempt == max_retries - 1:
                    raise
                await self._handle_retry_attempt(resilient_orchestrator, attempt)
    
    async def _handle_retry_attempt(self, resilient_orchestrator, attempt):
        """Handle retry attempt with agent reset."""
        agent = resilient_orchestrator.agents["user1"]
        if attempt == 1:  # Second attempt succeeds
            agent.should_fail = False
        await asyncio.sleep(resilient_orchestrator.retry_delay)
    async def test_agent_timeout_handling(self, resilient_orchestrator):
        """Test handling of agent timeouts."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.execution_time = 1.0  # 1 second execution
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                resilient_orchestrator.execute_agent_task("user1", "slow request", "run_slow"),
                timeout=0.1  # 100ms timeout
            )
    async def test_agent_resource_cleanup_on_error(self, resilient_orchestrator):
        """Test resource cleanup when agent encounters errors."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        
        initial_active = resilient_orchestrator.active_agents
        
        with pytest.raises(NetraException):
            await resilient_orchestrator.execute_agent_task("user1", "failing request", "run_cleanup")
        
        await resilient_orchestrator.release_agent("user1")
        self._verify_resource_cleanup(resilient_orchestrator, initial_active)
    
    def _verify_resource_cleanup(self, resilient_orchestrator, initial_active):
        """Verify proper resource cleanup after error."""
        assert resilient_orchestrator.active_agents == initial_active - 1
        assert "user1" not in resilient_orchestrator.agents
    async def test_circuit_breaker_pattern(self, resilient_orchestrator):
        """Test circuit breaker pattern for failing agents."""
        circuit_breaker = self._create_circuit_breaker()
        
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        agent.should_fail = True
        
        await self._trigger_circuit_breaker_failures(circuit_breaker, resilient_orchestrator)
        self._verify_circuit_breaker_open(circuit_breaker)
        await self._verify_circuit_breaker_blocks_requests(circuit_breaker, resilient_orchestrator)
    
    def _create_circuit_breaker(self):
        """Create circuit breaker state tracker."""
        return {
            'failure_threshold': 3,
            'failure_count': 0,
            'circuit_open': False
        }
    
    async def _trigger_circuit_breaker_failures(self, circuit_breaker, resilient_orchestrator):
        """Trigger failures to open circuit breaker."""
        for i in range(circuit_breaker['failure_threshold']):
            try:
                await self._circuit_breaker_execute(circuit_breaker, resilient_orchestrator, f"request_{i}", f"run_{i}")
            except NetraException:
                pass
    
    async def _circuit_breaker_execute(self, circuit_breaker, resilient_orchestrator, request, run_id):
        """Execute with circuit breaker logic."""
        if circuit_breaker['circuit_open']:
            raise NetraException("Circuit breaker open")
        
        try:
            return await resilient_orchestrator.execute_agent_task("user1", request, run_id)
        except NetraException:
            circuit_breaker['failure_count'] += 1
            if circuit_breaker['failure_count'] >= circuit_breaker['failure_threshold']:
                circuit_breaker['circuit_open'] = True
            raise
    
    def _verify_circuit_breaker_open(self, circuit_breaker):
        """Verify circuit breaker is open."""
        assert circuit_breaker['circuit_open'] == True
        assert circuit_breaker['failure_count'] == circuit_breaker['failure_threshold']
    
    async def _verify_circuit_breaker_blocks_requests(self, circuit_breaker, resilient_orchestrator):
        """Verify circuit breaker blocks subsequent requests."""
        with pytest.raises(NetraException) as exc_info:
            await self._circuit_breaker_execute(circuit_breaker, resilient_orchestrator, "circuit_test", "run_circuit")
        
        assert "Circuit breaker open" in str(exc_info.value)


class TestAgentResiliencePatterns:
    """Test advanced resilience patterns for agent management."""
    async def test_graceful_degradation_on_partial_failure(self, resilient_orchestrator):
        """Test graceful degradation when some agents fail."""
        # Create multiple agents, make some fail
        agents = await self._create_mixed_agent_pool(resilient_orchestrator)
        
        results = await self._execute_mixed_success_failure_tasks(resilient_orchestrator)
        
        self._verify_partial_success_results(results)
    
    async def _create_mixed_agent_pool(self, resilient_orchestrator):
        """Create pool with mix of working and failing agents."""
        agents = []
        for i in range(5):
            agent = await resilient_orchestrator.get_or_create_agent(f"user_{i}")
            if i % 2 == 1:  # Make every other agent fail
                agent.should_fail = True
            agents.append(agent)
        return agents
    
    async def _execute_mixed_success_failure_tasks(self, resilient_orchestrator):
        """Execute tasks with mixed success/failure expected."""
        tasks = []
        for i in range(5):
            task = self._safe_execute_agent_task(resilient_orchestrator, f"user_{i}", f"request_{i}", f"run_{i}")
            tasks.append(task)
        return await asyncio.gather(*tasks)
    
    async def _safe_execute_agent_task(self, resilient_orchestrator, user_id, request, run_id):
        """Safely execute agent task with error handling."""
        try:
            return await resilient_orchestrator.execute_agent_task(user_id, request, run_id)
        except NetraException:
            return {'status': 'failed', 'run_id': run_id}
    
    def _verify_partial_success_results(self, results):
        """Verify partial success in mixed execution."""
        success_count = sum(1 for result in results if result['status'] == 'completed')
        failure_count = sum(1 for result in results if result['status'] == 'failed')
        
        assert success_count > 0  # Some should succeed
        assert failure_count > 0  # Some should fail
        assert success_count + failure_count == len(results)
    async def test_agent_recovery_after_transient_failure(self, resilient_orchestrator):
        """Test agent recovery after transient failures."""
        agent = await resilient_orchestrator.get_or_create_agent("user1")
        
        # Simulate transient failure
        agent.should_fail = True
        await self._attempt_and_expect_failure(resilient_orchestrator)
        
        # Recovery - agent works again
        agent.should_fail = False
        result = await resilient_orchestrator.execute_agent_task("user1", "recovery request", "run_recovery")
        
        assert result['status'] == 'completed'
    
    async def _attempt_and_expect_failure(self, resilient_orchestrator):
        """Attempt execution and expect failure."""
        try:
            await resilient_orchestrator.execute_agent_task("user1", "transient fail", "run_transient")
            assert False, "Expected NetraException"
        except NetraException:
            pass  # Expected
    async def test_concurrent_failure_isolation(self, resilient_orchestrator):
        """Test that concurrent failures don't cascade."""
        num_agents = 5
        
        # Create agents with staggered failure modes
        await self._setup_staggered_failure_agents(resilient_orchestrator, num_agents)
        
        # Execute concurrent tasks
        results = await self._execute_isolated_failure_tasks(resilient_orchestrator, num_agents)
        
        # Verify failures are isolated
        self._verify_failure_isolation(results)
    
    async def _setup_staggered_failure_agents(self, resilient_orchestrator, num_agents):
        """Setup agents with staggered failure patterns."""
        for i in range(num_agents):
            agent = await resilient_orchestrator.get_or_create_agent(f"isolation_user_{i}")
            if i < 2:  # First 2 agents fail
                agent.should_fail = True
    
    async def _execute_isolated_failure_tasks(self, resilient_orchestrator, num_agents):
        """Execute tasks to test failure isolation."""
        tasks = []
        for i in range(num_agents):
            task = self._safe_execute_agent_task(
                resilient_orchestrator, f"isolation_user_{i}", f"isolation_request_{i}", f"isolation_run_{i}"
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)
    
    def _verify_failure_isolation(self, results):
        """Verify that failures are properly isolated."""
        failed_results = [r for r in results if r['status'] == 'failed']
        success_results = [r for r in results if r['status'] == 'completed']
        
        assert len(failed_results) == 2  # Only first 2 should fail
        assert len(success_results) == 3  # Last 3 should succeed
    async def test_error_propagation_containment(self, resilient_orchestrator):
        """Test that errors don't propagate beyond their scope."""
        # Create parent and child agent relationships
        parent_agent = await resilient_orchestrator.get_or_create_agent("parent_user")
        child_agent = await resilient_orchestrator.get_or_create_agent("child_user")
        
        # Make child fail
        child_agent.should_fail = True
        
        # Execute child task (should fail)
        child_result = await self._safe_execute_agent_task(
            resilient_orchestrator, "child_user", "child request", "child_run"
        )
        
        # Execute parent task (should succeed)
        parent_result = await resilient_orchestrator.execute_agent_task(
            "parent_user", "parent request", "parent_run"
        )
        
        self._verify_error_containment(child_result, parent_result)
    
    def _verify_error_containment(self, child_result, parent_result):
        """Verify error containment between related agents."""
        assert child_result['status'] == 'failed'
        assert parent_result['status'] == 'completed'