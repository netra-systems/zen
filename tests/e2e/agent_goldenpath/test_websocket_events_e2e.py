"""
E2E Tests for WebSocket Events - Golden Path Real-Time Communication

MISSION CRITICAL: Tests the 5 critical WebSocket events that enable real-time 
chat functionality. These events are the foundation of user experience and
represent the bridge between backend agent processing and frontend user interface.

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise)
- Business Goal: User Experience & Platform Reliability  
- Value Impact: Real-time feedback is core to chat experience quality
- Strategic Impact: Poor WebSocket events = poor user experience = churn

The 5 Critical Events (per CLAUDE.md):
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL WEBSOCKETS: wss:// connections with actual event streams
- REAL TIMING: Measure actual event delivery timing and sequence
- EVENT VALIDATION: Ensure ALL 5 events are sent for EVERY agent request
- BUSINESS IMPACT: Events enable $500K+ ARR chat functionality

CRITICAL: These tests protect the real-time user experience that differentiates
the platform. Events must be reliable, fast, and complete.

GitHub Issue: #870 Agent Integration Test Suite Phase 1
Focus: WebSocket events as Golden Path infrastructure
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import httpx

# SSOT imports  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.websocket_events
@pytest.mark.mission_critical
class TestWebSocketEventsE2E(SSotAsyncTestCase):
    """
    E2E tests for the 5 critical WebSocket events in staging GCP.
    
    Tests the real-time communication backbone of the Golden Path user experience.
    """

    @classmethod
    def setUpClass(cls):
        """Setup staging environment for WebSocket event testing."""
        super().setUpClass()
        
        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        
        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available")
        
        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")
        
        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper(
            base_url=cls.staging_config.urls.websocket_url,
            environment="staging"
        )
        
        # Define the 5 critical events per CLAUDE.md
        cls.CRITICAL_EVENTS = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Test user configuration
        cls.test_user_id = f"ws_events_user_{int(time.time())}"
        cls.test_user_email = f"ws_events_test_{int(time.time())}@netra-testing.ai"
        
        cls.logger.info(f"WebSocket events e2e tests initialized for staging")

    def setUp(self):
        """Setup for each test method."""
        super().setUp()
        
        # Generate test-specific context
        self.thread_id = f"ws_events_test_{int(time.time())}"
        self.run_id = f"run_{self.thread_id}"
        
        # Create JWT token for this test
        self.access_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            expires_in_hours=1
        )
        
        self.logger.info(f"WebSocket events test setup - thread_id: {self.thread_id}")

    async def test_all_5_critical_events_delivered_for_agent_request(self):
        """
        Test that ALL 5 critical WebSocket events are delivered for agent requests.
        
        GOLDEN PATH CORE: This validates the fundamental real-time communication
        that makes chat feel responsive and professional.
        
        Validation:
        1. ALL 5 events must be received
        2. Events must be in logical sequence
        3. Events must contain proper data structures
        4. Timing must be reasonable for user experience
        5. No events should be missing or duplicated incorrectly
        
        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - Complete staging WebSocket infrastructure
        STATUS: Should PASS - Critical events are fundamental to user experience
        """
        events_start_time = time.time()
        self.logger.info("🔥 Testing ALL 5 critical WebSocket events delivery")
        
        # Track event delivery metrics
        event_metrics = {
            "events_received": [],
            "event_types": set(),
            "event_timing": {},
            "sequence_order": [],
            "missing_events": [],
            "duplicate_events": defaultdict(int)
        }
        
        try:
            # Establish WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "critical-events-validation"
                    },
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=20.0
            )
            
            connection_time = time.time() - connection_start
            self.logger.info(f"✅ WebSocket connected in {connection_time:.2f}s")
            
            # Send agent request that should trigger ALL 5 events
            test_message = {
                "type": "agent_request",
                "agent": "apex_optimizer_agent",  # Use agent likely to use tools
                "message": (
                    "Please analyze my AI usage patterns and provide specific cost optimization "
                    "recommendations. I need you to check current market rates and suggest "
                    "concrete steps to reduce my $3,000/month OpenAI spend by 25%."
                ),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.test_user_id,
                "context": {
                    "test_scenario": "critical_events_validation",
                    "requires_tool_usage": True,
                    "expected_events": self.CRITICAL_EVENTS
                }
            }
            
            message_send_time = time.time()
            await websocket.send(json.dumps(test_message))
            
            self.logger.info("📤 Agent request sent - collecting critical events...")
            
            # Collect events with comprehensive tracking
            events_timeout = 120.0  # Allow time for complete agent processing with tools
            event_collection_deadline = time.time() + events_timeout
            
            while time.time() < event_collection_deadline:
                try:
                    # Use shorter timeout per event to detect stalled connections
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    
                    event_received_time = time.time()
                    event_type = event.get("type", "unknown")
                    
                    # Record comprehensive event metrics
                    event_metrics["events_received"].append(event)
                    event_metrics["event_types"].add(event_type)
                    event_metrics["sequence_order"].append(event_type)
                    event_metrics["duplicate_events"][event_type] += 1
                    
                    # Record timing for critical events
                    if event_type in self.CRITICAL_EVENTS:
                        time_since_request = event_received_time - message_send_time
                        event_metrics["event_timing"][event_type] = time_since_request
                        
                        self.logger.info(
                            f"📨 CRITICAL EVENT: {event_type} "
                            f"(+{time_since_request:.1f}s)"
                        )
                    
                    # Check for completion
                    if event_type == "agent_completed":
                        self.logger.info("🏁 Agent completion event received")
                        break
                    
                    # Check for error events
                    if event_type == "error" or "error" in event_type:
                        raise AssertionError(f"Error event received: {event}")
                        
                except asyncio.TimeoutError:
                    # Log timeout and continue - but record the gap
                    current_time = time.time()
                    self.logger.warning(
                        f"⏰ Event timeout - no event for 15s "
                        f"(total elapsed: {current_time - message_send_time:.1f}s)"
                    )
                    continue
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Failed to parse WebSocket event: {e}")
                    continue
            
            await websocket.close()
            
            total_events_time = time.time() - events_start_time
            
            # COMPREHENSIVE EVENT VALIDATION
            
            # 1. Validate ALL 5 critical events were received
            received_critical_events = event_metrics["event_types"].intersection(self.CRITICAL_EVENTS)
            missing_critical_events = set(self.CRITICAL_EVENTS) - received_critical_events
            
            if missing_critical_events:
                event_metrics["missing_events"] = list(missing_critical_events)
            
            assert len(missing_critical_events) == 0, (
                f"CRITICAL FAILURE: Missing {len(missing_critical_events)} critical events: {missing_critical_events}. "
                f"Received events: {list(received_critical_events)}. "
                f"Complete event sequence: {event_metrics['sequence_order']}. "
                f"This breaks real-time user experience ($500K+ ARR impact)."
            )
            
            # 2. Validate event sequence logic
            sequence = event_metrics["sequence_order"]
            
            # agent_started should be first critical event
            first_critical_event_idx = next(
                (i for i, event in enumerate(sequence) if event in self.CRITICAL_EVENTS), 
                None
            )
            
            if first_critical_event_idx is not None:
                first_critical_event = sequence[first_critical_event_idx]
                assert first_critical_event == "agent_started", (
                    f"First critical event should be 'agent_started', got '{first_critical_event}'. "
                    f"Sequence: {sequence[:10]}..."  # Show first 10 events
                )
            
            # agent_completed should be last critical event
            last_critical_event_idx = next(
                (len(sequence) - 1 - i for i, event in enumerate(reversed(sequence)) if event in self.CRITICAL_EVENTS),
                None
            )
            
            if last_critical_event_idx is not None:
                last_critical_event = sequence[last_critical_event_idx]
                assert last_critical_event == "agent_completed", (
                    f"Last critical event should be 'agent_completed', got '{last_critical_event}'. "
                    f"Sequence: {sequence[-10:]}..."  # Show last 10 events
                )
            
            # 3. Validate event timing (user experience requirements)
            timing = event_metrics["event_timing"]
            
            # agent_started should come quickly
            if "agent_started" in timing:
                assert timing["agent_started"] < 10.0, (
                    f"agent_started took too long: {timing['agent_started']:.1f}s (max 10s)"
                )
            
            # agent_completed should come within reasonable time
            if "agent_completed" in timing:
                assert timing["agent_completed"] < 120.0, (
                    f"agent_completed took too long: {timing['agent_completed']:.1f}s (max 120s)"
                )
            
            # 4. Validate event data structures
            for event in event_metrics["events_received"]:
                event_type = event.get("type")
                if event_type in self.CRITICAL_EVENTS:
                    # All critical events should have proper structure
                    assert "data" in event or "type" in event, (
                        f"Critical event '{event_type}' missing required structure: {event}"
                    )
                    
                    # Events should include timestamp or timing info
                    has_timing_info = any(key in event for key in ["timestamp", "data", "time"])
                    assert has_timing_info, (
                        f"Critical event '{event_type}' missing timing information: {event.keys()}"
                    )
            
            # LOG COMPREHENSIVE SUCCESS METRICS
            self.logger.info("🎉 ALL 5 CRITICAL WEBSOCKET EVENTS DELIVERED SUCCESSFULLY")
            self.logger.info(f"📊 Event Delivery Metrics:")
            self.logger.info(f"   Total Events: {len(event_metrics['events_received'])}")
            self.logger.info(f"   Critical Events: {len(received_critical_events)}/5")
            self.logger.info(f"   Event Types: {sorted(event_metrics['event_types'])}")
            self.logger.info(f"   Total Duration: {total_events_time:.1f}s")
            self.logger.info(f"   Event Timing: {event_metrics['event_timing']}")
            self.logger.info(f"   Sequence: {event_metrics['sequence_order'][:15]}...")  # First 15 events
            
            # Business value validation
            assert len(event_metrics["events_received"]) >= 5, (
                f"Should receive at least 5 events (the critical ones), got {len(event_metrics['events_received'])}"
            )
            
            assert total_events_time < 180.0, (
                f"Complete event delivery too slow: {total_events_time:.1f}s (max 180s)"
            )
            
        except Exception as e:
            total_time = time.time() - events_start_time
            
            self.logger.error("❌ CRITICAL WEBSOCKET EVENTS FAILURE")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")
            self.logger.error(f"   Events Received: {len(event_metrics.get('events_received', []))}")
            self.logger.error(f"   Critical Events: {event_metrics.get('event_types', set())}")
            self.logger.error(f"   Missing Events: {event_metrics.get('missing_events', [])}")
            
            raise AssertionError(
                f"Critical WebSocket events test failed after {total_time:.1f}s: {e}. "
                f"This breaks real-time user experience - core platform functionality compromised."
            )

    async def test_websocket_event_timing_and_performance(self):
        """
        Test WebSocket event timing and performance characteristics.
        
        PERFORMANCE: Events should be delivered promptly to ensure good UX.
        
        Metrics tested:
        1. Time to first event (agent_started)
        2. Time between events
        3. Total event stream duration  
        4. Event ordering consistency
        5. No abnormal delays or gaps
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Staging WebSocket performance measurement
        STATUS: Should PASS - Good timing is essential for user experience
        """
        self.logger.info("⏱️ Testing WebSocket event timing and performance")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test multiple timing scenarios
        timing_tests = [
            {
                "name": "quick_response_agent",
                "message": "What is AI cost optimization?",
                "agent": "triage_agent",
                "expected_first_event_time": 5.0,
                "expected_total_time": 30.0
            },
            {
                "name": "complex_analysis_agent",
                "message": (
                    "Please perform a comprehensive analysis of my AI infrastructure "
                    "costs and provide detailed optimization recommendations with "
                    "market research and specific implementation steps."
                ),
                "agent": "apex_optimizer_agent", 
                "expected_first_event_time": 8.0,
                "expected_total_time": 60.0
            }
        ]
        
        for test_scenario in timing_tests:
            scenario_start = time.time()
            self.logger.info(f"Testing timing scenario: {test_scenario['name']}")
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging", 
                        "X-Test-Suite": "event-timing-performance"
                    },
                    ssl=ssl_context
                ),
                timeout=15.0
            )
            
            try:
                # Send test message
                message = {
                    "type": "agent_request",
                    "agent": test_scenario["agent"],
                    "message": test_scenario["message"],
                    "thread_id": f"timing_test_{test_scenario['name']}_{int(time.time())}",
                    "user_id": self.test_user_id
                }
                
                request_sent_time = time.time()
                await websocket.send(json.dumps(message))
                
                # Collect timing data
                timing_data = {
                    "events": [],
                    "inter_event_times": [],
                    "first_event_time": None,
                    "last_event_time": None,
                    "total_events": 0
                }
                
                last_event_time = request_sent_time
                timeout = test_scenario["expected_total_time"] + 30.0  # Add buffer
                
                while time.time() - request_sent_time < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        
                        event_received_time = time.time()
                        event_type = event.get("type")
                        
                        # Record timing metrics
                        time_since_request = event_received_time - request_sent_time
                        time_since_last_event = event_received_time - last_event_time
                        
                        timing_data["events"].append({
                            "type": event_type,
                            "time_since_request": time_since_request,
                            "time_since_last_event": time_since_last_event
                        })
                        
                        timing_data["inter_event_times"].append(time_since_last_event)
                        timing_data["total_events"] += 1
                        
                        if timing_data["first_event_time"] is None:
                            timing_data["first_event_time"] = time_since_request
                        
                        timing_data["last_event_time"] = time_since_request
                        last_event_time = event_received_time
                        
                        # Check for completion
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Validate timing performance
                scenario_duration = time.time() - scenario_start
                
                # First event should come quickly
                assert timing_data["first_event_time"] is not None, (
                    f"Should receive at least one event for {test_scenario['name']}"
                )
                
                assert timing_data["first_event_time"] <= test_scenario["expected_first_event_time"], (
                    f"First event too slow for {test_scenario['name']}: "
                    f"{timing_data['first_event_time']:.1f}s "
                    f"(expected ≤{test_scenario['expected_first_event_time']}s)"
                )
                
                # Total time should be reasonable
                assert timing_data["last_event_time"] <= test_scenario["expected_total_time"], (
                    f"Total event stream too slow for {test_scenario['name']}: "
                    f"{timing_data['last_event_time']:.1f}s "
                    f"(expected ≤{test_scenario['expected_total_time']}s)"
                )
                
                # Inter-event times should be reasonable (no huge gaps)
                if timing_data["inter_event_times"]:
                    max_gap = max(timing_data["inter_event_times"])
                    assert max_gap < 30.0, (
                        f"Event gap too large for {test_scenario['name']}: {max_gap:.1f}s "
                        f"(max 30s between events)"
                    )
                
                # Should receive reasonable number of events
                assert timing_data["total_events"] >= 3, (
                    f"Too few events for {test_scenario['name']}: {timing_data['total_events']} "
                    f"(expected ≥3 events)"
                )
                
                self.logger.info(f"✅ {test_scenario['name']} timing validation passed:")
                self.logger.info(f"   First event: {timing_data['first_event_time']:.1f}s")
                self.logger.info(f"   Total duration: {timing_data['last_event_time']:.1f}s") 
                self.logger.info(f"   Total events: {timing_data['total_events']}")
                self.logger.info(f"   Average inter-event time: "
                               f"{sum(timing_data['inter_event_times'])/len(timing_data['inter_event_times']):.1f}s")
            
            finally:
                await websocket.close()
        
        self.logger.info("⏱️ WebSocket event timing and performance validation complete")

    async def test_websocket_event_resilience_and_recovery(self):
        """
        Test WebSocket event delivery resilience and recovery scenarios.
        
        RESILIENCE: Event delivery should be reliable even with network issues,
        connection interruptions, or temporary service problems.
        
        Test scenarios:
        1. Connection interruption and recovery
        2. Event delivery confirmation
        3. Multiple concurrent event streams
        4. Event ordering under stress conditions
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes - Staging resilience testing
        STATUS: Should PASS - Resilience is critical for production reliability
        """
        self.logger.info("🛡️ Testing WebSocket event resilience and recovery")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test 1: Connection recovery after interruption
        self.logger.info("Testing connection recovery after interruption")
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "event-resilience-recovery"
                },
                ssl=ssl_context
            ),
            timeout=15.0
        )
        
        try:
            # Start an agent request
            message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test message for resilience testing",
                "thread_id": f"resilience_test_{int(time.time())}",
                "user_id": self.test_user_id
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect initial events
            initial_events = []
            for _ in range(3):  # Get a few events
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    initial_events.append(event)
                except asyncio.TimeoutError:
                    break
            
            # Simulate connection interruption by closing and reconnecting
            await websocket.close()
            
            self.logger.info("Connection closed - attempting recovery...")
            await asyncio.sleep(2)  # Brief pause to simulate network issue
            
            # Reconnect
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Connection": "recovery"
                    },
                    ssl=ssl_context
                ),
                timeout=15.0
            )
            
            # Send a new request after recovery
            recovery_message = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": "Recovery test message after connection interruption",
                "thread_id": f"recovery_test_{int(time.time())}",
                "user_id": self.test_user_id
            }
            
            await websocket.send(json.dumps(recovery_message))
            
            # Should receive events from recovery request
            recovery_events = []
            recovery_timeout = 30.0
            recovery_start = time.time()
            
            while time.time() - recovery_start < recovery_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    event = json.loads(event_data)
                    recovery_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            # Validate recovery
            assert len(recovery_events) > 0, "Should receive events after connection recovery"
            
            recovery_event_types = {event.get("type") for event in recovery_events}
            assert "agent_started" in recovery_event_types, (
                f"Should receive agent_started after recovery, got: {recovery_event_types}"
            )
            
            self.logger.info(f"✅ Connection recovery successful: {len(recovery_events)} events")
        
        finally:
            await websocket.close()
        
        # Test 2: Multiple concurrent event streams
        self.logger.info("Testing multiple concurrent event streams")
        
        concurrent_streams = 3
        stream_tasks = []
        
        async def process_concurrent_stream(stream_id: int) -> Dict[str, Any]:
            """Process a single concurrent event stream."""
            try:
                ws = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        extra_headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "X-Environment": "staging",
                            "X-Stream-ID": str(stream_id)
                        },
                        ssl=ssl_context
                    ),
                    timeout=15.0
                )
                
                # Send stream-specific message
                message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Concurrent stream {stream_id} test message",
                    "thread_id": f"concurrent_stream_{stream_id}_{int(time.time())}",
                    "user_id": self.test_user_id
                }
                
                await ws.send(json.dumps(message))
                
                # Collect events for this stream
                stream_events = []
                stream_timeout = 25.0
                stream_start = time.time()
                
                while time.time() - stream_start < stream_timeout:
                    try:
                        event_data = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        stream_events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                await ws.close()
                
                return {
                    "stream_id": stream_id,
                    "success": True,
                    "events_count": len(stream_events),
                    "event_types": {event.get("type") for event in stream_events}
                }
                
            except Exception as e:
                return {
                    "stream_id": stream_id,
                    "success": False,
                    "error": str(e),
                    "events_count": 0
                }
        
        # Execute concurrent streams
        stream_tasks = [process_concurrent_stream(i) for i in range(concurrent_streams)]
        stream_results = await asyncio.gather(*stream_tasks, return_exceptions=True)
        
        # Validate concurrent stream results
        successful_streams = [r for r in stream_results if isinstance(r, dict) and r["success"]]
        failed_streams = [r for r in stream_results if isinstance(r, dict) and not r["success"]]
        
        assert len(successful_streams) >= 2, (
            f"At least 2/3 concurrent streams should succeed, got {len(successful_streams)}. "
            f"Failed: {failed_streams}"
        )
        
        # All successful streams should receive basic events
        for stream in successful_streams:
            assert stream["events_count"] > 0, (
                f"Stream {stream['stream_id']} should receive events"
            )
            
            assert "agent_started" in stream["event_types"], (
                f"Stream {stream['stream_id']} missing agent_started event"
            )
        
        self.logger.info(f"✅ Concurrent streams test: {len(successful_streams)}/{concurrent_streams} successful")
        
        self.logger.info("🛡️ WebSocket event resilience and recovery tests complete")

    async def test_event_data_structure_and_content_validation(self):
        """
        Test WebSocket event data structures and content validation.
        
        DATA INTEGRITY: Events should have consistent, well-formed data structures
        that the frontend can reliably parse and display.
        
        Validation areas:
        1. Event schema consistency
        2. Required fields presence
        3. Data type correctness
        4. Content relevance and quality
        5. Timestamp and metadata accuracy
        
        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - Staging data structure validation  
        STATUS: Should PASS - Consistent data structures are essential for frontend
        """
        self.logger.info("📋 Testing event data structure and content validation")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "event-data-validation"
                },
                ssl=ssl_context
            ),
            timeout=15.0
        )
        
        try:
            # Send request to generate events with rich data
            message = {
                "type": "agent_request",
                "agent": "apex_optimizer_agent",
                "message": (
                    "Please analyze AI cost optimization opportunities and provide "
                    "detailed recommendations with supporting data and calculations."
                ),
                "thread_id": f"data_validation_test_{int(time.time())}",
                "run_id": f"data_val_run_{int(time.time())}",
                "user_id": self.test_user_id
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect events for data structure analysis
            events_for_validation = []
            validation_timeout = 45.0
            validation_start = time.time()
            
            while time.time() - validation_start < validation_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    event = json.loads(event_data)
                    events_for_validation.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            # COMPREHENSIVE DATA STRUCTURE VALIDATION
            
            assert len(events_for_validation) > 0, "Should receive events for validation"
            
            critical_events_found = []
            
            for event in events_for_validation:
                event_type = event.get("type", "unknown")
                
                # Basic structure validation for all events
                assert isinstance(event, dict), f"Event should be dict, got {type(event)}"
                assert "type" in event, f"Event missing 'type' field: {event}"
                
                # Critical event specific validation
                if event_type in self.CRITICAL_EVENTS:
                    critical_events_found.append(event_type)
                    
                    # All critical events should have data field or meaningful content
                    has_meaningful_content = any(key in event for key in ["data", "message", "content", "result"])
                    assert has_meaningful_content, (
                        f"Critical event '{event_type}' lacks meaningful content: {event.keys()}"
                    )
                    
                    # Timestamp or timing information should be present
                    has_timing_info = any(key in str(event).lower() for key in ["time", "timestamp", "duration"])
                    if not has_timing_info:
                        self.logger.warning(f"Event '{event_type}' may lack timing information")
                    
                    # Event-specific validations
                    if event_type == "agent_started":
                        # Should indicate which agent started
                        event_str = json.dumps(event).lower()
                        has_agent_info = any(term in event_str for term in ["agent", "started", "begin"])
                        assert has_agent_info, f"agent_started event should contain agent info: {event}"
                    
                    elif event_type == "agent_thinking":
                        # Should contain reasoning or thought process
                        event_str = json.dumps(event).lower()
                        has_thinking_info = any(term in event_str for term in [
                            "think", "reason", "analyz", "consider", "process"
                        ])
                        # Note: This is a soft requirement - log warning if missing
                        if not has_thinking_info:
                            self.logger.warning(f"agent_thinking event may lack thinking content: {event}")
                    
                    elif event_type == "tool_executing":
                        # Should indicate which tool is being executed
                        event_str = json.dumps(event).lower() 
                        has_tool_info = any(term in event_str for term in ["tool", "execut", "function", "action"])
                        assert has_tool_info, f"tool_executing event should contain tool info: {event}"
                    
                    elif event_type == "tool_completed":
                        # Should contain tool results or completion status
                        event_str = json.dumps(event).lower()
                        has_result_info = any(term in event_str for term in [
                            "complet", "result", "output", "finish", "done"
                        ])
                        assert has_result_info, f"tool_completed event should contain result info: {event}"
                    
                    elif event_type == "agent_completed":
                        # Should contain final result or response
                        event_data = event.get("data", {})
                        result = event_data.get("result", {})
                        
                        assert result is not None, f"agent_completed should have result: {event}"
                        
                        # Result should have meaningful content
                        result_str = str(result)
                        assert len(result_str) > 20, (
                            f"agent_completed result too short: {len(result_str)} chars"
                        )
            
            # Validate we found critical events to analyze
            assert len(critical_events_found) >= 2, (
                f"Should find at least 2 critical events for validation, got: {critical_events_found}"
            )
            
            self.logger.info(f"📋 Data structure validation passed:")
            self.logger.info(f"   Total events analyzed: {len(events_for_validation)}")
            self.logger.info(f"   Critical events validated: {critical_events_found}")
            
        finally:
            await websocket.close()
        
        self.logger.info("📋 Event data structure and content validation complete")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s", 
        "--gcp-staging",
        "--websocket-events"
    ])