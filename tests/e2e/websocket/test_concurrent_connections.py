"""WebSocket Concurrent Connection Test - Test #7

CRITICAL P1 Test: Multiple simultaneous connections per user (multi-tab/device scenarios)
Tests concurrent WebSocket connections for the same user across multiple tabs/devices.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Support power users with multiple browser tabs/devices
- Value Impact: Enables multi-tab workflows that enterprise users require
- Revenue Impact: Prevents user frustration and churn from multi-tab limitations

Core Requirements:
- Same user can open 5+ concurrent connections
- Messages broadcast to all user connections
- Connection limits per user enforced
- Independent connection lifecycle management
- One connection failure doesn't affect others
- Proper resource cleanup when connections close

Test Scenarios:
1. Multiple connections for same user (multi-tab simulation)
2. Message broadcasting to all user connections
3. Connection limits and enforcement
4. Independent connection lifecycle
5. Isolation of connection failures
6. Resource cleanup validation

Compliance: SPEC/unified_system_testing.xml, SPEC/websockets.xml
Performance: <5s execution, real connections only, no mocking
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Set

import httpx
import pytest

from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.real_client_types import ClientConfig, ConnectionState
from tests.e2e.real_websocket_client import RealWebSocketClient

class ConcurrentConnectionManager:
    """Manages multiple concurrent WebSocket connections for testing."""
    
    def __init__(self, max_connections: int = 10):
        """Initialize concurrent connection manager."""
        self.jwt_helper = JWTTestHelper()
        self.ws_url = "ws://localhost:8000/ws"
        self.config = ClientConfig(timeout=3.0, max_retries=1)
        self.max_connections = max_connections
        self.connections: Dict[str, RealWebSocketClient] = {}
        self.user_token: Optional[str] = None
        self.active_connections: Set[str] = set()
        self.auth_base_url = "http://localhost:8001"
        
    async def setup_user_authentication(self) -> None:
        """Create valid JWT token for testing."""
        payload = self.jwt_helper.create_valid_payload()
        self.user_token = self.jwt_helper.create_token(payload)
    
    def create_connection_client(self, connection_id: str) -> RealWebSocketClient:
        """Create WebSocket client for specific connection."""
        client = RealWebSocketClient(self.ws_url, self.config)
        self.connections[connection_id] = client
        return client
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for WebSocket."""
        return {"Authorization": f"Bearer {self.user_token}"}
    
    def get_authenticated_ws_url(self) -> str:
        """Get WebSocket URL with authentication token in query params."""
        if not self.user_token:
            raise ValueError("User token not set. Call setup_user_authentication() first.")
        return f"{self.ws_url}?token={self.user_token}"
    
    def get_connection_count(self) -> int:
        """Get current active connection count."""
        return len(self.active_connections)
    
    def is_connection_active(self, connection_id: str) -> bool:
        """Check if specific connection is active."""
        return connection_id in self.active_connections

class ConcurrentMessageBroadcaster:
    """Handles message broadcasting across concurrent connections."""
    
    def __init__(self, manager: ConcurrentConnectionManager):
        """Initialize broadcaster with connection manager."""
        self.manager = manager
        self.broadcast_messages: List[Dict] = []
        self.received_messages: Dict[str, List[Dict]] = {}
        
    def create_broadcast_message(self, sender_id: str) -> Dict[str, Any]:
        """Create test message for broadcasting."""
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "type": "chat_message",
            "content": f"Broadcast from {sender_id}",
            "sender": sender_id,
            "timestamp": time.time(),
            "broadcast": True
        }
        self.broadcast_messages.append(message)
        return message
    
    async def send_broadcast_message(self, sender_id: str) -> Dict[str, Any]:
        """Send message from specific connection for broadcasting."""
        client = self.manager.connections.get(sender_id)
        if not client:
            raise ValueError(f"Connection {sender_id} not found")
        
        message = self.create_broadcast_message(sender_id)
        success = await client.send(message)
        if not success:
            raise RuntimeError(f"Failed to send message from {sender_id}")
        return message
    
    async def collect_received_messages(self, connection_ids: List[str], 
                                      timeout: float = 2.0) -> Dict[str, List[Dict]]:
        """Collect messages received by all connections."""
        self.received_messages.clear()
        
        for conn_id in connection_ids:
            client = self.manager.connections.get(conn_id)
            if client:
                messages = await self._collect_connection_messages(client, conn_id, timeout)
                self.received_messages[conn_id] = messages
        
        return self.received_messages
    
    async def _collect_connection_messages(self, client: RealWebSocketClient, 
                                         connection_id: str, timeout: float) -> List[Dict]:
        """Collect messages from specific connection."""
        messages = []
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await client.receive(timeout=0.5)
                if message:
                    messages.append(message)
            except asyncio.TimeoutError:
                break
        
        return messages

