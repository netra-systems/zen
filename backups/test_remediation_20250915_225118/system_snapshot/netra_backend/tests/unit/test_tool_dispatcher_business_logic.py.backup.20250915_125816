"""Unit Tests for Tool Dispatcher Business Logic

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable tool execution for AI agent functionality
- Value Impact: Enables agents to deliver actionable insights and value to users
- Strategic Impact: Core platform capability that differentiates Netra AI

CRITICAL TEST PURPOSE:
These unit tests validate the business logic of the unified tool dispatcher
facade and its factory patterns for request-scoped isolation.

Test Coverage:
- Tool dispatcher facade functionality
- Factory method patterns for user isolation
- Backward compatibility with deprecation warnings
- Tool registration and execution workflows
- WebSocket bridge integration
- Error handling and security boundaries
"""

import pytest
import warnings
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from langchain_core.tools import BaseTool

from netra_backend.app.agents.tool_dispatcher import (
    ToolDispatcher,
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_tool_dispatcher,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy
)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from test_framework.ssot.mocks import MockFactory


class MockBaseTool(BaseTool):
    """Mock tool for testing purposes."""
    
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, query: str = "") -> str:
        return f"Mock result for: {query}"
    
    async def _arun(self, query: str = "") -> str:
        return f"Mock async result for: {query}"


