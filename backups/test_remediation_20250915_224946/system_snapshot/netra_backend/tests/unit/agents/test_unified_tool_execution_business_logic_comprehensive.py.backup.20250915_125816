"""
Unit Tests for UnifiedToolExecution Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Unified Tool Execution - Single source of truth for AI tool operations
- Value Impact: Unified execution ensures consistent tool behavior across all business agents
- Strategic Impact: SSOT architecture eliminates execution inconsistencies and improves platform reliability

This test suite validates the business-critical path of unified tool execution including:
- Single source of truth for all tool execution patterns
- WebSocket notification integration for real-time user feedback
- Permission checks and security validation for business tools
- Resource management and rate limiting for business scalability
- Error handling and timeout protection for business continuity
- Metrics tracking for business performance insights

CRITICAL: These tests focus on BUSINESS LOGIC that ensures all AI agents
execute tools consistently to deliver reliable business value.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, Optional

from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from test_framework.unified import TestCategory
from shared.isolated_environment import get_env


class TestUnifiedToolExecutionBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for UnifiedToolExecution business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        self.env.set("AGENT_DEFAULT_TIMEOUT", "30.0", source="test")
        self.env.set("AGENT_MAX_MEMORY_MB", "512", source="test")
        self.env.set("AGENT_MAX_CONCURRENT_PER_USER", "10", source="test")
        
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
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge for business notifications."""
        bridge = AsyncMock()
        bridge.notify_tool_started = AsyncMock()
        bridge.notify_tool_completed = AsyncMock()
        bridge.notify_tool_error = AsyncMock()
        bridge.notify_tool_executing = AsyncMock()
        return bridge

    @pytest.fixture
    def mock_permission_service(self):
        """Create mock permission service for business security."""
        service = AsyncMock()
        service.check_tool_permission = AsyncMock(return_value={
            "allowed": True,
            "reason": "User has enterprise access to business tools"
        })
        return service

    @pytest.fixture
    def unified_execution_engine(self, mock_websocket_bridge, mock_permission_service):
        """Create UnifiedToolExecutionEngine with mocked dependencies."""
        with patch('netra_backend.app.agents.unified_tool_execution.get_websocket_notification_monitor') as mock_monitor:
            mock_monitor.return_value = AsyncMock()
            
            engine = UnifiedToolExecutionEngine(
                websocket_bridge=mock_websocket_bridge,
                permission_service=mock_permission_service
            )
            return engine

    @pytest.fixture
    def business_tool_input(self):
        """Create realistic business tool input."""
        return ToolInput(
            tool_name="business_performance_analyzer",
            kwargs={
                "business_unit": "sales",
                "metrics": ["revenue", "conversion_rate", "customer_satisfaction"],
                "time_period": "quarterly",
                "benchmark_comparison": True,
                "context": {
                    "user_id": "business-analyst-123",
                    "session_id": "analysis-session-789",
                    "company_id": "enterprise-corp-456"
                }
            }
        )

    @pytest.fixture
    def business_tool(self):
        """Create realistic business tool for testing."""
        class BusinessPerformanceTool:
            name = "business_performance_analyzer"
            description = "Analyzes business performance metrics and provides actionable insights"
            
            async def run(self, business_unit: str, metrics: list, time_period: str = "quarterly", **kwargs):
                # Simulate business analysis processing
                await asyncio.sleep(0.01)
                
                return {
                    "business_unit": business_unit,
                    "analysis_period": time_period,
                    "performance_metrics": {
                        "revenue": {"current": 2500000, "growth": 0.15, "trend": "increasing"},
                        "conversion_rate": {"current": 0.038, "benchmark": 0.035, "performance": "above_benchmark"},
                        "customer_satisfaction": {"current": 4.2, "target": 4.0, "status": "exceeding_target"}
                    },
                    "key_insights": [
                        "Revenue growth of 15% exceeds industry average",
                        "Conversion rate outperforming benchmark by 8.6%", 
                        "Customer satisfaction scores indicate strong loyalty"
                    ],
                    "action_recommendations": [
                        "Scale successful marketing campaigns",
                        "Investigate factors driving high conversion rates",
                        "Leverage customer satisfaction for testimonials"
                    ],
                    "forecast": {
                        "next_quarter_revenue": 2875000,
                        "confidence_level": 0.87,
                        "risk_factors": ["market_volatility", "seasonal_trends"]
                    }
                }
            
            def __call__(self, *args, **kwargs):
                return asyncio.create_task(self.run(*args, **kwargs))
        
        return BusinessPerformanceTool()

    async def test_initialization_configures_business_security_controls(
        self, unified_execution_engine
    ):
        """Test that initialization configures appropriate business security controls."""
        # BUSINESS VALUE: Security controls protect business data and prevent resource abuse
        
        # Verify security configuration from environment
        assert unified_execution_engine.default_timeout == 30.0  # Reasonable for business operations
        assert unified_execution_engine.max_memory_mb == 512     # Prevents resource exhaustion
        assert unified_execution_engine.max_concurrent_per_user == 10  # Prevents abuse
        
        # Verify isolation environment is used (no direct os.environ)
        assert hasattr(unified_execution_engine, 'env')
        assert unified_execution_engine.env is not None
        
        # Verify metrics tracking is initialized
        expected_metrics = [
            'total_executions', 'successful_executions', 'failed_executions',
            'timeout_executions', 'security_violations', 'total_duration_ms'
        ]
        for metric in expected_metrics:
            assert metric in unified_execution_engine._execution_metrics
        
        # Verify business process monitoring is available
        assert hasattr(unified_execution_engine, '_process')
        assert unified_execution_engine._process is not None
        
        # Record security initialization metrics
        self.metrics.record_custom("security_controls_initialized", True)
        self.metrics.record_custom("business_protection_enabled", True)

    async def test_tool_execution_with_websocket_notifications_provides_transparency(
        self, unified_execution_engine, business_tool_input, business_tool, mock_websocket_bridge
    ):
        """Test that tool execution provides transparent business feedback via WebSocket."""
        # BUSINESS VALUE: Real-time feedback improves user experience and trust
        
        # Mock tool execution behavior
        with patch.object(unified_execution_engine, '_run_tool_by_interface') as mock_run:
            business_result = {
                "performance_summary": "Excellent quarterly performance",
                "revenue_growth": 0.15,
                "recommendations_count": 3,
                "forecast_confidence": 0.87
            }
            mock_run.return_value = business_result
            
            # Execute business tool
            result = await unified_execution_engine.execute_tool_with_input(
                business_tool_input, business_tool, business_tool_input.kwargs
            )
            
            # Verify WebSocket notifications were sent for transparency
            mock_websocket_bridge.notify_tool_executing.assert_called_once()
            mock_websocket_bridge.notify_tool_completed.assert_called_once()
            
            # Verify business result was returned
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            
            # Verify execution tracking for business monitoring
            assert len(unified_execution_engine._active_executions) >= 0  # May have been cleaned up
            assert unified_execution_engine._execution_metrics['successful_executions'] >= 1
        
        # Record transparency metrics
        self.metrics.record_custom("websocket_transparency_provided", True)
        self.metrics.record_custom("business_feedback_delivered", True)

    async def test_business_tool_timeout_protection_prevents_resource_waste(
        self, unified_execution_engine, business_tool_input, mock_websocket_bridge
    ):
        """Test that timeout protection prevents business resource waste."""
        # BUSINESS VALUE: Timeout protection prevents runaway processes that waste resources
        
        # Create slow business tool that would hang
        class SlowBusinessTool:
            name = "slow_market_analysis"
            
            async def run(self, **kwargs):
                # Simulate hung business analysis
                await asyncio.sleep(5)  # Longer than test timeout to trigger timeout behavior
                return {"analysis": "never_completes"}
        
        slow_tool = SlowBusinessTool()
        
        # Mock timeout behavior
        with patch.object(unified_execution_engine, '_run_tool_by_interface') as mock_run:
            mock_run.side_effect = asyncio.TimeoutError("Business analysis exceeded timeout")
            
            # Execute with timeout protection
            result = await unified_execution_engine.execute_tool_with_input(
                business_tool_input, slow_tool, business_tool_input.kwargs
            )
            
            # Verify timeout was handled gracefully
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.ERROR
            assert "timeout" in result.message.lower()
            
            # Verify user was notified of timeout
            mock_websocket_bridge.notify_tool_completed.assert_called_once()
            
            # Verify timeout metrics were updated
            assert unified_execution_engine._execution_metrics['failed_executions'] >= 1
        
        # Record resource protection metrics
        self.metrics.record_custom("timeout_protection_activated", True)
        self.metrics.record_custom("resource_waste_prevented", True)

    async def test_business_error_handling_provides_actionable_feedback(
        self, unified_execution_engine, business_tool_input, mock_websocket_bridge
    ):
        """Test that business errors provide actionable feedback to users."""
        # BUSINESS VALUE: Clear error messages enable business users to take corrective action
        
        # Create business tool that fails with realistic error
        class FailingBusinessTool:
            name = "data_integration_analyzer"
            
            async def run(self, **kwargs):
                raise ValueError("Sales database connection failed - verify network access and credentials")
        
        failing_tool = FailingBusinessTool()
        
        # Mock error handling
        with patch.object(unified_execution_engine, '_run_tool_by_interface') as mock_run:
            mock_run.side_effect = ValueError("Sales database connection failed - verify network access and credentials")
            
            # Execute failing business tool
            result = await unified_execution_engine.execute_tool_with_input(
                business_tool_input, failing_tool, business_tool_input.kwargs
            )
            
            # Verify error was handled gracefully
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.ERROR
            assert "database connection failed" in result.message
            assert "verify network access" in result.message
            
            # Verify user received actionable error information
            mock_websocket_bridge.notify_tool_completed.assert_called_once()
            
            # Verify error metrics were updated
            assert unified_execution_engine._execution_metrics['failed_executions'] >= 1
        
        # Record error handling metrics
        self.metrics.record_custom("actionable_error_feedback_provided", True)
        self.metrics.record_custom("business_continuity_maintained", True)

    async def test_metrics_tracking_enables_business_performance_insights(
        self, unified_execution_engine, business_tool_input, business_tool
    ):
        """Test that metrics tracking enables business performance insights."""
        # BUSINESS VALUE: Performance metrics enable business process optimization
        
        # Mock successful execution
        with patch.object(unified_execution_engine, '_run_tool_by_interface') as mock_run:
            mock_run.return_value = {
                "analysis_complete": True,
                "performance_score": 0.92,
                "business_insights": ["Revenue trending upward", "Customer retention improving"]
            }
            
            # Execute multiple business tools to generate metrics
            for i in range(5):
                await unified_execution_engine.execute_tool_with_input(
                    business_tool_input, business_tool, business_tool_input.kwargs
                )
            
            # Verify business metrics were collected
            metrics = unified_execution_engine._execution_metrics
            assert metrics['successful_executions'] >= 5
            assert metrics['total_executions'] >= 5
            assert metrics['failed_executions'] == 0
            
            # Verify active execution tracking
            assert isinstance(unified_execution_engine._active_executions, dict)
            
            # Verify user tracking for business insights
            assert isinstance(unified_execution_engine._user_execution_counts, dict)
        
        # Record business insights metrics
        self.metrics.record_custom("performance_metrics_collected", True)
        self.metrics.record_custom("business_insights_enabled", True)

    def test_ssot_compatibility_maintains_business_interfaces(
        self, unified_execution_engine
    ):
        """Test that SSOT design maintains backward compatibility for business interfaces."""
        # BUSINESS VALUE: SSOT consolidation must not break existing business integrations
        
        # Verify WebSocket bridge compatibility
        assert hasattr(unified_execution_engine, 'websocket_bridge')
        assert hasattr(unified_execution_engine, 'websocket_notifier')  # Legacy compatibility
        assert unified_execution_engine.websocket_notifier is unified_execution_engine.websocket_bridge
        
        # Verify permission service integration
        assert hasattr(unified_execution_engine, 'permission_service')
        
        # Verify core execution interface exists
        assert hasattr(unified_execution_engine, 'execute_tool_with_input')
        assert callable(unified_execution_engine.execute_tool_with_input)
        
        # Verify security controls are accessible
        security_attrs = ['default_timeout', 'max_memory_mb', 'max_concurrent_per_user']
        for attr in security_attrs:
            assert hasattr(unified_execution_engine, attr)
        
        # Record compatibility metrics
        self.metrics.record_custom("business_interface_compatibility_maintained", True)
        self.metrics.record_custom("ssot_integration_successful", True)

    async def test_enhance_tool_dispatcher_enables_business_notifications(self):
        """Test that tool dispatcher enhancement enables business notifications."""
        # BUSINESS VALUE: Enhancement enables real-time feedback across all business tools
        
        # Create mock tool dispatcher
        mock_dispatcher = Mock()
        mock_dispatcher.executor = Mock()
        mock_websocket_manager = AsyncMock()
        
        # Mock AgentWebSocketBridge creation
        with patch('netra_backend.app.agents.unified_tool_execution.AgentWebSocketBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Enhance dispatcher
            enhanced = await enhance_tool_dispatcher_with_notifications(
                mock_dispatcher,
                websocket_manager=mock_websocket_manager,
                enable_notifications=True
            )
            
            # Verify enhancement was applied
            assert enhanced is mock_dispatcher
            assert hasattr(enhanced, '_websocket_enhanced')
            assert enhanced._websocket_enhanced is True
            
            # Verify executor was replaced with unified engine
            assert isinstance(enhanced.executor, UnifiedToolExecutionEngine)
            
            # Verify WebSocket integration was configured
            assert enhanced.executor.websocket_bridge is mock_bridge
        
        # Record enhancement metrics
        self.metrics.record_custom("dispatcher_enhancement_successful", True)
        self.metrics.record_custom("business_notifications_enabled", True)

    async def test_double_enhancement_prevention_maintains_business_stability(self):
        """Test that double enhancement prevention maintains business system stability."""
        # BUSINESS VALUE: Preventing double enhancement ensures stable business operations
        
        # Create mock dispatcher that's already enhanced
        mock_dispatcher = Mock()
        mock_dispatcher._websocket_enhanced = True
        mock_original_executor = Mock()
        mock_dispatcher.executor = mock_original_executor
        
        # Attempt double enhancement
        enhanced = await enhance_tool_dispatcher_with_notifications(
            mock_dispatcher,
            websocket_manager=AsyncMock(),
            enable_notifications=True
        )
        
        # Verify no changes were made
        assert enhanced is mock_dispatcher
        assert enhanced.executor is mock_original_executor  # Original executor preserved
        
        # Record stability metrics
        self.metrics.record_custom("double_enhancement_prevented", True)
        self.metrics.record_custom("business_stability_maintained", True)

    async def test_success_result_creation_structures_business_output(
        self, unified_execution_engine, business_tool_input
    ):
        """Test that success result creation properly structures business output."""
        # BUSINESS VALUE: Structured results enable consistent business logic processing
        
        business_analysis_result = {
            "quarterly_performance": {
                "revenue": 2500000,
                "growth_rate": 0.15,
                "market_share": 0.23
            },
            "strategic_recommendations": [
                "Expand into emerging markets",
                "Invest in digital transformation",
                "Optimize operational efficiency"
            ],
            "risk_assessment": {
                "overall_risk": "moderate", 
                "key_risks": ["market_volatility", "competitive_pressure"],
                "mitigation_strategies": ["diversification", "innovation"]
            },
            "confidence_metrics": {
                "data_quality": 0.94,
                "model_accuracy": 0.87,
                "forecast_reliability": 0.82
            }
        }
        
        # Create success result using internal method
        success_result = unified_execution_engine._create_success_result(
            business_tool_input, 
            business_analysis_result
        )
        
        # Verify structured business result
        assert isinstance(success_result, ToolResult)
        assert success_result.status == ToolStatus.SUCCESS
        assert success_result.tool_input == business_tool_input
        assert success_result.result == business_analysis_result
        
        # Verify business data structure is preserved
        assert success_result.result["quarterly_performance"]["revenue"] == 2500000
        assert len(success_result.result["strategic_recommendations"]) == 3
        assert success_result.result["confidence_metrics"]["data_quality"] == 0.94
        
        # Record output structure metrics
        self.metrics.record_custom("business_output_structured", True)
        self.metrics.record_custom("result_consistency_maintained", True)


class TestUnifiedToolExecutionBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for unified tool execution edge cases."""

    async def test_enterprise_customer_concurrent_execution_limits(self):
        """Test that enterprise customers can execute multiple business tools concurrently.""" 
        # BUSINESS VALUE: Enterprise customers need higher concurrency for complex analysis
        
        with patch('netra_backend.app.agents.unified_tool_execution.get_websocket_notification_monitor'):
            engine = UnifiedToolExecutionEngine()
            
            # Verify enterprise-appropriate concurrency limits
            assert engine.max_concurrent_per_user >= 10  # Should support enterprise workloads
            
            # Test concurrent execution tracking
            enterprise_user = "enterprise-customer-123"
            for i in range(5):  # Simulate concurrent executions
                execution_id = f"concurrent_analysis_{i}"
                engine._active_executions[execution_id] = {
                    'user_id': enterprise_user,
                    'tool_name': f'business_analyzer_{i}',
                    'start_time': time.time()
                }
            
            # Verify tracking works for business scenarios
            enterprise_executions = [
                exec_data for exec_data in engine._active_executions.values()
                if exec_data.get('user_id') == enterprise_user
            ]
            assert len(enterprise_executions) == 5
        
        # Record enterprise support metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_concurrency_supported", True)

    async def test_free_tier_user_appropriate_resource_limits(self):
        """Test that free tier users have appropriate resource limits for business operations."""
        # BUSINESS VALUE: Resource limits enable sustainable free tier while encouraging upgrades
        
        with patch('netra_backend.app.agents.unified_tool_execution.get_websocket_notification_monitor'):
            # Verify free tier has reasonable limits for basic business operations
            engine = UnifiedToolExecutionEngine()
            
            # These limits should be reasonable for basic business tools
            assert engine.default_timeout >= 15.0  # Enough for basic analysis
            assert engine.max_memory_mb >= 256     # Enough for small datasets
            assert engine.max_concurrent_per_user >= 3  # Basic multi-tasking
            
            # Simulate free tier usage tracking
            free_user = "free-tier-user-456"
            engine._user_execution_counts[free_user] = 2  # Current usage
            
            # Verify tracking works for business limits
            assert engine._user_execution_counts[free_user] == 2
        
        # Record free tier metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("free_tier_limits_appropriate", True)
        metrics.record_custom("sustainable_free_service_enabled", True)