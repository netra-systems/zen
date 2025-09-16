"""Test ToolDispatcher Business Logic

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise)
- Business Goal: Tool Security & User Isolation
- Value Impact: Ensures secure tool execution and proper user data isolation
- Strategic Impact: Tool security breaches = compliance violations & customer data loss
"""

import asyncio
import pytest
import warnings
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest

from langchain_core.tools import BaseTool
from netra_backend.app.agents.tool_dispatcher import (
    create_tool_dispatcher,
    create_request_scoped_tool_dispatcher,
    ToolDispatcher,
    UnifiedToolDispatcher
)


class TestToolDispatcher(BaseIntegrationTest):
    """Test ToolDispatcher pure business logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_user_context = Mock()
        self.mock_user_context.user_id = UserID("user-tool-123")
        self.mock_user_context.thread_id = ThreadID("thread-tool-456") 
        self.mock_websocket_manager = AsyncMock()

    @pytest.mark.unit
    def test_legacy_dispatcher_deprecation_business_warning(self):
        """Test legacy dispatcher raises appropriate business warnings."""
        # Business Value: Prevents isolation issues that could compromise user data
        
        # Capture deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Test legacy factory method
            dispatcher = create_tool_dispatcher()
            
            # Verify deprecation warning for business risk
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, DeprecationWarning))
            self.assertIn("isolation issues", str(w[0].message))

    @pytest.mark.unit
    def test_request_scoped_dispatcher_business_isolation(self):
        """Test request-scoped dispatcher ensures proper user isolation."""
        # Business Value: Proper isolation prevents data leaks between users
        
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory') as mock_factory:
            mock_dispatcher = Mock(spec=UnifiedToolDispatcher)
            mock_factory.create_for_request.return_value = mock_dispatcher
            
            # Create request-scoped dispatcher
            result = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=[]
            )
            
            # Verify proper factory usage for business isolation
            mock_factory.create_for_request.assert_called_once_with(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=[]
            )
            self.assertEqual(result, mock_dispatcher)

    @pytest.mark.unit
    def test_tool_security_validation_business_protection(self):
        """Test tool security validation protects business operations."""
        # Business Value: Prevents unauthorized tool access that could breach security
        
        # Mock a secure tool
        mock_tool = Mock(spec=BaseTool)
        mock_tool.name = "sensitive_database_query"
        mock_tool.description = "Access customer financial data"
        
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory') as mock_factory:
            mock_dispatcher = Mock(spec=UnifiedToolDispatcher)
            mock_dispatcher.has_tool.return_value = True
            mock_factory.create_for_request.return_value = mock_dispatcher
            
            dispatcher = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager,
                tools=[mock_tool]
            )
            
            # Verify tool registration with business context
            mock_factory.create_for_request.assert_called_once()
            call_kwargs = mock_factory.create_for_request.call_args.kwargs
            self.assertEqual(call_kwargs['tools'], [mock_tool])

    @pytest.mark.unit
    def test_websocket_integration_business_transparency(self):
        """Test WebSocket integration provides business operation transparency."""
        # Business Value: Real-time tool execution updates improve user trust
        
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory') as mock_factory:
            mock_dispatcher = Mock(spec=UnifiedToolDispatcher)
            mock_factory.create_for_request.return_value = mock_dispatcher
            
            # Create dispatcher with WebSocket manager
            dispatcher = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # Verify WebSocket manager is passed for business transparency
            call_kwargs = mock_factory.create_for_request.call_args.kwargs
            self.assertEqual(call_kwargs['websocket_manager'], self.mock_websocket_manager)

    @pytest.mark.unit
    def test_user_context_propagation_business_compliance(self):
        """Test user context propagation for compliance and auditing."""
        # Business Value: Proper context tracking enables audit trails and compliance
        
        # Set up user context with business-relevant data
        self.mock_user_context.session_id = "session-audit-789"
        self.mock_user_context.permissions = ["read_data", "analyze_costs"]
        
        with patch('netra_backend.app.agents.tool_dispatcher.UnifiedToolDispatcherFactory') as mock_factory:
            mock_dispatcher = Mock(spec=UnifiedToolDispatcher)
            mock_factory.create_for_request.return_value = mock_dispatcher
            
            # Create dispatcher with full user context
            dispatcher = create_request_scoped_tool_dispatcher(
                user_context=self.mock_user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # Verify complete user context propagation for business compliance
            call_kwargs = mock_factory.create_for_request.call_args.kwargs
            self.assertEqual(call_kwargs['user_context'], self.mock_user_context)

    @pytest.mark.unit
    def test_tool_dispatcher_alias_business_compatibility(self):
        """Test ToolDispatcher alias maintains business compatibility."""
        # Business Value: Smooth migration path prevents business disruption
        
        # Verify alias exists for backward compatibility
        self.assertEqual(ToolDispatcher, UnifiedToolDispatcher)
        
        # Verify it's the same class reference
        self.assertTrue(ToolDispatcher is UnifiedToolDispatcher)

    @pytest.mark.unit
    def test_production_tool_support_business_operations(self):
        """Test production tool support for business-critical operations."""
        # Business Value: Production tools enable real business value delivery
        
        # Test production tool import handling
        with patch('netra_backend.app.agents.tool_dispatcher.ProductionTool') as mock_prod_tool:
            mock_prod_tool.return_value = Mock()
            
            # Verify production tools can be imported
            from netra_backend.app.agents.tool_dispatcher import ProductionTool
            self.assertIsNotNone(ProductionTool)

    @pytest.mark.unit
    def test_tool_execution_result_business_standardization(self):
        """Test tool execution results follow business standard formats."""
        # Business Value: Consistent result formats enable reliable business logic
        
        # Test core tool models import
        from netra_backend.app.agents.tool_dispatcher import ToolExecutionResult, UnifiedTool
        
        # Verify business-standard result types exist
        self.assertIsNotNone(ToolExecutionResult)
        self.assertIsNotNone(UnifiedTool)

    @pytest.mark.unit
    def test_dispatch_strategy_business_flexibility(self):
        """Test dispatch strategies provide business operation flexibility."""
        # Business Value: Different strategies optimize for different business scenarios
        
        from netra_backend.app.agents.tool_dispatcher import DispatchStrategy
        
        # Verify dispatch strategy options for business flexibility
        self.assertIsNotNone(DispatchStrategy)

    @pytest.mark.unit
    def test_tool_dispatch_models_business_typing(self):
        """Test tool dispatch models provide business-safe typing."""
        # Business Value: Strong typing prevents business logic errors
        
        from netra_backend.app.agents.tool_dispatcher import (
            ToolDispatchRequest,
            ToolDispatchResponse
        )
        
        # Test request model business validation
        request = ToolDispatchRequest(
            tool_name="cost_analyzer",
            parameters={"timeframe": "30_days", "include_projections": True}
        )
        
        self.assertEqual(request.tool_name, "cost_analyzer")
        self.assertEqual(request.parameters["timeframe"], "30_days")
        self.assertTrue(request.parameters["include_projections"])
        
        # Test response model business structure
        response = ToolDispatchResponse(
            success=True,
            result={"savings_identified": "$5000/month"},
            metadata={"execution_time_ms": 2500}
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.result["savings_identified"], "$5000/month")
        self.assertEqual(response.metadata["execution_time_ms"], 2500)