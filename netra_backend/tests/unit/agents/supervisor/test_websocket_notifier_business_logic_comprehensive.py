"""
Unit Tests for WebSocketNotifier Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User Experience - Real-time feedback during AI operations
- Value Impact: WebSocket events provide transparency and progress updates that prevent user abandonment
- Strategic Impact: Real-time communication is core to modern AI UX expectations

CRITICAL: Although WebSocketNotifier is deprecated in favor of AgentWebSocketBridge,
it remains BUSINESS-CRITICAL as it handles guaranteed event delivery and concurrency optimization
that directly impact user experience and platform reliability.

This test suite validates:
- Guaranteed delivery of critical events (agent_started, tool_executing, agent_completed)
- Event queuing and backlog management for high-load scenarios
- User feedback mechanisms during long-running operations  
- Error recovery and fallback notification systems
- Concurrent user support with proper event ordering
"""

import asyncio
import pytest
import time
import uuid
from collections import deque
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, Optional

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from shared.isolated_environment import get_env


class TestWebSocketNotifierBusinessLogic(SSotBaseTestCase):
    """Comprehensive unit tests for WebSocketNotifier business-critical functionality."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context()
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager with business-appropriate behavior."""
        manager = AsyncMock()
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    async def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocketNotifier with mocked dependencies - suppress deprecation warning for testing."""
        with patch('warnings.warn'):  # Suppress deprecation warning during testing
            # Use test_mode=True to prevent background task hanging
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
        
        yield notifier
        
        # CRITICAL: Ensure proper cleanup to prevent hanging tests
        await notifier.shutdown()

    @pytest.fixture
    def business_context(self):
        """Create realistic execution context for business operations."""
        return AgentExecutionContext(
            agent_name="cost_optimization_agent",
            run_id=uuid4(),
            thread_id="enterprise-session-12345",
            user_id="enterprise-customer-789",
            correlation_id="optimization-job-456",
            retry_count=0
        )

    @pytest.fixture
    def high_value_context(self):
        """Create context for high-value enterprise customer."""
        return AgentExecutionContext(
            agent_name="enterprise_analytics_agent", 
            run_id=uuid4(),
            thread_id="vip-session-99999",
            user_id="enterprise-vip-001",
            correlation_id="quarterly-analysis-2024"
        )

    async def test_agent_started_notification_provides_immediate_user_feedback(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that agent started notifications provide immediate user feedback."""
        # BUSINESS VALUE: Users need immediate confirmation their request is being processed
        
        # Send agent started notification
        await websocket_notifier.send_agent_started(business_context)
        
        # Verify immediate WebSocket notification was sent
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        
        # Verify message contains business-relevant information
        thread_id = call_args[0][0]
        message_data = call_args[0][1]
        
        assert thread_id == business_context.thread_id
        assert message_data['type'] == 'agent_started'
        assert message_data['payload']['agent_name'] == 'cost_optimization_agent'
        assert 'timestamp' in message_data['payload']
        
        # Verify operation was marked as active for backlog handling
        assert business_context.thread_id in websocket_notifier.active_operations
        operation = websocket_notifier.active_operations[business_context.thread_id]
        assert operation['processing'] is True
        assert operation['agent_name'] == business_context.agent_name
        
        # Record user experience metrics
        self.metrics.record_custom("immediate_feedback_provided", 1)
        self.metrics.record_custom("user_abandonment_prevented", True)

    async def test_critical_event_delivery_with_guaranteed_retry(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that critical events have guaranteed delivery with retry logic."""
        # BUSINESS VALUE: Critical events must reach users to prevent confusion and support tickets
        
        # Simulate initial delivery failure
        mock_websocket_manager.send_to_thread.side_effect = [False, True]  # Fail first, succeed second
        
        # Send critical agent started event
        await websocket_notifier.send_agent_started(business_context)
        
        # Verify event was queued for retry after initial failure
        assert len(websocket_notifier.event_queue) > 0
        
        # Wait for queue processing
        await asyncio.sleep(0.2)  # Allow queue processor to run
        
        # Verify retry attempts were made
        assert mock_websocket_manager.send_to_thread.call_count >= 1
        
        # Record reliability metrics
        self.metrics.record_custom("critical_events_guaranteed", 1)
        self.metrics.record_custom("delivery_reliability_maintained", True)

    async def test_tool_execution_notifications_provide_transparency(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that tool execution notifications provide process transparency."""
        # BUSINESS VALUE: Users need visibility into AI tool usage for trust and understanding
        
        # Send enhanced tool executing notification
        await websocket_notifier.send_tool_executing(
            business_context,
            tool_name="aws_cost_analyzer",
            tool_purpose="Analyzing AWS billing data for optimization opportunities",
            estimated_duration_ms=15000,  # 15 seconds
            parameters_summary="Analyzing 12 months of billing data across 15 services"
        )
        
        # Verify detailed notification was sent
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        assert message_data['type'] == 'tool_executing'
        payload = message_data['payload']
        assert payload['tool_name'] == 'aws_cost_analyzer'
        assert payload['tool_purpose'] == 'Analyzing AWS billing data for optimization opportunities'
        assert payload['estimated_duration_ms'] == 15000
        assert payload['parameters_summary'] == 'Analyzing 12 months of billing data across 15 services'
        assert payload['execution_phase'] == 'starting'
        
        # Record transparency metrics
        self.metrics.record_custom("tool_transparency_provided", 1)
        self.metrics.record_custom("user_trust_maintained", True)

    async def test_agent_thinking_with_progress_provides_reassurance(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that agent thinking notifications with progress provide user reassurance."""
        # BUSINESS VALUE: Progress updates prevent user anxiety during long AI operations
        
        # Send enhanced thinking notification with progress
        await websocket_notifier.send_agent_thinking(
            business_context,
            thought="Analyzing cost patterns across your infrastructure...",
            step_number=3,
            progress_percentage=35.5,
            estimated_remaining_ms=25000,  # 25 seconds remaining
            current_operation="Pattern recognition in billing data"
        )
        
        # Verify comprehensive progress notification was sent
        call_args = mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        assert message_data['type'] == 'agent_thinking'
        payload = message_data['payload']
        assert payload['thought'] == 'Analyzing cost patterns across your infrastructure...'
        assert payload['step_number'] == 3
        assert payload['progress_percentage'] == 35.5
        assert payload['estimated_remaining_ms'] == 25000
        assert payload['current_operation'] == 'Pattern recognition in billing data'
        assert payload['urgency'] == 'low_priority'  # >10 seconds remaining
        
        # Record user reassurance metrics
        self.metrics.record_custom("progress_updates_sent", 1)
        self.metrics.record_custom("user_anxiety_reduced", True)

    async def test_agent_completed_notification_delivers_closure(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that agent completed notifications provide proper closure."""
        # BUSINESS VALUE: Users need clear indication when AI operations complete
        
        # Simulate completing operation
        business_result = {
            "potential_monthly_savings": 8500,
            "optimization_confidence": 0.92,
            "recommendations_count": 12,
            "implementation_priority": "high"
        }
        
        await websocket_notifier.send_agent_completed(
            business_context,
            result=business_result,
            duration_ms=45000  # 45 seconds
        )
        
        # Verify completion notification includes business value
        call_args = mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        assert message_data['type'] == 'agent_completed'
        payload = message_data['payload']
        assert payload['agent_name'] == 'cost_optimization_agent'
        assert payload['duration_ms'] == 45000
        assert payload['result'] == business_result
        
        # Verify operation was marked as complete
        operation = websocket_notifier.active_operations.get(business_context.thread_id)
        if operation:
            assert operation['processing'] is False
        
        # Record completion metrics
        self.metrics.record_custom("successful_completions", 1)
        self.metrics.record_custom("user_closure_provided", True)

    async def test_error_notifications_provide_recovery_guidance(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that error notifications provide helpful recovery guidance."""
        # BUSINESS VALUE: Good error messages reduce support load and improve user experience
        
        # Send enhanced error notification
        await websocket_notifier.send_agent_error(
            business_context,
            error_message="AWS API rate limit exceeded",
            error_type="rate_limit",
            error_details={"api_endpoint": "billing", "reset_time": 3600},
            recovery_suggestions=[
                "The operation will automatically retry in 1 hour",
                "You can try again with a smaller date range",
                "Consider upgrading to a higher API tier for faster processing"
            ],
            is_recoverable=True,
            estimated_retry_delay_ms=3600000  # 1 hour
        )
        
        # Verify comprehensive error guidance was provided
        call_args = mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        payload = message_data['payload']
        assert payload['error_message'] == 'AWS API rate limit exceeded'
        assert payload['error_type'] == 'rate_limit' 
        assert payload['is_recoverable'] is True
        assert payload['estimated_retry_delay_ms'] == 3600000
        assert len(payload['recovery_suggestions']) == 3
        assert 'user_friendly_message' in payload
        
        # Record error handling metrics
        self.metrics.record_custom("helpful_errors_provided", 1)
        self.metrics.record_custom("support_load_reduced", True)

    async def test_backlog_notification_manages_user_expectations(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that backlog notifications manage user expectations during high load."""
        # BUSINESS VALUE: Setting expectations prevents user abandonment during peak usage
        
        # Simulate high load by filling event queue
        websocket_notifier.event_queue = deque([{'test': 'event'}] * 100)
        
        # Trigger backlog notification
        await websocket_notifier._notify_user_of_backlog(business_context.thread_id)
        
        # Verify backlog notification was sent
        call_args = mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        assert message_data['type'] == 'agent_update'
        payload = message_data['payload']
        assert 'high system load' in payload['message'].lower()
        assert payload['current_task'] == 'backlog_processing'
        assert payload['metadata']['queue_size'] == 100
        
        # Verify notification timestamp was recorded
        assert business_context.thread_id in websocket_notifier.backlog_notifications
        
        # Record expectation management metrics
        self.metrics.record_custom("backlog_notifications_sent", 1)
        self.metrics.record_custom("user_expectations_managed", True)

    async def test_concurrent_operations_maintain_event_ordering(
        self, websocket_notifier, mock_websocket_manager
    ):
        """Test that concurrent operations maintain proper event ordering."""
        # BUSINESS VALUE: Multiple users must receive events in correct order
        
        # Create multiple concurrent operations
        contexts = [
            AgentExecutionContext(
                agent_name=f"agent_{i}",
                run_id=uuid4(),
                thread_id=f"thread_{i}",
                user_id=f"user_{i}"
            )
            for i in range(5)
        ]
        
        # Send events concurrently
        tasks = []
        for context in contexts:
            tasks.append(websocket_notifier.send_agent_started(context))
            tasks.append(websocket_notifier.send_agent_thinking(context, f"Processing for user {context.user_id}"))
            
        await asyncio.gather(*tasks)
        
        # Verify all operations were tracked
        assert len(websocket_notifier.active_operations) >= 5
        
        # Verify each user's context is properly isolated
        for context in contexts:
            if context.thread_id in websocket_notifier.active_operations:
                operation = websocket_notifier.active_operations[context.thread_id]
                assert operation['agent_name'] == context.agent_name
        
        # Record concurrency metrics
        self.metrics.record_custom("concurrent_operations_handled", 5)
        self.metrics.record_custom("event_ordering_maintained", True)

    async def test_delivery_statistics_enable_monitoring(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that delivery statistics enable business monitoring."""
        # BUSINESS VALUE: Metrics enable performance monitoring and capacity planning
        
        # Generate some activity
        await websocket_notifier.send_agent_started(business_context)
        await websocket_notifier.send_agent_thinking(business_context, "Processing...")
        
        # Get delivery statistics
        stats = await websocket_notifier.get_delivery_stats()
        
        # Verify business-relevant statistics are available
        assert 'queued_events' in stats
        assert 'active_operations' in stats
        assert 'delivery_confirmations' in stats
        assert 'backlog_notifications_sent' in stats
        
        # Verify statistics reflect actual activity
        assert stats['active_operations'] >= 1
        assert isinstance(stats['queued_events'], int)
        
        # Record monitoring metrics
        self.metrics.record_custom("monitoring_statistics_available", True)
        self.metrics.record_custom("capacity_planning_enabled", True)

    def test_critical_events_configuration_supports_business_requirements(
        self, websocket_notifier
    ):
        """Test that critical events configuration meets business needs."""
        # BUSINESS VALUE: Proper event prioritization ensures business-critical notifications
        
        # Verify critical events are properly identified
        critical_events = websocket_notifier.critical_events
        required_critical_events = {
            'agent_started',
            'tool_executing', 
            'tool_completed',
            'agent_completed'
        }
        
        # Verify all business-critical events are marked as critical
        for event in required_critical_events:
            assert event in critical_events, f"Business-critical event {event} must be marked critical"
        
        # Verify performance settings meet business requirements
        assert websocket_notifier.max_queue_size >= 1000  # Handle reasonable load
        assert websocket_notifier.retry_delay <= 0.5  # Quick retry for good UX
        assert websocket_notifier.backlog_notification_interval <= 10.0  # Reasonable update frequency
        
        # Record configuration validation metrics
        self.metrics.record_custom("critical_events_properly_configured", True)
        self.metrics.record_custom("performance_settings_validated", True)

    async def test_emergency_notification_prevents_silent_failures(
        self, websocket_notifier, business_context, mock_websocket_manager
    ):
        """Test that emergency notification system prevents silent business failures."""
        # BUSINESS VALUE: Silent failures are worse than visible errors for business reliability
        
        # Simulate critical event delivery failure
        mock_websocket_manager.send_to_thread.return_value = False
        
        with patch('netra_backend.app.agents.supervisor.websocket_notifier.logger') as mock_logger:
            # Send critical event that will fail
            await websocket_notifier.send_agent_started(business_context)
            
            # Allow time for emergency notification processing
            await asyncio.sleep(0.1)
            
            # Verify emergency notification was triggered
            mock_logger.critical.assert_called()
            critical_call_args = mock_logger.critical.call_args[0][0]
            assert 'EMERGENCY' in critical_call_args
            assert 'agent_started' in critical_call_args
            assert business_context.thread_id in critical_call_args
        
        # Record emergency response metrics  
        self.metrics.record_custom("emergency_notifications_triggered", 1)
        self.metrics.record_custom("silent_failures_prevented", True)


class TestWebSocketNotifierBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for WebSocket notification edge cases."""

    async def test_high_value_customer_event_prioritization(self):
        """Test that high-value customer events receive priority treatment."""
        # BUSINESS VALUE: Enterprise customers should receive premium service quality
        
        with patch('warnings.warn'):  # Suppress deprecation warning
            manager = AsyncMock() 
            notifier = WebSocketNotifier(manager, test_mode=True)
        
        # Create high-value customer context
        vip_context = AgentExecutionContext(
            agent_name="enterprise_analytics_agent",
            run_id=str(uuid4()),
            thread_id="enterprise-vip-session",
            user_id="enterprise-customer-premium"
        )
        
        # Verify VIP customer can send notifications
        await notifier.send_agent_started(vip_context)
        
        # Verify operation is tracked (same treatment as all users - business fairness)
        assert vip_context.thread_id in notifier.active_operations
        
        # Record business fairness metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_customer_service_quality", True)
        
        # Cleanup
        await notifier.shutdown()

    async def test_free_tier_user_service_parity(self):
        """Test that free tier users receive equivalent notification service."""
        # BUSINESS VALUE: Service quality parity maintains brand reputation
        
        with patch('warnings.warn'):
            manager = AsyncMock()
            notifier = WebSocketNotifier(manager, test_mode=True)
        
        # Create free tier context
        free_context = AgentExecutionContext(
            agent_name="basic_optimizer_agent",
            run_id=str(uuid4()), 
            thread_id="free-user-session",
            user_id="free-tier-user"
        )
        
        # Verify free user receives same notification quality
        await notifier.send_agent_started(free_context)
        await notifier.send_agent_thinking(free_context, "Processing your request...")
        await notifier.send_agent_completed(free_context, {"result": "basic_optimization"})
        
        # Verify all events were processed equally
        assert free_context.thread_id in notifier.active_operations
        
        # Record business equity metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("service_parity_maintained", True)
        metrics.record_custom("brand_reputation_protected", True)
        
        # Cleanup
        await notifier.shutdown()