"""
Unit Tests for Tool Dispatcher Execution - Batch 2 Priority Tests (tool_dispatcher_execution.py)

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure tool execution engine handles all scenarios correctly
- Value Impact: Prevents tool execution failures that would break agent workflows
- Strategic Impact: Core execution engine that enables reliable tool operations

These tests focus on tool_dispatcher_execution.py validation:
1. Tool execution engine delegation to unified implementation
2. WebSocket manager integration with execution
3. Error handling and state management
4. Response conversion and formatting
5. Interface compliance validation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput,
    ToolResult,
    ToolStatus,
    ToolExecuteResponse
)


class TestToolExecutionEngineUnit(SSotBaseTestCase):
    """Unit tests for tool execution engine."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = Mock()
        
        # Create test engine
        self.execution_engine = ToolExecutionEngine(
            websocket_manager=self.mock_websocket_manager
        )
        
        # Create mock tool
        self.mock_tool = Mock()
        self.mock_tool.name = "execution_test_tool"
        self.mock_tool.description = "Test tool for execution testing"
        
        # Create test tool input
        self.tool_input = ToolInput(
            tool_name="execution_test_tool",
            parameters={"test_param": "test_value"}
        )
        
        # Create mock agent state
        self.mock_state = Mock(spec=DeepAgentState)
        self.mock_state.run_id = "execution_test_run"
        self.mock_state.user_id = "execution_test_user"
    
    def test_engine_initializes_with_websocket_manager(self):
        """Test engine properly initializes with WebSocket manager.
        
        BVJ: Ensures WebSocket events are enabled for real-time updates.
        """
        # Assert engine has WebSocket manager
        assert self.execution_engine._core_engine is not None
        
        # Verify core engine was initialized with WebSocket manager
        assert hasattr(self.execution_engine, '_core_engine')
        
        self.record_metric("engine_initialization", "success")
    
    def test_engine_initializes_without_websocket_manager(self):
        """Test engine can initialize without WebSocket manager.
        
        BVJ: Allows operation in environments where WebSocket isn't available.
        """
        # Act
        engine_no_ws = ToolExecutionEngine(websocket_manager=None)
        
        # Assert
        assert engine_no_ws._core_engine is not None
        self.record_metric("engine_no_websocket_init", "success")
    
    @patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine')
    @pytest.mark.asyncio
    async def test_execute_tool_with_input_delegates_correctly(self, mock_unified_engine_class):
        """Test execute_tool_with_input delegates to unified engine.
        
        BVJ: Ensures consistent tool execution across all dispatch paths.
        """
        # Arrange
        mock_unified_engine = Mock()
        mock_unified_engine_class.return_value = mock_unified_engine
        
        expected_result = ToolResult(
            tool_name="execution_test_tool",
            status=ToolStatus.SUCCESS,
            result="Test execution successful",
            metadata={"execution_time_ms": 150}
        )
        mock_unified_engine.execute_tool_with_input = AsyncMock(return_value=expected_result)
        
        # Create new engine to use mocked unified engine
        engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
        
        kwargs = {"test_param": "test_value", "additional_param": 42}
        
        # Act
        result = await engine.execute_tool_with_input(
            self.tool_input,
            self.mock_tool,
            kwargs
        )
        
        # Assert
        mock_unified_engine.execute_tool_with_input.assert_called_once_with(
            self.tool_input,
            self.mock_tool,
            kwargs
        )
        assert result == expected_result
        
        self.record_metric("delegation_to_unified_engine", "validated")
    
    @patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine')
    @pytest.mark.asyncio
    async def test_execute_with_state_converts_response_correctly(self, mock_unified_engine_class):
        """Test execute_with_state properly converts unified engine response.
        
        BVJ: Ensures response format compatibility across different interfaces.
        """
        # Arrange
        mock_unified_engine = Mock()
        mock_unified_engine_class.return_value = mock_unified_engine
        
        # Mock successful response from unified engine
        unified_response = {
            "success": True,
            "result": {"analysis": "completed", "confidence": 0.95},
            "metadata": {"execution_time_ms": 200, "tool_version": "1.0"}
        }
        mock_unified_engine.execute_with_state = AsyncMock(return_value=unified_response)
        
        # Create engine and test parameters
        engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
        tool_name = "execution_test_tool"
        parameters = {"data": "test_data", "options": ["opt1", "opt2"]}
        run_id = "test_run_123"
        
        # Act
        result = await engine.execute_with_state(
            self.mock_tool,
            tool_name,
            parameters,
            self.mock_state,
            run_id
        )
        
        # Assert unified engine was called correctly
        mock_unified_engine.execute_with_state.assert_called_once_with(
            self.mock_tool,
            tool_name,
            parameters,
            self.mock_state,
            run_id
        )
        
        # Assert response conversion is correct
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        assert isinstance(result, ToolDispatchResponse)
        assert result.success is True
        assert result.result == {"analysis": "completed", "confidence": 0.95}
        assert result.error is None
        assert result.metadata == {"execution_time_ms": 200, "tool_version": "1.0"}
        
        self.record_metric("state_execution_response_conversion", "validated")
    
    @patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine')
    @pytest.mark.asyncio
    async def test_execute_with_state_handles_error_response(self, mock_unified_engine_class):
        """Test execute_with_state properly converts error responses.
        
        BVJ: Ensures error information is properly communicated to users.
        """
        # Arrange
        mock_unified_engine = Mock()
        mock_unified_engine_class.return_value = mock_unified_engine
        
        # Mock error response from unified engine
        unified_error_response = {
            "success": False,
            "error": "Tool execution failed: Connection timeout",
            "metadata": {"execution_time_ms": 5000, "timeout_reached": True}
        }
        mock_unified_engine.execute_with_state = AsyncMock(return_value=unified_error_response)
        
        # Create engine
        engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
        
        # Act
        result = await engine.execute_with_state(
            self.mock_tool,
            "failing_tool",
            {"data": "test"},
            self.mock_state,
            "error_test_run"
        )
        
        # Assert error response conversion
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        assert isinstance(result, ToolDispatchResponse)
        assert result.success is False
        assert result.result is None
        assert result.error == "Tool execution failed: Connection timeout"
        assert result.metadata["timeout_reached"] is True
        
        self.record_metric("error_response_conversion", "validated")


