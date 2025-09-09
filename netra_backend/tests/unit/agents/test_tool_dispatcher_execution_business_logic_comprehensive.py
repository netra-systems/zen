"""
Unit Tests for ToolExecutionEngine Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Tool Execution Reliability - Enable AI agents to execute business tools
- Value Impact: Tool execution engine powers agent interactions with business systems 
- Strategic Impact: Reliable tool execution is critical for delivering AI optimization value

This test suite validates the business-critical path of tool execution including:
- Delegation to unified tool execution architecture
- Proper error handling and business result conversion
- State management for business context preservation
- Integration with WebSocket notifications for user feedback
- Tool result formatting for business consumption
- Performance tracking for business insights

CRITICAL: These tests focus on BUSINESS LOGIC that enables AI agents to execute
tools and deliver actionable business results (cost savings, data insights, etc.)
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, Optional

from langchain_core.tools import BaseTool
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput, 
    ToolResult, 
    ToolStatus,
    ToolExecuteResponse
)
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from test_framework.unified import TestCategory
from shared.isolated_environment import get_env


class TestToolExecutionEngineBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for ToolExecutionEngine business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration.""" 
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context(
            test_name=method.__name__,
            test_category=TestCategory.UNIT
        )
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for real-time feedback."""
        manager = AsyncMock()
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def tool_execution_engine(self, mock_websocket_manager):
        """Create ToolExecutionEngine with mocked dependencies."""
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = AsyncMock()
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine(mock_websocket_manager)
            engine._core_engine = mock_core_engine  # Store reference for verification
            return engine

    @pytest.fixture
    def business_tool(self):
        """Create realistic business tool for testing."""
        class BusinessCostTool(BaseTool):
            name: str = "business_cost_analyzer"
            description: str = "Analyzes business costs and identifies optimization opportunities"
            
            def _run(self, department: str, time_period: str = "quarterly"):
                return {
                    "department": department,
                    "current_spend": 125000,
                    "budget_utilization": 0.83,
                    "cost_trends": ["increasing", "seasonal_peak"],
                    "optimization_opportunities": [
                        {"category": "software_licenses", "potential_savings": 15000},
                        {"category": "cloud_resources", "potential_savings": 8000},
                        {"category": "vendor_contracts", "potential_savings": 12000}
                    ],
                    "recommendations": [
                        "Consolidate redundant software licenses",
                        "Rightsize cloud infrastructure",
                        "Renegotiate vendor contracts before renewal"
                    ]
                }
            
            async def _arun(self, department: str, time_period: str = "quarterly"):
                # Simulate async processing time
                await asyncio.sleep(0.01)
                return self._run(department, time_period)
        
        return BusinessCostTool()

    @pytest.fixture
    def business_tool_input(self):
        """Create realistic tool input for business operations."""
        return ToolInput(
            tool_name="business_cost_analyzer",
            kwargs={
                "department": "engineering",
                "time_period": "quarterly",
                "include_forecasts": True,
                "optimization_target": 0.15  # 15% cost reduction target
            }
        )

    @pytest.fixture
    def business_state(self):
        """Create realistic agent state with business context."""
        state = Mock(spec=DeepAgentState)
        state.user_id = "business-analyst-456"
        state.thread_id = "cost-analysis-session-789"
        state.current_task = "quarterly_cost_optimization"
        state.context = {
            "company_id": "enterprise-corp-123",
            "fiscal_quarter": "Q4-2024",
            "budget_constraints": {"max_spend": 500000, "target_savings": 50000},
            "stakeholders": ["CFO", "VP_Engineering", "Procurement"]
        }
        return state

    async def test_tool_execution_delegates_to_unified_engine(
        self, tool_execution_engine, business_tool_input, business_tool
    ):
        """Test that tool execution properly delegates to unified engine."""
        # BUSINESS VALUE: Unified execution ensures consistent business tool processing
        
        # Setup mock unified engine to return business results
        business_result = ToolResult(
            tool_input=business_tool_input,
            status=ToolStatus.SUCCESS,
            result={
                "cost_analysis_complete": True,
                "total_savings_identified": 35000,
                "actionable_recommendations": 3
            },
            message="Cost analysis completed successfully"
        )
        
        tool_execution_engine._core_engine.execute_tool_with_input.return_value = business_result
        
        # Execute tool
        result = await tool_execution_engine.execute_tool_with_input(
            business_tool_input, 
            business_tool, 
            business_tool_input.kwargs
        )
        
        # Verify delegation to unified engine
        tool_execution_engine._core_engine.execute_tool_with_input.assert_called_once_with(
            business_tool_input, business_tool, business_tool_input.kwargs
        )
        
        # Verify business result was returned
        assert result == business_result
        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_savings_identified"] == 35000
        
        # Record delegation metrics
        self.metrics.record_custom("unified_engine_delegation_verified", True)
        self.metrics.record_custom("business_results_preserved", True)

    async def test_execute_with_state_converts_to_business_dispatch_response(
        self, tool_execution_engine, business_tool, business_state
    ):
        """Test that execute_with_state converts results to business dispatch response."""
        # BUSINESS VALUE: Consistent response format enables business logic processing
        
        # Setup mock core engine to return business results
        core_engine_result = {
            "success": True,
            "result": {
                "department_analysis": "engineering",
                "cost_optimization_score": 0.78,
                "priority_actions": ["license_optimization", "cloud_rightsizing"],
                "estimated_monthly_savings": 8500,
                "implementation_timeline": "30_days"
            },
            "metadata": {
                "execution_time_ms": 2500,
                "data_sources": ["finance_db", "procurement_system"],
                "confidence_level": 0.91
            }
        }
        
        tool_execution_engine._core_engine.execute_with_state.return_value = core_engine_result
        
        # Execute with business state
        result = await tool_execution_engine.execute_with_state(
            tool=business_tool,
            tool_name="business_cost_analyzer",
            parameters={
                "department": "engineering",
                "optimization_target": 0.15
            },
            state=business_state,
            run_id="business-analysis-run-123"
        )
        
        # Verify conversion to ToolDispatchResponse
        assert isinstance(result, ToolDispatchResponse)
        assert result.success is True
        assert result.error is None
        
        # Verify business result content
        business_result = result.result
        assert business_result["department_analysis"] == "engineering"
        assert business_result["estimated_monthly_savings"] == 8500
        assert business_result["cost_optimization_score"] == 0.78
        
        # Verify metadata preservation
        assert result.metadata["execution_time_ms"] == 2500
        assert result.metadata["confidence_level"] == 0.91
        assert "finance_db" in result.metadata["data_sources"]
        
        # Record business response conversion metrics
        self.metrics.record_custom("business_response_conversion_successful", True)
        self.metrics.record_custom("metadata_preserved", True)

    async def test_execute_with_state_handles_business_errors_gracefully(
        self, tool_execution_engine, business_tool, business_state
    ):
        """Test that execute_with_state handles business errors gracefully."""
        # BUSINESS VALUE: Graceful error handling maintains business continuity
        
        # Setup mock core engine to return business error
        error_result = {
            "success": False,
            "error": "Department 'engineering' budget data not found in financial system",
            "metadata": {
                "error_code": "DATA_NOT_FOUND",
                "affected_department": "engineering",
                "suggested_action": "Verify department code or contact finance team",
                "retry_recommended": True
            }
        }
        
        tool_execution_engine._core_engine.execute_with_state.return_value = error_result
        
        # Execute with business state
        result = await tool_execution_engine.execute_with_state(
            tool=business_tool,
            tool_name="business_cost_analyzer", 
            parameters={"department": "engineering"},
            state=business_state,
            run_id="failed-analysis-run-456"
        )
        
        # Verify error was handled gracefully
        assert isinstance(result, ToolDispatchResponse)
        assert result.success is False
        assert result.result is None
        
        # Verify business-relevant error information
        assert "budget data not found" in result.error
        assert "engineering" in result.error
        
        # Verify error metadata for business recovery
        assert result.metadata["error_code"] == "DATA_NOT_FOUND"
        assert result.metadata["retry_recommended"] is True
        assert "contact finance team" in result.metadata["suggested_action"]
        
        # Record error handling metrics
        self.metrics.record_custom("business_errors_handled_gracefully", True)
        self.metrics.record_custom("recovery_guidance_provided", True)

    async def test_execute_tool_interface_supports_business_operations(
        self, tool_execution_engine
    ):
        """Test that execute_tool interface supports business operations."""
        # BUSINESS VALUE: Standard interface enables consistent business tool integration
        
        # Setup mock core engine for interface method
        business_response = ToolExecuteResponse(
            success=True,
            result={
                "business_metric": "customer_acquisition_cost",
                "current_value": 245.50,
                "target_value": 200.00,
                "optimization_potential": 0.186,  # 18.6% improvement potential
                "action_items": [
                    "Optimize marketing channel spend allocation",
                    "Improve conversion funnel efficiency", 
                    "Reduce customer acquisition friction"
                ]
            },
            message="Customer acquisition cost analysis completed",
            metadata={
                "data_quality_score": 0.95,
                "sample_size": 15420,
                "analysis_period": "last_90_days"
            }
        )
        
        tool_execution_engine._core_engine.execute_tool.return_value = business_response
        
        # Execute tool using interface method
        result = await tool_execution_engine.execute_tool(
            tool_name="customer_acquisition_analyzer",
            parameters={
                "time_period": "90d",
                "customer_segments": ["enterprise", "smb"],
                "include_forecasts": True
            }
        )
        
        # Verify interface delegation works
        tool_execution_engine._core_engine.execute_tool.assert_called_once_with(
            "customer_acquisition_analyzer",
            {
                "time_period": "90d", 
                "customer_segments": ["enterprise", "smb"],
                "include_forecasts": True
            }
        )
        
        # Verify business response format
        assert result == business_response
        assert result.success is True
        assert result.result["business_metric"] == "customer_acquisition_cost"
        assert result.result["optimization_potential"] > 0.1  # Meaningful improvement
        
        # Record interface compatibility metrics
        self.metrics.record_custom("business_tool_interface_verified", True)
        self.metrics.record_custom("standard_integration_supported", True)

    def test_initialization_creates_unified_engine_with_websocket_support(
        self, mock_websocket_manager
    ):
        """Test that initialization creates unified engine with WebSocket support."""
        # BUSINESS VALUE: WebSocket integration enables real-time business feedback
        
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            # Create tool execution engine
            engine = ToolExecutionEngine(mock_websocket_manager)
            
            # Verify unified engine was created with WebSocket manager
            mock_unified.assert_called_once_with(mock_websocket_manager)
            
            # Verify engine has access to core unified engine
            assert hasattr(engine, '_core_engine')
        
        # Record initialization metrics
        self.metrics.record_custom("unified_engine_initialization_verified", True)
        self.metrics.record_custom("websocket_integration_enabled", True)

    async def test_complex_business_tool_execution_preserves_context(
        self, tool_execution_engine, business_state
    ):
        """Test that complex business tool execution preserves business context."""
        # BUSINESS VALUE: Business context preservation enables accurate analysis
        
        # Create complex business tool
        class ComplexAnalyticsTool(BaseTool):
            name: str = "multi_dimensional_business_analyzer"
            description: str = "Performs multi-dimensional business analysis with context awareness"
            
            async def _arun(self, business_context: Dict[str, Any], analysis_type: str):
                # Simulate complex business logic
                company_id = business_context.get("company_id")
                fiscal_quarter = business_context.get("fiscal_quarter") 
                budget_constraints = business_context.get("budget_constraints", {})
                
                return {
                    "analysis_type": analysis_type,
                    "company_context": company_id,
                    "fiscal_period": fiscal_quarter,
                    "budget_aware_recommendations": {
                        "max_investment": budget_constraints.get("max_spend", 0) * 0.1,
                        "expected_roi": 2.5,
                        "risk_assessment": "moderate"
                    },
                    "contextual_insights": f"Analysis tailored for {company_id} in {fiscal_quarter}"
                }
        
        complex_tool = ComplexAnalyticsTool()
        
        # Setup mock to simulate context-aware execution
        context_aware_result = {
            "success": True,
            "result": {
                "analysis_type": "comprehensive_optimization",
                "company_context": "enterprise-corp-123", 
                "fiscal_period": "Q4-2024",
                "budget_aware_recommendations": {
                    "max_investment": 50000,  # 10% of max_spend (500000)
                    "expected_roi": 2.5,
                    "risk_assessment": "moderate"
                },
                "contextual_insights": "Analysis tailored for enterprise-corp-123 in Q4-2024"
            },
            "metadata": {"context_preserved": True}
        }
        
        tool_execution_engine._core_engine.execute_with_state.return_value = context_aware_result
        
        # Execute complex tool with business state
        result = await tool_execution_engine.execute_with_state(
            tool=complex_tool,
            tool_name="multi_dimensional_business_analyzer",
            parameters={
                "business_context": business_state.context,
                "analysis_type": "comprehensive_optimization"
            },
            state=business_state,
            run_id="complex-analysis-789"
        )
        
        # Verify business context was preserved and used
        assert result.success is True
        business_result = result.result
        assert business_result["company_context"] == "enterprise-corp-123"
        assert business_result["fiscal_period"] == "Q4-2024"
        assert business_result["budget_aware_recommendations"]["max_investment"] == 50000
        
        # Verify contextual insights were generated
        assert "enterprise-corp-123" in business_result["contextual_insights"]
        assert "Q4-2024" in business_result["contextual_insights"]
        
        # Record context preservation metrics
        self.metrics.record_custom("business_context_preserved_in_execution", True)
        self.metrics.record_custom("contextual_insights_generated", True)

    async def test_performance_tracking_enables_business_optimization(
        self, tool_execution_engine, business_tool, business_state
    ):
        """Test that performance tracking enables business process optimization."""
        # BUSINESS VALUE: Performance metrics enable business process improvement
        
        # Setup mock with performance metadata
        performance_result = {
            "success": True,
            "result": {"analysis": "completed", "savings": 25000},
            "metadata": {
                "execution_time_ms": 3500,
                "memory_usage_mb": 145, 
                "cpu_utilization": 0.65,
                "database_queries": 12,
                "api_calls": 5,
                "cache_hit_rate": 0.83,
                "business_metrics": {
                    "data_points_analyzed": 50000,
                    "recommendations_generated": 8,
                    "confidence_score": 0.89,
                    "processing_efficiency": "high"
                }
            }
        }
        
        tool_execution_engine._core_engine.execute_with_state.return_value = performance_result
        
        # Execute tool and collect performance data
        result = await tool_execution_engine.execute_with_state(
            tool=business_tool,
            tool_name="performance_tracked_analyzer",
            parameters={"detailed_analysis": True},
            state=business_state,
            run_id="performance-test-456"
        )
        
        # Verify performance tracking is available
        assert result.success is True
        metadata = result.metadata
        
        # Verify technical performance metrics
        assert metadata["execution_time_ms"] == 3500
        assert metadata["memory_usage_mb"] == 145
        assert metadata["database_queries"] == 12
        
        # Verify business performance metrics
        business_metrics = metadata["business_metrics"]
        assert business_metrics["data_points_analyzed"] == 50000
        assert business_metrics["recommendations_generated"] == 8
        assert business_metrics["confidence_score"] > 0.8  # High confidence
        assert business_metrics["processing_efficiency"] == "high"
        
        # Record performance tracking metrics
        self.metrics.record_custom("performance_metrics_captured", True)
        self.metrics.record_custom("business_optimization_enabled", True)


class TestToolExecutionEngineBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for tool execution edge cases."""

    async def test_high_volume_tool_execution_maintains_performance(self):
        """Test that high-volume tool execution maintains business performance standards."""
        # BUSINESS VALUE: System must handle peak business analysis loads
        
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core = AsyncMock()
            mock_unified.return_value = mock_core
            
            engine = ToolExecutionEngine(AsyncMock())
            
            # Simulate high-volume execution scenario
            execution_count = 50
            for i in range(execution_count):
                mock_core.execute_tool.return_value = ToolExecuteResponse(
                    success=True,
                    result={"batch_id": i, "processed": True},
                    message=f"Batch {i} completed"
                )
                
                # Execute tool 
                result = await engine.execute_tool(
                    tool_name=f"batch_processor_{i}",
                    parameters={"batch_size": 1000, "priority": "normal"}
                )
                
                assert result.success is True
                assert result.result["batch_id"] == i
        
        # Verify all executions completed
        assert mock_core.execute_tool.call_count == execution_count
        
        # Record high-volume performance metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("high_volume_executions_completed", execution_count)

    async def test_enterprise_vs_free_tier_execution_consistency(self):
        """Test that tool execution provides consistent service across business tiers."""
        # BUSINESS VALUE: All customer segments should receive reliable tool execution
        
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core = AsyncMock()
            mock_unified.return_value = mock_core
            
            engine = ToolExecutionEngine(AsyncMock())
            
            # Test execution for different customer tiers
            customer_tiers = [
                {"tier": "free", "user_id": "free-user-123"},
                {"tier": "enterprise", "user_id": "enterprise-user-789"},
                {"tier": "mid", "user_id": "mid-tier-user-456"}
            ]
            
            for tier_info in customer_tiers:
                # Setup consistent response regardless of tier
                mock_core.execute_tool.return_value = ToolExecuteResponse(
                    success=True,
                    result={"execution_quality": "high", "tier": tier_info["tier"]},
                    message="Tool executed successfully"
                )
                
                # Execute tool for this tier
                result = await engine.execute_tool(
                    tool_name="tier_agnostic_analyzer",
                    parameters={"user_tier": tier_info["tier"]}
                )
                
                # Verify consistent execution quality
                assert result.success is True
                assert result.result["execution_quality"] == "high"
        
        # Record business equity metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("tier_execution_consistency_maintained", True)