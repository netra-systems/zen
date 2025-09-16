"""
Base Agent Reliability Infrastructure Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Production Reliability & Error Recovery
Tests circuit breaker integration, retry mechanisms, error handling patterns,
and reliability infrastructure that ensures production stability and uptime.

SSOT Compliance: Uses SSotAsyncTestCase, tests real error scenarios,
follows unified reliability patterns per CLAUDE.md standards.

Coverage Target: BaseAgent reliability infrastructure, error handling, circuit breakers
Current BaseAgent Reliability Coverage: ~3% -> Target: 18%+

Critical Infrastructure Tested:
- Circuit breaker integration and state management
- Unified retry handler (UnifiedRetryHandler SSOT)
- Error recovery and fallback patterns
- Reliability manager integration
- Execution monitoring and health status
- Failure threshold management

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, Any, Optional, List, Callable, Awaitable

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from netra_backend.app.core.resilience.domain_circuit_breakers import AgentCircuitBreaker


class ReliabilityTestAgent(BaseAgent):
    """Agent implementation for testing reliability infrastructure."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "reliability_test_agent"
        self.execution_attempts = 0
        self.failure_mode = None

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Implementation that can simulate various failure modes."""
        self.execution_attempts += 1

        # Simulate different failure modes for testing
        if self.failure_mode == "always_fail":
            raise RuntimeError(f"Simulated failure on attempt {self.execution_attempts}")
        elif self.failure_mode == "fail_once":
            if self.execution_attempts == 1:
                raise ValueError("Simulated failure on first attempt")
        elif self.failure_mode == "fail_twice":
            if self.execution_attempts <= 2:
                raise ConnectionError(f"Simulated connection failure on attempt {self.execution_attempts}")
        elif self.failure_mode == "timeout":
            await asyncio.sleep(2.0)  # Simulate timeout
            raise TimeoutError("Simulated timeout error")

        # Success case
        return {
            "status": "success",
            "result": "reliability test completed",
            "agent_type": self.agent_type,
            "execution_attempts": self.execution_attempts,
            "failure_mode": self.failure_mode
        }

    def set_failure_mode(self, mode: str):
        """Set failure mode for testing."""
        self.failure_mode = mode
        self.execution_attempts = 0


class BaseAgentReliabilityInfrastructureTests(SSotAsyncTestCase):
    """Test BaseAgent reliability infrastructure and error handling."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()

        # Create test context
        self.test_context = UserExecutionContext(
            user_id="reliability-test-user-001",
            thread_id="reliability-test-thread-001",
            run_id="reliability-test-run-001",
            agent_context={
                "user_request": "reliability infrastructure test"
            }
        ).with_db_session(AsyncMock())

    def test_agent_reliability_manager_initialization(self):
        """Test agent initializes with reliability manager by default."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)

        # Verify: Reliability manager exists
        reliability_manager = agent.reliability_manager
        assert reliability_manager is not None
        assert isinstance(reliability_manager, ReliabilityManager)

        # Verify: Agent has reliability features enabled
        assert agent._enable_reliability is True

    def test_agent_reliability_manager_disabled(self):
        """Test agent can be created without reliability features."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=False)

        # Verify: Reliability is disabled
        assert agent._enable_reliability is False

        # But reliability_manager property should still provide fallback
        reliability_manager = agent.reliability_manager
        assert reliability_manager is not None  # Fallback created as per implementation

    def test_agent_circuit_breaker_initialization(self):
        """Test agent initializes with circuit breaker."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)

        # Verify: Circuit breaker exists
        assert hasattr(agent, 'circuit_breaker')
        assert agent.circuit_breaker is not None
        assert isinstance(agent.circuit_breaker, AgentCircuitBreaker)

        # Verify: Circuit breaker has correct name
        assert agent.circuit_breaker.name == agent.name

        # Verify: Circuit breaker can report status
        status = agent.circuit_breaker.get_status()
        assert isinstance(status, dict)
        assert "state" in status

    def test_agent_unified_reliability_handler_integration(self):
        """Test agent integrates with UnifiedRetryHandler (SSOT pattern)."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)

        # Verify: Unified reliability handler exists
        unified_handler = agent.unified_reliability_handler
        assert unified_handler is not None
        assert isinstance(unified_handler, UnifiedRetryHandler)

        # Verify: Handler has correct service name
        assert unified_handler.service_name == f"agent_{agent.name}"

        # Verify: Handler has configuration
        config = unified_handler.config
        assert config is not None
        assert hasattr(config, 'max_attempts')
        assert hasattr(config, 'circuit_breaker_enabled')

    async def test_agent_execute_with_reliability_basic(self):
        """Test agent execute_with_reliability method."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-test-001")

        # Test operation that succeeds
        async def successful_operation():
            return {"result": "success", "operation": "test"}

        # Execute with reliability
        result = await agent.execute_with_reliability(
            operation=successful_operation,
            operation_name="test_operation"
        )

        # Verify: Result returned correctly
        assert result["result"] == "success"
        assert result["operation"] == "test"

    async def test_agent_execute_with_reliability_retry_on_failure(self):
        """Test agent retry mechanism on failures."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-retry-001")

        attempt_count = 0

        async def failing_then_succeeding_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ValueError("First attempt fails")
            return {"result": "success", "attempt": attempt_count}

        # Execute with reliability (should retry and succeed)
        result = await agent.execute_with_reliability(
            operation=failing_then_succeeding_operation,
            operation_name="retry_test"
        )

        # Verify: Operation succeeded after retry
        assert result["result"] == "success"
        assert result["attempt"] == 2
        assert attempt_count == 2

    async def test_agent_execute_with_reliability_fallback(self):
        """Test agent fallback mechanism when primary operation fails."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-fallback-001")

        async def always_failing_operation():
            raise RuntimeError("Primary operation always fails")

        async def fallback_operation():
            return {"result": "fallback_success", "source": "fallback"}

        # Execute with reliability and fallback
        result = await agent.execute_with_reliability(
            operation=always_failing_operation,
            operation_name="fallback_test",
            fallback=fallback_operation
        )

        # Verify: Fallback was used
        assert result["result"] == "fallback_success"
        assert result["source"] == "fallback"

    async def test_agent_circuit_breaker_integration(self):
        """Test circuit breaker integration during agent execution."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-circuit-001")

        # Get initial circuit breaker status
        initial_status = agent.get_circuit_breaker_status()
        assert isinstance(initial_status, dict)

        # Circuit breaker should start in closed/healthy state
        if "state" in initial_status:
            assert initial_status["state"].lower() in ["closed", "healthy"]
        elif "status" in initial_status:
            assert initial_status["status"].lower() in ["closed", "healthy", "not_available"]

        # Test that circuit breaker can execute
        assert agent.circuit_breaker.can_execute()

    async def test_agent_execution_monitoring_integration(self):
        """Test execution monitoring during agent operations."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-monitor-001")

        # Verify: Execution monitor exists
        monitor = agent.execution_monitor
        assert monitor is not None

        # Get initial health status
        initial_health = monitor.get_health_status()
        assert isinstance(initial_health, dict)

        # Execute agent to generate monitoring data
        result = await agent.execute_with_context(self.test_context, stream_updates=False)
        assert result["status"] == "success"

        # Get updated health status
        updated_health = monitor.get_health_status()
        assert isinstance(updated_health, dict)

    async def test_agent_error_handling_patterns(self):
        """Test various error handling patterns in agent execution."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-errors-001")

        # Test 1: ValueError (should be retryable per agent config)
        agent.set_failure_mode("fail_once")
        result = await agent.execute_with_context(self.test_context, stream_updates=False)
        assert result["status"] == "success"
        assert result["execution_attempts"] == 2  # Failed once, succeeded on retry

        # Reset for next test
        agent.set_failure_mode(None)

        # Test 2: RuntimeError (should also be retryable)
        agent.set_failure_mode("fail_twice")
        result = await agent.execute_with_context(self.test_context, stream_updates=False)
        assert result["status"] == "success"
        assert result["execution_attempts"] == 3  # Failed twice, succeeded on third

    async def test_agent_timeout_handling(self):
        """Test agent timeout handling mechanisms."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-timeout-001")

        # Set timeout failure mode
        agent.set_failure_mode("timeout")

        # Execute with timeout expectation
        # Note: This may succeed or fail depending on retry configuration
        # The test verifies the timeout is handled gracefully
        try:
            start_time = time.time()
            result = await agent.execute_with_context(self.test_context, stream_updates=False)
            # If it succeeds, verify it took reasonable time
            elapsed = time.time() - start_time
            # Should either timeout quickly or succeed after retries
            assert elapsed < 10  # Reasonable upper bound
        except (TimeoutError, RuntimeError, asyncio.TimeoutError):
            # Timeout is acceptable - verify it happened in reasonable time
            elapsed = time.time() - start_time
            assert elapsed > 1  # Should have attempted the operation
            assert elapsed < 10  # But not wait forever

    def test_agent_health_status_includes_reliability_data(self):
        """Test agent health status includes reliability infrastructure data."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-health-001")

        # Get comprehensive health status
        health = agent.get_health_status()

        # Verify: Health includes reliability components
        reliability_keys = [
            "circuit_breaker", "circuit_breaker_state", "reliability_manager",
            "legacy_reliability", "unified_reliability", "monitor", "monitoring"
        ]

        # Should have at least some reliability data
        has_reliability_data = any(key in health for key in reliability_keys)
        assert has_reliability_data

        # Should have overall status
        assert "overall_status" in health or "status" in health

        # Should indicate unified reliability usage
        assert health.get("uses_unified_reliability", False) is True

    def test_agent_reliability_configuration_validation(self):
        """Test agent reliability configuration is properly validated."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager, enable_reliability=True)

        # Verify: Circuit breaker configuration
        cb_status = agent.get_circuit_breaker_status()
        assert isinstance(cb_status, dict)

        # Verify: Unified reliability handler configuration
        unified_handler = agent.unified_reliability_handler
        if unified_handler:
            config = unified_handler.config
            assert hasattr(config, 'max_attempts')
            assert hasattr(config, 'retryable_exceptions')
            assert hasattr(config, 'circuit_breaker_enabled')

            # Agent configuration should enable circuit breaker
            assert config.circuit_breaker_enabled is True

            # Should include ValueError and RuntimeError as retryable
            retryable_exceptions = config.retryable_exceptions
            assert ValueError in retryable_exceptions
            assert RuntimeError in retryable_exceptions

    async def test_agent_reliability_concurrent_executions(self):
        """Test reliability infrastructure works correctly with concurrent executions."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-concurrent-001")

        # Create multiple contexts for concurrent testing
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent-reliability-user-{i}",
                thread_id=f"concurrent-reliability-thread-{i}",
                run_id=f"concurrent-reliability-run-{i}",
                agent_context={"user_request": f"concurrent reliability test {i}"}
            ).with_db_session(AsyncMock())
            contexts.append(context)

        # Execute concurrent operations
        tasks = [
            agent.execute_with_context(ctx, stream_updates=False)
            for ctx in contexts
        ]

        results = await asyncio.gather(*tasks)

        # Verify: All executions succeeded
        assert len(results) == 3
        for result in results:
            assert result["status"] == "success"
            assert result["execution_attempts"] == 1  # No failures in this test

        # Verify: Circuit breaker still healthy after concurrent load
        cb_status = agent.get_circuit_breaker_status()
        if "state" in cb_status:
            assert cb_status["state"].lower() in ["closed", "healthy"]

    async def test_agent_reliability_stress_test(self):
        """Test reliability infrastructure under stress conditions."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-stress-001")

        # Execute many operations in quick succession
        stress_contexts = []
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"stress-user-{i}",
                thread_id=f"stress-thread-{i}",
                run_id=f"stress-run-{i}",
                agent_context={"user_request": f"stress test {i}"}
            ).with_db_session(AsyncMock())
            stress_contexts.append(context)

        # Execute all operations
        tasks = [
            agent.execute_with_context(ctx, stream_updates=False)
            for ctx in stress_contexts
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time

        # Verify: All operations completed successfully
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result["status"] == "success"

        # Verify: Performance is reasonable
        assert elapsed_time < 5  # Should complete within 5 seconds

        # Verify: Reliability infrastructure is still healthy
        health = agent.get_health_status()
        assert health.get("overall_status", "unknown") == "healthy" or health.get("status", "unknown") == "healthy"

    async def test_agent_error_recovery_state_management(self):
        """Test agent properly manages state during error recovery."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-recovery-001")

        # Set up for failure then recovery
        agent.set_failure_mode("fail_once")

        # Execute (should fail once then recover)
        result = await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: Recovery was successful
        assert result["status"] == "success"
        assert result["execution_attempts"] == 2

        # Verify: Agent state is healthy after recovery
        health = agent.get_health_status()
        assert health.get("overall_status", "unknown") in ["healthy", "degraded"]

        # Verify: Circuit breaker state after recovery
        cb_status = agent.get_circuit_breaker_status()
        if "state" in cb_status:
            # Should not be in open state after successful recovery
            assert cb_status["state"].lower() != "open"

    def test_agent_reliability_legacy_compatibility(self):
        """Test reliability infrastructure maintains backward compatibility."""
        agent = ReliabilityTestAgent(llm_manager=self.llm_manager)
        agent.set_websocket_bridge(self.websocket_bridge, "reliability-legacy-001")

        # Verify: Legacy reliability property exists
        legacy_reliability = agent.legacy_reliability
        # Should return the unified handler for backward compatibility
        assert legacy_reliability is agent.unified_reliability_handler

        # Verify: Golden Path compatibility methods exist
        assert hasattr(agent, 'execute_with_retry')
        assert hasattr(agent, 'execute_with_fallback')
        assert callable(agent.execute_with_retry)
        assert callable(agent.execute_with_fallback)