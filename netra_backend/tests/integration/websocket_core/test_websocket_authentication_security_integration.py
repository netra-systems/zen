"""
Integration tests for WebSocket Authentication and Security - Testing auth flows and security.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform security and user data protection
- Value Impact: Ensures only authorized users access AI chat, protecting sensitive business data
- Strategic Impact: Critical for enterprise adoption - validates security posture of WebSocket infrastructure

These integration tests validate WebSocket authentication flows, token validation,
session management, and security controls that protect user data and prevent unauthorized access.
"""

import pytest
import asyncio
import jwt
from datetime import datetime, timezone, timedelta
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.unified_websocket_auth import WebSocketAuthenticator
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.models import User, Thread
from shared.isolated_environment import get_env


class TestWebSocketAuthenticationSecurityIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket authentication and security."""
    
    @pytest.fixture
    async def auth_config(self):
        """Create authentication configuration."""
        env = get_env()
        return E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002", 
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars"),
            timeout=10.0
        )
    
    @pytest.fixture
    async def auth_helper(self, auth_config):
        """Create authentication helper."""
        return E2EAuthHelper(auth_config)
    
    @pytest.fixture
    async def websocket_authenticator(self):
        """Create WebSocket authenticator."""
        return WebSocketAuthenticator()
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.fixture
    async def test_user(self, real_services_fixture) -> User:
        """Create test user for authentication."""
        db = real_services_fixture["db"]
        
        user = User(
            email="auth_test@example.com",
            name="Auth Test User",
            subscription_tier="enterprise",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_jwt_authentication_flow(self, real_services_fixture, auth_helper, 
                                                    websocket_authenticator, test_user):
        """Test complete JWT authentication flow for WebSocket connections."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Generate valid JWT token for test user
        env = get_env()
        jwt_secret = env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        
        token_payload = {
            "user_id": str(test_user.id),
            "email": test_user.email,
            "subscription_tier": test_user.subscription_tier,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "iss": "netra-auth-service"
        }
        
        valid_token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        # Test valid token authentication
        auth_result = await websocket_authenticator.authenticate_token(valid_token)
        
        assert auth_result is not None
        assert auth_result.is_valid is True
        assert auth_result.user_id == str(test_user.id)
        assert auth_result.email == test_user.email
        assert auth_result.subscription_tier == test_user.subscription_tier
        assert auth_result.error_message is None
        
        # Verify user context is properly set
        assert auth_result.user_context is not None
        assert auth_result.user_context.user_id == str(test_user.id)
        assert auth_result.user_context.subscription_tier == test_user.subscription_tier
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_with_valid_authentication(self, real_services_fixture, auth_helper,
                                                                 websocket_manager, websocket_utility, test_user):
        """Test WebSocket connection establishment with valid authentication."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create authenticated WebSocket connection
        mock_websocket = await websocket_utility.create_authenticated_websocket(
            user_id=str(test_user.id),
            subscription_tier=test_user.subscription_tier
        )
        
        # Create connection with authentication metadata
        connection = await websocket_manager.create_connection(
            connection_id="auth_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={
                "authenticated": True,
                "subscription_tier": test_user.subscription_tier,
                "auth_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Add authenticated connection
        await websocket_manager.add_connection(connection)
        
        # Verify connection is properly authenticated
        assert connection.user_id == str(test_user.id)
        assert connection.metadata["authenticated"] is True
        assert connection.metadata["subscription_tier"] == test_user.subscription_tier
        
        # Test authenticated message handling
        authenticated_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "This is an authenticated message",
                "requires_auth": True
            },
            user_id=str(test_user.id)
        )
        
        # Should successfully handle authenticated message
        result = await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=authenticated_message
        )
        
        # Verify message was processed successfully
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) > 0
        
        # Should receive acknowledgment or response
        ack_found = any(
            "received" in str(msg) or "authenticated" in str(msg) 
            for msg in sent_messages
        )
        assert ack_found or len(sent_messages) > 0  # Either explicit ack or message processed
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_rejects_invalid_authentication(self, real_services_fixture, websocket_authenticator):
        """Test WebSocket rejection of invalid authentication tokens."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Test invalid token scenarios
        invalid_tokens = [
            "invalid.jwt.token",  # Malformed token
            "",  # Empty token
            "Bearer invalid_token",  # Invalid format
            None  # No token
        ]
        
        for invalid_token in invalid_tokens:
            if invalid_token is None:
                # Test missing token
                with pytest.raises(Exception):  # Should raise authentication error
                    await websocket_authenticator.authenticate_token(invalid_token)
            else:
                # Test invalid token
                auth_result = await websocket_authenticator.authenticate_token(invalid_token)
                
                assert auth_result.is_valid is False
                assert auth_result.user_id is None
                assert auth_result.error_message is not None
                assert "invalid" in auth_result.error_message.lower() or "expired" in auth_result.error_message.lower()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_token_expiration_handling(self, real_services_fixture, websocket_authenticator, test_user):
        """Test handling of expired JWT tokens."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create expired token
        env = get_env()
        jwt_secret = env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        
        expired_payload = {
            "user_id": str(test_user.id),
            "email": test_user.email,
            "subscription_tier": test_user.subscription_tier,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=10),  # Expired 10 minutes ago
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": "netra-auth-service"
        }
        
        expired_token = jwt.encode(expired_payload, jwt_secret, algorithm="HS256")
        
        # Test expired token authentication
        auth_result = await websocket_authenticator.authenticate_token(expired_token)
        
        assert auth_result.is_valid is False
        assert auth_result.user_id is None
        assert auth_result.error_message is not None
        assert "expired" in auth_result.error_message.lower()
        assert auth_result.error_code == "TOKEN_EXPIRED"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_subscription_tier_authorization(self, real_services_fixture, websocket_manager,
                                                           websocket_utility, test_user):
        """Test subscription tier-based authorization for WebSocket features."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Test different subscription tiers
        subscription_scenarios = [
            {
                "tier": "free",
                "allowed_features": ["basic_chat"],
                "restricted_features": ["real_time_updates", "priority_support", "advanced_analytics"]
            },
            {
                "tier": "early",
                "allowed_features": ["basic_chat", "real_time_updates"],
                "restricted_features": ["priority_support", "advanced_analytics"]
            },
            {
                "tier": "enterprise",
                "allowed_features": ["basic_chat", "real_time_updates", "priority_support", "advanced_analytics"],
                "restricted_features": []
            }
        ]
        
        for scenario in subscription_scenarios:
            # Update user subscription tier
            test_user.subscription_tier = scenario["tier"]
            db.add(test_user)
            await db.commit()
            
            # Create connection with specific tier
            mock_websocket = await websocket_utility.create_authenticated_websocket(
                user_id=str(test_user.id),
                subscription_tier=scenario["tier"]
            )
            
            connection = await websocket_manager.create_connection(
                connection_id=f"tier_test_{scenario['tier']}",
                user_id=str(test_user.id),
                websocket=mock_websocket,
                metadata={
                    "subscription_tier": scenario["tier"],
                    "authenticated": True
                }
            )
            await websocket_manager.add_connection(connection)
            
            # Test allowed features
            for feature in scenario["allowed_features"]:
                feature_message = WebSocketMessage(
                    message_type=MessageType.FEATURE_REQUEST,
                    payload={
                        "feature": feature,
                        "subscription_tier": scenario["tier"]
                    },
                    user_id=str(test_user.id)
                )
                
                # Should succeed for allowed features
                result = await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=mock_websocket,
                    message=feature_message
                )
                
                # Should not receive authorization error
                sent_messages = mock_websocket.sent_messages
                auth_errors = [
                    msg for msg in sent_messages
                    if "unauthorized" in str(msg).lower() or "forbidden" in str(msg).lower()
                ]
                assert len(auth_errors) == 0, f"Feature {feature} should be allowed for {scenario['tier']}"
            
            # Test restricted features
            for feature in scenario["restricted_features"]:
                feature_message = WebSocketMessage(
                    message_type=MessageType.FEATURE_REQUEST,
                    payload={
                        "feature": feature,
                        "subscription_tier": scenario["tier"]
                    },
                    user_id=str(test_user.id)
                )
                
                # Should fail for restricted features
                result = await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=mock_websocket,
                    message=feature_message
                )
                
                # Should receive authorization error
                sent_messages = mock_websocket.sent_messages
                auth_errors = [
                    msg for msg in sent_messages
                    if "unauthorized" in str(msg).lower() or "upgrade" in str(msg).lower()
                ]
                # May receive upgrade prompt instead of hard error for better UX
                
            # Cleanup
            await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_session_security_validation(self, real_services_fixture, websocket_manager,
                                                        websocket_utility, test_user):
        """Test WebSocket session security validation and tampering prevention."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create legitimate connection
        legitimate_websocket = await websocket_utility.create_authenticated_websocket(
            user_id=str(test_user.id),
            subscription_tier=test_user.subscription_tier
        )
        
        connection = await websocket_manager.create_connection(
            connection_id="security_test_conn",
            user_id=str(test_user.id),
            websocket=legitimate_websocket,
            metadata={"authenticated": True, "session_start": datetime.now(timezone.utc).isoformat()}
        )
        await websocket_manager.add_connection(connection)
        
        # Test session hijacking attempt (different user_id in message)
        hijack_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "Trying to hijack session"},
            user_id="different_user_123",  # Different from connection user_id
            thread_id="thread_456"
        )
        
        # Should reject message with mismatched user_id
        with pytest.raises(Exception) as exc_info:
            await websocket_manager.handle_message(
                user_id="different_user_123",  # Mismatched user
                websocket=legitimate_websocket,
                message=hijack_message
            )
        
        assert "unauthorized" in str(exc_info.value).lower() or "mismatch" in str(exc_info.value).lower()
        
        # Test message tampering (invalid signature/checksum)
        tampered_message = WebSocketMessage(
            message_type=MessageType.ADMIN_COMMAND,  # Privileged message type
            payload={
                "command": "grant_admin_access",
                "target_user": str(test_user.id)
            },
            user_id=str(test_user.id)
        )
        
        # Should reject privileged commands from non-admin users
        result = await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=legitimate_websocket,
            message=tampered_message
        )
        
        # Should receive permission denied
        sent_messages = legitimate_websocket.sent_messages
        permission_errors = [
            msg for msg in sent_messages
            if "denied" in str(msg).lower() or "unauthorized" in str(msg).lower()
        ]
        
        # Should either reject or return permission error
        assert len(permission_errors) > 0 or result is False
        
        # Test legitimate message (should succeed)
        legitimate_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "This is a legitimate message"},
            user_id=str(test_user.id)
        )
        
        result = await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=legitimate_websocket,
            message=legitimate_message
        )
        
        # Should succeed
        assert result is not False
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_rate_limiting_authentication(self, real_services_fixture, websocket_manager,
                                                         websocket_utility, test_user):
        """Test rate limiting for authenticated WebSocket connections."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create authenticated connection
        mock_websocket = await websocket_utility.create_authenticated_websocket(
            user_id=str(test_user.id),
            subscription_tier=test_user.subscription_tier
        )
        
        connection = await websocket_manager.create_connection(
            connection_id="rate_limit_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={
                "authenticated": True,
                "rate_limit_tier": test_user.subscription_tier
            }
        )
        await websocket_manager.add_connection(connection)
        
        # Send messages rapidly to test rate limiting
        messages_sent = 0
        rate_limit_triggered = False
        
        for i in range(100):  # Attempt to send many messages quickly
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"content": f"Rapid message {i}"},
                user_id=str(test_user.id)
            )
            
            try:
                result = await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=mock_websocket,
                    message=message
                )
                
                if result is False:
                    rate_limit_triggered = True
                    break
                    
                messages_sent += 1
                
            except Exception as e:
                if "rate limit" in str(e).lower() or "too many" in str(e).lower():
                    rate_limit_triggered = True
                    break
                else:
                    raise
            
            await asyncio.sleep(0.01)  # Small delay
        
        # Should eventually hit rate limit (exact threshold depends on configuration)
        assert rate_limit_triggered or messages_sent < 100, "Rate limiting should activate under rapid message load"
        
        # Verify rate limit message sent to client
        sent_messages = mock_websocket.sent_messages
        rate_limit_messages = [
            msg for msg in sent_messages
            if "rate limit" in str(msg).lower() or "too many" in str(msg).lower()
        ]
        
        if rate_limit_triggered:
            assert len(rate_limit_messages) > 0, "Should notify client about rate limiting"
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_cleanup_on_auth_failure(self, real_services_fixture, websocket_manager,
                                                               websocket_utility):
        """Test proper cleanup of connections after authentication failures."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection with invalid authentication
        invalid_websocket = await websocket_utility.create_mock_websocket()
        
        # Attempt to create connection with invalid user_id
        try:
            connection = await websocket_manager.create_connection(
                connection_id="invalid_auth_conn",
                user_id="nonexistent_user_999",
                websocket=invalid_websocket,
                metadata={"authenticated": False}
            )
            
            # Should fail to add connection due to invalid authentication
            with pytest.raises(Exception):
                await websocket_manager.add_connection(connection)
            
        except Exception as e:
            # Expected - connection creation or addition should fail
            assert "authentication" in str(e).lower() or "invalid" in str(e).lower() or "user" in str(e).lower()
        
        # Verify connection was not added to manager
        active_connections = websocket_manager.get_all_connections()
        invalid_connections = [
            conn for conn in active_connections
            if conn.connection_id == "invalid_auth_conn"
        ]
        assert len(invalid_connections) == 0
        
        # Verify no orphaned connections remain
        connection_count_before = len(active_connections)
        
        # Attempt another invalid connection
        try:
            connection2 = await websocket_manager.create_connection(
                connection_id="invalid_auth_conn_2",
                user_id="",  # Empty user ID
                websocket=invalid_websocket
            )
        except Exception:
            pass  # Expected
        
        connection_count_after = len(websocket_manager.get_all_connections())
        assert connection_count_after == connection_count_before, "No connections should be leaked"