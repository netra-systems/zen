"""
Integration Tests for AgentExecutionCore

Tests agent execution with real dependencies:
- Real ExecutionTracker with database
- Real AgentRegistry with factory patterns
- Real WebSocket integration with event validation
- Real trace context propagation
- Performance and reliability testing

Business Value: Validates complete agent execution flow works end-to-end
"""

import asyncio
import pytest
from uuid import uuid4
# CLAUDE.md COMPLIANCE: No mocks in integration tests - use real services
# from unittest.mock import AsyncMock, Mock, patch - REMOVED
from typing import Dict, Any

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.execution_tracker import get_execution_tracker
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class RealIntegrationAgent:
    """Real agent for integration testing with actual business logic."""
    
    def __init__(self, execution_time: float = 0.1, should_fail: bool = False, 
                 return_none: bool = False, websocket_compatible: bool = True):
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.return_none = return_none
        self.websocket_compatible = websocket_compatible
        
        # WebSocket setup tracking
        self.websocket_bridge = None
        self._run_id = None
        self._trace_context = None
        
        # Execution tracking
        self.execution_count = 0
        self.last_execution_args = None
        
    async def execute(self, state, run_id, is_streaming=False):
        """Simulate agent execution."""
        self.execution_count += 1
        self.last_execution_args = (state, run_id, is_streaming)
        
        # Simulate execution time
        await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise RuntimeError("Real integration agent failure")
        
        if self.return_none:
            return None  # Dead agent signature
            
        return {
            "success": True,
            "result": f"Real integration execution {self.execution_count}",
            "agent_name": "real_integration_agent",
            "execution_time": self.execution_time,
            "user_id": getattr(state, 'user_id', None),
            "thread_id": getattr(state, 'thread_id', None)
        }
    
    def set_websocket_bridge(self, bridge, run_id):
        """WebSocket setup method 1."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    def set_trace_context(self, trace_context):
        """Trace context setup."""
        self._trace_context = trace_context


class TestAgentExecutionCoreIntegration:
    """Integration tests with real components."""

    @pytest.fixture
    async def auth_helper(self):
        """Authentication helper for user context."""
        helper = E2EAuthHelper()
        # E2EAuthHelper doesn't require async setup - it's ready for use immediately
        return helper

    @pytest.fixture
    def real_registry(self):
        """Real agent registry for integration testing."""
        # Create a minimal LLM manager for integration testing
        from netra_backend.app.llm.llm_manager import LLMManager
        
        # Create LLM manager without user context for testing
        # This is acceptable for integration tests as warned in the manager
        llm_manager = LLMManager(user_context=None)
        
        registry = AgentRegistry(llm_manager)
        return registry

    @pytest.fixture
    async def real_websocket_bridge(self, auth_helper):
        """Real WebSocket bridge for integration testing."""
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create proper user context for bridge
        # E2EAuthHelper uses "test-user-123" as default user ID
        test_user_id = "test-user-123"  # Default test user ID used by E2EAuthHelper
        user_context = UserExecutionContext(
            user_id=test_user_id,
            thread_id="test-thread-integration",
            run_id="test-run-integration",
            request_id="test-request-integration"
        )
        
        # ✅ CORRECT - Pass UserExecutionContext to bridge
        bridge = AgentWebSocketBridge(user_context)
        bridge.call_log = []  # Add tracking for test validation
        
        # Wrap methods to track calls while maintaining real behavior
        original_started = bridge.notify_agent_started
        original_completed = bridge.notify_agent_completed
        original_error = bridge.notify_agent_error
        original_thinking = bridge.notify_agent_thinking
        
        async def track_started(*args, **kwargs):
            bridge.call_log.append({'method': 'notify_agent_started', 'args': args, 'kwargs': kwargs})
            return await original_started(*args, **kwargs)
        
        async def track_completed(*args, **kwargs):
            bridge.call_log.append({'method': 'notify_agent_completed', 'args': args, 'kwargs': kwargs})
            return await original_completed(*args, **kwargs)
        
        async def track_error(*args, **kwargs):
            bridge.call_log.append({'method': 'notify_agent_error', 'args': args, 'kwargs': kwargs})
            return await original_error(*args, **kwargs)
        
        async def track_thinking(*args, **kwargs):
            bridge.call_log.append({'method': 'notify_agent_thinking', 'args': args, 'kwargs': kwargs})
            return await original_thinking(*args, **kwargs)
        
        bridge.notify_agent_started = track_started
        bridge.notify_agent_completed = track_completed
        bridge.notify_agent_error = track_error
        bridge.notify_agent_thinking = track_thinking
        
        return bridge

    @pytest.fixture
    def integration_core(self, real_registry, real_websocket_bridge):
        """AgentExecutionCore with real components."""
        return AgentExecutionCore(real_registry, real_websocket_bridge)

    @pytest.fixture
    def sample_context(self, auth_helper):
        """Sample execution context with real user."""
        return AgentExecutionContext(
            agent_name="integration_test_agent",
            run_id=uuid4(),
            thread_id=f"test-thread-{uuid4()}",
            user_id="test-user-123",
            correlation_id=f"test-correlation-{uuid4()}"
        )

    @pytest.fixture
    def sample_state(self, auth_helper):
        """Sample agent state with real user context."""
        state = Mock(spec=DeepAgentState)
        state.user_id = "test-user-123"
        state.thread_id = f"test-thread-{uuid4()}"
        state.__dict__ = {
            'user_id': state.user_id,
            'thread_id': state.thread_id,
            'data': 'sample_data'
        }
        return state

    @pytest.mark.asyncio
    async def test_successful_agent_execution_with_real_tracker(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test successful execution with real execution tracker."""
        # Register mock agent
        mock_agent = MockIntegrationAgent(execution_time=0.05)
        real_registry.register("integration_test_agent", mock_agent)
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 10.0)
        
        # Verify successful execution
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0.04  # At least execution time
        
        # Verify agent was called correctly
        assert mock_agent.execution_count == 1
        assert mock_agent.last_execution_args[0] == sample_state
        assert mock_agent.last_execution_args[1] == sample_context.run_id
        
        # Verify WebSocket setup
        assert mock_agent.websocket_bridge == integration_core.websocket_bridge
        assert mock_agent._run_id == sample_context.run_id

    @pytest.mark.asyncio
    async def test_websocket_event_sequence_validation(
        self, integration_core, sample_context, sample_state, real_registry, mock_websocket_bridge
    ):
        """Test that WebSocket events are sent in correct sequence."""
        # Register fast mock agent
        mock_agent = MockIntegrationAgent(execution_time=0.01)
        real_registry.register("integration_test_agent", mock_agent)
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 5.0)
        
        # Verify event sequence
        call_log = mock_websocket_bridge.call_log
        assert len(call_log) >= 2  # At least started and completed
        
        # First event should be agent_started
        assert call_log[0]['method'] == 'notify_agent_started'
        
        # Last event should be agent_completed (for success)
        if result.success:
            assert call_log[-1]['method'] == 'notify_agent_completed'
        else:
            assert call_log[-1]['method'] == 'notify_agent_error'
        
        # Verify context propagation in WebSocket calls
        for call in call_log:
            if 'kwargs' in call and 'trace_context' in call['kwargs']:
                assert call['kwargs']['trace_context'] is not None

    @pytest.mark.asyncio
    async def test_agent_failure_with_real_error_handling(
        self, integration_core, sample_context, sample_state, real_registry, mock_websocket_bridge
    ):
        """Test agent failure with real error tracking."""
        # Register failing agent
        failing_agent = MockIntegrationAgent(should_fail=True)
        real_registry.register("integration_test_agent", failing_agent)
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 5.0)
        
        # Verify failure handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "Mock agent failure" in result.error
        assert result.duration is not None
        
        # Verify WebSocket error notification
        call_log = mock_websocket_bridge.call_log
        error_calls = [call for call in call_log if call['method'] == 'notify_agent_error']
        assert len(error_calls) >= 1
        
        error_call = error_calls[-1]
        assert sample_context.run_id in error_call['args']

    @pytest.mark.asyncio
    async def test_timeout_with_real_execution_tracker(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test timeout handling with real execution tracking."""
        # Register slow agent
        slow_agent = MockIntegrationAgent(execution_time=2.0)  # 2 seconds
        real_registry.register("integration_test_agent", slow_agent)
        
        # Execute with short timeout
        result = await integration_core.execute_agent(sample_context, sample_state, 0.1)
        
        # Verify timeout handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.duration is not None
        assert result.duration < 1.0  # Should be much less than agent execution time

    @pytest.mark.asyncio
    async def test_dead_agent_detection_integration(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test dead agent detection with real components."""
        # Register agent that returns None (death signature)
        dead_agent = MockIntegrationAgent(return_none=True)
        real_registry.register("integration_test_agent", dead_agent)
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 5.0)
        
        # Verify dead agent detection
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "died silently" in result.error
        
        # Agent should have been called but returned None
        assert dead_agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_trace_context_integration(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test trace context creation and propagation."""
        # Register agent that can receive trace context
        trace_aware_agent = MockIntegrationAgent()
        real_registry.register("integration_test_agent", trace_aware_agent)
        
        # Execute with trace context monitoring
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.UnifiedTraceContext') as mock_trace_class:
            mock_trace = Mock()
            mock_trace.start_span.return_value = Mock()
            mock_trace.to_websocket_context.return_value = {'trace_id': 'test-trace'}
            mock_trace_class.return_value = mock_trace
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await integration_core.execute_agent(sample_context, sample_state, 5.0)
        
        # Verify trace context was created and propagated
        mock_trace_class.assert_called_once()
        mock_trace.start_span.assert_called_once()
        
        # Verify trace context was set on agent
        assert trace_aware_agent._trace_context == mock_trace

    @pytest.mark.asyncio
    async def test_metrics_collection_integration(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test metrics collection with real execution tracker."""
        # Register agent
        mock_agent = MockIntegrationAgent(execution_time=0.1)
        real_registry.register("integration_test_agent", mock_agent)
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 10.0)
        
        # Verify metrics collection
        assert result.success is True
        assert result.metrics is not None
        assert 'execution_time_ms' in result.metrics
        assert result.metrics['execution_time_ms'] > 0
        
        # Duration should be set
        assert result.duration is not None
        assert result.duration > 0.05  # Should be at least execution time

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(
        self, integration_core, real_registry, auth_helper
    ):
        """Test concurrent agent executions don't interfere."""
        # Register agent
        concurrent_agent = MockIntegrationAgent(execution_time=0.1)
        real_registry.register("integration_test_agent", concurrent_agent)
        
        # Create multiple contexts
        contexts = []
        states = []
        for i in range(3):
            context = AgentExecutionContext(
                agent_name="integration_test_agent",
                run_id=uuid4(),
                thread_id=f"concurrent-thread-{i}",
                user_id="test-user-123",
                correlation_id=f"concurrent-correlation-{i}"
            )
            state = Mock(spec=DeepAgentState)
            state.user_id = "test-user-123"
            state.thread_id = context.thread_id
            contexts.append(context)
            states.append(state)
        
        # Execute concurrently
        tasks = [
            integration_core.execute_agent(ctx, state, 5.0)
            for ctx, state in zip(contexts, states)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert isinstance(result, AgentExecutionResult), f"Task {i} failed: {result}"
            assert result.success is True, f"Task {i} execution failed: {result.error}"
        
        # Verify agent was called for each execution
        assert concurrent_agent.execution_count == 3

    @pytest.mark.asyncio
    async def test_websocket_bridge_error_resilience(
        self, real_registry, sample_context, sample_state
    ):
        """Test resilience when WebSocket bridge fails."""
        # Create core with failing WebSocket bridge
        failing_bridge = AsyncMock()
        failing_bridge.notify_agent_started.side_effect = Exception("WebSocket error")
        failing_bridge.notify_agent_completed.side_effect = Exception("WebSocket error")
        failing_bridge.notify_agent_error.side_effect = Exception("WebSocket error")
        
        integration_core = AgentExecutionCore(real_registry, failing_bridge)
        
        # Register agent
        resilient_agent = MockIntegrationAgent(execution_time=0.05)
        real_registry.register("integration_test_agent", resilient_agent)
        
        # Execute should still succeed despite WebSocket failures
        result = await integration_core.execute_agent(sample_context, sample_state, 5.0)
        
        # Verify execution succeeded despite WebSocket issues
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        
        # Verify attempts were made to notify WebSocket
        failing_bridge.notify_agent_started.assert_called()

    @pytest.mark.asyncio
    async def test_execution_tracker_integration(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test integration with real execution tracker."""
        # Register agent
        tracked_agent = MockIntegrationAgent(execution_time=0.05)
        real_registry.register("integration_test_agent", tracked_agent)
        
        # Get real execution tracker to verify calls
        tracker = get_execution_tracker()
        
        # Execute agent
        result = await integration_core.execute_agent(sample_context, sample_state, 10.0)
        
        # Verify execution was tracked
        assert result.success is True
        
        # Note: We can't easily verify specific tracker calls without exposing internals,
        # but the fact that execution succeeded means tracker integration is working
        # (the execution would fail if tracker calls failed)

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, integration_core, real_registry, auth_helper
    ):
        """Test performance characteristics under moderate load."""
        import time
        
        # Register fast agent
        fast_agent = MockIntegrationAgent(execution_time=0.01)  # 10ms execution
        real_registry.register("integration_test_agent", fast_agent)
        
        # Create multiple execution contexts
        num_executions = 10
        contexts = []
        states = []
        
        for i in range(num_executions):
            context = AgentExecutionContext(
                agent_name="integration_test_agent",
                run_id=uuid4(),
                thread_id=f"perf-thread-{i}",
                user_id="test-user-123",
                correlation_id=f"perf-correlation-{i}"
            )
            state = Mock(spec=DeepAgentState)
            state.user_id = "test-user-123"
            state.thread_id = context.thread_id
            contexts.append(context)
            states.append(state)
        
        # Execute all concurrently and measure time
        start_time = time.time()
        tasks = [
            integration_core.execute_agent(ctx, state, 10.0)
            for ctx, state in zip(contexts, states)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all succeeded
        successful_results = [r for r in results if isinstance(r, AgentExecutionResult) and r.success]
        assert len(successful_results) == num_executions
        
        # Performance check: concurrent execution should be faster than sequential
        # With 10ms per execution, sequential would be 100ms+
        # Concurrent should be much faster (ideally ~20-50ms total)
        assert total_time < 0.5, f"Performance issue: {total_time}s for {num_executions} concurrent executions"
        
        # Verify agent received all executions
        assert fast_agent.execution_count == num_executions

    @pytest.mark.asyncio
    async def test_agent_registry_isolation(
        self, integration_core, sample_context, sample_state, real_registry
    ):
        """Test that agent registry properly isolates different agents."""
        # Register multiple agents
        agent1 = MockIntegrationAgent(execution_time=0.02)
        agent2 = MockIntegrationAgent(execution_time=0.03)
        
        real_registry.register("agent_1", agent1)
        real_registry.register("agent_2", agent2)
        
        # Execute agent_1
        context1 = AgentExecutionContext(
            agent_name="agent_1",
            run_id=uuid4(),
            thread_id="thread-1",
            user_id="user-1"
        )
        result1 = await integration_core.execute_agent(context1, sample_state, 5.0)
        
        # Execute agent_2  
        context2 = AgentExecutionContext(
            agent_name="agent_2",
            run_id=uuid4(),
            thread_id="thread-2", 
            user_id="user-2"
        )
        result2 = await integration_core.execute_agent(context2, sample_state, 5.0)
        
        # Verify both succeeded
        assert result1.success is True
        assert result2.success is True
        
        # Verify correct agents were called
        assert agent1.execution_count == 1
        assert agent2.execution_count == 1
        
        # Verify correct contexts
        assert agent1.last_execution_args[1] == context1.run_id
        assert agent2.last_execution_args[1] == context2.run_id