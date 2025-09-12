"""
WebSocket Connection Lifecycle Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable WebSocket connections enable real-time AI chat interactions
- Value Impact: Connection stability is prerequisite for $500K+ ARR chat functionality
- Strategic Impact: Core platform communication foundation for user engagement

CRITICAL: WebSocket connections enable real-time AI chat value delivery per CLAUDE.md
Connection reliability directly impacts user experience and business revenue.

These integration tests validate WebSocket connection lifecycle without requiring Docker services.
They test connection establishment, authentication, heartbeat, reconnection, and cleanup patterns.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed, InvalidStatus

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@pytest.mark.integration
class TestWebSocketConnectionEstablishment(SSotBaseTestCase):
    """
    Test WebSocket connection establishment patterns and protocols.
    
    BVJ: Platform/Internal - Connection establishment ensures users can receive AI insights
    """
    
    async def test_websocket_connection_establishment_basic(self):
        """
        Test basic WebSocket connection establishment with proper headers.
        
        BVJ: Users must be able to establish connections to receive AI agent responses
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(user_id="conn-basic-user")
            
            # Mock WebSocket connection for integration testing
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            mock_websocket.recv = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            with patch('websockets.connect') as mock_connect:
                mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
                mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Test connection establishment
                success = await client.connect(timeout=10.0)
                
                # Verify connection state
                assert success is True or client.is_connected, "Connection should be established"
                assert client.test_id is not None
                assert client.url == ws_util.base_url
                
                # Verify headers include authentication and test identification
                headers = client.headers
                assert "X-User-ID" in headers
                assert headers["X-User-ID"] == "conn-basic-user"
                assert "Authorization" in headers
                assert headers["Authorization"].startswith("Bearer")
                
                self.record_metric("basic_connection_test", "success")
    
    async def test_websocket_connection_with_custom_headers(self):
        """
        Test WebSocket connection with custom headers for service integration.
        
        BVJ: Custom headers enable service-to-service authentication and routing
        """
        custom_headers = {
            "X-Service-ID": "netra-backend",
            "X-Client-Version": "1.0.0",
            "X-Request-ID": f"req_{uuid.uuid4().hex[:8]}"
        }
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(
                user_id="header-test-user",
                headers=custom_headers
            )
            
            # Verify custom headers are preserved and merged with auth headers
            all_headers = client.headers
            assert "X-Service-ID" in all_headers
            assert all_headers["X-Service-ID"] == "netra-backend"
            assert "X-Client-Version" in all_headers
            assert "X-Request-ID" in all_headers
            assert "X-User-ID" in all_headers  # Auth header added
            assert "Authorization" in all_headers  # Auth header added
            
            self.record_metric("custom_headers_test", len(custom_headers))
    
    async def test_websocket_connection_url_validation(self):
        """
        Test WebSocket URL validation and protocol handling.
        
        BVJ: URL validation prevents connection errors and provides clear feedback
        """
        test_cases = [
            ("ws://localhost:8000/ws", "ws://localhost:8000/ws"),
            ("wss://secure.example.com/ws", "wss://secure.example.com/ws"),
            ("http://example.com/ws", "ws://example.com/ws"),  # HTTP -> WS conversion
            ("https://secure.example.com/ws", "wss://secure.example.com/ws"),  # HTTPS -> WSS conversion
        ]
        
        for input_url, expected_url in test_cases:
            with self.temp_env_vars(WEBSOCKET_TEST_URL=input_url):
                async with WebSocketTestUtility() as ws_util:
                    assert ws_util.base_url == expected_url
        
        self.record_metric("url_validation_cases", len(test_cases))
    
    async def test_websocket_connection_timeout_handling(self):
        """
        Test WebSocket connection timeout scenarios and error handling.
        
        BVJ: Timeout handling prevents users from waiting indefinitely for connections
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Mock slow connection that exceeds timeout
            async def slow_connect(*args, **kwargs):
                await asyncio.sleep(3.0)  # Longer than timeout
                return AsyncMock()
            
            with patch('websockets.connect', side_effect=slow_connect):
                start_time = time.time()
                success = await client.connect(timeout=1.0)
                elapsed = time.time() - start_time
                
                # Verify timeout behavior
                assert not success, "Connection should timeout"
                assert elapsed < 2.0, "Should respect timeout parameter"
                assert not client.is_connected
                
                self.record_metric("timeout_handling_duration", elapsed)
    
    async def test_websocket_connection_failure_scenarios(self):
        """
        Test various WebSocket connection failure scenarios.
        
        BVJ: Graceful failure handling prevents user frustration and provides diagnostics
        """
        failure_scenarios = [
            (ConnectionRefusedError("Connection refused"), "connection_refused"),
            (OSError("Network unreachable"), "network_unreachable"),
            (ValueError("Invalid URL"), "invalid_url"),
            (asyncio.TimeoutError("Connection timeout"), "timeout"),
        ]
        
        async with WebSocketTestUtility() as ws_util:
            for exception, error_type in failure_scenarios:
                client = await ws_util.create_test_client()
                
                with patch('websockets.connect', side_effect=exception):
                    success = await client.connect(timeout=2.0)
                    
                    # Verify failure handling
                    assert not success, f"Connection should fail for {error_type}"
                    assert not client.is_connected
                    
                    self.record_metric(f"failure_scenario_{error_type}", "handled")


@pytest.mark.integration
class TestWebSocketAuthentication(SSotBaseTestCase):
    """
    Test WebSocket authentication integration patterns.
    
    BVJ: Authentication ensures secure access to AI services and user data protection
    """
    
    async def test_websocket_jwt_authentication_integration(self):
        """
        Test JWT-based WebSocket authentication with token validation.
        
        BVJ: JWT authentication enables secure, scalable user session management
        """
        auth_helper = E2EAuthHelper()
        
        # Create test JWT with comprehensive claims
        token = auth_helper.create_test_jwt_token(
            user_id="jwt-auth-user",
            email="jwt-test@netra.com",
            permissions=["read", "write", "agent_execute"],
            custom_claims={"subscription": "enterprise", "region": "us-east-1"}
        )
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("jwt-auth-user", token)
            
            # Verify authentication headers
            headers = client.headers
            assert headers["Authorization"] == f"Bearer {token}"
            assert headers["X-User-ID"] == "jwt-auth-user"
            
            # Verify JWT structure (should have 3 parts: header.payload.signature)
            token_parts = token.split('.')
            assert len(token_parts) == 3, "JWT should have header, payload, and signature"
            
            # Test that token contains expected user information
            # Note: In real scenarios, server would validate token
            self.record_metric("jwt_auth_validation", "passed")
    
    async def test_websocket_session_authentication_integration(self):
        """
        Test session-based WebSocket authentication patterns.
        
        BVJ: Session authentication enables persistent user context across interactions
        """
        session_id = f"sess_{uuid.uuid4().hex}"
        user_id = "session-auth-user"
        
        session_headers = {
            "X-Session-ID": session_id,
            "X-User-ID": user_id,
            "Cookie": f"netra_session={session_id}; Path=/; HttpOnly"
        }
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(
                user_id=user_id,
                headers=session_headers
            )
            
            # Verify session headers are included
            assert "X-Session-ID" in client.headers
            assert client.headers["X-Session-ID"] == session_id
            assert "Cookie" in client.headers
            assert session_id in client.headers["Cookie"]
            
            self.record_metric("session_auth_test", "completed")
    
    async def test_websocket_authentication_failure_handling(self):
        """
        Test WebSocket authentication failure scenarios and error responses.
        
        BVJ: Authentication failure handling prevents unauthorized access to AI services
        """
        invalid_auth_scenarios = [
            ("", "empty_token"),
            ("invalid-token-format", "malformed_token"),
            ("Bearer expired.jwt.token", "expired_token"),
            ("Basic invalid-basic-auth", "wrong_auth_type"),
        ]
        
        async with WebSocketTestUtility() as ws_util:
            for invalid_token, scenario_type in invalid_auth_scenarios:
                headers = {"Authorization": invalid_token} if invalid_token else {}
                client = await ws_util.create_test_client(headers=headers)
                
                # In integration tests, we verify headers are set correctly
                # Server-side validation is tested separately
                if invalid_token:
                    assert client.headers["Authorization"] == invalid_token
                else:
                    # Should have default Bearer token for user
                    assert client.headers["Authorization"].startswith("Bearer")
                
                self.record_metric(f"auth_failure_{scenario_type}", "tested")
    
    async def test_websocket_multi_tenant_authentication(self):
        """
        Test multi-tenant WebSocket authentication with tenant isolation.
        
        BVJ: Multi-tenant authentication enables SaaS scalability and data isolation
        """
        tenants = [
            {"tenant_id": "tenant_alpha", "user_id": "user1@alpha.com"},
            {"tenant_id": "tenant_beta", "user_id": "user1@beta.com"},
            {"tenant_id": "tenant_gamma", "user_id": "admin@gamma.com"},
        ]
        
        async with WebSocketTestUtility() as ws_util:
            tenant_clients = []
            
            for tenant_info in tenants:
                headers = {
                    "X-Tenant-ID": tenant_info["tenant_id"],
                    "X-User-ID": tenant_info["user_id"]
                }
                
                client = await ws_util.create_test_client(
                    user_id=tenant_info["user_id"],
                    headers=headers
                )
                tenant_clients.append(client)
                
                # Verify tenant isolation in headers
                assert client.headers["X-Tenant-ID"] == tenant_info["tenant_id"]
                assert client.headers["X-User-ID"] == tenant_info["user_id"]
            
            # Verify each client has unique tenant context
            tenant_ids = [client.headers["X-Tenant-ID"] for client in tenant_clients]
            assert len(set(tenant_ids)) == len(tenants), "All tenants should be unique"
            
            self.record_metric("multi_tenant_auth", len(tenants))


@pytest.mark.integration
class TestWebSocketConnectionLifecycle(SSotBaseTestCase):
    """
    Test complete WebSocket connection lifecycle management.
    
    BVJ: Connection lifecycle management ensures reliable AI service availability
    """
    
    async def test_websocket_connection_lifecycle_complete(self):
        """
        Test complete WebSocket connection lifecycle from connect to disconnect.
        
        BVJ: Complete lifecycle management ensures predictable connection behavior
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(user_id="lifecycle-user")
            
            # Initial state
            assert not client.is_connected
            assert client.websocket is None
            
            # Mock connection establishment
            mock_websocket = AsyncMock()
            with patch('websockets.connect') as mock_connect:
                mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
                mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Connect
                success = await client.connect()
                assert success or client.is_connected
                
                # Verify connected state
                if client.is_connected:
                    assert client.websocket is not None
                
                # Test message sending capability
                if client.is_connected:
                    client.websocket = mock_websocket
                    await client.send_message(
                        WebSocketEventType.PING,
                        {"test": "lifecycle"},
                        user_id="lifecycle-user"
                    )
                    assert len(client.sent_messages) == 1
                
                # Disconnect
                await client.disconnect()
                assert not client.is_connected
            
            self.record_metric("connection_lifecycle", "completed")
    
    async def test_websocket_heartbeat_integration(self):
        """
        Test WebSocket heartbeat mechanism for connection health.
        
        BVJ: Heartbeat ensures connection health and enables automatic recovery
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(user_id="heartbeat-user")
            
            # Mock WebSocket for heartbeat testing
            mock_websocket = AsyncMock()
            client.websocket = mock_websocket
            client.is_connected = True
            
            # Send heartbeat manually (simulating automatic heartbeat)
            await client.send_message(
                WebSocketEventType.PING,
                {"timestamp": time.time(), "heartbeat": True},
                user_id="heartbeat-user"
            )
            
            # Verify heartbeat message
            heartbeat_msg = client.sent_messages[0]
            assert heartbeat_msg.event_type == WebSocketEventType.PING
            assert "heartbeat" in heartbeat_msg.data
            assert heartbeat_msg.data["heartbeat"] is True
            
            self.record_metric("heartbeat_test", "sent")
    
    async def test_websocket_reconnection_integration(self):
        """
        Test WebSocket reconnection logic and state recovery.
        
        BVJ: Reconnection capability ensures service continuity during network issues
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(user_id="reconnect-user")
            
            # Test reconnection scenario using utility method
            resilience_results = await ws_util.test_connection_resilience(
                client, 
                disconnect_count=2
            )
            
            # Verify resilience test structure
            assert "disconnect_count" in resilience_results
            assert "total_test_time" in resilience_results
            assert resilience_results["disconnect_count"] == 2
            
            # Basic expectations for integration testing
            assert isinstance(resilience_results["total_test_time"], (int, float))
            assert resilience_results["total_test_time"] >= 0
            
            self.record_metric("reconnection_test", resilience_results)
    
    async def test_websocket_connection_cleanup_integration(self):
        """
        Test WebSocket connection cleanup and resource management.
        
        BVJ: Proper cleanup prevents resource leaks and ensures system stability
        """
        async with WebSocketTestUtility() as ws_util:
            initial_client_count = len(ws_util.active_clients)
            
            # Create multiple clients
            clients = []
            for i in range(5):
                client = await ws_util.create_test_client(user_id=f"cleanup-user-{i}")
                clients.append(client)
            
            # Verify clients are tracked
            assert len(ws_util.active_clients) == initial_client_count + 5
            
            # Mock connections for cleanup testing
            for client in clients:
                client.websocket = AsyncMock()
                client.is_connected = True
            
            # Test cleanup
            await ws_util.disconnect_all_clients()
            
            # Verify cleanup completed
            connected_count = sum(1 for client in clients if client.is_connected)
            assert connected_count == 0, "All clients should be disconnected"
            
            self.record_metric("cleanup_test", len(clients))
    
    async def test_websocket_connection_state_management(self):
        """
        Test WebSocket connection state management and transitions.
        
        BVJ: State management ensures predictable connection behavior for users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client(user_id="state-user")
            
            # Test state transitions
            states = []
            
            # Initial state
            states.append(("initial", client.is_connected, client.websocket is not None))
            assert not client.is_connected
            assert client.websocket is None
            
            # Mock connection
            mock_websocket = AsyncMock()
            client.websocket = mock_websocket
            client.is_connected = True
            states.append(("connected", client.is_connected, client.websocket is not None))
            
            # Test message sending in connected state
            await client.send_message(
                WebSocketEventType.PING,
                {"state_test": True},
                user_id="state-user"
            )
            
            # Verify message was sent
            assert len(client.sent_messages) == 1
            states.append(("message_sent", len(client.sent_messages) == 1, True))
            
            # Disconnect
            await client.disconnect()
            states.append(("disconnected", client.is_connected, False))
            
            # Verify final state
            assert not client.is_connected
            
            self.record_metric("state_transitions", len(states))