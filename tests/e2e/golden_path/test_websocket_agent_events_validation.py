"""
WebSocket Agent Events Validation - Supporting Test for Golden Path

This test validates the critical WebSocket agent events infrastructure that enables
the golden path business value delivery. It focuses specifically on the 5 mandatory
WebSocket events that provide real-time visibility into agent execution.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time chat visibility works (enables user engagement)
- Value Impact: Users see agent progress, building trust and reducing abandonment
- Strategic Impact: Foundation for golden path user experience

CRITICAL WEBSOCKET EVENTS (per CLAUDE.md Section 6):
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)  
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

This test ensures these events are delivered correctly and in proper sequence.
"""

import asyncio
import json
import pytest  
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock

# SSOT IMPORTS
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestHelpers, assert_websocket_events

# System imports
from shared.id_generation.unified_id_generator import UnifiedIdGenerator, generate_uuid_replacement
from shared.types.core_types import UserID, ThreadID, RunID


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
class TestWebSocketAgentEventsValidation(SSotAsyncTestCase):
    """
    Validates the 5 critical WebSocket agent events that enable golden path user experience.
    
    These events are the foundation of chat-based business value delivery.
    """
    
    def setup_method(self, method=None):
        """Setup with WebSocket event focus."""
        super().setup_method(method)
        
        # Event-focused metrics
        self.record_metric("target_event_types", 5)
        self.record_metric("event_system", "websocket_agent_notifications")
        
        self._websocket_connection = None
        
    async def async_setup_method(self, method=None):
        """Async setup for WebSocket testing."""
        await super().async_setup_method(method)
        
        # Initialize helpers
        self._auth_helper = E2EAuthHelper(environment=self.get_env_var("TEST_ENV", "test"))
        self._websocket_helper = E2EWebSocketAuthHelper(environment=self.get_env_var("TEST_ENV", "test"))
        
    async def async_teardown_method(self, method=None):
        """Cleanup WebSocket connections."""
        if self._websocket_connection:
            try:
                await WebSocketTestHelpers.close_test_connection(self._websocket_connection)
            except:
                pass
        await super().async_teardown_method(method)

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    @pytest.mark.asyncio
    async def test_all_five_critical_websocket_events_delivered(self, real_services_fixture):
        """
        CRITICAL: Validate all 5 mandatory WebSocket events are delivered in proper sequence.
        
        This test ensures the event infrastructure that enables golden path user visibility
        works correctly. Without these events, users cannot see agent progress.
        
        REQUIRED EVENTS (per CLAUDE.md Section 6.1):
        1. agent_started - User sees agent began processing  
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results display
        5. agent_completed - User knows when response ready
        """
        # === AUTHENTICATION & CONNECTION ===
        user_id = f"event_test_{generate_uuid_replacement()}"
        jwt_token = self._auth_helper.create_test_jwt_token(user_id=user_id)
        
        ws_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        self._websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=ws_headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # === SEND AGENT EXECUTION REQUEST ===
        test_message = {
            "type": "chat_message",
            "content": "Test agent execution with event validation",
            "user_id": user_id,
            "timestamp": time.time(),
            "test_context": "websocket_events_validation"
        }
        
        await WebSocketTestHelpers.send_test_message(self._websocket_connection, test_message)
        
        # === COLLECT WEBSOCKET EVENTS ===
        collected_events = []
        required_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Allow up to 30 seconds for agent execution with events
        max_wait_time = 30.0
        event_timeout = 3.0
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait_time:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    self._websocket_connection,
                    timeout=event_timeout
                )
                
                collected_events.append(event)
                self.increment_websocket_events(1)
                
                # Check if we have all required events
                received_types = [e.get("type") for e in collected_events]
                if all(req_type in received_types for req_type in required_event_types):
                    break
                    
            except Exception as e:
                # If we've been waiting a while and still don't have events, fail
                if (time.time() - start_time) > max_wait_time - 5:
                    break
        
        # === VALIDATE ALL 5 CRITICAL EVENTS ===
        received_types = [e.get("type") for e in collected_events]
        
        assert len(collected_events) >= 5, (
            f"Expected at least 5 WebSocket events, received {len(collected_events)}: {received_types}"
        )
        
        # Use SSOT assertion helper
        assert_websocket_events(collected_events, required_event_types)
        
        # Validate event structure and content
        for event in collected_events:
            assert isinstance(event, dict), f"Event must be dict, got {type(event)}"
            assert "type" in event, f"Event missing 'type' field: {event}"
            assert "timestamp" in event, f"Event missing 'timestamp' field: {event}"
            
            # Validate specific event types
            event_type = event.get("type")
            if event_type == "agent_started":
                assert "agent_name" in event, f"agent_started event missing agent_name: {event}"
            elif event_type == "agent_thinking":
                assert "reasoning" in event or "thinking" in event, f"agent_thinking event missing reasoning: {event}"
            elif event_type == "tool_executing":
                assert "tool_name" in event, f"tool_executing event missing tool_name: {event}"
            elif event_type == "tool_completed":
                assert "tool_name" in event, f"tool_completed event missing tool_name: {event}"
            elif event_type == "agent_completed":
                assert "final_response" in event or "result" in event, f"agent_completed missing final_response: {event}"
        
        # === VALIDATE EVENT SEQUENCE ===
        # Events should generally follow the expected order
        agent_started_indices = [i for i, e in enumerate(collected_events) if e.get("type") == "agent_started"]
        agent_completed_indices = [i for i, e in enumerate(collected_events) if e.get("type") == "agent_completed"]
        
        if agent_started_indices and agent_completed_indices:
            # At least one agent_started should come before agent_completed
            earliest_start = min(agent_started_indices)
            latest_complete = max(agent_completed_indices)
            assert earliest_start < latest_complete, "agent_started should come before agent_completed"
        
        # === RECORD SUCCESS METRICS ===
        self.record_metric("events_received", len(collected_events))
        self.record_metric("all_required_events_present", True)
        self.record_metric("event_delivery_success", True)
        
        unique_event_types = set(received_types)
        self.record_metric("unique_event_types", len(unique_event_types))
        
        print(f"\n✅ WEBSOCKET EVENTS VALIDATION SUCCESS:")
        print(f"   📊 Total events received: {len(collected_events)}")
        print(f"   📡 Event types: {unique_event_types}")
        print(f"   ✅ All 5 critical events present: {all(et in received_types for et in required_event_types)}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_event_timing_and_performance(self, real_services_fixture):
        """
        Validate WebSocket event delivery timing and performance characteristics.
        
        Events must be delivered promptly to maintain good user experience.
        """
        # === SETUP AND CONNECTION ===
        user_id = f"timing_test_{generate_uuid_replacement()}"
        jwt_token = self._auth_helper.create_test_jwt_token(user_id=user_id)
        ws_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        self._websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=ws_headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # === SEND MESSAGE AND TRACK TIMING ===
        start_time = time.time()
        
        test_message = {
            "type": "chat_message", 
            "content": "Performance test for event timing",
            "user_id": user_id,
            "timestamp": start_time
        }
        
        await WebSocketTestHelpers.send_test_message(self._websocket_connection, test_message)
        
        # === COLLECT EVENTS WITH TIMING ===
        events_with_timing = []
        first_event_time = None
        
        for _ in range(10):  # Collect up to 10 events
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    self._websocket_connection,
                    timeout=2.0
                )
                
                receive_time = time.time()
                if first_event_time is None:
                    first_event_time = receive_time
                
                events_with_timing.append({
                    "event": event,
                    "receive_time": receive_time,
                    "time_since_start": receive_time - start_time,
                    "time_since_first": receive_time - first_event_time if first_event_time else 0
                })
                
            except:
                break
        
        # === VALIDATE TIMING REQUIREMENTS ===
        assert len(events_with_timing) >= 3, f"Expected at least 3 events for timing test, got {len(events_with_timing)}"
        
        # First event should arrive quickly (within 5 seconds of request)
        first_event_delay = events_with_timing[0]["time_since_start"]
        assert first_event_delay < 5.0, f"First event took {first_event_delay:.2f}s (max: 5s)"
        
        # Events should arrive at reasonable intervals (not all at once, not too slow)
        if len(events_with_timing) >= 2:
            intervals = []
            for i in range(1, len(events_with_timing)):
                interval = events_with_timing[i]["time_since_first"] - events_with_timing[i-1]["time_since_first"]
                intervals.append(interval)
            
            # Most intervals should be reasonable (0.1s to 10s)
            reasonable_intervals = [i for i in intervals if 0.1 <= i <= 10.0]
            assert len(reasonable_intervals) >= len(intervals) * 0.7, \
                f"Too many unreasonable event intervals: {intervals}"
        
        # === RECORD PERFORMANCE METRICS ===
        self.record_metric("first_event_delay_seconds", first_event_delay)
        self.record_metric("total_events_for_timing", len(events_with_timing))
        self.record_metric("event_timing_validated", True)
        
        print(f"\n✅ EVENT TIMING VALIDATION SUCCESS:")
        print(f"   ⏱️ First event delay: {first_event_delay:.2f}s")
        print(f"   📊 Total events tracked: {len(events_with_timing)}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_event_error_handling(self, real_services_fixture):
        """
        Test WebSocket event delivery under error conditions.
        
        Even when agents encounter errors, users should receive appropriate event notifications.
        """
        # === SETUP CONNECTION ===
        user_id = f"error_test_{generate_uuid_replacement()}"
        jwt_token = self._auth_helper.create_test_jwt_token(user_id=user_id)
        ws_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        self._websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=ws_headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # === SEND MESSAGE THAT MIGHT TRIGGER ERROR CONDITIONS ===
        error_test_message = {
            "type": "chat_message",
            "content": "Test error handling with intentionally problematic input: #ERROR_TEST#",
            "user_id": user_id,
            "timestamp": time.time(),
            "test_scenario": "error_handling"
        }
        
        await WebSocketTestHelpers.send_test_message(self._websocket_connection, error_test_message)
        
        # === COLLECT EVENTS INCLUDING ERROR EVENTS ===
        all_events = []
        
        for _ in range(8):  # Collect events, may include error events
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    self._websocket_connection,
                    timeout=3.0
                )
                all_events.append(event)
                
            except:
                break
        
        # === VALIDATE ERROR HANDLING ===
        assert len(all_events) >= 1, "Should receive at least one event even in error scenarios"
        
        # Check for error events
        error_events = [e for e in all_events if e.get("type") == "error"]
        normal_events = [e for e in all_events if e.get("type") != "error"]
        
        # Either we get normal events (system handled the error) or error events (graceful failure)
        assert len(normal_events) >= 1 or len(error_events) >= 1, \
            "Should receive either normal events or error events"
        
        # If error events exist, they should be well-formed
        for error_event in error_events:
            assert "error" in error_event or "message" in error_event, \
                f"Error event should have error/message field: {error_event}"
        
        # === RECORD ERROR HANDLING METRICS ===
        self.record_metric("total_events_in_error_test", len(all_events))
        self.record_metric("error_events_received", len(error_events))
        self.record_metric("normal_events_received", len(normal_events))
        self.record_metric("error_handling_validated", True)
        
        print(f"\n✅ ERROR HANDLING VALIDATION SUCCESS:")
        print(f"   📊 Total events: {len(all_events)}")
        print(f"   ❌ Error events: {len(error_events)}")
        print(f"   ✅ Normal events: {len(normal_events)}")