class ConcurrentConnectionValidator:
    """Validates concurrent connection behavior and constraints."""
    
    def __init__(self):
        """Initialize connection validator."""
        self.validation_results: Dict[str, Any] = {}
        
    def validate_connection_establishment(self, manager: ConcurrentConnectionManager,
                                        target_count: int) -> Dict[str, Any]:
        """Validate that target number of connections established."""
        actual_count = manager.get_connection_count()
        return {
            "target_connections": target_count,
            "actual_connections": actual_count,
            "establishment_success": actual_count >= target_count,
            "all_connections_active": self._validate_all_active(manager)
        }
    
    def validate_message_broadcast(self, broadcaster: ConcurrentMessageBroadcaster,
                                 sender_id: str, receiver_ids: List[str]) -> Dict[str, Any]:
        """Validate message broadcasting to all receivers."""
        sender_messages = broadcaster.received_messages.get(sender_id, [])
        broadcast_results = {}
        
        for receiver_id in receiver_ids:
            if receiver_id != sender_id:  # Skip sender
                receiver_messages = broadcaster.received_messages.get(receiver_id, [])
                broadcast_results[receiver_id] = self._check_message_received(
                    broadcaster.broadcast_messages, receiver_messages
                )
        
        return {
            "sender_id": sender_id,
            "receivers_tested": len(receiver_ids) - 1,
            "successful_broadcasts": sum(1 for result in broadcast_results.values() if result),
            "broadcast_results": broadcast_results,
            "broadcast_success": all(broadcast_results.values())
        }
    
    def validate_connection_isolation(self, manager: ConcurrentConnectionManager,
                                    failed_connection: str, active_connections: List[str]) -> Dict[str, Any]:
        """Validate that one connection failure doesn't affect others."""
        isolation_results = {}
        
        for conn_id in active_connections:
            if conn_id != failed_connection:
                client = manager.connections.get(conn_id)
                is_isolated = client and client.state == ConnectionState.CONNECTED
                isolation_results[conn_id] = is_isolated
        
        return {
            "failed_connection": failed_connection,
            "active_connections_tested": len(active_connections) - 1,
            "isolation_success": all(isolation_results.values()),
            "isolation_results": isolation_results
        }
    
    def _validate_all_active(self, manager: ConcurrentConnectionManager) -> bool:
        """Check if all registered connections are active."""
        for conn_id in manager.connections:
            client = manager.connections[conn_id]
            if not client or client.state != ConnectionState.CONNECTED:
                return False
        return True
    
    def _check_message_received(self, sent_messages: List[Dict], 
                               received_messages: List[Dict]) -> bool:
        """Check if any sent message was received."""
        if not sent_messages or not received_messages:
            return False
        
        sent_ids = {msg.get("id") for msg in sent_messages}
        received_ids = {msg.get("id") for msg in received_messages}
        return bool(sent_ids.intersection(received_ids))

