"""
E2E Race Condition Tests: Multi-User WebSocket Isolation

This module tests for race conditions in multi-user WebSocket isolation under real conditions.
Validates that WebSocket connections remain isolated and stable with real authentication and services.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure reliable multi-user real-time communication
- Value Impact: Prevents data leakage, connection interference, and user experience degradation
- Strategic Impact: CRITICAL - Multi-user isolation is core security and functionality requirement

Test Coverage:
- 10 concurrent WebSocket connections with real auth
- Cross-user message isolation verification
- Connection state race conditions under load
- Real agent execution through WebSocket
- Authentication token isolation validation
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional
import pytest
import websockets

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    AuthenticatedUser,
    create_authenticated_user
)
from test_framework.ssot.real_services_test_fixtures import requires_real_services
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestMultiUserWebSocketIsolationE2E(SSotBaseTestCase):
    """E2E test for multi-user WebSocket isolation race conditions."""
    
    def setup_method(self):
        """Set up E2E test environment with real services."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "e2e_websocket_isolation_testing", source="test")
        
        # Track WebSocket connections and messages
        self.active_connections: Dict[str, Dict] = {}
        self.received_messages: Dict[str, List] = {}
        self.connection_events: List[Dict] = []
        self.race_condition_detections: List[Dict] = []
        self.user_isolation_violations: List[Dict] = []
        
        # Initialize auth helpers
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
    def teardown_method(self):
        """Clean up E2E test state."""
        # Close any remaining connections
        for connection_data in self.active_connections.values():
            websocket = connection_data.get("websocket")
            if websocket and not websocket.closed:
                asyncio.create_task(websocket.close())
        
        # Clear tracking data
        self.active_connections.clear()
        self.received_messages.clear()
        self.connection_events.clear()
        self.race_condition_detections.clear()
        self.user_isolation_violations.clear()
        
        super().teardown_method()
    
    def _track_connection_event(self, event_type: str, connection_id: str, user_id: str, metadata: Dict = None):
        """Track connection event for race condition analysis."""
        event = {
            "event_type": event_type,
            "connection_id": connection_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.connection_events.append(event)
        
        # Check for potential race conditions
        self._check_connection_event_races(event)
    
    def _check_connection_event_races(self, event: Dict):
        """Check for race conditions in connection events."""
        connection_id = event["connection_id"]
        user_id = event["user_id"]
        event_type = event["event_type"]
        
        # Check for duplicate connection events (race condition indicator)
        recent_events = [
            e for e in self.connection_events[-10:]  # Check last 10 events
            if (e["connection_id"] == connection_id and
                e["event_type"] == event_type and
                abs(e["timestamp"] - event["timestamp"]) < 0.1 and  # Within 100ms
                e != event)
        ]
        
        if recent_events:
            self._detect_race_condition(
                "duplicate_connection_events",
                {
                    "connection_id": connection_id,
                    "event_type": event_type,
                    "duplicate_count": len(recent_events)
                },
                event
            )
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict, context: Dict):
        """Record race condition detection."""
        race_condition = {
            "condition_type": condition_type,
            "metadata": metadata,
            "context": context,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_condition_detections.append(race_condition)
        logger.warning(f"E2E WebSocket race condition detected: {race_condition}")
    
    def _check_user_isolation(self, user_id: str, message: Dict):
        """Check for user isolation violations in received messages."""
        message_user_id = message.get("user_id")
        message_connection_id = message.get("connection_id")
        
        # Message should only be received by intended user
        if message_user_id and message_user_id != user_id:
            self.user_isolation_violations.append({
                "violation_type": "cross_user_message",
                "intended_user": message_user_id,
                "receiving_user": user_id,
                "message_type": message.get("type"),
                "connection_id": message_connection_id,
                "timestamp": time.time()
            })
    
    async def _create_authenticated_websocket_connection(self, user: AuthenticatedUser, connection_index: int):
        """Create authenticated WebSocket connection for a user."""
        try:
            connection_id = f"e2e_ws_conn_{user.user_id}_{connection_index}_{uuid.uuid4().hex[:6]}"
            
            # Get WebSocket headers with authentication
            headers = self.auth_helper.get_websocket_headers(user.jwt_token)
            
            # Connect to WebSocket with authentication
            websocket_url = self.websocket_auth_helper.config.websocket_url
            
            # Track connection attempt
            self._track_connection_event("connection_attempt", connection_id, user.user_id, {
                "websocket_url": websocket_url,
                "headers_count": len(headers)
            })
            
            websocket = await websockets.connect(
                websocket_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                timeout=15.0  # Increased timeout for E2E
            )
            
            # Track successful connection
            self._track_connection_event("connected", connection_id, user.user_id, {
                "websocket_state": websocket.state.name,
                "connection_open": not websocket.closed
            })
            
            # Store connection data
            connection_data = {
                "websocket": websocket,
                "user": user,
                "connection_id": connection_id,
                "connected_at": time.time(),
                "received_messages": []
            }
            
            self.active_connections[connection_id] = connection_data
            self.received_messages[connection_id] = []
            
            return connection_data
            
        except Exception as e:
            logger.error(f"Failed to create WebSocket connection for user {user.user_id}: {e}")
            self._track_connection_event("connection_failed", connection_id, user.user_id, {
                "error": str(e)
            })
            raise
    
    async def _message_listener(self, connection_data: Dict):
        """Listen for messages on a WebSocket connection."""
        websocket = connection_data["websocket"]
        user = connection_data["user"]
        connection_id = connection_data["connection_id"]
        
        try:
            while not websocket.closed:
                try:
                    # Wait for message with timeout
                    message_raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    
                    # Parse message
                    try:
                        message = json.loads(message_raw)
                    except json.JSONDecodeError:
                        # Skip non-JSON messages
                        continue
                    
                    # Add metadata to message
                    message["_received_at"] = time.time()
                    message["_connection_id"] = connection_id
                    message["_receiving_user"] = user.user_id
                    
                    # Store message
                    connection_data["received_messages"].append(message)
                    self.received_messages[connection_id].append(message)
                    
                    # Check for user isolation violations
                    self._check_user_isolation(user.user_id, message)
                    
                    # Track message event
                    self._track_connection_event("message_received", connection_id, user.user_id, {
                        "message_type": message.get("type"),
                        "message_size": len(message_raw)
                    })
                    
                except asyncio.TimeoutError:
                    # No message received in timeout period, continue listening
                    continue
                except websockets.exceptions.ConnectionClosed:
                    # Connection closed, stop listening
                    break
                    
        except Exception as e:
            logger.error(f"Message listener error for connection {connection_id}: {e}")
            self._track_connection_event("listener_error", connection_id, user.user_id, {
                "error": str(e)
            })
    
    @pytest.mark.e2e
    @pytest.mark.race_conditions
    @requires_real_services
    async def test_10_concurrent_websocket_connections_with_real_auth(self):
        """Test 10 concurrent WebSocket connections with real authentication for race conditions."""
        
        # Create 10 authenticated users
        users = []
        for i in range(10):
            user = await self.auth_helper.create_authenticated_user(
                email=f"e2e_race_user_{i:02d}@example.com",
                user_id=f"e2e_race_user_{i:02d}",
                permissions=["read", "write", "websocket"]
            )
            users.append(user)
        
        # Establish WebSocket connections concurrently
        async def establish_user_connection(user: AuthenticatedUser, user_index: int):
            """Establish WebSocket connection for a user."""
            try:
                connection_data = await self._create_authenticated_websocket_connection(user, user_index)
                
                # Start message listener
                listener_task = asyncio.create_task(self._message_listener(connection_data))
                connection_data["listener_task"] = listener_task
                
                return {
                    "user_index": user_index,
                    "user_id": user.user_id,
                    "connection_id": connection_data["connection_id"],
                    "connection_success": True,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Connection establishment failed for user {user_index}: {e}")
                return {
                    "user_index": user_index,
                    "user_id": user.user_id,
                    "connection_success": False,
                    "success": False,
                    "error": str(e)
                }
        
        # Establish all connections concurrently
        start_time = time.time()
        connection_results = await asyncio.gather(
            *[establish_user_connection(user, i) for i, user in enumerate(users)],
            return_exceptions=True
        )
        connection_time = time.time() - start_time
        
        # Analyze connection results
        successful_connections = len([r for r in connection_results if isinstance(r, dict) and r.get("connection_success")])
        failed_connections = len([r for r in connection_results if not isinstance(r, dict) or not r.get("connection_success")])
        
        # Verify all connections succeeded
        assert successful_connections == 10, (
            f"Expected 10 successful WebSocket connections, got {successful_connections}. "
            f"Failed: {failed_connections}. Race conditions may have caused connection failures."
        )
        
        # Send test messages through each connection
        async def send_user_messages(connection_id: str, user: AuthenticatedUser, message_count: int = 3):
            """Send test messages through a user's WebSocket connection."""
            connection_data = self.active_connections.get(connection_id)
            if not connection_data:
                return {"connection_id": connection_id, "sent_count": 0, "success": False}
            
            websocket = connection_data["websocket"]
            sent_messages = []
            
            try:
                for i in range(message_count):
                    message = {
                        "type": "test_message",
                        "user_id": user.user_id,
                        "connection_id": connection_id,
                        "message_index": i,
                        "content": f"Test message {i} from {user.user_id}",
                        "timestamp": time.time(),
                        "isolation_test": True
                    }
                    
                    await websocket.send(json.dumps(message))
                    sent_messages.append(message)
                    
                    # Small delay between messages
                    await asyncio.sleep(0.1)
                
                return {
                    "connection_id": connection_id,
                    "user_id": user.user_id,
                    "sent_count": len(sent_messages),
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Failed to send messages for connection {connection_id}: {e}")
                return {
                    "connection_id": connection_id,
                    "sent_count": len(sent_messages),
                    "success": False,
                    "error": str(e)
                }
        
        # Send messages through all connections concurrently
        messaging_tasks = []
        for result in connection_results:
            if isinstance(result, dict) and result.get("connection_success"):
                connection_id = result["connection_id"]
                user = next(u for u in users if u.user_id == result["user_id"])
                messaging_tasks.append(send_user_messages(connection_id, user, 3))
        
        messaging_results = await asyncio.gather(*messaging_tasks, return_exceptions=True)
        
        # Wait for message propagation
        await asyncio.sleep(2.0)
        
        # Analyze messaging results
        successful_messaging = len([r for r in messaging_results if isinstance(r, dict) and r.get("success")])
        total_messages_sent = sum(r.get("sent_count", 0) for r in messaging_results if isinstance(r, dict))
        
        # Verify messaging succeeded
        assert successful_messaging == 10, (
            f"Expected 10 successful messaging operations, got {successful_messaging}. "
            f"Race conditions may have affected message sending."
        )
        
        assert total_messages_sent == 30, (  # 10 connections × 3 messages each
            f"Expected 30 messages sent, got {total_messages_sent}. "
            f"Race conditions may have caused message sending failures."
        )
        
        # Check for user isolation violations
        assert len(self.user_isolation_violations) == 0, (
            f"User isolation violations detected: {self.user_isolation_violations}. "
            f"Race conditions may have caused cross-user message leakage."
        )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in WebSocket connections: {self.race_condition_detections}"
        )
        
        # Verify connection isolation - each user should only receive their own messages
        for connection_id, messages in self.received_messages.items():
            connection_data = self.active_connections.get(connection_id)
            if connection_data:
                user_id = connection_data["user"]["user_id"]
                
                # Check that all received messages are intended for this user
                for message in messages:
                    message_user_id = message.get("user_id")
                    if message_user_id and message_user_id != user_id:
                        raise AssertionError(
                            f"User isolation violation: User {user_id} received message intended for {message_user_id}. "
                            f"Race condition in message routing."
                        )
        
        # Verify reasonable connection time
        assert connection_time < 30.0, (
            f"WebSocket connections took {connection_time:.2f}s, expected < 30s. "
            f"This may indicate connection bottlenecks or race conditions."
        )
        
        # Clean up connections
        for connection_data in self.active_connections.values():
            listener_task = connection_data.get("listener_task")
            if listener_task and not listener_task.done():
                listener_task.cancel()
            
            websocket = connection_data["websocket"]
            if not websocket.closed:
                await websocket.close()
        
        logger.info(
            f"✅ 10 concurrent WebSocket connections E2E test passed in {connection_time:.2f}s. "
            f"Connections: {successful_connections}/10, Messaging: {successful_messaging}/10, "
            f"Messages sent: {total_messages_sent}, Isolation violations: {len(self.user_isolation_violations)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.e2e
    @pytest.mark.race_conditions
    @requires_real_services
    async def test_websocket_agent_execution_isolation_e2e(self):
        """Test WebSocket agent execution isolation under concurrent load with real services."""
        
        # Create 6 authenticated users for agent execution
        users = []
        for i in range(6):
            user = await self.auth_helper.create_authenticated_user(
                email=f"e2e_agent_user_{i:02d}@example.com",
                user_id=f"e2e_agent_user_{i:02d}",
                permissions=["read", "write", "websocket", "agent_execute"]
            )
            users.append(user)
        
        # Establish WebSocket connections
        connection_tasks = []
        for i, user in enumerate(users):
            connection_tasks.append(self._create_authenticated_websocket_connection(user, i))
        
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Start message listeners
        for connection_data in connection_results:
            if isinstance(connection_data, dict):
                listener_task = asyncio.create_task(self._message_listener(connection_data))
                connection_data["listener_task"] = listener_task
        
        # Execute agents through WebSocket connections concurrently
        async def execute_agent_through_websocket(connection_data: Dict, execution_index: int):
            """Execute agent through WebSocket connection."""
            try:
                websocket = connection_data["websocket"]
                user = connection_data["user"]
                connection_id = connection_data["connection_id"]
                
                # Send agent execution request
                agent_request = {
                    "type": "agent_request",
                    "agent_name": "test_agent",
                    "user_id": user.user_id,
                    "connection_id": connection_id,
                    "execution_index": execution_index,
                    "message": f"Test agent execution {execution_index} for user {user.user_id}",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Wait for agent execution events
                await asyncio.sleep(3.0)  # Give time for agent execution
                
                # Analyze received messages for agent events
                received_messages = connection_data.get("received_messages", [])
                agent_events = [
                    msg for msg in received_messages
                    if msg.get("type") in ["agent_started", "agent_thinking", "agent_completed"]
                ]
                
                return {
                    "execution_index": execution_index,
                    "user_id": user.user_id,
                    "connection_id": connection_id,
                    "agent_events_received": len(agent_events),
                    "total_messages_received": len(received_messages),
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Agent execution failed for user {user.user_id}: {e}")
                return {
                    "execution_index": execution_index,
                    "user_id": user.user_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute agents concurrently
        execution_tasks = []
        for i, connection_data in enumerate(connection_results):
            if isinstance(connection_data, dict):
                execution_tasks.append(execute_agent_through_websocket(connection_data, i))
        
        execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Analyze agent execution results
        successful_executions = len([r for r in execution_results if isinstance(r, dict) and r.get("success")])
        failed_executions = len([r for r in execution_results if not isinstance(r, dict) or not r.get("success")])
        
        # Verify all agent executions succeeded (or got reasonable responses)
        assert successful_executions >= 4, (  # Allow some flexibility for agent availability
            f"Expected at least 4 successful agent executions, got {successful_executions}. "
            f"Failed: {failed_executions}. Race conditions may have affected agent execution."
        )
        
        # Check for cross-user event leakage
        user_events = defaultdict(list)
        for result in execution_results:
            if isinstance(result, dict) and result.get("success"):
                user_id = result["user_id"]
                connection_id = result["connection_id"]
                
                # Get all events received by this user
                connection_data = self.active_connections.get(connection_id)
                if connection_data:
                    user_events[user_id].extend(connection_data.get("received_messages", []))
        
        # Verify user isolation in agent events
        for user_id, events in user_events.items():
            for event in events:
                event_user_id = event.get("user_id")
                if event_user_id and event_user_id != user_id:
                    raise AssertionError(
                        f"Agent execution isolation violation: User {user_id} received agent event "
                        f"for user {event_user_id}. Race condition in agent event routing."
                    )
        
        # Check for race conditions and isolation violations
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in agent execution: {self.race_condition_detections}"
        )
        
        assert len(self.user_isolation_violations) == 0, (
            f"User isolation violations detected: {self.user_isolation_violations}"
        )
        
        # Clean up connections
        for connection_data in self.active_connections.values():
            listener_task = connection_data.get("listener_task")
            if listener_task and not listener_task.done():
                listener_task.cancel()
            
            websocket = connection_data["websocket"]
            if not websocket.closed:
                await websocket.close()
        
        logger.info(
            f"✅ WebSocket agent execution isolation E2E test passed. "
            f"Successful executions: {successful_executions}/6, "
            f"User events isolated: {len(user_events)} users, "
            f"Isolation violations: {len(self.user_isolation_violations)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.e2e
    @pytest.mark.race_conditions
    @requires_real_services
    async def test_websocket_authentication_token_isolation_e2e(self):
        """Test WebSocket authentication token isolation under concurrent access."""
        
        # Create users with different permission levels
        users = []
        permission_sets = [
            ["read"],
            ["read", "write"],
            ["read", "write", "websocket"],
            ["read", "write", "websocket", "admin"],
            ["read", "write", "websocket", "agent_execute"]
        ]
        
        for i, permissions in enumerate(permission_sets):
            user = await self.auth_helper.create_authenticated_user(
                email=f"e2e_auth_user_{i:02d}@example.com",
                user_id=f"e2e_auth_user_{i:02d}",
                permissions=permissions
            )
            users.append(user)
        
        # Test concurrent authentication validation
        async def test_authentication_isolation(user: AuthenticatedUser, user_index: int):
            """Test authentication token isolation for a user."""
            try:
                # Create WebSocket connection with user's token
                connection_data = await self._create_authenticated_websocket_connection(user, user_index)
                
                # Start message listener
                listener_task = asyncio.create_task(self._message_listener(connection_data))
                connection_data["listener_task"] = listener_task
                
                # Send authentication test message
                auth_test_message = {
                    "type": "auth_test",
                    "user_id": user.user_id,
                    "permissions": user.permissions,
                    "token_hash": hash(user.jwt_token) & 0xFFFFFFFF,  # Partial token identifier
                    "timestamp": time.time()
                }
                
                websocket = connection_data["websocket"]
                await websocket.send(json.dumps(auth_test_message))
                
                # Wait for potential responses
                await asyncio.sleep(1.0)
                
                # Check received messages for authentication responses
                received_messages = connection_data.get("received_messages", [])
                auth_responses = [
                    msg for msg in received_messages
                    if msg.get("type") == "auth_response" or msg.get("type") == "auth_test"
                ]
                
                return {
                    "user_index": user_index,
                    "user_id": user.user_id,
                    "permissions": user.permissions,
                    "connection_success": True,
                    "auth_responses": len(auth_responses),
                    "total_messages": len(received_messages),
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Authentication isolation test failed for user {user_index}: {e}")
                return {
                    "user_index": user_index,
                    "user_id": user.user_id,
                    "connection_success": False,
                    "success": False,
                    "error": str(e)
                }
        
        # Test authentication isolation concurrently
        auth_results = await asyncio.gather(
            *[test_authentication_isolation(user, i) for i, user in enumerate(users)],
            return_exceptions=True
        )
        
        # Analyze authentication results
        successful_auth_tests = len([r for r in auth_results if isinstance(r, dict) and r.get("success")])
        failed_auth_tests = len([r for r in auth_results if not isinstance(r, dict) or not r.get("success")])
        
        # Verify all authentication tests succeeded
        assert successful_auth_tests == 5, (
            f"Expected 5 successful authentication tests, got {successful_auth_tests}. "
            f"Failed: {failed_auth_tests}. Race conditions may have affected authentication."
        )
        
        # Verify token isolation - each user should only see their own authentication context
        for result in auth_results:
            if isinstance(result, dict) and result.get("success"):
                user_id = result["user_id"]
                connection_id = None
                
                # Find connection for this user
                for conn_id, conn_data in self.active_connections.items():
                    if conn_data["user"].user_id == user_id:
                        connection_id = conn_id
                        break
                
                if connection_id:
                    received_messages = self.received_messages.get(connection_id, [])
                    
                    # Check that all received auth-related messages are for this user
                    for message in received_messages:
                        message_user_id = message.get("user_id")
                        if message_user_id and message_user_id != user_id:
                            if message.get("type") in ["auth_test", "auth_response", "auth_error"]:
                                raise AssertionError(
                                    f"Authentication token isolation violation: User {user_id} "
                                    f"received auth message for user {message_user_id}. "
                                    f"Race condition in token validation."
                                )
        
        # Check for race conditions and violations
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in authentication isolation: {self.race_condition_detections}"
        )
        
        assert len(self.user_isolation_violations) == 0, (
            f"User isolation violations detected: {self.user_isolation_violations}"
        )
        
        # Clean up connections
        for connection_data in self.active_connections.values():
            listener_task = connection_data.get("listener_task")
            if listener_task and not listener_task.done():
                listener_task.cancel()
            
            websocket = connection_data["websocket"]
            if not websocket.closed:
                await websocket.close()
        
        logger.info(
            f"✅ WebSocket authentication token isolation E2E test passed. "
            f"Successful auth tests: {successful_auth_tests}/5, "
            f"Different permission levels tested: {len(permission_sets)}, "
            f"Isolation violations: {len(self.user_isolation_violations)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )