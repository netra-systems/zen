"""
Comprehensive Unit Tests for AgentExecutionCore

Tests the core agent execution engine focusing on business logic, error boundaries,
timeout handling, WebSocket integration, and trace context management.

CRITICAL REQUIREMENTS from CLAUDE.md:
1. Uses absolute imports 
2. Follows SSOT patterns from test_framework/ssot/
3. Uses StronglyTypedUserExecutionContext and proper type safety
4. Tests MUST RAISE ERRORS (no try/except blocks that hide failures)
5. Focuses on individual methods/functions in isolation

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures the critical agent execution engine works correctly under all conditions.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from uuid import UUID, uuid4
from typing import Optional, Any, Dict

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class TestAgentExecutionCoreUnit(SSotBaseTestCase):
    """Comprehensive unit tests for AgentExecutionCore business logic."""

    @pytest.fixture
    def mock_registry(self):
        """Mock agent registry with controlled behavior."""
        registry = Mock()
        registry.get = Mock()
        return registry

    @pytest.fixture  
    def mock_websocket_bridge(self):
        """Mock AgentWebSocketBridge with all required methods."""
        bridge = AsyncMock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_agent_error = AsyncMock()
        bridge.notify_agent_thinking = AsyncMock()
        return bridge

    @pytest.fixture
    def mock_execution_tracker(self):
        """Mock execution tracker for lifecycle management."""
        tracker = AsyncMock()
        tracker.register_execution = AsyncMock(return_value=uuid4())
        tracker.start_execution = AsyncMock()
        tracker.complete_execution = AsyncMock()
        tracker.collect_metrics = AsyncMock(return_value={'duration': 1.5, 'memory_mb': 128})
        return tracker

    @pytest.fixture
    def mock_state_tracker(self):
        """Mock agent state tracker for centralized phase tracking."""
        tracker = AsyncMock()
        tracker.start_execution = Mock(return_value="mock_state_exec_id")
        tracker.transition_phase = AsyncMock()
        tracker.complete_execution = Mock()
        return tracker

    @pytest.fixture
    def execution_core(self, mock_registry, mock_websocket_bridge, mock_execution_tracker, mock_state_tracker):
        """AgentExecutionCore instance with mocked dependencies."""
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker, \
             patch('netra_backend.app.agents.supervisor.agent_execution_core.get_agent_state_tracker') as mock_get_state_tracker:
            mock_get_tracker.return_value = mock_execution_tracker
            mock_get_state_tracker.return_value = mock_state_tracker
            core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
            return core

    @pytest.fixture
    def sample_context(self):
        """Sample agent execution context with strongly typed IDs."""
        return AgentExecutionContext(
            agent_name="test_agent",
            run_id=RunID(str(uuid4())),
            thread_id=ThreadID("test-thread-123"),
            user_id=UserID("test-user-456"),
            correlation_id="test-correlation-789",
            retry_count=0
        )

    @pytest.fixture
    def sample_state(self):
        """Real DeepAgentState for security-compliant testing.
        
        CRITICAL: Uses real DeepAgentState instead of Mock to pass security validation
        in _ensure_user_execution_context(). Mock objects fail isinstance() checks
        which are required for Issue #159 security compliance.
        """
        from netra_backend.app.agents.state import DeepAgentState
        
        state = DeepAgentState(
            user_id=str(UserID("test-user-456")),
            thread_id=str(ThreadID("test-thread-123")),
            user_request="test_request",
            chat_thread_id="test-thread-123"
        )
        return state

    @pytest.fixture
    def mock_successful_agent(self):
        """Mock agent that executes successfully."""
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={
            "success": True, 
            "result": "Agent completed successfully", 
            "metrics": {"duration": 2.5, "operations": 3}
        })
        agent.__class__.__name__ = "SuccessfulTestAgent"
        
        # Mock synchronous methods to avoid AsyncMock warnings
        agent.set_trace_context = Mock()
        agent.set_websocket_bridge = Mock()
        agent.websocket_bridge = None
        agent.execution_engine = None
        return agent

    @pytest.fixture
    def mock_failing_agent(self):
        """Mock agent that fails during execution."""
        agent = AsyncMock()
        agent.execute = AsyncMock(side_effect=RuntimeError("Agent execution failed"))
        agent.__class__.__name__ = "FailingTestAgent"
        
        # Mock synchronous methods
        agent.set_trace_context = Mock()
        agent.set_websocket_bridge = Mock()
        agent.websocket_bridge = None
        agent.execution_engine = None
        return agent

    def test_init_creates_proper_dependencies(self, mock_registry, mock_websocket_bridge):
        """Test that initialization creates proper dependencies and disables heartbeat."""
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker:
            mock_tracker = AsyncMock()
            mock_get_tracker.return_value = mock_tracker
            
            core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
            
            # Verify dependencies are set
            assert core.registry == mock_registry
            assert core.websocket_bridge == mock_websocket_bridge
            assert core.execution_tracker == mock_tracker
            assert core.persistence is None  # trace_persistence was removed
            
            # Verify timeout configuration
            assert core.DEFAULT_TIMEOUT == 25.0  # Changed from 30.0 for faster user feedback (Issue #158)
            assert core.HEARTBEAT_INTERVAL == 5.0

    @pytest.mark.asyncio
    async def test_execute_agent_successful_flow(
        self, execution_core, sample_context, sample_state, mock_successful_agent, 
        mock_execution_tracker, mock_websocket_bridge
    ):
        """Test successful agent execution with complete lifecycle."""
        # Setup mocks
        execution_core.registry.get.return_value = mock_successful_agent
        mock_exec_id = uuid4()
        mock_execution_tracker.register_execution.return_value = mock_exec_id
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None  # No parent trace
            
            # Execute agent
            result = await execution_core.execute_agent(sample_context, sample_state, timeout=15.0)
            
            # Verify successful result
            assert isinstance(result, AgentExecutionResult)
            assert result.success is True
            assert result.agent_name == "test_agent"
            assert result.duration is not None
            assert result.metrics is not None
            
            # Verify execution lifecycle calls
            mock_execution_tracker.register_execution.assert_called_once()
            mock_execution_tracker.start_execution.assert_called_once_with(mock_exec_id)
            mock_execution_tracker.complete_execution.assert_called_once()
            
            # Verify WebSocket notifications  
            # Note: notify_agent_started may be called multiple times during execution phases
            assert mock_websocket_bridge.notify_agent_started.call_count >= 1
            mock_websocket_bridge.notify_agent_completed.assert_called_once()
            
            # Verify agent was executed with UserExecutionContext (security conversion)
            # NOTE: DeepAgentState gets converted to UserExecutionContext for security compliance
            mock_successful_agent.execute.assert_called_once()
            call_args = mock_successful_agent.execute.call_args
            executed_state, executed_run_id, executed_flag = call_args[0]
            
            # Verify the security conversion happened
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            assert isinstance(executed_state, UserExecutionContext)
            assert executed_run_id == sample_context.run_id
            assert executed_flag is True

    @pytest.mark.asyncio
    async def test_execute_agent_with_failure(
        self, execution_core, sample_context, sample_state, mock_failing_agent,
        mock_execution_tracker, mock_websocket_bridge, mock_state_tracker
    ):
        """Test agent execution handles failures gracefully."""
        # Setup mocks
        execution_core.registry.get.return_value = mock_failing_agent
        mock_exec_id = uuid4()
        mock_execution_tracker.register_execution.return_value = mock_exec_id
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            
            # Execute agent
            result = await execution_core.execute_agent(sample_context, sample_state)
            
            # Verify failure result
            assert isinstance(result, AgentExecutionResult)
            assert result.success is False
            assert result.agent_name == "test_agent"
            assert "Agent execution failed" in result.error
            assert result.duration is not None
            
            # Verify execution was marked as failed
            mock_execution_tracker.complete_execution.assert_called_once()
            call_args = mock_execution_tracker.complete_execution.call_args
            assert "error" in call_args.kwargs or len(call_args.args) > 1
            
            # Verify centralized error notification through state tracker
            # The state tracker should have transitioned to FAILED phase, which automatically sends error notification
            from netra_backend.app.agents.agent_state_tracker import AgentExecutionPhase
            mock_state_tracker.transition_phase.assert_any_call(
                mock_state_tracker.start_execution.return_value,
                AgentExecutionPhase.FAILED,
                metadata={'error': result.error or 'Unknown error'},
                websocket_manager=mock_websocket_bridge
            )

    @pytest.mark.asyncio
    async def test_execute_agent_timeout_handling(
        self, execution_core, sample_context, sample_state, mock_execution_tracker
    ):
        """Test agent execution timeout handling."""
        # Create slow agent that will timeout
        slow_agent = AsyncMock()
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"success": True}
        slow_agent.execute = AsyncMock(side_effect=slow_execute)
        slow_agent.__class__.__name__ = "SlowAgent"
        slow_agent.set_trace_context = Mock()
        slow_agent.set_websocket_bridge = Mock()
        slow_agent.websocket_bridge = None
        slow_agent.execution_engine = None
        
        execution_core.registry.get.return_value = slow_agent
        mock_execution_tracker.register_execution.return_value = uuid4()
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            
            # Execute with short timeout
            result = await execution_core.execute_agent(sample_context, sample_state, timeout=0.5)
            
            # Verify timeout result
            assert isinstance(result, AgentExecutionResult)
            assert result.success is False
            assert result.agent_name == "test_agent"
            assert "timeout" in result.error.lower()
            assert result.duration is not None

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(
        self, execution_core, sample_context, sample_state, mock_execution_tracker, mock_websocket_bridge, mock_state_tracker
    ):
        """Test behavior when agent is not found in registry."""
        # Setup registry to return None (agent not found)
        execution_core.registry.get.return_value = None
        mock_exec_id = uuid4()
        mock_execution_tracker.register_execution.return_value = mock_exec_id
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            
            # Execute agent
            result = await execution_core.execute_agent(sample_context, sample_state)
            
            # Verify agent not found result
            assert isinstance(result, AgentExecutionResult)
            assert result.success is False
            assert result.agent_name == "test_agent"
            assert "not found" in result.error.lower()
            
            # Verify centralized error notification through state tracker
            # The state tracker should have transitioned to FAILED phase, which automatically sends error notification
            from netra_backend.app.agents.agent_state_tracker import AgentExecutionPhase
            mock_state_tracker.transition_phase.assert_any_call(
                mock_state_tracker.start_execution.return_value,
                AgentExecutionPhase.FAILED,
                metadata={"error": "Agent not found"},
                websocket_manager=mock_websocket_bridge
            )

    @pytest.mark.asyncio
    async def test_execute_with_protection_result_validation(
        self, execution_core, sample_context, sample_state, mock_execution_tracker
    ):
        """Test _execute_with_protection validates agent results properly."""
        # Test with None result (dead agent signature)
        dead_agent = AsyncMock()
        dead_agent.execute = AsyncMock(return_value=None)
        dead_agent.__class__.__name__ = "DeadAgent"
        dead_agent.set_trace_context = Mock()
        dead_agent.set_websocket_bridge = Mock()
        dead_agent.websocket_bridge = None
        dead_agent.execution_engine = None
        
        mock_exec_id = uuid4()
        mock_trace_context = Mock()
        mock_trace_context.to_websocket_context.return_value = {}
        
        # Execute with protection
        result = await execution_core._execute_with_protection(
            dead_agent, sample_context, sample_state, mock_exec_id, None, 30.0, mock_trace_context
        )
        
        # Verify dead agent detection
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "died silently" in result.error

    def test_calculate_performance_metrics(self, execution_core):
        """Test performance metrics calculation."""
        start_time = time.time() - 2.5  # 2.5 seconds ago
        
        # Test without heartbeat (heartbeat is disabled)
        metrics = execution_core._calculate_performance_metrics(start_time, None)
        
        # Verify basic metrics
        assert isinstance(metrics, dict)
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics
        assert metrics['execution_time_ms'] > 2000  # At least 2 seconds
        assert metrics['start_timestamp'] == start_time

    @pytest.mark.asyncio
    async def test_setup_agent_websocket_multiple_methods(self, execution_core, sample_context, sample_state):
        """Test WebSocket setup tries multiple methods for compatibility."""
        # Create agent with different WebSocket setup capabilities
        agent = Mock()
        agent.set_websocket_bridge = Mock()
        agent.websocket_bridge = None
        agent.execution_engine = Mock()
        agent.execution_engine.set_websocket_bridge = Mock()
        agent.__class__.__name__ = "TestAgent"
        
        mock_trace_context = Mock()
        mock_bridge = Mock()
        execution_core.websocket_bridge = mock_bridge
        
        # Setup agent WebSocket
        await execution_core._setup_agent_websocket(agent, sample_context, sample_state, mock_trace_context)
        
        # Verify multiple setup methods were attempted
        agent.set_websocket_bridge.assert_called_once_with(mock_bridge, sample_context.run_id)
        assert agent.websocket_bridge == mock_bridge
        assert agent._run_id == sample_context.run_id
        agent.execution_engine.set_websocket_bridge.assert_called_once_with(mock_bridge, sample_context.run_id)

    @pytest.mark.asyncio
    async def test_collect_metrics_comprehensive(
        self, execution_core, sample_state, mock_execution_tracker
    ):
        """Test comprehensive metrics collection."""
        mock_exec_id = uuid4()
        
        # Create result with metrics
        result = AgentExecutionResult(
            success=True,
            agent_name="test_agent",
            duration=3.5,
            metrics={"custom_metric": 123, "operations": 5}
        )
        
        # Setup tracker metrics
        tracker_metrics = {"db_queries": 2, "api_calls": 3}
        mock_execution_tracker.collect_metrics.return_value = tracker_metrics
        
        # Collect metrics
        combined_metrics = await execution_core._collect_metrics(mock_exec_id, result, sample_state, None)
        
        # Verify metrics combination
        assert isinstance(combined_metrics, dict)
        assert combined_metrics["db_queries"] == 2
        assert combined_metrics["api_calls"] == 3
        assert combined_metrics["custom_metric"] == 123
        assert combined_metrics["operations"] == 5
        assert combined_metrics["result_success"] is True
        assert combined_metrics["total_duration_seconds"] == 3.5
        assert "state_size" in combined_metrics

    def test_get_agent_or_error_success(self, execution_core):
        """Test successful agent retrieval from registry."""
        mock_agent = Mock()
        execution_core.registry.get.return_value = mock_agent
        
        result = execution_core._get_agent_or_error("test_agent")
        
        assert result == mock_agent
        execution_core.registry.get.assert_called_once_with("test_agent")

    def test_get_agent_or_error_not_found(self, execution_core):
        """Test agent not found error handling."""
        execution_core.registry.get.return_value = None
        
        result = execution_core._get_agent_or_error("missing_agent")
        
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert result.agent_name == "missing_agent"
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_persist_metrics_disabled(self, execution_core, sample_state):
        """Test metrics persistence when disabled (persistence=None)."""
        mock_exec_id = uuid4()
        metrics = {"test_metric": 456}
        
        # persistence is None by default (disabled)
        assert execution_core.persistence is None
        
        # This should not raise an error
        await execution_core._persist_metrics(mock_exec_id, metrics, "test_agent", sample_state)
        
        # No exception means test passed

    def test_create_websocket_callback(self, execution_core, sample_context):
        """Test WebSocket callback creation for heartbeat updates."""
        mock_trace_context = Mock()
        mock_trace_context.to_websocket_context.return_value = {"trace_id": "test-trace"}
        
        callback = execution_core._create_websocket_callback(sample_context, mock_trace_context)
        
        # Verify callback is created when websocket_bridge exists
        assert callback is not None
        assert callable(callback)
        
        # Test with no websocket_bridge
        execution_core.websocket_bridge = None
        callback_none = execution_core._create_websocket_callback(sample_context, mock_trace_context)
        assert callback_none is None