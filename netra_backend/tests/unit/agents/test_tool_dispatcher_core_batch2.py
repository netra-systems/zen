"""
Unit Tests for Tool Dispatcher Core - Batch 2 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure core dispatcher logic provides reliable foundation
- Value Impact: Prevents core tool execution failures affecting all agent workflows  
- Strategic Impact: Foundation layer enabling secure multi-user tool dispatching

Focus Areas:
1. Factory method patterns and user isolation enforcement
2. Core dispatch logic and error handling
3. WebSocket integration and event emission
4. Permission validation and security boundaries
5. Component initialization and lifecycle management
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from netra_backend.app.agents.state import DeepAgentState


class TestToolDispatcherCoreUnit(SSotBaseTestCase):
    """Unit tests for core tool dispatcher functionality."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "core_test_user"
        self.mock_user_context.run_id = "core_test_run"
        self.mock_user_context.thread_id = "core_test_thread"
        self.mock_user_context.session_id = "core_test_session"
    
    # ===================== FACTORY ENFORCEMENT TESTS =====================
    
    def test_direct_instantiation_raises_runtime_error(self):
        """Test direct ToolDispatcher instantiation is prevented.
        
        BVJ: Enforces factory pattern for proper user isolation.
        """
        with pytest.raises(RuntimeError, match="Direct ToolDispatcher instantiation is no longer supported"):
            ToolDispatcher()
        
        self.record_metric("direct_instantiation_blocked", True)
    
    def test_factory_method_bypasses_init_restriction(self):
        """Test factory method successfully bypasses __init__ restriction.
        
        BVJ: Ensures factory can create properly isolated instances.
        """
        # Mock the dependencies to avoid real initialization
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator') as mock_validator:
                    
                    # This should work via factory method
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    # Verify instance was created
                    assert dispatcher is not None
                    assert isinstance(dispatcher, ToolDispatcher)
                    
                    # Verify components were initialized
                    mock_registry.assert_called_once()
                    mock_executor.assert_called_once()
                    mock_validator.assert_called_once()
        
        self.record_metric("factory_bypass_successful", True)
    
    @pytest.mark.asyncio
    async def test_create_request_scoped_dispatcher_calls_factory(self):
        """Test create_request_scoped_dispatcher properly calls factory.
        
        BVJ: Ensures recommended pattern works correctly.
        """
        with patch('netra_backend.app.agents.tool_executor_factory.create_isolated_tool_dispatcher') as mock_factory:
            mock_dispatcher = Mock()
            mock_factory.return_value = mock_dispatcher
            
            result = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=self.mock_user_context,
                tools=[Mock(name="test_tool")],
                websocket_manager=Mock()
            )
            
            # Verify factory was called with correct parameters
            mock_factory.assert_called_once()
            call_kwargs = mock_factory.call_args[1]
            assert call_kwargs['user_context'] == self.mock_user_context
            assert 'tools' in call_kwargs
            assert 'websocket_manager' in call_kwargs
            
            assert result == mock_dispatcher
        
        self.record_metric("request_scoped_factory_tested", True)
    
    def test_create_scoped_dispatcher_context_returns_context_manager(self):
        """Test create_scoped_dispatcher_context returns proper context manager.
        
        BVJ: Ensures automatic cleanup for memory safety.
        """
        with patch('netra_backend.app.agents.tool_executor_factory.isolated_tool_dispatcher_scope') as mock_scope:
            mock_context_manager = Mock()
            mock_scope.return_value = mock_context_manager
            
            result = ToolDispatcher.create_scoped_dispatcher_context(
                user_context=self.mock_user_context
            )
            
            # Verify scope factory was called
            mock_scope.assert_called_once()
            call_kwargs = mock_scope.call_args[1]
            assert call_kwargs['user_context'] == self.mock_user_context
            
            assert result == mock_context_manager
        
        self.record_metric("scoped_context_manager_tested", True)
    
    # ===================== COMPONENT INITIALIZATION TESTS =====================
    
    def test_init_components_creates_required_components(self):
        """Test _init_components creates all required components.
        
        BVJ: Ensures dispatcher has all necessary functionality.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator') as mock_validator:
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    # Verify all components were created
                    assert hasattr(dispatcher, 'registry')
                    assert hasattr(dispatcher, 'executor') 
                    assert hasattr(dispatcher, 'validator')
                    
                    # Verify components are correct instances
                    mock_registry.assert_called_once()
                    mock_executor.assert_called_once()
                    mock_validator.assert_called_once()
        
        self.record_metric("component_initialization_verified", True)
    
    def test_register_initial_tools_registers_provided_tools(self):
        """Test _register_initial_tools registers provided tools.
        
        BVJ: Ensures tools are available for execution after initialization.
        """
        mock_tool1 = Mock()
        mock_tool1.name = "test_tool_1"
        mock_tool2 = Mock()
        mock_tool2.name = "test_tool_2"
        tools = [mock_tool1, mock_tool2]
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry_class.return_value = mock_registry
                    
                    dispatcher = ToolDispatcher._init_from_factory(tools=tools)
                    
                    # Verify registry.register_tools was called with the tools
                    mock_registry.register_tools.assert_called_once_with(tools)
        
        self.record_metric("initial_tools_registration_tested", True)
    
    # ===================== TOOL MANAGEMENT TESTS =====================
    
    def test_has_tool_delegates_to_registry(self):
        """Test has_tool method delegates to registry.
        
        BVJ: Ensures consistent tool lookup behavior.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry.has_tool.return_value = True
                    mock_registry_class.return_value = mock_registry
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    result = dispatcher.has_tool("test_tool")
                    
                    assert result is True
                    mock_registry.has_tool.assert_called_once_with("test_tool")
        
        self.record_metric("has_tool_delegation_tested", True)
    
    def test_register_tool_creates_dynamic_tool_wrapper(self):
        """Test register_tool creates proper dynamic tool wrapper for functions.
        
        BVJ: Enables flexible tool registration patterns.
        """
        def test_function(param1, param2):
            return f"Result: {param1}, {param2}"
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry_class.return_value = mock_registry
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    dispatcher.register_tool("test_func", test_function, "Test function description")
                    
                    # Verify registry.register_tool was called
                    mock_registry.register_tool.assert_called_once()
                    
                    # Get the registered tool and verify it's a BaseTool
                    registered_tool = mock_registry.register_tool.call_args[0][0]
                    from langchain_core.tools import BaseTool
                    assert isinstance(registered_tool, BaseTool)
                    assert registered_tool.name == "test_func"
                    assert "Test function description" in registered_tool.description
        
        self.record_metric("dynamic_tool_wrapper_tested", True)
    
    def test_register_tool_handles_basetool_directly(self):
        """Test register_tool handles BaseTool instances directly.
        
        BVJ: Supports standard LangChain tool patterns.
        """
        from langchain_core.tools import BaseTool
        
        class TestTool(BaseTool):
            name = "test_base_tool"
            description = "Test BaseTool"
            
            def _run(self, *args, **kwargs):
                return "test result"
        
        mock_tool = TestTool()
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry_class.return_value = mock_registry
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    dispatcher.register_tool("test_base_tool", mock_tool)
                    
                    # Verify registry.register_tool was called with the tool directly
                    mock_registry.register_tool.assert_called_once_with(mock_tool)
        
        self.record_metric("basetool_direct_registration_tested", True)
    
    # ===================== DISPATCH LOGIC TESTS =====================
    
    @pytest.mark.asyncio
    async def test_dispatch_creates_correct_tool_input(self):
        """Test dispatch method creates correct ToolInput.
        
        BVJ: Ensures consistent tool execution interface.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry.has_tool.return_value = True
                    mock_registry.get_tool.return_value = Mock(name="test_tool")
                    mock_registry_class.return_value = mock_registry
                    
                    mock_executor = Mock()
                    mock_executor.execute_tool_with_input = AsyncMock(return_value=Mock())
                    mock_executor_class.return_value = mock_executor
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    await dispatcher.dispatch("test_tool", param1="value1", param2=42)
                    
                    # Verify execute_tool_with_input was called with correct ToolInput
                    mock_executor.execute_tool_with_input.assert_called_once()
                    call_args = mock_executor.execute_tool_with_input.call_args[0]
                    
                    tool_input = call_args[0]
                    assert isinstance(tool_input, ToolInput)
                    assert tool_input.tool_name == "test_tool"
                    assert tool_input.kwargs == {"param1": "value1", "param2": 42}
        
        self.record_metric("dispatch_tool_input_creation_tested", True)
    
    @pytest.mark.asyncio
    async def test_dispatch_handles_tool_not_found(self):
        """Test dispatch handles tool not found scenario.
        
        BVJ: Provides clear error handling for missing tools.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry.has_tool.return_value = False
                    mock_registry_class.return_value = mock_registry
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    result = await dispatcher.dispatch("nonexistent_tool")
                    
                    # Verify error result is returned
                    assert isinstance(result, ToolResult)
                    assert result.status == ToolStatus.ERROR
                    assert "nonexistent_tool not found" in result.message
        
        self.record_metric("dispatch_tool_not_found_handled", True)
    
    @pytest.mark.asyncio  
    async def test_dispatch_tool_with_state_delegates_to_executor(self):
        """Test dispatch_tool method delegates to executor with state.
        
        BVJ: Ensures stateful tool execution works correctly.
        """
        mock_state = Mock(spec=DeepAgentState)
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_registry = Mock()
                    mock_registry.has_tool.return_value = True
                    mock_registry.get_tool.return_value = Mock(name="test_tool")
                    mock_registry_class.return_value = mock_registry
                    
                    mock_executor = Mock()
                    mock_executor.execute_with_state = AsyncMock(return_value={"success": True, "result": "success"})
                    mock_executor_class.return_value = mock_executor
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    result = await dispatcher.dispatch_tool(
                        "test_tool", 
                        {"param": "value"}, 
                        mock_state, 
                        "test_run_id"
                    )
                    
                    # Verify executor was called correctly
                    mock_executor.execute_with_state.assert_called_once()
                    call_args = mock_executor.execute_with_state.call_args[0]
                    assert call_args[1] == "test_tool"  # tool_name
                    assert call_args[2] == {"param": "value"}  # parameters
                    assert call_args[3] == mock_state  # state
                    assert call_args[4] == "test_run_id"  # run_id
                    
                    # Verify response is ToolDispatchResponse
                    assert isinstance(result, ToolDispatchResponse)
                    assert result.success is True
        
        self.record_metric("dispatch_tool_with_state_tested", True)
    
    # ===================== WEBSOCKET INTEGRATION TESTS =====================
    
    def test_has_websocket_support_property(self):
        """Test has_websocket_support property checks executor bridge.
        
        BVJ: Enables conditional WebSocket event emission.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    # Test with WebSocket bridge
                    mock_executor_with_bridge = Mock()
                    mock_executor_with_bridge.websocket_bridge = Mock()
                    mock_executor_class.return_value = mock_executor_with_bridge
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    assert dispatcher.has_websocket_support is True
                    
                    # Test without WebSocket bridge
                    mock_executor_without_bridge = Mock()
                    mock_executor_without_bridge.websocket_bridge = None
                    dispatcher.executor = mock_executor_without_bridge
                    
                    assert dispatcher.has_websocket_support is False
        
        self.record_metric("websocket_support_property_tested", True)
    
    def test_set_websocket_bridge_updates_executor(self):
        """Test set_websocket_bridge updates executor bridge.
        
        BVJ: Enables dynamic WebSocket configuration.
        """
        mock_bridge = Mock()
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_executor = Mock()
                    mock_executor.websocket_bridge = None
                    mock_executor_class.return_value = mock_executor
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    dispatcher.set_websocket_bridge(mock_bridge)
                    
                    # Verify executor bridge was updated
                    assert dispatcher.executor.websocket_bridge == mock_bridge
        
        self.record_metric("set_websocket_bridge_tested", True)
    
    def test_get_websocket_bridge_returns_executor_bridge(self):
        """Test get_websocket_bridge returns executor's bridge.
        
        BVJ: Provides access to current WebSocket configuration.
        """
        mock_bridge = Mock()
        
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_executor = Mock()
                    mock_executor.websocket_bridge = mock_bridge
                    mock_executor_class.return_value = mock_executor
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    result = dispatcher.get_websocket_bridge()
                    
                    assert result == mock_bridge
        
        self.record_metric("get_websocket_bridge_tested", True)
    
    # ===================== DIAGNOSTIC TESTS =====================
    
    def test_diagnose_websocket_wiring_provides_comprehensive_info(self):
        """Test diagnose_websocket_wiring provides comprehensive diagnostic info.
        
        BVJ: Enables debugging of WebSocket event failures.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    mock_executor = Mock()
                    mock_executor.websocket_bridge = None
                    mock_executor_class.return_value = mock_executor
                    
                    dispatcher = ToolDispatcher._init_from_factory()
                    
                    diagnosis = dispatcher.diagnose_websocket_wiring()
                    
                    # Verify all diagnostic fields are present
                    expected_fields = [
                        "dispatcher_has_executor",
                        "executor_type", 
                        "executor_has_websocket_bridge_attr",
                        "websocket_bridge_is_none",
                        "websocket_bridge_type",
                        "has_websocket_support",
                        "critical_issues"
                    ]
                    
                    for field in expected_fields:
                        assert field in diagnosis
                    
                    # Verify specific values for this test case
                    assert diagnosis["dispatcher_has_executor"] is True
                    assert diagnosis["websocket_bridge_is_none"] is True
                    assert "WebSocket bridge is None" in diagnosis["critical_issues"]
        
        self.record_metric("websocket_diagnostics_tested", True)


