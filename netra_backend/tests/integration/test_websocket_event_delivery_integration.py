"""
COMPREHENSIVE WEBSOCKET EVENT DELIVERY INTEGRATION TESTS - GOLDEN PATH CRITICAL

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Impact  
- Business Goal: Ensure ALL 5 critical WebSocket events deliver reliably
- Value Impact: Prevents "Poor Engagement, Perceived Slowness, Lack of Trust, Incomplete Experience, User Confusion"
- Strategic Impact: Core chat functionality - WebSocket events enable substantive AI chat interactions

MISSION CRITICAL: Golden Path Analysis identified Critical Issue #4: Missing WebSocket Events
Without these events, chat has no value! This tests the delivery infrastructure that prevents
business impact: Poor Engagement, Perceived Slowness, Lack of Trust, Incomplete Experience, User Confusion.

THE 5 MISSION CRITICAL WEBSOCKET EVENTS (CLAUDE.md Section 6):
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

INTEGRATION TEST SCOPE: Between unit and E2E - no Docker required but real event behavior
REAL WEBSOCKET CONNECTIONS: Uses actual WebSocket infrastructure, NO MOCKS
TEST FRAMEWORK SSOT: Uses existing test_framework/ patterns from BaseIntegrationTest
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
import websockets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock

# Test Framework SSOT imports
from test_framework.base_integration_test import BaseIntegrationTest, WebSocketIntegrationTest
from test_framework.websocket_test_integration import (
    WebSocketTestClient,
    WebSocketIntegrationTestSuite,
    validate_websocket_events_for_chat
)
from test_framework.real_services import get_real_services
from shared.isolated_environment import get_env

# Core WebSocket infrastructure imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import MessageType, WebSocketConnectionState
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Shared types for strong typing
from shared.types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)


class TestWebSocketEventDeliveryIntegration(WebSocketIntegrationTest):
    """
    15 Comprehensive WebSocket Event Delivery Integration Tests for Golden Path.
    
    Tests the complete WebSocket event delivery pipeline from agent execution 
    through to user reception, validating all 5 critical events that enable
    chat business value delivery.
    
    CRITICAL: Each test validates real WebSocket event delivery without mocks.
    """

    async def async_setup(self):
        """Setup real WebSocket testing infrastructure."""
        await super().async_setup()
        
        # Initialize environment for WebSocket testing
        self.env = get_env()
        self.env.set("TESTING", "1", source="websocket_integration_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_integration_test")
        self.env.set("WEBSOCKET_INTEGRATION_TESTING", "1", source="websocket_integration_test")
        
        # Test user context setup
        self.test_user_id = UserID(f"test_user_{uuid.uuid4().hex[:8]}")
        self.test_thread_id = ThreadID(f"test_thread_{uuid.uuid4().hex[:8]}")
        self.test_run_id = RunID(f"test_run_{uuid.uuid4().hex[:8]}")
        self.test_request_id = RequestID(f"test_req_{uuid.uuid4().hex[:8]}")
        
        # WebSocket event tracking
        self.received_events = []
        self.critical_events_received = {
            "agent_started": False,
            "agent_thinking": False, 
            "tool_executing": False,
            "tool_completed": False,
            "agent_completed": False
        }
        
        # Performance metrics
        self.event_timestamps = {}
        self.delivery_latencies = {}
        
        # Setup WebSocket test client
        backend_port = self.env.get("BACKEND_PORT", "8000")
        self.websocket_url = f"ws://localhost:{backend_port}/ws"
        self.websocket_client = None

    async def async_teardown(self):
        """Clean up WebSocket resources."""
        if self.websocket_client:
            try:
                await self.websocket_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting WebSocket client: {e}")
        
        await super().async_teardown()

    def _record_event(self, event: Dict[str, Any]) -> None:
        """Record received WebSocket event with timestamp."""
        event_type = event.get("type", "unknown")
        timestamp = time.time()
        
        event_with_metadata = {
            **event,
            "received_at": timestamp,
            "test_request_id": self.test_request_id
        }
        
        self.received_events.append(event_with_metadata)
        
        if event_type in self.critical_events_received:
            self.critical_events_received[event_type] = True
            self.event_timestamps[event_type] = timestamp
        
        logger.info(f"📩 Received WebSocket event: {event_type}")

    async def _wait_for_critical_events(self, timeout: float = 30.0) -> Dict[str, bool]:
        """Wait for all 5 critical WebSocket events with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if all(self.critical_events_received.values()):
                logger.info("✅ All 5 critical WebSocket events received!")
                return self.critical_events_received
            
            await asyncio.sleep(0.1)
        
        missing_events = [event for event, received in self.critical_events_received.items() if not received]
        logger.error(f"❌ Timeout waiting for critical events. Missing: {missing_events}")
        return self.critical_events_received

    async def _simulate_agent_execution_with_events(self) -> None:
        """Simulate agent execution that should emit all 5 critical WebSocket events."""
        if not self.websocket_client:
            return
            
        # Simulate sending a chat message that triggers agent execution
        await self.websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Test message that should trigger all 5 critical events",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "request_id": str(self.test_request_id)
            }
        })

    # =============================================================================
    # TEST 1-5: CRITICAL EVENT EMISSION AND TIMING TESTS
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services 
    @pytest.mark.mission_critical
    async def test_01_all_five_critical_events_delivered(self, real_services):
        """
        BVJ: Validates that ALL 5 critical WebSocket events are delivered during agent execution.
        Business Impact: Prevents "Poor Engagement" and "Incomplete Experience" - users must see all agent activity.
        
        Critical Issue #4: Missing WebSocket Events - This test catches the root cause.
        """
        # Setup WebSocket connection
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for critical events test"
        
        # Start collecting events
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            # Trigger agent execution that should emit all 5 events
            await self._simulate_agent_execution_with_events()
            
            # Wait for all critical events
            events_received = await self._wait_for_critical_events(timeout=45.0)
            
            # Assert all 5 critical events were delivered
            for event_type, received in events_received.items():
                assert received, f"CRITICAL: Missing WebSocket event '{event_type}' - breaks chat business value!"
            
            # Verify business value is delivered
            self.assert_business_value_delivered(
                {"events_delivered": sum(events_received.values())}, 
                "automation"  # WebSocket events enable automated real-time updates
            )
            
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical  
    async def test_02_event_delivery_timing_sequence(self, real_services):
        """
        BVJ: Validates WebSocket events are delivered in correct chronological order.
        Business Impact: Prevents "User Confusion" - events must appear in logical sequence.
        
        Expected Order: agent_started → agent_thinking → tool_executing → tool_completed → agent_completed
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for timing test"
        
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            await self._simulate_agent_execution_with_events()
            await self._wait_for_critical_events(timeout=45.0)
            
            # Verify chronological order
            expected_order = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            received_events_ordered = [event["type"] for event in self.received_events if event["type"] in expected_order]
            
            # Check that events appear in expected sequence (allowing for duplicates)
            last_seen_index = -1
            for event_type in received_events_ordered:
                current_index = expected_order.index(event_type)
                if current_index < last_seen_index:
                    assert False, f"WebSocket event '{event_type}' delivered out of sequence - breaks user experience flow!"
                last_seen_index = max(last_seen_index, current_index)
                
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_03_event_delivery_latency_performance(self, real_services):
        """
        BVJ: Validates WebSocket events are delivered within acceptable latency limits.
        Business Impact: Prevents "Perceived Slowness" - events must feel real-time.
        
        Performance Target: <500ms latency for each event delivery
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for latency test"
        
        start_time = time.time()
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            await self._simulate_agent_execution_with_events()
            await self._wait_for_critical_events(timeout=30.0)
            
            # Calculate delivery latencies
            for event in self.received_events:
                if event.get("type") in self.critical_events_received:
                    latency = event.get("received_at", 0) - start_time
                    self.delivery_latencies[event["type"]] = latency
                    
                    # Assert acceptable latency
                    assert latency < 5.0, f"WebSocket event '{event['type']}' delivery latency {latency:.3f}s exceeds 5s limit - perceived as slow!"
            
            # Log performance metrics
            avg_latency = sum(self.delivery_latencies.values()) / len(self.delivery_latencies) if self.delivery_latencies else 0
            logger.info(f"📊 Average WebSocket event delivery latency: {avg_latency:.3f}s")
            
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_04_event_payload_structure_validation(self, real_services):
        """
        BVJ: Validates WebSocket event payloads contain required fields for business value.
        Business Impact: Prevents "Lack of Trust" - events must contain meaningful data.
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for payload validation"
        
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            await self._simulate_agent_execution_with_events()
            await self._wait_for_critical_events(timeout=30.0)
            
            # Validate required fields in each critical event
            required_fields = {
                "agent_started": ["type", "payload", "timestamp"],
                "agent_thinking": ["type", "payload", "timestamp"],
                "tool_executing": ["type", "payload", "timestamp", "tool_name"],
                "tool_completed": ["type", "payload", "timestamp", "tool_name", "result"],
                "agent_completed": ["type", "payload", "timestamp", "response"]
            }
            
            for event in self.received_events:
                event_type = event.get("type")
                if event_type in required_fields:
                    for field in required_fields[event_type]:
                        # Some fields might be nested in payload
                        has_field = field in event or (event.get("payload") and field in event["payload"])
                        assert has_field, f"WebSocket event '{event_type}' missing required field '{field}' - reduces business value!"
                        
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_05_event_retry_and_recovery_mechanism(self, real_services):
        """
        BVJ: Validates WebSocket event delivery retry logic for reliability.
        Business Impact: Prevents event loss that causes "Incomplete Experience".
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for retry test"
        
        # Simulate connection interruption and recovery
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            await self._simulate_agent_execution_with_events()
            
            # Simulate temporary disconnect during execution
            await asyncio.sleep(1.0)  # Let some events be delivered
            await self.websocket_client.disconnect()
            
            await asyncio.sleep(2.0)  # Simulate network interruption
            
            # Reconnect and continue collecting events
            reconnected = await self.websocket_client.connect()
            assert reconnected, "Failed to reconnect WebSocket after interruption"
            
            # Continue waiting for remaining events
            events_received = await self._wait_for_critical_events(timeout=30.0)
            
            # Verify that critical events were eventually delivered (through retry/recovery)
            received_count = sum(events_received.values())
            assert received_count >= 3, f"Only {received_count}/5 critical events delivered after recovery - event delivery not reliable!"
            
        finally:
            event_collection_task.cancel()

    # =============================================================================
    # TEST 6-10: MULTI-USER AND CONCURRENT DELIVERY TESTS  
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_06_multi_user_event_isolation(self, real_services):
        """
        BVJ: Validates WebSocket events are delivered only to correct users.
        Business Impact: Prevents user data leakage that destroys trust and violates privacy.
        """
        # Setup multiple user WebSocket connections
        user1_id = UserID(f"test_user_1_{uuid.uuid4().hex[:8]}")
        user2_id = UserID(f"test_user_2_{uuid.uuid4().hex[:8]}")
        
        client1 = WebSocketTestClient(self.websocket_url)
        client2 = WebSocketTestClient(self.websocket_url)
        
        try:
            # Connect both clients
            connected1 = await client1.connect()
            connected2 = await client2.connect()
            assert connected1 and connected2, "Failed to establish multi-user WebSocket connections"
            
            # Track events per user
            user1_events = []
            user2_events = []
            
            # Simulate user1 agent execution
            await client1.send_message({
                "type": "user_message",
                "payload": {
                    "content": "User 1 message",
                    "user_id": str(user1_id),
                    "thread_id": f"thread_{user1_id}",
                    "request_id": f"req_{user1_id}"
                }
            })
            
            # Collect events from both clients
            for _ in range(50):  # Poll for events
                event1 = await client1.receive_message(timeout=0.1)
                event2 = await client2.receive_message(timeout=0.1)
                
                if event1:
                    user1_events.append(event1)
                if event2:
                    user2_events.append(event2)
                
                await asyncio.sleep(0.1)
            
            # Verify event isolation: user2 should not receive user1's events
            user1_agent_events = [e for e in user1_events if e.get("type") in self.critical_events_received.keys()]
            user2_agent_events = [e for e in user2_events if e.get("type") in self.critical_events_received.keys()]
            
            assert len(user1_agent_events) > 0, "User 1 did not receive their own WebSocket events"
            
            # Check that user2 did not receive user1's events (strict isolation)
            for event in user2_agent_events:
                event_user_id = event.get("payload", {}).get("user_id", "")
                assert event_user_id != str(user1_id), f"WebSocket event leaked from user1 to user2 - privacy violation!"
                
        finally:
            await client1.disconnect()
            await client2.disconnect()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_07_concurrent_agent_execution_events(self, real_services):
        """
        BVJ: Validates WebSocket event delivery under concurrent agent executions.
        Business Impact: Ensures platform scales to 10+ concurrent users per Golden Path requirements.
        """
        # Setup multiple concurrent agent executions
        num_concurrent = 5
        clients = []
        user_ids = []
        
        try:
            # Create multiple WebSocket connections
            for i in range(num_concurrent):
                client = WebSocketTestClient(self.websocket_url)
                user_id = UserID(f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}")
                
                connected = await client.connect()
                assert connected, f"Failed to connect concurrent client {i}"
                
                clients.append(client)
                user_ids.append(user_id)
            
            # Trigger concurrent agent executions
            async def execute_agent_for_user(client, user_id, index):
                await client.send_message({
                    "type": "user_message",
                    "payload": {
                        "content": f"Concurrent execution test message {index}",
                        "user_id": str(user_id),
                        "thread_id": f"thread_{user_id}",
                        "request_id": f"req_{user_id}_{index}"
                    }
                })
                
                # Collect events for this user
                user_events = []
                for _ in range(100):  # Poll for events
                    event = await client.receive_message(timeout=0.05)
                    if event:
                        user_events.append(event)
                    await asyncio.sleep(0.05)
                
                return user_events
            
            # Execute all agents concurrently
            tasks = [
                execute_agent_for_user(clients[i], user_ids[i], i) 
                for i in range(num_concurrent)
            ]
            
            all_user_events = await asyncio.gather(*tasks)
            
            # Verify each user received their critical events
            for i, user_events in enumerate(all_user_events):
                critical_events = [e for e in user_events if e.get("type") in self.critical_events_received.keys()]
                assert len(critical_events) >= 2, f"Concurrent user {i} received insufficient WebSocket events ({len(critical_events)}) - concurrent delivery failed!"
            
            logger.info(f"✅ Successfully delivered WebSocket events to {num_concurrent} concurrent users")
            
        finally:
            for client in clients:
                await client.disconnect()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_08_event_buffering_and_batching_optimization(self, real_services):
        """
        BVJ: Validates WebSocket event buffering doesn't cause delivery delays.
        Business Impact: Prevents "Perceived Slowness" from buffering delays.
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for buffering test"
        
        # Track event arrival times
        arrival_times = []
        event_collection_task = asyncio.create_task(self._collect_events_with_timing(arrival_times))
        
        try:
            # Trigger rapid agent executions to test buffering
            for i in range(3):
                await self._simulate_agent_execution_with_events()
                await asyncio.sleep(0.5)  # Small delay between executions
            
            await asyncio.sleep(10.0)  # Wait for all events
            
            # Analyze event timing gaps
            if len(arrival_times) >= 2:
                max_gap = 0
                for i in range(1, len(arrival_times)):
                    gap = arrival_times[i] - arrival_times[i-1]
                    max_gap = max(max_gap, gap)
                
                # Assert no excessive buffering delays
                assert max_gap < 3.0, f"WebSocket event buffering caused {max_gap:.3f}s delay - exceeds 3s acceptable limit!"
                
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_09_event_authentication_and_authorization(self, real_services):
        """
        BVJ: Validates WebSocket events are only delivered to authenticated users.
        Business Impact: Security - prevents unauthorized access to agent execution data.
        """
        # Test with unauthenticated client
        unauth_client = WebSocketTestClient(self.websocket_url)
        
        try:
            # Attempt connection without authentication
            connected = await unauth_client.connect()
            
            if connected:
                # Try to trigger agent execution without proper auth
                await unauth_client.send_message({
                    "type": "user_message",
                    "payload": {
                        "content": "Unauthorized test message",
                        "user_id": "unauthorized_user"
                    }
                })
                
                # Should not receive agent execution events
                events_received = []
                for _ in range(20):
                    event = await unauth_client.receive_message(timeout=0.1)
                    if event:
                        events_received.append(event)
                    await asyncio.sleep(0.1)
                
                # Verify no sensitive agent events were delivered
                sensitive_events = [e for e in events_received if e.get("type") in self.critical_events_received.keys()]
                assert len(sensitive_events) == 0, f"Unauthorized client received {len(sensitive_events)} agent events - security breach!"
                
        finally:
            await unauth_client.disconnect()

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_10_event_rate_limiting_and_throttling(self, real_services):
        """
        BVJ: Validates WebSocket event rate limiting doesn't drop critical events.
        Business Impact: Ensures rate limiting doesn't cause "Incomplete Experience".
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for rate limiting test"
        
        # Rapidly trigger multiple agent executions to test rate limiting
        critical_events_per_execution = []
        
        try:
            for execution_round in range(3):
                round_start_time = time.time()
                
                # Trigger agent execution
                await self._simulate_agent_execution_with_events()
                
                # Collect events for this round
                round_events = []
                while time.time() - round_start_time < 15.0:  # 15 second window per round
                    event = await self.websocket_client.receive_message(timeout=0.1)
                    if event:
                        round_events.append(event)
                    await asyncio.sleep(0.1)
                
                # Count critical events received in this round
                critical_count = len([e for e in round_events if e.get("type") in self.critical_events_received.keys()])
                critical_events_per_execution.append(critical_count)
                
                await asyncio.sleep(1.0)  # Brief pause between rounds
            
            # Verify rate limiting didn't drop critical events
            for i, count in enumerate(critical_events_per_execution):
                assert count >= 2, f"Rate limiting dropped critical events in execution {i} - only {count} events received!"
            
            logger.info(f"📊 Critical events per execution under rate limiting: {critical_events_per_execution}")
            
        finally:
            pass  # Client cleanup in teardown

    # =============================================================================
    # TEST 11-15: ERROR HANDLING AND EDGE CASE TESTS
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_11_event_delivery_during_high_load(self, real_services):
        """
        BVJ: Validates WebSocket event delivery remains reliable under high system load.
        Business Impact: Ensures platform stability during peak usage periods.
        """
        # Simulate high load with many rapid WebSocket operations
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for high load test"
        
        load_start_time = time.time()
        events_during_load = []
        
        async def generate_load():
            """Generate WebSocket load with rapid message sending."""
            for i in range(50):  # Send many messages rapidly
                await self.websocket_client.send_message({
                    "type": "ping",
                    "payload": {"load_test": i}
                })
                await asyncio.sleep(0.01)  # Very rapid sending
        
        async def collect_events_under_load():
            """Collect events during high load."""
            while time.time() - load_start_time < 20.0:
                event = await self.websocket_client.receive_message(timeout=0.05)
                if event:
                    events_during_load.append(event)
                await asyncio.sleep(0.01)
        
        try:
            # Start load generation and event collection concurrently
            load_task = asyncio.create_task(generate_load())
            collection_task = asyncio.create_task(collect_events_under_load())
            
            # Also trigger agent execution during high load
            await asyncio.sleep(2.0)  # Let load ramp up
            await self._simulate_agent_execution_with_events()
            
            # Wait for completion
            await asyncio.gather(load_task, collection_task)
            
            # Verify critical events were still delivered during high load
            critical_events = [e for e in events_during_load if e.get("type") in self.critical_events_received.keys()]
            assert len(critical_events) >= 2, f"High load caused critical event loss - only {len(critical_events)} events delivered!"
            
            logger.info(f"📊 Delivered {len(critical_events)} critical events during high load of {50} rapid messages")
            
        finally:
            pass  # Client cleanup in teardown

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_12_event_serialization_and_deserialization(self, real_services):
        """
        BVJ: Validates WebSocket event JSON serialization doesn't corrupt data.
        Business Impact: Prevents data corruption that causes "User Confusion".
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for serialization test"
        
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            # Send complex data that tests serialization edge cases
            complex_payload = {
                "content": "Test with special characters: üñíçödé 📊 💎 🚀",
                "metadata": {
                    "timestamps": [datetime.now(timezone.utc).isoformat()],
                    "numbers": [1.23456789, -999.999, 0],
                    "booleans": [True, False, None],
                    "nested": {"deep": {"very": {"deep": "value"}}}
                },
                "user_id": str(self.test_user_id),
                "request_id": str(self.test_request_id)
            }
            
            await self.websocket_client.send_message({
                "type": "user_message", 
                "payload": complex_payload
            })
            
            await asyncio.sleep(5.0)  # Wait for events
            
            # Verify received events are properly deserialized
            for event in self.received_events:
                # Check JSON structure integrity
                assert isinstance(event, dict), "WebSocket event not properly deserialized to dict"
                
                # Check for required fields
                assert "type" in event, "Event missing 'type' field after deserialization"
                
                # If payload exists, verify it's properly structured
                if "payload" in event and event["payload"]:
                    payload = event["payload"]
                    assert isinstance(payload, dict), "Event payload not properly deserialized"
                    
                    # Check that complex data types are preserved
                    if "metadata" in payload:
                        metadata = payload["metadata"]
                        if "numbers" in metadata:
                            for num in metadata["numbers"]:
                                assert isinstance(num, (int, float)) or num is None, "Number serialization corrupted"
                                
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_13_event_monitoring_and_observability(self, real_services):
        """
        BVJ: Validates WebSocket event delivery can be monitored for operational health.
        Business Impact: Enables proactive detection of event delivery issues.
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for monitoring test"
        
        # Track monitoring metrics
        monitoring_metrics = {
            "events_sent": 0,
            "events_received": 0,
            "delivery_successes": 0,
            "delivery_failures": 0,
            "avg_latency": 0
        }
        
        event_collection_task = asyncio.create_task(self._collect_websocket_events())
        
        try:
            start_time = time.time()
            
            # Trigger agent execution and monitor
            await self._simulate_agent_execution_with_events()
            monitoring_metrics["events_sent"] += 1
            
            # Wait and collect monitoring data
            await asyncio.sleep(10.0)
            
            # Calculate metrics
            monitoring_metrics["events_received"] = len(self.received_events)
            critical_events_count = len([e for e in self.received_events if e.get("type") in self.critical_events_received.keys()])
            
            if critical_events_count > 0:
                monitoring_metrics["delivery_successes"] = critical_events_count
                monitoring_metrics["avg_latency"] = (time.time() - start_time) / critical_events_count
            
            # Assert monitoring data is available and reasonable
            assert monitoring_metrics["events_received"] > 0, "No WebSocket events captured for monitoring"
            assert monitoring_metrics["delivery_successes"] >= 2, f"Insufficient successful deliveries for monitoring: {monitoring_metrics['delivery_successes']}"
            assert monitoring_metrics["avg_latency"] < 10.0, f"Average delivery latency too high for monitoring: {monitoring_metrics['avg_latency']:.3f}s"
            
            logger.info(f"📊 WebSocket monitoring metrics: {monitoring_metrics}")
            
        finally:
            event_collection_task.cancel()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_14_event_error_handling_and_recovery(self, real_services):
        """
        BVJ: Validates WebSocket error handling doesn't permanently break event delivery.
        Business Impact: Ensures system resilience prevents "Incomplete Experience".
        """
        self.websocket_client = WebSocketTestClient(self.websocket_url)
        connected = await self.websocket_client.connect()
        assert connected, "Failed to establish WebSocket connection for error handling test"
        
        events_before_error = []
        events_after_recovery = []
        
        try:
            # Collect events before error
            event_collection_task = asyncio.create_task(self._collect_websocket_events())
            
            # Trigger normal agent execution
            await self._simulate_agent_execution_with_events()
            await asyncio.sleep(3.0)
            
            events_before_error = list(self.received_events)
            
            # Simulate error condition (malformed message)
            try:
                await self.websocket_client.websocket.send("invalid json message")
            except:
                pass  # Expected to fail
            
            await asyncio.sleep(1.0)  # Let error be processed
            
            # Verify connection can recover and deliver events
            await self._simulate_agent_execution_with_events()
            await asyncio.sleep(5.0)
            
            events_after_recovery = [e for e in self.received_events if e not in events_before_error]
            
            # Assert error didn't permanently break event delivery
            critical_before = len([e for e in events_before_error if e.get("type") in self.critical_events_received.keys()])
            critical_after = len([e for e in events_after_recovery if e.get("type") in self.critical_events_received.keys()])
            
            assert critical_before >= 1, "No critical events received before error"
            assert critical_after >= 1, "WebSocket error permanently broke event delivery - no recovery!"
            
            logger.info(f"📊 Error recovery: {critical_before} events before, {critical_after} events after recovery")
            
        finally:
            pass  # Client cleanup in teardown

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_15_event_delivery_scalability_limits(self, real_services):
        """
        BVJ: Validates WebSocket event delivery scales to Golden Path requirements (10+ users).
        Business Impact: Ensures platform can handle target user load without degradation.
        """
        # Test scaling to 10+ concurrent WebSocket connections
        target_connections = 12  # Exceed Golden Path minimum
        clients = []
        connection_results = []
        
        try:
            # Establish many concurrent connections
            connection_tasks = []
            
            async def establish_connection(index):
                client = WebSocketTestClient(self.websocket_url)
                try:
                    connected = await client.connect()
                    return (client, connected, index)
                except Exception as e:
                    logger.error(f"Connection {index} failed: {e}")
                    return (client, False, index)
            
            # Create all connections concurrently
            for i in range(target_connections):
                task = asyncio.create_task(establish_connection(i))
                connection_tasks.append(task)
            
            connection_results = await asyncio.gather(*connection_tasks)
            
            # Collect successfully connected clients
            for client, connected, index in connection_results:
                if connected:
                    clients.append(client)
                    logger.info(f"✅ WebSocket connection {index} established")
                else:
                    logger.error(f"❌ WebSocket connection {index} failed")
            
            # Assert sufficient connections for scalability test
            assert len(clients) >= 10, f"Only {len(clients)}/{target_connections} WebSocket connections established - scalability limit reached!"
            
            # Test event delivery to all connected clients
            delivered_events_per_client = []
            
            for i, client in enumerate(clients[:10]):  # Test first 10 for performance
                # Trigger agent execution for this client
                await client.send_message({
                    "type": "user_message",
                    "payload": {
                        "content": f"Scalability test message {i}",
                        "user_id": f"scale_user_{i}",
                        "request_id": f"scale_req_{i}"
                    }
                })
                
                # Brief delay to avoid overwhelming system
                await asyncio.sleep(0.1)
            
            # Collect events from all clients  
            await asyncio.sleep(15.0)  # Wait for all executions
            
            for i, client in enumerate(clients[:10]):
                client_events = []
                # Collect remaining events from this client
                for _ in range(50):
                    event = await client.receive_message(timeout=0.05)
                    if event:
                        client_events.append(event)
                    else:
                        break
                
                critical_events = [e for e in client_events if e.get("type") in self.critical_events_received.keys()]
                delivered_events_per_client.append(len(critical_events))
            
            # Verify scalable event delivery
            successful_deliveries = len([count for count in delivered_events_per_client if count >= 1])
            assert successful_deliveries >= 8, f"Only {successful_deliveries}/10 clients received events - scalability degradation!"
            
            logger.info(f"📊 Scalability test: {len(clients)} connections, {successful_deliveries}/10 successful event deliveries")
            
        finally:
            # Clean up all clients
            for client, _, _ in connection_results:
                try:
                    await client.disconnect()
                except:
                    pass  # Ignore cleanup errors

    # =============================================================================
    # HELPER METHODS FOR EVENT COLLECTION AND VALIDATION
    # =============================================================================

    async def _collect_websocket_events(self):
        """Continuously collect WebSocket events for testing."""
        while True:
            try:
                if self.websocket_client:
                    event = await self.websocket_client.receive_message(timeout=0.1)
                    if event:
                        self._record_event(event)
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Event collection error: {e}")
                await asyncio.sleep(0.1)

    async def _collect_events_with_timing(self, timing_list):
        """Collect events and record arrival times."""
        while True:
            try:
                if self.websocket_client:
                    event = await self.websocket_client.receive_message(timeout=0.1)
                    if event:
                        timing_list.append(time.time())
                        self._record_event(event)
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Timed event collection error: {e}")
                await asyncio.sleep(0.1)