"""Supervisor Agent Error Handling Tests
Priority: P0 - CRITICAL
Coverage: Error handling, recovery mechanisms, and resilience patterns
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
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from netra_backend.app.schemas import SubAgentLifecycle

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    # Add project root to path
    AgentExecutionContext,
    AgentExecutionResult,
)

# Add project root to path
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from .supervisor_extensions import (
    install_supervisor_extensions,
)
from .supervisor_test_helpers import (
    create_agent_state,
    create_execution_context,
    create_supervisor_agent,
    create_supervisor_mocks,
    setup_circuit_breaker,
    setup_failing_agent_mock,
    setup_retry_agent_mock,
)

# Install extension methods for testing
install_supervisor_extensions()


class TestSupervisorErrorHandling:
    """Test supervisor handles agent initialization errors gracefully"""
    async def test_supervisor_error_handling(self):
        """Test supervisor handles agent initialization errors gracefully"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Mock an agent failure
        state = create_agent_state("Test error handling")
        context = create_execution_context("error-test", 
                                         started_at=datetime.now(timezone.utc))
        
        # Make triage agent fail
        setup_failing_agent_mock(supervisor, "triage", "Agent failed")
        
        # Test direct routing that should fail
        result = await supervisor._route_to_agent(state, context, "triage")
        
        # Verify error was handled
        assert not result.success
        assert "Agent failed" in str(result.error)
    async def test_supervisor_state_management(self):
        """Test supervisor properly manages agent states"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Test initial state
        assert supervisor.state == SubAgentLifecycle.PENDING
        
        # Test state transitions (following valid lifecycle)
        supervisor.set_state(SubAgentLifecycle.RUNNING)
        assert supervisor.get_state() == SubAgentLifecycle.RUNNING
        
        supervisor.set_state(SubAgentLifecycle.COMPLETED)
        assert supervisor.get_state() == SubAgentLifecycle.COMPLETED
        
        # Note: Cannot transition back to PENDING from COMPLETED
        # This is valid supervisor behavior


class TestSupervisorConcurrentRequests:
    """Test supervisor handles multiple concurrent requests"""
    async def test_supervisor_concurrent_requests(self):
        """Test supervisor handles multiple concurrent requests"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Mock triage agent for concurrent requests
        async def mock_execute(state, run_id, stream_updates=True):
            await asyncio.sleep(0.01)  # Simulate processing time
            state.triage_result = {"message_type": "query", "confidence": 0.9}
            return state
        
        supervisor.agents["triage"].execute = mock_execute
        
        # Create multiple concurrent requests
        requests = [f"Message {i}" for i in range(3)]  # Reduced to 3 for stability
        
        tasks = []
        for i, req in enumerate(requests):
            state = create_agent_state(req)
            
            async def run_single_task(message_index=i, request_text=req):
                try:
                    # Use a simpler approach - just test the agent execution
                    result = await supervisor._route_to_agent(
                        create_agent_state(request_text), 
                        create_execution_context(f"run_{message_index}"), 
                        "triage"
                    )
                    return result
                except Exception as e:
                    return AgentExecutionResult(success=False, error=str(e))
            
            tasks.append(run_single_task())
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests were processed
        assert len(results) == 3
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} failed with: {result}")
            assert result.success is True


class TestRetryMechanisms:
    """Test retry and circuit breaker patterns"""
    async def test_retry_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup agent that fails multiple times then succeeds
        setup_retry_agent_mock(supervisor, "triage",
                             ["Retry 1", "Retry 2"],
                             {'user_request': "Test", 'triage_result': {"success": True}})
        
        state = create_agent_state("Test")
        context = create_execution_context("retry-test", max_retries=3)
        
        start_time = asyncio.get_event_loop().time()
        result = await supervisor._route_to_agent_with_retry(state, context, "triage")
        end_time = asyncio.get_event_loop().time()
        
        assert result.success
        assert result.state.triage_result.category == "success"
        # Should have taken some time due to backoff
        assert end_time - start_time > 0.1
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker can recover after cooldown"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        setup_circuit_breaker(supervisor, threshold=2)
        
        # First: trigger circuit breaker
        setup_failing_agent_mock(supervisor, "optimization", "Service down")
        state = create_agent_state("Test")
        
        # Fail twice to open circuit
        for i in range(2):
            context = create_execution_context(f"fail-{i}")
            result = await supervisor._route_to_agent_with_circuit_breaker(
                state, context, "optimization"
            )
            assert not result.success
        
        # Third call should be blocked by circuit breaker
        context = create_execution_context("blocked")
        result = await supervisor._route_to_agent_with_circuit_breaker(
            state, context, "optimization"
        )
        assert not result.success
        assert "Circuit breaker open" in result.error
        
        # Wait for cooldown and setup working agent
        await asyncio.sleep(0.15)
        agent = supervisor.agents["optimization"]
        agent.execute = AsyncMock()
        agent.execute.return_value = create_agent_state("Test", 
                                                       optimizations_result={"success": True})
        
        # Should work again after cooldown
        context = create_execution_context("recovery")
        result = await supervisor._route_to_agent_with_circuit_breaker(
            state, context, "optimization"
        )
        assert result.success


