"""
Async tests for WebSocket authentication
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    WebSocketAuthResult,
    get_websocket_authenticator
)
from netra_backend.app.websocket_core.auth import WebSocketAuthenticator, AuthHandler
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.asyncio
class TestWebSocketAuthAsync:
    """Async test suite for WebSocket Authentication using SSOT patterns"""

    async def test_auth_result_creation(self):
        """Test WebSocketAuthResult creation and properties"""
        # Create a mock auth result
        auth_result = WebSocketAuthResult(
            success=True,
            user_context=None,
            auth_result=None,
            error_message=None,
            error_code=None
        )
        assert auth_result.success is True
        assert auth_result.is_valid is True  # Property, not method
        assert auth_result.user_id is None  # Should be None when user_context is None
        assert auth_result.email is None

    async def test_auth_result_failure(self):
        """Test WebSocketAuthResult failure case"""
        auth_result = WebSocketAuthResult(
            success=False,
            user_context=None,
            auth_result=None,
            error_message="Authentication failed",
            error_code="INVALID_TOKEN"
        )
        assert auth_result.success is False
        assert auth_result.is_valid is False
        assert auth_result.error_message == "Authentication failed"
        assert auth_result.error_code == "INVALID_TOKEN"

    async def test_ssot_authenticator_function_exists(self):
        """Test that the SSOT authentication function exists and is callable"""
        # Test that the function exists and is callable
        assert callable(authenticate_websocket_ssot)

        # Test that it's an async function
        import inspect
        assert inspect.iscoroutinefunction(authenticate_websocket_ssot)

    async def test_websocket_authenticator_factory(self):
        """Test that the authenticator factory returns a valid instance"""
        authenticator = get_websocket_authenticator()
        assert authenticator is not None
        # Should have the deprecated warning but still be functional
        assert hasattr(authenticator, 'get_websocket_auth_stats')

    async def test_compatibility_layer_authenticator(self):
        """Test the compatibility layer WebSocketAuthenticator"""
        # Test that the compatibility layer class exists and can be instantiated
        authenticator = WebSocketAuthenticator()
        assert authenticator is not None
        # Should delegate to SSOT implementation
        assert hasattr(authenticator, 'get_websocket_auth_stats')

    async def test_compatibility_layer_auth_handler(self):
        """Test the compatibility layer AuthHandler"""
        # Test that the AuthHandler class exists and can be instantiated
        handler = AuthHandler()
        assert handler is not None
        # Should have basic auth handler methods
        assert hasattr(handler, 'connect')
        assert hasattr(handler, 'disconnect')
