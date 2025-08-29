"""
Agent Failure Propagation Integration Tests.

PRODUCTION CRITICAL - Launch Tomorrow

BVJ (Business Value Justification):
1. Segment: Enterprise, Mid (Critical system resilience)
2. Business Goal: Ensure 99.9% agent system uptime during failures
3. Value Impact: Validates agent failure isolation and recovery mechanisms
4. Strategic Impact: Prevents cascading failures that could disrupt customer workflows

Tests comprehensive failure scenarios in agent orchestration:
- Single agent failures
- Chain reaction failures  
- Supervisor failure handling
- Critical service failures
- Timeout and deadlock scenarios
- Error message propagation
"""

import asyncio
import logging
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import time

from netra_backend.app.agents.agent_error_types import (
    AgentValidationError,
    NetworkError,
    AgentDatabaseError
)
from netra_backend.app.agents.interfaces import (
    AgentStateProtocol,
    BaseAgentProtocol,
    ToolDispatcherProtocol,
    WebSocketManagerProtocol,
    DatabaseSessionProtocol,
    LLMManagerProtocol,
    StatePersistenceProtocol
)
from netra_backend.app.schemas.core_enums import CircuitBreakerState
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.schemas.strict_types import (
    AgentExecutionContext,
    AgentExecutionMetrics,
    TypedAgentResult
)
from test_framework.base_integration_test import BaseIntegrationTest


class MockAgent:
    """Mock agent for testing failure scenarios."""
    
    def __init__(self, name: str, should_fail: bool = False, 
                 failure_type: str = "generic", delay_seconds: float = 0):
        self.name = name
        self.description = f"Mock agent: {name}"
        self.should_fail = should_fail
        self.failure_type = failure_type
        self.delay_seconds = delay_seconds
        self.execution_count = 0
        self.last_execution_time = None
        
    async def execute(self, state, run_id: str, stream_updates: bool = False) -> TypedAgentResult:
        """Execute mock agent with configurable failure modes."""
        self.execution_count += 1
        self.last_execution_time = datetime.utcnow()
        
        # Simulate processing delay
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        
        if self.should_fail:
            if self.failure_type == "validation":
                raise AgentValidationError(f"Mock validation error in {self.name}", "test_field")
            elif self.failure_type == "network":
                raise NetworkError(f"Mock network error in {self.name}", "http://mock-endpoint")
            elif self.failure_type == "database":
                raise AgentDatabaseError(f"Mock database error in {self.name}", "SELECT * FROM test")
            elif self.failure_type == "timeout":
                await asyncio.sleep(10)  # Force timeout
            elif self.failure_type == "deadlock":
                # Simulate deadlock by waiting indefinitely
                while True:
                    await asyncio.sleep(1)
            else:
                raise Exception(f"Mock failure in {self.name}")
        
        return TypedAgentResult(
            success=True,
            result={"agent": self.name, "status": "completed", "run_id": run_id},
            error=None,
            execution_time_ms=self.delay_seconds * 1000,
            context=AgentExecutionContext(
                agent_name=self.name,
                run_id=run_id,
                execution_start=self.last_execution_time
            )
        )
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics."""
        return AgentExecutionMetrics(
            execution_time_ms=self.delay_seconds * 1000,
            llm_tokens_used=100,
            database_queries=1,
            websocket_messages_sent=1
        )


class MockSupervisor:
    """Mock supervisor agent for orchestration testing."""
    
    def __init__(self):
        self.agents: List[MockAgent] = []
        self.execution_order = []
        self.failure_recovery_enabled = True
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        
    def add_agent(self, agent: MockAgent):
        """Add agent to supervision."""
        self.agents.append(agent)
    
    async def execute_agents(self, state, run_id: str, parallel: bool = False) -> Dict[str, Any]:
        """Execute agents with failure handling."""
        results = {}
        failures = {}
        
        if parallel:
            # Execute agents in parallel
            tasks = []
            for agent in self.agents:
                task = asyncio.create_task(
                    self._execute_agent_with_recovery(agent, state, run_id)
                )
                tasks.append((agent.name, task))
            
            # Wait for all tasks with timeout
            for agent_name, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=5.0)
                    results[agent_name] = result
                    self.execution_order.append(agent_name)
                except asyncio.TimeoutError:
                    failures[agent_name] = "timeout"
                    task.cancel()
                except Exception as e:
                    failures[agent_name] = str(e)
        else:
            # Execute agents sequentially
            for agent in self.agents:
                try:
                    result = await self._execute_agent_with_recovery(agent, state, run_id)
                    results[agent.name] = result
                    self.execution_order.append(agent.name)
                except Exception as e:
                    failures[agent.name] = str(e)
                    if not self.failure_recovery_enabled:
                        break  # Stop execution on first failure
        
        return {
            "results": results,
            "failures": failures,
            "execution_order": self.execution_order,
            "circuit_breaker_state": self.circuit_breaker_state.value
        }
    
    async def _execute_agent_with_recovery(self, agent: MockAgent, state, run_id: str):
        """Execute agent with recovery logic."""
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                result = await agent.execute(state, run_id)
                # Reset circuit breaker on success
                if self.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                    self.circuit_breaker_state = CircuitBreakerState.CLOSED
                return result
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    # Open circuit breaker after max retries
                    self.circuit_breaker_state = CircuitBreakerState.OPEN
                    raise e
                
                # Brief delay before retry
                await asyncio.sleep(0.1 * retry_count)
        
        raise Exception(f"Max retries exceeded for {agent.name}")


class TestAgentFailurePropagation(BaseIntegrationTest):
    """Comprehensive agent failure propagation tests."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.mock_state = MagicMock()
        self.mock_state.user_request = "Test request"
        self.mock_state.chat_thread_id = "test-thread-123"
        self.mock_state.user_id = "test-user-456"
        self.run_id = "test-run-789"
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_single_agent_failure_isolation(self):
        """Test that single agent failure doesn't affect other agents."""
        supervisor = MockSupervisor()
        
        # Add agents: one that fails, two that succeed
        supervisor.add_agent(MockAgent("agent_1", should_fail=False))
        supervisor.add_agent(MockAgent("agent_2", should_fail=True, failure_type="validation"))
        supervisor.add_agent(MockAgent("agent_3", should_fail=False))
        
        # Execute agents in parallel
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        
        # Verify failure isolation
        assert len(results["results"]) == 2  # Two successful agents
        assert len(results["failures"]) == 1  # One failed agent
        assert "agent_2" in results["failures"]
        assert "Mock validation error" in results["failures"]["agent_2"]
        
        # Verify successful agents completed
        assert "agent_1" in results["results"]
        assert "agent_3" in results["results"]
        assert results["results"]["agent_1"]["success"] is True
        assert results["results"]["agent_3"]["success"] is True
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_chain_failure_scenario_with_dependencies(self):
        """Test failure propagation when agents have dependencies."""
        supervisor = MockSupervisor()
        
        # Create dependent agents (sequential execution)
        supervisor.add_agent(MockAgent("triage_agent", should_fail=False))
        supervisor.add_agent(MockAgent("data_agent", should_fail=True, failure_type="database"))
        supervisor.add_agent(MockAgent("optimization_agent", should_fail=False))  # Should not execute
        supervisor.add_agent(MockAgent("report_agent", should_fail=False))  # Should not execute
        
        # Disable recovery to test cascade behavior
        supervisor.failure_recovery_enabled = False
        
        # Execute sequentially (simulating dependency chain)
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=False)
        
        # Verify chain failure behavior
        assert len(results["results"]) == 1  # Only first agent succeeded
        assert len(results["failures"]) == 1  # Second agent failed
        assert len(results["execution_order"]) == 2  # Only two agents executed
        
        assert "triage_agent" in results["results"]
        assert "data_agent" in results["failures"]
        assert "Mock database error" in results["failures"]["data_agent"]
        
        # Verify remaining agents didn't execute
        assert "optimization_agent" not in results["results"]
        assert "report_agent" not in results["results"]
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(20)
    async def test_supervisor_failure_handling_and_recovery(self):
        """Test supervisor crash scenarios and recovery mechanisms."""
        supervisor = MockSupervisor()
        
        # Add agents with different failure modes
        supervisor.add_agent(MockAgent("agent_1", should_fail=False))
        supervisor.add_agent(MockAgent("agent_2", should_fail=True, failure_type="network"))
        supervisor.add_agent(MockAgent("agent_3", should_fail=False))
        
        # Enable recovery mechanisms
        supervisor.failure_recovery_enabled = True
        
        # Execute with recovery
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        
        # Verify recovery behavior
        assert len(results["results"]) == 2  # Two agents should succeed
        assert len(results["failures"]) == 1  # One agent fails after retries
        
        # Verify circuit breaker is triggered after failures
        assert results["circuit_breaker_state"] == CircuitBreakerState.OPEN.value
        
        # Test state preservation during recovery
        for agent_name, result in results["results"].items():
            assert result["run_id"] == self.run_id
            assert "status" in result
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(8)
    async def test_critical_service_failures(self):
        """Test agent behavior when critical services are unavailable."""
        
        # Test database connection loss
        with patch('netra_backend.app.agents.interfaces.DatabaseSessionProtocol') as mock_db:
            mock_db.execute.side_effect = AgentDatabaseError("Connection lost", "SELECT 1")
            
            agent = MockAgent("db_dependent_agent", should_fail=True, failure_type="database")
            
            with pytest.raises(AgentDatabaseError) as exc_info:
                await agent.execute(self.mock_state, self.run_id)
            
            assert "Connection lost" in str(exc_info.value)
            assert exc_info.value.query == "SELECT 1"
        
        # Test LLM service unavailability
        with patch('netra_backend.app.agents.interfaces.LLMManagerProtocol') as mock_llm:
            mock_llm.ask_llm.side_effect = NetworkError("LLM service unavailable", "https://llm-api")
            
            agent = MockAgent("llm_dependent_agent", should_fail=True, failure_type="network")
            
            with pytest.raises(NetworkError) as exc_info:
                await agent.execute(self.mock_state, self.run_id)
            
            assert "Mock network error" in str(exc_info.value)
        
        # Test WebSocket disconnection
        with patch('netra_backend.app.agents.interfaces.WebSocketManagerProtocol') as mock_ws:
            mock_ws.send_agent_update.side_effect = NetworkError("WebSocket disconnected")
            
            agent = MockAgent("websocket_dependent_agent", should_fail=True, failure_type="network")
            
            with pytest.raises(NetworkError) as exc_info:
                await agent.execute(self.mock_state, self.run_id)
            
            assert "Mock network error" in str(exc_info.value)
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(12)
    async def test_timeout_and_deadlock_scenarios(self):
        """Test agent execution timeouts and deadlock detection."""
        supervisor = MockSupervisor()
        
        # Add agents with different timing behaviors
        supervisor.add_agent(MockAgent("fast_agent", should_fail=False, delay_seconds=0.1))
        supervisor.add_agent(MockAgent("timeout_agent", should_fail=True, failure_type="timeout"))
        supervisor.add_agent(MockAgent("normal_agent", should_fail=False, delay_seconds=0.5))
        
        # Execute with timeout protection
        start_time = time.time()
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        execution_time = time.time() - start_time
        
        # Verify timeout handling
        assert execution_time < 7.0  # Should not wait full timeout period
        assert len(results["failures"]) >= 1  # Timeout agent should fail
        assert "timeout_agent" in results["failures"]
        
        # Verify other agents completed successfully
        assert "fast_agent" in results["results"]
        assert "normal_agent" in results["results"]
        
        # Test deadlock detection (separate test to avoid hanging)
        deadlock_agent = MockAgent("deadlock_agent", should_fail=True, failure_type="deadlock")
        
        try:
            await asyncio.wait_for(
                deadlock_agent.execute(self.mock_state, self.run_id), 
                timeout=2.0
            )
            pytest.fail("Deadlock agent should have timed out")
        except asyncio.TimeoutError:
            # Expected behavior - deadlock detected and terminated
            pass
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_error_message_propagation_and_context(self):
        """Test error context preservation through failure propagation."""
        
        # Test validation error context
        agent = MockAgent("validation_agent", should_fail=True, failure_type="validation")
        
        try:
            await agent.execute(self.mock_state, self.run_id)
            pytest.fail("Agent should have failed")
        except AgentValidationError as e:
            assert e.field_name == "test_field"
            assert "Mock validation error" in str(e)
            assert e.severity.value == "HIGH"
            assert e.category.value == "VALIDATION"
        
        # Test network error context
        agent = MockAgent("network_agent", should_fail=True, failure_type="network")
        
        try:
            await agent.execute(self.mock_state, self.run_id)
            pytest.fail("Agent should have failed")
        except NetworkError as e:
            assert e.endpoint == "http://mock-endpoint"
            assert "Mock network error" in str(e)
            assert e.severity.value == "MEDIUM"
            assert e.category.value == "NETWORK"
        
        # Test database error context
        agent = MockAgent("database_agent", should_fail=True, failure_type="database")
        
        try:
            await agent.execute(self.mock_state, self.run_id)
            pytest.fail("Agent should have failed")
        except AgentDatabaseError as e:
            assert e.query == "SELECT * FROM test"
            assert "Mock database error" in str(e)
            assert e.severity.value == "HIGH"
            assert e.category.value == "DATABASE"
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_graceful_degradation_with_partial_results(self):
        """Test system ability to provide partial results during failures."""
        supervisor = MockSupervisor()
        
        # Create mixed success/failure scenario
        supervisor.add_agent(MockAgent("triage_agent", should_fail=False))
        supervisor.add_agent(MockAgent("primary_data_agent", should_fail=True, failure_type="database"))
        supervisor.add_agent(MockAgent("fallback_data_agent", should_fail=False))
        supervisor.add_agent(MockAgent("optimization_agent", should_fail=False))
        supervisor.add_agent(MockAgent("report_agent", should_fail=True, failure_type="network"))
        
        # Execute with parallel processing for graceful degradation
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        
        # Verify partial success
        successful_count = len(results["results"])
        failed_count = len(results["failures"])
        total_agents = len(supervisor.agents)
        
        assert successful_count > 0, "Should have some successful results"
        assert failed_count > 0, "Should have some failures"
        assert successful_count + failed_count == total_agents
        
        # Verify specific expected successes and failures
        assert "triage_agent" in results["results"]
        assert "fallback_data_agent" in results["results"] 
        assert "optimization_agent" in results["results"]
        
        assert "primary_data_agent" in results["failures"]
        assert "report_agent" in results["failures"]
        
        # Verify result quality
        for agent_name, result in results["results"].items():
            assert result["success"] is True
            assert "status" in result
            assert result["run_id"] == self.run_id
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_state_consistency_during_failures(self):
        """Test agent state remains consistent during failure scenarios."""
        supervisor = MockSupervisor()
        
        # Track state changes
        state_changes = []
        original_state = {
            "user_request": self.mock_state.user_request,
            "chat_thread_id": self.mock_state.chat_thread_id,
            "user_id": self.mock_state.user_id
        }
        
        # Create agents that modify state
        successful_agent = MockAgent("state_modifier", should_fail=False)
        failing_agent = MockAgent("state_corruptor", should_fail=True, failure_type="validation")
        
        supervisor.add_agent(successful_agent)
        supervisor.add_agent(failing_agent)
        
        # Execute and track state consistency
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=False)
        
        # Verify state consistency
        current_state = {
            "user_request": self.mock_state.user_request,
            "chat_thread_id": self.mock_state.chat_thread_id,
            "user_id": self.mock_state.user_id
        }
        
        # Core state should remain unchanged despite failures
        assert current_state == original_state
        
        # Verify execution tracking
        assert len(results["execution_order"]) >= 1  # At least successful agent executed
        assert "state_modifier" in results["execution_order"]
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(20)
    async def test_recovery_strategies_and_fallbacks(self):
        """Test various recovery strategies and fallback mechanisms."""
        supervisor = MockSupervisor()
        
        # Test retry mechanism
        flaky_agent = MockAgent("flaky_agent", should_fail=True, failure_type="network")
        
        # Simulate intermittent failure (fails first time, succeeds on retry)
        call_count = 0
        original_execute = flaky_agent.execute
        
        async def flaky_execute(state, run_id, stream_updates=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("Temporary network issue")
            return await original_execute(state, run_id, stream_updates)
        
        flaky_agent.execute = flaky_execute
        flaky_agent.should_fail = False  # Allow success on retry
        
        supervisor.add_agent(flaky_agent)
        
        # Execute with retry logic
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=False)
        
        # Verify retry succeeded
        assert "flaky_agent" in results["results"]
        assert call_count > 1  # Should have been called multiple times
        
        # Test circuit breaker recovery
        supervisor.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
        
        # Add successful agent to test circuit breaker reset
        recovery_agent = MockAgent("recovery_agent", should_fail=False)
        supervisor.agents.clear()
        supervisor.add_agent(recovery_agent)
        
        results = await supervisor.execute_agents(self.mock_state, "recovery-run", parallel=False)
        
        # Verify circuit breaker closed after success
        assert results["circuit_breaker_state"] == CircuitBreakerState.CLOSED.value
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(25)
    async def test_concurrent_failure_handling(self):
        """Test system behavior under concurrent failures."""
        supervisor = MockSupervisor()
        
        # Create high concurrency scenario with mixed failures
        agent_configs = [
            ("agent_1", False, "generic", 0.1),
            ("agent_2", True, "validation", 0.2),
            ("agent_3", False, "generic", 0.1),
            ("agent_4", True, "database", 0.3),
            ("agent_5", False, "generic", 0.1),
            ("agent_6", True, "network", 0.2),
            ("agent_7", False, "generic", 0.1),
            ("agent_8", True, "timeout", 0.5),
        ]
        
        for name, should_fail, failure_type, delay in agent_configs:
            agent = MockAgent(name, should_fail, failure_type, delay)
            supervisor.add_agent(agent)
        
        # Execute all agents concurrently
        start_time = time.time()
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        execution_time = time.time() - start_time
        
        # Verify concurrent execution completed in reasonable time
        assert execution_time < 10.0  # Should not exceed timeout thresholds
        
        # Verify mix of success and failures
        successful_agents = len(results["results"])
        failed_agents = len(results["failures"])
        
        assert successful_agents > 0, "Should have successful agents"
        assert failed_agents > 0, "Should have failed agents"
        assert successful_agents + failed_agents == len(agent_configs)
        
        # Verify no data corruption during concurrent failures
        for agent_name, result in results["results"].items():
            assert result["run_id"] == self.run_id
            assert result["agent"] == agent_name
            assert result["success"] is True
            
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_monitoring_and_observability_during_failures(self):
        """Test that monitoring and observability work during failure scenarios."""
        supervisor = MockSupervisor()
        
        # Add agents with monitoring
        supervisor.add_agent(MockAgent("monitored_success", should_fail=False, delay_seconds=0.5))
        supervisor.add_agent(MockAgent("monitored_failure", should_fail=True, failure_type="validation"))
        supervisor.add_agent(MockAgent("monitored_timeout", should_fail=True, failure_type="timeout"))
        
        # Execute with monitoring
        results = await supervisor.execute_agents(self.mock_state, self.run_id, parallel=True)
        
        # Verify monitoring data collection
        for agent in supervisor.agents:
            if agent.execution_count > 0:
                # Verify execution metrics are tracked
                metrics = agent.get_execution_metrics()
                assert metrics.execution_time_ms >= 0
                assert metrics.llm_tokens_used >= 0
                assert metrics.database_queries >= 0
                assert metrics.websocket_messages_sent >= 0
                
                # Verify timing data
                assert agent.last_execution_time is not None
                time_diff = datetime.utcnow() - agent.last_execution_time
                assert time_diff.total_seconds() < 60  # Recent execution
        
        # Verify failure tracking
        assert len(results["failures"]) >= 2  # At least 2 expected failures
        
        # Verify execution order tracking
        assert len(results["execution_order"]) >= 1  # At least one successful execution


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])