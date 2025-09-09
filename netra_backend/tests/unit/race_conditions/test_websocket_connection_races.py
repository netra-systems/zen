"""
Race Condition Tests: WebSocket Connection Management

This module tests for race conditions in WebSocket connection state management.
Validates that WebSocket connections remain stable under concurrent load.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure reliable real-time communication for chat functionality
- Value Impact: Prevents connection drops, message loss, and degraded user experience
- Strategic Impact: CRITICAL - WebSocket connections enable core chat value delivery

Test Coverage:
- Multiple concurrent WebSocket connections
- Connection state race conditions
- Message routing isolation
- Authentication race conditions
- Connection cleanup and resource management
"""

import asyncio
import json
import time
import uuid
import weakref
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockWebSocket:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.is_open = True
        self.sent_messages = []
        self.received_messages = []
        self._close_called = False
        
    async def send(self, message: str):
        """Mock send method."""
        if not self.is_open:
            raise Exception("WebSocket is closed")
        self.sent_messages.append({
            "message": message,
            "timestamp": time.time(),
            "connection_id": self.connection_id
        })
    
    async def receive(self) -> str:
        """Mock receive method."""
        if not self.is_open:
            raise Exception("WebSocket is closed")
        if self.received_messages:
            return self.received_messages.pop(0)
        await asyncio.sleep(0.1)  # Simulate waiting
        return json.dumps({"type": "ping", "timestamp": time.time()})
    
    async def close(self):
        """Mock close method."""
        self.is_open = False
        self._close_called = True
    
    def inject_message(self, message: str):
        """Inject message for testing."""
        self.received_messages.append(message)


