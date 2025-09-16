"""
Unit Tests for Tool Dispatcher Facade

Tests the unified tool dispatcher facade that consolidates all tool dispatching
operations into a single source of truth.

Focus: Factory patterns, backward compatibility, deprecation warnings, SSOT compliance
"""

import pytest
import warnings
from unittest.mock import Mock, AsyncMock, patch
from typing import List
from uuid import uuid4

from langchain_core.tools import BaseTool

from netra_backend.app.agents.tool_dispatcher import (
    ToolDispatcher,
    UnifiedToolDispatcher, 
    create_tool_dispatcher,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy
)
from netra_backend.app.core.tool_models import ToolExecutionResult


class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, *args, **kwargs):
        return "mock tool result"
    
    async def _arun(self, *args, **kwargs):
        return "async mock tool result"


class TestToolDispatcherFacade:
    """Unit tests for tool dispatcher facade and factory patterns."""

    def test_backward_compatibility_alias(self):
        """Test that ToolDispatcher is an alias for UnifiedToolDispatcher."""
        assert ToolDispatcher is UnifiedToolDispatcher

    def test_create_tool_dispatcher_deprecation_warning(self):
        """Test that legacy factory function shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            dispatcher = create_tool_dispatcher()
            
            # Verify deprecation warning
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "create_tool_dispatcher() creates global state" in str(w[0].message)
            assert "UnifiedToolDispatcherFactory.create_for_request()" in str(w[0].message)
        
        # Verify it returns a UnifiedToolDispatcher
        assert isinstance(dispatcher, UnifiedToolDispatcher)

    def test_create_tool_dispatcher_with_tools(self):
        """Test legacy factory with initial tools."""
        mock_tools = [MockTool(), MockTool(name="mock_tool_2")]
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress deprecation warning
            dispatcher = create_tool_dispatcher(tools=mock_tools)
        
        assert isinstance(dispatcher, UnifiedToolDispatcher)
        # Note: Can't easily test tool registration without exposing internals

    @patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory')
    def test_create_request_scoped_tool_dispatcher(self, mock_factory):
        """Test request-scoped factory function."""
        mock_user_context = Mock()
        mock_websocket_manager = Mock()
        mock_tools = [MockTool()]
        
        mock_dispatcher = Mock(spec=UnifiedToolDispatcher)
        mock_factory.create_for_request.return_value = mock_dispatcher
        
        result = create_request_scoped_tool_dispatcher(
            user_context=mock_user_context,
            websocket_manager=mock_websocket_manager,
            tools=mock_tools
        )
        
        # Verify factory was called correctly
        mock_factory.create_for_request.assert_called_once_with(
            user_context=mock_user_context,
            websocket_manager=mock_websocket_manager,
            tools=mock_tools
        )
        assert result == mock_dispatcher

    def test_tool_dispatch_request_model(self):
        """Test ToolDispatchRequest data model."""
        request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"param1": "value1", "param2": 42},
            user_id="test-user",
            correlation_id="test-correlation"
        )
        
        assert request.tool_name == "test_tool"
        assert request.parameters == {"param1": "value1", "param2": 42}
        assert request.user_id == "test-user"
        assert request.correlation_id == "test-correlation"

    def test_tool_dispatch_response_model(self):
        """Test ToolDispatchResponse data model."""
        response = ToolDispatchResponse(
            success=True,
            result="test result",
            tool_name="test_tool",
            execution_time_ms=250
        )
        
        assert response.success is True
        assert response.result == "test result"
        assert response.tool_name == "test_tool"
        assert response.execution_time_ms == 250

    def test_dispatch_strategy_enum(self):
        """Test DispatchStrategy enumeration."""
        # Verify enum values exist
        assert hasattr(DispatchStrategy, 'SEQUENTIAL')
        assert hasattr(DispatchStrategy, 'PARALLEL')
        assert hasattr(DispatchStrategy, 'PRIORITY')
        
        # Verify values are distinct
        strategies = [DispatchStrategy.SEQUENTIAL, DispatchStrategy.PARALLEL, DispatchStrategy.PRIORITY]
        assert len(set(strategies)) == 3

    @patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory')
    def test_create_request_scoped_dispatcher_alias(self, mock_factory):
        """Test create_request_scoped_dispatcher function import."""
        from netra_backend.app.agents.tool_dispatcher import create_request_scoped_dispatcher
        
        mock_user_context = Mock()
        mock_dispatcher = Mock()
        mock_factory.create_for_request.return_value = mock_dispatcher
        
        result = create_request_scoped_dispatcher(mock_user_context)
        
        mock_factory.create_for_request.assert_called_once()
        assert result == mock_dispatcher

    def test_tool_execution_result_import(self):
        """Test that ToolExecutionResult is available from this module."""
        # Should be importable
        assert ToolExecutionResult is not None
        
        # Should be able to create instance
        result = ToolExecutionResult(
            success=True,
            result="test",
            tool_name="test_tool"
        )
        assert result.success is True

    @patch('netra_backend.app.agents.tool_dispatcher.ProductionTool', None)
    @patch('netra_backend.app.agents.tool_dispatcher.ToolExecuteResponse', None)
    def test_production_tool_import_failure_handling(self):
        """Test graceful handling when ProductionTool is not available."""
        # Re-import the module to test import failure handling
        import importlib
        import netra_backend.app.agents.tool_dispatcher as dispatcher_module
        
        # Should not raise exception even if ProductionTool is None
        dispatcher = create_tool_dispatcher()
        assert isinstance(dispatcher, UnifiedToolDispatcher)

    def test_module_level_imports_available(self):
        """Test that all expected imports are available at module level."""
        from netra_backend.app.agents.tool_dispatcher import (
            UnifiedToolDispatcher,
            UnifiedToolDispatcherFactory,
            ToolDispatchRequest,
            ToolDispatchResponse,
            DispatchStrategy,
            create_request_scoped_dispatcher,
            ToolExecutionResult,
            UnifiedTool
        )
        
        # All imports should be available
        assert UnifiedToolDispatcher is not None
        assert UnifiedToolDispatcherFactory is not None
        assert ToolDispatchRequest is not None
        assert ToolDispatchResponse is not None
        assert DispatchStrategy is not None
        assert create_request_scoped_dispatcher is not None
        assert ToolExecutionResult is not None
        assert UnifiedTool is not None

    def test_facade_pattern_documentation(self):
        """Test that facade provides proper documentation."""
        import netra_backend.app.agents.tool_dispatcher as dispatcher_module
        
        # Module should have docstring explaining consolidation
        assert dispatcher_module.__doc__ is not None
        assert "CONSOLIDATION COMPLETE" in dispatcher_module.__doc__
        assert "Single source of truth" in dispatcher_module.__doc__

    @patch('netra_backend.app.agents.tool_dispatcher.warnings.warn')
    def test_legacy_function_warning_stacklevel(self, mock_warn):
        """Test that deprecation warnings use correct stacklevel."""
        create_tool_dispatcher()
        
        # Verify warning was called with correct stacklevel
        mock_warn.assert_called_once()
        args, kwargs = mock_warn.call_args
        assert 'stacklevel' in kwargs
        assert kwargs['stacklevel'] == 2

    def test_backward_compatibility_function_signatures(self):
        """Test that legacy functions maintain compatible signatures."""
        import inspect
        
        # create_tool_dispatcher should accept expected parameters
        sig = inspect.signature(create_tool_dispatcher)
        expected_params = ['tools', 'websocket_bridge', 'permission_service']
        
        for param in expected_params:
            assert param in sig.parameters
            # All should have default None
            assert sig.parameters[param].default is None

    def test_request_scoped_function_signature(self):
        """Test request-scoped function has proper signature."""
        import inspect
        
        sig = inspect.signature(create_request_scoped_tool_dispatcher)
        
        # Should have required user_context parameter
        assert 'user_context' in sig.parameters
        assert sig.parameters['user_context'].default == inspect.Parameter.empty
        
        # Should have optional websocket_manager and tools
        assert 'websocket_manager' in sig.parameters
        assert 'tools' in sig.parameters
        assert sig.parameters['websocket_manager'].default is None
        assert sig.parameters['tools'].default is None

    @pytest.mark.asyncio
    async def test_mock_tool_execution(self):
        """Test that mock tools work correctly for testing."""
        tool = MockTool()
        
        # Test sync execution
        result = tool._run()
        assert result == "mock tool result"
        
        # Test async execution
        async_result = await tool._arun()
        assert async_result == "async mock tool result"

    def test_mock_tool_properties(self):
        """Test mock tool properties."""
        tool = MockTool()
        
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert isinstance(tool, BaseTool)

    def test_multiple_mock_tools(self):
        """Test creating multiple mock tools with different names."""
        tool1 = MockTool()
        tool2 = MockTool(name="custom_tool")
        
        assert tool1.name == "mock_tool"
        assert tool2.name == "custom_tool"
        assert tool1.description == tool2.description  # Same description

    @patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global')
    def test_create_tool_dispatcher_calls_factory(self, mock_create_legacy):
        """Test that create_tool_dispatcher calls the correct factory method."""
        mock_tools = [MockTool()]
        mock_dispatcher = Mock()
        mock_create_legacy.return_value = mock_dispatcher
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = create_tool_dispatcher(tools=mock_tools)
        
        mock_create_legacy.assert_called_once_with(mock_tools)
        assert result == mock_dispatcher

    def test_tool_dispatch_models_are_dataclasses_or_pydantic(self):
        """Test that data models have proper structure."""
        # Create instances to verify they work
        request = ToolDispatchRequest(
            tool_name="test",
            parameters={},
            user_id="user"
        )
        
        response = ToolDispatchResponse(
            success=True,
            result="result",
            tool_name="test"
        )
        
        # Should have proper attributes
        assert hasattr(request, 'tool_name')
        assert hasattr(request, 'parameters') 
        assert hasattr(request, 'user_id')
        
        assert hasattr(response, 'success')
        assert hasattr(response, 'result')
        assert hasattr(response, 'tool_name')

    def test_imports_from_correct_modules(self):
        """Test that imports come from the expected consolidated locations."""
        # These should come from unified_tool_dispatcher
        from netra_backend.app.core.tools.unified_tool_dispatcher import (
            UnifiedToolDispatcher as CoreUnifiedToolDispatcher,
            UnifiedToolDispatcherFactory as CoreFactory
        )
        
        from netra_backend.app.agents.tool_dispatcher import (
            UnifiedToolDispatcher as FacadeUnifiedToolDispatcher,
            UnifiedToolDispatcherFactory as FacadeFactory
        )
        
        # Facade should import from core
        assert CoreUnifiedToolDispatcher is FacadeUnifiedToolDispatcher
        assert CoreFactory is FacadeFactory

    def test_facade_provides_clean_api(self):
        """Test that facade provides a clean, simplified API."""
        # Should be able to create dispatcher with minimal imports
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dispatcher = create_tool_dispatcher()
        
        assert isinstance(dispatcher, UnifiedToolDispatcher)
        
        # Should support request-scoped creation
        mock_context = Mock()
        scoped_dispatcher = create_request_scoped_tool_dispatcher(mock_context)
        assert isinstance(scoped_dispatcher, UnifiedToolDispatcher)