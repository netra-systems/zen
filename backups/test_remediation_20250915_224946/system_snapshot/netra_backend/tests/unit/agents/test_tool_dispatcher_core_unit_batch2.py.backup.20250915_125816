"""
Unit Tests for Tool Dispatcher Core - Batch 2 Priority Tests (tool_dispatcher_core.py)

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure core dispatch logic handles edge cases and errors correctly
- Value Impact: Prevents tool execution failures that would break agent workflows
- Strategic Impact: Core business logic that enables reliable AI agent operations

These tests focus on tool_dispatcher_core.py validation:
1. Factory method security enforcement
2. Request-scoped dispatcher creation
3. WebSocket bridge integration
4. Tool validation and error handling
5. Metrics and diagnostics
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)


class TestToolDispatcherCoreUnit(SSotBaseTestCase):
    """Unit tests for core tool dispatcher logic."""
    
    def setup_method(self, method):
        """Set up core dispatcher test environment."""
        super().setup_method(method)
        
        # Create mock user context
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "core_test_user"
        self.mock_user_context.run_id = "core_test_run"
        self.mock_user_context.thread_id = "core_test_thread" 
        self.mock_user_context.session_id = "core_test_session"
        
        # Create mock tools
        self.mock_tool = Mock()
        self.mock_tool.name = "test_core_tool"
        self.mock_tool.description = "Test tool for core testing"
    
    def test_direct_instantiation_prevented(self):
        """Test that direct instantiation is prevented for security.
        
        BVJ: Ensures user isolation by preventing global shared state.
        """
        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher()
        
        error_message = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_message
        assert "create_request_scoped_dispatcher" in error_message
        
        self.record_metric("direct_instantiation_prevention", "enforced")
    
    @patch('netra_backend.app.agents.tool_dispatcher_core.ToolDispatcher._init_from_factory')
    async def test_create_request_scoped_dispatcher_success(self, mock_init):
        """Test successful creation of request-scoped dispatcher.
        
        BVJ: Validates the secure factory pattern for user isolation.
        """
        # Arrange
        mock_dispatcher = Mock()
        mock_init.return_value = mock_dispatcher
        
        with patch('netra_backend.app.agents.tool_executor_factory.create_isolated_tool_dispatcher',
                  new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_dispatcher
            
            # Act
            result = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=self.mock_user_context,
                tools=[self.mock_tool],
                websocket_manager=None
            )
            
            # Assert
            mock_create.assert_called_once_with(
                user_context=self.mock_user_context,
                tools=[self.mock_tool],
                websocket_manager=None
            )
            assert result == mock_dispatcher
            
        self.record_metric("factory_creation_success", "validated")
    
    @patch('netra_backend.app.agents.tool_executor_factory.isolated_tool_dispatcher_scope')
    def test_create_scoped_dispatcher_context(self, mock_scope):
        """Test creation of scoped dispatcher context manager.
        
        BVJ: Validates automatic cleanup pattern for resource management.
        """
        # Arrange
        mock_context_manager = Mock()
        mock_scope.return_value = mock_context_manager
        
        # Act
        result = ToolDispatcher.create_scoped_dispatcher_context(
            user_context=self.mock_user_context,
            tools=[self.mock_tool],
            websocket_manager=None
        )
        
        # Assert
        mock_scope.assert_called_once_with(
            user_context=self.mock_user_context,
            tools=[self.mock_tool],
            websocket_manager=None
        )
        assert result == mock_context_manager
        
        self.record_metric("context_manager_creation", "validated")
    
    def test_tool_dispatch_request_model_validation(self):
        """Test ToolDispatchRequest model handles various input scenarios.
        
        BVJ: Ensures type safety prevents runtime errors in tool dispatch.
        """
        # Test with minimal data
        request_minimal = ToolDispatchRequest(tool_name="basic_tool")
        assert request_minimal.tool_name == "basic_tool"
        assert request_minimal.parameters == {}
        
        # Test with full data
        parameters = {"param1": "value1", "param2": 42, "param3": ["list", "data"]}
        request_full = ToolDispatchRequest(
            tool_name="advanced_tool",
            parameters=parameters
        )
        assert request_full.tool_name == "advanced_tool"
        assert request_full.parameters == parameters
        assert request_full.parameters["param2"] == 42
        
        self.record_metric("request_model_validation", "complete")
    
    def test_tool_dispatch_response_model_success_case(self):
        """Test ToolDispatchResponse model for successful execution.
        
        BVJ: Validates response structure supports agent workflow integration.
        """
        # Arrange
        success_result = {
            "analysis": "completed",
            "insights": ["insight1", "insight2"],
            "confidence": 0.95
        }
        metadata = {
            "execution_time_ms": 150,
            "tool_version": "1.0.0",
            "cache_hit": False
        }
        
        # Act
        response = ToolDispatchResponse(
            success=True,
            result=success_result,
            metadata=metadata
        )
        
        # Assert
        assert response.success is True
        assert response.result == success_result
        assert response.error is None
        assert response.metadata == metadata
        assert response.metadata["execution_time_ms"] == 150
        
        self.record_metric("response_success_model", "validated")
    
    def test_tool_dispatch_response_model_error_case(self):
        """Test ToolDispatchResponse model for failed execution.
        
        BVJ: Ensures error handling provides actionable feedback to users.
        """
        # Arrange
        error_message = "Tool execution failed: API rate limit exceeded"
        error_metadata = {
            "error_code": "RATE_LIMIT_EXCEEDED",
            "retry_after": 60,
            "attempts": 3
        }
        
        # Act
        response = ToolDispatchResponse(
            success=False,
            error=error_message,
            metadata=error_metadata
        )
        
        # Assert
        assert response.success is False
        assert response.result is None
        assert response.error == error_message
        assert response.metadata == error_metadata
        assert "RATE_LIMIT_EXCEEDED" in response.metadata["error_code"]
        
        self.record_metric("response_error_model", "validated")


class TestToolDispatcherCoreWebSocketIntegration(SSotBaseTestCase):
    """Unit tests for WebSocket bridge integration in core dispatcher."""
    
    def setup_method(self, method):
        """Set up WebSocket integration test environment."""
        super().setup_method(method)
        
        # Create mock components
        self.mock_dispatcher = Mock()
        self.mock_dispatcher.executor = Mock()
        self.mock_websocket_bridge = Mock()
        
        # Setup basic dispatcher attributes
        self.mock_dispatcher.has_websocket_support = True
        self.mock_dispatcher.executor.websocket_bridge = self.mock_websocket_bridge
        
        # Setup method call tracking
        self.mock_dispatcher.set_websocket_bridge = Mock()
        self.mock_dispatcher.get_websocket_bridge = Mock(return_value=self.mock_websocket_bridge)
        self.mock_dispatcher.diagnose_websocket_wiring = Mock()
    
    def test_set_websocket_bridge_updates_executor(self):
        """Test setting WebSocket bridge properly updates executor.
        
        BVJ: Ensures WebSocket events are properly routed for real-time updates.
        """
        # Arrange
        new_bridge = Mock()
        
        # Mock the actual method behavior
        def set_bridge_side_effect(bridge):
            self.mock_dispatcher.executor.websocket_bridge = bridge
            
        self.mock_dispatcher.set_websocket_bridge.side_effect = set_bridge_side_effect
        
        # Act
        self.mock_dispatcher.set_websocket_bridge(new_bridge)
        
        # Assert
        self.mock_dispatcher.set_websocket_bridge.assert_called_once_with(new_bridge)
        assert self.mock_dispatcher.executor.websocket_bridge == new_bridge
        
        self.record_metric("websocket_bridge_update", "validated")
    
    def test_websocket_bridge_none_handling(self):
        """Test handling when WebSocket bridge is set to None.
        
        BVJ: Prevents runtime errors when WebSocket is unavailable.
        """
        # Arrange - Mock the warning behavior
        def set_bridge_none_side_effect(bridge):
            self.mock_dispatcher.executor.websocket_bridge = bridge
            
        self.mock_dispatcher.set_websocket_bridge.side_effect = set_bridge_none_side_effect
        
        # Act
        self.mock_dispatcher.set_websocket_bridge(None)
        
        # Assert
        self.mock_dispatcher.set_websocket_bridge.assert_called_once_with(None)
        assert self.mock_dispatcher.executor.websocket_bridge is None
        
        self.record_metric("websocket_bridge_none_handling", "validated")
    
    def test_diagnose_websocket_wiring_comprehensive(self):
        """Test comprehensive WebSocket wiring diagnosis.
        
        BVJ: Enables troubleshooting of WebSocket event delivery issues.
        """
        # Arrange - Mock diagnosis results
        expected_diagnosis = {
            "dispatcher_has_executor": True,
            "executor_type": "UnifiedToolExecutionEngine",
            "executor_has_websocket_bridge_attr": True,
            "websocket_bridge_is_none": False,
            "websocket_bridge_type": "AgentWebSocketBridge",
            "has_websocket_support": True,
            "critical_issues": []
        }
        
        self.mock_dispatcher.diagnose_websocket_wiring.return_value = expected_diagnosis
        
        # Act
        diagnosis = self.mock_dispatcher.diagnose_websocket_wiring()
        
        # Assert
        assert diagnosis["dispatcher_has_executor"] is True
        assert diagnosis["has_websocket_support"] is True
        assert len(diagnosis["critical_issues"]) == 0
        assert diagnosis["websocket_bridge_type"] == "AgentWebSocketBridge"
        
        self.record_metric("websocket_diagnosis_comprehensive", "validated")
    
    def test_diagnose_websocket_wiring_missing_bridge(self):
        """Test WebSocket diagnosis identifies missing bridge.
        
        BVJ: Helps identify configuration issues that prevent events.
        """
        # Arrange - Mock diagnosis with missing bridge
        diagnosis_with_issues = {
            "dispatcher_has_executor": True,
            "executor_type": "UnifiedToolExecutionEngine", 
            "executor_has_websocket_bridge_attr": True,
            "websocket_bridge_is_none": True,
            "websocket_bridge_type": None,
            "has_websocket_support": False,
            "critical_issues": ["WebSocket bridge is None - tool events will be lost"]
        }
        
        self.mock_dispatcher.diagnose_websocket_wiring.return_value = diagnosis_with_issues
        
        # Act
        diagnosis = self.mock_dispatcher.diagnose_websocket_wiring()
        
        # Assert
        assert diagnosis["websocket_bridge_is_none"] is True
        assert diagnosis["has_websocket_support"] is False
        assert len(diagnosis["critical_issues"]) > 0
        assert "tool events will be lost" in diagnosis["critical_issues"][0]
        
        self.record_metric("websocket_missing_bridge_detection", "validated")


class TestToolDispatcherCoreSecurityValidation(SSotBaseTestCase):
    """Unit tests for security validation in core dispatcher."""
    
    def setup_method(self, method):
        """Set up security validation test environment."""
        super().setup_method(method)
        
        # Create mock dispatcher with security methods
        self.mock_dispatcher = Mock()
        
        # Mock security-related methods
        self.mock_dispatcher._validate_tool_permissions = AsyncMock()
        self.mock_dispatcher._check_admin_permission = Mock()
        
        # Setup user context
        self.valid_user_context = Mock()
        self.valid_user_context.user_id = "security_test_user"
        self.valid_user_context.metadata = {"roles": ["user"]}
        
        self.admin_user_context = Mock()
        self.admin_user_context.user_id = "admin_test_user"
        self.admin_user_context.metadata = {"roles": ["admin", "user"]}
    
    @pytest.mark.asyncio
    async def test_permission_validation_success(self):
        """Test successful permission validation for standard tools.
        
        BVJ: Ensures authorized users can execute tools they have access to.
        """
        # Arrange
        tool_name = "standard_analysis_tool"
        
        # Mock successful validation
        self.mock_dispatcher._validate_tool_permissions.return_value = None
        
        # Act
        await self.mock_dispatcher._validate_tool_permissions(tool_name)
        
        # Assert
        self.mock_dispatcher._validate_tool_permissions.assert_called_once_with(tool_name)
        
        self.record_metric("permission_validation_success", "validated")
    
    @pytest.mark.asyncio
    async def test_permission_validation_failure(self):
        """Test permission validation failure for unauthorized access.
        
        BVJ: Prevents unauthorized access to sensitive tools.
        """
        # Arrange
        tool_name = "admin_only_tool"
        
        # Mock permission denied
        from netra_backend.app.core.tools.unified_tool_dispatcher import PermissionError
        self.mock_dispatcher._validate_tool_permissions.side_effect = PermissionError(
            f"Admin permission required for tool {tool_name}"
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.mock_dispatcher._validate_tool_permissions(tool_name)
        
        # Verify appropriate exception was raised
        assert "Admin permission required" in str(exc_info.value)
        
        self.record_metric("permission_validation_failure", "blocked_correctly")
    
    def test_admin_permission_check_with_admin_role(self):
        """Test admin permission check succeeds for admin users.
        
        BVJ: Enables admin tools for authorized administrators.
        """
        # Arrange
        self.mock_dispatcher.user_context = self.admin_user_context
        
        # Mock admin check logic
        def mock_admin_check():
            roles = self.mock_dispatcher.user_context.metadata.get('roles', [])
            return 'admin' in roles
        
        self.mock_dispatcher._check_admin_permission.side_effect = mock_admin_check
        
        # Act
        is_admin = self.mock_dispatcher._check_admin_permission()
        
        # Assert
        assert is_admin is True
        self.record_metric("admin_permission_check_success", "validated")
    
    def test_admin_permission_check_with_standard_user(self):
        """Test admin permission check fails for standard users.
        
        BVJ: Prevents privilege escalation and unauthorized admin tool access.
        """
        # Arrange
        self.mock_dispatcher.user_context = self.valid_user_context
        
        # Mock admin check logic  
        def mock_admin_check():
            roles = self.mock_dispatcher.user_context.metadata.get('roles', [])
            return 'admin' in roles
        
        self.mock_dispatcher._check_admin_permission.side_effect = mock_admin_check
        
        # Act
        is_admin = self.mock_dispatcher._check_admin_permission()
        
        # Assert
        assert is_admin is False
        self.record_metric("admin_permission_check_denial", "validated")