class TestToolDispatcherDataModelsUnit(SSotBaseTestCase):
    """Unit tests for data models in tool_dispatcher_core."""
    
    def test_tool_dispatch_request_model_validation(self):
        """Test ToolDispatchRequest model validation.
        
        BVJ: Ensures type safety in dispatch operations.
        """
        # Test valid request
        request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"key": "value", "number": 42}
        )
        
        assert request.tool_name == "test_tool"
        assert request.parameters == {"key": "value", "number": 42}
        
        # Test default parameters
        minimal_request = ToolDispatchRequest(tool_name="minimal")
        assert minimal_request.parameters == {}
        
        self.record_metric("dispatch_request_model_validated", True)
    
    def test_tool_dispatch_response_model_validation(self):
        """Test ToolDispatchResponse model validation.
        
        BVJ: Ensures consistent response structure.
        """
        # Test success response
        success_response = ToolDispatchResponse(
            success=True,
            result={"output": "success"},
            metadata={"timing": 150}
        )
        
        assert success_response.success is True
        assert success_response.result == {"output": "success"}
        assert success_response.error is None
        assert success_response.metadata == {"timing": 150}
        
        # Test error response
        error_response = ToolDispatchResponse(
            success=False,
            error="Tool execution failed"
        )
        
        assert error_response.success is False
        assert error_response.result is None
        assert error_response.error == "Tool execution failed"
        assert error_response.metadata == {}
        
        self.record_metric("dispatch_response_model_validated", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])