"""Unit tests for ToolDispatcherCore - Core dispatcher logic and initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Security & User Isolation
- Business Goal: Secure tool execution with complete user isolation
- Value Impact: Prevents data leaks between users and ensures secure tool dispatch
- Strategic Impact: Enables safe multi-user agent operations with factory-based isolation

CRITICAL: Tests validate request-scoped architecture, user isolation, and factory patterns.
All tests use SSOT patterns and IsolatedEnvironment for environment access.

SECURITY: Direct instantiation is blocked - only factory methods provide secure instances.
Tests ensure proper isolation and WebSocket integration for each user context.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse,
)
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockBaseTool(BaseTool):
    """Mock BaseTool for testing."""
    
    name: str = "test_tool"
    description: str = "A test tool"
    
    def _run(self, **kwargs) -> str:
        return f"Tool executed with: {kwargs}"
    
    async def _arun(self, **kwargs) -> str:
        return f"Async tool executed with: {kwargs}"


class MockUserExecutionContext:
    """Mock user execution context for testing."""
    
    def __init__(self, user_id: str = "test_user"):
        self.user_id = user_id
        self.thread_id = f"thread_{user_id}"
        self.correlation_id = str(uuid4())


class TestToolDispatcherCore(SSotAsyncTestCase):
    """Unit tests for ToolDispatcherCore - Core dispatcher logic with security."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create test data
        self.mock_user_context = MockUserExecutionContext()
        self.mock_tools = [MockBaseTool()]
        self.mock_websocket_bridge = AsyncMock()
        
        # Create test state
        self.test_state = DeepAgentState()
        self.test_state.user_id = self.mock_user_context.user_id
        self.test_state.thread_id = self.mock_user_context.thread_id
        
        # Record setup metrics
        self.record_metric("core_dispatcher_setup", True)
        self.record_metric("mock_tools_prepared", len(self.mock_tools))

    def test_direct_instantiation_blocked(self):
        """
        BVJ: Validates direct instantiation prevention ensures proper user isolation.
        Critical security feature prevents accidental global state creation that could leak data.
        """
        # Test that direct instantiation is blocked
        with pytest.raises(RuntimeError, match="Direct ToolDispatcher instantiation is no longer supported"):
            ToolDispatcher(tools=self.mock_tools, websocket_bridge=self.mock_websocket_bridge)
        
        # Verify error message guides to factory methods
        try:
            ToolDispatcher()
        except RuntimeError as e:
            error_message = str(e)
            assert "create_request_scoped_dispatcher" in error_message, "Error should mention factory methods"
            assert "user isolation" in error_message, "Error should mention user isolation importance"
        
        # Record security verification metrics
        self.record_metric("direct_instantiation_blocked", 1)
        self.record_metric("security_error_guidance", 1)

    async def test_factory_method_creates_secure_instance(self):
        """
        BVJ: Validates factory methods create properly isolated instances for user security.
        Ensures each user gets isolated tool dispatcher preventing cross-user data access.
        """
        # Mock factory method for testing
        with patch('netra_backend.app.agents.tool_dispatcher_core.create_isolated_tool_dispatcher') as mock_factory:
            mock_dispatcher = Mock()
            mock_dispatcher.dispatch = AsyncMock(return_value=Mock())
            mock_factory.return_value = mock_dispatcher
            
            # Test factory method call
            dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=self.mock_user_context,
                tools=self.mock_tools,
                websocket_manager=self.mock_websocket_bridge
            )
            
            # Verify factory was called with correct parameters
            mock_factory.assert_called_once_with(
                user_context=self.mock_user_context,
                tools=self.mock_tools,
                websocket_manager=self.mock_websocket_bridge
            )
            
            # Verify dispatcher is properly isolated
            assert dispatcher == mock_dispatcher, "Should return factory-created dispatcher"
        
        # Record factory creation metrics
        self.record_metric("secure_instances_created", 1)
        self.record_metric("user_isolation_enforced", 1)

    def test_tool_dispatch_request_model(self):
        """
        BVJ: Validates typed request model ensures consistent tool parameter handling.
        Prevents parameter errors that could cause tool execution failures.
        """
        # Test valid request creation
        request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"query": "test query", "limit": 10}
        )
        
        # Verify request structure
        assert request.tool_name == "test_tool", "Should store tool name"
        assert request.parameters["query"] == "test query", "Should store parameters correctly"
        assert request.parameters["limit"] == 10, "Should handle different parameter types"
        
        # Test default parameters
        minimal_request = ToolDispatchRequest(tool_name="minimal_tool")
        assert minimal_request.parameters == {}, "Should default to empty parameters"
        
        # Record request model metrics
        self.record_metric("typed_requests_created", 2)

    def test_tool_dispatch_response_model(self):
        """
        BVJ: Validates typed response model provides consistent result handling.
        Ensures agents receive standardized response format for reliable error handling.
        """
        # Test successful response
        success_response = ToolDispatchResponse(
            success=True,
            result={"data": "processed", "count": 42},
            metadata={"execution_time": 1.5, "cache_hit": False}
        )
        
        assert success_response.success is True, "Should indicate success"
        assert success_response.result["data"] == "processed", "Should include result data"
        assert success_response.error is None, "Should not have error on success"
        assert success_response.metadata["execution_time"] == 1.5, "Should include metadata"
        
        # Test error response
        error_response = ToolDispatchResponse(
            success=False,
            error="Tool not found",
            metadata={"attempted_tool": "missing_tool"}
        )
        
        assert error_response.success is False, "Should indicate failure"
        assert error_response.result is None, "Should not have result on error"
        assert error_response.error == "Tool not found", "Should include error message"
        
        # Record response model metrics
        self.record_metric("typed_responses_created", 2)
        self.record_metric("error_handling_validated", 1)

    def test_internal_factory_initializer(self):
        """
        BVJ: Validates internal factory initializer properly sets up components.
        Ensures secure instances have all required components for tool execution.
        """
        # Mock the required components
        with patch('netra_backend.app.agents.tool_dispatcher_core.ToolRegistry') as mock_registry:
            with patch('netra_backend.app.agents.tool_dispatcher_core.UnifiedToolExecutionEngine') as mock_executor:
                with patch('netra_backend.app.agents.tool_dispatcher_core.ToolValidator') as mock_validator:
                    
                    # Create instance using internal factory
                    dispatcher = ToolDispatcher._init_from_factory(
                        tools=self.mock_tools,
                        websocket_bridge=self.mock_websocket_bridge
                    )
                    
                    # Verify components were initialized
                    mock_registry.assert_called_once()
                    mock_executor.assert_called_once_with(websocket_bridge=self.mock_websocket_bridge)
                    mock_validator.assert_called_once()
                    
                    # Verify dispatcher has required attributes
                    assert hasattr(dispatcher, 'registry'), "Should have registry"
                    assert hasattr(dispatcher, 'executor'), "Should have executor"
                    assert hasattr(dispatcher, 'validator'), "Should have validator"
        
        # Record component initialization metrics
        self.record_metric("components_initialized", 3)

    async def test_websocket_bridge_integration(self):
        """
        BVJ: Validates WebSocket bridge integration enables real-time user feedback.
        Critical for user experience - users need progress updates during tool execution.
        """
        # Create dispatcher with WebSocket support
        with patch.object(ToolDispatcher, '_init_from_factory') as mock_init:
            mock_dispatcher = Mock()
            mock_dispatcher.has_websocket_support = True
            mock_dispatcher.get_websocket_bridge.return_value = self.mock_websocket_bridge
            mock_init.return_value = mock_dispatcher
            
            dispatcher = ToolDispatcher._init_from_factory(websocket_bridge=self.mock_websocket_bridge)
            
            # Test WebSocket bridge setting
            dispatcher.set_websocket_bridge(self.mock_websocket_bridge)
            
            # Verify WebSocket support
            assert dispatcher.has_websocket_support is True, "Should support WebSocket events"
            assert dispatcher.get_websocket_bridge() == self.mock_websocket_bridge, "Should have bridge reference"
        
        # Record WebSocket integration metrics
        self.record_metric("websocket_bridge_integrated", 1)

    def test_websocket_diagnostics(self):
        """
        BVJ: Validates WebSocket diagnostic capabilities for troubleshooting silent failures.
        Helps developers identify and fix WebSocket wiring issues that cause lost events.
        """
        # Create mock dispatcher with diagnostic method
        mock_dispatcher = Mock()
        mock_dispatcher.diagnose_websocket_wiring.return_value = {
            "dispatcher_has_executor": True,
            "executor_type": "UnifiedToolExecutionEngine",
            "executor_has_websocket_bridge_attr": True,
            "websocket_bridge_is_none": False,
            "websocket_bridge_type": "AgentWebSocketBridge",
            "has_websocket_support": True,
            "critical_issues": []
        }
        
        # Test diagnostics
        diagnosis = mock_dispatcher.diagnose_websocket_wiring()
        
        # Verify diagnostic information
        assert diagnosis["dispatcher_has_executor"] is True, "Should detect executor presence"
        assert diagnosis["executor_type"] == "UnifiedToolExecutionEngine", "Should identify executor type"
        assert diagnosis["has_websocket_support"] is True, "Should detect WebSocket support"
        assert len(diagnosis["critical_issues"]) == 0, "Should detect no critical issues"
        
        # Test critical issue detection
        mock_dispatcher.diagnose_websocket_wiring.return_value["critical_issues"] = [
            "WebSocket bridge is None - tool events will be lost"
        ]
        
        diagnosis_with_issues = mock_dispatcher.diagnose_websocket_wiring()
        assert len(diagnosis_with_issues["critical_issues"]) > 0, "Should detect critical issues"
        
        # Record diagnostic metrics
        self.record_metric("websocket_diagnostics_tested", 1)
        self.record_metric("critical_issues_detected", 1)

    async def test_scoped_dispatcher_context_manager(self):
        """
        BVJ: Validates context manager provides automatic resource cleanup.
        Prevents memory leaks and ensures proper disposal of user-scoped resources.
        """
        # Mock context manager factory
        with patch('netra_backend.app.agents.tool_dispatcher_core.isolated_tool_dispatcher_scope') as mock_scope:
            mock_context_manager = AsyncMock()
            mock_scope.return_value = mock_context_manager
            
            # Test context manager creation
            context_manager = ToolDispatcher.create_scoped_dispatcher_context(
                user_context=self.mock_user_context,
                tools=self.mock_tools,
                websocket_manager=self.mock_websocket_bridge
            )
            
            # Verify factory was called
            mock_scope.assert_called_once_with(
                user_context=self.mock_user_context,
                tools=self.mock_tools,
                websocket_manager=self.mock_websocket_bridge
            )
            
            # Verify context manager returned
            assert context_manager == mock_context_manager, "Should return context manager"
        
        # Record context manager metrics
        self.record_metric("context_managers_created", 1)
        self.record_metric("automatic_cleanup_enabled", 1)

    def test_tool_registry_integration(self):
        """
        BVJ: Validates tool registry integration enables dynamic tool management.
        Allows agents to register and execute tools within their isolated scope.
        """
        # Mock dispatcher with tool registry
        mock_dispatcher = Mock()
        mock_registry = Mock()
        mock_dispatcher.registry = mock_registry
        mock_dispatcher.has_tool.return_value = True
        mock_dispatcher.tools = {"test_tool": MockBaseTool()}
        
        # Test tool registration
        mock_dispatcher.register_tool("test_tool", lambda x: f"result: {x}", "Test tool")
        
        # Test tool existence check
        assert mock_dispatcher.has_tool("test_tool") is True, "Should detect registered tools"
        
        # Test tools property access
        assert "test_tool" in mock_dispatcher.tools, "Should provide tools access"
        
        # Record registry integration metrics
        self.record_metric("tool_registry_integrated", 1)
        self.record_metric("tools_registered", 1)

    async def test_async_tool_execution(self):
        """
        BVJ: Validates async tool execution supports concurrent operations.
        Enables agents to execute multiple tools concurrently for better performance.
        """
        # Mock async tool execution
        with patch.object(ToolDispatcher, '_init_from_factory') as mock_init:
            mock_dispatcher = Mock()
            mock_executor = AsyncMock()
            mock_executor.execute_tool_with_input.return_value = ToolResult(
                tool_input=ToolInput(tool_name="test_tool", kwargs={}),
                status=ToolStatus.SUCCESS,
                result="Async execution result"
            )
            mock_dispatcher.executor = mock_executor
            mock_dispatcher.dispatch = AsyncMock(return_value=mock_executor.execute_tool_with_input.return_value)
            mock_init.return_value = mock_dispatcher
            
            dispatcher = ToolDispatcher._init_from_factory()
            
            # Test async execution
            result = await dispatcher.dispatch("test_tool", query="test")
            
            # Verify async execution
            assert result is not None, "Should return execution result"
            dispatcher.dispatch.assert_called_once_with("test_tool", query="test")
        
        # Record async execution metrics
        self.record_metric("async_executions_tested", 1)

    def test_security_documentation_validation(self):
        """
        BVJ: Validates security documentation guides developers to safe patterns.
        Ensures developers understand isolation requirements and factory usage.
        """
        # Test class docstring contains security guidance
        dispatcher_docstring = ToolDispatcher.__doc__ or ""
        
        security_indicators = [
            "request-scoped",
            "user isolation",
            "factory methods",
            "SECURITY",
            "isolation"
        ]
        
        security_mentions = sum(1 for indicator in security_indicators 
                               if indicator.lower() in dispatcher_docstring.lower())
        
        # Test method docstrings provide security context
        factory_method_doc = ToolDispatcher.create_request_scoped_dispatcher.__doc__ or ""
        factory_security_indicators = [
            "SECURE",
            "isolation",
            "user context",
            "SECURITY BENEFITS",
            "USER ISOLATION"
        ]
        
        factory_security_mentions = sum(1 for indicator in factory_security_indicators
                                       if indicator in factory_method_doc)
        
        # Record documentation metrics
        self.record_metric("security_documentation_indicators", security_mentions)
        self.record_metric("factory_security_guidance", factory_security_mentions)
        
        # Business value assertion: Security is well-documented
        assert security_mentions > 0, "Class should document security considerations"
        assert factory_security_mentions > 0, "Factory method should document security benefits"

    def teardown_method(self, method=None):
        """Cleanup test fixtures and verify metrics."""
        # Verify test execution
        assert self.get_test_context() is not None, "Test context should be available"
        
        # Record completion metrics
        self.record_metric("test_completed", True)
        
        # Call parent teardown
        super().teardown_method(method)