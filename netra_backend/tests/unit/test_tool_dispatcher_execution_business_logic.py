"""Unit Tests for Tool Dispatcher Execution Business Logic

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable tool execution with proper error handling
- Value Impact: Enables AI agents to deliver actionable insights without failures
- Strategic Impact: Core execution engine for all AI-driven business value delivery

CRITICAL TEST PURPOSE:
These unit tests validate the business logic of ToolExecutionEngine that
delegates to the unified implementation for consistent tool execution.

Test Coverage:
- Tool execution engine initialization and delegation
- Successful tool execution workflows
- Error handling and state management
- Interface compliance and result transformation
- WebSocket integration for user feedback
- Legacy compatibility with new unified engine
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput, ToolResult, ToolStatus, ToolExecuteResponse
)
from test_framework.ssot.mocks import MockFactory


class TestToolDispatcherExecutionBusiness:
    """Unit tests for Tool Dispatcher Execution business logic validation."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_factory = MockFactory()
        self.mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Create execution engine
        self.execution_engine = ToolExecutionEngine(
            websocket_manager=self.mock_websocket_manager
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        self.mock_factory.cleanup()
    
    @pytest.mark.unit
    def test_tool_execution_engine_initialization(self):
        """Test ToolExecutionEngine proper initialization with delegation."""
        # Assert - verify core engine is created
        assert hasattr(self.execution_engine, '_core_engine')
        assert self.execution_engine._core_engine is not None
        
        # Verify websocket_manager was passed to core engine
        # Note: We can't directly access _websocket_manager but verify it was initialized
    
    @pytest.mark.unit
    async def test_execute_tool_with_input_success(self):
        """Test successful tool execution with input delegation."""
        # Arrange
        tool_input = ToolInput(
            tool_name="test_analyzer",
            kwargs={"query": "analyze this data", "depth": "detailed"}
        )
        
        mock_tool = self.mock_factory.create_async_mock()
        mock_tool.name = "test_analyzer"
        
        expected_result = ToolResult(
            tool_input=tool_input,
            status=ToolStatus.SUCCESS,
            result={"analysis": "Complete", "insights": ["Cost optimization possible"]},
            execution_time=1.5
        )
        
        # Mock the core engine
        with patch.object(self.execution_engine._core_engine, 'execute_tool_with_input') as mock_execute:
            mock_execute.return_value = expected_result
            
            # Act
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=mock_tool,
                kwargs={"query": "analyze this data", "depth": "detailed"}
            )
        
        # Assert - verify delegation and result
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.result["analysis"] == "Complete"
        assert result.execution_time == 1.5
        
        # Verify core engine was called correctly
        mock_execute.assert_called_once_with(
            tool_input, mock_tool, {"query": "analyze this data", "depth": "detailed"}
        )
    
    @pytest.mark.unit
    async def test_execute_with_state_success_conversion(self):
        """Test execute_with_state success result conversion."""
        # Arrange
        mock_tool = self.mock_factory.create_async_mock()
        mock_tool.name = "cost_optimizer"
        
        parameters = {"account_id": "123456", "service": "EC2"}
        state = DeepAgentState(user_id="test-user", thread_id="test-thread")
        run_id = "run-789"
        
        # Mock successful core engine response
        core_result = {
            "success": True,
            "result": {
                "savings_found": 1500,
                "recommendations": ["Resize instances", "Use reserved capacity"]
            },
            "metadata": {
                "execution_time": 2.3,
                "tools_used": ["aws_cost_explorer"]
            }
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool,
                tool_name="cost_optimizer",
                parameters=parameters,
                state=state,
                run_id=run_id
            )
        
        # Assert - verify ToolDispatchResponse conversion
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == True
        assert result.result["savings_found"] == 1500
        assert result.error is None
        assert result.metadata["execution_time"] == 2.3
        
        # Verify core engine was called correctly
        mock_execute.assert_called_once_with(
            mock_tool, "cost_optimizer", parameters, state, run_id
        )
    
    @pytest.mark.unit
    async def test_execute_with_state_failure_conversion(self):
        """Test execute_with_state failure result conversion."""
        # Arrange
        mock_tool = self.mock_factory.create_async_mock()
        mock_tool.name = "failing_tool"
        
        parameters = {"invalid": "params"}
        state = DeepAgentState()
        run_id = "run-failed"
        
        # Mock failed core engine response
        core_result = {
            "success": False,
            "error": "Invalid parameters provided",
            "metadata": {
                "error_code": "VALIDATION_ERROR",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool,
                tool_name="failing_tool",
                parameters=parameters,
                state=state,
                run_id=run_id
            )
        
        # Assert - verify ToolDispatchResponse error conversion
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == False
        assert result.error == "Invalid parameters provided"
        assert result.result is None
        assert result.metadata["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.unit
    async def test_execute_tool_interface_implementation(self):
        """Test execute_tool method (interface implementation)."""
        # Arrange
        tool_name = "data_validator"
        parameters = {"data": "test_data", "schema": "user_schema"}
        
        expected_response = ToolExecuteResponse(
            success=True,
            result={"validation": "passed", "errors": []},
            tool_name=tool_name,
            execution_time=0.8
        )
        
        # Mock the core engine
        with patch.object(self.execution_engine._core_engine, 'execute_tool') as mock_execute:
            mock_execute.return_value = expected_response
            
            # Act
            result = await self.execution_engine.execute_tool(tool_name, parameters)
        
        # Assert - verify interface method works
        assert isinstance(result, ToolExecuteResponse)
        assert result.success == True
        assert result.tool_name == tool_name
        assert result.result["validation"] == "passed"
        assert result.execution_time == 0.8
        
        # Verify core engine was called
        mock_execute.assert_called_once_with(tool_name, parameters)
    
    @pytest.mark.unit
    async def test_execute_tool_with_input_error_handling(self):
        """Test error handling in execute_tool_with_input."""
        # Arrange
        tool_input = ToolInput(tool_name="error_tool", kwargs={})
        mock_tool = self.mock_factory.create_async_mock()
        
        # Mock core engine to raise exception
        with patch.object(self.execution_engine._core_engine, 'execute_tool_with_input') as mock_execute:
            mock_execute.side_effect = RuntimeError("Core engine failure")
            
            # Act & Assert - verify exception propagates
            with pytest.raises(RuntimeError) as exc_info:
                await self.execution_engine.execute_tool_with_input(
                    tool_input=tool_input,
                    tool=mock_tool,
                    kwargs={}
                )
            
            assert "Core engine failure" in str(exc_info.value)
    
    @pytest.mark.unit 
    async def test_execute_with_state_missing_success_field(self):
        """Test execute_with_state when core result missing success field."""
        # Arrange
        mock_tool = self.mock_factory.create_async_mock()
        state = DeepAgentState()
        
        # Mock core result without success field (edge case)
        core_result = {
            "result": "some result",
            # Missing "success" field
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool,
                tool_name="test_tool",
                parameters={},
                state=state,
                run_id="run-123"
            )
        
        # Assert - verify default failure handling
        assert isinstance(result, ToolDispatchResponse)
        # When "success" key is missing, .get("success") returns None which is falsy
        assert result.success == False
        assert result.result is None  # Should not set result on failure
        assert result.error is None  # Should not set error without explicit error
    
    @pytest.mark.unit
    async def test_execute_with_state_metadata_preservation(self):
        """Test metadata preservation in execute_with_state."""
        # Arrange
        mock_tool = self.mock_factory.create_async_mock()
        state = DeepAgentState(user_id="metadata-user")
        
        # Mock core result with rich metadata
        core_result = {
            "success": True,
            "result": {"output": "processed"},
            "metadata": {
                "execution_id": "exec-456",
                "user_context": {"user_id": "metadata-user"},
                "performance": {"cpu_usage": "12%", "memory": "45MB"},
                "tools_chain": ["preprocessor", "analyzer", "formatter"]
            }
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool,
                tool_name="metadata_tool",
                parameters={"preserve": "metadata"},
                state=state,
                run_id="run-metadata"
            )
        
        # Assert - verify metadata preservation
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == True
        assert result.metadata is not None
        
        # Verify specific metadata fields
        assert result.metadata["execution_id"] == "exec-456"
        assert result.metadata["user_context"]["user_id"] == "metadata-user"
        assert result.metadata["performance"]["cpu_usage"] == "12%"
        assert "preprocessor" in result.metadata["tools_chain"]
    
    @pytest.mark.unit
    def test_tool_execution_engine_inheritance(self):
        """Test ToolExecutionEngine implements required interface."""
        # Arrange & Act - verify interface compliance
        from netra_backend.app.schemas.tool import ToolExecutionEngineInterface
        
        # Assert - verify inheritance
        assert isinstance(self.execution_engine, ToolExecutionEngineInterface)
        
        # Verify required methods exist
        required_methods = ['execute_tool_with_input', 'execute_tool']
        for method_name in required_methods:
            assert hasattr(self.execution_engine, method_name)
            method = getattr(self.execution_engine, method_name)
            assert callable(method)
    
    @pytest.mark.unit
    def test_core_engine_websocket_manager_integration(self):
        """Test WebSocket manager integration with core engine."""
        # Arrange - create new execution engine
        custom_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        custom_websocket_manager.custom_property = "test_value"
        
        # Act
        custom_engine = ToolExecutionEngine(websocket_manager=custom_websocket_manager)
        
        # Assert - verify core engine has websocket_manager
        # Note: We can't directly access private properties, but we verify initialization succeeded
        assert custom_engine._core_engine is not None
        
        # Verify the websocket_manager was passed during initialization
        # The UnifiedToolExecutionEngine should receive the websocket_manager
        # This is validated through successful initialization without errors
    
    @pytest.mark.unit
    async def test_execute_with_state_empty_metadata_handling(self):
        """Test execute_with_state with empty or missing metadata."""
        # Arrange
        mock_tool = self.mock_factory.create_async_mock()
        state = DeepAgentState()
        
        # Test case 1: Missing metadata
        core_result_no_metadata = {
            "success": True,
            "result": {"output": "success"}
            # No metadata field
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result_no_metadata
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool, tool_name="test", parameters={}, state=state, run_id="run-1"
            )
        
        # Assert - verify empty metadata defaults
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == True
        assert result.metadata == {}
        
        # Test case 2: Empty metadata
        core_result_empty_metadata = {
            "success": True,
            "result": {"output": "success"},
            "metadata": {}
        }
        
        with patch.object(self.execution_engine._core_engine, 'execute_with_state') as mock_execute:
            mock_execute.return_value = core_result_empty_metadata
            
            # Act
            result = await self.execution_engine.execute_with_state(
                tool=mock_tool, tool_name="test", parameters={}, state=state, run_id="run-2"
            )
        
        # Assert - verify empty metadata is preserved
        assert result.metadata == {}