class TestToolDispatcherBusiness:
    """Unit tests for Tool Dispatcher business logic validation."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_factory = MockFactory()
        
        # Create mock tools for testing
        self.mock_tool1 = MockBaseTool()
        self.mock_tool1.name = "test_tool_1"
        self.mock_tool1.description = "First test tool"
        
        self.mock_tool2 = MockBaseTool()
        self.mock_tool2.name = "test_tool_2" 
        self.mock_tool2.description = "Second test tool"
        
        self.test_tools = [self.mock_tool1, self.mock_tool2]
    
    def teardown_method(self):
        """Clean up after each test."""
        self.mock_factory.cleanup()
    
    @pytest.mark.unit
    def test_tool_dispatcher_alias_backward_compatibility(self):
        """Test backward compatibility alias for ToolDispatcher."""
        # Act & Assert - verify alias works
        assert ToolDispatcher is UnifiedToolDispatcher
        assert ToolDispatcher.__name__ == "UnifiedToolDispatcher"
    
    @pytest.mark.unit
    def test_create_tool_dispatcher_deprecation_warning(self):
        """Test deprecation warning for legacy global tool dispatcher creation."""
        # Act & Assert - verify deprecation warning is raised
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            dispatcher = create_tool_dispatcher(tools=self.test_tools)
            
            # Verify warning was issued
            assert len(warning_list) == 1
            warning = warning_list[0]
            assert issubclass(warning.category, DeprecationWarning)
            assert "global state" in str(warning.message)
            assert "UnifiedToolDispatcherFactory.create_for_request" in str(warning.message)
            
            # Verify dispatcher was created
            assert dispatcher is not None
            assert isinstance(dispatcher, UnifiedToolDispatcher)
    
    @pytest.mark.unit
    async def test_create_request_scoped_tool_dispatcher_recommended_pattern(self):
        """Test recommended request-scoped tool dispatcher creation."""
        # Arrange
        mock_user_context = self.mock_factory.create_mock()
        mock_user_context.user_id = "test-user-123"
        mock_user_context.request_id = "req-456"
        
        mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Act
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory') as mock_factory:
            mock_dispatcher = self.mock_factory.create_async_mock()
            mock_factory.create_for_request.return_value = mock_dispatcher
            
            result = create_request_scoped_tool_dispatcher(
                user_context=mock_user_context,
                websocket_manager=mock_websocket_manager,
                tools=self.test_tools
            )
            
            # Assert - verify factory method called correctly
            mock_factory.create_for_request.assert_called_once_with(
                user_context=mock_user_context,
                websocket_manager=mock_websocket_manager,
                tools=self.test_tools
            )
            
            assert result == mock_dispatcher
    
    @pytest.mark.unit
    def test_tool_dispatch_request_model_validation(self):
        """Test ToolDispatchRequest model validation."""
        # Test valid request
        valid_request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"query": "test query", "limit": 10}
        )
        
        assert valid_request.tool_name == "test_tool"
        assert valid_request.parameters == {"query": "test query", "limit": 10}
        
        # Test request with empty parameters (should default to empty dict)
        minimal_request = ToolDispatchRequest(tool_name="minimal_tool")
        assert minimal_request.tool_name == "minimal_tool"
        assert minimal_request.parameters == {}
    
    @pytest.mark.unit
    def test_tool_dispatch_response_model_validation(self):
        """Test ToolDispatchResponse model validation."""
        # Test successful response
        success_response = ToolDispatchResponse(
            success=True,
            result={"output": "Tool executed successfully"},
            metadata={"execution_time": 1.5, "tool_version": "1.0"}
        )
        
        assert success_response.success == True
        assert success_response.result == {"output": "Tool executed successfully"}
        assert success_response.error is None
        assert success_response.metadata["execution_time"] == 1.5
        
        # Test error response
        error_response = ToolDispatchResponse(
            success=False,
            error="Tool execution failed",
            metadata={"error_code": "TOOL_ERROR"}
        )
        
        assert error_response.success == False
        assert error_response.error == "Tool execution failed"
        assert error_response.result is None
        assert error_response.metadata["error_code"] == "TOOL_ERROR"
    
    @pytest.mark.unit
    def test_dispatch_strategy_enum_values(self):
        """Test DispatchStrategy enum has expected values."""
        # Verify enum values exist and are accessible
        assert hasattr(DispatchStrategy, 'SEQUENTIAL')
        assert hasattr(DispatchStrategy, 'PARALLEL') 
        assert hasattr(DispatchStrategy, 'PRIORITY')
        
        # Verify string representations are meaningful
        sequential = DispatchStrategy.SEQUENTIAL
        parallel = DispatchStrategy.PARALLEL
        priority = DispatchStrategy.PRIORITY
        
        assert sequential.value == "sequential"
        assert parallel.value == "parallel"
        assert priority.value == "priority"
    
    @pytest.mark.unit
    def test_tool_execution_result_model_structure(self):
        """Test ToolExecutionResult model structure."""
        # Create sample execution result
        execution_result = ToolExecutionResult(
            tool_name="test_analyzer",
            success=True,
            result={"analysis": "Complete", "score": 95},
            execution_time=2.3,
            error=None,
            metadata={"version": "2.1", "cached": False}
        )
        
        # Verify all fields are accessible
        assert execution_result.tool_name == "test_analyzer"
        assert execution_result.success == True
        assert execution_result.result["analysis"] == "Complete"
        assert execution_result.execution_time == 2.3
        assert execution_result.error is None
        assert execution_result.metadata["version"] == "2.1"
    
    @pytest.mark.unit
    def test_unified_tool_model_structure(self):
        """Test UnifiedTool model structure."""
        # Create sample unified tool
        unified_tool = UnifiedTool(
            name="cost_optimizer",
            description="Optimizes cloud costs",
            category="optimization",
            parameters_schema={"type": "object", "properties": {"account_id": {"type": "string"}}},
            permissions_required=["read:billing", "write:resources"],
            version="1.0.0"
        )
        
        # Verify all fields are accessible
        assert unified_tool.name == "cost_optimizer"
        assert unified_tool.description == "Optimizes cloud costs"
        assert unified_tool.category == "optimization"
        assert unified_tool.parameters_schema["type"] == "object"
        assert "read:billing" in unified_tool.permissions_required
        assert unified_tool.version == "1.0.0"
    
    @pytest.mark.unit
    def test_production_tool_imports_fallback_handling(self):
        """Test graceful handling when ProductionTool imports are unavailable."""
        # This test verifies the import fallback mechanism
        from netra_backend.app.agents import tool_dispatcher
        
        # Verify that if ProductionTool is None, it's handled gracefully
        if hasattr(tool_dispatcher, 'ProductionTool'):
            if tool_dispatcher.ProductionTool is None:
                # Verify it doesn't break the module
                assert tool_dispatcher.ToolExecuteResponse is None
                
                # Verify __all__ exports are adjusted appropriately
                all_exports = getattr(tool_dispatcher, '__all__', [])
                if "ProductionTool" in all_exports:
                    assert "ToolExecuteResponse" in all_exports
    
    @pytest.mark.unit
    def test_module_exports_completeness(self):
        """Test that all necessary components are exported."""
        from netra_backend.app.agents import tool_dispatcher
        
        # Verify essential exports are available
        essential_exports = [
            "ToolDispatcher",  # Backward compatibility
            "UnifiedToolDispatcher",  # Modern implementation
            "UnifiedToolDispatcherFactory",  # Factory for request-scoped
            "create_request_scoped_tool_dispatcher",  # Recommended function
            "ToolDispatchRequest",  # Request model
            "ToolDispatchResponse",  # Response model
            "DispatchStrategy",  # Execution strategy enum
            "ToolExecutionResult",  # Core result model
            "UnifiedTool",  # Unified tool model
        ]
        
        module_all = getattr(tool_dispatcher, '__all__', [])
        
        for export in essential_exports:
            assert export in module_all, f"Missing essential export: {export}"
            assert hasattr(tool_dispatcher, export), f"Export {export} not accessible"
    
    @pytest.mark.unit
    def test_migration_notice_emission(self):
        """Test that migration notice is properly emitted."""
        # This test verifies the migration notice function exists and can be called
        from netra_backend.app.agents.tool_dispatcher import _emit_migration_notice
        
        # Should not raise any exceptions
        with patch('logging.Logger.info') as mock_log:
            _emit_migration_notice()
            
            # Verify informational log was emitted
            mock_log.assert_called_once()
            log_message = mock_log.call_args[0][0]
            assert "consolidation complete" in log_message.lower()
            assert "unified_tool_dispatcher" in log_message
            assert "deprecation warnings" in log_message
    
    @pytest.mark.unit 
    def test_tool_dispatcher_factory_method_signatures(self):
        """Test factory method signatures are properly defined."""
        # Verify UnifiedToolDispatcherFactory has expected methods
        factory_methods = [
            'create_for_request',
            'create_legacy_global'
        ]
        
        for method_name in factory_methods:
            assert hasattr(UnifiedToolDispatcherFactory, method_name), f"Missing factory method: {method_name}"
            
            method = getattr(UnifiedToolDispatcherFactory, method_name)
            assert callable(method), f"Factory method {method_name} should be callable"
    
    @pytest.mark.unit
    def test_create_request_scoped_dispatcher_function_signature(self):
        """Test create_request_scoped_dispatcher function signature."""
        import inspect
        
        # Get function signature
        sig = inspect.signature(create_request_scoped_tool_dispatcher)
        
        # Verify expected parameters
        expected_params = ['user_context', 'websocket_manager', 'tools']
        param_names = list(sig.parameters.keys())
        
        for param in expected_params:
            assert param in param_names, f"Missing parameter: {param}"
        
        # Verify optional parameters have defaults
        assert sig.parameters['websocket_manager'].default is None
        assert sig.parameters['tools'].default is None
        
        # Verify user_context is required (no default)
        assert sig.parameters['user_context'].default == inspect.Parameter.empty