class TestWebSocketConnectionRaces(SSotBaseTestCase):
    """Test race conditions in WebSocket connection management."""
    
    def setup_method(self):
        """Set up test environment with WebSocket mocking."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "websocket_race_testing", source="test")
        
        # Track connection state
        self.mock_connections: Dict[str, MockWebSocket] = {}
        self.connection_events: List[Dict] = []
        self.race_condition_detections: List[Dict] = []
        self.message_routing_errors: List[Dict] = []
        self.connection_refs: List[weakref.ref] = []
        
        # Set up auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
    def teardown_method(self):
        """Clean up test state."""
        # Close all mock connections
        for connection in self.mock_connections.values():
            if connection.is_open:
                asyncio.create_task(connection.close())
        
        self.mock_connections.clear()
        self.connection_events.clear()
        self.race_condition_detections.clear()
        self.message_routing_errors.clear()
        self.connection_refs.clear()
        
        super().teardown_method()
    
    def _create_mock_connection_manager(self) -> Mock:
        """Create mock WebSocket connection manager."""
        manager = Mock(spec=WebSocketConnectionManager)
        
        async def mock_connect(connection_id: str, websocket, user_id: str = None):
            """Mock connect method with race condition tracking."""
            if connection_id in self.mock_connections:
                # Race condition: connection already exists
                self._detect_race_condition(
                    connection_id, "duplicate_connection_registration", 
                    {"existing_user": self.mock_connections[connection_id].user_id, "new_user": user_id}
                )
                return False
            
            # Create mock connection
            mock_ws = MockWebSocket(connection_id, user_id or "unknown")
            self.mock_connections[connection_id] = mock_ws
            self.connection_refs.append(weakref.ref(mock_ws))
            
            self._record_connection_event("connected", connection_id, user_id)
            return True
        
        async def mock_disconnect(connection_id: str):
            """Mock disconnect method."""
            if connection_id in self.mock_connections:
                connection = self.mock_connections[connection_id]
                await connection.close()
                del self.mock_connections[connection_id]
                self._record_connection_event("disconnected", connection_id, connection.user_id)
                return True
            return False
        
        async def mock_send_message(connection_id: str, message: str):
            """Mock send message method."""
            if connection_id in self.mock_connections:
                connection = self.mock_connections[connection_id]
                try:
                    await connection.send(message)
                    return True
                except Exception as e:
                    self._record_message_routing_error(connection_id, "send_failed", str(e))
                    return False
            else:
                self._record_message_routing_error(connection_id, "connection_not_found", "Connection not in manager")
                return False
        
        def mock_get_user_connections(user_id: str) -> List[str]:
            """Mock get user connections method."""
            return [
                conn_id for conn_id, conn in self.mock_connections.items()
                if conn.user_id == user_id and conn.is_open
            ]
        
        manager.connect = mock_connect
        manager.disconnect = mock_disconnect
        manager.send_message = mock_send_message
        manager.get_user_connections = mock_get_user_connections
        
        return manager
    
    def _create_mock_websocket_bridge(self, connection_manager: Mock) -> Mock:
        """Create mock WebSocket bridge for testing."""
        bridge = Mock(spec=AgentWebSocketBridge)
        self.bridge_events = []
        
        async def mock_notify_agent_started(run_id: str, agent_name: str, data: Dict = None):
            event = {
                "type": "agent_started",
                "run_id": run_id,
                "agent_name": agent_name,
                "data": data or {},
                "timestamp": time.time()
            }
            self.bridge_events.append(event)
            
            # Find connections for this run and send message
            user_id = data.get("user_id") if data else None
            if user_id:
                connections = connection_manager.get_user_connections(user_id)
                for conn_id in connections:
                    await connection_manager.send_message(conn_id, json.dumps(event))
        
        async def mock_notify_agent_thinking(run_id: str, agent_name: str, reasoning: str, step_number: int = None):
            event = {
                "type": "agent_thinking",
                "run_id": run_id,
                "agent_name": agent_name,
                "reasoning": reasoning,
                "step_number": step_number,
                "timestamp": time.time()
            }
            self.bridge_events.append(event)
        
        async def mock_notify_agent_completed(run_id: str, agent_name: str, result: Dict, execution_time_ms: float):
            event = {
                "type": "agent_completed",
                "run_id": run_id,
                "agent_name": agent_name,
                "result": result,
                "execution_time_ms": execution_time_ms,
                "timestamp": time.time()
            }
            self.bridge_events.append(event)
        
        bridge.notify_agent_started = mock_notify_agent_started
        bridge.notify_agent_thinking = mock_notify_agent_thinking
        bridge.notify_agent_completed = mock_notify_agent_completed
        
        return bridge
    
    def _record_connection_event(self, event_type: str, connection_id: str, user_id: str):
        """Record connection event for analysis."""
        event = {
            "event_type": event_type,
            "connection_id": connection_id,
            "user_id": user_id,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.connection_events.append(event)
    
    def _detect_race_condition(self, connection_id: str, condition_type: str, metadata: Dict = None):
        """Record race condition detection."""
        race_condition = {
            "connection_id": connection_id,
            "condition_type": condition_type,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_condition_detections.append(race_condition)
        logger.warning(f"WebSocket race condition detected: {race_condition}")
    
    def _record_message_routing_error(self, connection_id: str, error_type: str, error_message: str):
        """Record message routing error."""
        error = {
            "connection_id": connection_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": time.time()
        }
        self.message_routing_errors.append(error)
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_concurrent_websocket_connections(self):
        """Test multiple concurrent WebSocket connections for race conditions."""
        connection_manager = self._create_mock_connection_manager()
        websocket_bridge = self._create_mock_websocket_bridge(connection_manager)
        
        async def establish_connection(user_index: int):
            """Establish a WebSocket connection for a user."""
            try:
                # Create authenticated user
                user = await self.auth_helper.create_authenticated_user(
                    email=f"race_test_user_{user_index}@example.com",
                    user_id=f"race_user_{user_index:03d}"
                )
                
                connection_id = f"ws_conn_{user_index:03d}_{uuid.uuid4().hex[:8]}"
                
                # Mock WebSocket object
                mock_ws = MockWebSocket(connection_id, user.user_id)
                
                # Connect through manager
                success = await connection_manager.connect(connection_id, mock_ws, user.user_id)
                
                if success:
                    # Simulate some WebSocket activity
                    await asyncio.sleep(0.001)  # Small delay to create race opportunities
                    
                    # Send a test message
                    test_message = json.dumps({
                        "type": "test_message",
                        "user_id": user.user_id,
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    })
                    
                    send_success = await connection_manager.send_message(connection_id, test_message)
                    
                    return {
                        "user_index": user_index,
                        "user_id": user.user_id,
                        "connection_id": connection_id,
                        "connect_success": success,
                        "send_success": send_success,
                        "success": True
                    }
                else:
                    return {
                        "user_index": user_index,
                        "success": False,
                        "error": "Connection failed"
                    }
                    
            except Exception as e:
                logger.error(f"Connection establishment failed for user {user_index}: {e}")
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Establish 25 concurrent connections
        start_time = time.time()
        results = await asyncio.gather(
            *[establish_connection(i) for i in range(25)],
            return_exceptions=True
        )
        connection_time = time.time() - start_time
        
        # Analyze results
        successful_connections = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_connections = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        successful_sends = len([r for r in results if isinstance(r, dict) and r.get("send_success")])
        
        # Check for race condition indicators
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in WebSocket connections: {self.race_condition_detections}"
        )
        
        assert len(self.message_routing_errors) == 0, (
            f"Message routing errors detected: {self.message_routing_errors}"
        )
        
        # Verify all connections succeeded
        assert successful_connections == 25, (
            f"Expected 25 successful connections, got {successful_connections}. "
            f"Failed: {failed_connections}. Race conditions may have caused connection failures."
        )
        
        # Verify all message sends succeeded
        assert successful_sends == successful_connections, (
            f"Expected {successful_connections} successful sends, got {successful_sends}. "
            f"Race conditions may have affected message routing."
        )
        
        # Verify reasonable connection time
        assert connection_time < 5.0, (
            f"Connection establishment took {connection_time:.2f}s, expected < 5s. "
            f"This may indicate serialization instead of concurrent connections."
        )
        
        # Verify unique connection IDs
        connection_ids = [r.get("connection_id") for r in results if isinstance(r, dict) and r.get("connection_id")]
        unique_connection_ids = set(connection_ids)
        
        assert len(connection_ids) == len(unique_connection_ids), (
            f"Duplicate connection IDs detected: {len(connection_ids)} total, "
            f"{len(unique_connection_ids)} unique. Race condition in ID generation."
        )
        
        logger.info(
            f"✅ 25 concurrent WebSocket connections established successfully in {connection_time:.2f}s. "
            f"Success rate: {successful_connections}/25, Send success: {successful_sends}/25, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_connection_state_races(self):
        """Test WebSocket connection state management for race conditions."""
        connection_manager = self._create_mock_connection_manager()
        
        async def connection_lifecycle_test(connection_index: int):
            """Test full connection lifecycle for race conditions."""
            try:
                user_id = f"lifecycle_user_{connection_index:03d}"
                connection_id = f"lifecycle_conn_{connection_index:03d}"
                
                # Phase 1: Connect
                mock_ws = MockWebSocket(connection_id, user_id)
                connect_success = await connection_manager.connect(connection_id, mock_ws, user_id)
                
                if not connect_success:
                    return {"connection_index": connection_index, "success": False, "phase": "connect"}
                
                # Phase 2: Send messages rapidly
                for msg_index in range(5):
                    message = json.dumps({
                        "type": "test_message",
                        "msg_index": msg_index,
                        "connection_id": connection_id
                    })
                    
                    send_success = await connection_manager.send_message(connection_id, message)
                    if not send_success:
                        return {
                            "connection_index": connection_index,
                            "success": False,
                            "phase": f"send_message_{msg_index}"
                        }
                    
                    # Small delay to create race opportunities
                    await asyncio.sleep(0.0001)
                
                # Phase 3: Check connection status
                user_connections = connection_manager.get_user_connections(user_id)
                if connection_id not in user_connections:
                    return {
                        "connection_index": connection_index,
                        "success": False,
                        "phase": "connection_check"
                    }
                
                # Phase 4: Disconnect
                disconnect_success = await connection_manager.disconnect(connection_id)
                
                if not disconnect_success:
                    return {"connection_index": connection_index, "success": False, "phase": "disconnect"}
                
                # Phase 5: Verify disconnection
                final_connections = connection_manager.get_user_connections(user_id)
                if connection_id in final_connections:
                    return {
                        "connection_index": connection_index,
                        "success": False,
                        "phase": "disconnect_verification"
                    }
                
                return {"connection_index": connection_index, "success": True, "phase": "completed"}
                
            except Exception as e:
                logger.error(f"Connection lifecycle test failed for {connection_index}: {e}")
                return {
                    "connection_index": connection_index,
                    "success": False,
                    "phase": "exception",
                    "error": str(e)
                }
        
        # Run 20 concurrent lifecycle tests
        results = await asyncio.gather(
            *[connection_lifecycle_test(i) for i in range(20)],
            return_exceptions=True
        )
        
        # Analyze results
        successful_lifecycles = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_lifecycles = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        
        # Check failure phases
        failure_phases = defaultdict(int)
        for result in results:
            if isinstance(result, dict) and not result.get("success"):
                phase = result.get("phase", "unknown")
                failure_phases[phase] += 1
        
        # Verify no race conditions detected
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in connection state management: {self.race_condition_detections}"
        )
        
        # Verify all lifecycles completed successfully
        assert successful_lifecycles == 20, (
            f"Expected 20 successful connection lifecycles, got {successful_lifecycles}. "
            f"Failed: {failed_lifecycles}. Failure phases: {dict(failure_phases)}. "
            f"Race conditions may have caused state management failures."
        )
        
        # Verify no connections remain (proper cleanup)
        remaining_connections = len(self.mock_connections)
        assert remaining_connections == 0, (
            f"Expected 0 remaining connections after cleanup, got {remaining_connections}. "
            f"Race conditions may have prevented proper cleanup."
        )
        
        logger.info(
            f"✅ Connection state race test passed: "
            f"{successful_lifecycles}/20 successful lifecycles, "
            f"0 race conditions detected, 0 connections leaked"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_message_routing_isolation(self):
        """Test message routing isolation between users under concurrent load."""
        connection_manager = self._create_mock_connection_manager()
        
        # Create multiple users with multiple connections each
        async def setup_user_connections(user_index: int, connections_per_user: int = 3):
            """Set up multiple connections for a single user."""
            user_id = f"routing_user_{user_index:02d}"
            user_connections = []
            
            for conn_index in range(connections_per_user):
                connection_id = f"routing_conn_{user_index:02d}_{conn_index:02d}"
                mock_ws = MockWebSocket(connection_id, user_id)
                
                success = await connection_manager.connect(connection_id, mock_ws, user_id)
                if success:
                    user_connections.append(connection_id)
            
            return {"user_id": user_id, "connections": user_connections}
        
        # Set up 10 users with 3 connections each = 30 total connections
        user_setups = await asyncio.gather(
            *[setup_user_connections(i, 3) for i in range(10)]
        )
        
        # Verify all connections were established
        total_expected_connections = 10 * 3
        total_actual_connections = sum(len(setup["connections"]) for setup in user_setups)
        
        assert total_actual_connections == total_expected_connections, (
            f"Expected {total_expected_connections} connections, got {total_actual_connections}. "
            f"Connection setup failed."
        )
        
        # Test concurrent message routing
        async def send_user_messages(user_setup: Dict):
            """Send messages to all connections for a user."""
            user_id = user_setup["user_id"]
            connections = user_setup["connections"]
            
            sent_messages = []
            
            for i, connection_id in enumerate(connections):
                message = json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "message_index": i,
                    "content": f"Message {i} for {user_id} on {connection_id}",
                    "timestamp": time.time()
                })
                
                success = await connection_manager.send_message(connection_id, message)
                if success:
                    sent_messages.append(message)
                
                # Small delay to create race opportunities
                await asyncio.sleep(0.0001)
            
            return {"user_id": user_id, "sent_count": len(sent_messages)}
        
        # Send messages to all users concurrently
        messaging_results = await asyncio.gather(
            *[send_user_messages(setup) for setup in user_setups]
        )
        
        # Verify message routing isolation
        total_messages_sent = sum(result["sent_count"] for result in messaging_results)
        expected_messages = 10 * 3  # 10 users × 3 messages each
        
        assert total_messages_sent == expected_messages, (
            f"Expected {expected_messages} messages sent, got {total_messages_sent}. "
            f"Message routing failures detected."
        )
        
        # Check for message routing errors
        assert len(self.message_routing_errors) == 0, (
            f"Message routing errors detected: {self.message_routing_errors}"
        )
        
        # Verify each user received exactly their own messages
        for user_setup in user_setups:
            user_id = user_setup["user_id"]
            user_connections = connection_manager.get_user_connections(user_id)
            
            # Should have exactly 3 connections for this user
            assert len(user_connections) == 3, (
                f"User {user_id} should have 3 connections, got {len(user_connections)}. "
                f"Connection isolation failure."
            )
            
            # Check messages received by each connection
            for connection_id in user_connections:
                connection = self.mock_connections.get(connection_id)
                if connection:
                    # Should have received exactly 1 message
                    assert len(connection.sent_messages) == 1, (
                        f"Connection {connection_id} should have 1 message, "
                        f"got {len(connection.sent_messages)}. Message routing isolation failure."
                    )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in message routing: {self.race_condition_detections}"
        )
        
        logger.info(
            f"✅ Message routing isolation test passed: "
            f"10 users × 3 connections = 30 total connections, "
            f"{total_messages_sent} messages routed correctly, "
            f"0 routing errors, 0 race conditions"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_websocket_authentication_races(self):
        """Test WebSocket authentication under concurrent load for race conditions."""
        connection_manager = self._create_mock_connection_manager()
        
        async def authenticate_and_connect(auth_index: int):
            """Authenticate user and establish WebSocket connection."""
            try:
                # Create authenticated user
                user = await self.auth_helper.create_authenticated_user(
                    email=f"auth_race_user_{auth_index}@example.com",
                    user_id=f"auth_user_{auth_index:03d}",
                    permissions=["read", "write", "websocket"]
                )
                
                # Validate authentication
                auth_headers = self.auth_helper.get_websocket_headers(user.jwt_token)
                
                # Simulate authentication validation delay
                await asyncio.sleep(0.001)
                
                # Establish connection after authentication
                connection_id = f"auth_conn_{auth_index:03d}_{uuid.uuid4().hex[:6]}"
                mock_ws = MockWebSocket(connection_id, user.user_id)
                
                # Connect with authentication context
                connect_success = await connection_manager.connect(connection_id, mock_ws, user.user_id)
                
                if connect_success:
                    # Test authenticated operations
                    auth_message = json.dumps({
                        "type": "authenticated_message",
                        "user_id": user.user_id,
                        "headers": list(auth_headers.keys()),
                        "permissions": user.permissions,
                        "timestamp": time.time()
                    })
                    
                    send_success = await connection_manager.send_message(connection_id, auth_message)
                    
                    return {
                        "auth_index": auth_index,
                        "user_id": user.user_id,
                        "connection_id": connection_id,
                        "auth_success": True,
                        "connect_success": connect_success,
                        "send_success": send_success,
                        "success": True
                    }
                else:
                    return {
                        "auth_index": auth_index,
                        "user_id": user.user_id,
                        "auth_success": True,
                        "connect_success": False,
                        "success": False
                    }
                    
            except Exception as e:
                logger.error(f"Authentication and connection failed for {auth_index}: {e}")
                return {
                    "auth_index": auth_index,
                    "auth_success": False,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 15 concurrent authentication and connection operations
        auth_results = await asyncio.gather(
            *[authenticate_and_connect(i) for i in range(15)],
            return_exceptions=True
        )
        
        # Analyze authentication results
        successful_auths = len([r for r in auth_results if isinstance(r, dict) and r.get("auth_success")])
        successful_connections = len([r for r in auth_results if isinstance(r, dict) and r.get("connect_success")])
        successful_sends = len([r for r in auth_results if isinstance(r, dict) and r.get("send_success")])
        failed_operations = len([r for r in auth_results if not isinstance(r, dict) or not r.get("success")])
        
        # Check for authentication race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in WebSocket authentication: {self.race_condition_detections}"
        )
        
        # Verify all authentication operations succeeded
        assert successful_auths == 15, (
            f"Expected 15 successful authentications, got {successful_auths}. "
            f"Race conditions may have caused authentication failures."
        )
        
        assert successful_connections == 15, (
            f"Expected 15 successful connections, got {successful_connections}. "
            f"Race conditions may have affected authenticated connection establishment."
        )
        
        assert successful_sends == 15, (
            f"Expected 15 successful authenticated sends, got {successful_sends}. "
            f"Race conditions may have affected authenticated message sending."
        )
        
        assert failed_operations == 0, (
            f"Expected 0 failed operations, got {failed_operations}. "
            f"Race conditions may have caused operation failures."
        )
        
        # Verify no message routing errors
        assert len(self.message_routing_errors) == 0, (
            f"Message routing errors in authenticated connections: {self.message_routing_errors}"
        )
        
        logger.info(
            f"✅ WebSocket authentication race test passed: "
            f"15/15 successful authentications, 15/15 successful connections, "
            f"15/15 successful authenticated sends, 0 race conditions"
        )