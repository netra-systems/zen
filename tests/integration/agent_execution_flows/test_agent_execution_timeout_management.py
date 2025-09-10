"""
Test Agent Execution Timeout Management Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent agent execution blocking that prevents users from receiving AI responses
- Value Impact: Ensures reliable response times and prevents system deadlock
- Strategic Impact: Critical for user experience - timeouts enable system recovery and consistent performance

Tests the timeout management system including circuit breakers, execution limits,
and graceful handling of long-running agent operations.
"""

import asyncio
import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.execution_timeout_manager import (
    get_timeout_manager,
    TimeoutConfig,
    CircuitBreakerOpenError,
    ExecutionTimeoutManager
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentExecutionTimeoutManagement(BaseIntegrationTest):
    """Integration tests for agent execution timeout management."""

    @pytest.mark.integration
    @pytest.mark.timeout_management
    async def test_agent_execution_timeout_enforcement(self, real_services_fixture):
        """Test enforcement of execution timeouts for agent operations."""
        # Arrange
        timeout_config = TimeoutConfig(
            default_timeout_seconds=2,  # Short timeout for testing
            max_timeout_seconds=5,
            circuit_breaker_failure_threshold=3
        )
        
        timeout_manager = ExecutionTimeoutManager(config=timeout_config)
        
        user_context = UserExecutionContext(
            user_id="test_user_300",
            thread_id="thread_600",
            session_id="session_900",
            workspace_id="workspace_200"
        )
        
        # Mock a slow LLM that exceeds timeout
        slow_llm = AsyncMock()
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(3)  # Exceeds 2 second timeout
            return {"status": "success", "data": "late_response"}
        
        slow_llm.generate_response = slow_response
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=slow_llm,
            websocket_emitter=MagicMock(),
            timeout_manager=timeout_manager
        )
        
        # Act & Assert - Should timeout
        start_time = time.time()
        
        with pytest.raises(asyncio.TimeoutError):
            await execution_engine.execute_agent(
                agent_type="slow_agent",
                message="This will timeout",
                timeout_seconds=2
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should timeout around 2 seconds, not wait for full 3 second sleep
        assert execution_time < 2.5
        assert execution_time >= 1.8  # Allow some variance

    @pytest.mark.integration
    @pytest.mark.timeout_management
    async def test_circuit_breaker_activation_and_recovery(self, real_services_fixture):
        """Test circuit breaker activation after repeated timeouts and recovery."""
        # Arrange
        timeout_config = TimeoutConfig(
            default_timeout_seconds=1,
            max_timeout_seconds=2,
            circuit_breaker_failure_threshold=3,
            circuit_breaker_recovery_timeout=2
        )
        
        timeout_manager = ExecutionTimeoutManager(config=timeout_config)
        
        user_context = UserExecutionContext(
            user_id="test_user_301",
            thread_id="thread_601", 
            session_id="session_901",
            workspace_id="workspace_201"
        )
        
        # Mock consistently slow LLM
        slow_llm = AsyncMock()
        async def always_slow(*args, **kwargs):
            await asyncio.sleep(2)  # Always exceeds 1 second timeout
            return {"status": "success", "data": "slow_response"}
        
        slow_llm.generate_response = always_slow
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=slow_llm,
            websocket_emitter=MagicMock(),
            timeout_manager=timeout_manager
        )
        
        # Act - Trigger failures to open circuit breaker
        failure_count = 0
        for i in range(4):  # Exceed failure threshold
            try:
                await execution_engine.execute_agent(
                    agent_type="failing_agent",
                    message=f"Attempt {i}",
                    timeout_seconds=1
                )
            except (asyncio.TimeoutError, CircuitBreakerOpenError):
                failure_count += 1
        
        # Circuit breaker should now be open
        with pytest.raises(CircuitBreakerOpenError):
            await execution_engine.execute_agent(
                agent_type="failing_agent", 
                message="This should fail fast",
                timeout_seconds=1
            )
        
        # Wait for recovery period
        await asyncio.sleep(2.5)
        
        # Mock now responds quickly for recovery test
        fast_llm = AsyncMock()
        fast_llm.generate_response = AsyncMock(return_value={"status": "success", "data": "fast_response"})
        
        execution_engine.llm_client = fast_llm
        
        # Should now allow execution again
        result = await execution_engine.execute_agent(
            agent_type="recovered_agent",
            message="Recovery test",
            timeout_seconds=1
        )
        
        assert result is not None
        assert failure_count >= 3  # Should have failed at least 3 times before circuit breaker opened

    @pytest.mark.integration
    @pytest.mark.timeout_management
    async def test_adaptive_timeout_adjustment(self, real_services_fixture):
        """Test adaptive timeout adjustment based on agent execution history."""
        # Arrange
        timeout_config = TimeoutConfig(
            default_timeout_seconds=3,
            max_timeout_seconds=10,
            adaptive_timeout_enabled=True,
            timeout_adjustment_factor=1.5
        )
        
        timeout_manager = ExecutionTimeoutManager(config=timeout_config)
        
        user_context = UserExecutionContext(
            user_id="test_user_302",
            thread_id="thread_602",
            session_id="session_902", 
            workspace_id="workspace_202"
        )
        
        # Mock LLM with variable response times
        variable_llm = AsyncMock()
        response_times = [0.5, 1.0, 2.0, 4.0]  # Increasingly slow
        call_count = 0
        
        async def variable_response(*args, **kwargs):
            nonlocal call_count
            sleep_time = response_times[call_count % len(response_times)]
            await asyncio.sleep(sleep_time)
            call_count += 1
            return {"status": "success", "data": f"response_after_{sleep_time}s"}
        
        variable_llm.generate_response = variable_response
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=variable_llm,
            websocket_emitter=MagicMock(),
            timeout_manager=timeout_manager
        )
        
        # Act - Execute multiple times to build history
        results = []
        for i in range(4):
            try:
                result = await execution_engine.execute_agent(
                    agent_type="adaptive_agent",
                    message=f"Request {i}",
                    use_adaptive_timeout=True
                )
                results.append(result)
            except asyncio.TimeoutError:
                results.append(None)  # Timeout occurred
        
        # Assert - Should adapt to longer timeouts for slower agent
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) >= 3  # Most should succeed due to adaptive timeout
        
        # Verify timeout was adjusted
        final_timeout = await timeout_manager.get_adaptive_timeout("adaptive_agent")
        assert final_timeout > timeout_config.default_timeout_seconds

    @pytest.mark.integration
    @pytest.mark.timeout_management
    async def test_timeout_resource_cleanup(self, real_services_fixture):
        """Test proper resource cleanup when execution times out."""
        # Arrange
        timeout_config = TimeoutConfig(
            default_timeout_seconds=1,
            cleanup_timeout_seconds=0.5
        )
        
        timeout_manager = ExecutionTimeoutManager(config=timeout_config)
        
        user_context = UserExecutionContext(
            user_id="test_user_303",
            thread_id="thread_603",
            session_id="session_903",
            workspace_id="workspace_203"
        )
        
        # Mock LLM that holds resources during execution
        resource_holding_llm = AsyncMock()
        resources_allocated = []
        
        async def resource_intensive_response(*args, **kwargs):
            # Simulate resource allocation
            resource_id = f"resource_{len(resources_allocated)}"
            resources_allocated.append(resource_id)
            try:
                await asyncio.sleep(2)  # Will timeout
                return {"status": "success", "data": "response"}
            except asyncio.CancelledError:
                # Simulate cleanup on cancellation
                if resource_id in resources_allocated:
                    resources_allocated.remove(resource_id)
                raise
        
        resource_holding_llm.generate_response = resource_intensive_response
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=resource_holding_llm,
            websocket_emitter=MagicMock(),
            timeout_manager=timeout_manager
        )
        
        # Act - Execute and let it timeout
        initial_resource_count = len(resources_allocated)
        
        with pytest.raises(asyncio.TimeoutError):
            await execution_engine.execute_agent(
                agent_type="resource_intensive_agent",
                message="This will timeout and cleanup",
                timeout_seconds=1
            )
        
        # Give time for cleanup
        await asyncio.sleep(0.6)
        
        # Assert - Resources should be cleaned up
        final_resource_count = len(resources_allocated)
        assert final_resource_count <= initial_resource_count  # Resources cleaned up

    @pytest.mark.integration
    @pytest.mark.timeout_management
    async def test_graceful_timeout_with_partial_results(self, real_services_fixture):
        """Test graceful timeout handling with partial result preservation."""
        # Arrange
        timeout_config = TimeoutConfig(
            default_timeout_seconds=2,
            allow_partial_results=True
        )
        
        timeout_manager = ExecutionTimeoutManager(config=timeout_config)
        
        user_context = UserExecutionContext(
            user_id="test_user_304",
            thread_id="thread_604",
            session_id="session_904",
            workspace_id="workspace_204"
        )
        
        # Mock LLM that produces partial results before timing out
        partial_result_llm = AsyncMock()
        partial_results = []
        
        async def partial_response(*args, **kwargs):
            # Produce some results quickly
            partial_results.append({"step": 1, "analysis": "initial_findings"})
            await asyncio.sleep(0.5)
            
            partial_results.append({"step": 2, "analysis": "intermediate_findings"})
            await asyncio.sleep(0.5)
            
            # This will cause timeout before completion
            await asyncio.sleep(2)
            partial_results.append({"step": 3, "analysis": "final_findings"})  # Won't reach this
            
            return {"status": "success", "results": partial_results}
        
        partial_result_llm.generate_response = partial_response
        
        execution_engine = UserExecutionEngine(
            user_context=user_context,
            llm_client=partial_result_llm,
            websocket_emitter=MagicMock(),
            timeout_manager=timeout_manager
        )
        
        # Act - Execute with partial result handling
        try:
            result = await execution_engine.execute_agent_with_partial_results(
                agent_type="partial_result_agent",
                message="Generate analysis with partial results",
                timeout_seconds=2,
                partial_result_callback=lambda pr: partial_results.extend(pr) if isinstance(pr, list) else partial_results.append(pr)
            )
        except asyncio.TimeoutError as e:
            # Should have captured partial results
            result = getattr(e, 'partial_results', None)
        
        # Assert - Should have partial results even though execution timed out
        assert len(partial_results) >= 2  # Should have captured at least first 2 steps
        assert partial_results[0]["step"] == 1
        assert partial_results[1]["step"] == 2
        assert len(partial_results) < 3  # Should not have final step due to timeout