class ConnectionLimitManager:
    """Manages and tests connection limits per user."""
    
    def __init__(self, limit: int = 5):
        """Initialize connection limit manager."""
        self.connection_limit = limit
        self.limit_test_results: Dict[str, Any] = {}
        
    async def test_connection_limit_enforcement(self, manager: ConcurrentConnectionManager) -> Dict[str, Any]:
        """Test that connection limits are properly enforced."""
        # Try to create more connections than the limit
        excess_connections = self.connection_limit + 3
        successful_connections = 0
        rejected_connections = 0
        
        authenticated_url = manager.get_authenticated_ws_url()
        
        for i in range(excess_connections):
            conn_id = f"limit_test_conn_{i}"
            # Create client with authenticated URL that includes token
            client = RealWebSocketClient(authenticated_url, manager.config)
            manager.connections[conn_id] = client
            
            # Connect without headers since token is in URL
            success = await client.connect()
            if success:
                successful_connections += 1
                manager.active_connections.add(conn_id)
            else:
                rejected_connections += 1
        
        return {
            "connection_limit": self.connection_limit,
            "attempted_connections": excess_connections,
            "successful_connections": successful_connections,
            "rejected_connections": rejected_connections,
            "limit_enforced": successful_connections <= self.connection_limit,
            "excess_rejected": rejected_connections > 0
        }

