"""Test WebSocketNotifier Business Logic

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise)
- Business Goal: Real-time User Engagement & Experience  
- Value Impact: Ensures users receive timely AI agent feedback, reducing abandonment
- Strategic Impact: Core chat experience - failed notifications = lost customers
"""

import asyncio
import pytest
import time
from collections import deque
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class TestWebSocketNotifier.create_for_user(BaseIntegrationTest):
    """Test WebSocketNotifier pure business logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_websocket_manager = AsyncMock()
        
        # Initialize notifier in test mode to prevent hanging background tasks
        self.notifier = WebSocketNotifier(
            websocket_manager=self.mock_websocket_manager, test_mode=True
        )

    @pytest.mark.unit 
    def test_critical_event_delivery_business_guarantee(self):
        """Test guaranteed delivery of critical business events."""
        # Business Value: Critical events (agent_started, tool_executing) must reach users
        context = AgentExecutionContext(
            agent_name="revenue_analyzer", 
            run_id=RequestID("run-critical-123"),
            correlation_id="corr-critical-456"
        )
        context.thread_id = ThreadID("thread-critical-789")
        
        # Mock successful delivery
        self.mock_websocket_manager.send_to_thread.return_value = True
        
        # Test critical event delivery
        result = asyncio.run(self.notifier._send_critical_event(
            ThreadID("thread-critical-789"), 
            Mock(spec=WebSocketMessage),
            'agent_started'
        ))
        
        # Verify critical event was delivered
        self.assertTrue(result)
        self.mock_websocket_manager.send_to_thread.assert_called_once()

    @pytest.mark.unit
    def test_agent_thinking_progress_business_value(self):
        """Test agent thinking notifications provide user progress visibility."""
        # Business Value: Progress updates keep users engaged during long AI operations
        context = AgentExecutionContext(
            agent_name="cost_optimizer",
            run_id=RequestID("run-think-123"), 
            correlation_id="corr-think-456"
        )
        context.thread_id = ThreadID("thread-think-789")
        
        # Test enhanced thinking with business context
        asyncio.run(self.notifier.send_agent_thinking(
            context=context,
            thought="Analyzing your cloud infrastructure costs...",
            step_number=3,
            progress_percentage=60.0,
            estimated_remaining_ms=15000,
            current_operation="cost_analysis"
        ))
        
        # Verify business-relevant thinking payload
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        payload = call_args[0][1]['payload']
        
        self.assertEqual(payload['progress_percentage'], 60.0)
        self.assertEqual(payload['estimated_remaining_ms'], 15000)
        self.assertEqual(payload['current_operation'], "cost_analysis")
        self.assertIn("urgency", payload)  # Business urgency indicator

    @pytest.mark.unit
    def test_tool_execution_business_transparency(self):
        """Test tool execution notifications provide business transparency."""
        # Business Value: Tool visibility builds user trust in AI decision-making
        context = AgentExecutionContext(
            agent_name="data_processor",
            run_id=RequestID("run-tool-123"),
            correlation_id="corr-tool-456" 
        )
        context.thread_id = ThreadID("thread-tool-789")
        
        # Test enhanced tool executing notification
        asyncio.run(self.notifier.send_tool_executing(
            context=context,
            tool_name="database_query",
            tool_purpose="Retrieving customer usage metrics",
            estimated_duration_ms=5000,
            parameters_summary="Query last 30 days of usage data"
        ))
        
        # Verify business context in tool notification
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        payload = call_args[0][1]['payload']
        
        self.assertEqual(payload['tool_purpose'], "Retrieving customer usage metrics")
        self.assertEqual(payload['estimated_duration_ms'], 5000)
        self.assertEqual(payload['parameters_summary'], "Query last 30 days of usage data")
        self.assertEqual(payload['execution_phase'], "starting")

    @pytest.mark.unit
    def test_error_recovery_suggestions_business_guidance(self):
        """Test error notifications provide actionable business guidance."""
        # Business Value: Clear error guidance reduces user frustration and support tickets
        context = AgentExecutionContext(
            agent_name="billing_analyzer", 
            run_id=RequestID("run-error-123"),
            correlation_id="corr-error-456"
        )
        context.thread_id = ThreadID("thread-error-789")
        
        # Test enhanced error notification
        asyncio.run(self.notifier.send_agent_error(
            context=context,
            error_message="Database connection timeout",
            error_type="timeout",
            is_recoverable=True,
            estimated_retry_delay_ms=30000
        ))
        
        # Verify business-focused error guidance
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        payload = call_args[0][1]['payload']
        
        self.assertEqual(payload['error_type'], "timeout")
        self.assertTrue(payload['is_recoverable'])
        self.assertEqual(payload['estimated_retry_delay_ms'], 30000)
        self.assertIn('recovery_suggestions', payload)
        self.assertIn('user_friendly_message', payload)
        
        # Verify actionable recovery suggestions
        suggestions = payload['recovery_suggestions']
        self.assertTrue(any("longer than expected" in s for s in suggestions))

    @pytest.mark.unit
    def test_backlog_notification_business_communication(self):
        """Test backlog notifications maintain user engagement."""
        # Business Value: Backlog awareness prevents user abandonment during peak load
        thread_id = ThreadID("thread-backlog-123")
        
        # Simulate backlog scenario
        self.notifier.backlog_notifications[thread_id] = time.time() - 10  # 10 seconds ago
        
        # Test backlog notification
        asyncio.run(self.notifier._notify_user_of_backlog(thread_id))
        
        # Verify backlog message sent
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        # Verify business-appropriate backlog message
        payload = call_args[0][1]['payload'] 
        self.assertIn("slight delay", payload['message'])
        self.assertIn("high system load", payload['message'])

    @pytest.mark.unit
    def test_operation_activity_tracking_business_metrics(self):
        """Test operation tracking provides business activity insights."""
        # Business Value: Activity metrics enable capacity planning and optimization
        context = AgentExecutionContext(
            agent_name="capacity_planner",
            run_id=RequestID("run-activity-123"),
            correlation_id="corr-activity-456"
        )
        context.thread_id = ThreadID("thread-activity-789")
        
        # Test operation marking
        self.notifier._mark_operation_active(context)
        
        # Verify business activity tracking
        activity = self.notifier.active_operations[context.thread_id]
        self.assertEqual(activity['agent_name'], "capacity_planner")
        self.assertEqual(activity['run_id'], RequestID("run-activity-123"))
        self.assertTrue(activity['processing'])
        self.assertEqual(activity['event_count'], 0)

    @pytest.mark.unit
    def test_delivery_confirmation_business_reliability(self):
        """Test delivery confirmations ensure business-critical message receipt."""
        # Business Value: Confirmation tracking prevents lost critical business events
        event_data = {
            'message_id': 'msg-123',
            'thread_id': ThreadID("thread-confirm-456"),
            'message': Mock(model_dump=Mock(return_value={})),
            'event_type': 'agent_started',
            'requires_confirmation': True
        }
        
        # Mock successful delivery
        self.mock_websocket_manager.send_to_thread.return_value = True
        
        # Test delivery attempt
        success = asyncio.run(self.notifier._attempt_delivery(event_data))
        
        # Verify confirmation tracking for business-critical events
        self.assertTrue(success)
        self.assertIn('msg-123', self.notifier.delivery_confirmations)

    @pytest.mark.unit
    def test_emergency_notification_business_escalation(self):
        """Test emergency notifications for critical business failures."""
        # Business Value: Critical failures require immediate business attention
        thread_id = ThreadID("thread-emergency-123")
        event_type = 'agent_started'
        
        # Test emergency notification
        asyncio.run(self.notifier._trigger_emergency_notification(thread_id, event_type))
        
        # Verify emergency tracking for business escalation
        self.assertTrue(hasattr(self.notifier, '_failed_critical_events'))
        failures = self.notifier._failed_critical_events
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['event_type'], 'agent_started')
        self.assertEqual(failures[0]['thread_id'], thread_id)

    @pytest.mark.unit
    def test_user_friendly_error_messages_business_communication(self):
        """Test user-friendly error messages improve customer experience."""
        # Business Value: Clear error communication reduces user confusion and churn
        
        # Test timeout error message
        timeout_msg = self.notifier._generate_user_friendly_error_message(
            "timeout", "Operation exceeded time limit", "cost_analyzer"
        )
        self.assertIn("cost_analyzer", timeout_msg)
        self.assertIn("longer than usual", timeout_msg)
        
        # Test rate limit error message  
        rate_limit_msg = self.notifier._generate_user_friendly_error_message(
            "rate_limit", "Too many requests", "data_processor"
        )
        self.assertIn("many requests recently", rate_limit_msg)
        self.assertIn("wait a moment", rate_limit_msg)

    @pytest.mark.unit
    def test_tool_context_hints_business_intelligence(self):
        """Test tool context hints provide business operation insights."""
        # Business Value: Tool categorization helps users understand AI capabilities
        
        # Test search tool context
        search_context = self.notifier._get_tool_context_hints("search_customers")
        self.assertEqual(search_context['category'], "information_retrieval")
        self.assertEqual(search_context['expected_duration'], "medium")
        
        # Test analysis tool context
        analyze_context = self.notifier._get_tool_context_hints("analyze_costs") 
        self.assertEqual(analyze_context['category'], "data_processing")
        self.assertEqual(analyze_context['expected_duration'], "long")

    @pytest.mark.unit
    def test_delivery_statistics_business_monitoring(self):
        """Test delivery statistics provide business health monitoring."""
        # Business Value: Event delivery metrics enable system health assessment
        
        # Set up test state
        self.notifier.event_queue.append({"test": "event"})
        self.notifier.active_operations["thread-1"] = {"status": "active"}
        self.notifier.delivery_confirmations["msg-1"] = time.time()
        
        # Get delivery statistics
        stats = asyncio.run(self.notifier.get_delivery_stats())
        
        # Verify business monitoring data
        self.assertEqual(stats['queued_events'], 1)
        self.assertEqual(stats['active_operations'], 1) 
        self.assertEqual(stats['delivery_confirmations'], 1)
        self.assertIn('backlog_notifications_sent', stats)