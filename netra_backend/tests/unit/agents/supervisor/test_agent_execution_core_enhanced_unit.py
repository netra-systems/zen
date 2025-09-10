"""
Enhanced Unit Tests for AgentExecutionCore - Business Logic Focus

BVJ (Business Value Justification): These tests validate critical business logic that directly impacts
customer experience and platform reliability:
- Agent death detection prevents silent failures that hurt customer trust
- Error boundary validation ensures customers get proper error messages
- Performance metrics collection enables data-driven optimization for cost reduction
- Memory tracking prevents resource exhaustion that could crash customer sessions

Focus: Death detection, error boundaries, metrics, and critical business logic validation
WITHOUT external dependencies to ensure fast test execution and clear failure isolation.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

# Use absolute imports from package root
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class TestAgentExecutionCoreEnhancedBusinessLogic:
    """Enhanced unit tests focusing on business-critical logic patterns."""

    @pytest.fixture
    def mock_registry(self):
        """Mock agent registry with configurable behavior."""
        registry = Mock()
        registry.get = Mock()
        return registry

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock websocket bridge for notification testing."""
        bridge = AsyncMock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_agent_error = AsyncMock()
        bridge.notify_agent_thinking = AsyncMock()
        return bridge

    @pytest.fixture
    def mock_execution_tracker(self):
        """Mock execution tracker with realistic behavior."""
        tracker = AsyncMock()
        tracker.register_execution = AsyncMock(return_value=uuid4())
        tracker.start_execution = AsyncMock()
        tracker.complete_execution = AsyncMock()
        tracker.collect_metrics = AsyncMock(return_value={'duration': 1.5, 'memory_peak': 128})
        return tracker

    @pytest.fixture
    def execution_core(self, mock_registry, mock_websocket_bridge, mock_execution_tracker):
        """AgentExecutionCore instance with mocked dependencies."""
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_execution_tracker') as mock_get_tracker:
            mock_get_tracker.return_value = mock_execution_tracker
            core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
            core.execution_tracker = mock_execution_tracker
            return core

    @pytest.fixture
    def business_context(self):
        """Business-focused agent execution context."""
        return AgentExecutionContext(
            agent_name="cost_optimization_agent",
            run_id=uuid4(),
            thread_id="business-thread-001",
            user_id="customer-premium-user",
            correlation_id="cost-analysis-session",
            retry_count=0,
            max_retries=2
        )

    @pytest.fixture
    def customer_state(self):
        """Customer-focused agent state."""
        state = Mock(spec=DeepAgentState)
        state.user_id = "customer-premium-user"
        state.thread_id = "business-thread-001"
        # Add business-relevant data
        state.customer_tier = "premium"
        state.current_spend = 1500.00
        return state

    @pytest.fixture
    def mock_business_agent(self):
        """Mock agent representing business value delivery."""
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={
            "success": True, 
            "cost_savings": 250.00,
            "recommendations": ["switch to gpt-3.5 for routine tasks"],
            "confidence": 0.87
        })
        agent.__class__.__name__ = "CostOptimizationAgent"
        agent.set_trace_context = Mock()
        agent.set_websocket_bridge = Mock()
        agent.websocket_bridge = None
        agent.execution_engine = None
        return agent

    @pytest.mark.asyncio
    async def test_agent_null_response_detection_business_critical(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: NULL response detection is MISSION CRITICAL for customer trust.
        Silent agent failures destroy customer confidence and waste their time.
        This test ensures we detect when agents die silently instead of providing value.
        
        Business Impact: Prevents silent failures that lead to customer churn.
        """
        # Simulate agent death - returns None instead of business value
        mock_business_agent.execute.return_value = None
        execution_core.registry.get.return_value = mock_business_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(business_context, customer_state)
        
        # CRITICAL: Must detect agent death and provide clear error
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "died silently" in result.error
        assert "returned None" in result.error
        
        # Business requirement: Customer must be notified of failure
        execution_core.websocket_bridge.notify_agent_error.assert_called_once()
        error_call = execution_core.websocket_bridge.notify_agent_error.call_args
        assert "died silently" in error_call[1]['error']

    @pytest.mark.asyncio
    async def test_agent_malformed_response_recovery_business_logic(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: Malformed responses must be handled gracefully to maintain customer experience.
        Agents sometimes return unexpected formats but still provide business value.
        We must extract value while ensuring system stability.
        
        Business Impact: Maintains service availability when agents return unexpected formats.
        """
        # Agent returns valuable data but in unexpected format
        mock_business_agent.execute.return_value = "Cost savings: $250 via model optimization"
        execution_core.registry.get.return_value = mock_business_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(business_context, customer_state)
        
        # CRITICAL: Must recover and deliver value to customer
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True  # Business value extracted
        assert result.duration is not None
        assert result.metrics is not None
        
        # Customer should receive successful completion notification
        execution_core.websocket_bridge.notify_agent_completed.assert_called_once()

    @pytest.mark.asyncio 
    async def test_timeout_boundary_conditions_business_impact(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: Timeout boundaries protect customer experience from hanging agents.
        Customers expect timely responses. Long-running agents without feedback 
        create poor UX and waste customer resources.
        
        Business Impact: Prevents customer frustration from unresponsive agents.
        """
        # Agent takes too long to deliver business value
        async def slow_business_logic(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"cost_savings": 500, "analysis": "complex optimization"}
        
        mock_business_agent.execute = slow_business_logic
        execution_core.registry.get.return_value = mock_business_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                # Business requirement: Fast timeout for customer responsiveness
                result = await execution_core.execute_agent(business_context, customer_state, timeout=0.1)
        
        # CRITICAL: Must timeout gracefully with business-relevant error
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.duration is not None
        assert result.duration >= 0.1  # Timeout duration tracked
        
        # Customer must be informed of timeout with actionable message
        execution_core.websocket_bridge.notify_agent_error.assert_called_once()
        error_call = execution_core.websocket_bridge.notify_agent_error.call_args
        assert "timeout" in error_call[1]['error'].lower()

    @pytest.mark.asyncio
    async def test_nested_exception_handling_customer_experience(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: Nested exceptions must be handled to prevent customer-facing crashes.
        Complex business logic can fail at multiple levels. Customers must receive
        clear error messages, not technical stack traces.
        
        Business Impact: Maintains professional customer experience during failures.
        """
        # Create nested exception scenario common in business logic
        def create_nested_exception(*args, **kwargs):
            try:
                raise ValueError("Database connection lost during cost analysis")
            except ValueError as e:
                raise RuntimeError("Cost optimization agent failed") from e
        
        mock_business_agent.execute.side_effect = create_nested_exception
        execution_core.registry.get.return_value = mock_business_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(business_context, customer_state)
        
        # CRITICAL: Must handle nested errors gracefully
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "Cost optimization agent failed" in result.error
        assert result.duration is not None
        
        # Customer gets clear error message, not technical details
        execution_core.websocket_bridge.notify_agent_error.assert_called_once()
        
        # Execution must be properly tracked even during failure
        execution_core.execution_tracker.complete_execution.assert_called_once()
        complete_call = execution_core.execution_tracker.complete_execution.call_args
        assert 'error' in complete_call[1] or len(complete_call[0]) > 1

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure_business_continuity(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: Resource cleanup ensures business continuity after failures.
        Failed agents must not leak resources that could impact other customers.
        Proper cleanup maintains system stability for all users.
        
        Business Impact: Prevents one customer's failed request from affecting others.
        """
        # Simulate agent failure that requires cleanup
        mock_business_agent.execute.side_effect = Exception("Resource allocation failed")
        execution_core.registry.get.return_value = mock_business_agent
        
        # Mock cleanup-sensitive resources
        execution_core._cleanup_resources = Mock()
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = None
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(business_context, customer_state)
        
        # CRITICAL: Failure must be tracked to enable cleanup
        assert result.success is False
        
        # Execution tracker must complete with error to trigger cleanup
        execution_core.execution_tracker.complete_execution.assert_called_once()
        complete_call = execution_core.execution_tracker.complete_execution.call_args
        
        # Verify error information is provided for cleanup
        has_error = 'error' in complete_call[1] if complete_call[1] else len(complete_call[0]) > 1
        assert has_error, "Execution tracker must receive error information for cleanup"

    def test_performance_metrics_accuracy_business_value(self, execution_core):
        """
        BVJ: Accurate performance metrics enable data-driven cost optimization.
        Customers pay for efficiency. Precise metrics help identify optimization
        opportunities that directly impact customer ROI.
        
        Business Impact: Enables cost optimization recommendations worth $$$$ to customers.
        """
        start_time = time.time() - 2.5  # 2.5 seconds of business processing
        
        # Mock realistic business metrics
        mock_heartbeat = Mock()
        mock_heartbeat.pulse_count = 5  # 5 heartbeats during processing
        
        metrics = execution_core._calculate_performance_metrics(start_time, mock_heartbeat)
        
        # CRITICAL: Metrics must be accurate for business decisions
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics
        assert 'heartbeat_count' in metrics
        
        # Verify accuracy for cost calculations
        assert metrics['execution_time_ms'] >= 2400  # At least 2.4s in ms
        assert metrics['execution_time_ms'] <= 2600  # At most 2.6s in ms 
        assert metrics['start_timestamp'] == start_time
        assert metrics['heartbeat_count'] == 5
        
        # Time range validation for billing accuracy
        duration_seconds = (metrics['end_timestamp'] - metrics['start_timestamp'])
        assert 2.4 <= duration_seconds <= 2.6

    def test_memory_usage_tracking_cost_optimization(self, execution_core):
        """
        BVJ: Memory usage tracking enables infrastructure cost optimization.
        Memory-hungry agents cost more to run. Tracking enables right-sizing
        for optimal cost-performance ratio.
        
        Business Impact: Reduces infrastructure costs while maintaining performance.
        """
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=512*1024*1024)  # 512MB business agent
        mock_process.cpu_percent.return_value = 25.5  # 25.5% CPU for cost analysis
        
        with patch('psutil.Process', return_value=mock_process):
            start_time = time.time() - 1.0
            metrics = execution_core._calculate_performance_metrics(start_time)
        
        # CRITICAL: Memory metrics must be accurate for cost optimization
        assert 'memory_usage_mb' in metrics
        assert 'cpu_percent' in metrics
        assert metrics['memory_usage_mb'] == 512.0  # Exact MB for cost calculation
        assert metrics['cpu_percent'] == 25.5  # Precise CPU for scaling decisions
        
        # Business thresholds validation
        assert metrics['memory_usage_mb'] > 0, "Memory usage must be tracked for cost analysis"
        assert 0 <= metrics['cpu_percent'] <= 100, "CPU percentage must be valid for scaling"

    def test_memory_tracking_fallback_business_continuity(self, execution_core):
        """
        BVJ: Memory tracking failures must not break business operations.
        psutil may not be available in all environments. Business logic
        must continue even without detailed metrics.
        
        Business Impact: Ensures service continuity across all deployment environments.
        """
        # Simulate psutil not available (common in Docker/Lambda)
        with patch('psutil.Process', side_effect=ImportError("psutil not available")):
            start_time = time.time() - 1.0
            metrics = execution_core._calculate_performance_metrics(start_time)
        
        # CRITICAL: Must continue operations without psutil
        assert 'execution_time_ms' in metrics  # Core metrics still available
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics
        
        # Optional metrics gracefully omitted
        assert 'memory_usage_mb' not in metrics
        assert 'cpu_percent' not in metrics
        
        # Business operations continue unaffected
        assert len(metrics) >= 3, "Core performance metrics still collected"

    @pytest.mark.asyncio
    async def test_trace_context_propagation_unit_level(
        self, execution_core, business_context, customer_state, mock_business_agent
    ):
        """
        BVJ: Trace context propagation enables customer request tracking.
        Multi-agent business workflows need end-to-end traceability for
        debugging customer issues and optimizing performance.
        
        Business Impact: Enables rapid customer issue resolution and performance optimization.
        """
        execution_core.registry.get.return_value = mock_business_agent
        
        # Create business trace context
        parent_trace = Mock(spec=UnifiedTraceContext)
        parent_trace.correlation_id = "customer-cost-analysis-001"
        
        child_trace = Mock(spec=UnifiedTraceContext)
        child_trace.correlation_id = "agent-optimization-step-001"
        child_trace.start_span.return_value = Mock()  # Mock span
        child_trace.to_websocket_context.return_value = {
            'trace_id': 'customer-trace',
            'correlation_id': 'agent-optimization-step-001'
        }
        
        parent_trace.propagate_to_child.return_value = child_trace
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_trace:
            mock_trace.return_value = parent_trace
            with patch('netra_backend.app.agents.supervisor.agent_execution_core.TraceContextManager'):
                result = await execution_core.execute_agent(business_context, customer_state)
        
        # CRITICAL: Business trace must propagate to child agents
        parent_trace.propagate_to_child.assert_called_once()
        child_trace.start_span.assert_called_once()
        
        # Span must include business-relevant attributes
        span_call = child_trace.start_span.call_args
        attributes = span_call[1]['attributes']
        assert attributes['agent.name'] == business_context.agent_name
        assert attributes['user.id'] == customer_state.user_id
        
        # WebSocket notifications must include trace context for customer visibility
        execution_core.websocket_bridge.notify_agent_started.assert_called_once()
        start_call = execution_core.websocket_bridge.notify_agent_started.call_args
        assert 'trace_context' in start_call[1]

    def test_get_agent_business_error_scenarios(self, execution_core):
        """
        BVJ: Clear agent lookup errors improve customer support experience.
        When customers request unavailable agents, they need clear, actionable
        error messages rather than technical jargon.
        
        Business Impact: Reduces customer support burden and improves user experience.
        """
        # Test missing agent scenario
        execution_core.registry.get.return_value = None
        
        result = execution_core._get_agent_or_error("premium_analytics_agent")
        
        # CRITICAL: Error must be customer-friendly
        assert isinstance(result, AgentExecutionResult)
        assert result.success is False
        assert "premium_analytics_agent not found" in result.error
        
        # Error message should be suitable for customer-facing display
        assert not result.error.startswith("ERROR:")  # Not technical
        assert "not found" in result.error  # Clear business language

    @pytest.mark.asyncio
    async def test_metrics_collection_business_intelligence(
        self, execution_core, customer_state
    ):
        """
        BVJ: Comprehensive metrics collection enables business intelligence.
        Metrics drive customer success insights, cost optimization, and
        platform improvements that increase customer lifetime value.
        
        Business Impact: Powers data-driven decisions that increase revenue per customer.
        """
        exec_id = uuid4()
        
        # Business-relevant execution result
        result = AgentExecutionResult(
            success=True,
            duration=3.2,  # 3.2 seconds of customer value delivery
            metrics={
                'cost_savings_calculated': 450.00,
                'recommendations_generated': 7,
                'confidence_score': 0.92
            }
        )
        
        # Mock tracker with business metrics
        execution_core.execution_tracker.collect_metrics.return_value = {
            'cpu_time_ms': 1200,
            'memory_peak_mb': 256,
            'api_calls_made': 3
        }
        
        combined_metrics = await execution_core._collect_metrics(exec_id, result, customer_state, None)
        
        # CRITICAL: Business and technical metrics must be combined
        assert 'cost_savings_calculated' in combined_metrics  # Business value
        assert 'recommendations_generated' in combined_metrics  # Customer outcome
        assert 'confidence_score' in combined_metrics  # Quality metric
        assert 'cpu_time_ms' in combined_metrics  # Cost metric
        assert 'memory_peak_mb' in combined_metrics  # Efficiency metric
        
        # Standard execution metrics
        assert 'context_size' in combined_metrics
        assert 'result_success' in combined_metrics
        assert 'total_duration_seconds' in combined_metrics
        
        # Verify business intelligence data quality
        assert combined_metrics['result_success'] is True
        assert combined_metrics['total_duration_seconds'] == 3.2
        assert combined_metrics['cost_savings_calculated'] == 450.00

    @pytest.mark.asyncio
    async def test_websocket_notification_business_transparency(
        self, execution_core, business_context
    ):
        """
        BVJ: WebSocket notifications provide customer transparency during agent execution.
        Customers need real-time visibility into agent progress to maintain trust
        and understand the value being delivered.
        
        Business Impact: Increases customer satisfaction and trust through transparency.
        """
        trace_context = Mock(spec=UnifiedTraceContext)
        trace_context.to_websocket_context.return_value = {
            'trace_id': 'customer-session-001',
            'user_id': 'premium-customer'
        }
        
        # Test callback creation
        callback = execution_core._create_websocket_callback(business_context, trace_context)
        assert callback is not None
        
        # Test business progress notification
        await callback({'pulse': 3, 'status': 'analyzing_costs'})
        
        # CRITICAL: Customer must receive progress updates
        execution_core.websocket_bridge.notify_agent_thinking.assert_called_once()
        thinking_call = execution_core.websocket_bridge.notify_agent_thinking.call_args
        
        # Verify customer-relevant information
        assert thinking_call[1]['run_id'] == business_context.run_id
        assert thinking_call[1]['agent_name'] == business_context.agent_name
        assert 'Processing...' in thinking_call[1]['reasoning']  # Customer-friendly message
        assert 'heartbeat #3' in thinking_call[1]['reasoning']  # Progress indicator
        assert thinking_call[1]['trace_context']['trace_id'] == 'customer-session-001'

    def test_websocket_callback_without_bridge_business_continuity(self):
        """
        BVJ: Missing WebSocket bridge must not break business operations.
        Not all execution contexts have WebSocket capabilities. Business logic
        must continue to deliver value even without real-time notifications.
        
        Business Impact: Ensures service availability across all deployment contexts.
        """
        # Execution core without WebSocket (e.g., batch processing)
        execution_core = AgentExecutionCore(Mock(), None)
        
        sample_context = Mock()
        trace_context = Mock()
        
        callback = execution_core._create_websocket_callback(sample_context, trace_context)
        
        # CRITICAL: Must handle gracefully without breaking business logic
        assert callback is None, "No callback should be created without WebSocket bridge"
        
        # Business operations continue unaffected
        assert execution_core.registry is not None
        assert execution_core.websocket_bridge is None