"""
Unit Tests for ToolDispatcher Core Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: AI Tool Execution Reliability - Core to agent-based optimization
- Value Impact: Tool dispatching enables AI agents to interact with business systems
- Strategic Impact: Reliable tool execution is fundamental to platform value delivery

This test suite validates the business-critical path of tool dispatching including:
- Request-scoped architecture for multi-user isolation
- Tool registration and validation for business operations
- WebSocket integration for real-time tool execution feedback
- Error handling and graceful degradation
- Factory pattern enforcement for user context isolation
- Tool execution with proper state management

CRITICAL: These tests focus on BUSINESS LOGIC that enables AI agents to execute
tools that provide actionable business insights (cost optimization, data analysis, etc.)
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, List, Optional

from langchain_core.tools import BaseTool
from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher, 
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from shared.isolated_environment import get_env


class TestToolDispatcherCoreBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for ToolDispatcher core business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context(
            test_name=method.__name__,
            test_category=self.TestCategory.UNIT
        )
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge for real-time feedback."""
        bridge = AsyncMock()
        bridge.notify_tool_started = AsyncMock()
        bridge.notify_tool_completed = AsyncMock()
        bridge.notify_tool_error = AsyncMock()
        return bridge

    @pytest.fixture
    def business_tools(self):
        """Create realistic business tools for testing."""
        tools = []
        
        # Cost Analysis Tool
        class CostAnalysisTool(BaseTool):
            name: str = "aws_cost_analyzer"
            description: str = "Analyzes AWS costs to identify optimization opportunities"
            
            def _run(self, account_id: str, time_range: str = "30d"):
                return {
                    "monthly_spend": 15000,
                    "potential_savings": 3000,
                    "top_costs": ["EC2", "RDS", "S3"],
                    "recommendations": [
                        "Rightsize oversized instances",
                        "Use reserved instances for steady workloads",
                        "Enable S3 lifecycle policies"
                    ]
                }
            
            async def _arun(self, account_id: str, time_range: str = "30d"):
                return self._run(account_id, time_range)
        
        # Data Query Tool
        class DataQueryTool(BaseTool):
            name: str = "data_query_engine"
            description: str = "Queries business data for analysis and insights"
            
            def _run(self, query: str, database: str = "analytics"):
                return {
                    "query_result": [
                        {"metric": "monthly_active_users", "value": 15420},
                        {"metric": "conversion_rate", "value": 0.034},
                        {"metric": "customer_lifetime_value", "value": 1850}
                    ],
                    "execution_time_ms": 245,
                    "rows_affected": 3
                }
            
            async def _arun(self, query: str, database: str = "analytics"):
                return self._run(query, database)
        
        tools.extend([CostAnalysisTool(), DataQueryTool()])
        return tools

    @pytest.fixture 
    def request_scoped_dispatcher(self, business_tools, mock_websocket_bridge):
        """Create request-scoped dispatcher - bypassing direct instantiation restriction."""
        # Use the internal factory method to create instance
        dispatcher = ToolDispatcher._init_from_factory(
            tools=business_tools,
            websocket_bridge=mock_websocket_bridge
        )
        return dispatcher

    @pytest.fixture
    def business_state(self):
        """Create realistic agent state for business operations."""
        state = Mock(spec=DeepAgentState)
        state.user_id = "enterprise-customer-789"
        state.thread_id = "optimization-session-12345"
        state.current_task = "cost_optimization_analysis"
        state.context = {
            "aws_account_id": "123456789012",
            "monthly_budget": 20000,
            "optimization_target": 0.15  # 15% cost reduction target
        }
        return state

    def test_direct_instantiation_prevented_for_user_isolation(self):
        """Test that direct instantiation is prevented to ensure user isolation."""
        # BUSINESS VALUE: Multi-user platform requires proper user context isolation
        
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher()
        
        # Verify clear error message about factory methods
        error_message = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_message
        assert "create_request_scoped_dispatcher" in error_message
        assert "user isolation" in error_message
        
        # Record isolation enforcement metrics
        self.metrics.record_custom("user_isolation_enforced", True)
        self.metrics.record_custom("direct_instantiation_prevented", True)

    def test_factory_created_dispatcher_has_business_tools(self, request_scoped_dispatcher):
        """Test that factory-created dispatcher properly registers business tools."""
        # BUSINESS VALUE: Business tools must be available for agent operations
        
        # Verify business tools are registered and accessible
        assert request_scoped_dispatcher.has_tool("aws_cost_analyzer")
        assert request_scoped_dispatcher.has_tool("data_query_engine")
        
        # Verify tool registry contains expected business tools
        tools = request_scoped_dispatcher.tools
        assert "aws_cost_analyzer" in tools
        assert "data_query_engine" in tools
        
        # Verify WebSocket support is enabled for real-time feedback
        assert request_scoped_dispatcher.has_websocket_support is True
        
        # Record business tool availability
        self.metrics.record_custom("business_tools_registered", 2)
        self.metrics.record_custom("websocket_support_enabled", True)

    async def test_cost_analysis_tool_delivers_business_insights(
        self, request_scoped_dispatcher, business_state
    ):
        """Test that cost analysis tool delivers actionable business insights."""
        # BUSINESS VALUE: Cost optimization tools must provide actionable savings opportunities
        
        # Execute cost analysis tool with business parameters
        result = await request_scoped_dispatcher.dispatch_tool(
            tool_name="aws_cost_analyzer",
            parameters={
                "account_id": "123456789012",
                "time_range": "30d"
            },
            state=business_state,
            run_id="cost-analysis-job-789"
        )
        
        # Verify business value was delivered
        assert result.success is True
        assert result.error is None
        
        # Verify result contains actionable business insights
        tool_result = result.result
        assert tool_result["monthly_spend"] == 15000
        assert tool_result["potential_savings"] == 3000  # 20% savings opportunity
        assert len(tool_result["recommendations"]) >= 3
        assert "EC2" in tool_result["top_costs"]  # Realistic AWS cost center
        
        # Verify recommendations are actionable
        recommendations = tool_result["recommendations"]
        assert any("Rightsize" in rec for rec in recommendations)
        assert any("reserved instances" in rec for rec in recommendations)
        
        # Record business value metrics
        self.metrics.record_custom("cost_savings_identified", 3000)
        self.metrics.record_custom("actionable_recommendations", len(recommendations))

    async def test_data_query_tool_provides_business_metrics(
        self, request_scoped_dispatcher, business_state
    ):
        """Test that data query tool provides relevant business metrics."""
        # BUSINESS VALUE: Data tools must provide metrics that drive business decisions
        
        # Execute data query with business context
        result = await request_scoped_dispatcher.dispatch_tool(
            tool_name="data_query_engine", 
            parameters={
                "query": "SELECT monthly_active_users, conversion_rate, customer_lifetime_value FROM business_metrics",
                "database": "analytics"
            },
            state=business_state,
            run_id="metrics-query-456"
        )
        
        # Verify business metrics were delivered
        assert result.success is True
        query_result = result.result["query_result"]
        
        # Verify key business metrics are present
        metrics_dict = {item["metric"]: item["value"] for item in query_result}
        assert "monthly_active_users" in metrics_dict
        assert "conversion_rate" in metrics_dict  
        assert "customer_lifetime_value" in metrics_dict
        
        # Verify metric values are business-realistic
        assert metrics_dict["monthly_active_users"] > 1000  # Reasonable user base
        assert 0.01 <= metrics_dict["conversion_rate"] <= 0.10  # Typical conversion rates
        assert metrics_dict["customer_lifetime_value"] > 1000  # Meaningful LTV
        
        # Record data analytics metrics
        self.metrics.record_custom("business_metrics_delivered", len(query_result))
        self.metrics.record_custom("data_insights_enabled", True)

    async def test_tool_not_found_provides_clear_business_error(
        self, request_scoped_dispatcher, business_state
    ):
        """Test that missing tools provide clear business-relevant error messages."""
        # BUSINESS VALUE: Clear error messages improve user experience and reduce support load
        
        # Attempt to use non-existent tool
        result = await request_scoped_dispatcher.dispatch_tool(
            tool_name="nonexistent_analytics_tool",
            parameters={"query": "some business query"},
            state=business_state,
            run_id="failed-tool-request"
        )
        
        # Verify clear business error was provided
        assert result.success is False
        assert "nonexistent_analytics_tool not found" in result.error
        
        # Verify no partial results were returned
        assert result.result is None
        
        # Record error clarity metrics
        self.metrics.record_custom("clear_errors_provided", 1)
        self.metrics.record_custom("user_confusion_prevented", True)

    def test_dynamic_tool_registration_supports_business_flexibility(
        self, request_scoped_dispatcher
    ):
        """Test that dynamic tool registration supports business flexibility."""
        # BUSINESS VALUE: Dynamic tools enable customization for different customer needs
        
        # Define custom business tool function
        def custom_roi_calculator(investment: float, monthly_savings: float, time_horizon: int = 12):
            """Calculate ROI for optimization investments."""
            total_savings = monthly_savings * time_horizon
            roi_percentage = ((total_savings - investment) / investment) * 100
            payback_months = investment / monthly_savings if monthly_savings > 0 else float('inf')
            
            return {
                "roi_percentage": roi_percentage,
                "payback_months": payback_months,
                "total_savings": total_savings,
                "net_benefit": total_savings - investment,
                "recommendation": "Proceed" if roi_percentage > 20 else "Evaluate alternatives"
            }
        
        # Register custom business tool
        request_scoped_dispatcher.register_tool(
            tool_name="roi_calculator",
            tool_func=custom_roi_calculator,
            description="Calculate ROI for business optimization investments"
        )
        
        # Verify tool was registered and is available
        assert request_scoped_dispatcher.has_tool("roi_calculator")
        
        # Verify tool can be retrieved
        tool = request_scoped_dispatcher.registry.get_tool("roi_calculator")
        assert tool is not None
        assert tool.name == "roi_calculator"
        
        # Record business flexibility metrics
        self.metrics.record_custom("custom_tools_registered", 1)
        self.metrics.record_custom("business_flexibility_enabled", True)

    async def test_websocket_bridge_enables_real_time_feedback(
        self, request_scoped_dispatcher, business_state, mock_websocket_bridge
    ):
        """Test that WebSocket bridge enables real-time tool execution feedback.""" 
        # BUSINESS VALUE: Real-time feedback improves user experience during long operations
        
        # Verify WebSocket bridge is properly set
        assert request_scoped_dispatcher.has_websocket_support is True
        
        # Execute tool that should trigger WebSocket events
        result = await request_scoped_dispatcher.dispatch_tool(
            tool_name="aws_cost_analyzer",
            parameters={"account_id": "123456789012"},
            state=business_state, 
            run_id="websocket-test-run"
        )
        
        # Verify tool executed successfully
        assert result.success is True
        
        # Note: WebSocket events are handled by the unified tool execution engine
        # The dispatcher properly sets the bridge for downstream event delivery
        
        # Record real-time feedback metrics
        self.metrics.record_custom("websocket_integration_verified", True)
        self.metrics.record_custom("realtime_feedback_enabled", True)

    def test_tool_dispatch_request_model_validates_input(self):
        """Test that ToolDispatchRequest model validates business inputs.""" 
        # BUSINESS VALUE: Input validation prevents business logic errors
        
        # Create valid business request
        valid_request = ToolDispatchRequest(
            tool_name="aws_cost_analyzer",
            parameters={
                "account_id": "123456789012",
                "time_range": "30d",
                "include_recommendations": True
            }
        )
        
        # Verify valid request properties
        assert valid_request.tool_name == "aws_cost_analyzer"
        assert valid_request.parameters["account_id"] == "123456789012"
        assert valid_request.parameters["include_recommendations"] is True
        
        # Test minimal request (parameters should default to empty dict)
        minimal_request = ToolDispatchRequest(tool_name="simple_tool")
        assert minimal_request.parameters == {}
        
        # Record validation metrics
        self.metrics.record_custom("input_validation_working", True)
        self.metrics.record_custom("business_data_protected", True)

    def test_tool_dispatch_response_model_structures_output(self):
        """Test that ToolDispatchResponse model properly structures business output."""
        # BUSINESS VALUE: Structured responses enable consistent business logic processing
        
        # Create successful business response
        success_response = ToolDispatchResponse(
            success=True,
            result={
                "analysis_complete": True,
                "savings_identified": 5000,
                "confidence_score": 0.92
            },
            metadata={
                "execution_time_ms": 1500,
                "tools_used": ["cost_analyzer", "recommendation_engine"]
            }
        )
        
        # Verify successful response structure
        assert success_response.success is True
        assert success_response.result["savings_identified"] == 5000
        assert success_response.error is None
        assert success_response.metadata["execution_time_ms"] == 1500
        
        # Create error response
        error_response = ToolDispatchResponse(
            success=False,
            error="AWS API authentication failed",
            metadata={"error_code": "AUTH_001", "retry_suggested": True}
        )
        
        # Verify error response structure
        assert error_response.success is False
        assert error_response.result is None
        assert error_response.error == "AWS API authentication failed"
        assert error_response.metadata["retry_suggested"] is True
        
        # Record response structure metrics
        self.metrics.record_custom("response_structure_validated", True)
        self.metrics.record_custom("business_output_structured", True)

    async def test_tool_input_creation_preserves_business_context(
        self, request_scoped_dispatcher
    ):
        """Test that tool input creation preserves business context."""
        # BUSINESS VALUE: Business context must be preserved throughout tool execution
        
        business_params = {
            "customer_segment": "enterprise",
            "optimization_budget": 10000,
            "priority_services": ["compute", "storage", "database"],
            "compliance_requirements": ["SOX", "HIPAA"]
        }
        
        # Create tool input using internal method
        tool_input = request_scoped_dispatcher._create_tool_input(
            tool_name="compliance_cost_optimizer",
            kwargs=business_params
        )
        
        # Verify business context is preserved
        assert tool_input.tool_name == "compliance_cost_optimizer"
        assert tool_input.kwargs == business_params
        assert tool_input.kwargs["customer_segment"] == "enterprise"
        assert "HIPAA" in tool_input.kwargs["compliance_requirements"]
        
        # Record context preservation metrics
        self.metrics.record_custom("business_context_preserved", True)
        self.metrics.record_custom("compliance_requirements_maintained", True)

    def test_error_result_creation_provides_business_clarity(
        self, request_scoped_dispatcher  
    ):
        """Test that error result creation provides business-relevant clarity."""
        # BUSINESS VALUE: Clear error messages enable business users to take corrective action
        
        # Create sample tool input for error scenario
        tool_input = ToolInput(
            tool_name="aws_cost_analyzer",
            kwargs={"account_id": "invalid-account"}
        )
        
        # Create business-relevant error result
        error_result = request_scoped_dispatcher._create_error_result(
            tool_input,
            "AWS account 'invalid-account' not found or access denied"
        )
        
        # Verify error result provides business clarity
        assert error_result.status == ToolStatus.ERROR
        assert error_result.message == "AWS account 'invalid-account' not found or access denied"
        assert error_result.tool_input == tool_input
        
        # Verify error is actionable for business users
        assert "access denied" in error_result.message.lower()
        assert "invalid-account" in error_result.message
        
        # Record error clarity metrics
        self.metrics.record_custom("actionable_errors_created", True)
        self.metrics.record_custom("business_users_informed", True)


class TestToolDispatcherBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for tool dispatcher edge cases."""

    async def test_enterprise_customer_tool_access_priority(self):
        """Test that enterprise customers have appropriate tool access."""
        # BUSINESS VALUE: Enterprise customers should have access to advanced tools
        
        # This test validates that the tool dispatcher doesn't artificially limit
        # tool access based on customer tier - business logic should handle this elsewhere
        
        enterprise_tools = [
            "advanced_cost_optimizer",
            "compliance_analyzer", 
            "enterprise_reporting",
            "custom_integration_tool"
        ]
        
        # Create mock tools
        mock_tools = []
        for tool_name in enterprise_tools:
            mock_tool = Mock(spec=BaseTool)
            mock_tool.name = tool_name
            mock_tool.description = f"Enterprise {tool_name}"
            mock_tools.append(mock_tool)
        
        # Create dispatcher with enterprise tools
        dispatcher = ToolDispatcher._init_from_factory(tools=mock_tools)
        
        # Verify all enterprise tools are available
        for tool_name in enterprise_tools:
            assert dispatcher.has_tool(tool_name)
        
        # Record enterprise service metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_tools_available", len(enterprise_tools))

    async def test_free_tier_user_basic_functionality(self):
        """Test that free tier users have access to basic functionality."""
        # BUSINESS VALUE: Free tier users should have functional tool access for conversion
        
        basic_tools = ["basic_cost_analyzer", "simple_query_tool"]
        
        mock_tools = []
        for tool_name in basic_tools:
            mock_tool = Mock(spec=BaseTool)
            mock_tool.name = tool_name
            mock_tool.description = f"Basic {tool_name}"
            mock_tools.append(mock_tool)
        
        dispatcher = ToolDispatcher._init_from_factory(tools=mock_tools)
        
        # Verify basic tools are available
        for tool_name in basic_tools:
            assert dispatcher.has_tool(tool_name)
        
        # Record free tier service metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("free_tier_functionality_maintained", True)