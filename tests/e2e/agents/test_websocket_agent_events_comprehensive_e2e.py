#!/usr/bin/env python
"""
WebSocket Agent Events Comprehensive E2E Tests

Business Value Justification (BVJ):
- Segment: All tiers - Critical for 90% of platform value (real-time chat experience)
- Business Goal: Ensure reliable real-time agent event delivery for user engagement
- Value Impact: Users see live agent progress - core differentiator of AI platform
- Strategic/Revenue Impact: $500K+ ARR depends on real-time agent transparency

This test suite validates comprehensive WebSocket agent event delivery:
1. All 5 required agent events delivered in sequence
2. Real-time event timing and order validation
3. Event content accuracy and user-specific data
4. Event delivery under concurrent load
5. Event recovery and error handling
6. Cross-browser and connection resilience

CRITICAL E2E REQUIREMENTS:
- Real GCP staging environment (NO Docker)
- Authenticated WebSocket connections with JWT
- All 5 agent events validated: started, thinking, tool_executing, tool_completed, completed
- Real-time delivery monitoring with precise timing
- Event payload validation and user isolation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
import pytest
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import E2E auth helper for SSOT authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper,
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config

logger = logging.getLogger(__name__)


class TestWebSocketAgentEventsE2E(BaseE2ETest):
    """
    Comprehensive WebSocket Agent Events E2E Tests for GCP Staging.

    Tests critical real-time event delivery that provides 90% of platform value
    through transparent AI agent progress visualization.
    """

    @pytest.fixture(autouse=True)
    async def setup_websocket_event_environment(self):
        """Set up WebSocket event testing environment with real-time monitoring."""
        await self.initialize_test_environment()

        # Configure for GCP staging environment
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")

        # Validate staging configuration
        assert self.staging_config.validate_configuration(), "Staging configuration invalid"

        # Create authenticated test users for event testing
        self.test_users = []
        for i in range(3):  # 3 users for event delivery validation
            user_context = await create_authenticated_user_context(
                user_email=f"websocket_event_test_{i}_{int(time.time())}@staging.netra.ai",
                environment="staging",
                permissions=["read", "write", "execute_agents", "websocket_events"]
            )
            self.test_users.append(user_context)

        # Event tracking infrastructure
        self.collected_events = {}
        self.event_timings = {}
        self.event_sequence_validation = {}

        for user in self.test_users:
            self.collected_events[user.user_id] = []
            self.event_timings[user.user_id] = {}
            self.event_sequence_validation[user.user_id] = {
                "expected_sequence": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                "received_sequence": [],
                "timing_gaps": [],
                "payload_validation": {}
            }

        self.logger.info(f"✅ PASS: WebSocket event test environment ready - {len(self.test_users)} users authenticated")

    async def test_complete_agent_event_sequence_validation(self):
        """
        Test complete agent event sequence with precise validation.

        BVJ: Validates $500K+ ARR core value - Users must see all agent progress
        Ensures: All 5 required events delivered in correct order with valid content
        """
        user_context = self.test_users[0]

        # Connect authenticated WebSocket with event monitoring
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))

        # Event collection with detailed validation
        collected_events = []
        event_sequence = []
        event_payloads = {}
        sequence_complete = False

        async def monitor_complete_event_sequence():
            """Monitor and validate complete agent event sequence."""
            nonlocal sequence_complete
            try:
                event_start_time = time.time()

                async for message in websocket:
                    receive_time = time.time()
                    event = json.loads(message)

                    event_type = event.get("type")
                    event_data = event.get("data", {})

                    # Store complete event with timing
                    event_record = {
                        **event,
                        "received_at": receive_time,
                        "sequence_position": len(collected_events) + 1,
                        "time_since_start": receive_time - event_start_time
                    }

                    collected_events.append(event_record)
                    event_sequence.append(event_type)
                    event_payloads[event_type] = event_data

                    self.logger.info(f"📡 Event {len(collected_events)}: {event_type} "
                                   f"({receive_time - event_start_time:.3f}s since start)")

                    # Validate event content based on type
                    self._validate_event_content(event_type, event_data, user_context)

                    if event_type == "agent_completed":
                        sequence_complete = True
                        break

            except Exception as e:
                self.logger.error(f"Event sequence monitoring error: {e}")

        event_task = asyncio.create_task(monitor_complete_event_sequence())

        # Send comprehensive agent request to trigger all events
        complete_request = {
            "type": "execute_agent",
            "agent_type": "comprehensive_event_test",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "event_sequence_validation": True,
                "require_all_events": True,
                "tool_execution_required": True,
                "thinking_updates_required": True,
                "completion_validation": True,
                "event_timing_test": True
            }
        }

        start_time = time.time()
        await websocket.send(json.dumps(complete_request))

        # Wait for complete event sequence
        try:
            await asyncio.wait_for(event_task, timeout=60.0)
        except asyncio.TimeoutError:
            pytest.fail(f"Complete event sequence timed out - only received {len(collected_events)} events")

        total_duration = time.time() - start_time

        # CRITICAL VALIDATION: All 5 required events present
        assert sequence_complete, "Agent never completed - missing agent_completed event"
        assert len(collected_events) >= 5, f"Expected at least 5 events, got {len(collected_events)}"

        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]

        # Validate all required events are present
        for required_event in expected_sequence:
            assert required_event in event_sequence, f"Missing required event: {required_event}"

        # Validate event sequence order (allowing for multiple thinking events)
        sequence_positions = {}
        for event_type in expected_sequence:
            # Find first occurrence of each required event type
            for i, received_event in enumerate(event_sequence):
                if received_event == event_type:
                    sequence_positions[event_type] = i
                    break

        # Verify logical order
        assert sequence_positions["agent_started"] < sequence_positions["agent_thinking"], "agent_started must come before agent_thinking"
        assert sequence_positions["agent_thinking"] < sequence_positions["tool_executing"], "agent_thinking must come before tool_executing"
        assert sequence_positions["tool_executing"] < sequence_positions["tool_completed"], "tool_executing must come before tool_completed"
        assert sequence_positions["tool_completed"] < sequence_positions["agent_completed"], "tool_completed must come before agent_completed"

        # Validate event timing - events should be spread over time
        event_times = [event["received_at"] for event in collected_events]
        time_spread = max(event_times) - min(event_times)
        assert time_spread >= 2.0, f"Events too clustered in time: {time_spread:.3f}s (expected >= 2s for realistic execution)"

        # Validate event content completeness
        agent_started_data = event_payloads.get("agent_started", {})
        assert "agent_name" in agent_started_data or "status" in agent_started_data, "agent_started missing essential data"

        thinking_data = event_payloads.get("agent_thinking", {})
        assert "reasoning" in thinking_data or "message" in thinking_data, "agent_thinking missing reasoning content"

        tool_executing_data = event_payloads.get("tool_executing", {})
        assert "tool_name" in tool_executing_data or "tool" in tool_executing_data, "tool_executing missing tool identification"

        tool_completed_data = event_payloads.get("tool_completed", {})
        assert "result" in tool_completed_data or "output" in tool_completed_data, "tool_completed missing result data"

        agent_completed_data = event_payloads.get("agent_completed", {})
        assert "status" in agent_completed_data or "result" in agent_completed_data, "agent_completed missing completion data"

        self.logger.info(f"✅ PASS: Complete agent event sequence validated successfully")
        self.logger.info(f"📊 Total events: {len(collected_events)}")
        self.logger.info(f"⏱️ Total duration: {total_duration:.3f}s")
        self.logger.info(f"📋 Event sequence: {' → '.join(event_sequence[:10])}")  # First 10 events

    async def test_real_time_event_timing_validation(self):
        """
        Test real-time event delivery timing and responsiveness.

        BVJ: Validates $200K+ MRR user experience - Events must feel real-time
        Ensures: Events delivered within milliseconds, proper timing distribution
        """
        user_context = self.test_users[0]

        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))

        # Precise timing collection
        event_timestamps = []
        inter_event_delays = []
        first_event_time = None

        async def monitor_event_timing():
            """Monitor precise event timing for real-time validation."""
            nonlocal first_event_time
            previous_event_time = None

            try:
                async for message in websocket:
                    receive_time = time.time()
                    event = json.loads(message)
                    event_type = event.get("type")

                    if first_event_time is None:
                        first_event_time = receive_time

                    event_timestamps.append({
                        "type": event_type,
                        "timestamp": receive_time,
                        "time_since_start": receive_time - first_event_time
                    })

                    # Calculate delay between events
                    if previous_event_time is not None:
                        delay = receive_time - previous_event_time
                        inter_event_delays.append(delay)

                    previous_event_time = receive_time

                    if event_type == "agent_completed":
                        break

            except Exception as e:
                self.logger.error(f"Event timing monitoring error: {e}")

        timing_task = asyncio.create_task(monitor_event_timing())

        # Send real-time timing test request
        timing_request = {
            "type": "execute_agent",
            "agent_type": "realtime_timing_test",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "realtime_events": True,
                "event_timing_test": True,
                "immediate_responses": True,
                "timing_validation": True
            }
        }

        request_start = time.time()
        await websocket.send(json.dumps(timing_request))

        # Wait for timing test completion
        try:
            await asyncio.wait_for(timing_task, timeout=30.0)
        except asyncio.TimeoutError:
            pytest.fail("Real-time timing test timed out")

        # Validate timing metrics
        assert len(event_timestamps) >= 5, f"Insufficient events for timing test: {len(event_timestamps)}"
        assert first_event_time is not None, "No events received for timing validation"

        # First event should arrive quickly (within 2 seconds of request)
        first_event_delay = first_event_time - request_start
        assert first_event_delay < 2.0, f"First event too slow: {first_event_delay:.3f}s (expected < 2s)"

        # Events should be reasonably spaced (not all instantaneous, not too slow)
        if len(inter_event_delays) >= 2:
            avg_inter_event_delay = sum(inter_event_delays) / len(inter_event_delays)
            max_inter_event_delay = max(inter_event_delays)

            # Average delay should be reasonable for real-time feel
            assert avg_inter_event_delay < 5.0, f"Events too slow on average: {avg_inter_event_delay:.3f}s"
            assert max_inter_event_delay < 15.0, f"Maximum event gap too large: {max_inter_event_delay:.3f}s"

        # Events should show progressive execution (not all bunched at start or end)
        total_execution_time = event_timestamps[-1]["timestamp"] - event_timestamps[0]["timestamp"]
        assert total_execution_time >= 3.0, f"Execution too fast - likely mocked: {total_execution_time:.3f}s"
        assert total_execution_time <= 45.0, f"Execution too slow: {total_execution_time:.3f}s"

        # Validate event distribution over time
        time_quartiles = [total_execution_time * 0.25, total_execution_time * 0.5, total_execution_time * 0.75]
        events_in_quartiles = [0, 0, 0, 0]  # Q1, Q2, Q3, Q4

        for event in event_timestamps:
            event_time = event["time_since_start"]
            if event_time <= time_quartiles[0]:
                events_in_quartiles[0] += 1
            elif event_time <= time_quartiles[1]:
                events_in_quartiles[1] += 1
            elif event_time <= time_quartiles[2]:
                events_in_quartiles[2] += 1
            else:
                events_in_quartiles[3] += 1

        # Events should be distributed across time (not all in one quartile)
        max_quartile_events = max(events_in_quartiles)
        total_events = len(event_timestamps)
        assert max_quartile_events < total_events * 0.8, f"Events too concentrated in time: {events_in_quartiles}"

        self.logger.info(f"✅ PASS: Real-time event timing validated successfully")
        self.logger.info(f"⚡ First event delay: {first_event_delay:.3f}s")
        self.logger.info(f"📊 Average inter-event delay: {sum(inter_event_delays)/len(inter_event_delays):.3f}s")
        self.logger.info(f"⏱️ Total execution time: {total_execution_time:.3f}s")
        self.logger.info(f"📈 Event distribution: Q1:{events_in_quartiles[0]} Q2:{events_in_quartiles[1]} Q3:{events_in_quartiles[2]} Q4:{events_in_quartiles[3]}")

    async def test_concurrent_websocket_event_delivery(self):
        """
        Test concurrent WebSocket event delivery with load validation.

        BVJ: Validates $300K+ MRR scalability - Multiple users need reliable events
        Ensures: Event delivery remains reliable under concurrent load
        """
        # Use all test users for concurrent load testing
        concurrent_results = []

        async def run_concurrent_event_test(user_context, user_index):
            """Run WebSocket event test for specific user under load."""
            try:
                # Create isolated WebSocket connection for each user
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)

                # Track events for this user
                user_events = []
                event_complete = False

                async def collect_user_events():
                    nonlocal event_complete
                    async for message in websocket:
                        event = json.loads(message)
                        event_type = event.get("type")

                        user_events.append({
                            **event,
                            "user_index": user_index,
                            "user_id": user_context.user_id,
                            "received_at": time.time()
                        })

                        if event_type == "agent_completed":
                            event_complete = True
                            break

                event_task = asyncio.create_task(collect_user_events())

                # Send concurrent load test request
                load_request = {
                    "type": "execute_agent",
                    "agent_type": "concurrent_event_load_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "user_index": user_index,
                        "concurrent_load_test": True,
                        "event_validation": True,
                        "stress_test": True
                    }
                }

                start_time = time.time()
                await websocket.send(json.dumps(load_request))

                # Wait for event completion
                await asyncio.wait_for(event_task, timeout=45.0)
                execution_duration = time.time() - start_time

                await websocket.close()

                # Validate events received under load
                required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
                received_event_types = [e.get("type") for e in user_events]

                missing_events = [event for event in required_events if event not in received_event_types]

                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": True,
                    "event_complete": event_complete,
                    "events_received": len(user_events),
                    "missing_events": missing_events,
                    "execution_duration": execution_duration,
                    "all_required_events": len(missing_events) == 0
                }

            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": False,
                    "error": str(e)
                }

        # Execute concurrent event tests
        tasks = [
            run_concurrent_event_test(user_context, i)
            for i, user_context in enumerate(self.test_users)
        ]

        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate concurrent event delivery
        successful_users = 0
        total_events = 0
        users_with_all_events = 0

        for result in concurrent_results:
            if isinstance(result, dict) and result.get("success"):
                successful_users += 1
                events_received = result.get("events_received", 0)
                total_events += events_received

                # Validate each user received all required events
                if result.get("all_required_events"):
                    users_with_all_events += 1

                # Validate reasonable execution time under load
                duration = result.get("execution_duration", 0)
                assert duration < 60.0, f"User {result['user_index']} took too long under load: {duration:.2f}s"

                # Validate sufficient events received
                assert events_received >= 5, f"User {result['user_index']} received insufficient events: {events_received}"

        # Critical validation: All users should succeed under load
        assert successful_users == len(self.test_users), f"Expected {len(self.test_users)} successful users, got {successful_users}"
        assert users_with_all_events == len(self.test_users), f"Expected {len(self.test_users)} users with all events, got {users_with_all_events}"

        # Validate total event throughput
        expected_min_events = len(self.test_users) * 5  # 5 events per user minimum
        assert total_events >= expected_min_events, f"Expected at least {expected_min_events} total events, got {total_events}"

        self.logger.info(f"✅ PASS: Concurrent WebSocket event delivery validated")
        self.logger.info(f"👥 Concurrent users: {successful_users}")
        self.logger.info(f"📊 Total events delivered: {total_events}")
        self.logger.info(f"🎯 Users with all events: {users_with_all_events}")

    async def test_event_payload_accuracy_validation(self):
        """
        Test WebSocket event payload accuracy and user-specific content.

        BVJ: Validates $150K+ MRR data accuracy - Events must contain correct user data
        Ensures: Event payloads are accurate, complete, and user-specific
        """
        user_context = self.test_users[0]

        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))

        # Detailed payload collection
        event_payloads = {}
        payload_validation_results = {}

        async def collect_detailed_payloads():
            """Collect and validate detailed event payloads."""
            try:
                async for message in websocket:
                    event = json.loads(message)
                    event_type = event.get("type")
                    event_data = event.get("data", {})

                    event_payloads[event_type] = event_data

                    # Validate payload structure based on event type
                    validation_result = self._validate_event_payload_structure(event_type, event_data, user_context)
                    payload_validation_results[event_type] = validation_result

                    if event_type == "agent_completed":
                        break

            except Exception as e:
                self.logger.error(f"Payload collection error: {e}")

        payload_task = asyncio.create_task(collect_detailed_payloads())

        # Send payload accuracy test request with specific user data
        user_specific_data = {
            "user_name": f"Test User {user_context.user_id[:8]}",
            "user_preference": "detailed_analysis",
            "user_context": f"payload_test_session_{int(time.time())}",
            "expected_outcomes": ["cost_analysis", "optimization_recommendations", "risk_assessment"]
        }

        payload_request = {
            "type": "execute_agent",
            "agent_type": "payload_accuracy_test",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "payload_validation": True,
                "user_specific_data": user_specific_data,
                "accuracy_test": True,
                "detailed_payloads": True
            }
        }

        await websocket.send(json.dumps(payload_request))

        # Wait for payload collection
        try:
            await asyncio.wait_for(payload_task, timeout=45.0)
        except asyncio.TimeoutError:
            pytest.fail("Payload accuracy test timed out")

        # Validate payload accuracy
        assert len(event_payloads) >= 5, f"Expected payloads for at least 5 events, got {len(event_payloads)}"

        # Validate each required event has valid payload
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]

        for event_type in required_events:
            assert event_type in event_payloads, f"Missing payload for {event_type}"

            validation = payload_validation_results.get(event_type, {})
            assert validation.get("valid", False), f"Invalid payload structure for {event_type}: {validation.get('issues', [])}"

        # Validate user-specific data appears in relevant events
        user_data_found = False
        user_context_found = False

        for event_type, payload in event_payloads.items():
            payload_str = json.dumps(payload, default=str).lower()

            # Check for user-specific identifiers
            if user_context.user_id[:8].lower() in payload_str:
                user_data_found = True

            if user_specific_data["user_context"].lower() in payload_str:
                user_context_found = True

        assert user_data_found, "User-specific data not found in any event payloads"
        assert user_context_found, "User context data not found in any event payloads"

        # Validate agent_completed payload completeness
        completed_payload = event_payloads.get("agent_completed", {})
        assert len(completed_payload) > 0, "agent_completed payload is empty"

        # Should contain result or status information
        has_result = any(key in completed_payload for key in ["result", "status", "outcome", "summary"])
        assert has_result, f"agent_completed payload missing result information: {list(completed_payload.keys())}"

        self.logger.info(f"✅ PASS: Event payload accuracy validated successfully")
        self.logger.info(f"📋 Event payloads validated: {len(event_payloads)}")
        self.logger.info(f"🎯 User-specific data found: {user_data_found}")
        self.logger.info(f"📊 Payload completeness: {sum(1 for v in payload_validation_results.values() if v.get('valid', False))}/{len(payload_validation_results)}")

    async def test_websocket_event_error_recovery(self):
        """
        Test WebSocket event delivery error recovery and resilience.

        BVJ: Validates $100K+ MRR reliability - Events must recover from failures
        Ensures: Event delivery continues after errors, proper error reporting
        """
        user_context = self.test_users[0]

        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))

        # Error recovery tracking
        events_before_error = []
        events_after_recovery = []
        error_events = []
        recovery_events = []

        async def monitor_error_recovery():
            """Monitor event delivery through error and recovery phases."""
            error_occurred = False
            recovery_occurred = False

            try:
                async for message in websocket:
                    event = json.loads(message)
                    event_type = event.get("type")
                    event_data = event.get("data", {})

                    if event_type == "agent_error":
                        error_occurred = True
                        error_events.append(event)
                        self.logger.info(f"🚨 Error event detected: {event_data.get('message', 'Unknown error')}")

                    elif event_type == "agent_recovery":
                        recovery_occurred = True
                        recovery_events.append(event)
                        self.logger.info(f"🔄 Recovery event detected: {event_data.get('message', 'Recovery in progress')}")

                    elif not error_occurred:
                        events_before_error.append(event)

                    elif error_occurred and recovery_occurred:
                        events_after_recovery.append(event)

                    if event_type == "agent_completed":
                        break

            except Exception as e:
                self.logger.error(f"Error recovery monitoring failed: {e}")

        recovery_task = asyncio.create_task(monitor_error_recovery())

        # Send error recovery test request
        error_recovery_request = {
            "type": "execute_agent",
            "agent_type": "error_recovery_event_test",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "error_recovery_test": True,
                "simulate_recoverable_error": True,
                "continue_after_recovery": True,
                "event_continuity_test": True
            }
        }

        await websocket.send(json.dumps(error_recovery_request))

        # Wait for error recovery test completion
        try:
            await asyncio.wait_for(recovery_task, timeout=60.0)
        except asyncio.TimeoutError:
            pytest.fail("Error recovery test timed out")

        # Validate error recovery behavior
        assert len(events_before_error) >= 2, f"Expected events before error, got {len(events_before_error)}"
        assert len(error_events) >= 1, f"Expected at least 1 error event, got {len(error_events)}"
        assert len(recovery_events) >= 1, f"Expected at least 1 recovery event, got {len(recovery_events)}"
        assert len(events_after_recovery) >= 2, f"Expected events after recovery, got {len(events_after_recovery)}"

        # Validate error event content
        first_error = error_events[0]
        error_data = first_error.get("data", {})
        assert "message" in error_data or "error" in error_data, "Error event missing error message"

        # Validate recovery event content
        first_recovery = recovery_events[0]
        recovery_data = first_recovery.get("data", {})
        assert "message" in recovery_data or "status" in recovery_data, "Recovery event missing recovery information"

        # Validate event continuity - events should continue after recovery
        final_event = events_after_recovery[-1] if events_after_recovery else None
        assert final_event is not None, "No events received after recovery"
        assert final_event.get("type") == "agent_completed", "Agent execution did not complete after recovery"

        # Validate total event flow
        total_events = len(events_before_error) + len(error_events) + len(recovery_events) + len(events_after_recovery)
        assert total_events >= 8, f"Expected at least 8 total events for complete error recovery flow, got {total_events}"

        self.logger.info(f"✅ PASS: WebSocket event error recovery validated")
        self.logger.info(f"📊 Events before error: {len(events_before_error)}")
        self.logger.info(f"🚨 Error events: {len(error_events)}")
        self.logger.info(f"🔄 Recovery events: {len(recovery_events)}")
        self.logger.info(f"✅ Events after recovery: {len(events_after_recovery)}")

    def _validate_event_content(self, event_type: str, event_data: Dict[str, Any], user_context) -> None:
        """Validate event content based on type and user context."""
        # Basic validation - event data should not be empty for most events
        if event_type in ["agent_started", "tool_executing", "tool_completed", "agent_completed"]:
            assert len(event_data) > 0, f"{event_type} event data is empty"

        # User context validation - events should be associated with correct user
        if "user_id" in event_data:
            assert event_data["user_id"] == user_context.user_id, f"Event user_id mismatch: {event_data['user_id']} != {user_context.user_id}"

        # Event-specific validation
        if event_type == "agent_started":
            assert any(key in event_data for key in ["agent_name", "status", "started"]), f"agent_started missing key fields: {event_data}"

        elif event_type == "agent_thinking":
            assert any(key in event_data for key in ["reasoning", "message", "thought", "step"]), f"agent_thinking missing reasoning content: {event_data}"

        elif event_type == "tool_executing":
            assert any(key in event_data for key in ["tool_name", "tool", "executing"]), f"tool_executing missing tool identification: {event_data}"

        elif event_type == "tool_completed":
            assert any(key in event_data for key in ["result", "output", "completed"]), f"tool_completed missing result data: {event_data}"

        elif event_type == "agent_completed":
            assert any(key in event_data for key in ["status", "result", "completed", "success"]), f"agent_completed missing completion status: {event_data}"

    def _validate_event_payload_structure(self, event_type: str, event_data: Dict[str, Any], user_context) -> Dict[str, Any]:
        """Validate detailed event payload structure and return validation results."""
        validation = {
            "valid": True,
            "issues": [],
            "completeness_score": 0.0
        }

        try:
            # Basic structure validation
            if not isinstance(event_data, dict):
                validation["valid"] = False
                validation["issues"].append(f"Event data is not a dictionary: {type(event_data)}")
                return validation

            # Required fields validation by event type
            required_fields = {
                "agent_started": ["status"],
                "agent_thinking": ["reasoning", "message"],  # Either is acceptable
                "tool_executing": ["tool_name", "tool"],
                "tool_completed": ["result", "output"],
                "agent_completed": ["status", "result"]
            }

            optional_fields = {
                "agent_started": ["agent_name", "timestamp", "user_id"],
                "agent_thinking": ["step_number", "progress"],
                "tool_executing": ["tool_args", "execution_id"],
                "tool_completed": ["execution_time", "success"],
                "agent_completed": ["duration", "summary", "success"]
            }

            event_required = required_fields.get(event_type, [])
            event_optional = optional_fields.get(event_type, [])

            # Check for required fields (at least one from alternatives)
            if event_required:
                has_required = any(field in event_data for field in event_required)
                if not has_required:
                    validation["valid"] = False
                    validation["issues"].append(f"Missing required fields for {event_type}: expected one of {event_required}")

            # Calculate completeness score
            total_possible_fields = len(event_required) + len(event_optional)
            present_fields = len([f for f in event_required + event_optional if f in event_data])

            if total_possible_fields > 0:
                validation["completeness_score"] = present_fields / total_possible_fields
            else:
                validation["completeness_score"] = 1.0 if len(event_data) > 0 else 0.0

            # Data type validation for known fields
            if "timestamp" in event_data:
                if not isinstance(event_data["timestamp"], (int, float, str)):
                    validation["issues"].append("timestamp field has invalid type")

            if "user_id" in event_data:
                if not isinstance(event_data["user_id"], str) or len(event_data["user_id"]) < 1:
                    validation["issues"].append("user_id field is invalid")

        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Validation error: {e}")

        return validation


# Integration with pytest for automated test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])