class TestToolExecutionEngineInterface(SSotBaseTestCase):
    """Unit tests for tool execution engine interface compliance."""
    
    def setup_method(self, method):
        """Set up interface compliance test environment.""" 
        super().setup_method(method)
        
        # Create engine for testing
        self.execution_engine = ToolExecutionEngine()
        
    @patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine')
    @pytest.mark.asyncio
    async def test_execute_tool_interface_method(self, mock_unified_engine_class):
        """Test execute_tool interface method delegates correctly.
        
        BVJ: Ensures interface compliance for different tool execution patterns.
        """
        # Arrange
        mock_unified_engine = Mock()
        mock_unified_engine_class.return_value = mock_unified_engine
        
        expected_response = ToolExecuteResponse(
            success=True,
            result="Interface test successful",
            metadata={"interface_version": "1.0"}
        )
        mock_unified_engine.execute_tool = AsyncMock(return_value=expected_response)
        
        # Create engine
        engine = ToolExecutionEngine(websocket_manager=None)
        
        tool_name = "interface_test_tool"
        parameters = {"interface_param": "interface_value"}
        
        # Act
        result = await engine.execute_tool(tool_name, parameters)
        
        # Assert
        mock_unified_engine.execute_tool.assert_called_once_with(
            tool_name,
            parameters
        )
        assert result == expected_response
        
        self.record_metric("interface_method_delegation", "validated")
    
    def test_engine_implements_tool_execution_engine_interface(self):
        """Test engine properly implements ToolExecutionEngineInterface.
        
        BVJ: Ensures compatibility with different tool dispatch implementations.
        """
        # Import interface
        from netra_backend.app.schemas.tool import ToolExecutionEngineInterface
        
        # Assert engine implements interface
        assert isinstance(self.execution_engine, ToolExecutionEngineInterface)
        
        # Verify interface methods exist
        assert hasattr(self.execution_engine, 'execute_tool')
        assert callable(self.execution_engine.execute_tool)
        
        assert hasattr(self.execution_engine, 'execute_tool_with_input')
        assert callable(self.execution_engine.execute_tool_with_input)
        
        assert hasattr(self.execution_engine, 'execute_with_state')
        assert callable(self.execution_engine.execute_with_state)
        
        self.record_metric("interface_compliance", "validated")
    
    @patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine')
    @pytest.mark.asyncio
    async def test_websocket_manager_passed_to_unified_engine(self, mock_unified_engine_class):
        """Test WebSocket manager is properly passed to unified engine.
        
        BVJ: Ensures WebSocket events are enabled for tool execution monitoring.
        """
        # Arrange
        mock_websocket_manager = Mock()
        mock_websocket_manager.send_event = AsyncMock(return_value=True)
        
        # Act
        engine = ToolExecutionEngine(websocket_manager=mock_websocket_manager)
        
        # Assert unified engine was created with WebSocket manager
        mock_unified_engine_class.assert_called_once_with(
            websocket_manager=mock_websocket_manager
        )
        
        self.record_metric("websocket_manager_propagation", "validated")
    
    def test_tool_execution_engine_has_core_engine_attribute(self):
        """Test execution engine maintains reference to core engine.
        
        BVJ: Enables access to core engine functionality when needed.
        """
        # Assert core engine attribute exists
        assert hasattr(self.execution_engine, '_core_engine')
        assert self.execution_engine._core_engine is not None
        
        self.record_metric("core_engine_reference", "maintained")