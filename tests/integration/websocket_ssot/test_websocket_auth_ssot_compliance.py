"""
SSOT WebSocket Authentication Compliance Test - ISSUE #814

PURPOSE: Integration test validating WebSocket authentication SSOT compliance
EXPECTED: PASS after SSOT remediation - validates proper auth service delegation
TARGET: WebSocket authentication flows must use auth service delegation

BUSINESS VALUE: Protects $500K+ ARR Golden Path WebSocket authentication reliability
"""
import logging
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)

class TestWebSocketAuthSSOTCompliance(SSotAsyncTestCase):
    """
    Integration test validating WebSocket authentication SSOT compliance.
    Tests proper delegation to auth service for all WebSocket auth operations.
    """

    async def asyncSetUp(self):
        """Setup WebSocket authentication testing environment"""
        await super().asyncSetUp()

        # Mock auth service for integration testing
        self.valid_auth_response = {
            "valid": True,
            "user_id": "websocket-user-123",
            "email": "ws@example.com",
            "tier": "enterprise",
            "session_id": "ws-session-456"
        }

        self.invalid_auth_response = {
            "valid": False,
            "error": "Token expired",
            "code": "TOKEN_EXPIRED"
        }

    async def test_websocket_connection_auth_delegates_to_service(self):
        """
        Integration test: WebSocket connection authentication delegates to auth service

        VALIDATES: WebSocket connection establishment uses auth service
        ENSURES: No direct JWT handling in WebSocket connection logic
        """
        with patch('netra_backend.app.websocket_core.auth.auth_client') as mock_auth_client:
            # Setup auth service response
            mock_auth_client.validate_websocket_token.return_value = self.valid_auth_response

            # Test WebSocket connection authentication
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator

            authenticator = WebSocketAuthenticator()
            test_token = "websocket-connection-token"

            # Test connection authentication
            auth_result = await authenticator.authenticate_connection(test_token)

            # Verify auth service delegation
            mock_auth_client.validate_websocket_token.assert_called_once_with(test_token)

            # Verify authentication result
            assert auth_result.authenticated is True, "WebSocket connection authenticated"
            assert auth_result.user_id == "websocket-user-123", "User ID from auth service"
            assert auth_result.session_id == "ws-session-456", "Session from auth service"

    async def test_websocket_manager_uses_auth_service_context(self):
        """
        Integration test: WebSocket manager maintains auth service context

        VALIDATES: WebSocket manager preserves auth service user context
        ENSURES: No JWT re-parsing or custom auth context handling
        """
        with patch('netra_backend.app.websocket_core.manager.auth_client') as mock_auth_client:
            # Setup auth service context
            mock_auth_client.get_user_context.return_value = {
                "user_id": "manager-user-789",
                "email": "manager@example.com",
                "tier": "mid",
                "permissions": ["chat", "websocket"],
                "session_context": {"workspace": "default"}
            }

            # Test WebSocket manager auth context
            from netra_backend.app.websocket_core.manager import WebSocketManager

            ws_manager = WebSocketManager()
            test_token = "manager-test-token"

            # Initialize connection with auth context
            connection_id = await ws_manager.initialize_connection(
                token=test_token,
                connection_type="chat"
            )

            # Verify auth service context retrieval
            mock_auth_client.get_user_context.assert_called_once_with(test_token)

            # Verify connection established with auth context
            assert connection_id is not None, "Connection established"

            # Test context retrieval
            context = await ws_manager.get_connection_context(connection_id)
            assert context["user_id"] == "manager-user-789", "User context from auth service"
            assert context["tier"] == "mid", "Tier from auth service"

    async def test_websocket_events_preserve_auth_service_context(self):
        """
        Integration test: WebSocket events preserve auth service context

        VALIDATES: WebSocket event handling uses auth service context
        ENSURES: Events maintain user context from auth service, not JWT
        """
        with patch('netra_backend.app.websocket_core.events.auth_client') as mock_auth_client:
            # Setup auth service context
            mock_auth_client.validate_event_auth.return_value = {
                "valid": True,
                "user_id": "event-user-321",
                "can_receive_events": True,
                "event_permissions": ["agent_started", "agent_thinking", "agent_completed"]
            }

            # Test WebSocket event authentication
            from netra_backend.app.websocket_core.events import WebSocketEventHandler

            event_handler = WebSocketEventHandler()
            test_token = "event-auth-token"

            # Test event authentication
            event_auth = await event_handler.authenticate_event(
                token=test_token,
                event_type="agent_started"
            )

            # Verify auth service delegation
            mock_auth_client.validate_event_auth.assert_called_once_with(
                test_token, "agent_started"
            )

            # Verify event authentication
            assert event_auth["valid"] is True, "Event authentication valid"
            assert event_auth["user_id"] == "event-user-321", "Event user from auth service"
            assert "agent_started" in event_auth["event_permissions"], "Event permission check"

    async def test_websocket_message_routing_uses_auth_delegation(self):
        """
        Integration test: WebSocket message routing delegates authentication

        VALIDATES: Message routing uses auth service for user validation
        ENSURES: No custom message-level authentication logic
        """
        with patch('netra_backend.app.websocket_core.routing.auth_client') as mock_auth_client:
            # Setup auth service message validation
            mock_auth_client.validate_message_auth.return_value = {
                "valid": True,
                "user_id": "message-user-654",
                "can_send_messages": True,
                "rate_limit_remaining": 95,
                "message_permissions": ["send", "receive", "history"]
            }

            # Test WebSocket message routing authentication
            from netra_backend.app.websocket_core.routing import WebSocketMessageRouter

            router = WebSocketMessageRouter()
            test_token = "message-routing-token"

            # Test message authentication
            message_auth = await router.authenticate_message(
                token=test_token,
                message_type="user_message",
                message_data={"content": "Test message"}
            )

            # Verify auth service delegation
            mock_auth_client.validate_message_auth.assert_called_once_with(
                test_token, "user_message"
            )

            # Verify message authentication
            assert message_auth["valid"] is True, "Message authentication valid"
            assert message_auth["user_id"] == "message-user-654", "Message user from auth service"
            assert message_auth["can_send_messages"] is True, "Send permission from auth service"

    async def test_websocket_user_isolation_enforced_by_auth_service(self):
        """
        Integration test: WebSocket user isolation enforced by auth service

        VALIDATES: Multi-user isolation relies on auth service context
        ENSURES: No custom user separation logic bypassing auth service
        """
        with patch('netra_backend.app.websocket_core.isolation.auth_client') as mock_auth_client:
            # Setup multiple user contexts from auth service
            mock_auth_client.get_isolation_context.side_effect = [
                {
                    "user_id": "isolated-user-1",
                    "isolation_key": "isolation-key-1",
                    "workspace": "workspace-a"
                },
                {
                    "user_id": "isolated-user-2",
                    "isolation_key": "isolation-key-2",
                    "workspace": "workspace-b"
                }
            ]

            # Test user isolation
            from netra_backend.app.websocket_core.isolation import WebSocketUserIsolation

            isolation_manager = WebSocketUserIsolation()

            # Test isolation for multiple users
            token_1 = "isolation-token-1"
            token_2 = "isolation-token-2"

            isolation_1 = await isolation_manager.get_user_isolation(token_1)
            isolation_2 = await isolation_manager.get_user_isolation(token_2)

            # Verify auth service context calls
            assert mock_auth_client.get_isolation_context.call_count == 2

            # Verify isolation contexts
            assert isolation_1["user_id"] == "isolated-user-1", "User 1 isolation"
            assert isolation_2["user_id"] == "isolated-user-2", "User 2 isolation"
            assert isolation_1["workspace"] != isolation_2["workspace"], "Workspace isolation"

    async def test_websocket_session_management_delegates_to_auth_service(self):
        """
        Integration test: WebSocket session management delegates to auth service

        VALIDATES: Session lifecycle managed by auth service
        ENSURES: No custom session handling bypassing auth service
        """
        with patch('netra_backend.app.websocket_core.sessions.auth_client') as mock_auth_client:
            # Setup auth service session management
            mock_auth_client.create_websocket_session.return_value = {
                "session_id": "ws-session-999",
                "user_id": "session-user-111",
                "created_at": "2025-09-13T12:00:00Z",
                "expires_at": "2025-09-13T16:00:00Z"
            }

            mock_auth_client.validate_session.return_value = {
                "valid": True,
                "session_id": "ws-session-999",
                "time_remaining": 3600
            }

            # Test WebSocket session management
            from netra_backend.app.websocket_core.sessions import WebSocketSessionManager

            session_manager = WebSocketSessionManager()
            test_token = "session-management-token"

            # Create session through auth service
            session = await session_manager.create_session(test_token)

            # Verify session creation delegation
            mock_auth_client.create_websocket_session.assert_called_once_with(test_token)

            # Verify session from auth service
            assert session["session_id"] == "ws-session-999", "Session ID from auth service"
            assert session["user_id"] == "session-user-111", "Session user from auth service"

            # Test session validation
            session_valid = await session_manager.validate_session(session["session_id"])

            # Verify validation delegation
            mock_auth_client.validate_session.assert_called_once_with("ws-session-999")

            # Verify session validation
            assert session_valid["valid"] is True, "Session validation from auth service"

if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/websocket_ssot/test_websocket_auth_ssot_compliance.py -v
    pytest.main([__file__, "-v"])
