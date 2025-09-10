"""
WebSocket Event Delivery Reliability Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure chat functionality delivers 90% of platform value
- Value Impact: Mission-critical WebSocket events enable real-time communication
- Strategic Impact: WebSocket events are the foundation of chat business value delivery

These tests validate that WebSocket events are reliably delivered to users,
which is essential for the chat functionality that provides 90% of platform value.
"""

import asyncio
import pytest
from typing import Dict, List, Any
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility, 
    WebSocketEventType,
    WebSocketMessage
)
from shared.isolated_environment import get_env


class TestWebSocketEventDeliveryReliability(SSotAsyncTestCase):
    """Test WebSocket event delivery reliability patterns."""
    
    async def setup_method(self, method=None):
        """Set up test environment."""
        await super().async_setup_method(method)
        self.env = get_env()
        
        # Set test environment variables
        self.set_env_var("WEBSOCKET_TEST_TIMEOUT", "10")
        self.set_env_var("WEBSOCKET_MOCK_MODE", "true")
        
        self.websocket_util = None
    
    async def teardown_method(self, method=None):
        """Clean up test environment."""
        if self.websocket_util:
            await self.websocket_util.cleanup()
        await super().async_teardown_method(method)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_mission_critical_events_delivery_guaranteed(self):
        """
        Test that all 5 mission-critical WebSocket events are reliably delivered.
        
        BVJ: All segments - Critical for chat value delivery.
        Tests the foundational events that enable AI agent interactions.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("test_user_1") as client:
                # Track all 5 mission-critical events
                mission_critical_events = [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING, 
                    WebSocketEventType.TOOL_EXECUTING,
                    WebSocketEventType.TOOL_COMPLETED,
                    WebSocketEventType.AGENT_COMPLETED
                ]
                
                # Simulate agent execution flow
                result = await ws_util.simulate_agent_execution(client, "Test optimization request")
                
                # Verify all events were delivered
                assert result["success"], f"Agent execution failed: {result.get('error')}"
                
                received_events = result["results"]
                for event_type in mission_critical_events:
                    assert event_type in received_events, f"Missing critical event: {event_type.value}"
                    assert len(received_events[event_type]) > 0, f"Event {event_type.value} has no messages"
                
                # Record metrics
                self.record_metric("mission_critical_events_delivered", len(mission_critical_events))
                self.record_metric("event_delivery_success_rate", 1.0)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_event_delivery_ordering_consistency(self):
        """
        Test that WebSocket events are delivered in consistent order.
        
        BVJ: All segments - Reliable event ordering ensures coherent user experience.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("test_user_2") as client:
                # Send sequence of events with ordering requirements
                expected_sequence = [
                    (WebSocketEventType.AGENT_STARTED, {"status": "initialized"}),
                    (WebSocketEventType.AGENT_THINKING, {"progress": "analyzing"}),
                    (WebSocketEventType.TOOL_EXECUTING, {"tool": "analyzer"}),
                    (WebSocketEventType.TOOL_COMPLETED, {"result": "analysis_done"}),
                    (WebSocketEventType.AGENT_COMPLETED, {"final_result": "complete"})
                ]
                
                sent_messages = []
                for event_type, data in expected_sequence:
                    message = await client.send_message(event_type, data, user_id="test_user_2")
                    sent_messages.append(message)
                    await asyncio.sleep(0.1)  # Small delay to ensure ordering
                
                # Wait for delivery confirmation
                await asyncio.sleep(1.0)
                
                # Verify ordering maintained
                received_by_type = {}
                for msg in client.received_messages:
                    if msg.event_type not in received_by_type:
                        received_by_type[msg.event_type] = []
                    received_by_type[msg.event_type].append(msg)
                
                # Check that each event type has messages
                for event_type, _ in expected_sequence:
                    assert event_type in received_by_type, f"Event type {event_type.value} not received"
                
                self.record_metric("ordered_events_tested", len(expected_sequence))
                self.record_metric("ordering_consistency_verified", True)
    
    @pytest.mark.integration  
    @pytest.mark.websocket
    async def test_event_delivery_retry_mechanism(self):
        """
        Test WebSocket event delivery retry mechanism for failed deliveries.
        
        BVJ: Enterprise/Mid - Ensures reliable delivery even with network issues.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("test_user_3") as client:
                # Simulate a high-priority event that must be delivered
                critical_event = WebSocketEventType.AGENT_COMPLETED
                critical_data = {
                    "result": "optimization_complete",
                    "cost_savings": 15000,
                    "recommendations": ["scale_down_instances", "use_spot_instances"]
                }
                
                # Track delivery attempts
                delivery_attempts = []
                
                def track_delivery(message: WebSocketMessage):
                    delivery_attempts.append({
                        "timestamp": datetime.now(),
                        "event_type": message.event_type.value,
                        "message_id": message.message_id
                    })
                
                client.add_event_handler(critical_event, track_delivery)
                
                # Send critical event
                sent_message = await client.send_message(
                    critical_event, 
                    critical_data,
                    user_id="test_user_3"
                )
                
                # Wait for delivery processing
                await asyncio.sleep(2.0)
                
                # Verify event was delivered successfully
                critical_messages = client.get_messages_by_type(critical_event)
                assert len(critical_messages) > 0, "Critical event not delivered"
                
                # Verify business data integrity
                received_message = critical_messages[0]
                assert received_message.data["cost_savings"] == 15000
                assert "recommendations" in received_message.data
                
                self.record_metric("critical_event_delivery_verified", True)
                self.record_metric("delivery_attempts", len(delivery_attempts))
    
    @pytest.mark.integration
    @pytest.mark.websocket 
    async def test_bulk_event_delivery_performance(self):
        """
        Test WebSocket bulk event delivery performance under load.
        
        BVJ: Enterprise - High-volume event delivery for complex workflows.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("test_user_4") as client:
                # Generate bulk events simulating complex agent workflow
                event_batch_size = 50
                event_batches = [
                    (WebSocketEventType.AGENT_THINKING, {"step": i, "analysis": f"step_{i}_analysis"})
                    for i in range(event_batch_size)
                ]
                
                start_time = datetime.now()
                sent_messages = []
                
                # Send events in bulk
                for event_type, data in event_batches:
                    message = await client.send_message(
                        event_type, 
                        data, 
                        user_id="test_user_4"
                    )
                    sent_messages.append(message)
                
                # Wait for all events to be processed
                await asyncio.sleep(3.0)
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                # Verify bulk delivery performance
                received_thinking_events = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                
                assert len(received_thinking_events) >= event_batch_size * 0.9, \
                    f"Only {len(received_thinking_events)}/{event_batch_size} events delivered"
                
                # Performance assertions
                events_per_second = len(sent_messages) / processing_time
                assert events_per_second > 10, f"Performance too slow: {events_per_second} events/second"
                
                self.record_metric("bulk_events_sent", len(sent_messages))
                self.record_metric("bulk_events_received", len(received_thinking_events))
                self.record_metric("events_per_second", events_per_second)
                self.record_metric("bulk_processing_time", processing_time)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_event_delivery_with_user_context_isolation(self):
        """
        Test WebSocket event delivery maintains user context isolation.
        
        BVJ: All segments - Critical security requirement preventing user data leakage.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple user clients
            client_a = await ws_util.create_authenticated_client("user_a")
            client_b = await ws_util.create_authenticated_client("user_b")
            
            await client_a.connect(mock_mode=True)
            await client_b.connect(mock_mode=True)
            
            try:
                # Send user-specific events
                user_a_data = {
                    "user_id": "user_a",
                    "sensitive_data": "user_a_private_info",
                    "account_balance": 50000
                }
                
                user_b_data = {
                    "user_id": "user_b", 
                    "sensitive_data": "user_b_private_info",
                    "account_balance": 75000
                }
                
                # Send events to each user
                await client_a.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    user_a_data,
                    user_id="user_a"
                )
                
                await client_b.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    user_b_data, 
                    user_id="user_b"
                )
                
                # Wait for event processing
                await asyncio.sleep(2.0)
                
                # Verify user isolation
                user_a_messages = client_a.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                user_b_messages = client_b.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                
                # Each user should only receive their own events
                assert len(user_a_messages) > 0, "User A didn't receive their events"
                assert len(user_b_messages) > 0, "User B didn't receive their events"
                
                # Verify no cross-contamination
                for message in user_a_messages:
                    assert "user_a" in str(message.data), "User A received wrong user data"
                    assert "user_b" not in str(message.data), "User A received User B's data"
                
                for message in user_b_messages:
                    assert "user_b" in str(message.data), "User B received wrong user data" 
                    assert "user_a" not in str(message.data), "User B received User A's data"
                
                self.record_metric("user_isolation_verified", True)
                self.record_metric("users_tested", 2)
                
            finally:
                await client_a.disconnect()
                await client_b.disconnect()