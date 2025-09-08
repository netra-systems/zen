"""
Integration Tests for WebSocket Event Delivery Validation - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable end-to-end WebSocket event delivery
- Value Impact: Users receive real-time updates enabling chat engagement and trust
- Strategic Impact: Core platform reliability - event delivery failures = lost customers

CRITICAL: This tests the complete event delivery pipeline with real WebSocket connections.
Uses real services to validate that events actually reach users.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types import UserID, ThreadID, RunID
from shared.isolated_environment import get_env

class TestWebSocketEventDeliveryValidation(BaseIntegrationTest):
    """Integration tests for WebSocket event delivery with real connections."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_delivery_end_to_end(self, real_services_fixture):
        """
        Test complete event delivery from generation to user reception.
        
        Business Value: Validates that users actually receive agent progress updates.
        CRITICAL: Without this, users see no AI activity and abandon the platform.
        """
        # Arrange: Setup real services
        env = get_env()
        websocket_url = f"ws://localhost:{env.get('BACKEND_PORT', '8000')}/ws"
        user_id = UserID("integration_test_user_001")
        thread_id = ThreadID("integration_test_thread_001")
        run_id = RunID("integration_test_run_001")
        
        # Create real WebSocket connection
        events_received = []
        
        async with WebSocketTestClient(websocket_url, str(user_id)) as ws_client:
            # Setup event capture
            async def capture_events():
                try:
                    async for message in ws_client.receive_events(timeout=10):
                        events_received.append(message)
                        if message.get("type") == "agent_completed":
                            break
                except asyncio.TimeoutError:
                    pass  # Expected when no more events
            
            # Start event capture task
            capture_task = asyncio.create_task(capture_events())
            
            # Act: Generate events through real bridge
            bridge = AgentWebSocketBridge()
            await bridge.ensure_integration()
            
            # Create execution context
            execution_context = Mock(spec=AgentExecutionContext)
            execution_context.user_id = user_id
            execution_context.thread_id = thread_id
            execution_context.run_id = run_id
            execution_context.agent_name = "integration_test_agent"
            
            # Send all critical events
            notifier = bridge.get_websocket_notifier()
            await notifier.notify_agent_started(execution_context)
            await asyncio.sleep(0.1)  # Brief pause for event delivery
            
            await notifier.notify_agent_thinking(execution_context, "Analyzing your request for cost optimization opportunities...")
            await asyncio.sleep(0.1)
            
            await notifier.notify_tool_executing(execution_context, "cost_analyzer", {"timeframe": "30_days"})
            await asyncio.sleep(0.1)
            
            await notifier.notify_tool_completed(execution_context, "cost_analyzer", {"potential_savings": 2500.00})
            await asyncio.sleep(0.1)
            
            await notifier.notify_agent_completed(execution_context, {
                "summary": "Found significant cost optimization opportunities",
                "total_savings": 2500.00,
                "recommendations": 3
            })
            
            # Wait for event capture completion
            await asyncio.sleep(1)  # Allow event delivery
            capture_task.cancel()
            
            # Assert: Verify all events were delivered
            assert len(events_received) >= 5, f"Expected 5 events, got {len(events_received)}"
            
            event_types = [event.get("type") for event in events_received]
            expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            # Business requirement: All critical events must be delivered
            for expected_type in expected_types:
                assert expected_type in event_types, f"Missing critical event: {expected_type}"
            
            # Verify event content for business value
            completed_event = next(e for e in events_received if e.get("type") == "agent_completed")
            assert "savings" in str(completed_event).lower()
            assert completed_event["result"]["total_savings"] > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_ordering_delivery(self, real_services_fixture):
        """
        Test that events are delivered in correct order.
        
        Business Value: Users see logical progression of AI work.
        Out-of-order events confuse users and reduce trust.
        """
        # Arrange
        env = get_env()
        websocket_url = f"ws://localhost:{env.get('BACKEND_PORT', '8000')}/ws"
        user_id = UserID("integration_test_user_002")
        
        events_received = []
        event_timestamps = []
        
        async with WebSocketTestClient(websocket_url, str(user_id)) as ws_client:
            # Setup ordered event capture
            async def capture_ordered_events():
                try:
                    async for message in ws_client.receive_events(timeout=8):
                        events_received.append(message)
                        event_timestamps.append(time.time())
                        if len(events_received) >= 3:  # Capture first 3 events
                            break
                except asyncio.TimeoutError:
                    pass
            
            capture_task = asyncio.create_task(capture_ordered_events())
            
            # Act: Send events rapidly to test ordering
            bridge = AgentWebSocketBridge()
            await bridge.ensure_integration()
            notifier = bridge.get_websocket_notifier()
            
            execution_context = Mock(spec=AgentExecutionContext)
            execution_context.user_id = user_id
            execution_context.thread_id = ThreadID("order_test_thread")
            execution_context.run_id = RunID("order_test_run")
            execution_context.agent_name = "ordering_test_agent"
            
            # Send events in rapid succession
            await notifier.notify_agent_started(execution_context)
            await notifier.notify_agent_thinking(execution_context, "Starting analysis...")
            await notifier.notify_tool_executing(execution_context, "analyzer", {})
            
            await capture_task
            
            # Assert: Events delivered in correct order
            assert len(events_received) >= 3
            
            event_types = [event.get("type") for event in events_received[:3]]
            expected_order = ["agent_started", "agent_thinking", "tool_executing"]
            
            assert event_types == expected_order, f"Events out of order: {event_types}"
            
            # Business requirement: Timestamps show proper progression
            for i in range(1, len(event_timestamps)):
                assert event_timestamps[i] >= event_timestamps[i-1], "Event timestamps show incorrect ordering"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_event_delivery_resilience(self, real_services_fixture):
        """
        Test event delivery continues after connection interruptions.
        
        Business Value: Users don't lose progress visibility during network issues.
        Ensures reliable chat experience even with connectivity problems.
        """
        # Arrange
        env = get_env()
        websocket_url = f"ws://localhost:{env.get('BACKEND_PORT', '8000')}/ws"
        user_id = UserID("resilience_test_user_003")
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        notifier = bridge.get_websocket_notifier()
        
        execution_context = Mock(spec=AgentExecutionContext)
        execution_context.user_id = user_id
        execution_context.thread_id = ThreadID("resilience_thread")
        execution_context.run_id = RunID("resilience_run")
        execution_context.agent_name = "resilience_agent"
        
        # Act & Assert: Test resilience to connection issues
        events_received_batch1 = []
        events_received_batch2 = []
        
        # First connection - receive some events
        async with WebSocketTestClient(websocket_url, str(user_id)) as ws_client1:
            async def capture_batch1():
                async for message in ws_client1.receive_events(timeout=3):
                    events_received_batch1.append(message)
                    if len(events_received_batch1) >= 2:
                        break
            
            capture_task1 = asyncio.create_task(capture_batch1())
            
            await notifier.notify_agent_started(execution_context)
            await notifier.notify_agent_thinking(execution_context, "Processing...")
            
            await capture_task1
        
        # Connection drops here (client disconnected)
        await asyncio.sleep(0.5)
        
        # Second connection - should still receive new events
        async with WebSocketTestClient(websocket_url, str(user_id)) as ws_client2:
            async def capture_batch2():
                async for message in ws_client2.receive_events(timeout=3):
                    events_received_batch2.append(message)
                    if len(events_received_batch2) >= 1:
                        break
            
            capture_task2 = asyncio.create_task(capture_batch2())
            
            await notifier.notify_agent_completed(execution_context, {"status": "completed"})
            
            await capture_task2
        
        # Assert: Events delivered across connection interruption
        assert len(events_received_batch1) >= 2, "First batch should have received events"
        assert len(events_received_batch2) >= 1, "Second batch should have received events after reconnection"
        
        # Business requirement: No critical events lost during reconnection
        all_event_types = ([e.get("type") for e in events_received_batch1] + 
                          [e.get("type") for e in events_received_batch2])
        assert "agent_started" in all_event_types
        assert "agent_completed" in all_event_types

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_user_isolation_delivery(self, real_services_fixture):
        """
        Test that events are delivered only to correct users.
        
        Business Value: Ensures user privacy and data isolation.
        CRITICAL: Users must not see other users' agent activity.
        """
        # Arrange: Two different users
        env = get_env()
        websocket_url = f"ws://localhost:{env.get('BACKEND_PORT', '8000')}/ws"
        user1_id = UserID("isolation_user_001")
        user2_id = UserID("isolation_user_002")
        
        user1_events = []
        user2_events = []
        
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        notifier = bridge.get_websocket_notifier()
        
        # Act: Create separate connections for each user
        async with WebSocketTestClient(websocket_url, str(user1_id)) as ws1, \
                   WebSocketTestClient(websocket_url, str(user2_id)) as ws2:
            
            # Setup event capture for both users
            async def capture_user1():
                async for message in ws1.receive_events(timeout=5):
                    user1_events.append(message)
                    if len(user1_events) >= 2:
                        break
            
            async def capture_user2():
                async for message in ws2.receive_events(timeout=5):
                    user2_events.append(message)
                    if len(user2_events) >= 2:
                        break
            
            capture1 = asyncio.create_task(capture_user1())
            capture2 = asyncio.create_task(capture_user2())
            
            # Send events for user1 only
            user1_context = Mock(spec=AgentExecutionContext)
            user1_context.user_id = user1_id
            user1_context.thread_id = ThreadID("user1_thread")
            user1_context.run_id = RunID("user1_run")
            user1_context.agent_name = "user1_agent"
            
            await notifier.notify_agent_started(user1_context)
            await notifier.notify_agent_completed(user1_context, {"user": "user1_result"})
            
            # Send events for user2 only
            user2_context = Mock(spec=AgentExecutionContext)
            user2_context.user_id = user2_id
            user2_context.thread_id = ThreadID("user2_thread")
            user2_context.run_id = RunID("user2_run")
            user2_context.agent_name = "user2_agent"
            
            await notifier.notify_agent_started(user2_context)
            await notifier.notify_agent_completed(user2_context, {"user": "user2_result"})
            
            # Wait for all events
            await asyncio.sleep(1)
            capture1.cancel()
            capture2.cancel()
            
        # Assert: Each user received only their events
        assert len(user1_events) >= 2, "User1 should receive their events"
        assert len(user2_events) >= 2, "User2 should receive their events"
        
        # Business requirement: No cross-user event leakage
        user1_content = str(user1_events)
        user2_content = str(user2_events)
        
        assert "user1_result" in user1_content
        assert "user1_result" not in user2_content  # Critical: User2 must not see User1's results
        
        assert "user2_result" in user2_content
        assert "user2_result" not in user1_content  # Critical: User1 must not see User2's results

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_content_validation(self, real_services_fixture):
        """
        Test that delivered events contain required business-critical content.
        
        Business Value: Ensures events provide actionable information to users.
        Empty or malformed events provide no value and frustrate users.
        """
        # Arrange
        env = get_env()
        websocket_url = f"ws://localhost:{env.get('BACKEND_PORT', '8000')}/ws"
        user_id = UserID("content_validation_user")
        
        events_received = []
        
        async with WebSocketTestClient(websocket_url, str(user_id)) as ws_client:
            # Setup content validation capture
            async def capture_for_validation():
                async for message in ws_client.receive_events(timeout=6):
                    events_received.append(message)
                    if message.get("type") == "agent_completed":
                        break
            
            capture_task = asyncio.create_task(capture_for_validation())
            
            # Act: Send events with rich business content
            bridge = AgentWebSocketBridge()
            await bridge.ensure_integration()
            notifier = bridge.get_websocket_notifier()
            
            execution_context = Mock(spec=AgentExecutionContext)
            execution_context.user_id = user_id
            execution_context.thread_id = ThreadID("validation_thread")
            execution_context.run_id = RunID("validation_run")
            execution_context.agent_name = "content_validation_agent"
            
            await notifier.notify_agent_started(execution_context)
            await notifier.notify_agent_thinking(execution_context, 
                "Analyzing your cloud infrastructure for cost optimization opportunities...")
            await notifier.notify_tool_executing(execution_context, "cloud_cost_analyzer", 
                {"provider": "aws", "timeframe": "30_days", "services": ["ec2", "s3", "rds"]})
            await notifier.notify_tool_completed(execution_context, "cloud_cost_analyzer", {
                "current_monthly_cost": 8750.25,
                "potential_monthly_savings": 1312.50,
                "optimization_confidence": 0.87,
                "top_recommendations": [
                    "Resize 3 oversized EC2 instances",
                    "Enable S3 intelligent tiering",
                    "Optimize RDS instance class"
                ]
            })
            await notifier.notify_agent_completed(execution_context, {
                "summary": "Identified $1,312.50 monthly savings opportunity",
                "total_annual_savings": 15750.00,
                "implementation_effort": "medium",
                "recommendations_count": 3,
                "confidence_score": 87
            })
            
            await capture_task
            
        # Assert: Validate business-critical content in each event type
        assert len(events_received) >= 5
        
        # Validate agent_started content
        started_event = next(e for e in events_received if e.get("type") == "agent_started")
        assert "thread_id" in started_event
        assert "agent_name" in started_event
        assert "timestamp" in started_event
        
        # Validate agent_thinking content provides value
        thinking_event = next(e for e in events_received if e.get("type") == "agent_thinking")
        thinking_content = thinking_event.get("content", "")
        assert len(thinking_content) > 20  # Substantial thinking content
        assert any(word in thinking_content.lower() for word in ["analyzing", "optimization", "cost", "cloud"])
        
        # Validate tool_executing shows actionable tool usage
        executing_event = next(e for e in events_received if e.get("type") == "tool_executing")
        assert executing_event.get("tool_name") == "cloud_cost_analyzer"
        tool_params = executing_event.get("tool_params", {})
        assert "provider" in tool_params
        assert "timeframe" in tool_params
        
        # Validate tool_completed shows quantifiable results
        completed_tool_event = next(e for e in events_received if e.get("type") == "tool_completed")
        tool_result = completed_tool_event.get("tool_result", {})
        assert "current_monthly_cost" in tool_result
        assert "potential_monthly_savings" in tool_result
        assert tool_result["potential_monthly_savings"] > 0
        
        # Validate agent_completed shows business value delivered
        final_event = next(e for e in events_received if e.get("type") == "agent_completed")
        result = final_event.get("result", {})
        assert "total_annual_savings" in result
        assert result["total_annual_savings"] > 0
        assert "recommendations_count" in result
        assert result["recommendations_count"] > 0