@pytest.mark.asyncio
@pytest.mark.integration
class TestConcurrentConnections:
    """Test #7: Concurrent Connection Test - Multiple simultaneous connections per user."""
    
    @pytest.fixture
    def connection_manager(self):
        """Initialize concurrent connection manager."""
        return ConcurrentConnectionManager(max_connections=10)
    
    @pytest.fixture
    def message_broadcaster(self, connection_manager):
        """Initialize message broadcaster."""
        return ConcurrentMessageBroadcaster(connection_manager)
    
    @pytest.fixture
    def connection_validator(self):
        """Initialize connection validator."""
        return ConcurrentConnectionValidator()
    
    @pytest.fixture
    def limit_manager(self):
        """Initialize connection limit manager."""
        return ConnectionLimitManager(limit=5)
    
    async def test_concurrent_connections_core_functionality(self, connection_manager:
                                                           message_broadcaster, connection_validator):
        """Test core concurrent connection functionality."""
        start_time = time.time()
        
        try:
            await self._setup_test_environment(connection_manager)
            await self._execute_concurrent_connection_test(connection_manager, message_broadcaster, connection_validator)
            execution_time = time.time() - start_time
            assert execution_time < 5.0, f"Test took {execution_time:.2f}s, expected < 5s"
        finally:
            await self._cleanup_all_connections(connection_manager)
    
    async def test_connection_limit_enforcement(self, connection_manager, limit_manager):
        """Test that connection limits per user are enforced."""
        start_time = time.time()
        
        try:
            await self._setup_test_environment(connection_manager)
            limit_results = await limit_manager.test_connection_limit_enforcement(connection_manager)
            
            assert limit_results["limit_enforced"], "Connection limit not enforced"
            assert limit_results["successful_connections"] <= limit_manager.connection_limit, \
                f"Too many connections allowed: {limit_results['successful_connections']}"
            
            execution_time = time.time() - start_time
            assert execution_time < 5.0, f"Limit test took {execution_time:.2f}s, expected < 5s"
        finally:
            await self._cleanup_all_connections(connection_manager)
    
    async def test_connection_failure_isolation(self, connection_manager, connection_validator):
        """Test that one connection failure doesn't affect others."""
        start_time = time.time()
        
        try:
            await self._setup_test_environment(connection_manager)
            connection_ids = await self._establish_multiple_connections(connection_manager, 3)
            
            # Force one connection to fail
            failed_conn = connection_ids[1]
            await self._force_connection_failure(connection_manager, failed_conn)
            
            # Validate other connections remain active
            isolation_results = connection_validator.validate_connection_isolation(
                connection_manager, failed_conn, connection_ids
            )
            
            assert isolation_results["isolation_success"], "Connection failure affected other connections"
            
            execution_time = time.time() - start_time
            assert execution_time < 5.0, f"Isolation test took {execution_time:.2f}s, expected < 5s"
        finally:
            await self._cleanup_all_connections(connection_manager)
    
    async def _setup_test_environment(self, manager: ConcurrentConnectionManager) -> None:
        """Set up test environment with user token."""
        await manager.setup_user_authentication()
    
    async def _execute_concurrent_connection_test(self, manager: ConcurrentConnectionManager,
                                                broadcaster: ConcurrentMessageBroadcaster,
                                                validator: ConcurrentConnectionValidator) -> None:
        """Execute main concurrent connection test flow."""
        # Establish multiple connections
        connection_ids = await self._establish_multiple_connections(manager, 5)
        
        # Validate connection establishment
        await self._validate_connection_establishment(manager, validator, 5)
        
        # Test message broadcasting
        await self._validate_message_broadcasting(broadcaster, validator, connection_ids)
        
        # Test resource cleanup
        await self._validate_resource_cleanup(manager, connection_ids[2:4])  # Close 2 connections
    
    async def _establish_multiple_connections(self, manager: ConcurrentConnectionManager, 
                                            count: int) -> List[str]:
        """Establish multiple WebSocket connections."""
        connection_ids = []
        authenticated_url = manager.get_authenticated_ws_url()
        
        for i in range(count):
            conn_id = f"concurrent_conn_{i}"
            # Create client with authenticated URL that includes token
            client = RealWebSocketClient(authenticated_url, manager.config)
            manager.connections[conn_id] = client
            
            # Connect without headers since token is in URL
            success = await client.connect()
            if success:
                connection_ids.append(conn_id)
                manager.active_connections.add(conn_id)
        
        return connection_ids
    
    async def _validate_connection_establishment(self, manager: ConcurrentConnectionManager,
                                               validator: ConcurrentConnectionValidator, 
                                               target_count: int) -> None:
        """Validate that connections were established successfully."""
        results = validator.validate_connection_establishment(manager, target_count)
        
        assert results["establishment_success"], \
            f"Failed to establish {target_count} connections, got {results['actual_connections']}"
        assert results["all_connections_active"], "Not all connections are active"
    
    async def _validate_message_broadcasting(self, broadcaster: ConcurrentMessageBroadcaster,
                                           validator: ConcurrentConnectionValidator,
                                           connection_ids: List[str]) -> None:
        """Validate message broadcasting across connections."""
        if len(connection_ids) < 2:
            return  # Need at least 2 connections for broadcast test
        
        # Send message from first connection
        sender_id = connection_ids[0]
        await broadcaster.send_broadcast_message(sender_id)
        
        # Wait for message propagation
        await asyncio.sleep(1.0)
        
        # Collect received messages
        await broadcaster.collect_received_messages(connection_ids)
        
        # Validate broadcast
        broadcast_results = validator.validate_message_broadcast(
            broadcaster, sender_id, connection_ids
        )
        
        assert broadcast_results["broadcast_success"], \
            f"Message not broadcast to all connections: {broadcast_results['broadcast_results']}"
    
    async def _validate_resource_cleanup(self, manager: ConcurrentConnectionManager,
                                       connections_to_close: List[str]) -> None:
        """Validate proper resource cleanup when connections close."""
        initial_count = manager.get_connection_count()
        
        # Close specified connections
        for conn_id in connections_to_close:
            await self._close_connection_safely(manager, conn_id)
        
        final_count = manager.get_connection_count()
        expected_count = initial_count - len(connections_to_close)
        
        assert final_count == expected_count, \
            f"Resource cleanup failed: expected {expected_count} connections, got {final_count}"
    
    async def _force_connection_failure(self, manager: ConcurrentConnectionManager, 
                                      connection_id: str) -> None:
        """Force a specific connection to fail."""
        client = manager.connections.get(connection_id)
        if client:
            await client.close()
            client.state = ConnectionState.FAILED
            manager.active_connections.discard(connection_id)
    
    async def _close_connection_safely(self, manager: ConcurrentConnectionManager, 
                                     connection_id: str) -> None:
        """Safely close a connection and update tracking."""
        client = manager.connections.get(connection_id)
        if client:
            await client.close()
            manager.active_connections.discard(connection_id)
            del manager.connections[connection_id]
    
    async def _cleanup_all_connections(self, manager: ConcurrentConnectionManager) -> None:
        """Clean up all WebSocket connections."""
        for conn_id, client in manager.connections.items():
            try:
                await client.close()
            except Exception:
                pass  # Best effort cleanup
        
        manager.connections.clear()
        manager.active_connections.clear()
