"""Test ToolDispatcherExecution Business Logic

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise)
- Business Goal: Tool Execution Engine & Result Processing
- Value Impact: Ensures reliable tool execution and proper business result handling  
- Strategic Impact: Tool execution failures = AI capability breakdowns & user frustration
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest

from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput,
    ToolResult,
    ToolExecuteResponse,
    ToolStatus
)


class TestToolDispatcherExecution(BaseIntegrationTest):
    """Test ToolDispatcherExecution pure business logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_websocket_manager = AsyncMock()
        
        # Create execution engine with business WebSocket support
        self.engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)

    @pytest.mark.unit
    def test_unified_engine_delegation_business_architecture(self):
        """Test unified engine delegation ensures business consistency."""
        # Business Value: Single execution path prevents business logic fragmentation
        
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_unified.return_value = mock_core_engine
            
            # Create engine instance
            engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Verify unified engine business integration
            mock_unified.assert_called_once_with(self.mock_websocket_manager)
            self.assertEqual(engine._core_engine, mock_core_engine)

    @pytest.mark.unit
    def test_tool_input_execution_business_processing(self):
        """Test tool input execution handles business data properly."""
        # Business Value: Proper input processing ensures accurate business outcomes
        
        # Create business-representative tool input
        business_input = ToolInput(
            tool_name="revenue_projector",
            parameters={
                "current_mrr": 50000,
                "growth_rate": 0.15,
                "projection_months": 12,
                "churn_rate": 0.05
            }
        )
        
        # Mock business tool
        mock_tool = Mock()
        mock_tool.name = "revenue_projector"
        
        # Mock business execution result
        mock_result = ToolResult(
            status=ToolStatus.SUCCESS,
            result={
                "projected_revenue": 685000,
                "monthly_breakdown": [52500, 55125, 57881],
                "confidence_interval": [0.85, 0.95]
            }
        )
        
        # Mock core engine execution
        self.engine._core_engine.execute_tool_with_input.return_value = mock_result
        
        # Test business input execution
        result = asyncio.run(
            self.engine.execute_tool_with_input(
                business_input, mock_tool, {"validate_assumptions": True}
            )
        )
        
        # Verify business result processing
        self.assertEqual(result, mock_result)
        self.engine._core_engine.execute_tool_with_input.assert_called_once_with(
            business_input, mock_tool, {"validate_assumptions": True}
        )

    @pytest.mark.unit
    def test_state_execution_business_context(self):
        """Test execution with state maintains business context."""
        # Business Value: State context enables personalized business results
        
        # Create business state context
        business_state = DeepAgentState()
        business_state.user_id = UserID("enterprise-client-456")
        business_state.subscription_tier = "enterprise"
        business_state.monthly_spend_limit = 10000
        business_state.preferred_currency = "USD"
        
        # Mock business tool
        mock_tool = Mock()
        mock_tool.name = "cost_optimizer"
        
        # Mock successful business execution
        business_execution_result = {
            "success": True,
            "result": {
                "potential_savings": 2500,
                "optimization_recommendations": [
                    "Resize oversized instances",
                    "Use reserved instances for predictable workloads"
                ]
            },
            "metadata": {
                "analysis_duration_ms": 3500,
                "resources_analyzed": 47
            }
        }
        
        self.engine._core_engine.execute_with_state.return_value = business_execution_result
        
        # Test business state execution
        result = asyncio.run(
            self.engine.execute_with_state(
                tool=mock_tool,
                tool_name="cost_optimizer", 
                parameters={"analysis_depth": "comprehensive"},
                state=business_state,
                run_id="run-cost-optimize-789"
            )
        )
        
        # Verify business result conversion
        self.assertTrue(result.success)
        self.assertEqual(result.result["potential_savings"], 2500)
        self.assertIn("optimization_recommendations", result.result)
        self.assertEqual(result.metadata["analysis_duration_ms"], 3500)

    @pytest.mark.unit
    def test_execution_error_business_handling(self):
        """Test execution errors are handled with business context."""
        # Business Value: Proper error handling prevents business disruption
        
        # Create business state
        business_state = DeepAgentState()
        business_state.user_id = UserID("user-error-123")
        
        # Mock business tool that fails
        mock_tool = Mock()
        mock_tool.name = "compliance_checker"
        
        # Mock business error result
        error_result = {
            "success": False,
            "error": "Compliance database temporarily unavailable",
            "metadata": {
                "error_code": "DB_TIMEOUT",
                "retry_after_seconds": 30,
                "business_impact": "compliance_checks_delayed"
            }
        }
        
        self.engine._core_engine.execute_with_state.return_value = error_result
        
        # Test business error handling
        result = asyncio.run(
            self.engine.execute_with_state(
                tool=mock_tool,
                tool_name="compliance_checker",
                parameters={"check_type": "gdpr_compliance"},
                state=business_state,
                run_id="run-compliance-456"
            )
        )
        
        # Verify business error response
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Compliance database temporarily unavailable")
        self.assertEqual(result.metadata["error_code"], "DB_TIMEOUT")
        self.assertEqual(result.metadata["business_impact"], "compliance_checks_delayed")

    @pytest.mark.unit
    def test_tool_interface_implementation_business_compliance(self):
        """Test tool interface implementation meets business requirements."""
        # Business Value: Standard interfaces enable predictable business integrations
        
        # Mock successful tool execution
        business_response = ToolExecuteResponse(
            success=True,
            result={
                "customer_lifetime_value": 15000,
                "segment": "high_value",
                "engagement_score": 0.87
            },
            metadata={
                "calculation_method": "predictive_model_v3",
                "data_points_used": 156
            }
        )
        
        self.engine._core_engine.execute_tool.return_value = business_response
        
        # Test business interface implementation
        result = asyncio.run(
            self.engine.execute_tool(
                tool_name="customer_value_calculator",
                parameters={
                    "customer_id": "cust-789",
                    "include_predictions": True
                }
            )
        )
        
        # Verify business interface compliance
        self.assertEqual(result, business_response)
        self.engine._core_engine.execute_tool.assert_called_once_with(
            "customer_value_calculator",
            {"customer_id": "cust-789", "include_predictions": True}
        )

    @pytest.mark.unit
    def test_websocket_integration_business_transparency(self):
        """Test WebSocket integration provides business operation transparency."""
        # Business Value: Real-time execution feedback improves user experience
        
        # Create engine with WebSocket manager
        engine_with_ws = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
        
        # Verify WebSocket manager is passed to core engine
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Verify business transparency setup
            mock_unified.assert_called_once_with(self.mock_websocket_manager)

    @pytest.mark.unit
    def test_result_metadata_business_intelligence(self):
        """Test result metadata provides business intelligence insights."""
        # Business Value: Execution metadata enables performance optimization decisions
        
        # Create business state with performance tracking
        business_state = DeepAgentState()
        business_state.user_id = UserID("performance-user-123")
        business_state.execution_start_time = 1640995200  # 2022-01-01
        
        # Mock tool with performance metadata
        mock_tool = Mock()
        mock_tool.name = "performance_analyzer"
        
        # Mock result with business intelligence metadata
        performance_result = {
            "success": True,
            "result": {"analysis_complete": True},
            "metadata": {
                "execution_time_ms": 2750,
                "memory_usage_mb": 45,
                "cpu_utilization": 0.23,
                "cache_hit_ratio": 0.89,
                "business_cost_cents": 12  # Cost tracking for business insights
            }
        }
        
        self.engine._core_engine.execute_with_state.return_value = performance_result
        
        # Test business intelligence metadata collection
        result = asyncio.run(
            self.engine.execute_with_state(
                tool=mock_tool,
                tool_name="performance_analyzer",
                parameters={"collect_detailed_metrics": True},
                state=business_state,
                run_id="run-perf-789"
            )
        )
        
        # Verify business intelligence metadata
        self.assertEqual(result.metadata["execution_time_ms"], 2750)
        self.assertEqual(result.metadata["business_cost_cents"], 12)
        self.assertEqual(result.metadata["cache_hit_ratio"], 0.89)

    @pytest.mark.unit
    def test_production_tool_business_integration(self):
        """Test production tool integration for business operations."""
        # Business Value: Production tools enable real business value delivery
        
        # Test production tool import and usage
        from netra_backend.app.agents.tool_dispatcher_execution import ProductionTool
        
        # Verify production tool is available for business operations
        self.assertIsNotNone(ProductionTool)

    @pytest.mark.unit
    def test_comprehensive_error_scenarios_business_resilience(self):
        """Test comprehensive error scenarios for business resilience."""
        # Business Value: Robust error handling maintains business continuity
        
        business_state = DeepAgentState()
        business_state.user_id = UserID("resilience-user-456")
        
        mock_tool = Mock()
        mock_tool.name = "business_critical_tool"
        
        # Test various business error scenarios
        error_scenarios = [
            {
                "error": "Rate limit exceeded for API calls",
                "metadata": {"retry_after": 60, "impact": "delayed_results"}
            },
            {
                "error": "Insufficient permissions for data access", 
                "metadata": {"required_role": "data_analyst", "impact": "access_denied"}
            },
            {
                "error": "External service temporarily unavailable",
                "metadata": {"service": "billing_api", "impact": "partial_results"}
            }
        ]
        
        for scenario in error_scenarios:
            error_result = {
                "success": False,
                "error": scenario["error"],
                "metadata": scenario["metadata"]
            }
            
            self.engine._core_engine.execute_with_state.return_value = error_result
            
            result = asyncio.run(
                self.engine.execute_with_state(
                    tool=mock_tool,
                    tool_name="business_critical_tool",
                    parameters={"operation": "test"},
                    state=business_state,
                    run_id="run-resilience-test"
                )
            )
            
            # Verify business error resilience
            self.assertFalse(result.success)
            self.assertEqual(result.error, scenario["error"])
            self.assertIn("impact", result.metadata)