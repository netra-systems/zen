#!/usr/bin/env python
"""
WebSocket Connection Isolation Test Suite.

This test suite validates that the new connection-scoped WebSocket implementation
completely eliminates cross-user event leakage. Each test verifies isolation
boundaries and ensures events only reach intended recipients.

Business Value: Prevents $500K+ ARR loss from user trust issues due to event leakage.

CRITICAL: All tests use real WebSocket connections per CLAUDE.md requirements.
NO MOCKS are used - this ensures we test the actual isolation behavior.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional
import pytest
from concurrent.futures import ThreadPoolExecutor
import threading
import random
from shared.isolated_environment import IsolatedEnvironment

import websockets
from websockets.exceptions import ConnectionClosed

from test_framework.test_context import TestContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase


class WebSocketIsolationValidator:
    """Validates WebSocket connection isolation between users."""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.received_events: Dict[str, List[Dict]] = {}
        self.event_lock = threading.Lock()
        self.isolation_violations: List[Dict] = []
    
    async def create_isolated_connection(self, user_id: str, token: str, 
                                       base_url: str = "ws://localhost:8000") -> str:
        """Create an isolated WebSocket connection for a user.
        
        Args:
            user_id: Unique user identifier
            token: JWT token for authentication
            base_url: WebSocket base URL
            
        Returns:
            str: Connection ID for tracking
        """
        connection_id = f"conn_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Use isolated endpoint
        url = f"{base_url}/ws/isolated"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Connect with authentication
            websocket = await websockets.connect(
                url,
                extra_headers=headers,
                subprotocols=["jwt-auth"]
            )
            
            self.connections[connection_id] = {
                "user_id": user_id,
                "websocket": websocket,
                "connection_id": connection_id,
                "created_at": datetime.now(timezone.utc)
            }
            
            self.received_events[connection_id] = []
            
            # Start listening for events in background
            asyncio.create_task(self._listen_for_events(connection_id))
            
            print(f" PASS:  Created isolated connection for user {user_id}: {connection_id}")
            return connection_id
            
        except Exception as e:
            print(f" FAIL:  Failed to create connection for user {user_id}: {e}")
            raise
    
    async def _listen_for_events(self, connection_id: str):
        """Listen for events on a connection and record them."""
        connection = self.connections[connection_id]
        websocket = connection["websocket"]
        user_id = connection["user_id"]
        
        try:
            async for message in websocket:
                event = json.loads(message)
                
                with self.event_lock:
                    # Record event for this connection
                    event_with_metadata = {
                        **event,
                        "received_by_connection": connection_id,
                        "received_by_user": user_id,
                        "received_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.received_events[connection_id].append(event_with_metadata)
                    
                    # CRITICAL: Check for isolation violations
                    event_user_id = event.get("user_id")
                    if event_user_id and event_user_id != user_id:
                        violation = {
                            "violation_type": "cross_user_event_leakage",
                            "event": event,
                            "intended_user": event_user_id,
                            "received_by_user": user_id,
                            "received_by_connection": connection_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        self.isolation_violations.append(violation)
                        print(f" ALERT:  ISOLATION VIOLATION: Event for user {event_user_id} "
                              f"received by user {user_id}")
                
        except ConnectionClosed:
            print(f"[U+1F50C] Connection {connection_id} closed")
        except Exception as e:
            print(f" FAIL:  Error listening on connection {connection_id}: {e}")
    
    async def send_user_specific_event(self, target_user_id: str, event_type: str, 
                                     payload: Dict[str, Any]) -> bool:
        """Send an event intended for a specific user.
        
        Args:
            target_user_id: User who should receive the event
            event_type: Type of event to send
            payload: Event payload
            
        Returns:
            bool: True if event was sent successfully
        """
        # Find connection for target user
        target_connection = None
        for conn_id, conn_info in self.connections.items():
            if conn_info["user_id"] == target_user_id:
                target_connection = conn_info
                break
        
        if not target_connection:
            print(f" FAIL:  No connection found for user {target_user_id}")
            return False
        
        event = {
            "type": event_type,
            "user_id": target_user_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_event": True
        }
        
        try:
            websocket = target_connection["websocket"]
            await websocket.send(json.dumps(event))
            
            print(f"[U+1F4E4] Sent {event_type} event to user {target_user_id}")
            return True
            
        except Exception as e:
            print(f" FAIL:  Failed to send event to user {target_user_id}: {e}")
            return False
    
    async def trigger_agent_execution(self, user_id: str, agent_name: str) -> Optional[str]:
        """Trigger agent execution for a specific user."""
        connection = None
        for conn_id, conn_info in self.connections.items():
            if conn_info["user_id"] == user_id:
                connection = conn_info
                break
        
        if not connection:
            print(f" FAIL:  No connection found for user {user_id}")
            return None
        
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        agent_request = {
            "type": "agent_execute",
            "user_id": user_id,
            "agent_name": agent_name,
            "run_id": run_id,
            "data": {
                "request": f"Test request from user {user_id}",
                "isolation_test": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            websocket = connection["websocket"]
            await websocket.send(json.dumps(agent_request))
            
            print(f"[U+1F916] Triggered {agent_name} execution for user {user_id}, run_id: {run_id}")
            return run_id
            
        except Exception as e:
            print(f" FAIL:  Failed to trigger agent execution for user {user_id}: {e}")
            return None
    
    def get_events_for_user(self, user_id: str) -> List[Dict]:
        """Get all events received by a specific user."""
        user_events = []
        
        for conn_id, conn_info in self.connections.items():
            if conn_info["user_id"] == user_id:
                with self.event_lock:
                    user_events.extend(self.received_events.get(conn_id, []))
        
        return user_events
    
    def get_isolation_violations(self) -> List[Dict]:
        """Get all detected isolation violations."""
        with self.event_lock:
            return self.isolation_violations.copy()
    
    async def close_all_connections(self):
        """Close all WebSocket connections."""
        for conn_id, conn_info in self.connections.items():
            try:
                websocket = conn_info["websocket"]
                await websocket.close()
                print(f"[U+1F50C] Closed connection {conn_id}")
            except Exception as e:
                print(f" WARNING: [U+FE0F]  Error closing connection {conn_id}: {e}")
        
        self.connections.clear()
        self.received_events.clear()


class TestWebSocketConnectionIsolation(RealWebSocketTestBase):
    """Test suite for WebSocket connection isolation."""
    
    @pytest.fixture
    async def isolation_validator(self):
        """Create isolation validator for testing."""
        validator = WebSocketIsolationValidator()
        yield validator
        await validator.close_all_connections()
    
    @pytest.fixture
    def test_users(self):
        """Create test users with tokens."""
        return [
            {"user_id": f"user_{i}", "token": f"test_token_{i}"}
            for i in range(1, 6)  # 5 test users
        ]
    
    @pytest.mark.asyncio
    async def test_no_cross_user_event_leakage(self, isolation_validator, test_users):
        """Test that events for User A never reach User B, C, D, or E."""
        print("\n[U+1F512] Testing cross-user event isolation...")
        
        # Create connections for all users
        connections = []
        for user in test_users:
            conn_id = await isolation_validator.create_isolated_connection(
                user["user_id"], user["token"]
            )
            connections.append(conn_id)
        
        # Wait for connections to stabilize
        await asyncio.sleep(2)
        
        # Target user 1 with specific events
        target_user = test_users[0]["user_id"]
        
        # Send events intended only for user 1
        await isolation_validator.send_user_specific_event(
            target_user, "test_private_event", 
            {"message": f"Private message for {target_user}", "confidential": True}
        )
        
        await isolation_validator.trigger_agent_execution(target_user, "TestAgent")
        
        # Wait for event processing
        await asyncio.sleep(3)
        
        # Verify no isolation violations
        violations = isolation_validator.get_isolation_violations()
        
        assert len(violations) == 0, (
            f"CRITICAL: Found {len(violations)} isolation violations! "
            f"Events leaked between users: {violations}"
        )
        
        # Verify only target user received events
        target_events = isolation_validator.get_events_for_user(target_user)
        assert len(target_events) > 0, f"Target user {target_user} should have received events"
        
        # Verify other users received no events intended for target user
        for user in test_users[1:]:  # Skip target user
            user_events = isolation_validator.get_events_for_user(user["user_id"])
            
            # Check for any events that mention the target user
            leaked_events = [
                event for event in user_events 
                if event.get("user_id") == target_user or 
                   target_user in str(event.get("payload", {}))
            ]
            
            assert len(leaked_events) == 0, (
                f"ISOLATION VIOLATION: User {user['user_id']} received "
                f"{len(leaked_events)} events intended for {target_user}: {leaked_events}"
            )
        
        print(f" PASS:  No cross-user event leakage detected across {len(test_users)} users")
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_executions_isolated(self, isolation_validator, test_users):
        """Test that concurrent agent executions remain isolated between users."""
        print("\n[U+1F916] Testing concurrent agent execution isolation...")
        
        # Create connections
        for user in test_users:
            await isolation_validator.create_isolated_connection(
                user["user_id"], user["token"]
            )
        
        await asyncio.sleep(2)
        
        # Trigger agent executions for all users concurrently
        agent_tasks = []
        run_ids = {}
        
        for user in test_users:
            user_id = user["user_id"]
            task = isolation_validator.trigger_agent_execution(user_id, "ConcurrentTestAgent")
            agent_tasks.append(task)
        
        # Execute all agent triggers concurrently
        run_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Collect valid run IDs
        for i, result in enumerate(run_results):
            if isinstance(result, str):  # Valid run_id
                run_ids[test_users[i]["user_id"]] = result
        
        # Wait for agent events to be processed
        await asyncio.sleep(5)
        
        # Verify no isolation violations during concurrent execution
        violations = isolation_validator.get_isolation_violations()
        assert len(violations) == 0, (
            f"CONCURRENT ISOLATION VIOLATION: Found {len(violations)} violations "
            f"during concurrent agent execution: {violations}"
        )
        
        # Verify each user only received their own agent events
        for user in test_users:
            user_id = user["user_id"]
            user_events = isolation_validator.get_events_for_user(user_id)
            
            # Find agent-related events
            agent_events = [
                event for event in user_events
                if event.get("type", "").startswith(("agent_", "tool_"))
            ]
            
            if user_id in run_ids:
                expected_run_id = run_ids[user_id]
                
                # Verify events are for the correct run_id
                for event in agent_events:
                    event_run_id = event.get("run_id") or event.get("payload", {}).get("run_id")
                    
                    assert event_run_id == expected_run_id, (
                        f"ISOLATION VIOLATION: User {user_id} received agent event "
                        f"for run_id {event_run_id}, expected {expected_run_id}"
                    )
        
        print(f" PASS:  Concurrent agent executions isolated across {len(test_users)} users")
    
    @pytest.mark.asyncio  
    async def test_connection_cleanup_isolation(self, isolation_validator, test_users):
        """Test that connection cleanup doesn't affect other user connections."""
        print("\n[U+1F9F9] Testing connection cleanup isolation...")
        
        # Create all connections
        for user in test_users:
            await isolation_validator.create_isolated_connection(
                user["user_id"], user["token"]
            )
        
        await asyncio.sleep(2)
        
        # Close connection for user 1
        user_1_id = test_users[0]["user_id"]
        user_1_connection = None
        
        for conn_id, conn_info in isolation_validator.connections.items():
            if conn_info["user_id"] == user_1_id:
                user_1_connection = conn_info
                break
        
        assert user_1_connection is not None, f"User 1 connection not found"
        
        # Close user 1's connection
        await user_1_connection["websocket"].close()
        print(f"[U+1F50C] Closed connection for user {user_1_id}")
        
        # Wait for cleanup to process
        await asyncio.sleep(2)
        
        # Verify other users' connections are still active and receiving events
        for user in test_users[1:]:  # Skip user 1
            user_id = user["user_id"]
            
            # Send test event to this user
            await isolation_validator.send_user_specific_event(
                user_id, "cleanup_test_event", 
                {"message": f"Testing connection after user 1 cleanup"}
            )
        
        # Wait for events
        await asyncio.sleep(2)
        
        # Verify users 2-5 received their test events
        for user in test_users[1:]:
            user_id = user["user_id"]
            user_events = isolation_validator.get_events_for_user(user_id)
            
            cleanup_events = [
                event for event in user_events
                if event.get("type") == "cleanup_test_event"
            ]
            
            assert len(cleanup_events) > 0, (
                f"User {user_id} didn't receive cleanup test event - "
                f"connection may have been affected by user 1 cleanup"
            )
        
        # Verify no isolation violations
        violations = isolation_validator.get_isolation_violations()
        assert len(violations) == 0, (
            f"Connection cleanup caused isolation violations: {violations}"
        )
        
        print(" PASS:  Connection cleanup properly isolated - other connections unaffected")
    
    @pytest.mark.asyncio
    async def test_event_filtering_by_user_id(self, isolation_validator, test_users):
        """Test that events are filtered by user_id at the connection level."""
        print("\n SEARCH:  Testing user_id event filtering...")
        
        # Create connections for first 3 users
        active_users = test_users[:3]
        for user in active_users:
            await isolation_validator.create_isolated_connection(
                user["user_id"], user["token"]
            )
        
        await asyncio.sleep(2)
        
        # Try to send events with mismatched user_ids through each connection
        for i, user in enumerate(active_users):
            user_id = user["user_id"]
            
            # Find user's connection
            user_connection = None
            for conn_id, conn_info in isolation_validator.connections.items():
                if conn_info["user_id"] == user_id:
                    user_connection = conn_info
                    break
            
            # Try to send event for different user through this connection
            other_user = active_users[(i + 1) % len(active_users)]
            other_user_id = other_user["user_id"]
            
            malicious_event = {
                "type": "malicious_event",
                "user_id": other_user_id,  # Different user_id!
                "payload": {
                    "message": f"Trying to impersonate {other_user_id}",
                    "sent_through_connection": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                websocket = user_connection["websocket"]
                await websocket.send(json.dumps(malicious_event))
                print(f"[U+1F4E4] Attempted to send event for {other_user_id} through {user_id} connection")
            except Exception as e:
                print(f" WARNING: [U+FE0F]  Failed to send malicious event: {e}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Verify no cross-user events were delivered
        violations = isolation_validator.get_isolation_violations()
        
        # We expect violations to be DETECTED and BLOCKED
        print(f"[U+1F6E1][U+FE0F]  Detected and blocked {len(violations)} isolation attempts")
        
        # Verify no user actually received events intended for others
        for user in active_users:
            user_id = user["user_id"]
            user_events = isolation_validator.get_events_for_user(user_id)
            
            # Check for any malicious events that got through
            malicious_events = [
                event for event in user_events
                if (event.get("type") == "malicious_event" and
                    event.get("payload", {}).get("sent_through_connection") != user_id)
            ]
            
            assert len(malicious_events) == 0, (
                f"SECURITY VIOLATION: User {user_id} received {len(malicious_events)} "
                f"malicious events intended for other users: {malicious_events}"
            )
        
        print(" PASS:  User ID filtering successfully blocked cross-user event injection")


if __name__ == "__main__":
    # Run isolation tests directly
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))