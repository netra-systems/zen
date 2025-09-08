"""
Unit Tests for Tool Dispatcher - Batch 2 Priority Tests (tool_dispatcher.py)

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure reliable tool dispatch operations for all user segments
- Value Impact: Prevents tool execution failures that would break agent workflows
- Strategic Impact: Core platform functionality that enables AI agent capabilities

These tests focus on the main tool_dispatcher.py facade interface, validating:
1. Factory method creation patterns
2. Backward compatibility maintenance
3. Tool registration and lookup
4. Error handling and isolation
"""

import asyncio
import pytest
import warnings
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
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


class TestToolDispatcherFacadeUnit(SSotBaseTestCase):
    """Unit tests for the main tool dispatcher facade."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = "test_user_123"
        self.mock_user_context.run_id = "test_run_456"
        self.mock_user_context.thread_id = "test_thread_789"
        self.mock_user_context.session_id = "test_session_012"
    
    def test_tool_dispatcher_alias_exists(self):
        """Test that ToolDispatcher alias exists for backward compatibility.
        
        BVJ: Ensures existing code doesn't break during migration.
        """
        # Act & Assert
        assert ToolDispatcher == UnifiedToolDispatcher
        self.record_metric("alias_validation", "passed")
    
    def test_create_tool_dispatcher_emits_deprecation_warning(self):
        """Test that legacy create_tool_dispatcher emits deprecation warning.
        
        BVJ: Guides developers toward secure request-scoped patterns.
        """
        # Act & Assert
        with pytest.warns(DeprecationWarning, match="create_tool_dispatcher.*creates global state"):
            with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_legacy_global') as mock_create:
                mock_dispatcher = Mock()
                mock_create.return_value = mock_dispatcher
                
                result = create_tool_dispatcher([])
                
                assert result == mock_dispatcher
                mock_create.assert_called_once()
        
        self.record_metric("deprecation_warning_test", "passed")
    
    @patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request')
    def test_create_request_scoped_tool_dispatcher_success(self, mock_create_for_request):
        """Test successful creation of request-scoped dispatcher.
        
        BVJ: Validates the recommended secure pattern for tool dispatch.
        """
        # Arrange
        mock_dispatcher = Mock()
        mock_create_for_request.return_value = mock_dispatcher
        mock_websocket_manager = Mock()
        mock_tools = [Mock()]
        
        # Act
        result = create_request_scoped_tool_dispatcher(
            user_context=self.mock_user_context,
            websocket_manager=mock_websocket_manager,
            tools=mock_tools
        )
        
        # Assert
        assert result == mock_dispatcher
        mock_create_for_request.assert_called_once_with(
            user_context=self.mock_user_context,
            websocket_manager=mock_websocket_manager,
            tools=mock_tools
        )
        self.record_metric("request_scoped_creation", "success")


class TestToolDispatchRequestResponseModels(SSotBaseTestCase):
    """Unit tests for tool dispatch request/response models."""
    
    def test_tool_dispatch_request_creation(self):
        """Test ToolDispatchRequest model creation with valid data.
        
        BVJ: Ensures type safety for tool dispatch operations.
        """
        # Arrange
        tool_name = "cost_analyzer"
        parameters = {"region": "us-west-2", "timeframe": "30d"}
        
        # Act
        request = ToolDispatchRequest(
            tool_name=tool_name,
            parameters=parameters
        )
        
        # Assert
        assert request.tool_name == tool_name
        assert request.parameters == parameters
        self.record_metric("request_model_validation", "passed")
    
    def test_tool_dispatch_request_defaults(self):
        """Test ToolDispatchRequest uses proper defaults.
        
        BVJ: Prevents runtime errors from missing parameters.
        """
        # Act
        request = ToolDispatchRequest(tool_name="test_tool")
        
        # Assert
        assert request.tool_name == "test_tool"
        assert request.parameters == {}
        self.record_metric("request_model_defaults", "validated")
    
    def test_tool_dispatch_response_success(self):
        """Test ToolDispatchResponse for successful execution.
        
        BVJ: Validates successful tool execution response structure.
        """
        # Arrange
        result_data = {"analysis": "cost_optimized", "savings": 1500}
        metadata = {"execution_time_ms": 250, "tool_version": "1.2.0"}
        
        # Act
        response = ToolDispatchResponse(
            success=True,
            result=result_data,
            metadata=metadata
        )
        
        # Assert
        assert response.success is True
        assert response.result == result_data
        assert response.error is None
        assert response.metadata == metadata
        self.record_metric("response_model_success", "validated")
    
    def test_tool_dispatch_response_error(self):
        """Test ToolDispatchResponse for failed execution.
        
        BVJ: Ensures proper error handling and reporting.
        """
        # Arrange
        error_message = "Tool execution timeout after 30s"
        metadata = {"execution_time_ms": 30000, "timeout_reason": "network"}
        
        # Act
        response = ToolDispatchResponse(
            success=False,
            error=error_message,
            metadata=metadata
        )
        
        # Assert
        assert response.success is False
        assert response.result is None
        assert response.error == error_message
        assert response.metadata == metadata
        self.record_metric("response_model_error", "validated")


class TestDispatchStrategy(SSotBaseTestCase):
    """Unit tests for dispatch strategy enumeration."""
    
    def test_dispatch_strategy_values(self):
        """Test all dispatch strategy values are properly defined.
        
        BVJ: Ensures strategy-based routing works correctly.
        """
        # Act & Assert
        assert DispatchStrategy.DEFAULT.value == "default"
        assert DispatchStrategy.ADMIN.value == "admin"
        assert DispatchStrategy.ISOLATED.value == "isolated"
        assert DispatchStrategy.LEGACY.value == "legacy"
        self.record_metric("strategy_enum_validation", "complete")
    
    def test_dispatch_strategy_comparison(self):
        """Test dispatch strategy enum comparison operations.
        
        BVJ: Validates strategy matching in conditional logic.
        """
        # Act & Assert
        assert DispatchStrategy.DEFAULT == DispatchStrategy.DEFAULT
        assert DispatchStrategy.ADMIN != DispatchStrategy.DEFAULT
        
        # Test string comparison
        assert DispatchStrategy.DEFAULT.value == "default"
        self.record_metric("strategy_comparison", "validated")