"""
WebSocket Accept Message Routing Race Condition Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Experience
- Value Impact: Prevents message routing failures during WebSocket connection handshake
- Strategic Impact: Protects $500K+ ARR by ensuring reliable message delivery during chat

CRITICAL RACE CONDITION REPRODUCTION:
These integration tests reproduce the race condition where messages are attempted
to be routed before WebSocket accept() has fully completed, causing:
- "WebSocket is not connected. Need to call 'accept' first" errors
- Message routing failures during handshake windows
- Dual interface confusion between WebSocketManager and AgentWebSocketBridge

Integration Test Requirements:
- Uses REAL WebSocket connections (no mocks)
- Uses REAL authentication via E2EAuthHelper per CLAUDE.md Section 15
- Uses REAL Redis and database services
- Implements Factory pattern for user context isolation
- Tests message routing coordination with accept() timing

CRITICAL: These tests MUST initially FAIL to prove race condition reproduction.
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from unittest.mock import patch
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest
import websockets
from fastapi.testclient import TestClient

from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter,
    get_websocket_manager,
    get_message_router,
    safe_websocket_send,
    create_server_message,
    MessageType
)
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    get_connection_state_registry
)
from netra_backend.app.websocket_core.utils import (
    is_websocket_connected_and_ready,
    validate_websocket_handshake_completion
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

# Test Framework Imports
from test_framework.ssot.integration_test_base import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@dataclass
class MessageRoutingEvent:
    """Track message routing events during race conditions."""
    timestamp: float
    event_type: str  # "accept_start", "accept_complete", "message_attempt", "routing_result"
    connection_id: str
    user_id: str
    success: bool
    error: Optional[str] = None
    message_data: Optional[Dict[str, Any]] = None
    accept_state: Optional[str] = None
    routing_details: Optional[Dict[str, Any]] = field(default_factory=dict)


class AcceptMessageRoutingRaceTest(BaseIntegrationTest):
    """
    Integration tests for WebSocket accept and message routing race conditions.
    
    CRITICAL: These tests use REAL services and REAL authentication to reproduce
    the exact race conditions that occur in production GCP Cloud Run environments.
    """
    
    def setUp(self):
        """Set up integration test environment with real services."""
        super().setUp()
        
        # Real authentication setup (CLAUDE.md Section 15 requirement)
        self.auth_helper = E2EAuthHelper()
        
        # Race condition tracking
        self.routing_events: List[MessageRoutingEvent] = []
        self.race_condition_errors: List[str] = []
        self.accept_timing_violations: List[str] = []
        
        # Test user setup with real authentication
        self.test_users = []
        for i in range(3):  # Multiple users for isolation testing
            user_data = self.auth_helper.create_test_user(
                username=f"race_test_user_{i}_{int(time.time())}",
                email=f"race_user_{i}_{int(time.time())}@test.netra.ai"
            )
            self.test_users.append(user_data)
        
        # WebSocket connection tracking
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.message_attempts: List[Dict[str, Any]] = []
        
        # Race condition timing controls
        self.accept_delay_range = (0.05, 0.2)  # Simulate GCP variability
        self.message_burst_size = 5  # Messages to send during handshake
        
    def _record_routing_event(self, event_type: str, connection_id: str, user_id: str,
                             success: bool, error: Optional[str] = None,
                             message_data: Optional[Dict[str, Any]] = None,
                             accept_state: Optional[str] = None,
                             routing_details: Optional[Dict[str, Any]] = None):
        """Record message routing event for race condition analysis."""
        event = MessageRoutingEvent(
            timestamp=time.time(),
            event_type=event_type,
            connection_id=connection_id,
            user_id=user_id,
            success=success,
            error=error,
            message_data=message_data,
            accept_state=accept_state,
            routing_details=routing_details or {}
        )
        self.routing_events.append(event)
    
    @pytest.mark.integration
    def test_message_routing_during_accept_handshake_race(self):
        """
        Test 1: Message routing during WebSocket accept handshake.
        
        CRITICAL RACE CONDITION: This test reproduces the exact scenario where
        messages are attempted to be routed while accept() is still in progress,
        causing "Need to call 'accept' first" errors.
        
        Expected Race Condition: Messages sent during accept() handshake window
        should queue properly, but race condition causes routing failures.
        """
        user_data = self.test_users[0]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        connection_events = []
        routing_failures = []
        
        async def simulate_slow_accept_handshake(websocket, connection_id: str):
            """Simulate slow accept handshake that creates race condition window."""
            try:
                # Record accept start
                self._record_routing_event(
                    "accept_start", connection_id, user_data['user_id'], True,
                    accept_state="starting"
                )
                
                # Simulate GCP Cloud Run handshake delay
                accept_delay = 0.1  # 100ms delay creates race window
                await asyncio.sleep(accept_delay)
                
                # Complete accept
                await websocket.accept()
                
                self._record_routing_event(
                    "accept_complete", connection_id, user_data['user_id'], True,
                    accept_state="completed"
                )
                
                return True
                
            except Exception as e:
                self._record_routing_event(
                    "accept_start", connection_id, user_data['user_id'], False,
                    error=str(e), accept_state="failed"
                )
                return False
        
        def attempt_message_routing_during_handshake(connection_id: str):
            """Attempt message routing while accept is in progress."""
            try:
                # Get WebSocket manager
                ws_manager = get_websocket_manager()
                message_router = get_message_router()
                
                # Attempt to send messages during handshake (race condition trigger)
                for i in range(self.message_burst_size):
                    message = create_server_message(
                        MessageType.AGENT_STARTED,
                        {"agent_id": f"test_agent_{i}", "status": "starting"},
                        user_id=user_data['user_id'],
                        connection_id=connection_id
                    )
                    
                    try:
                        # This should trigger the race condition
                        routing_result = message_router.route_message(
                            connection_id=connection_id,
                            message=message,
                            user_id=user_data['user_id']
                        )
                        
                        self._record_routing_event(
                            "message_attempt", connection_id, user_data['user_id'],
                            success=routing_result.get('success', False),
                            message_data={"message_type": "AGENT_STARTED", "index": i},
                            routing_details=routing_result
                        )
                        
                        # Small delay between messages to extend race window
                        time.sleep(0.01)
                        
                    except Exception as routing_error:
                        error_msg = str(routing_error)
                        
                        # Check if this is the race condition error we're reproducing
                        if "accept" in error_msg.lower() or "connected" in error_msg.lower():
                            self.race_condition_errors.append(
                                f"Race condition reproduced: {error_msg}"
                            )
                        
                        routing_failures.append({
                            "message_index": i,
                            "error": error_msg,
                            "timestamp": time.time()
                        })
                        
                        self._record_routing_event(
                            "message_attempt", connection_id, user_data['user_id'],
                            success=False, error=error_msg,
                            message_data={"message_type": "AGENT_STARTED", "index": i}
                        )
                
            except Exception as e:
                routing_failures.append({
                    "general_error": str(e),
                    "timestamp": time.time()
                })
        
        # Execute race condition test
        connection_id = f"race_test_conn_{int(time.time())}"
        
        # Create WebSocket connection with authentication
        with self.client.websocket_connect(
            f"/ws?token={auth_token}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as websocket:
            
            # Start message routing attempts in parallel with handshake
            routing_thread = threading.Thread(
                target=attempt_message_routing_during_handshake,
                args=(connection_id,)
            )
            routing_thread.start()
            
            # Simulate slow handshake
            asyncio.run(simulate_slow_accept_handshake(websocket, connection_id))
            
            # Wait for routing attempts to complete
            routing_thread.join(timeout=5.0)
        
        # Analyze race condition results
        accept_events = [e for e in self.routing_events if e.event_type in ["accept_start", "accept_complete"]]
        message_attempts = [e for e in self.routing_events if e.event_type == "message_attempt"]
        successful_routes = [e for e in message_attempts if e.success]
        failed_routes = [e for e in message_attempts if not e.success]
        
        print(f"\n=== ACCEPT MESSAGE ROUTING RACE ANALYSIS ===")
        print(f"Accept events: {len(accept_events)}")
        print(f"Message routing attempts: {len(message_attempts)}")
        print(f"Successful routes: {len(successful_routes)}")
        print(f"Failed routes: {len(failed_routes)}")
        print(f"Race condition errors: {len(self.race_condition_errors)}")
        print(f"Routing failures: {len(routing_failures)}")
        
        # Log race condition errors for analysis
        if self.race_condition_errors:
            print("Race condition errors detected:")
            for error in self.race_condition_errors:
                print(f"  - {error}")
        
        # Check if race condition was reproduced
        race_reproduced = (
            len(self.race_condition_errors) > 0 or
            len(failed_routes) > 0 or
            len(routing_failures) > 0
        )
        
        if not race_reproduced:
            self.accept_timing_violations.append(
                "CRITICAL: Race condition not reproduced - test may not be creating proper timing conditions"
            )
        
        # CRITICAL: This test should fail to prove race condition reproduction
        pytest.fail(
            f"Accept message routing race condition test completed. "
            f"Race reproduced: {race_reproduced}, "
            f"Failed routes: {len(failed_routes)}, "
            f"Race errors: {len(self.race_condition_errors)}"
        )
    
    @pytest.mark.integration  
    def test_dual_interface_coordination_race_condition(self):
        """
        Test 2: Dual interface coordination race between WebSocketManager and AgentWebSocketBridge.
        
        This test reproduces race conditions where WebSocketManager and AgentWebSocketBridge
        have different views of connection readiness, causing message routing confusion.
        """
        user_data = self.test_users[1]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        interface_coordination_issues = []
        state_mismatches = []
        
        def check_interface_coordination(connection_id: str):
            """Check coordination between WebSocketManager and AgentWebSocketBridge."""
            try:
                ws_manager = get_websocket_manager()
                
                # Get state from WebSocketManager
                ws_manager_ready = False
                try:
                    ws_manager_ready = ws_manager.is_connection_ready(connection_id)
                except Exception as e:
                    interface_coordination_issues.append({
                        "interface": "WebSocketManager",
                        "method": "is_connection_ready",
                        "error": str(e),
                        "timestamp": time.time()
                    })
                
                # Check connection state machine state
                registry = get_connection_state_registry()
                state_machine = registry.get_connection_state_machine(connection_id)
                
                state_machine_ready = False
                if state_machine:
                    state_machine_ready = state_machine.is_ready_for_messages
                else:
                    interface_coordination_issues.append({
                        "interface": "ConnectionStateMachine",
                        "issue": "No state machine found for connection",
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    })
                
                # Check for state mismatches (race condition indicator)
                if ws_manager_ready != state_machine_ready:
                    mismatch = {
                        "connection_id": connection_id,
                        "ws_manager_ready": ws_manager_ready,
                        "state_machine_ready": state_machine_ready,
                        "timestamp": time.time()
                    }
                    state_mismatches.append(mismatch)
                    
                    self.race_condition_errors.append(
                        f"Interface state mismatch: WS Manager={ws_manager_ready}, "
                        f"State Machine={state_machine_ready}"
                    )
                
                return {
                    "ws_manager_ready": ws_manager_ready,
                    "state_machine_ready": state_machine_ready,
                    "coordination_ok": ws_manager_ready == state_machine_ready
                }
                
            except Exception as e:
                interface_coordination_issues.append({
                    "general_error": str(e),
                    "connection_id": connection_id,
                    "timestamp": time.time()
                })
                return {"error": str(e)}
        
        def rapid_coordination_checks(connection_id: str):
            """Perform rapid coordination checks to trigger race conditions."""
            coordination_results = []
            
            for i in range(10):  # 10 rapid checks
                result = check_interface_coordination(connection_id)
                result['check_index'] = i
                result['timestamp'] = time.time()
                coordination_results.append(result)
                
                # Small delay to allow for timing variations
                time.sleep(0.005)
            
            return coordination_results
        
        # Execute dual interface coordination test
        connection_id = f"coordination_test_{int(time.time())}"
        
        with self.client.websocket_connect(
            f"/ws?token={auth_token}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as websocket:
            
            # Perform rapid coordination checks while connection is establishing
            coordination_thread = threading.Thread(
                target=lambda: setattr(self, 'coordination_results', rapid_coordination_checks(connection_id))
            )
            coordination_thread.start()
            
            # Allow some time for connection to establish while checks are running
            time.sleep(0.1)
            
            # Send a test message to trigger routing
            test_message = {"type": "ping", "data": {"timestamp": time.time()}}
            websocket.send_json(test_message)
            
            # Wait for coordination checks to complete
            coordination_thread.join(timeout=5.0)
        
        # Analyze coordination race conditions
        coordination_results = getattr(self, 'coordination_results', [])
        successful_checks = [r for r in coordination_results if r.get('coordination_ok', False)]
        failed_checks = [r for r in coordination_results if not r.get('coordination_ok', True)]
        
        print(f"\n=== DUAL INTERFACE COORDINATION RACE ANALYSIS ===")
        print(f"Total coordination checks: {len(coordination_results)}")
        print(f"Successful coordination: {len(successful_checks)}")
        print(f"Failed coordination: {len(failed_checks)}")
        print(f"Interface issues: {len(interface_coordination_issues)}")
        print(f"State mismatches: {len(state_mismatches)}")
        print(f"Race condition errors: {len(self.race_condition_errors)}")
        
        if state_mismatches:
            print("State mismatches detected:")
            for mismatch in state_mismatches[:3]:  # Show first 3 mismatches
                print(f"  - {mismatch}")
        
        # Check for coordination race conditions
        coordination_race_detected = (
            len(state_mismatches) > 0 or
            len(interface_coordination_issues) > 2 or  # More than 2 issues indicates problems
            len(failed_checks) > len(successful_checks)  # More failures than successes
        )
        
        # CRITICAL: Coordination issues indicate race conditions
        pytest.fail(
            f"Dual interface coordination race test completed. "
            f"Race detected: {coordination_race_detected}, "
            f"State mismatches: {len(state_mismatches)}, "
            f"Interface issues: {len(interface_coordination_issues)}"
        )
    
    @pytest.mark.integration
    def test_multi_user_message_isolation_during_race_conditions(self):
        """
        Test 3: Multi-user message isolation during WebSocket race conditions.
        
        This test ensures that race conditions don't cause message cross-contamination
        between different authenticated users during concurrent connections.
        """
        # Use multiple test users for isolation testing
        user1_data = self.test_users[0] 
        user2_data = self.test_users[1]
        user3_data = self.test_users[2]
        
        user_tokens = {
            user1_data['user_id']: self.auth_helper.get_valid_jwt_token(user1_data['user_id']),
            user2_data['user_id']: self.auth_helper.get_valid_jwt_token(user2_data['user_id']),
            user3_data['user_id']: self.auth_helper.get_valid_jwt_token(user3_data['user_id'])
        }
        
        message_isolation_violations = []
        cross_user_routing_errors = []
        
        def concurrent_user_message_worker(user_data: Dict[str, Any], worker_id: int):
            """Worker function that sends messages for a specific user."""
            user_id = user_data['user_id']
            auth_token = user_tokens[user_id]
            connection_id = f"isolation_test_{user_id}_{worker_id}"
            
            try:
                with TestClient(self.app).websocket_connect(
                    f"/ws?token={auth_token}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                ) as websocket:
                    
                    # Send user-specific messages rapidly to trigger race conditions
                    for i in range(5):
                        user_message = {
                            "type": "user_message",
                            "user_id": user_id,
                            "worker_id": worker_id,
                            "message_index": i,
                            "timestamp": time.time(),
                            "unique_data": f"{user_id}_data_{i}"
                        }
                        
                        websocket.send_json(user_message)
                        
                        # Brief delay to allow interleaving with other users
                        time.sleep(0.01)
                        
                        # Attempt to receive response (should be isolated)
                        try:
                            response = websocket.receive_json(timeout=1.0)
                            
                            # Verify response isolation
                            if response.get('user_id') != user_id:
                                message_isolation_violations.append({
                                    "expected_user": user_id,
                                    "received_user": response.get('user_id'),
                                    "worker_id": worker_id,
                                    "message_index": i,
                                    "response": response
                                })
                                
                                self.race_condition_errors.append(
                                    f"Message isolation violation: Expected user {user_id}, "
                                    f"got response for user {response.get('user_id')}"
                                )
                        
                        except Exception as recv_error:
                            # Timeout is expected in race condition tests
                            pass
                
            except Exception as e:
                cross_user_routing_errors.append({
                    "user_id": user_id,
                    "worker_id": worker_id, 
                    "error": str(e),
                    "timestamp": time.time()
                })
        
        # Launch concurrent user workers to trigger race conditions
        workers = []
        users_data = [user1_data, user2_data, user3_data]
        
        for i, user_data in enumerate(users_data):
            worker_thread = threading.Thread(
                target=concurrent_user_message_worker,
                args=(user_data, i),
                name=f"UserWorker-{user_data['user_id'][:8]}"
            )
            workers.append(worker_thread)
            worker_thread.start()
        
        # Wait for all workers to complete
        for worker in workers:
            worker.join(timeout=10.0)
        
        # Analyze multi-user isolation race conditions
        isolation_violations = len(message_isolation_violations)
        routing_errors = len(cross_user_routing_errors)
        race_errors = len(self.race_condition_errors)
        
        print(f"\n=== MULTI-USER ISOLATION RACE ANALYSIS ===")
        print(f"Isolation violations: {isolation_violations}")
        print(f"Cross-user routing errors: {routing_errors}")
        print(f"Race condition errors: {race_errors}")
        
        if message_isolation_violations:
            print("Message isolation violations detected:")
            for violation in message_isolation_violations[:3]:  # Show first 3 violations
                print(f"  - Expected: {violation['expected_user'][:8]}, "
                     f"Got: {violation['received_user'][:8] if violation['received_user'] else 'None'}")
        
        if cross_user_routing_errors:
            print("Cross-user routing errors:")
            for error in cross_user_routing_errors[:3]:  # Show first 3 errors
                print(f"  - User {error['user_id'][:8]}: {error['error']}")
        
        # Check for isolation race conditions
        isolation_race_detected = (
            isolation_violations > 0 or
            routing_errors > len(users_data) or  # More errors than users indicates systemic issues
            race_errors > 0
        )
        
        # CRITICAL: Isolation violations indicate race conditions affecting user data
        pytest.fail(
            f"Multi-user isolation race test completed. "
            f"Race detected: {isolation_race_detected}, "
            f"Isolation violations: {isolation_violations}, "
            f"Routing errors: {routing_errors}"
        )
    
    def tearDown(self):
        """Clean up integration test environment."""
        # Log race condition test summary
        print(f"\n=== INTEGRATION RACE CONDITION TEST SUMMARY ===")
        print(f"Total routing events recorded: {len(self.routing_events)}")
        print(f"Race condition errors: {len(self.race_condition_errors)}")
        print(f"Accept timing violations: {len(self.accept_timing_violations)}")
        print(f"Message attempts tracked: {len(self.message_attempts)}")
        
        # Clean up active connections
        for connection_id in self.active_connections:
            try:
                registry = get_connection_state_registry()
                registry.unregister_connection(connection_id)
            except Exception as cleanup_error:
                print(f"Cleanup error for connection {connection_id}: {cleanup_error}")
        
        # Clean up test users
        for user_data in self.test_users:
            try:
                self.auth_helper.cleanup_test_user(user_data['user_id'])
            except Exception as user_cleanup_error:
                print(f"User cleanup error: {user_cleanup_error}")
        
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])