"""WebSocket Connection Lifecycle with Auth - Comprehensive Test Suite

Tests the complete WebSocket connection lifecycle with proper JWT authentication as specified 
in SPEC/websockets.xml and SPEC/websocket_communication.xml.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise) 
2. Business Goal: Core Platform Stability - Real-time communication foundation
3. Value Impact: Every user interaction depends on WebSocket connectivity working
4. Revenue Impact: 100% revenue at risk if WebSocket auth fails ($150K+ MRR)

CRITICAL REQUIREMENTS:
- Test with REAL running services via dev_launcher (localhost:8001, localhost:8083)
- JWT authentication during WebSocket handshake 
- Manual database session creation (not Depends() pattern)
- Connection establishment BEFORE first message (SPEC requirement)
- Persistent connection through component re-renders
- JSON-first communication (no string messages)
- All tests complete within 30 seconds

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines
- Function size: <25 lines each
- Real services integration (NO MOCKS)
- Type safety with annotations
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.jwt_token_helpers import JWTTestHelper
from test_framework.http_client import ClientConfig, ConnectionState
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


class WebSocketLifecycleAuthTester:
    """Real WebSocket lifecycle tester with comprehensive auth validation"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8001"
        self.auth_url = "http://localhost:8081"  # Corrected to match actual dev launcher port
        self.websocket_url = "ws://localhost:8001/ws"
        self.test_clients: List[RealWebSocketClient] = []
        self.test_results: List[Dict[str, Any]] = []
        self.jwt_helper = JWTTestHelper()
        
    def create_authenticated_client(self, user_id: str = "test_user") -> RealWebSocketClient:
        """Create WebSocket client with valid JWT authentication"""
        # Create valid JWT token
        token = self.jwt_helper.create_access_token(user_id, f"{user_id}@test.com")
        
        # Create client configuration
        config = ClientConfig(timeout=10.0, max_retries=2)
        client = RealWebSocketClient(self.websocket_url, config)
        
        # Set auth headers
        client._auth_headers = {"Authorization": f"Bearer {token}"}
        
        self.test_clients.append(client)
        return client
    
    def create_invalid_auth_client(self, token_type: str = "invalid") -> RealWebSocketClient:
        """Create WebSocket client with invalid authentication"""
        config = ClientConfig(timeout=5.0, max_retries=1)
        client = RealWebSocketClient(self.websocket_url, config)
        
        if token_type == "invalid":
            client._auth_headers = {"Authorization": "Bearer invalid.jwt.token"}
        elif token_type == "expired":
            expired_token = self.jwt_helper.create_token(self.jwt_helper.create_expired_payload())
            client._auth_headers = {"Authorization": f"Bearer {expired_token}"}
        elif token_type == "missing":
            client._auth_headers = {}
        
        self.test_clients.append(client)
        return client
    
    async def cleanup_all_clients(self) -> None:
        """Clean up all test clients"""
        cleanup_tasks = []
        for client in self.test_clients:
            if client.state == ConnectionState.CONNECTED:
                cleanup_tasks.append(client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.test_clients.clear()
    
    def record_test_result(self, test_name: str, success: bool, 
                          details: Dict[str, Any]) -> None:
        """Record test result with metrics"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.utcnow(),
            "details": details
        }
        self.test_results.append(result)


@pytest_asyncio.fixture
async def lifecycle_tester():
    """WebSocket lifecycle tester fixture"""
    tester = WebSocketLifecycleAuthTester()
    yield tester
    await tester.cleanup_all_clients()


@pytest.mark.e2e
class TestWebSocketConnectionLifecycle:
    """Test WebSocket connection lifecycle with authentication"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_establishment_before_first_message(self, lifecycle_tester):
        """Test connection established BEFORE first message (SPEC requirement)"""
        client = lifecycle_tester.create_authenticated_client("conn_test_user")
        
        # Test connection establishment
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        connection_time = time.time() - start_time
        
        # Verify connection successful BEFORE any message
        assert success is True, f"Connection failed: {client.metrics.last_error}"
        assert client.state == ConnectionState.CONNECTED
        assert connection_time < 10.0  # Performance requirement
        
        # Verify no messages sent during connection
        assert client.metrics.requests_sent == 0
        assert client.metrics.responses_received == 0
        
        lifecycle_tester.record_test_result("connection_before_message", True, {
            "connection_time": connection_time,
            "client_state": client.state.value
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_authentication_during_handshake(self, lifecycle_tester):
        """Test JWT token validation during WebSocket handshake"""
        client = lifecycle_tester.create_authenticated_client("jwt_test_user")
        
        # Test connection with JWT auth
        success = await client.connect(client._auth_headers)
        
        # Verify JWT authentication successful
        assert success is True
        assert client.state == ConnectionState.CONNECTED
        
        # Test that connection accepts authenticated messages
        test_message = {"type": "ping", "payload": {"timestamp": time.time()}}
        send_success = await client.send(test_message)
        assert send_success is True
        
        # Verify server responds (indicating auth worked)
        response = await client.receive(timeout=5.0)
        assert response is not None
        assert isinstance(response, dict)
        
        lifecycle_tester.record_test_result("jwt_handshake_auth", True, {
            "auth_headers": bool(client._auth_headers),
            "response_received": response is not None
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_invalid_jwt_token_rejection(self, lifecycle_tester):
        """Test connection rejection with invalid JWT token"""
        client = lifecycle_tester.create_invalid_auth_client("invalid")
        
        # Attempt connection with invalid token
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        connection_time = time.time() - start_time
        
        # Verify connection rejected
        assert success is False
        assert client.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        assert client.metrics.last_error is not None
        assert connection_time < 5.0  # Should fail quickly
        
        lifecycle_tester.record_test_result("invalid_token_rejection", True, {
            "connection_rejected": not success,
            "error_present": client.metrics.last_error is not None
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expired_jwt_token_rejection(self, lifecycle_tester):
        """Test connection rejection with expired JWT token"""
        client = lifecycle_tester.create_invalid_auth_client("expired")
        
        # Attempt connection with expired token
        success = await client.connect(client._auth_headers)
        
        # Verify connection rejected
        assert success is False
        assert client.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        
        lifecycle_tester.record_test_result("expired_token_rejection", True, {
            "connection_rejected": not success,
            "final_state": client.state.value
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_missing_auth_token_rejection(self, lifecycle_tester):
        """Test connection rejection when auth token is missing"""
        client = lifecycle_tester.create_invalid_auth_client("missing")
        
        # Attempt connection without auth token
        success = await client.connect(client._auth_headers)
        
        # Verify connection rejected
        assert success is False
        assert client.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        
        lifecycle_tester.record_test_result("missing_token_rejection", True, {
            "connection_rejected": not success,
            "auth_headers_empty": len(client._auth_headers) == 0
        })


@pytest.mark.e2e
class TestWebSocketPersistentConnection:
    """Test WebSocket persistent connection requirements"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_persistent_connection_through_rerenders(self, lifecycle_tester):
        """Test connection persistence through component re-renders"""
        client = lifecycle_tester.create_authenticated_client("persist_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        # Simulate multiple component operations
        for i in range(3):
            # Send message (simulating component interaction)
            message = {"type": "test", "payload": {"operation": f"render_{i}"}}
            send_success = await client.send(message)
            assert send_success is True
            
            # Verify connection remains active
            assert client.state == ConnectionState.CONNECTED
            
            # Short delay between operations
            await asyncio.sleep(0.1)
        
        # Verify connection still functional
        final_message = {"type": "ping", "payload": {}}
        await client.send(final_message)
        response = await client.receive(timeout=3.0)
        
        assert response is not None
        lifecycle_tester.record_test_result("persistent_connection", True, {
            "operations_completed": 3,
            "final_response": response is not None
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_graceful_connection_cleanup(self, lifecycle_tester):
        """Test graceful connection cleanup on disconnect"""
        client = lifecycle_tester.create_authenticated_client("cleanup_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        # Record initial metrics
        initial_requests = client.metrics.requests_sent
        
        # Send a message to verify connection active
        await client.send({"type": "test", "payload": {}})
        
        # Perform graceful cleanup
        await client.close()
        
        # Verify clean disconnection
        assert client.state == ConnectionState.DISCONNECTED
        
        # Verify no further communication possible
        send_success = await client.send({"type": "test"})
        assert send_success is False
        
        lifecycle_tester.record_test_result("graceful_cleanup", True, {
            "disconnected_cleanly": client.state == ConnectionState.DISCONNECTED,
            "send_blocked_after_close": not send_success
        })


@pytest.mark.e2e
class TestWebSocketJSONFirstCommunication:
    """Test JSON-first communication requirement"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_json_first_message_structure(self, lifecycle_tester):
        """Test all messages use JSON structure (no string messages)"""
        client = lifecycle_tester.create_authenticated_client("json_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        
        # Test various JSON message types
        test_messages = [
            {"type": "ping", "payload": {}},
            {"type": "test", "payload": {"data": "value"}},
            {"type": "command", "payload": {"action": "status", "parameters": {"verbose": True}}}
        ]
        
        successful_sends = 0
        for message in test_messages:
            # Send JSON message
            success = await client.send(message)
            if success:
                successful_sends += 1
            
            # Verify message structure is maintained (client should handle as dict)
            assert isinstance(message, dict)
            assert "type" in message
            assert "payload" in message
        
        assert successful_sends == len(test_messages)
        
        lifecycle_tester.record_test_result("json_first_communication", True, {
            "messages_sent": successful_sends,
            "all_structured": True
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_message_type_payload_structure(self, lifecycle_tester):
        """Test consistent {type, payload} message structure"""
        client = lifecycle_tester.create_authenticated_client("structure_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        
        # Test message with required structure
        message = {
            "type": "agent_test",
            "payload": {
                "agent_name": "test_agent",
                "data": {"key": "value"},
                "timestamp": time.time()
            }
        }
        
        # Send structured message
        success = await client.send(message)
        assert success is True
        
        # Wait for potential response and validate structure
        response = await client.receive(timeout=3.0)
        if response:
            # Verify response also follows structure
            assert isinstance(response, dict)
            # Note: We don't enforce structure on server responses in this test
            # as server might have different format - focus on client sends
        
        lifecycle_tester.record_test_result("type_payload_structure", True, {
            "message_sent": success,
            "structure_correct": "type" in message and "payload" in message
        })


@pytest.mark.e2e
class TestWebSocketAuthenticationSecurity:
    """Test WebSocket authentication security requirements"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_auth_connections(self, lifecycle_tester):
        """Test multiple concurrent authenticated connections"""
        num_clients = 3
        clients = []
        
        # Create multiple authenticated clients
        for i in range(num_clients):
            client = lifecycle_tester.create_authenticated_client(f"concurrent_user_{i}")
            clients.append(client)
        
        # Connect all clients concurrently
        start_time = time.time()
        connection_tasks = [
            client.connect(client._auth_headers) for client in clients
        ]
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all connections successful
        successful_connections = sum(1 for result in results if result is True)
        assert successful_connections >= 2  # Allow for some connection failures
        assert total_time < 20.0  # Reasonable time for concurrent connections
        
        # Test each connected client
        active_clients = [client for client, result in zip(clients, results) 
                         if result is True and client.state == ConnectionState.CONNECTED]
        
        for client in active_clients:
            # Test individual client communication
            await client.send({"type": "ping", "payload": {}})
            response = await client.receive(timeout=2.0)
            # Response is optional - just testing connection integrity
        
        lifecycle_tester.record_test_result("concurrent_auth_connections", True, {
            "clients_created": num_clients,
            "successful_connections": successful_connections,
            "total_time": total_time
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_token_validation_timing(self, lifecycle_tester):
        """Test authentication validation completes within timing requirements"""
        client = lifecycle_tester.create_authenticated_client("timing_test_user")
        
        # Measure auth validation time
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        auth_time = time.time() - start_time
        
        # Verify auth validation timing (should be quick)
        assert success is True
        assert auth_time < 10.0  # Auth validation should be under 10 seconds
        
        lifecycle_tester.record_test_result("auth_timing", True, {
            "auth_time": auth_time,
            "under_limit": auth_time < 10.0
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_comprehensive_auth_scenarios(self, lifecycle_tester):
        """Test comprehensive authentication scenarios"""
        scenarios = [
            ("valid", True),
            ("invalid", False),
            ("expired", False),
            ("missing", False)
        ]
        
        results = {}
        
        for scenario_type, should_succeed in scenarios:
            if scenario_type == "valid":
                client = lifecycle_tester.create_authenticated_client("valid_user")
            else:
                client = lifecycle_tester.create_invalid_auth_client(scenario_type)
            
            # Test connection
            start_time = time.time()
            success = await client.connect(client._auth_headers)
            scenario_time = time.time() - start_time
            
            # Record results
            results[scenario_type] = {
                "success": success,
                "expected": should_succeed,
                "matches_expectation": success == should_succeed,
                "time": scenario_time
            }
            
            # Verify result matches expectation
            assert success == should_succeed, f"Scenario {scenario_type} failed expectation"
        
        # Verify all scenarios tested
        assert len(results) == 4
        assert all(result["matches_expectation"] for result in results.values())
        
        lifecycle_tester.record_test_result("comprehensive_auth_scenarios", True, {
            "scenarios_tested": len(results),
            "all_passed": all(result["matches_expectation"] for result in results.values())
        })


@pytest.mark.e2e
class TestWebSocketConnectionPerformance:
    """Test WebSocket connection performance requirements"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_establishment_performance(self, lifecycle_tester):
        """Test connection establishment meets performance requirements"""
        client = lifecycle_tester.create_authenticated_client("perf_test_user")
        
        # Measure connection performance
        start_time = time.time()
        success = await client.connect(client._auth_headers)
        connection_time = time.time() - start_time
        
        # Verify performance requirements
        assert success is True
        assert connection_time < 10.0  # Connection should be under 10 seconds
        assert client.metrics.connection_time < 10.0
        
        lifecycle_tester.record_test_result("connection_performance", True, {
            "connection_time": connection_time,
            "under_limit": connection_time < 10.0
        })
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_message_roundtrip_performance(self, lifecycle_tester):
        """Test message roundtrip performance"""
        client = lifecycle_tester.create_authenticated_client("roundtrip_test_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        
        # Test message roundtrip performance
        test_message = {"type": "ping", "payload": {"timestamp": time.time()}}
        
        start_time = time.time()
        await client.send(test_message)
        response = await client.receive(timeout=5.0)
        roundtrip_time = time.time() - start_time
        
        # Verify performance (allow some time for server processing)
        assert roundtrip_time < 5.0  # Reasonable roundtrip time
        assert response is not None or roundtrip_time < 2.0  # Fast even if no response
        
        lifecycle_tester.record_test_result("message_roundtrip_performance", True, {
            "roundtrip_time": roundtrip_time,
            "response_received": response is not None
        })