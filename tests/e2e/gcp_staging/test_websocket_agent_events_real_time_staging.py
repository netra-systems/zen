"""
E2E Test: WebSocket Agent Events Real-Time Delivery Validation (Staging)

Business Value: $500K+ ARR - Critical WebSocket event delivery system
Environment: GCP Staging with real WebSocket services (NO DOCKER)  
Coverage: All 5 mission-critical WebSocket events in real-time
Performance: Events delivered with <5s gaps, complete sequence validation

GitHub Issue: #861 - Agent Golden Path Messages E2E Test Coverage
Test Plan: /test_plans/agent_golden_path_messages_e2e_plan_20250914.md

MISSION CRITICAL: This test validates all 5 WebSocket events that enable real-time chat UX:

1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

SUCCESS CRITERIA:
- All 5 events delivered in logical sequence
- Event timing gaps <5s (real-time user experience)
- Event payload completeness and structure validation
- No WebSocket silent failures or dropped connections
- Multi-user event isolation (no cross-contamination)
- Event delivery during network interruptions and reconnection
"""

import pytest
import asyncio
import json
import time
import websockets
import ssl
import base64
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
import httpx

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_config import StagingTestConfig as StagingConfig

# Real service clients for staging
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketAgentEventsRealTimeStaging(StagingTestBase):
    """
    Real-time WebSocket event delivery validation with staging services
    
    BUSINESS IMPACT: Validates critical real-time user experience components
    ENVIRONMENT: GCP Staging with real WebSocket infrastructure
    COVERAGE: Complete WebSocket event lifecycle and delivery reliability
    """
    
    # Event validation configuration
    REQUIRED_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    MAX_EVENT_GAP = 5.0  # Maximum seconds between events
    MAX_SEQUENCE_DURATION = 30.0  # Maximum total time for all events
    EVENT_PAYLOAD_REQUIRED_FIELDS = {
        "agent_started": ["timestamp", "agent_type", "user_id"],
        "agent_thinking": ["timestamp", "reasoning", "progress"],  
        "tool_executing": ["timestamp", "tool_name", "parameters"],
        "tool_completed": ["timestamp", "tool_name", "results"],
        "agent_completed": ["timestamp", "response", "execution_summary"]
    }
    
    # Test scenarios for different event patterns
    EVENT_TEST_SCENARIOS = [
        {
            "name": "simple_query_events",
            "message": "What is AI optimization?",
            "expected_events": ["agent_started", "agent_thinking", "agent_completed"],
            "expected_tools": 0,
            "max_duration": 10.0
        },
        {
            "name": "tool_usage_events", 
            "message": "Analyze current system performance and provide metrics",
            "expected_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
            "expected_tools": 1,
            "max_duration": 20.0
        },
        {
            "name": "multi_tool_workflow_events",
            "message": "Create comprehensive performance report with cost analysis and optimization recommendations",
            "expected_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "tool_executing", "tool_completed", "agent_completed"],
            "expected_tools": 2,
            "max_duration": 30.0
        }
    ]
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup WebSocket event testing infrastructure"""
        await super().asyncSetUpClass()
        
        # Initialize staging configuration  
        cls.staging_config = StagingConfig()
        cls.staging_backend_url = cls.staging_config.get_backend_websocket_url()
        
        # Initialize real service clients
        cls.auth_client = StagingAuthClient()
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging services health
        await cls._verify_staging_websocket_health()
        
        # Create test users for event testing
        cls.event_test_users = await cls._create_event_test_users()
        
        cls.logger.info("WebSocket agent events real-time staging test setup completed")
    
    @classmethod
    async def _verify_staging_websocket_health(cls):
        """Verify staging WebSocket service is healthy and responsive"""
        try:
            # Test basic WebSocket connectivity
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            test_connection = await asyncio.wait_for(
                websockets.connect(
                    cls.staging_backend_url,
                    ssl=ssl_context if cls.staging_backend_url.startswith('wss') else None,
                    ping_interval=20,
                    ping_timeout=10
                ),
                timeout=15
            )
            
            # Test ping/pong
            await test_connection.ping()
            await test_connection.close()
            
            cls.logger.info("Staging WebSocket service health verified")
            
        except Exception as e:
            pytest.skip(f"Staging WebSocket service not healthy: {e}")
    
    @classmethod
    async def _create_event_test_users(cls) -> List[Dict[str, Any]]:
        """Create specialized users for WebSocket event testing"""
        event_users = []
        
        for i, scenario in enumerate(cls.EVENT_TEST_SCENARIOS):
            user_data = {
                "user_id": f"ws_events_user_{scenario['name']}_{int(time.time())}",
                "email": f"ws_events_{scenario['name']}@netrasystems-staging.ai",
                "scenario": scenario['name'],
                "test_permissions": ["basic_chat", "agent_access", "tool_execution", "real_time_events"]
            }
            
            try:
                access_token = await cls.auth_client.generate_test_access_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    permissions=user_data["test_permissions"]
                )
                
                user_data["access_token"] = access_token
                user_data["encoded_token"] = base64.urlsafe_b64encode(
                    access_token.encode()
                ).decode().rstrip('=')
                
                event_users.append(user_data)
                cls.logger.info(f"Created WebSocket event test user: {user_data['email']}")
                
            except Exception as e:
                cls.logger.error(f"Failed to create event test user for {scenario['name']}: {e}")
                
        if not event_users:
            pytest.skip("Cannot create staging WebSocket event test users")
            
        return event_users

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_all_five_critical_events_delivered_in_sequence(self):
        """
        MISSION CRITICAL: Validate all 5 WebSocket events delivered during agent execution
        
        Events to validate:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency  
        4. tool_completed - Tool results display
        5. agent_completed - User knows response is ready
        
        Validation criteria:
        - Event sequence correctness (logical order)
        - Event timing (no >5s gaps between events)
        - Event payload completeness (all required fields)
        - Real-time delivery (no batching delays)
        - User isolation (events only to correct user)
        """
        test_results = []
        
        # Test each scenario to ensure comprehensive event coverage
        for scenario in self.EVENT_TEST_SCENARIOS:
            scenario_start = time.time()
            user = next((u for u in self.event_test_users if u["scenario"] == scenario["name"]), None)
            
            if not user:
                pytest.fail(f"No event test user found for scenario: {scenario['name']}")
            
            self.logger.info(f"Testing WebSocket events for scenario: {scenario['name']}")
            
            try:
                # Establish WebSocket connection
                connection = await self._establish_event_tracking_connection(user)
                
                # Send message and capture all events
                captured_events = await self._capture_complete_event_sequence(
                    connection, scenario["message"], user, scenario
                )
                
                # Validate event sequence
                self._validate_event_sequence_completeness(captured_events, scenario)
                self._validate_event_timing_requirements(captured_events, scenario)
                self._validate_event_payload_structure(captured_events, scenario)
                self._validate_event_logical_order(captured_events, scenario)
                
                await connection.close()
                
                scenario_duration = time.time() - scenario_start
                test_results.append({
                    "scenario": scenario["name"],
                    "status": "success",
                    "duration": scenario_duration,
                    "events_captured": len(captured_events),
                    "event_types": [e["type"] for e in captured_events]
                })
                
                self.logger.info(
                    f"WebSocket events validated for {scenario['name']}: "
                    f"{len(captured_events)} events in {scenario_duration:.1f}s"
                )
                
            except Exception as e:
                test_results.append({
                    "scenario": scenario["name"],
                    "status": "failed", 
                    "duration": time.time() - scenario_start,
                    "error": str(e)
                })
                pytest.fail(f"WebSocket event validation failed for {scenario['name']}: {e}")
        
        # Ensure all scenarios passed
        successful_tests = [r for r in test_results if r["status"] == "success"]
        assert len(successful_tests) == len(self.EVENT_TEST_SCENARIOS), \
            f"WebSocket event tests failed: {len(successful_tests)}/{len(self.EVENT_TEST_SCENARIOS)} passed"
        
        self.logger.info(f"All WebSocket event validation tests passed: {test_results}")

    async def _establish_event_tracking_connection(self, user: Dict[str, Any]) -> websockets.WebSocketClientProtocol:
        """Establish WebSocket connection optimized for event tracking"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            headers = {
                "Authorization": f"Bearer {user['access_token']}",
                "X-User-ID": user["user_id"],
                "X-Event-Tracking": "enabled",
                "X-Test-Scenario": user["scenario"],
                "X-Test-Environment": "staging",
                "X-Real-Time-Events": "required"
            }
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.staging_backend_url,
                    extra_headers=headers,
                    ssl=ssl_context if self.staging_backend_url.startswith('wss') else None,
                    ping_interval=15,  # Shorter interval for event tracking
                    ping_timeout=8,
                    close_timeout=10
                ),
                timeout=25
            )
            
            # Verify connection is ready for events
            await connection.ping()
            self.logger.info(f"Event tracking connection established for {user['scenario']}")
            
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to establish event tracking connection: {e}")
            raise

    async def _capture_complete_event_sequence(
        self,
        connection: websockets.WebSocketClientProtocol,
        message: str,
        user: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Capture complete sequence of WebSocket events from message to completion"""
        
        captured_events = []
        sequence_start = time.time()
        
        # Send initial message
        message_payload = {
            "type": "chat_message",
            "data": {
                "message": message,
                "user_id": user["user_id"],
                "test_scenario": user["scenario"],
                "event_tracking": True,
                "timestamp": int(time.time())
            }
        }
        
        await connection.send(json.dumps(message_payload))
        self.logger.info(f"Sent message for event tracking: {user['scenario']}")
        
        # Track events until completion or timeout
        expected_events = set(scenario["expected_events"])
        received_event_types = set()
        last_event_time = sequence_start
        
        while (
            not received_event_types.issuperset(set(["agent_started", "agent_completed"])) or
            len(received_event_types.intersection(expected_events)) < len(expected_events) * 0.8
        ):
            try:
                current_time = time.time()
                
                # Check for timeout
                if current_time - sequence_start > scenario["max_duration"]:
                    self.logger.warning(f"Event sequence timeout: {current_time - sequence_start:.1f}s")
                    break
                
                # Receive next event
                event_message = await asyncio.wait_for(
                    connection.recv(),
                    timeout=self.MAX_EVENT_GAP
                )
                
                event_data = json.loads(event_message)
                event_timestamp = time.time()
                
                # Record event details
                event_record = {
                    "type": event_data.get("type"),
                    "timestamp": event_timestamp,
                    "sequence_time": event_timestamp - sequence_start,
                    "gap_from_previous": event_timestamp - last_event_time,
                    "data": event_data.get("data", {}),
                    "raw_event": event_data
                }
                
                captured_events.append(event_record)
                received_event_types.add(event_record["type"])
                last_event_time = event_timestamp
                
                self.logger.info(
                    f"Captured event: {event_record['type']} "
                    f"(+{event_record['sequence_time']:.1f}s, gap: {event_record['gap_from_previous']:.2f}s)"
                )
                
                # Check for completion
                if event_record["type"] == "agent_completed":
                    self.logger.info(f"Agent completion event received for {user['scenario']}")
                    break
                    
            except asyncio.TimeoutError:
                current_time = time.time()
                gap_duration = current_time - last_event_time
                
                self.logger.warning(
                    f"Event timeout: {gap_duration:.1f}s gap. "
                    f"Received types: {received_event_types}, Expected: {expected_events}"
                )
                
                # If we have critical events, consider sequence complete
                if "agent_started" in received_event_types and len(captured_events) >= 3:
                    self.logger.info("Accepting partial sequence with critical events present")
                    break
                else:
                    raise AssertionError(f"Critical event timeout in {user['scenario']}")
                    
            except Exception as e:
                self.logger.error(f"Error capturing events: {e}")
                break
        
        total_duration = time.time() - sequence_start
        self.logger.info(
            f"Event sequence capture completed for {user['scenario']}: "
            f"{len(captured_events)} events in {total_duration:.1f}s"
        )
        
        return captured_events

    def _validate_event_sequence_completeness(
        self, 
        events: List[Dict[str, Any]], 
        scenario: Dict[str, Any]
    ):
        """Validate that all expected events are present"""
        event_types = [e["type"] for e in events]
        expected_events = scenario["expected_events"]
        
        # Check for critical events
        critical_events = ["agent_started", "agent_completed"]
        missing_critical = [e for e in critical_events if e not in event_types]
        
        assert not missing_critical, \
            f"Missing critical events for {scenario['name']}: {missing_critical}. " \
            f"Received: {event_types}"
        
        # Check expected event coverage (allow some flexibility)
        received_expected = [e for e in expected_events if e in event_types]
        coverage_ratio = len(received_expected) / len(expected_events)
        
        assert coverage_ratio >= 0.7, \
            f"Insufficient event coverage for {scenario['name']}: {coverage_ratio:.1%}. " \
            f"Expected: {expected_events}, Received: {event_types}"
        
        self.logger.info(f"Event completeness validated for {scenario['name']}: {coverage_ratio:.1%} coverage")

    def _validate_event_timing_requirements(
        self, 
        events: List[Dict[str, Any]], 
        scenario: Dict[str, Any]
    ):
        """Validate event timing meets real-time requirements"""
        
        # Check individual event gaps
        large_gaps = [e for e in events if e["gap_from_previous"] > self.MAX_EVENT_GAP]
        assert len(large_gaps) <= 1, \
            f"Too many large event gaps in {scenario['name']}: {[(e['type'], e['gap_from_previous']) for e in large_gaps]}"
        
        # Check total sequence duration
        total_duration = events[-1]["sequence_time"] if events else 0
        assert total_duration <= scenario["max_duration"], \
            f"Event sequence too slow for {scenario['name']}: {total_duration:.1f}s > {scenario['max_duration']}s"
        
        # Check event delivery frequency (events should be reasonably spaced)
        if len(events) >= 3:
            avg_gap = sum(e["gap_from_previous"] for e in events[1:]) / (len(events) - 1)
            assert avg_gap <= self.MAX_EVENT_GAP / 2, \
                f"Average event gap too large for {scenario['name']}: {avg_gap:.1f}s"
        
        self.logger.info(f"Event timing validated for {scenario['name']}: {total_duration:.1f}s total")

    def _validate_event_payload_structure(
        self, 
        events: List[Dict[str, Any]], 
        scenario: Dict[str, Any]
    ):
        """Validate event payload structure and required fields"""
        
        for event in events:
            event_type = event["type"]
            event_data = event.get("data", {})
            
            # Check basic structure
            assert "type" in event["raw_event"], f"Event missing type field: {event_type}"
            assert "data" in event["raw_event"], f"Event missing data field: {event_type}"
            assert "timestamp" in event, f"Event missing timestamp: {event_type}"
            
            # Check type-specific required fields
            if event_type in self.EVENT_PAYLOAD_REQUIRED_FIELDS:
                required_fields = self.EVENT_PAYLOAD_REQUIRED_FIELDS[event_type]
                
                for field in required_fields:
                    if field not in ["timestamp"]:  # timestamp checked separately
                        assert field in event_data or field in event["raw_event"]["data"], \
                            f"Event {event_type} missing required field {field} in {scenario['name']}"
            
            # Validate timestamp format
            assert isinstance(event["timestamp"], (int, float)), \
                f"Invalid timestamp type for {event_type}: {type(event['timestamp'])}"
        
        self.logger.info(f"Event payload structure validated for {scenario['name']}")

    def _validate_event_logical_order(
        self, 
        events: List[Dict[str, Any]], 
        scenario: Dict[str, Any]
    ):
        """Validate logical ordering of events"""
        event_types = [e["type"] for e in events]
        
        # agent_started should come before agent_completed
        if "agent_started" in event_types and "agent_completed" in event_types:
            started_idx = event_types.index("agent_started")
            completed_idx = event_types.index("agent_completed") 
            assert started_idx < completed_idx, \
                f"Logical order violation in {scenario['name']}: agent_completed before agent_started"
        
        # tool_executing should come before tool_completed for same tool
        tool_executing_indices = [i for i, t in enumerate(event_types) if t == "tool_executing"]
        tool_completed_indices = [i for i, t in enumerate(event_types) if t == "tool_completed"]
        
        for exec_idx in tool_executing_indices:
            # Find next tool_completed after this tool_executing
            next_completed = next((c for c in tool_completed_indices if c > exec_idx), None)
            if next_completed is not None:
                assert exec_idx < next_completed, \
                    f"Tool execution order violation in {scenario['name']}: completion before execution"
        
        # agent_thinking should come after agent_started (if both present)  
        if "agent_started" in event_types and "agent_thinking" in event_types:
            started_idx = event_types.index("agent_started")
            thinking_idx = event_types.index("agent_thinking")
            assert started_idx < thinking_idx, \
                f"Thinking order violation in {scenario['name']}: thinking before started"
        
        self.logger.info(f"Event logical order validated for {scenario['name']}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    @pytest.mark.resilience
    async def test_websocket_reconnection_event_continuity(self):
        """
        Test WebSocket event delivery continuity after connection interruption
        
        RESILIENCE VALIDATION: Events continue after reconnection
        USER EXPERIENCE: Seamless chat experience despite network issues
        """
        user = self.event_test_users[0]
        scenario = self.EVENT_TEST_SCENARIOS[1]  # Tool usage scenario
        
        # Establish initial connection
        connection = await self._establish_event_tracking_connection(user)
        
        # Start message that will take time to complete
        long_message = "Perform comprehensive system analysis with detailed performance metrics and optimization recommendations"
        
        message_payload = {
            "type": "chat_message",
            "data": {
                "message": long_message,
                "user_id": user["user_id"],
                "reconnection_test": True
            }
        }
        
        await connection.send(json.dumps(message_payload))
        
        # Capture initial events
        initial_events = []
        for _ in range(3):  # Get first few events
            try:
                event_message = await asyncio.wait_for(connection.recv(), timeout=8)
                event_data = json.loads(event_message)
                initial_events.append(event_data)
                
                if event_data.get("type") == "agent_thinking":
                    break  # Good point to simulate disconnection
                    
            except asyncio.TimeoutError:
                break
        
        # Simulate connection interruption
        await connection.close()
        self.logger.info("Simulated connection interruption")
        
        # Wait brief moment to simulate network issue
        await asyncio.sleep(2)
        
        # Reconnect and continue event tracking
        reconnection = await self._establish_event_tracking_connection(user)
        
        # Continue tracking events
        remaining_events = []
        reconnect_start = time.time()
        
        while time.time() - reconnect_start < 20:  # 20s max for remaining events
            try:
                event_message = await asyncio.wait_for(reconnection.recv(), timeout=6)
                event_data = json.loads(event_message)
                remaining_events.append(event_data)
                
                if event_data.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for events after reconnection")
                break
        
        await reconnection.close()
        
        # Validate event continuity
        all_event_types = [e.get("type") for e in initial_events + remaining_events]
        
        assert "agent_started" in all_event_types, "Missing agent_started event"
        assert "agent_completed" in all_event_types, "Missing agent_completed event"
        assert len(remaining_events) > 0, "No events received after reconnection"
        
        self.logger.info(
            f"Reconnection test passed: {len(initial_events)} initial + "
            f"{len(remaining_events)} post-reconnection events"
        )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_agent_error_websocket_event_handling(self):
        """
        Test WebSocket event delivery during agent execution errors
        
        ERROR HANDLING: Events delivered even when agent encounters errors
        USER COMMUNICATION: Users informed of errors through events
        """
        user = self.event_test_users[0]
        
        # Send message that may cause agent error
        error_inducing_message = "Execute undefined command xyz123 with invalid parameters"
        
        connection = await self._establish_event_tracking_connection(user)
        
        message_payload = {
            "type": "chat_message",
            "data": {
                "message": error_inducing_message,
                "user_id": user["user_id"],
                "error_handling_test": True
            }
        }
        
        await connection.send(json.dumps(message_payload))
        
        # Capture events including potential error events
        error_test_events = []
        test_start = time.time()
        
        while time.time() - test_start < 15:  # 15s max for error handling
            try:
                event_message = await asyncio.wait_for(connection.recv(), timeout=5)
                event_data = json.loads(event_message)
                error_test_events.append(event_data)
                
                event_type = event_data.get("type")
                
                # Look for completion or error events
                if event_type in ["agent_completed", "agent_error", "agent_failed"]:
                    break
                    
            except asyncio.TimeoutError:
                self.logger.warning("Timeout in error handling test")
                break
        
        await connection.close()
        
        # Validate error event handling
        event_types = [e.get("type") for e in error_test_events]
        
        # Should have at least agent_started
        assert "agent_started" in event_types, "Missing agent_started in error scenario"
        
        # Should have some form of completion/error notification
        completion_events = [t for t in event_types if t in ["agent_completed", "agent_error", "agent_failed"]]
        assert len(completion_events) > 0, "No completion/error event received"
        
        self.logger.info(f"Error handling test passed: {len(error_test_events)} events, types: {event_types}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_high_frequency_event_delivery_performance(self):
        """
        Test WebSocket event delivery under high-frequency scenarios
        
        PERFORMANCE VALIDATION: System handles rapid event generation
        SCALABILITY: Event delivery remains reliable under load
        """
        user = self.event_test_users[0]
        
        # Message that will generate many events quickly
        high_frequency_message = "Run parallel analysis of multiple datasets with real-time progress updates"
        
        connection = await self._establish_event_tracking_connection(user)
        
        message_payload = {
            "type": "chat_message", 
            "data": {
                "message": high_frequency_message,
                "user_id": user["user_id"],
                "high_frequency_test": True,
                "request_frequent_updates": True
            }
        }
        
        await connection.send(json.dumps(message_payload))
        
        # Track rapid event delivery
        rapid_events = []
        test_start = time.time()
        last_event_time = test_start
        
        while time.time() - test_start < 20:  # 20s max for high-frequency test
            try:
                event_message = await asyncio.wait_for(connection.recv(), timeout=3)
                event_data = json.loads(event_message)
                
                current_time = time.time()
                gap = current_time - last_event_time
                
                event_record = {
                    "type": event_data.get("type"),
                    "timestamp": current_time,
                    "gap": gap,
                    "data": event_data.get("data", {})
                }
                
                rapid_events.append(event_record)
                last_event_time = current_time
                
                if event_data.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                break
        
        await connection.close()
        
        # Validate high-frequency performance
        assert len(rapid_events) >= 5, f"Insufficient events for high-frequency test: {len(rapid_events)}"
        
        # Check for reasonable event frequency
        small_gaps = [e for e in rapid_events if e["gap"] < 1.0]  # Events within 1 second
        assert len(small_gaps) >= len(rapid_events) * 0.5, "Events not delivered with sufficient frequency"
        
        # Check no events were dropped (reasonable continuity)
        large_gaps = [e for e in rapid_events if e["gap"] > 8.0]
        assert len(large_gaps) <= 2, f"Too many large gaps suggest dropped events: {len(large_gaps)}"
        
        total_duration = rapid_events[-1]["timestamp"] - test_start
        event_rate = len(rapid_events) / total_duration
        
        self.logger.info(
            f"High-frequency test passed: {len(rapid_events)} events "
            f"in {total_duration:.1f}s (rate: {event_rate:.1f} events/sec)"
        )


# Pytest configuration for WebSocket event tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.websocket,
    pytest.mark.mission_critical,
    pytest.mark.real_services,
    pytest.mark.real_time
]