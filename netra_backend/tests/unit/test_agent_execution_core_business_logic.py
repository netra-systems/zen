"""Unit Tests for AgentExecutionCore Business Logic

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable AI agent execution for chat functionality
- Value Impact: Prevents agent death scenarios that block $120K+ MRR
- Strategic Impact: Core platform functionality that delivers AI value

CRITICAL TEST PURPOSE:
These unit tests validate the business logic of AgentExecutionCore that manages
the lifecycle of agent execution with death detection and recovery.

Test Coverage:
- Agent execution lifecycle management 
- Death detection and error boundaries
- WebSocket event coordination
- Timeout and heartbeat handling
- Result validation and error handling
"""

import pytest
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from test_framework.ssot.mocks import MockFactory


class TestAgentExecutionCoreBusiness:
    """Unit tests for AgentExecutionCore business logic validation."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_factory = MockFactory()
        self.mock_registry = self.mock_factory.create_mock()
        self.mock_websocket_bridge = self.mock_factory.create_async_mock()
        
        # Create AgentExecutionCore instance
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        self.mock_factory.cleanup()
    
    @pytest.mark.unit
    def test_agent_execution_core_initialization(self):
        """Test AgentExecutionCore proper initialization."""
        # Arrange & Act - initialization happens in setup_method
        
        # Assert - verify core components are initialized
        assert self.execution_core.registry is not None
        assert self.execution_core.websocket_bridge is not None
        assert self.execution_core.execution_tracker is not None
        assert hasattr(self.execution_core, 'DEFAULT_TIMEOUT')
        assert hasattr(self.execution_core, 'HEARTBEAT_INTERVAL')
        assert self.execution_core.DEFAULT_TIMEOUT == 25.0  # Changed from 30.0 for faster user feedback (Issue #158)
        assert self.execution_core.HEARTBEAT_INTERVAL == 5.0
    
    @pytest.mark.unit
    async def test_execute_agent_success_flow(self):
        """Test successful agent execution flow with proper lifecycle management."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=uuid.uuid4(),
            correlation_id="test-correlation"
        )
        
        state = DeepAgentState(
            user_id="test-user",
            thread_id="test-thread"
        )
        
        # Mock successful agent
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.execute = AsyncMock(return_value={"result": "success", "status": "completed"})
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        self.execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify successful execution
        assert isinstance(result, AgentExecutionResult)
        assert result.success == True
        assert result.agent_name == "test_agent"
        assert result.duration is not None
        
        # Verify execution tracker lifecycle
        self.execution_core.execution_tracker.register_execution.assert_called_once()
        self.execution_core.execution_tracker.start_execution.assert_called_once()
        self.execution_core.execution_tracker.complete_execution.assert_called_once()
        
        # Verify WebSocket events sent
        self.mock_websocket_bridge.notify_agent_thinking.assert_called()
    
    @pytest.mark.unit
    async def test_execute_agent_not_found_error(self):
        """Test agent execution when agent not found in registry."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="nonexistent_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock registry returning None (agent not found)
        self.mock_registry.get.return_value = None
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify error handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success == False
        assert result.agent_name == "nonexistent_agent"
        assert "not found" in result.error.lower()
        
        # Verify error notification sent
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        
        # Verify execution marked as failed
        self.execution_core.execution_tracker.complete_execution.assert_called_once()
    
    @pytest.mark.unit 
    async def test_execute_agent_timeout_handling(self):
        """Test agent execution timeout handling and protection."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="slow_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock agent that takes too long
        mock_agent = self.mock_factory.create_async_mock()
        
        async def slow_execute(*args, **kwargs):
            import asyncio
            await asyncio.sleep(2)  # Longer than test timeout
            return {"result": "too_slow"}
            
        mock_agent.execute = slow_execute
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        self.execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Act - execute with short timeout
        result = await self.execution_core.execute_agent(context, state, timeout=0.1)
        
        # Assert - verify timeout handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success == False
        assert result.agent_name == "slow_agent"
        assert "timeout" in result.error.lower()
        assert result.duration is not None
        assert result.duration > 0.1  # Should have actual execution time
    
    @pytest.mark.unit
    async def test_execute_agent_death_detection(self):
        """Test agent death detection when agent returns None."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="dying_agent", 
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock agent that returns None (dead agent signature)
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.execute = AsyncMock(return_value=None)
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        self.execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify death detection
        assert isinstance(result, AgentExecutionResult)
        assert result.success == False
        assert result.agent_name == "dying_agent"
        assert "died silently" in result.error.lower()
        
        # Verify execution marked as failed
        self.execution_core.execution_tracker.complete_execution.assert_called_once()
    
    @pytest.mark.unit
    async def test_execute_agent_exception_handling(self):
        """Test exception handling during agent execution."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="error_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock agent that throws exception
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.execute = AsyncMock(side_effect=RuntimeError("Test agent error"))
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify exception handling
        assert isinstance(result, AgentExecutionResult)
        assert result.success == False
        assert result.agent_name == "error_agent"
        assert "Agent execution failed" in result.error
        assert "Test agent error" in result.error
        
        # Verify error notification sent
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        
        # Verify execution marked as failed
        self.execution_core.execution_tracker.complete_execution.assert_called_once()
    
    @pytest.mark.unit
    async def test_websocket_bridge_integration(self):
        """Test WebSocket bridge integration for user feedback."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="feedback_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock successful agent
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.execute = AsyncMock(return_value={"result": "success"})
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        self.execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify WebSocket events sent for user feedback
        assert result.success == True
        
        # Verify thinking events sent (business value: user sees AI working)
        thinking_calls = self.mock_websocket_bridge.notify_agent_thinking.call_args_list
        assert len(thinking_calls) >= 2  # Should have multiple thinking updates
        
        # Verify thinking events contain meaningful content
        for call in thinking_calls:
            args, kwargs = call
            assert "run_id" in kwargs
            assert "agent_name" in kwargs
            assert "reasoning" in kwargs
            assert kwargs["reasoning"] is not None
            assert len(kwargs["reasoning"]) > 0
    
    @pytest.mark.unit
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation for execution monitoring."""
        # Arrange
        start_time = time.time() - 1.5  # Simulate 1.5 second execution
        
        # Act
        metrics = self.execution_core._calculate_performance_metrics(start_time)
        
        # Assert - verify metrics structure
        assert "execution_time_ms" in metrics
        assert "start_timestamp" in metrics 
        assert "end_timestamp" in metrics
        
        # Verify execution time is reasonable
        execution_time_ms = metrics["execution_time_ms"]
        assert execution_time_ms > 1000  # At least 1 second
        assert execution_time_ms < 2000  # Less than 2 seconds
        
        # Verify timestamps make sense
        assert metrics["start_timestamp"] == start_time
        assert metrics["end_timestamp"] > metrics["start_timestamp"]
    
    @pytest.mark.unit
    async def test_agent_websocket_setup(self):
        """Test WebSocket setup on agent for event propagation."""
        # Arrange
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.set_websocket_bridge = Mock()
        mock_agent.websocket_bridge = None
        
        context = AgentExecutionContext(
            agent_name="websocket_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState(user_id="test-user")
        
        # Mock trace context
        from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
        trace_context = UnifiedTraceContext(user_id="test-user")
        
        # Act
        await self.execution_core._setup_agent_websocket(mock_agent, context, state, trace_context)
        
        # Assert - verify WebSocket setup
        mock_agent.set_websocket_bridge.assert_called_once()
        call_args = mock_agent.set_websocket_bridge.call_args
        assert call_args[0][0] == self.mock_websocket_bridge  # First arg is bridge
        assert call_args[0][1] == context.run_id  # Second arg is run_id
        
        # Verify user_id was set
        assert hasattr(mock_agent, '_user_id')
        assert mock_agent._user_id == "test-user"
    
    @pytest.mark.unit
    async def test_result_validation_and_wrapping(self):
        """Test result validation and proper wrapping of agent responses."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="result_agent",
            run_id=uuid.uuid4()
        )
        state = DeepAgentState()
        
        # Mock agent returning non-standard result
        mock_agent = self.mock_factory.create_async_mock()
        mock_agent.execute = AsyncMock(return_value="simple string result")
        self.mock_registry.get.return_value = mock_agent
        
        # Mock execution tracker
        mock_exec_id = uuid.uuid4()
        self.execution_core.execution_tracker.register_execution = AsyncMock(return_value=mock_exec_id)
        self.execution_core.execution_tracker.start_execution = AsyncMock()
        self.execution_core.execution_tracker.complete_execution = AsyncMock()
        self.execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Act
        result = await self.execution_core.execute_agent(context, state)
        
        # Assert - verify result wrapping
        assert isinstance(result, AgentExecutionResult)
        assert result.success == True
        assert result.agent_name == "result_agent"
        assert result.data == "simple string result"  # Original result preserved in data field
        assert result.duration is not None
        assert result.metrics is not None