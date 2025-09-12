"""
Agent Execution Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise)
- Business Goal: Ensure core agent execution logic is reliable and performant
- Value Impact: Unit tests validate critical execution paths that deliver AI insights to users
- Strategic Impact: Foundation layer testing for the entire agent execution pipeline

This test suite validates the Agent Execution Core functionality through targeted
unit testing, focusing on individual components and their business logic without
external dependencies.

CRITICAL REQUIREMENTS VALIDATED:
- Agent execution lifecycle management
- Timeout and error handling mechanisms
- WebSocket notification integration
- Execution state tracking and validation
- Agent registry integration patterns
- Trace context propagation
- Performance metrics collection
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Core imports for agent execution testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
from netra_backend.app.core.execution_tracker import ExecutionState


class MockAgent:
    """Mock agent for unit testing."""
    
    def __init__(self, name: str = "MockAgent", should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.execution_count = 0
        self.websocket_bridge = None
        self.execution_engine = None
        self._user_id = None
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> Dict[str, Any]:
        """Mock agent execution method."""
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"Mock agent {self.name} execution failed")
        
        # Simulate some processing time
        await asyncio.sleep(0.01)
        
        return {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "run_id": run_id,
            "business_value": "Generated insights successfully"
        }
    
    def set_websocket_bridge(self, bridge, run_id):
        """Set websocket bridge for testing."""
        self.websocket_bridge = bridge
        self.run_id = run_id
    
    def set_trace_context(self, trace_context):
        """Set trace context for testing."""
        self.trace_context = trace_context


class TestAgentExecutionCoreUnit(SSotBaseTestCase):
    """Unit tests for Agent Execution Core functionality."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Create mock registry
        self.mock_registry = MagicMock()
        self.mock_registry.get.return_value = None
        
        # Create mock websocket bridge
        self.mock_websocket_bridge = AsyncMock()
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        self.mock_websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create execution core instance
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create test context and state
        self.test_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id="test_thread_456",
            user_id="test_user_123",
            agent_name="test_agent",
            retry_count=0
        )
        
        self.test_state = DeepAgentState(
            user_id="test_user_123",
            thread_id="test_thread_456",
            agent_context={"user_request": "Test request"}
        )

    @pytest.mark.unit
    async def test_basic_agent_execution_success(self):
        """
        Test basic successful agent execution.
        
        BVJ: Validates core execution path works correctly for delivering user value.
        """
        # Arrange
        mock_agent = MockAgent("TestSuccessAgent")
        self.mock_registry.get.return_value = mock_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0
        assert result.metrics is not None
        assert mock_agent.execution_count == 1
        
        # Verify WebSocket notifications were sent
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()

    @pytest.mark.unit
    async def test_agent_execution_with_failure(self):
        """
        Test agent execution with simulated failure.
        
        BVJ: Ensures proper error handling maintains system stability when agents fail.
        """
        # Arrange
        failing_agent = MockAgent("FailingAgent", should_fail=True)
        self.mock_registry.get.return_value = failing_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is False
        assert result.error is not None
        assert "execution failed" in result.error
        assert result.duration is not None
        
        # Verify error notification was sent
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.unit
    async def test_agent_not_found_handling(self):
        """
        Test handling when requested agent is not found in registry.
        
        BVJ: Ensures graceful handling of configuration errors that could impact user experience.
        """
        # Arrange - registry returns None (agent not found)
        self.mock_registry.get.return_value = None
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is False
        assert "not found" in result.error
        
        # Verify error notification was sent
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.unit
    async def test_execution_timeout_handling(self):
        """
        Test execution timeout handling.
        
        BVJ: Ensures system remains responsive and doesn't hang on slow operations.
        """
        # Arrange
        slow_agent = MockAgent("SlowAgent")
        
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(2.0)  # Simulate slow execution
            return {"success": True}
            
        slow_agent.execute = slow_execute
        self.mock_registry.get.return_value = slow_agent
        
        # Act - use very short timeout
        start_time = time.time()
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=0.1  # 100ms timeout
        )
        end_time = time.time()
        
        # Assert
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert (end_time - start_time) < 0.5  # Should timeout quickly
        
        # Verify error notification was sent
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.unit
    async def test_trace_context_propagation(self):
        """
        Test trace context creation and propagation.
        
        BVJ: Enables end-to-end tracing for debugging and performance optimization.
        """
        # Arrange
        mock_agent = MockAgent("TracingAgent")
        self.mock_registry.get.return_value = mock_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            # Create parent trace context
            parent_trace = UnifiedTraceContext(
                user_id="trace_user",
                thread_id="trace_thread",
                correlation_id="trace_corr_123"
            )
            mock_get_trace.return_value = parent_trace
            
            # Act
            result = await self.execution_core.execute_agent(
                context=self.test_context,
                state=self.test_state,
                timeout=5.0
            )
            
            # Assert
            assert result.success is True
            # Verify trace context was used
            mock_get_trace.assert_called_once()

    @pytest.mark.unit
    async def test_websocket_bridge_integration(self):
        """
        Test WebSocket bridge integration and event notifications.
        
        BVJ: Ensures real-time user feedback for better engagement and transparency.
        """
        # Arrange
        mock_agent = MockAgent("WSAgent")
        self.mock_registry.get.return_value = mock_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is True
        
        # Verify all required WebSocket events were sent
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Verify websocket bridge was set on agent
        assert mock_agent.websocket_bridge is not None

    @pytest.mark.unit
    async def test_execution_state_validation(self):
        """
        Test execution state validation and lifecycle management.
        
        BVJ: Ensures proper state tracking for system observability and debugging.
        """
        # Arrange
        mock_agent = MockAgent("StateAgent")
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        with patch.object(self.execution_core.execution_tracker, 'register_execution') as mock_register, \
             patch.object(self.execution_core.execution_tracker, 'start_execution') as mock_start, \
             patch.object(self.execution_core.execution_tracker, 'complete_execution') as mock_complete:
            
            mock_exec_id = uuid.uuid4()
            mock_register.return_value = mock_exec_id
            
            # Act
            result = await self.execution_core.execute_agent(
                context=self.test_context,
                state=self.test_state,
                timeout=5.0
            )
            
            # Assert
            assert result.success is True
            
            # Verify execution tracking lifecycle
            mock_register.assert_called_once()
            mock_start.assert_called_once_with(mock_exec_id)
            mock_complete.assert_called_once()

    @pytest.mark.unit
    def test_get_agent_or_error_success(self):
        """
        Test successful agent retrieval from registry.
        
        BVJ: Validates agent discovery mechanism works correctly.
        """
        # Arrange
        mock_agent = MockAgent("RegistryAgent")
        self.mock_registry.get.return_value = mock_agent
        
        # Act
        result = self.execution_core._get_agent_or_error("test_agent")
        
        # Assert
        assert result == mock_agent
        self.mock_registry.get.assert_called_once_with("test_agent")

    @pytest.mark.unit
    def test_get_agent_or_error_not_found(self):
        """
        Test agent retrieval when agent is not found.
        
        BVJ: Ensures proper error handling for missing agents.
        """
        # Arrange
        self.mock_registry.get.return_value = None
        
        # Act
        result = self.execution_core._get_agent_or_error("missing_agent")
        
        # Assert
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.unit
    def test_calculate_performance_metrics(self):
        """
        Test performance metrics calculation.
        
        BVJ: Enables performance monitoring and optimization for better user experience.
        """
        # Arrange
        start_time = time.time() - 1.5  # 1.5 seconds ago
        
        # Act
        metrics = self.execution_core._calculate_performance_metrics(start_time)
        
        # Assert
        assert isinstance(metrics, dict)
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics
        
        # Verify timing calculations
        assert metrics['execution_time_ms'] >= 1400  # Should be around 1500ms
        assert metrics['execution_time_ms'] <= 1600
        assert metrics['start_timestamp'] == start_time

    @pytest.mark.unit
    async def test_setup_agent_websocket_propagation(self):
        """
        Test WebSocket context setup and propagation to agents.
        
        BVJ: Ensures agents can send real-time updates for better user experience.
        """
        # Arrange
        mock_agent = MockAgent("WSSetupAgent")
        trace_context = UnifiedTraceContext(
            user_id="ws_user",
            thread_id="ws_thread",
            correlation_id="ws_corr"
        )
        
        # Add methods to mock agent to test different setup paths
        mock_agent.set_websocket_bridge = MagicMock()
        mock_agent.set_trace_context = MagicMock()
        mock_agent.execution_engine = MagicMock()
        mock_agent.execution_engine.set_websocket_bridge = MagicMock()
        
        # Act
        await self.execution_core._setup_agent_websocket(
            agent=mock_agent,
            context=self.test_context,
            state=self.test_state,
            trace_context=trace_context
        )
        
        # Assert
        # Verify WebSocket bridge was set via preferred method
        mock_agent.set_websocket_bridge.assert_called_once_with(
            self.mock_websocket_bridge, 
            self.test_context.run_id
        )
        
        # Verify trace context was set
        mock_agent.set_trace_context.assert_called_once_with(trace_context)
        
        # Verify user ID was set
        assert mock_agent._user_id == self.test_state.user_id

    @pytest.mark.unit
    async def test_agent_execution_with_none_result(self):
        """
        Test handling of agent execution returning None (dead agent detection).
        
        BVJ: Prevents silent failures that could impact user experience.
        """
        # Arrange
        dead_agent = MockAgent("DeadAgent")
        
        async def return_none(*args, **kwargs):
            return None  # Simulate dead agent
            
        dead_agent.execute = return_none
        self.mock_registry.get.return_value = dead_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.test_context,
            state=self.test_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is False
        assert "died silently" in result.error
        
        # Verify error notification
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.unit
    async def test_metrics_collection_and_persistence(self):
        """
        Test metrics collection and persistence workflow.
        
        BVJ: Enables performance monitoring and system optimization.
        """
        # Arrange
        mock_agent = MockAgent("MetricsAgent")
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.execution_core, '_collect_metrics') as mock_collect, \
             patch.object(self.execution_core, '_persist_metrics') as mock_persist:
            
            mock_collect.return_value = {
                'execution_time_ms': 150,
                'memory_usage_mb': 45.2,
                'context_size': 1024
            }
            
            # Act
            result = await self.execution_core.execute_agent(
                context=self.test_context,
                state=self.test_state,
                timeout=5.0
            )
            
            # Assert
            assert result.success is True
            
            # Verify metrics collection and persistence
            mock_collect.assert_called_once()
            mock_persist.assert_called_once()

    def cleanup_resources(self):
        """Clean up test resources."""
        super().cleanup_resources()
        # Clean up any additional resources if needed
        self.execution_core = None