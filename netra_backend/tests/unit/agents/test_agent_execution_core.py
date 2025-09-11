"""Unit tests for AgentExecutionCore - Core agent execution logic with death detection and recovery.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Platform Stability & Risk Reduction
- Value Impact: Ensures reliable agent execution with proper error handling and recovery
- Strategic Impact: Prevents silent agent failures that could impact user experience

CRITICAL: Tests validate core agent execution logic, death detection, and recovery mechanisms.
All tests use SSOT patterns and IsolatedEnvironment for environment access.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestAgentExecutionCore(SSotAsyncTestCase):
    """Unit tests for AgentExecutionCore - Core agent execution with death detection."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create mock registry and websocket bridge
        self.mock_registry = Mock()
        self.mock_websocket_bridge = AsyncMock()
        self.mock_execution_tracker = AsyncMock()
        self.mock_agent = AsyncMock()
        
        # Setup execution tracker mock
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker:
            mock_get_tracker.return_value = self.mock_execution_tracker
            self.execution_core = AgentExecutionCore(
                registry=self.mock_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
        
        # Create test context and state
        self.test_run_id = uuid4()
        self.test_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=str(self.test_run_id),
            thread_id="test_thread_123",
            user_id="test_user_123",
            retry_count=0
        )
        
        self.test_state = DeepAgentState()
        self.test_state.user_id = "test_user_123"
        self.test_state.thread_id = "test_thread_123"
        
        # Record metrics for business value tracking
        self.record_metric("test_setup_duration", time.time())

    async def test_execute_agent_successful_execution(self):
        """
        BVJ: Validates successful agent execution flow for reliable system operation.
        Tests complete agent lifecycle from start to completion with proper event handling.
        """
        # Setup successful agent execution
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        
        # Mock successful agent execution result
        expected_result = AgentExecutionResult(
            success=True,
            agent_name="test_agent",
            data="test_result"
        )
        self.mock_agent.execute.return_value = expected_result
        
        # Execute agent
        start_time = time.time()
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=30.0
        )
        execution_time = time.time() - start_time
        
        # Verify business value: Successful execution
        assert result is not None, "Agent execution should return a result"
        assert isinstance(result, AgentExecutionResult), "Result should be AgentExecutionResult type"
        assert result.success is True, "Agent execution should succeed"
        assert result.duration is not None, "Execution duration should be recorded"
        
        # Verify execution tracking for monitoring
        self.mock_execution_tracker.register_execution.assert_called_once()
        self.mock_execution_tracker.start_execution.assert_called_once_with(exec_id)
        self.mock_execution_tracker.complete_execution.assert_called_once()
        
        # Verify WebSocket notifications for user feedback
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Record performance metrics
        self.record_metric("agent_execution_time", execution_time)
        self.record_metric("websocket_events_sent", 2)  # started + completed
        
        # Business value assertion: Execution under performance threshold
        assert execution_time < 5.0, f"Agent execution took too long: {execution_time}s"

    async def test_execute_agent_not_found_error(self):
        """
        BVJ: Validates proper error handling when agent is not found in registry.
        Prevents silent failures that could confuse users about system status.
        """
        # Setup agent not found scenario
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = None  # Agent not found
        
        # Execute agent
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify proper error handling
        assert result is not None, "Should return error result, not None"
        assert isinstance(result, AgentExecutionResult), "Should return AgentExecutionResult"
        assert result.success is False, "Should indicate failure"
        assert "not found" in result.error.lower(), f"Error should mention 'not found': {result.error}"
        
        # Verify error tracking for monitoring
        self.mock_execution_tracker.complete_execution.assert_called_once()
        call_args = self.mock_execution_tracker.complete_execution.call_args
        assert "error" in call_args.kwargs, "Should record error in execution tracker"
        
        # Verify error notification to user
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        
        # Record error metrics for monitoring
        self.record_metric("agent_not_found_errors", 1)

    async def test_execute_agent_timeout_protection(self):
        """
        BVJ: Validates timeout protection prevents system from hanging on unresponsive agents.
        Critical for maintaining system reliability and user experience under load.
        """
        # Setup hanging agent
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        
        # Mock agent that hangs (never returns)
        async def hanging_agent(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate hanging
            return {"success": True}
        
        self.mock_agent.execute = hanging_agent
        
        # Execute with short timeout
        timeout = 0.5  # 500ms timeout
        start_time = time.time()
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=timeout
        )
        execution_time = time.time() - start_time
        
        # Verify timeout protection worked
        assert result is not None, "Should return timeout result, not None"
        assert result.success is False, "Should indicate failure on timeout"
        assert "timeout" in result.error.lower(), f"Error should mention timeout: {result.error}"
        assert execution_time < timeout + 0.2, f"Should timeout quickly: {execution_time}s"
        
        # Verify timeout metrics
        assert result.duration is not None, "Should record execution duration"
        assert result.duration <= execution_time, "Recorded duration should be realistic"
        
        # Record timeout metrics for monitoring
        self.record_metric("timeout_errors", 1)
        self.record_metric("timeout_duration", execution_time)
        
        # Business value assertion: System remained responsive
        assert execution_time < 1.0, "System should remain responsive during timeouts"

    async def test_execute_agent_exception_handling(self):
        """
        BVJ: Validates proper exception handling prevents crashes and provides clear error information.
        Ensures system stability when agent execution encounters unexpected errors.
        """
        # Setup exception-throwing agent
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        
        # Mock agent that throws exception
        test_exception = RuntimeError("Test agent failure")
        self.mock_agent.execute.side_effect = test_exception
        
        # Execute agent
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify exception handling
        assert result is not None, "Should return error result, not raise exception"
        assert result.success is False, "Should indicate failure"
        assert "Test agent failure" in result.error, f"Should include original error: {result.error}"
        
        # Verify error tracking
        self.mock_execution_tracker.complete_execution.assert_called_once()
        call_args = self.mock_execution_tracker.complete_execution.call_args
        assert "error" in call_args.kwargs, "Should record error in tracker"
        
        # Verify error notification
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        
        # Record exception metrics
        self.record_metric("agent_exceptions", 1)

    async def test_execute_agent_websocket_propagation(self):
        """
        BVJ: Validates WebSocket bridge is properly propagated to agents for event delivery.
        Critical for real-time user feedback during agent execution.
        """
        # Setup successful execution
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        self.mock_agent.execute.return_value = AgentExecutionResult(
            success=True,
            agent_name="test_agent"
        )
        
        # Execute agent
        await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify WebSocket bridge was set on agent (multiple methods)
        websocket_set = False
        
        # Check if set_websocket_bridge was called
        if hasattr(self.mock_agent, 'set_websocket_bridge') and self.mock_agent.set_websocket_bridge.called:
            websocket_set = True
        
        # Check if websocket_bridge attribute was set
        if hasattr(self.mock_agent, 'websocket_bridge') and self.mock_agent.websocket_bridge is not None:
            websocket_set = True
        
        # Check execution engine WebSocket setting
        if hasattr(self.mock_agent, 'execution_engine') and self.mock_agent.execution_engine:
            if hasattr(self.mock_agent.execution_engine, 'set_websocket_bridge'):
                websocket_set = True
        
        # For this test, we'll mock the setup to verify the logic
        with patch.object(self.execution_core, '_setup_agent_websocket') as mock_setup:
            await self.execution_core.execute_agent(
                context=self.test_context,
                state=self.test_state
            )
            mock_setup.assert_called_once()
        
        # Record WebSocket propagation metrics
        self.record_metric("websocket_propagation_attempts", 1)

    async def test_execute_agent_death_detection(self):
        """
        BVJ: Validates detection of silent agent death (None result) to prevent hanging operations.
        Critical for maintaining system reliability and preventing resource leaks.
        """
        # Setup agent that returns None (death signature)
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        self.mock_agent.execute.return_value = None  # Dead agent signature
        
        # Execute agent
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify death detection
        assert result is not None, "Death detection should return error result"
        assert result.success is False, "Should indicate failure for dead agent"
        assert "died silently" in result.error.lower(), f"Should detect death: {result.error}"
        
        # Verify error tracking for dead agents
        self.mock_execution_tracker.complete_execution.assert_called_once()
        call_args = self.mock_execution_tracker.complete_execution.call_args
        error_message = call_args.kwargs.get("error", "")
        assert "died silently" in error_message.lower(), "Should record death in tracker"
        
        # Record death detection metrics
        self.record_metric("dead_agent_detections", 1)

    async def test_execute_agent_metrics_collection(self):
        """
        BVJ: Validates comprehensive metrics collection for performance monitoring and optimization.
        Enables data-driven improvements to agent execution performance.
        """
        # Setup successful execution with metrics
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        self.mock_agent.execute.return_value = AgentExecutionResult(
            success=True,
            agent_name="test_agent",
            data="test"
        )
        
        # Mock metrics collection
        test_metrics = {
            "execution_time_ms": 1500,
            "memory_usage_mb": 128,
            "cpu_percent": 15.5
        }
        self.mock_execution_tracker.collect_metrics.return_value = test_metrics
        
        # Execute agent
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify metrics collection
        assert result.success is True, "Execution should succeed"
        assert result.duration is not None, "Should record execution duration"
        assert result.metrics is not None, "Should include performance metrics"
        
        # Verify metrics were collected
        self.mock_execution_tracker.collect_metrics.assert_called_once_with(exec_id)
        
        # Verify metrics persistence (if configured)
        # Note: persistence is disabled in this component but logic should be tested
        
        # Record metrics collection for monitoring
        self.record_metric("metrics_collected", len(test_metrics))
        self.record_metric("execution_duration_recorded", result.duration)

    async def test_execute_agent_trace_context_propagation(self):
        """
        BVJ: Validates trace context propagation for distributed tracing and debugging.
        Critical for troubleshooting issues across the distributed agent execution system.
        """
        # Setup execution with trace context
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        self.mock_agent.execute.return_value = AgentExecutionResult(
            success=True,
            agent_name="test_agent"
        )
        
        # Mock trace context creation
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.UnifiedTraceContext') as mock_trace_class:
                mock_trace_instance = Mock()
                mock_trace_instance.propagate_to_child.return_value = mock_trace_instance
                mock_trace_instance.start_span.return_value = Mock()
                mock_trace_instance.to_websocket_context.return_value = {}
                mock_trace_class.return_value = mock_trace_instance
                mock_get_trace.return_value = None  # No parent trace
                
                # Execute agent
                result = await self.execution_core.execute_agent(
                    context=self.test_context,
                    state=self.test_state
                )
                
                # Verify trace context creation
                mock_trace_class.assert_called_once()
                mock_trace_instance.start_span.assert_called_once()
                mock_trace_instance.to_websocket_context.assert_called()
        
        # Verify successful execution with tracing
        assert result.success is True, "Execution should succeed with tracing"
        
        # Record tracing metrics
        self.record_metric("trace_contexts_created", 1)

    async def test_execute_agent_heartbeat_disabled_by_design(self):
        """
        BVJ: Validates heartbeat system is properly disabled to prevent error suppression.
        Based on AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md findings.
        """
        # Setup execution
        exec_id = uuid4()
        self.mock_execution_tracker.register_execution.return_value = exec_id
        self.mock_registry.get.return_value = self.mock_agent
        self.mock_agent.execute.return_value = AgentExecutionResult(
            success=True,
            agent_name="test_agent"
        )
        
        # Execute agent
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state
        )
        
        # Verify heartbeat is disabled (business requirement)
        # The heartbeat variable in _execute_with_protection should be None
        assert result.success is True, "Execution should work without heartbeat"
        
        # Verify no heartbeat-related metrics are recorded
        assert "heartbeat_count" not in (result.metrics or {}), "Heartbeat metrics should not be present"
        
        # Record heartbeat disabled verification
        self.record_metric("heartbeat_disabled_verification", 1)
        
        # Business value: Error visibility is maintained without heartbeat suppression
        # This is verified by the absence of heartbeat noise in error reporting

    def teardown_method(self, method=None):
        """Cleanup test fixtures and verify metrics."""
        # Verify test executed successfully
        assert self.get_test_context() is not None, "Test context should be available"
        
        # Record final metrics
        self.record_metric("test_completed", True)
        
        # Call parent teardown
        super().teardown_method(method)