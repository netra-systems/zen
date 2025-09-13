"""
Unit Tests for AgentExecutionCore

Tests the core agent execution engine with death detection, recovery,
and proper trace context management without external dependencies.

Focus: Business logic, error boundaries, timeout handling, WebSocket setup
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from typing import Optional

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class TestAgentExecutionCore:
    """Unit tests for AgentExecutionCore business logic."""

    @pytest.fixture
    def mock_registry(self):
        """Mock agent registry."""
        registry = Mock()
        registry.get = Mock()
        registry.get_async = AsyncMock()  # Fix: Add async method that's actually called
        return registry

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock websocket bridge."""
        bridge = AsyncMock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_agent_error = AsyncMock()
        return bridge

    @pytest.fixture
    def mock_execution_tracker(self):
        """Mock execution tracker."""
        tracker = Mock()  # Fix: Use Mock() for sync methods to avoid coroutine warnings
        tracker.register_execution = Mock(return_value=uuid4())  # Sync method
        tracker.start_execution = Mock()  # Sync method
        tracker.complete_execution = Mock()  # Sync method
        tracker.collect_metrics = AsyncMock(return_value={'duration': 1.5})  # Keep async for actual async method
        return tracker

    @pytest.fixture
    def execution_core(self, mock_registry, mock_websocket_bridge):
        """AgentExecutionCore instance with mocked dependencies."""
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker:
            # Create mock execution tracker with proper sync methods
            mock_tracker = Mock()
            mock_tracker.create_execution = Mock(return_value=str(uuid4()))
            mock_tracker.start_execution = Mock(return_value=True)
            mock_tracker.update_execution_state = Mock()
            mock_tracker.get_metrics = Mock(return_value={'duration': 1.5})
            mock_get_tracker.return_value = mock_tracker
            core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
            return core

    @pytest.fixture
    def sample_context(self):
        """Sample agent execution context."""
        return AgentExecutionContext(
            agent_name="test_agent",
            run_id=uuid4(),
            thread_id="test-thread",
            user_id="test-user",
            correlation_id="test-correlation"
        )

    @pytest.fixture
    def sample_user_context(self):
        """Sample user execution context - replaces DeepAgentState for security."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        return UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread", 
            run_id=str(uuid4()),
            agent_context={'tool_dispatcher': None}  # Add empty agent_context
        )

    @pytest.fixture
    def mock_agent(self):
        """Mock agent that can be executed."""
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={"success": True, "result": "test result", "metrics": {"duration": 1.0}})
        agent.__class__.__name__ = "TestAgent"
        # Fix AsyncMock warnings by making synchronous methods use Mock()
        agent.set_trace_context = Mock()
        agent.set_websocket_bridge = Mock()
        agent.websocket_bridge = None
        agent.execution_engine = None
        return agent

    def test_init_creates_proper_dependencies(self, mock_registry, mock_websocket_bridge):
        """Test that initialization creates proper dependencies."""
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker:
            mock_tracker = Mock()  # Fix: Use Mock() instead of AsyncMock() for sync methods
            mock_get_tracker.return_value = mock_tracker
            
            core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
            
            assert core.registry == mock_registry
            assert core.websocket_bridge == mock_websocket_bridge
            assert core.execution_tracker == mock_tracker
            assert core.persistence is None  # Disabled per comment

    def test_timeout_constants(self, execution_core):
        """Test timeout constants are properly configured."""
        assert execution_core.DEFAULT_TIMEOUT == 25.0  # Changed from 30.0 for faster user feedback (Issue #158)
        assert execution_core.HEARTBEAT_INTERVAL == 5.0

    @pytest.mark.asyncio
    async def test_execute_agent_success(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test successful agent execution with proper lifecycle."""
        # Setup mocks
        execution_core.registry.get_async.return_value = mock_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None  # No parent trace
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(sample_context, sample_user_context, 15.0)
        
        # Verify result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        
        # Verify lifecycle calls
        execution_core.execution_tracker.create_execution.assert_called_once()
        execution_core.execution_tracker.start_execution.assert_called_once()
        
        # Verify WebSocket notifications (may be called multiple times due to state transitions)
        assert execution_core.websocket_bridge.notify_agent_started.call_count >= 1
        assert execution_core.websocket_bridge.notify_agent_completed.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self, execution_core, sample_context, sample_user_context):
        """Test agent not found scenario."""
        # Agent doesn't exist
        execution_core.registry.get_async.return_value = None
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(sample_context, sample_user_context)
        
        # Verify error result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "not found" in result.error
        
        # Verify error notifications
        execution_core.websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_agent_timeout(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test agent execution timeout handling."""
        # Make agent execution hang
        async def hanging_execute(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"success": True}
        
        mock_agent.execute = hanging_execute
        execution_core.registry.get_async.return_value = mock_agent
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                # Set very short timeout
                result = await execution_core.execute_agent(sample_context, sample_user_context, 0.1)
        
        # Verify timeout result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.duration is not None

    @pytest.mark.asyncio
    async def test_execute_agent_exception(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test agent execution with unexpected exception."""
        # Make agent raise exception
        mock_agent.execute.side_effect = ValueError("Test exception")
        execution_core.registry.get_async.return_value = mock_agent
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(sample_context, sample_user_context)
        
        # Verify exception handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "Test exception" in result.error
        
        # Verify error tracking
        execution_core.execution_tracker.complete_execution.assert_called()
        args, kwargs = execution_core.execution_tracker.complete_execution.call_args
        assert 'error' in kwargs or len(args) > 1

    @pytest.mark.asyncio
    async def test_execute_agent_dead_agent_detection(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test detection of dead agents (returning None)."""
        # Agent returns None (death signature)
        mock_agent.execute.return_value = None
        execution_core.registry.get_async.return_value = mock_agent
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(sample_context, sample_user_context)
        
        # Verify dead agent detection
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "died silently" in result.error

    def test_setup_agent_websocket_multiple_methods(self, execution_core, sample_context, sample_user_context):
        """Test WebSocket setup tries multiple methods."""
        mock_agent = Mock()
        trace_context = Mock(spec=UnifiedTraceContext)
        
        # Test method 1: set_websocket_bridge
        mock_agent.set_websocket_bridge = Mock()
        
        asyncio.run(execution_core._setup_agent_websocket(
            mock_agent, sample_context, sample_user_context, trace_context
        ))
        
        mock_agent.set_websocket_bridge.assert_called_once_with(
            execution_core.websocket_bridge, 
            sample_context.run_id
        )

    def test_setup_agent_websocket_direct_assignment(self, execution_core, sample_context, sample_user_context):
        """Test WebSocket setup via direct assignment."""
        mock_agent = Mock()
        # No set_websocket_bridge method, but has websocket_bridge attribute
        delattr(mock_agent, 'set_websocket_bridge') if hasattr(mock_agent, 'set_websocket_bridge') else None
        mock_agent.websocket_bridge = None
        
        trace_context = Mock(spec=UnifiedTraceContext)
        
        asyncio.run(execution_core._setup_agent_websocket(
            mock_agent, sample_context, sample_user_context, trace_context
        ))
        
        assert mock_agent.websocket_bridge == execution_core.websocket_bridge
        assert mock_agent._run_id == sample_context.run_id

    def test_setup_agent_websocket_execution_engine(self, execution_core, sample_context, sample_user_context):
        """Test WebSocket setup on execution engine."""
        mock_agent = Mock()
        mock_execution_engine = Mock()
        mock_execution_engine.set_websocket_bridge = Mock()
        
        # No direct websocket methods, but has execution engine
        delattr(mock_agent, 'set_websocket_bridge') if hasattr(mock_agent, 'set_websocket_bridge') else None
        delattr(mock_agent, 'websocket_bridge') if hasattr(mock_agent, 'websocket_bridge') else None
        mock_agent.execution_engine = mock_execution_engine
        
        trace_context = Mock(spec=UnifiedTraceContext)
        
        asyncio.run(execution_core._setup_agent_websocket(
            mock_agent, sample_context, sample_user_context, trace_context
        ))
        
        mock_execution_engine.set_websocket_bridge.assert_called_once_with(
            execution_core.websocket_bridge, 
            sample_context.run_id
        )

    def test_calculate_performance_metrics_basic(self, execution_core):
        """Test performance metrics calculation."""
        start_time = time.time() - 1.5  # 1.5 seconds ago
        
        metrics = execution_core._calculate_performance_metrics(start_time)
        
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics  
        assert 'end_timestamp' in metrics
        assert metrics['execution_time_ms'] > 1400  # About 1.5s in ms
        assert metrics['start_timestamp'] == start_time

    def test_calculate_performance_metrics_with_psutil(self, execution_core):
        """Test performance metrics with psutil available."""
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024*1024*100)  # 100MB
        mock_process.cpu_percent.return_value = 15.5
        
        # Mock psutil using patch as a context manager since it's imported in the method
        with patch('psutil.Process', return_value=mock_process):
            start_time = time.time() - 1.0
            metrics = execution_core._calculate_performance_metrics(start_time)
        
            assert 'memory_usage_mb' in metrics
            assert 'cpu_percent' in metrics
            assert metrics['memory_usage_mb'] == 100.0  # 100MB
            assert metrics['cpu_percent'] == 15.5

    @pytest.mark.asyncio
    async def test_get_agent_or_error_success(self, execution_core):
        """Test successful agent retrieval."""
        mock_agent = Mock()
        execution_core.registry.get_async.return_value = mock_agent
        
        result = await execution_core._get_agent_or_error("test_agent")
        assert result == mock_agent

    @pytest.mark.asyncio
    async def test_get_agent_or_error_not_found(self, execution_core):
        """Test agent not found scenario."""
        execution_core.registry.get_async.return_value = None
        
        result = await execution_core._get_agent_or_error("missing_agent")
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "missing_agent not found" in result.error

    @pytest.mark.asyncio
    async def test_collect_metrics_integration(self, execution_core, sample_user_context):
        """Test metrics collection from multiple sources."""
        exec_id = uuid4()
        result = AgentExecutionResult(
            success=True,
            duration=2.5,
            metrics={'custom_metric': 42}
        )
        
        # Mock tracker returning metrics
        execution_core.execution_tracker.collect_metrics.return_value = {
            'tracker_metric': 'value'
        }
        
        metrics = await execution_core._collect_metrics(exec_id, result, sample_user_context, None)
        
        # Verify metrics combination
        assert 'tracker_metric' in metrics
        assert 'custom_metric' in metrics
        assert 'context_size' in metrics
        assert 'result_success' in metrics
        assert 'total_duration_seconds' in metrics
        assert metrics['result_success'] is True
        assert metrics['total_duration_seconds'] == 2.5

    @pytest.mark.asyncio
    async def test_persist_metrics_success(self, execution_core, sample_user_context):
        """Test successful metrics persistence."""
        exec_id = uuid4()
        metrics = {
            'execution_time': 1500,
            'memory_usage': 256.5,
            'string_metric': 'ignored'  # Non-numeric should be ignored
        }
        
        # Mock persistence
        execution_core.persistence = AsyncMock()
        execution_core.persistence.write_performance_metrics = AsyncMock()
        
        await execution_core._persist_metrics(exec_id, metrics, "test_agent", sample_user_context)
        
        # Should be called for each numeric metric
        assert execution_core.persistence.write_performance_metrics.call_count == 2
        
        # Verify calls contain expected data
        calls = execution_core.persistence.write_performance_metrics.call_args_list
        for call in calls:
            args, kwargs = call
            assert args[0] == exec_id  # execution_id
            assert 'agent_name' in args[1]
            assert 'user_id' in args[1]
            assert 'metric_type' in args[1]
            assert 'metric_value' in args[1]

    @pytest.mark.asyncio
    async def test_persist_metrics_error_handling(self, execution_core, sample_user_context):
        """Test metrics persistence error handling."""
        exec_id = uuid4()
        metrics = {'test_metric': 123}
        
        # Mock persistence that fails
        execution_core.persistence = AsyncMock()
        execution_core.persistence.write_performance_metrics.side_effect = Exception("DB Error")
        
        # Should not raise exception
        await execution_core._persist_metrics(exec_id, metrics, "test_agent", sample_user_context)
        
        # Verify attempt was made
        execution_core.persistence.write_performance_metrics.assert_called_once()

    def test_create_websocket_callback_with_bridge(self, execution_core, sample_context):
        """Test WebSocket callback creation when bridge exists."""
        trace_context = Mock(spec=UnifiedTraceContext)
        trace_context.to_websocket_context.return_value = {'trace_id': 'test'}
        
        callback = execution_core._create_websocket_callback(sample_context, trace_context)
        assert callback is not None
        
        # Test callback execution
        asyncio.run(callback({'pulse': 5}))
        execution_core.websocket_bridge.notify_agent_thinking.assert_called_once()

    def test_create_websocket_callback_without_bridge(self):
        """Test WebSocket callback creation when no bridge exists."""
        execution_core = AgentExecutionCore(Mock(), None)  # No websocket bridge
        sample_context = Mock()
        trace_context = Mock()
        
        callback = execution_core._create_websocket_callback(sample_context, trace_context)
        assert callback is None

    @pytest.mark.asyncio
    async def test_execute_with_protection_result_validation(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test that execute_with_protection validates result format."""
        # Agent returns non-standard result
        mock_agent.execute.return_value = "simple string result"
        execution_core._setup_agent_websocket = AsyncMock()
        
        trace_context = Mock(spec=UnifiedTraceContext)
        result = await execution_core._execute_with_protection(
            mock_agent, sample_context, sample_user_context, uuid4(), None, 30.0, trace_context
        )
        
        # Should wrap non-standard result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.duration is not None
        assert result.metrics is not None

    @pytest.mark.asyncio
    async def test_trace_context_propagation(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test trace context creation and propagation."""
        execution_core.registry.get_async.return_value = mock_agent
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        # Test with parent trace context
        parent_trace = Mock(spec=UnifiedTraceContext)
        child_trace = Mock(spec=UnifiedTraceContext)
        parent_trace.propagate_to_child.return_value = child_trace
        child_trace.start_span.return_value = Mock()
        child_trace.to_websocket_context.return_value = {'trace_id': 'child'}
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = parent_trace
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(sample_context, sample_user_context)
        
        # Verify trace propagation
        parent_trace.propagate_to_child.assert_called_once()
        child_trace.start_span.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_heartbeat_disabled_by_design(self, execution_core, sample_context, sample_user_context, mock_agent):
        """Test that heartbeat is disabled as per AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md"""
        execution_core.registry.get_async.return_value = mock_agent
        # Fix: register_execution is now a Mock() method, not AsyncMock
        execution_core.execution_tracker.create_execution = Mock(return_value=str(uuid4()))
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            mock_get_trace.return_value = None
            
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                # Call should succeed without heartbeat
                result = await execution_core.execute_agent(sample_context, sample_user_context)
        
        # Verify execution works without heartbeat
        assert isinstance(result, AgentExecutionResult)
        # Note: We're testing that the system works WITHOUT heartbeat, as designed
        # Heartbeat is disabled to prevent error suppression