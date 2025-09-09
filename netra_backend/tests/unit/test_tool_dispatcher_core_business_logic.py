"""Unit Tests for Tool Dispatcher Core Business Logic

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and isolated tool execution per user request
- Value Impact: Prevents data leakage between users and enables concurrent execution
- Strategic Impact: Foundation for multi-tenant AI tool execution at scale

CRITICAL TEST PURPOSE:
These unit tests validate the business logic of ToolDispatcher core functionality
including factory patterns, user isolation, and security boundaries.

Test Coverage:
- Request-scoped dispatcher factory methods
- User isolation and context management
- Tool registration and execution workflows
- WebSocket bridge integration and diagnostics
- Error handling and security validation
- Registry and executor component initialization
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from langchain_core.tools import BaseTool

from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from test_framework.ssot.mocks import MockFactory


class MockTool(BaseTool):
    """Mock tool for testing purposes."""
    
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, query: str = "") -> str:
        return f"Mock result for: {query}"
    
    async def _arun(self, query: str = "") -> str:
        return f"Mock async result for: {query}"


class TestToolDispatcherCoreBusiness:
    """Unit tests for Tool Dispatcher Core business logic validation."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_factory = MockFactory()
        
        # Create test tools
        self.test_tool = MockTool()
        self.test_tool.name = "test_analyzer"
        self.test_tool.description = "Analyzes test data"
        
        # Create mock user context
        self.mock_user_context = self.mock_factory.create_mock()
        self.mock_user_context.user_id = "test-user-123"
        self.mock_user_context.request_id = "req-456"
    
    def teardown_method(self):
        """Clean up after each test."""
        self.mock_factory.cleanup()
    
    @pytest.mark.unit
    def test_tool_dispatcher_direct_instantiation_blocked(self):
        """Test that direct ToolDispatcher instantiation is blocked for security."""
        # Act & Assert - verify direct instantiation raises RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher()
        
        error_message = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_message
        assert "create_request_scoped_dispatcher" in error_message
        assert "proper user isolation" in error_message
    
    @pytest.mark.unit
    def test_tool_dispatcher_direct_instantiation_with_args_blocked(self):
        """Test that direct ToolDispatcher instantiation with args is blocked."""
        # Act & Assert - verify instantiation with args still raises RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher(tools=[self.test_tool])
        
        error_message = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_message
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry')
    @patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine')
    @patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator')
    def test_tool_dispatcher_factory_initialization(self, mock_validator, mock_executor, mock_registry):
        """Test ToolDispatcher factory initialization components."""
        # Arrange
        mock_websocket_bridge = self.mock_factory.create_async_mock()
        
        # Act - use internal factory method
        dispatcher = ToolDispatcher._init_from_factory(
            tools=[self.test_tool],
            websocket_bridge=mock_websocket_bridge
        )
        
        # Assert - verify components are initialized
        assert dispatcher is not None
        mock_registry.assert_called_once()
        mock_executor.assert_called_once()
        mock_validator.assert_called_once()
        
        # Verify websocket_bridge was passed to executor
        executor_call_args = mock_executor.call_args
        assert executor_call_args[1]['websocket_bridge'] == mock_websocket_bridge
    
    @pytest.mark.unit
    def test_tool_dispatcher_properties(self):
        """Test ToolDispatcher properties for registry access."""
        # Arrange - create dispatcher via factory
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.tools = {"test_tool": self.test_tool}
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Act & Assert - verify properties
        assert dispatcher.tools == {"test_tool": self.test_tool}
        assert dispatcher.has_websocket_support in [True, False]  # Depends on executor setup
    
    @pytest.mark.unit
    def test_has_tool_functionality(self):
        """Test has_tool method for tool existence checking."""
        # Arrange - create dispatcher with registry
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.has_tool = Mock()
            mock_registry.has_tool.side_effect = lambda name: name == "existing_tool"
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Act & Assert
        assert dispatcher.has_tool("existing_tool") == True
        assert dispatcher.has_tool("nonexistent_tool") == False
        
        # Verify registry method was called
        mock_registry.has_tool.assert_called()
    
    @pytest.mark.unit
    def test_register_tool_with_function(self):
        """Test tool registration with plain function."""
        # Arrange - create dispatcher
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.register_tool = Mock()
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Define test function
        def test_function(query: str) -> str:
            return f"Result for {query}"
        
        # Act
        dispatcher.register_tool("dynamic_tool", test_function, "Test tool description")
        
        # Assert - verify tool was registered via registry
        mock_registry.register_tool.assert_called_once()
        
        # Get the registered tool
        registered_tool = mock_registry.register_tool.call_args[0][0]
        assert hasattr(registered_tool, 'name')
        assert registered_tool.name == "dynamic_tool"
        assert hasattr(registered_tool, 'description')
        assert "Test tool description" in registered_tool.description
    
    @pytest.mark.unit
    def test_register_tool_with_base_tool(self):
        """Test tool registration with BaseTool instance."""
        # Arrange - create dispatcher
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.register_tool = Mock()
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Act
        dispatcher.register_tool("base_tool", self.test_tool)
        
        # Assert - verify BaseTool was registered directly
        mock_registry.register_tool.assert_called_once_with(self.test_tool)
    
    @pytest.mark.unit
    async def test_dispatch_tool_success(self):
        """Test successful tool dispatch workflow."""
        # Arrange - create dispatcher with mocked components
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.has_tool = Mock(return_value=True)
            mock_registry.get_tool = Mock(return_value=self.test_tool)
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                mock_executor = self.mock_factory.create_async_mock()
                mock_executor.execute_with_state = AsyncMock(return_value={
                    "success": True,
                    "result": {"output": "Tool executed successfully"}
                })
                mock_executor_class.return_value = mock_executor
                
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        from netra_backend.app.agents.state import DeepAgentState
        test_state = DeepAgentState()
        
        # Act
        result = await dispatcher.dispatch_tool(
            tool_name="test_analyzer",
            parameters={"query": "test data"},
            state=test_state,
            run_id="run-123"
        )
        
        # Assert - verify successful dispatch
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == True
        assert result.result == {"output": "Tool executed successfully"}
        assert result.error is None
        
        # Verify executor was called
        mock_executor.execute_with_state.assert_called_once()
    
    @pytest.mark.unit
    async def test_dispatch_tool_not_found(self):
        """Test tool dispatch when tool is not found."""
        # Arrange - create dispatcher with registry that returns no tool
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.has_tool = Mock(return_value=False)
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine'):
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        from netra_backend.app.agents.state import DeepAgentState
        test_state = DeepAgentState()
        
        # Act
        result = await dispatcher.dispatch_tool(
            tool_name="nonexistent_tool",
            parameters={},
            state=test_state,
            run_id="run-123"
        )
        
        # Assert - verify error response
        assert isinstance(result, ToolDispatchResponse)
        assert result.success == False
        assert "not found" in result.error.lower()
    
    @pytest.mark.unit
    async def test_dispatch_legacy_method(self):
        """Test legacy dispatch method functionality."""
        # Arrange - create dispatcher with mocked components
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry_class:
            mock_registry = self.mock_factory.create_mock()
            mock_registry.has_tool = Mock(return_value=True)
            mock_registry.get_tool = Mock(return_value=self.test_tool)
            mock_registry_class.return_value = mock_registry
            
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                mock_executor = self.mock_factory.create_async_mock()
                mock_result = ToolResult(
                    tool_input=ToolInput(tool_name="test_analyzer", kwargs={"query": "test"}),
                    status=ToolStatus.SUCCESS,
                    result="Success result"
                )
                mock_executor.execute_tool_with_input = AsyncMock(return_value=mock_result)
                mock_executor_class.return_value = mock_executor
                
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Act
        result = await dispatcher.dispatch("test_analyzer", query="test data")
        
        # Assert - verify legacy dispatch works
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.result == "Success result"
    
    @pytest.mark.unit
    def test_websocket_bridge_management(self):
        """Test WebSocket bridge setter and getter methods."""
        # Arrange - create dispatcher
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                mock_executor = self.mock_factory.create_mock()
                mock_executor.websocket_bridge = None
                mock_executor_class.return_value = mock_executor
                
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Test initial state
        assert dispatcher.get_websocket_bridge() is None
        
        # Act - set WebSocket bridge
        mock_bridge = self.mock_factory.create_async_mock()
        dispatcher.set_websocket_bridge(mock_bridge)
        
        # Assert - verify bridge was set
        assert mock_executor.websocket_bridge == mock_bridge
        assert dispatcher.get_websocket_bridge() == mock_bridge
    
    @pytest.mark.unit
    def test_websocket_wiring_diagnostics(self):
        """Test WebSocket wiring diagnostic functionality."""
        # Arrange - create dispatcher with mock executor
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry'):
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor_class:
                mock_executor = self.mock_factory.create_mock()
                mock_executor.websocket_bridge = None
                mock_executor_class.return_value = mock_executor
                
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator'):
                    dispatcher = ToolDispatcher._init_from_factory()
        
        # Act
        diagnosis = dispatcher.diagnose_websocket_wiring()
        
        # Assert - verify diagnostic information
        assert "dispatcher_has_executor" in diagnosis
        assert "executor_type" in diagnosis
        assert "executor_has_websocket_bridge_attr" in diagnosis
        assert "websocket_bridge_is_none" in diagnosis
        assert "critical_issues" in diagnosis
        
        assert diagnosis["dispatcher_has_executor"] == True
        assert diagnosis["executor_has_websocket_bridge_attr"] == True
        assert diagnosis["websocket_bridge_is_none"] == True
        assert "WebSocket bridge is None" in diagnosis["critical_issues"]
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.tool_dispatcher_core.create_isolated_tool_dispatcher')
    async def test_create_request_scoped_dispatcher_factory_method(self, mock_create_isolated):
        """Test request-scoped dispatcher factory method."""
        # Arrange
        mock_dispatcher = self.mock_factory.create_async_mock()
        mock_create_isolated.return_value = mock_dispatcher
        
        mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Act
        result = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.mock_user_context,
            tools=[self.test_tool],
            websocket_manager=mock_websocket_manager
        )
        
        # Assert - verify factory function was called correctly
        mock_create_isolated.assert_called_once_with(
            user_context=self.mock_user_context,
            tools=[self.test_tool],
            websocket_manager=mock_websocket_manager
        )
        
        assert result == mock_dispatcher
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.tool_dispatcher_core.isolated_tool_dispatcher_scope')
    def test_create_scoped_dispatcher_context_factory_method(self, mock_scope):
        """Test scoped dispatcher context factory method."""
        # Arrange
        mock_context_manager = self.mock_factory.create_async_mock()
        mock_scope.return_value = mock_context_manager
        
        mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Act
        result = ToolDispatcher.create_scoped_dispatcher_context(
            user_context=self.mock_user_context,
            tools=[self.test_tool],
            websocket_manager=mock_websocket_manager
        )
        
        # Assert - verify context manager factory was called correctly
        mock_scope.assert_called_once_with(
            user_context=self.mock_user_context,
            tools=[self.test_tool],
            websocket_manager=mock_websocket_manager
        )
        
        assert result == mock_context_manager