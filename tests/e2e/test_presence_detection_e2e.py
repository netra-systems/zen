"""
End-to-End Tests for Presence Detection System

Business Value Justification:
- Segment: All (Critical for chat functionality - 90% of value)
- Business Goal: User Experience & Chat Reliability
- Value Impact: Real-time presence is essential for chat interactions
- Strategic Impact: Validates complete presence flow in production-like environment

Tests complete presence detection flow with real services:
- Real WebSocket connections
- Real Redis/database
- Real authentication
- Production-like network conditions
- Multi-client scenarios
"""

import asyncio
import json
import time
import jwt
import websockets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
import pytest
import httpx
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from test_framework.conftest_real_services import (
    real_postgres,
    real_redis,
    real_backend_server,
    get_test_token,
    TEST_USER_EMAIL
)

logger = central_logger.get_logger(__name__)

# Test configuration
env = get_env()
BACKEND_URL = env.get("BACKEND_URL", "http://localhost:8000")
WS_URL = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://")


class WebSocketClient:
    """WebSocket client for E2E testing."""
    
    def __init__(self, user_id: str, token: str):
        self.user_id = user_id
        self.token = token
        self.websocket: Optional[websockets.ClientConnection] = None
        self.messages_received: List[Dict] = []
        self.connection_id: Optional[str] = None
        self.is_connected = False
        self.heartbeat_count = 0
        self.last_heartbeat_time = None
        
    async def connect(self):
        """Connect to WebSocket server with authentication."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Sec-WebSocket-Protocol": "jwt-auth"
        }
        
        try:
            self.websocket = await websockets.connect(
                f"{WS_URL}/ws",
                extra_headers=headers,
                subprotocols=["jwt-auth"]
            )
            self.is_connected = True
            
            # Start message receiver
            asyncio.create_task(self._receive_messages())
            
            # Wait for connection established message
            await self._wait_for_connection_established()
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
    
    async def send_message(self, message: Dict):
        """Send message to server."""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def send_heartbeat_response(self):
        """Send heartbeat response (pong)."""
        await self.send_message({
            "type": "pong",
            "timestamp": time.time()
        })
    
    async def _receive_messages(self):
        """Receive messages from server."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages_received.append(data)
                
                # Handle specific message types
                if data.get("type") == "system_message":
                    if data.get("data", {}).get("event") == "connection_established":
                        self.connection_id = data["data"].get("connection_id")
                        logger.info(f"Connection established: {self.connection_id}")
                
                elif data.get("type") == "ping" or "heartbeat" in str(data):
                    self.heartbeat_count += 1
                    self.last_heartbeat_time = time.time()
                    # Auto-respond to heartbeats
                    await self.send_heartbeat_response()
                    
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            self.is_connected = False
    
    async def _wait_for_connection_established(self, timeout: int = 5):
        """Wait for connection established message."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.connection_id:
                return
            await asyncio.sleep(0.1)
        raise TimeoutError("Connection established message not received")
    
    def get_messages_by_type(self, msg_type: str) -> List[Dict]:
        """Get all messages of a specific type."""
        return [msg for msg in self.messages_received if msg.get("type") == msg_type]


@pytest.fixture
async def auth_token(real_backend_server):
    """Get authentication token for testing."""
    return get_test_token()


@pytest.fixture
async def websocket_client(auth_token):
    """Create WebSocket client for testing."""
    client = WebSocketClient("test_user", auth_token)
    yield client
    if client.is_connected:
        await client.disconnect()


@pytest.mark.e2e
class TestPresenceDetectionE2E:
    """End-to-end tests for presence detection."""
    
    @pytest.mark.asyncio
    async def test_single_user_presence_lifecycle(self, websocket_client):
        """Test complete presence lifecycle for single user."""
        # Connect to WebSocket
        await websocket_client.connect()
        assert websocket_client.is_connected
        assert websocket_client.connection_id is not None
        
        # Wait for heartbeats
        await asyncio.sleep(3)
        
        # Should have received heartbeats
        assert websocket_client.heartbeat_count > 0
        
        # Send chat message to generate activity
        await websocket_client.send_message({
            "type": "chat_message",
            "content": "Test message for presence",
            "timestamp": time.time()
        })
        
        # Wait for more heartbeats
        await asyncio.sleep(2)
        
        # Verify continued heartbeats
        heartbeat_before_disconnect = websocket_client.heartbeat_count
        
        # Disconnect
        await websocket_client.disconnect()
        assert not websocket_client.is_connected
        
        # Verify heartbeats were received
        assert heartbeat_before_disconnect > 2
    
    @pytest.mark.asyncio
    async def test_multiple_users_presence(self, auth_token):
        """Test presence with multiple concurrent users."""
        clients = []
        
        # Create multiple clients
        for i in range(3):
            client = WebSocketClient(f"user_{i}", auth_token)
            await client.connect()
            clients.append(client)
        
        # All should be connected
        for client in clients:
            assert client.is_connected
            assert client.connection_id is not None
        
        # Wait for heartbeats
        await asyncio.sleep(3)
        
        # All should receive heartbeats
        for client in clients:
            assert client.heartbeat_count > 0
        
        # Disconnect clients one by one
        for i, client in enumerate(clients):
            await client.disconnect()
            
            # Remaining clients should still receive heartbeats
            await asyncio.sleep(1)
            for j, other_client in enumerate(clients):
                if j > i:  # Still connected
                    heartbeat_before = other_client.heartbeat_count
                    await asyncio.sleep(1)
                    # Should have received more heartbeats
                    if other_client.is_connected:
                        assert other_client.heartbeat_count > heartbeat_before
    
    @pytest.mark.asyncio
    async def test_presence_recovery_after_network_interruption(self, websocket_client):
        """Test presence recovery after simulated network interruption."""
        await websocket_client.connect()
        initial_connection_id = websocket_client.connection_id
        
        # Wait for initial heartbeats
        await asyncio.sleep(2)
        initial_heartbeat_count = websocket_client.heartbeat_count
        
        # Simulate network interruption by force closing WebSocket
        if websocket_client.websocket:
            await websocket_client.websocket.close(code=1006)  # Abnormal closure
        
        # Mark as disconnected
        websocket_client.is_connected = False
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Reconnect
        await websocket_client.connect()
        
        # Should have new connection ID
        assert websocket_client.connection_id != initial_connection_id
        
        # Should start receiving heartbeats again
        await asyncio.sleep(2)
        assert websocket_client.heartbeat_count > 0
    
    @pytest.mark.asyncio
    async def test_presence_with_chat_activity(self, websocket_client):
        """Test presence updates with chat activity."""
        await websocket_client.connect()
        
        # Record initial state
        await asyncio.sleep(1)
        heartbeats_before_activity = websocket_client.heartbeat_count
        
        # Send multiple chat messages
        for i in range(5):
            await websocket_client.send_message({
                "type": "chat_message",
                "content": f"Message {i}",
                "timestamp": time.time()
            })
            await asyncio.sleep(0.5)
        
        # Activity should keep presence alive
        await asyncio.sleep(2)
        
        # Should continue receiving heartbeats
        assert websocket_client.heartbeat_count > heartbeats_before_activity
        assert websocket_client.is_connected
    
    @pytest.mark.asyncio
    async def test_presence_timeout_simulation(self, auth_token):
        """Test presence timeout by not responding to heartbeats."""
        # Create client that doesn't auto-respond to heartbeats
        class NoResponseClient(WebSocketClient):
            async def _receive_messages(self):
                """Override to not respond to heartbeats."""
                try:
                    async for message in self.websocket:
                        data = json.loads(message)
                        self.messages_received.append(data)
                        
                        if data.get("type") == "system_message":
                            if data.get("data", {}).get("event") == "connection_established":
                                self.connection_id = data["data"].get("connection_id")
                        
                        # Don't respond to heartbeats
                        if data.get("type") == "ping" or "heartbeat" in str(data):
                            self.heartbeat_count += 1
                            self.last_heartbeat_time = time.time()
                            # NO RESPONSE
                            
                except websockets.exceptions.ConnectionClosed as e:
                    logger.info(f"Connection closed: {e.code} - {e.reason}")
                    self.is_connected = False
        
        client = NoResponseClient("timeout_user", auth_token)
        await client.connect()
        
        # Wait for timeout (should disconnect after missing heartbeats)
        start_time = time.time()
        timeout_duration = 10  # Maximum wait time
        
        while client.is_connected and (time.time() - start_time) < timeout_duration:
            await asyncio.sleep(0.5)
        
        # Should have been disconnected due to timeout
        assert not client.is_connected
        
        # Should have received some heartbeats before disconnect
        assert client.heartbeat_count > 0
    
    @pytest.mark.asyncio
    async def test_presence_with_rapid_reconnects(self, auth_token):
        """Test presence handling with rapid connect/disconnect cycles."""
        connection_ids = []
        
        for i in range(5):
            client = WebSocketClient(f"rapid_user_{i}", auth_token)
            
            # Connect
            await client.connect()
            connection_ids.append(client.connection_id)
            
            # Brief activity
            await client.send_message({
                "type": "chat_message",
                "content": f"Rapid message {i}",
                "timestamp": time.time()
            })
            
            # Quick disconnect
            await client.disconnect()
            
            # Small delay between connections
            await asyncio.sleep(0.2)
        
        # All connection IDs should be unique
        assert len(set(connection_ids)) == len(connection_ids)
    
    @pytest.mark.asyncio
    async def test_presence_statistics_endpoint(self, websocket_client, real_backend_server):
        """Test presence statistics via HTTP endpoint."""
        # Connect WebSocket
        await websocket_client.connect()
        
        # Wait for presence to be established
        await asyncio.sleep(2)
        
        # Query presence statistics (if endpoint exists)
        async with httpx.AsyncClient() as client:
            # Try to get WebSocket stats
            response = await client.get(
                f"{BACKEND_URL}/ws/stats",
                headers={"Authorization": f"Bearer {get_test_token()}"}
            )
            
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"Presence stats: {stats}")
                
                # Should show active connections
                assert "active_connections" in stats or "connections" in stats
    
    @pytest.mark.asyncio
    async def test_presence_cross_service_consistency(self, websocket_client, real_redis):
        """Test presence consistency across services via Redis."""
        await websocket_client.connect()
        connection_id = websocket_client.connection_id
        
        # Wait for presence to be established
        await asyncio.sleep(2)
        
        # Check Redis for presence data (if stored there)
        if real_redis:
            # Check for connection in Redis
            keys = await real_redis.keys("ws:conn:*")
            logger.info(f"WebSocket connection keys in Redis: {keys}")
            
            # Check for user presence
            user_keys = await real_redis.keys("presence:*")
            logger.info(f"Presence keys in Redis: {user_keys}")
        
        # Send activity
        await websocket_client.send_message({
            "type": "chat_message",
            "content": "Test for Redis consistency",
            "timestamp": time.time()
        })
        
        await asyncio.sleep(1)
        
        # Disconnect and check cleanup
        await websocket_client.disconnect()
        
        if real_redis:
            await asyncio.sleep(1)
            # Connection should be cleaned up
            remaining_keys = await real_redis.keys(f"ws:conn:{connection_id}")
            assert len(remaining_keys) == 0 or remaining_keys == []


@pytest.mark.e2e
class TestPresenceDetectionEdgeCases:
    """Test edge cases in presence detection E2E."""
    
    @pytest.mark.asyncio
    async def test_presence_with_invalid_auth(self):
        """Test presence behavior with invalid authentication."""
        invalid_token = "invalid.jwt.token"
        client = WebSocketClient("invalid_user", invalid_token)
        
        with pytest.raises(Exception):
            await client.connect()
        
        assert not client.is_connected
    
    @pytest.mark.asyncio
    async def test_presence_with_expired_token(self):
        """Test presence with expired JWT token."""
        # Create expired token
        secret_key = get_env().get("JWT_SECRET_KEY", "test-secret")
        expired_token = jwt.encode(
            {
                "sub": "test_user",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1)
            },
            secret_key,
            algorithm="HS256"
        )
        
        client = WebSocketClient("expired_user", expired_token)
        
        with pytest.raises(Exception):
            await client.connect()
        
        assert not client.is_connected
    
    @pytest.mark.asyncio
    async def test_presence_with_malformed_messages(self, websocket_client):
        """Test presence handling with malformed messages."""
        await websocket_client.connect()
        
        # Send various malformed messages
        malformed_messages = [
            "not json",
            '{"incomplete": ',
            '{"type": null}',
            '{"type": 123}',  # Wrong type
            '{}',  # Empty
        ]
        
        for msg in malformed_messages:
            try:
                if websocket_client.websocket:
                    await websocket_client.websocket.send(msg)
            except Exception:
                pass  # Expected to fail
            
            await asyncio.sleep(0.1)
        
        # Connection should still be alive despite malformed messages
        assert websocket_client.is_connected
        
        # Should still receive heartbeats
        await asyncio.sleep(2)
        assert websocket_client.heartbeat_count > 0
    
    @pytest.mark.asyncio
    async def test_presence_bandwidth_optimization(self, websocket_client):
        """Test that presence detection is bandwidth-efficient."""
        await websocket_client.connect()
        
        # Track message sizes
        message_sizes = []
        
        # Monitor for 5 seconds
        start_time = time.time()
        while time.time() - start_time < 5:
            if websocket_client.messages_received:
                last_msg = websocket_client.messages_received[-1]
                msg_size = len(json.dumps(last_msg))
                message_sizes.append(msg_size)
            await asyncio.sleep(0.1)
        
        # Heartbeat messages should be small
        if message_sizes:
            avg_size = sum(message_sizes) / len(message_sizes)
            logger.info(f"Average heartbeat message size: {avg_size} bytes")
            
            # Heartbeats should be efficient (< 200 bytes average)
            assert avg_size < 200
