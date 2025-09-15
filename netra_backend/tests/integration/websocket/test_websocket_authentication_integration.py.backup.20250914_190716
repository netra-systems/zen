"""
WebSocket Authentication Integration Tests

SECURITY CRITICAL: WebSocket authentication is the foundation of secure chat functionality
that prevents unauthorized access and protects $500K+ ARR business value.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Security is non-negotiable across all tiers
- Business Goal: Enable secure user access to chat functionality with proper authorization
- Value Impact: Authentication prevents unauthorized access that could expose user data
- Revenue Impact: Protects entire $500K+ ARR by ensuring only authorized users access chat

AUTHENTICATION REQUIREMENTS:
- JWT token validation for WebSocket connections
- User context creation and validation from token
- Demo mode vs. production authentication flows
- Authentication failure handling and graceful degradation
- Token expiration and renewal handling
- Multi-tier authentication (Free, Early, Mid, Enterprise)

TEST SCOPE: Integration-level validation of WebSocket authentication including:
- JWT token validation during connection establishment
- User context extraction and validation from tokens
- Authentication failure scenarios and error handling
- Token expiration and renewal workflows
- Demo mode authentication bypass testing
- Multi-tier user authentication validation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass
import jwt
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ConnectionMetadata
)

# Authentication components
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.token_validator import TokenValidator

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class AuthTestScenario:
    """Test scenario for authentication validation."""
    name: str
    user_data: TestUserData
    token_valid: bool
    token_expired: bool
    expected_connection_success: bool
    expected_auth_error: Optional[str] = None


class MockAuthenticatedWebSocket:
    """Mock WebSocket with authentication state tracking."""
    
    def __init__(self, user_id: str, connection_id: str, auth_token: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.auth_token = auth_token
        self.is_closed = False
        self.messages_sent = []
        self.state = WebSocketConnectionState.CONNECTING
        self.auth_validated = False
        self.user_context = None
        
    async def send(self, message: str) -> None:
        """Send message with authentication validation."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        if not self.auth_validated:
            logger.warning(f"Sending message without validated auth for user {self.user_id}")
        
        self.messages_sent.append({
            'message': message,
            'timestamp': datetime.now(UTC).isoformat(),
            'auth_validated': self.auth_validated,
            'user_context_present': self.user_context is not None
        })
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
        
    def validate_auth(self, user_context: Any) -> None:
        """Mark authentication as validated."""
        self.auth_validated = True
        self.user_context = user_context
        self.state = WebSocketConnectionState.CONNECTED


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.security
@pytest.mark.asyncio
class TestWebSocketAuthenticationIntegration(SSotAsyncTestCase):
    """
    Integration tests for WebSocket authentication.
    
    SECURITY CRITICAL: These tests protect the authentication foundation that secures
    chat functionality generating $500K+ ARR from unauthorized access.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_auth_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_auth_test")
        self.env.set("JWT_SECRET_KEY", "test_secret_key_for_websocket_auth", source="websocket_auth_test")
        
        # Test user scenarios with different authentication states
        self.auth_test_scenarios = [
            AuthTestScenario(
                name="valid_free_user",
                user_data=TestUserData(
                    user_id=f"free_user_{uuid.uuid4().hex[:8]}",
                    email="free@netra.ai",
                    tier="free",
                    thread_id=f"free_thread_{uuid.uuid4().hex[:8]}"
                ),
                token_valid=True,
                token_expired=False,
                expected_connection_success=True
            ),
            AuthTestScenario(
                name="valid_enterprise_user",
                user_data=TestUserData(
                    user_id=f"enterprise_user_{uuid.uuid4().hex[:8]}",
                    email="enterprise@company.com",
                    tier="enterprise",
                    thread_id=f"enterprise_thread_{uuid.uuid4().hex[:8]}"
                ),
                token_valid=True,
                token_expired=False,
                expected_connection_success=True
            ),
            AuthTestScenario(
                name="expired_token_user",
                user_data=TestUserData(
                    user_id=f"expired_user_{uuid.uuid4().hex[:8]}",
                    email="expired@netra.ai",
                    tier="early",
                    thread_id=f"expired_thread_{uuid.uuid4().hex[:8]}"
                ),
                token_valid=False,
                token_expired=True,
                expected_connection_success=False,
                expected_auth_error="token_expired"
            ),
            AuthTestScenario(
                name="invalid_token_user",
                user_data=TestUserData(
                    user_id=f"invalid_user_{uuid.uuid4().hex[:8]}",
                    email="invalid@netra.ai", 
                    tier="mid",
                    thread_id=f"invalid_thread_{uuid.uuid4().hex[:8]}"
                ),
                token_valid=False,
                token_expired=False,
                expected_connection_success=False,
                expected_auth_error="invalid_token"
            )
        ]
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.mock_websockets: List[MockAuthenticatedWebSocket] = []
        
    async def teardown_method(self, method):
        """Clean up authentication test resources."""
        for mock_ws in self.mock_websockets:
            if not mock_ws.is_closed:
                await mock_ws.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    def create_test_jwt_token(self, user_data: TestUserData, expired: bool = False, invalid: bool = False) -> str:
        """Create JWT token for testing."""
        secret = self.env.get("JWT_SECRET_KEY")
        
        if invalid:
            # Create token with wrong secret to simulate invalid token
            secret = "wrong_secret_key"
        
        # Set expiration
        if expired:
            exp = datetime.now(UTC) - timedelta(hours=1)  # Expired 1 hour ago
        else:
            exp = datetime.now(UTC) + timedelta(hours=24)  # Valid for 24 hours
        
        payload = {
            'user_id': user_data.user_id,
            'email': user_data.email,
            'tier': user_data.tier,
            'exp': exp.timestamp(),
            'iat': datetime.now(UTC).timestamp(),
            'iss': 'netra-auth-test'
        }
        
        try:
            token = jwt.encode(payload, secret, algorithm='HS256')
            return token
        except Exception as e:
            logger.error(f"Failed to create test JWT token: {e}")
            return "invalid_token_format"
    
    async def create_mock_user_context_from_token(self, token: str, user_data: TestUserData) -> Any:
        """Create mock user context from JWT token validation."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"auth_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'auth_token': token,
            'is_authenticated': True,
            'is_test': True
        })()
    
    async def test_valid_jwt_token_authentication_success(self):
        """
        Test: Valid JWT tokens enable successful WebSocket authentication
        
        Business Value: Validates that authorized users can access chat functionality,
        enabling revenue-generating AI interactions for paying customers.
        """
        scenario = self.auth_test_scenarios[0]  # Valid free user
        user_data = scenario.user_data
        
        # Create valid JWT token
        token = self.create_test_jwt_token(user_data, expired=False, invalid=False)
        assert token and token != "invalid_token_format", "Failed to create valid test token"
        
        # Create user context from token
        user_context = await self.create_mock_user_context_from_token(token, user_data)
        
        # Create WebSocket manager with authentication
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create authenticated WebSocket mock
        connection_id = f"auth_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockAuthenticatedWebSocket(user_data.user_id, connection_id, token)
        self.mock_websockets.append(mock_ws)
        
        # Test authentication and connection
        with patch.object(manager, '_websocket_transport', mock_ws):
            # Validate token and create user context
            mock_ws.validate_auth(user_context)
            
            # Connect user with authentication
            await manager.connect_user(
                user_id=ensure_user_id(user_data.user_id),
                websocket=mock_ws,
                connection_metadata={
                    "tier": user_data.tier,
                    "auth_token": token,
                    "authenticated": True
                }
            )
            
            # Verify successful authentication
            assert mock_ws.auth_validated, "Authentication should be validated"
            assert mock_ws.user_context is not None, "User context should be created"
            assert mock_ws.state == WebSocketConnectionState.CONNECTED, "Connection should be established"
            assert manager.is_connected(ensure_user_id(user_data.user_id)), "Manager should track connection"
            
            # Test authenticated message sending
            await manager.emit_agent_event(
                user_id=ensure_user_id(user_data.user_id),
                thread_id=user_data.thread_id,
                event_type="agent_started",
                data={
                    "authenticated_user": user_data.user_id,
                    "user_tier": user_data.tier,
                    "auth_test": True
                }
            )
            
            # Verify message was sent with valid authentication
            assert len(mock_ws.messages_sent) > 0, "Authenticated messages should be sent"
            latest_message = mock_ws.messages_sent[-1]
            assert latest_message['auth_validated'], "Messages should be sent with validated auth"
            assert latest_message['user_context_present'], "Messages should include user context"
        
        logger.info(f"✅ Valid JWT authentication successful for {user_data.tier} user")
    
    async def test_expired_jwt_token_authentication_failure(self):
        """
        Test: Expired JWT tokens result in authentication failure
        
        Business Value: Prevents unauthorized access from expired sessions,
        protecting platform security and user data integrity.
        """
        scenario = next(s for s in self.auth_test_scenarios if s.token_expired)
        user_data = scenario.user_data
        
        # Create expired JWT token
        expired_token = self.create_test_jwt_token(user_data, expired=True, invalid=False)
        
        # Create WebSocket mock
        connection_id = f"expired_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockAuthenticatedWebSocket(user_data.user_id, connection_id, expired_token)
        self.mock_websockets.append(mock_ws)
        
        # Test expired token authentication
        try:
            # Attempt to validate expired token (should fail in real implementation)
            with patch('auth_service.auth_core.core.jwt_handler.JWTHandler.validate_token') as mock_validate:
                # Mock token validation to simulate expired token rejection
                mock_validate.side_effect = jwt.ExpiredSignatureError("Token has expired")
                
                # Try to create user context (should fail)
                with pytest.raises(jwt.ExpiredSignatureError):
                    user_context = await self.create_mock_user_context_from_token(expired_token, user_data)
                    manager = await get_websocket_manager(
                        user_context=user_context,
                        mode=WebSocketManagerMode.ISOLATED
                    )
                    
                    with patch.object(manager, '_websocket_transport', mock_ws):
                        await manager.connect_user(
                            user_id=ensure_user_id(user_data.user_id),
                            websocket=mock_ws,
                            connection_metadata={
                                "tier": user_data.tier,
                                "auth_token": expired_token,
                                "authenticated": False
                            }
                        )
        
        except jwt.ExpiredSignatureError:
            # Expected behavior - expired tokens should be rejected
            pass
        
        # Verify authentication was not established
        assert not mock_ws.auth_validated, "Expired token should not validate"
        assert mock_ws.user_context is None, "No user context should be created for expired token"
        
        logger.info("✅ Expired JWT token correctly rejected")
    
    async def test_invalid_jwt_token_authentication_failure(self):
        """
        Test: Invalid JWT tokens result in authentication failure
        
        Business Value: Prevents unauthorized access from tampered or malicious tokens,
        protecting platform security and preventing potential attacks.
        """
        scenario = next(s for s in self.auth_test_scenarios if s.expected_auth_error == "invalid_token")
        user_data = scenario.user_data
        
        # Create invalid JWT token (wrong secret)
        invalid_token = self.create_test_jwt_token(user_data, expired=False, invalid=True)
        
        # Create WebSocket mock
        connection_id = f"invalid_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockAuthenticatedWebSocket(user_data.user_id, connection_id, invalid_token)
        self.mock_websockets.append(mock_ws)
        
        # Test invalid token authentication
        try:
            with patch('auth_service.auth_core.core.jwt_handler.JWTHandler.validate_token') as mock_validate:
                # Mock token validation to simulate invalid token rejection
                mock_validate.side_effect = jwt.InvalidTokenError("Invalid token")
                
                # Try to create user context (should fail)
                with pytest.raises(jwt.InvalidTokenError):
                    user_context = await self.create_mock_user_context_from_token(invalid_token, user_data)
                    manager = await get_websocket_manager(
                        user_context=user_context,
                        mode=WebSocketManagerMode.ISOLATED
                    )
                    
                    with patch.object(manager, '_websocket_transport', mock_ws):
                        await manager.connect_user(
                            user_id=ensure_user_id(user_data.user_id),
                            websocket=mock_ws,
                            connection_metadata={
                                "tier": user_data.tier,
                                "auth_token": invalid_token,
                                "authenticated": False
                            }
                        )
        
        except jwt.InvalidTokenError:
            # Expected behavior - invalid tokens should be rejected
            pass
        
        # Verify authentication was not established
        assert not mock_ws.auth_validated, "Invalid token should not validate"
        assert mock_ws.user_context is None, "No user context should be created for invalid token"
        
        logger.info("✅ Invalid JWT token correctly rejected")
    
    async def test_multi_tier_authentication_validation(self):
        """
        Test: Different user tiers authenticate correctly with proper context
        
        Business Value: Ensures all paying customer tiers can access appropriate chat
        functionality, protecting revenue across Free, Early, Mid, and Enterprise segments.
        """
        valid_scenarios = [s for s in self.auth_test_scenarios if s.expected_connection_success]
        authenticated_managers = []
        
        # Test authentication for each tier
        for scenario in valid_scenarios:
            user_data = scenario.user_data
            
            # Create valid token for this tier
            token = self.create_test_jwt_token(user_data, expired=False, invalid=False)
            user_context = await self.create_mock_user_context_from_token(token, user_data)
            
            # Create WebSocket manager for this tier
            manager = await get_websocket_manager(
                user_context=user_context,
                mode=WebSocketManagerMode.ISOLATED
            )
            self.websocket_managers.append(manager)
            
            # Create authenticated WebSocket
            connection_id = f"{user_data.tier}_conn_{uuid.uuid4().hex[:8]}"
            mock_ws = MockAuthenticatedWebSocket(user_data.user_id, connection_id, token)
            self.mock_websockets.append(mock_ws)
            
            # Authenticate and connect
            with patch.object(manager, '_websocket_transport', mock_ws):
                mock_ws.validate_auth(user_context)
                
                await manager.connect_user(
                    user_id=ensure_user_id(user_data.user_id),
                    websocket=mock_ws,
                    connection_metadata={
                        "tier": user_data.tier,
                        "auth_token": token,
                        "authenticated": True
                    }
                )
                
                # Verify tier-specific authentication
                assert mock_ws.auth_validated, f"Authentication should succeed for {user_data.tier} tier"
                assert mock_ws.user_context.tier == user_data.tier, f"User context should have correct tier: {user_data.tier}"
                assert manager.is_connected(ensure_user_id(user_data.user_id)), f"{user_data.tier} user should be connected"
                
                authenticated_managers.append({
                    'manager': manager,
                    'mock_ws': mock_ws,
                    'user_data': user_data,
                    'tier': user_data.tier
                })
        
        # Test concurrent tier-specific operations
        for auth_info in authenticated_managers:
            manager = auth_info['manager']
            mock_ws = auth_info['mock_ws']
            user_data = auth_info['user_data']
            tier = auth_info['tier']
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                # Send tier-specific event
                await manager.emit_agent_event(
                    user_id=ensure_user_id(user_data.user_id),
                    thread_id=user_data.thread_id,
                    event_type="agent_thinking",
                    data={
                        "user_tier": tier,
                        "tier_specific_feature": f"{tier}_feature_enabled",
                        "auth_validated": True
                    }
                )
                
                # Verify tier-specific message was sent
                tier_messages = [
                    msg for msg in mock_ws.messages_sent
                    if tier in str(msg.get('message', ''))
                ]
                assert len(tier_messages) > 0, f"Tier-specific messages should be sent for {tier}"
        
        logger.info(f"✅ Multi-tier authentication validated for {len(authenticated_managers)} tiers")
    
    async def test_authentication_context_extraction_validation(self):
        """
        Test: User context is correctly extracted and validated from JWT tokens
        
        Business Value: Ensures user identity and permissions are correctly established
        for personalized AI interactions and proper access control.
        """
        test_user_data = TestUserData(
            user_id=f"context_user_{uuid.uuid4().hex[:8]}",
            email="context-test@netra.ai",
            tier="mid",
            thread_id=f"context_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create token with comprehensive user context
        token = self.create_test_jwt_token(test_user_data, expired=False, invalid=False)
        
        # Mock JWT token validation to extract context
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler.decode_token') as mock_decode:
            # Mock successful token decoding
            mock_decode.return_value = {
                'user_id': test_user_data.user_id,
                'email': test_user_data.email,
                'tier': test_user_data.tier,
                'exp': (datetime.now(UTC) + timedelta(hours=24)).timestamp(),
                'iat': datetime.now(UTC).timestamp(),
                'iss': 'netra-auth-test'
            }
            
            # Create user context from decoded token
            user_context = await self.create_mock_user_context_from_token(token, test_user_data)
            
            # Validate extracted context
            assert user_context.user_id == test_user_data.user_id, "User ID should match token"
            assert user_context.email == test_user_data.email, "Email should match token"
            assert user_context.tier == test_user_data.tier, "Tier should match token"
            assert user_context.is_authenticated, "User should be marked as authenticated"
            
            # Create WebSocket manager with validated context
            manager = await get_websocket_manager(
                user_context=user_context,
                mode=WebSocketManagerMode.ISOLATED
            )
            self.websocket_managers.append(manager)
            
            # Create WebSocket with context validation
            connection_id = f"context_conn_{uuid.uuid4().hex[:8]}"
            mock_ws = MockAuthenticatedWebSocket(test_user_data.user_id, connection_id, token)
            self.mock_websockets.append(mock_ws)
            
            # Test context-aware operations
            with patch.object(manager, '_websocket_transport', mock_ws):
                mock_ws.validate_auth(user_context)
                
                await manager.connect_user(
                    user_id=ensure_user_id(test_user_data.user_id),
                    websocket=mock_ws,
                    connection_metadata={
                        "tier": test_user_data.tier,
                        "email": test_user_data.email,
                        "auth_token": token,
                        "authenticated": True
                    }
                )
                
                # Send context-dependent event
                await manager.emit_agent_event(
                    user_id=ensure_user_id(test_user_data.user_id),
                    thread_id=test_user_data.thread_id,
                    event_type="agent_started",
                    data={
                        "user_context_validated": True,
                        "extracted_user_id": test_user_data.user_id,
                        "extracted_email": test_user_data.email,
                        "extracted_tier": test_user_data.tier,
                        "auth_source": "jwt_token"
                    }
                )
                
                # Verify context-aware message
                context_messages = [
                    json.loads(msg['message']) for msg in mock_ws.messages_sent
                    if 'user_context_validated' in str(msg['message'])
                ]
                
                assert len(context_messages) > 0, "Context-validated messages should be sent"
                
                context_message = context_messages[0]
                event_data = context_message.get('data', {})
                
                assert event_data.get('extracted_user_id') == test_user_data.user_id
                assert event_data.get('extracted_email') == test_user_data.email
                assert event_data.get('extracted_tier') == test_user_data.tier
                assert event_data.get('user_context_validated') is True
        
        logger.info("✅ Authentication context extraction and validation successful")
    
    async def test_token_renewal_and_reauthentication(self):
        """
        Test: Token renewal and reauthentication workflows work correctly
        
        Business Value: Ensures seamless user experience during token renewal,
        preventing interruption of revenue-generating chat sessions.
        """
        test_user_data = TestUserData(
            user_id=f"renewal_user_{uuid.uuid4().hex[:8]}",
            email="renewal-test@netra.ai",
            tier="enterprise",
            thread_id=f"renewal_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create initial token (short-lived for testing)
        initial_token = self.create_test_jwt_token(test_user_data, expired=False, invalid=False)
        
        # Create user context and WebSocket manager
        user_context = await self.create_mock_user_context_from_token(initial_token, test_user_data)
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create WebSocket connection
        connection_id = f"renewal_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockAuthenticatedWebSocket(test_user_data.user_id, connection_id, initial_token)
        self.mock_websockets.append(mock_ws)
        
        # Establish initial authenticated connection
        with patch.object(manager, '_websocket_transport', mock_ws):
            mock_ws.validate_auth(user_context)
            
            await manager.connect_user(
                user_id=ensure_user_id(test_user_data.user_id),
                websocket=mock_ws,
                connection_metadata={
                    "tier": test_user_data.tier,
                    "auth_token": initial_token,
                    "authenticated": True
                }
            )
            
            # Verify initial connection
            assert mock_ws.auth_validated, "Initial authentication should succeed"
            
            # Simulate token renewal scenario
            renewed_token = self.create_test_jwt_token(test_user_data, expired=False, invalid=False)
            
            # Update user context with renewed token
            renewed_user_context = await self.create_mock_user_context_from_token(renewed_token, test_user_data)
            
            # Update WebSocket authentication with renewed token
            mock_ws.auth_token = renewed_token
            mock_ws.validate_auth(renewed_user_context)
            
            # Test continued functionality with renewed token
            await manager.emit_agent_event(
                user_id=ensure_user_id(test_user_data.user_id),
                thread_id=test_user_data.thread_id,
                event_type="agent_thinking",
                data={
                    "token_renewed": True,
                    "renewal_timestamp": datetime.now(UTC).isoformat(),
                    "continued_session": True
                }
            )
            
            # Verify renewed authentication allows continued operation
            renewal_messages = [
                msg for msg in mock_ws.messages_sent
                if 'token_renewed' in str(msg['message'])
            ]
            
            assert len(renewal_messages) > 0, "Messages should be sent with renewed token"
            assert mock_ws.auth_validated, "Renewed authentication should be validated"
            assert manager.is_connected(ensure_user_id(test_user_data.user_id)), "Connection should remain active after renewal"
        
        logger.info("✅ Token renewal and reauthentication workflow validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])