class TestErrorPropagation:
    """Test error propagation and isolation"""
    async def test_error_isolation_between_agents(self):
        """Test that errors in one agent don't affect others"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup one failing agent and one working agent
        setup_failing_agent_mock(supervisor, "triage", "Triage service down")
        
        data_agent = supervisor.agents["data"]
        data_agent.execute = AsyncMock()
        data_agent.execute.return_value = create_agent_state("Test", 
                                                           data_result={"status": "healthy"})
        
        state = create_agent_state("Test")
        context = create_execution_context("isolation-test")
        
        # Triage should fail
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert not triage_result.success
        
        # Data agent should still work
        data_result = await supervisor._route_to_agent(state, context, "data")
        assert data_result.success
        assert data_result.state.data_result["status"] == "healthy"
    async def test_partial_pipeline_failure_recovery(self):
        """Test recovery when part of pipeline fails"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup pipeline: triage (works) -> data (fails) -> optimization (works)
        triage_agent = supervisor.agents["triage"]
        triage_agent.execute = AsyncMock()
        triage_agent.execute.return_value = create_agent_state("Test",
                                                             triage_result={"requires_data": True})
        
        setup_failing_agent_mock(supervisor, "data", "Data service unavailable")
        
        opt_agent = supervisor.agents["optimization"]
        opt_agent.execute = AsyncMock()
        opt_agent.execute.return_value = create_agent_state("Test",
                                                          optimizations_result={"fallback": True})
        
        state = create_agent_state("Test")
        context = create_execution_context("partial-failure")
        
        # Execute pipeline with error handling
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert triage_result.success
        
        data_result = await supervisor._route_to_agent(state, context, "data")
        assert not data_result.success
        
        # Optimization should still work despite data failure
        opt_result = await supervisor._route_to_agent(state, context, "optimization")
        assert opt_result.success
        assert opt_result.state.optimizations_result["fallback"]


class TestErrorRecoveryStrategies:
    """Test different error recovery strategies"""
    async def test_graceful_degradation(self):
        """Test graceful degradation when services are unavailable"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # All agents fail except basic triage
        setup_failing_agent_mock(supervisor, "data", "Data unavailable")
        setup_failing_agent_mock(supervisor, "optimization", "Optimization unavailable")
        
        # Triage provides minimal response
        triage_agent = supervisor.agents["triage"]
        triage_agent.execute = AsyncMock()
        triage_agent.execute.return_value = create_agent_state("Test",
                                                             triage_result={
                                                                 "message_type": "query",
                                                                 "degraded_mode": True,
                                                                 "available_features": ["basic_response"]
                                                             })
        
        state = create_agent_state("Test")
        context = create_execution_context("degradation-test")
        
        # Should still provide some response via triage
        result = await supervisor._route_to_agent(state, context, "triage")
        assert result.success
        assert result.state.triage_result["degraded_mode"]
        assert "basic_response" in result.state.triage_result["available_features"]
    async def test_fallback_agent_selection(self):
        """Test fallback to alternative agents when primary fails"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Primary data agent fails
        setup_failing_agent_mock(supervisor, "data", "Primary data service down")
        
        # Mock a fallback data processing capability in optimization agent
        opt_agent = supervisor.agents["optimization"]
        opt_agent.execute = AsyncMock()
        opt_agent.execute.return_value = create_agent_state("Test",
                                                          optimizations_result={
                                                              "fallback_data_processing": True,
                                                              "limited_analysis": {"basic_metrics": True}
                                                          })
        
        state = create_agent_state("Test")
        context = create_execution_context("fallback-test")
        
        # Try primary data agent (should fail)
        data_result = await supervisor._route_to_agent(state, context, "data")
        assert not data_result.success
        
        # Use optimization agent as fallback for basic data processing
        fallback_result = await supervisor._route_to_agent(state, context, "optimization")
        assert fallback_result.success
        assert fallback_result.state.optimizations_result["fallback_data_processing"]