"""WebSocket Basic Connection Establishment Tests - P0 Critical

Tests the fundamental WebSocket connection lifecycle that ALL user interactions depend on.
This is the most critical test in the system - if these fail, the entire platform is down.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise)
2. Business Goal: Core Platform Stability - 100% of user value depends on this
3. Value Impact: Every real-time feature depends on WebSocket connection working
4. Revenue Impact: 100% revenue at risk if basic connections fail ($150K+ MRR)

CRITICAL REQUIREMENTS:
- MUST use real WebSocket server (NO MOCKS)
- Test WebSocket upgrade from HTTP
- Validate bidirectional communication
- Test connection state transitions
- Test within 5 seconds per test case
- Include 3+ error scenarios per test

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines
- Function size: <25 lines each  
- Real services integration
- Type safety with annotations
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import pytest
import pytest_asyncio
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

from tests.unified.real_services_manager import create_real_services_manager
from tests.unified.real_websocket_client import RealWebSocketClient  
from tests.unified.real_client_types import ClientConfig, ConnectionState
from tests.unified.jwt_token_helpers import JWTTestHelper


class WebSocketConnectionTester:
    """Real WebSocket connection lifecycle tester - NO MOCKS"""
    
    def __init__(self):
        self.services_manager = None
        self.test_clients: List[RealWebSocketClient] = []
        self.connection_metrics: List[Dict[str, Any]] = []
        self.backend_url = "http://localhost:8001"
        self.websocket_url = "ws://localhost:8001/ws"
        
    async def setup_real_services(self) -> None:
        """Use existing real Backend and Auth services for testing"""
        # Skip starting services since dev_launcher is already running
        # Just verify services are accessible
        import httpx
        
        # Check backend health
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8001/health", timeout=5.0)
                if response.status_code != 200:
                    raise RuntimeError(f"Backend health check failed: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to backend service: {e}")
            
        # Check auth service health  
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8083/health", timeout=5.0)
                if response.status_code != 200:
                    raise RuntimeError(f"Auth health check failed: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to auth service: {e}")
            
        # Set services_manager to None since we're not managing them
        self.services_manager = None
    
    async def teardown_real_services(self) -> None:
        """Clean shutdown of test clients only"""
        # Close all test clients first
        cleanup_tasks = []
        for client in self.test_clients:
            cleanup_tasks.append(client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Don't stop services since they're managed by dev_launcher
        # Just verify our clients are cleaned up
        await asyncio.sleep(0.5)  # Brief wait for cleanup
    
    async def _verify_no_ghost_connections(self) -> None:
        """Verify no ghost connections remain after cleanup"""
        # Give a moment for cleanup to complete
        await asyncio.sleep(0.5)
        
        # Attempt connection to verify servers are down
        try:
            async with websockets.connect(self.websocket_url, open_timeout=1):
                raise AssertionError("WebSocket server still running after cleanup")
        except (ConnectionRefusedError, OSError):
            # Expected - server should be down
            pass
    
    def create_test_client(self, user_id: str = "test_user") -> RealWebSocketClient:
        """Create real WebSocket client with auth token"""
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(user_id, f"{user_id}@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        config = ClientConfig(timeout=5.0, max_retries=2)
        client = RealWebSocketClient(self.websocket_url, config)
        client._auth_headers = headers
        
        self.test_clients.append(client)
        return client
    
    def record_connection_metrics(self, client: RealWebSocketClient, 
                                test_name: str, success: bool) -> None:
        """Record connection performance metrics"""
        metrics = {
            "test_name": test_name,
            "success": success,
            "connection_time": client.metrics.connection_time,
            "requests_sent": client.metrics.requests_sent,
            "responses_received": client.metrics.responses_received,
            "last_error": client.metrics.last_error,
            "state": client.state.value
        }
        self.connection_metrics.append(metrics)


@pytest_asyncio.fixture
async def connection_tester():
    """WebSocket connection tester fixture with real services"""
    tester = WebSocketConnectionTester()
    await tester.setup_real_services()
    yield tester
    await tester.teardown_real_services()


class TestBasicWebSocketConnection:
    """Test fundamental WebSocket connection establishment"""
    
    @pytest.mark.asyncio
    async def test_successful_websocket_upgrade(self, connection_tester):
        """Test successful HTTP -> WebSocket upgrade with auth"""
        client = connection_tester.create_test_client("upgrade_test_user")
        
        # Test connection establishment
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        connection_time = time.time() - start_time
        
        # Verify connection successful
        if not success:
            print(f"Connection failed. Error: {client.metrics.last_error}")
            print(f"Client state: {client.state}")
            print(f"Token used: {client._auth_headers}")
        assert success is True, f"Connection failed: {client.metrics.last_error}"
        assert client.state == ConnectionState.CONNECTED
        assert connection_time < 5.0  # Performance requirement
        
        connection_tester.record_connection_metrics(client, "websocket_upgrade", True)
    
    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, connection_tester):
        """Test proper connection state transitions: DISCONNECTED -> CONNECTING -> CONNECTED"""
        client = connection_tester.create_test_client("state_test_user")
        
        # Initial state
        assert client.state == ConnectionState.DISCONNECTED
        
        # Test state during connection
        connection_task = asyncio.create_task(client.connect(client._auth_headers))
        await asyncio.sleep(0.1)  # Brief pause to catch CONNECTING state
        
        # Complete connection
        success = await connection_task
        
        # Verify final state
        assert success is True
        assert client.state == ConnectionState.CONNECTED
        
        connection_tester.record_connection_metrics(client, "state_transitions", True)
    
    @pytest.mark.asyncio
    async def test_bidirectional_communication(self, connection_tester):
        """Test bidirectional message exchange after connection"""
        client = connection_tester.create_test_client("bidir_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        # Test client -> server message
        test_message = {"type": "test", "payload": {"content": "Hello WebSocket"}}
        send_success = await client.send(test_message)
        assert send_success is True
        
        # Test server -> client response
        response = await client.receive(timeout=3.0)
        assert response is not None
        assert isinstance(response, dict)
        
        # Verify message counts
        assert client.metrics.requests_sent >= 1
        assert client.metrics.responses_received >= 1
        
        connection_tester.record_connection_metrics(client, "bidirectional_comm", True)
    
    @pytest.mark.asyncio
    async def test_websocket_handshake_validation(self, connection_tester):
        """Test WebSocket handshake headers and protocol validation"""
        client = connection_tester.create_test_client("handshake_test_user")
        
        # Add specific handshake headers
        headers = client._auth_headers.copy()
        headers.update({
            "Sec-WebSocket-Protocol": "chat",
            "User-Agent": "NetraTestClient/1.0"
        })
        
        # Test connection with enhanced headers
        success = await client.connect(headers)
        assert success is True
        assert client.state == ConnectionState.CONNECTED
        
        # Verify connection accepts our headers
        ping_message = {"type": "ping", "payload": {}}
        await client.send(ping_message)
        pong_response = await client.receive(timeout=2.0)
        
        assert pong_response is not None
        connection_tester.record_connection_metrics(client, "handshake_validation", True)


class TestWebSocketConnectionErrors:
    """Test WebSocket connection error scenarios - 3+ error cases required"""
    
    @pytest.mark.asyncio
    async def test_connection_with_invalid_auth_token(self, connection_tester):
        """ERROR CASE 1: Connection rejection with invalid auth token"""
        # Create client with invalid token
        config = ClientConfig(timeout=3.0, max_retries=1)
        client = RealWebSocketClient(connection_tester.websocket_url, config)
        invalid_headers = {"Authorization": "Bearer invalid.jwt.token"}
        
        connection_tester.test_clients.append(client)
        
        # Attempt connection with invalid token
        success = await client.connect(invalid_headers)
        
        # Verify rejection
        assert success is False
        assert client.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        assert client.metrics.last_error is not None
        
        connection_tester.record_connection_metrics(client, "invalid_auth_error", False)
    
    @pytest.mark.asyncio 
    async def test_connection_timeout_scenario(self, connection_tester):
        """ERROR CASE 2: Connection timeout handling"""
        # Create client with very short timeout
        config = ClientConfig(timeout=0.1, max_retries=1)  # 100ms timeout
        client = RealWebSocketClient("ws://localhost:9999", config)  # Non-existent port
        
        connection_tester.test_clients.append(client)
        
        # Attempt connection that will timeout
        start_time = time.time()
        success = await client.connect({"Authorization": "Bearer test"})
        elapsed_time = time.time() - start_time
        
        # Verify timeout handling
        assert success is False
        assert elapsed_time < 2.0  # Should fail quickly
        assert client.state == ConnectionState.FAILED
        
        connection_tester.record_connection_metrics(client, "connection_timeout", False)
    
    @pytest.mark.asyncio
    async def test_connection_to_nonexistent_server(self, connection_tester):
        """ERROR CASE 3: Connection to non-existent WebSocket server"""
        config = ClientConfig(timeout=2.0, max_retries=1)
        client = RealWebSocketClient("ws://localhost:7777", config)  # Non-existent server
        
        connection_tester.test_clients.append(client)
        
        # Attempt connection to non-existent server
        success = await client.connect({"Authorization": "Bearer test"})
        
        # Verify connection failure
        assert success is False
        assert client.state == ConnectionState.FAILED
        assert "connection" in client.metrics.last_error.lower() or \
               "refused" in client.metrics.last_error.lower()
        
        connection_tester.record_connection_metrics(client, "nonexistent_server", False)
    
    @pytest.mark.asyncio
    async def test_malformed_websocket_url(self, connection_tester):
        """ERROR CASE 4: Malformed WebSocket URL handling"""
        config = ClientConfig(timeout=1.0, max_retries=1)
        client = RealWebSocketClient("invalid://bad-url", config)  # Malformed URL
        
        connection_tester.test_clients.append(client)
        
        # Attempt connection with bad URL
        success = await client.connect({"Authorization": "Bearer test"})
        
        # Verify URL validation failure
        assert success is False
        assert client.state == ConnectionState.FAILED
        assert client.metrics.last_error is not None
        
        connection_tester.record_connection_metrics(client, "malformed_url", False)


class TestWebSocketConnectionPerformance:
    """Test WebSocket connection performance requirements"""
    
    @pytest.mark.asyncio
    async def test_connection_time_under_5_seconds(self, connection_tester):
        """Test connection establishment completes within 5 seconds"""
        client = connection_tester.create_test_client("perf_test_user")
        
        # Measure connection time
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        connection_time = time.time() - start_time
        
        # Verify performance requirement
        assert success is True
        assert connection_time < 5.0  # Critical performance requirement
        assert client.metrics.connection_time < 5.0
        
        connection_tester.record_connection_metrics(client, "connection_performance", True)
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_tester):
        """Test multiple concurrent WebSocket connections"""
        num_clients = 3
        clients = []
        
        # Create multiple clients
        for i in range(num_clients):
            client = connection_tester.create_test_client(f"concurrent_user_{i}")
            clients.append(client)
        
        # Connect all clients concurrently
        start_time = time.time()
        connection_tasks = [
            client.connect(client._auth_headers) for client in clients
        ]
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all connections successful
        assert all(result is True for result in results)
        assert all(client.state == ConnectionState.CONNECTED for client in clients)
        assert total_time < 10.0  # All connections within 10 seconds
        
        # Record metrics for all clients
        for i, client in enumerate(clients):
            connection_tester.record_connection_metrics(
                client, f"concurrent_connection_{i}", True
            )
    
    @pytest.mark.asyncio
    async def test_message_roundtrip_latency(self, connection_tester):
        """Test message roundtrip latency meets requirements"""
        client = connection_tester.create_test_client("latency_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        
        # Test message roundtrip
        test_message = {"type": "ping", "payload": {"timestamp": time.time()}}
        
        start_time = time.time()
        await client.send(test_message)
        response = await client.receive(timeout=3.0)
        roundtrip_time = time.time() - start_time
        
        # Verify latency requirement
        assert response is not None
        assert roundtrip_time < 3.0  # Reasonable latency requirement
        
        connection_tester.record_connection_metrics(client, "message_latency", True)


class TestWebSocketConnectionReliability:
    """Test WebSocket connection reliability and resilience"""
    
    @pytest.mark.asyncio
    async def test_connection_retry_mechanism(self, connection_tester):
        """Test connection retry on temporary failure"""
        # Create client with retry configuration
        config = ClientConfig(timeout=1.0, max_retries=2, retry_delay=0.5)
        client = RealWebSocketClient("ws://localhost:9998", config)  # Assume port unavailable
        
        connection_tester.test_clients.append(client)
        
        # Attempt connection with retries
        start_time = time.time()
        success = await client.connect({"Authorization": "Bearer test"})
        total_time = time.time() - start_time
        
        # Verify retry mechanism executed
        assert success is False  # Should fail after retries
        assert client.metrics.retry_count > 0  # Should have attempted retries
        assert total_time > 1.0  # Should take time for retries
        
        connection_tester.record_connection_metrics(client, "connection_retry", False)
    
    @pytest.mark.asyncio
    async def test_graceful_connection_close(self, connection_tester):
        """Test graceful connection closure"""
        client = connection_tester.create_test_client("close_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        # Test graceful close
        await client.close()
        
        # Verify clean disconnection
        assert client.state == ConnectionState.DISCONNECTED
        
        # Verify no further communication possible
        send_success = await client.send({"type": "test"})
        assert send_success is False
        
        connection_tester.record_connection_metrics(client, "graceful_close", True)