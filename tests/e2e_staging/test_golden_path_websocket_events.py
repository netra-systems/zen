"""Golden Path WebSocket Events E2E Staging Test Suite

PURPOSE: Verify all 5 critical WebSocket events work reliably for Issue #1182 WebSocket Manager SSOT Migration
BUSINESS VALUE: Protects $500K+ ARR Golden Path functionality through comprehensive event validation

This test suite MUST FAIL with current race conditions and PASS after SSOT consolidation.

CRITICAL: These tests follow claude.md requirements:
- E2E GCP staging only (NO Docker)
- Real staging environment validation
- Golden Path event sequence testing
- Race condition detection
"""

import asyncio
import unittest
import json
import time
import uuid
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import websockets
import aiohttp

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)

# Staging environment configuration
STAGING_WS_URL = "wss://backend.staging.netrasystems.ai/ws"
STAGING_API_URL = "https://backend.staging.netrasystems.ai"
STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"


class WebSocketEventType(Enum):
    """Critical WebSocket events for Golden Path."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


@dataclass
class EventSequence:
    """Tracks WebSocket event sequence for validation."""
    user_id: str
    session_id: str
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    events_expected: List[WebSocketEventType] = field(default_factory=list)
    race_conditions: List[str] = field(default_factory=list)
    timing_violations: List[str] = field(default_factory=list)
    sequence_violations: List[str] = field(default_factory=list)


class GoldenPathWebSocketEventsTests(SSotAsyncTestCase):
    """Test Golden Path WebSocket events in staging environment.
    
    These tests MUST FAIL with current race conditions in event delivery.
    After SSOT consolidation, they MUST PASS with reliable event sequences.
    """

    def setUp(self):
        """Set up test environment for Golden Path event testing."""
        super().setUp()
        self.event_sequences = {}
        self.race_condition_violations = []
        self.event_delivery_failures = []
        self.performance_violations = []
        
    async def asyncSetUp(self):
        """Async setup for staging environment testing."""
        await super().asyncSetUp()
        await self._validate_staging_environment()
        
    async def _validate_staging_environment(self) -> None:
        """Validate staging environment is accessible and functional."""
        try:
            # Test API connectivity
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STAGING_API_URL}/health") as response:
                    if response.status != 200:
                        self.fail(f"Staging API not accessible: {response.status}")
                    
                    health_data = await response.json()
                    logger.info(f"Staging API health: {health_data}")
            
            # Test WebSocket connectivity
            try:
                async with websockets.connect(STAGING_WS_URL, timeout=10) as websocket:
                    await websocket.send(json.dumps({"type": "ping"}))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    logger.info(f"WebSocket connectivity verified: {response}")
            except Exception as e:
                logger.warning(f"WebSocket pre-test failed (may be auth-protected): {e}")
            
        except Exception as e:
            self.fail(f"Staging environment validation failed: {e}")

    async def test_golden_path_event_sequence_integrity(self):
        """
        CRITICAL TEST: Verify all 5 Golden Path events are delivered in correct sequence
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Race conditions cause missing or out-of-order events
        - MUST PASS (after SSOT): All events delivered in correct sequence
        """
        logger.info("Testing Golden Path event sequence integrity...")
        
        try:
            # Create test user session
            user_id = f"test_golden_path_{uuid.uuid4().hex[:8]}"
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            event_sequence = EventSequence(
                user_id=user_id,
                session_id=session_id,
                events_expected=[
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.TOOL_EXECUTING,
                    WebSocketEventType.TOOL_COMPLETED,
                    WebSocketEventType.AGENT_COMPLETED
                ]
            )
            
            # Authenticate and establish WebSocket connection
            auth_token = await self._authenticate_staging_user(user_id)
            
            # Connect to WebSocket and trigger Golden Path
            async with websockets.connect(
                f"{STAGING_WS_URL}",
                additional_headers={"Authorization": f"Bearer {auth_token}"}
            ) as websocket:
                
                # Start event collection
                event_collection_task = asyncio.create_task(
                    self._collect_websocket_events(websocket, event_sequence)
                )
                
                # Trigger Golden Path user flow
                golden_path_message = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": "Analyze the current market trends and provide investment recommendations",
                    "request_id": f"req_{uuid.uuid4().hex[:8]}"
                }
                
                await websocket.send(json.dumps(golden_path_message))
                logger.info(f"Triggered Golden Path for user {user_id}")
                
                # Wait for event collection (with timeout)
                try:
                    await asyncio.wait_for(event_collection_task, timeout=30)
                except asyncio.TimeoutError:
                    event_sequence.race_conditions.append("Event collection timed out after 30 seconds")
            
            # Validate event sequence
            self._validate_event_sequence(event_sequence)
            
            # ASSERTION: This MUST FAIL currently (proving race conditions)
            # After SSOT consolidation, this MUST PASS (reliable event delivery)
            total_violations = (len(event_sequence.race_conditions) + 
                              len(event_sequence.timing_violations) + 
                              len(event_sequence.sequence_violations))
            
            self.assertEqual(total_violations, 0,
                           f"GOLDEN PATH EVENT VIOLATIONS: Found {total_violations} violations. "
                           f"Race conditions: {event_sequence.race_conditions}. "
                           f"Timing violations: {event_sequence.timing_violations}. "
                           f"Sequence violations: {event_sequence.sequence_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test Golden Path event sequence: {e}")

    async def _authenticate_staging_user(self, user_id: str) -> str:
        """Authenticate user with staging auth service."""
        try:
            # Create test user authentication
            auth_payload = {
                "user_id": user_id,
                "email": f"{user_id}@test.netrasystems.ai",
                "test_user": True,
                "permissions": ["chat", "ai_interaction"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STAGING_AUTH_URL}/auth/test-token",
                    json=auth_payload
                ) as response:
                    if response.status != 200:
                        # Try alternative auth method
                        return "test_token_for_staging"
                    
                    auth_data = await response.json()
                    return auth_data.get("access_token", "test_token_for_staging")
                    
        except Exception as e:
            logger.warning(f"Auth failed, using test token: {e}")
            return "test_token_for_staging"

    async def _collect_websocket_events(self, websocket, event_sequence: EventSequence) -> None:
        """Collect WebSocket events and track timing/sequence."""
        start_time = time.time()
        last_event_time = start_time
        
        try:
            while True:
                try:
                    # Wait for event with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    current_time = time.time()
                    
                    try:
                        event_data = json.loads(message)
                        event_type = event_data.get("type", "unknown")
                        
                        # Track event timing
                        event_info = {
                            "type": event_type,
                            "timestamp": current_time,
                            "time_since_start": current_time - start_time,
                            "time_since_last": current_time - last_event_time,
                            "data": event_data
                        }
                        
                        event_sequence.events_received.append(event_info)
                        last_event_time = current_time
                        
                        logger.info(f"Received event: {event_type} at {event_info['time_since_start']:.2f}s")
                        
                        # Check if this completes the Golden Path sequence
                        if event_type == WebSocketEventType.AGENT_COMPLETED.value:
                            logger.info("Golden Path sequence completed")
                            break
                            
                    except json.JSONDecodeError:
                        event_sequence.race_conditions.append(f"Invalid JSON received: {message}")
                        
                except asyncio.TimeoutError:
                    # Check if we have all expected events
                    received_types = [e["type"] for e in event_sequence.events_received]
                    expected_types = [e.value for e in event_sequence.events_expected]
                    
                    missing_events = set(expected_types) - set(received_types)
                    if missing_events:
                        event_sequence.race_conditions.append(f"Missing events after timeout: {missing_events}")
                    break
                    
        except Exception as e:
            event_sequence.race_conditions.append(f"Event collection error: {e}")

    def _validate_event_sequence(self, event_sequence: EventSequence) -> None:
        """Validate the received event sequence against Golden Path requirements."""
        received_events = event_sequence.events_received
        expected_events = event_sequence.events_expected
        
        # Check for missing events
        received_types = [e["type"] for e in received_events]
        expected_types = [e.value for e in expected_events]
        
        missing_events = set(expected_types) - set(received_types)
        if missing_events:
            event_sequence.sequence_violations.append(f"Missing events: {missing_events}")
        
        # Check event order
        expected_order = [e.value for e in expected_events]
        received_order = [e["type"] for e in received_events if e["type"] in expected_order]
        
        if received_order != expected_order:
            event_sequence.sequence_violations.append(
                f"Event order violation: expected {expected_order}, got {received_order}"
            )
        
        # Check timing constraints
        for i, event in enumerate(received_events):
            # Events should not arrive too quickly (indicates race conditions)
            if i > 0 and event["time_since_last"] < 0.01:  # Less than 10ms between events
                event_sequence.timing_violations.append(
                    f"Events too close together: {event['type']} only {event['time_since_last']*1000:.1f}ms after previous"
                )
            
            # Events should not take too long (indicates blocking)
            if event["time_since_start"] > 25:  # More than 25 seconds total
                event_sequence.timing_violations.append(
                    f"Event {event['type']} took too long: {event['time_since_start']:.2f}s"
                )

    async def test_concurrent_user_event_isolation(self):
        """
        CRITICAL TEST: Verify WebSocket events are properly isolated between concurrent users
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Events leak between users due to shared manager state
        - MUST PASS (after SSOT): Complete event isolation per user
        """
        logger.info("Testing concurrent user event isolation...")
        
        try:
            # Create multiple concurrent users
            num_users = 3
            user_sessions = []
            
            for i in range(num_users):
                user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"
                session_id = f"session_{i}_{uuid.uuid4().hex[:8]}"
                
                user_sessions.append({
                    'user_id': user_id,
                    'session_id': session_id,
                    'events': [],
                    'violations': []
                })
            
            # Start concurrent Golden Path flows
            tasks = []
            for session in user_sessions:
                task = asyncio.create_task(
                    self._run_concurrent_golden_path(session)
                )
                tasks.append(task)
            
            # Wait for all concurrent flows to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze for event contamination between users
            contamination_violations = []
            
            for i, session1 in enumerate(user_sessions):
                for j, session2 in enumerate(user_sessions):
                    if i == j:
                        continue
                    
                    # Check if session1 received events meant for session2
                    for event in session1['events']:
                        event_user_id = event.get('data', {}).get('user_id')
                        if event_user_id and event_user_id == session2['user_id']:
                            contamination_violations.append(
                                f"User {session1['user_id']} received event for user {session2['user_id']}: {event['type']}"
                            )
            
            # Collect all violations
            all_violations = contamination_violations
            for session in user_sessions:
                all_violations.extend(session['violations'])
            
            # ASSERTION: This MUST FAIL currently (proving event contamination)
            # After SSOT consolidation, this MUST PASS (isolated event delivery)
            self.assertEqual(len(all_violations), 0,
                           f"CONCURRENT USER EVENT VIOLATIONS: Found {len(all_violations)} violations. "
                           f"Violations: {all_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test concurrent user event isolation: {e}")

    async def _run_concurrent_golden_path(self, session: Dict[str, Any]) -> None:
        """Run Golden Path flow for a specific user session."""
        try:
            user_id = session['user_id']
            session_id = session['session_id']
            
            # Authenticate user
            auth_token = await self._authenticate_staging_user(user_id)
            
            # Connect to WebSocket
            async with websockets.connect(
                f"{STAGING_WS_URL}",
                additional_headers={"Authorization": f"Bearer {auth_token}"}
            ) as websocket:
                
                # Start event collection
                event_task = asyncio.create_task(
                    self._collect_concurrent_events(websocket, session)
                )
                
                # Trigger Golden Path
                message = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": f"User {user_id} specific query for market analysis",
                    "request_id": f"req_{user_id}_{uuid.uuid4().hex[:8]}"
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for events with timeout
                try:
                    await asyncio.wait_for(event_task, timeout=20)
                except asyncio.TimeoutError:
                    session['violations'].append(f"User {user_id} event collection timed out")
                    
        except Exception as e:
            session['violations'].append(f"User {user_id} concurrent flow failed: {e}")

    async def _collect_concurrent_events(self, websocket, session: Dict[str, Any]) -> None:
        """Collect events for concurrent user session."""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3)
                    event_data = json.loads(message)
                    
                    session['events'].append({
                        "type": event_data.get("type", "unknown"),
                        "timestamp": time.time(),
                        "data": event_data
                    })
                    
                    # Stop on completion
                    if event_data.get("type") == WebSocketEventType.AGENT_COMPLETED.value:
                        break
                        
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    session['violations'].append("Invalid JSON in concurrent event")
                    
        except Exception as e:
            session['violations'].append(f"Concurrent event collection error: {e}")

    async def test_websocket_manager_recovery_after_failure(self):
        """
        CRITICAL TEST: Verify WebSocket manager recovery mechanisms work properly
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Failures cascade and prevent recovery
        - MUST PASS (after SSOT): Graceful recovery with continued event delivery
        """
        logger.info("Testing WebSocket manager recovery after failure...")
        
        try:
            user_id = f"recovery_test_{uuid.uuid4().hex[:8]}"
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            recovery_violations = []
            
            # Establish initial connection
            auth_token = await self._authenticate_staging_user(user_id)
            
            async with websockets.connect(
                f"{STAGING_WS_URL}",
                additional_headers={"Authorization": f"Bearer {auth_token}"}
            ) as websocket:
                
                # Send initial message
                initial_message = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": "Initial test message",
                    "request_id": f"req_initial_{uuid.uuid4().hex[:8]}"
                }
                
                await websocket.send(json.dumps(initial_message))
                
                # Collect initial events
                initial_events = []
                try:
                    for _ in range(3):  # Collect a few events
                        message = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event = json.loads(message)
                        initial_events.append(event)
                except asyncio.TimeoutError:
                    recovery_violations.append("Failed to receive initial events")
                
                # Simulate connection disruption by sending invalid data
                try:
                    await websocket.send("invalid_json_data")
                except Exception:
                    pass  # Expected to cause issues
                
                # Try to recover with new message
                recovery_message = {
                    "type": "chat_message",
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": "Recovery test message",
                    "request_id": f"req_recovery_{uuid.uuid4().hex[:8]}"
                }
                
                try:
                    await websocket.send(json.dumps(recovery_message))
                    
                    # Check if we can still receive events
                    recovery_events = []
                    for _ in range(2):
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            recovery_events.append(event)
                        except asyncio.TimeoutError:
                            recovery_violations.append("Recovery event timeout")
                            break
                    
                    if len(recovery_events) == 0:
                        recovery_violations.append("No events received after recovery attempt")
                        
                except Exception as e:
                    recovery_violations.append(f"Failed to send recovery message: {e}")
            
            # ASSERTION: This MUST FAIL currently (proving poor recovery)
            # After SSOT consolidation, this MUST PASS (robust recovery)
            self.assertEqual(len(recovery_violations), 0,
                           f"WEBSOCKET RECOVERY VIOLATIONS: Found {len(recovery_violations)} recovery issues. "
                           f"Violations: {recovery_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test WebSocket recovery: {e}")

    def tearDown(self):
        """Clean up after Golden Path event tests."""
        super().tearDown()
        logger.info("Golden Path WebSocket event testing completed")
        logger.info(f"Event sequences tested: {len(self.event_sequences)}")
        logger.info(f"Race condition violations: {len(self.race_condition_violations)}")
        logger.info(f"Event delivery failures: {len(self.event_delivery_failures)}")


if __name__ == '__main__':
    unittest.main()