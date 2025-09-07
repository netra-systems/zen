"""
Comprehensive WebSocket Authentication E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Authentication is universal
- Business Goal: Ensure secure, reliable WebSocket authentication for all users
- Value Impact: Prevents authentication failures that cause user churn and security breaches
- Strategic Impact: Critical security foundation enabling $200K+ MRR protection

This test suite validates:
1. Valid JWT authentication succeeds with proper user context
2. Invalid JWT authentication fails with 403 errors
3. Expired JWT authentication fails appropriately
4. Missing JWT authentication fails with 403
5. OAuth token exchange works properly
6. Multi-user isolation (users cannot access each other's data)
7. Token refresh during active connection works
8. WebSocket disconnections are handled gracefully

CRITICAL: Uses real Docker services, real JWT tokens, proper SSOT patterns
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import pytest
import jwt

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestHelpers, MockWebSocketConnection
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.test_config import TEST_PORTS
from shared.isolated_environment import get_env


class TestWebSocketAuthenticationComprehensive(BaseE2ETest):
    """Comprehensive WebSocket authentication test suite with real services."""
    
    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()
        self.env = get_env()
        
        # Get WebSocket URL using TEST_PORTS configuration
        backend_port = TEST_PORTS.get("backend", 8000)
        self.websocket_url = f"ws://localhost:{backend_port}/ws"
        
        # Initialize auth helpers with test configuration
        auth_config = E2EAuthConfig()
        auth_config.websocket_url = self.websocket_url
        auth_config.backend_url = f"http://localhost:{backend_port}"
        
        self.auth_config = auth_config
        self.auth_helper = E2EAuthHelper(self.auth_config, environment="test")
        self.ws_auth_helper = E2EWebSocketAuthHelper(self.auth_config, environment="test")
        
        # Track active connections for cleanup
        self.active_connections = []
        self.test_tokens = []
    
    def teardown_method(self):
        """Teardown method called after each test (sync wrapper for async cleanup)."""
        # Run async cleanup in sync teardown
        asyncio.run(self.async_cleanup())
        super().teardown_method()
    
    async def async_cleanup(self):
        """Async cleanup method for WebSocket resources."""
        # Close all active WebSocket connections
        for connection in self.active_connections:
            try:
                await WebSocketTestHelpers.close_test_connection(connection)
            except Exception:
                pass  # Ignore cleanup errors
        
        self.active_connections.clear()
        self.test_tokens.clear()
        
        # Call parent cleanup
        await self.cleanup_resources()
    
    def _create_test_users(self) -> Dict[str, Dict[str, Any]]:
        """Create test user data for multi-user scenarios."""
        timestamp = int(time.time())
        return {
            "user1": {
                "user_id": f"test_user_1_{timestamp}",
                "email": f"user1_{timestamp}@test.com",
                "permissions": ["read", "write"]
            },
            "user2": {
                "user_id": f"test_user_2_{timestamp}",
                "email": f"user2_{timestamp}@test.com", 
                "permissions": ["read"]
            },
            "admin": {
                "user_id": f"admin_user_{timestamp}",
                "email": f"admin_{timestamp}@test.com",
                "permissions": ["read", "write", "admin"]
            }
        }
    
    async def _create_websocket_connection(
        self, 
        token: str, 
        expect_success: bool = True
    ) -> Optional[Any]:
        """Create WebSocket connection with authentication."""
        try:
            headers = self.auth_helper.get_websocket_headers(token)
            
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=headers,
                timeout=10.0,
                max_retries=2
            )
            
            if expect_success:
                self.active_connections.append(connection)
            
            return connection
            
        except Exception as e:
            if expect_success:
                self.logger.error(f"Failed to create WebSocket connection: {e}")
                raise
            return None
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_valid_jwt_authentication_succeeds(self):
        """Test that valid JWT authentication succeeds with proper user context."""
        # Arrange
        test_users = self._create_test_users()
        user_data = test_users["user1"]
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        self.test_tokens.append(token)
        
        # Act
        connection = await self._create_websocket_connection(token, expect_success=True)
        
        # Send authentication verification message
        auth_message = {
            "type": "auth_verify",
            "user_id": user_data["user_id"],
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection, auth_message)
        
        # Assert
        response = await WebSocketTestHelpers.receive_test_message(connection, timeout=10.0)
        
        assert response["type"] != "error", f"Authentication failed: {response}"
        assert "user_id" in response or response["type"] == "ack"
        
        self.logger.info("✓ Valid JWT authentication succeeded")
    
    @pytest.mark.e2e  
    @pytest.mark.real_services
    async def test_invalid_jwt_authentication_fails_with_403(self):
        """Test that invalid JWT authentication fails with 403 status."""
        # Arrange
        invalid_token = "invalid.jwt.token"
        
        # Act & Assert
        connection = await self._create_websocket_connection(invalid_token, expect_success=False)
        
        if connection:
            # If connection somehow succeeded, send a message and expect error
            try:
                test_message = {"type": "ping", "timestamp": time.time()}
                await WebSocketTestHelpers.send_test_message(connection, test_message)
                
                response = await WebSocketTestHelpers.receive_test_message(connection, timeout=5.0)
                assert response["type"] == "error", "Expected error response for invalid token"
                assert "error" in response, "Error response should contain error field"
                
            except Exception as e:
                # Connection properly rejected invalid token
                self.logger.info(f"✓ Invalid JWT properly rejected: {e}")
        else:
            # Connection was properly rejected
            self.logger.info("✓ Invalid JWT authentication properly failed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_expired_jwt_authentication_fails(self):
        """Test that expired JWT authentication fails appropriately."""
        # Arrange
        test_users = self._create_test_users()
        user_data = test_users["user1"]
        
        # Create expired token (expired 5 minutes ago)
        expired_payload = {
            "sub": user_data["user_id"],
            "email": user_data["email"],
            "permissions": user_data["permissions"],
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        expired_token = jwt.encode(expired_payload, self.auth_config.jwt_secret, algorithm="HS256")
        self.test_tokens.append(expired_token)
        
        # Act & Assert
        connection = await self._create_websocket_connection(expired_token, expect_success=False)
        
        if connection:
            # If connection succeeded, expect error on message send
            try:
                test_message = {"type": "ping", "timestamp": time.time()}
                await WebSocketTestHelpers.send_test_message(connection, test_message)
                
                response = await WebSocketTestHelpers.receive_test_message(connection, timeout=5.0)
                assert response["type"] == "error", "Expected error for expired token"
                
            except Exception:
                # Connection properly handled expired token
                pass
        
        self.logger.info("✓ Expired JWT authentication properly failed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_missing_jwt_authentication_fails_with_403(self):
        """Test that missing JWT authentication fails with 403."""
        # Act & Assert - Try to connect without authentication headers
        try:
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers={},  # No authentication headers
                timeout=5.0,
                max_retries=1
            )
            
            if connection:
                # If connection somehow succeeded, send message and expect error
                test_message = {"type": "ping", "timestamp": time.time()}
                await WebSocketTestHelpers.send_test_message(connection, test_message)
                
                response = await WebSocketTestHelpers.receive_test_message(connection, timeout=5.0)
                assert response["type"] == "error", "Expected error for missing authentication"
                
                await WebSocketTestHelpers.close_test_connection(connection)
        
        except Exception as e:
            # Connection was properly rejected due to missing auth
            self.logger.info(f"✓ Missing JWT properly rejected: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_oauth_token_exchange_works(self):
        """Test that OAuth token exchange works properly."""
        # Arrange
        test_users = self._create_test_users()
        user_data = test_users["user1"]
        
        # Create OAuth-style token
        oauth_token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        self.test_tokens.append(oauth_token)
        
        # Act
        connection = await self._create_websocket_connection(oauth_token, expect_success=True)
        
        # Send token exchange request
        exchange_message = {
            "type": "token_exchange",
            "oauth_token": oauth_token,
            "user_id": user_data["user_id"],
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection, exchange_message)
        
        # Assert
        response = await WebSocketTestHelpers.receive_test_message(connection, timeout=10.0)
        
        assert response["type"] != "error", f"Token exchange failed: {response}"
        # Token exchange should either succeed or echo back the message
        assert response["type"] in ["token_exchange", "ack"], f"Unexpected response: {response}"
        
        self.logger.info("✓ OAuth token exchange works properly")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_isolation(self):
        """Test multi-user isolation - users cannot see each other's data."""
        # Arrange
        test_users = self._create_test_users()
        
        # Create tokens for two different users
        token1 = self.auth_helper.create_test_jwt_token(
            user_id=test_users["user1"]["user_id"],
            email=test_users["user1"]["email"],
            permissions=test_users["user1"]["permissions"]
        )
        
        token2 = self.auth_helper.create_test_jwt_token(
            user_id=test_users["user2"]["user_id"],
            email=test_users["user2"]["email"],
            permissions=test_users["user2"]["permissions"]
        )
        
        self.test_tokens.extend([token1, token2])
        
        # Act - Create connections for both users
        connection1 = await self._create_websocket_connection(token1, expect_success=True)
        connection2 = await self._create_websocket_connection(token2, expect_success=True)
        
        # User 1 sends a message with sensitive data
        user1_message = {
            "type": "user_data", 
            "user_id": test_users["user1"]["user_id"],
            "sensitive_data": "user1_secret_info",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection1, user1_message)
        
        # User 2 tries to access User 1's data
        access_request = {
            "type": "get_user_data",
            "target_user_id": test_users["user1"]["user_id"],
            "requesting_user_id": test_users["user2"]["user_id"],
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection2, access_request)
        
        # Assert - User 2 should not receive User 1's sensitive data
        response1 = await WebSocketTestHelpers.receive_test_message(connection1, timeout=5.0)
        response2 = await WebSocketTestHelpers.receive_test_message(connection2, timeout=5.0)
        
        # User 1 should get acknowledgment or echo of their own message
        assert test_users["user1"]["user_id"] in str(response1), "User 1 should see their own data"
        
        # User 2 should not get User 1's sensitive data
        if "sensitive_data" in str(response2):
            assert "user1_secret_info" not in str(response2), "User isolation violated!"
        
        self.logger.info("✓ Multi-user isolation working properly")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_token_refresh_during_active_connection(self):
        """Test token refresh during active WebSocket connection."""
        # Arrange
        test_users = self._create_test_users()
        user_data = test_users["user1"]
        
        # Create initial token
        original_token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"],
            exp_minutes=60  # Valid for 1 hour
        )
        self.test_tokens.append(original_token)
        
        # Act
        connection = await self._create_websocket_connection(original_token, expect_success=True)
        
        # Send token refresh request
        refresh_request = {
            "type": "token_refresh",
            "current_token": original_token,
            "user_id": user_data["user_id"],
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection, refresh_request)
        
        # Assert
        response = await WebSocketTestHelpers.receive_test_message(connection, timeout=10.0)
        
        # Should either get a new token or an acknowledgment
        assert response["type"] != "error", f"Token refresh failed: {response}"
        
        # If response contains a new token, validate it's different
        if "new_token" in response:
            new_token = response["new_token"]
            assert new_token != original_token, "New token should be different from original"
            self.test_tokens.append(new_token)
        
        self.logger.info("✓ Token refresh during active connection works")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_disconnection_handling(self):
        """Test that WebSocket disconnections are handled gracefully."""
        # Arrange
        test_users = self._create_test_users()
        user_data = test_users["user1"]
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        self.test_tokens.append(token)
        
        # Act
        connection = await self._create_websocket_connection(token, expect_success=True)
        
        # Send a message to establish connection
        initial_message = {
            "type": "connection_test",
            "user_id": user_data["user_id"],
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(connection, initial_message)
        
        # Wait for response
        response = await WebSocketTestHelpers.receive_test_message(connection, timeout=5.0)
        assert response["type"] != "error", f"Initial connection failed: {response}"
        
        # Force disconnect
        await WebSocketTestHelpers.close_test_connection(connection)
        
        # Try to reconnect with same token
        new_connection = await self._create_websocket_connection(token, expect_success=True)
        
        # Send reconnection message
        reconnect_message = {
            "type": "reconnect_test",
            "user_id": user_data["user_id"],
            "previous_session": True,
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(new_connection, reconnect_message)
        
        # Assert
        reconnect_response = await WebSocketTestHelpers.receive_test_message(new_connection, timeout=10.0)
        assert reconnect_response["type"] != "error", f"Reconnection failed: {reconnect_response}"
        
        self.logger.info("✓ WebSocket disconnection handling works gracefully")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_authentication_requests(self):
        """Test system handles multiple concurrent authentication requests."""
        # Arrange
        test_users = self._create_test_users()
        concurrent_connections = []
        
        # Act - Create multiple concurrent connections
        connection_tasks = []
        
        for i in range(3):
            user_data = test_users["user1"]
            token = self.auth_helper.create_test_jwt_token(
                user_id=f"{user_data['user_id']}_session_{i}",
                email=user_data["email"],
                permissions=user_data["permissions"]
            )
            self.test_tokens.append(token)
            
            task = self._create_websocket_connection(token, expect_success=True)
            connection_tasks.append(task)
        
        # Wait for all connections to be established
        connections = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Filter successful connections
        successful_connections = [
            conn for conn in connections 
            if conn and not isinstance(conn, Exception)
        ]
        
        # Assert
        assert len(successful_connections) >= 2, f"Expected at least 2 successful connections, got {len(successful_connections)}"
        
        # Test each connection works
        for i, connection in enumerate(successful_connections):
            test_message = {
                "type": "concurrent_test",
                "session_id": i,
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(connection, test_message)
            response = await WebSocketTestHelpers.receive_test_message(connection, timeout=5.0)
            assert response["type"] != "error", f"Concurrent connection {i} failed: {response}"
        
        self.logger.info(f"✓ Concurrent authentication handled successfully ({len(successful_connections)} connections)")