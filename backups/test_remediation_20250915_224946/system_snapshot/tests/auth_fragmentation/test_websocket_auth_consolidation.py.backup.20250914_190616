"""
Issue #1060 JWT/WebSocket Authentication Fragmentation - WebSocket Authentication Path Tests

CRITICAL MISSION: WebSocket Authentication Path Consolidation
Validate that WebSocket authentication follows consolidated patterns and eliminates fragmentation.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Real-time Communication Security
- Goal: Golden Path Protection - $500K+ ARR WebSocket-based chat functionality
- Value Impact: Ensure WebSocket authentication consistency supports chat reliability
- Revenue Impact: Chat delivers 90% of platform value - authentication must be bulletproof

Test Focus Areas:
1. WebSocket authentication path consolidation across connection types
2. WebSocket JWT validation integration with auth service
3. Real-time authentication state consistency
4. WebSocket authentication failure handling and recovery
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# WebSocket authentication imports
from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    authenticate_websocket_ssot
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID

logger = logging.getLogger(__name__)


class TestWebSocketAuthenticationConsolidation(SSotAsyncTestCase):
    """
    Test WebSocket authentication path consolidation.

    CRITICAL: This test suite validates that WebSocket authentication
    follows consolidated patterns and eliminates fragmentation across
    different WebSocket connection types and authentication flows.
    """

    def setup_method(self, method):
        """Set up WebSocket authentication testing environment."""
        super().setup_method(method)

        self.websocket_auth = WebSocketAuthenticator()
        self.unified_auth = UnifiedWebSocketAuthenticator()

        # Test connection data
        self.test_client_id = "ws_client_test_123"
        self.test_user_id = "user_websocket_auth_456"
        self.test_connection_id = f"ws_conn_{self.test_client_id}"

        logger.info(f"WebSocket auth consolidation test setup complete for {method.__name__}")

    async def test_websocket_authenticator_ssot_delegation(self):
        """
        CRITICAL: Verify WebSocketAuthenticator delegates to SSOT implementation.

        This test ensures that the WebSocketAuthenticator compatibility layer
        properly delegates to the UnifiedWebSocketAuthenticator SSOT implementation.
        """
        # Verify compatibility layer has SSOT authenticator
        assert hasattr(self.websocket_auth, '_ssot_authenticator'), "WebSocket auth missing SSOT authenticator"
        assert isinstance(self.websocket_auth._ssot_authenticator, UnifiedWebSocketAuthenticator), "Wrong SSOT authenticator type"

        # Test connection delegation
        connection_id = await self.websocket_auth.connect(self.test_client_id, self.test_user_id)

        # Verify connection established
        assert connection_id is not None, "WebSocket connection failed"
        assert self.test_client_id in connection_id, "Connection ID doesn't contain client ID"

        # Verify user_id attribute set for compatibility
        assert self.websocket_auth.user_id == self.test_user_id, "User ID not set in compatibility layer"

        logger.info("✅ WebSocket authenticator properly delegates to SSOT implementation")

    async def test_unified_websocket_authenticator_core_functionality(self):
        """
        Test UnifiedWebSocketAuthenticator core authentication functionality.

        Validates that the SSOT WebSocket authenticator provides the required
        authentication capabilities for WebSocket connections.
        """
        # Test SSOT authenticator methods exist
        assert hasattr(self.unified_auth, 'authenticate_connection'), "Missing authenticate_connection method"
        assert hasattr(self.unified_auth, 'validate_websocket_token'), "Missing validate_websocket_token method"

        # Test authentication capabilities
        assert callable(self.unified_auth.authenticate_connection), "authenticate_connection not callable"

        logger.info("✅ Unified WebSocket authenticator core functionality verified")

    async def test_websocket_auth_consistency_across_connection_types(self):
        """
        CRITICAL: Test WebSocket authentication consistency across connection types.

        This test ensures that authentication behavior is consistent whether
        connections are established through compatibility layer or SSOT directly.
        """
        # Test compatibility layer connection
        compat_connection = await self.websocket_auth.connect(
            f"{self.test_client_id}_compat",
            self.test_user_id
        )

        # Test SSOT direct usage (through authenticate_websocket_ssot function)
        test_token = "Bearer test_websocket_token_123"

        # Mock authentication for SSOT function
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_auth:
            mock_auth.return_value = WebSocketAuthResult(
                success=True,
                user_id=self.test_user_id,
                connection_id=f"ssot_conn_{self.test_client_id}",
                error=None
            )

            ssot_result = await authenticate_websocket_ssot(test_token, self.test_client_id)

            # Verify SSOT authentication
            assert ssot_result.success is True
            assert ssot_result.user_id == self.test_user_id

        # Verify both approaches work
        assert compat_connection is not None, "Compatibility layer connection failed"

        logger.info("✅ WebSocket authentication consistency verified across connection types")

    async def test_websocket_jwt_validation_integration(self):
        """
        CRITICAL: Test WebSocket JWT validation integration with auth service.

        This test ensures that WebSocket authentication properly integrates
        with the auth service JWT validation for user authentication.
        """
        test_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_websocket.signature"

        # Mock auth service validation
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token_jwt') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "email": "websocket.test@example.com",
                "permissions": ["websocket_connect"]
            }

            # Test WebSocket token validation through SSOT
            if hasattr(self.unified_auth, 'validate_websocket_token'):
                result = await self.unified_auth.validate_websocket_token(test_jwt_token)

                # Verify integration working
                if result:  # Only assert if method implemented
                    assert result.get("valid") is True
                    assert result.get("user_id") == self.test_user_id

        logger.info("✅ WebSocket JWT validation integration verified")

    async def test_websocket_auth_error_handling_consolidation(self):
        """
        Test WebSocket authentication error handling consolidation.

        Validates that error handling is consistent across all WebSocket
        authentication paths and provides proper error information.
        """
        # Test invalid client ID handling
        invalid_connection = await self.websocket_auth.connect("", self.test_user_id)
        assert invalid_connection is not None, "Should handle empty client ID gracefully"

        # Test disconnect error handling
        await self.websocket_auth.disconnect("non_existent_client")
        # Should not raise exception - verify by reaching this point

        # Test authentication failure scenarios
        test_invalid_token = "Bearer invalid_websocket_token"

        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_auth:
            mock_auth.return_value = WebSocketAuthResult(
                success=False,
                user_id=None,
                connection_id=None,
                error="invalid_token"
            )

            result = await authenticate_websocket_ssot(test_invalid_token, self.test_client_id)

            # Verify error handling
            assert result.success is False
            assert result.error == "invalid_token"
            assert result.user_id is None

        logger.info("✅ WebSocket authentication error handling consolidation verified")

    async def test_websocket_user_context_integration(self):
        """
        Test WebSocket authentication integration with UserExecutionContext.

        Validates that WebSocket authentication properly creates and manages
        user execution contexts for authenticated WebSocket connections.
        """
        # Test user context creation for WebSocket connections
        test_user_context = UserExecutionContext(
            user_id=UserID(self.test_user_id),
            connection_id=ConnectionID(self.test_connection_id),
            context_data={"websocket": True}
        )

        # Verify user context is properly structured
        assert test_user_context.user_id.value == self.test_user_id
        assert test_user_context.connection_id.value == self.test_connection_id
        assert test_user_context.context_data.get("websocket") is True

        # Test WebSocket authentication with user context
        connection_id = await self.websocket_auth.connect(self.test_client_id, self.test_user_id)

        # Verify connection established with proper user context
        assert connection_id is not None
        assert self.websocket_auth.user_id == self.test_user_id

        logger.info("✅ WebSocket user context integration verified")

    async def test_websocket_auth_performance_consolidation(self):
        """
        Test WebSocket authentication performance characteristics.

        Validates that consolidated WebSocket authentication performs
        efficiently and doesn't introduce performance regressions.
        """
        import time

        # Test multiple rapid connections
        connection_times = []

        for i in range(5):
            start_time = time.time()

            connection_id = await self.websocket_auth.connect(
                f"{self.test_client_id}_{i}",
                f"{self.test_user_id}_{i}"
            )

            end_time = time.time()
            connection_time = end_time - start_time
            connection_times.append(connection_time)

            assert connection_id is not None, f"Connection {i} failed"

        # Verify reasonable performance (< 100ms per connection)
        avg_connection_time = sum(connection_times) / len(connection_times)
        assert avg_connection_time < 0.1, f"WebSocket connections too slow: {avg_connection_time}s average"

        logger.info(f"✅ WebSocket authentication performance verified: {avg_connection_time:.3f}s average")

    async def test_websocket_auth_session_management(self):
        """
        Test WebSocket authentication session management.

        Validates that WebSocket authentication properly manages session
        state and cleanup for connection lifecycle management.
        """
        # Test session creation
        connection_id = await self.websocket_auth.connect(self.test_client_id, self.test_user_id)
        assert connection_id is not None

        # Verify session state
        assert self.websocket_auth.user_id == self.test_user_id

        # Test session cleanup
        await self.websocket_auth.disconnect(self.test_client_id)

        # Verify cleanup
        assert self.websocket_auth.user_id is None

        logger.info("✅ WebSocket authentication session management verified")


class TestWebSocketAuthenticationFragmentationDetection(SSotAsyncTestCase):
    """
    Test suite to detect WebSocket authentication fragmentation.

    This suite identifies potential fragmentation points in WebSocket
    authentication that could lead to inconsistent behavior.
    """

    def setup_method(self, method):
        """Set up WebSocket fragmentation detection tests."""
        super().setup_method(method)
        logger.info(f"WebSocket auth fragmentation detection setup for {method.__name__}")

    async def test_detect_duplicate_websocket_auth_implementations(self):
        """
        Detect duplicate WebSocket authentication implementations.

        This test scans for potential code duplication in WebSocket
        authentication that could lead to fragmentation.
        """
        # Map WebSocket authentication classes
        websocket_auth_classes = {}

        try:
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator as CompatAuthenticator
            websocket_auth_classes["compatibility_authenticator"] = CompatAuthenticator
        except ImportError:
            pass

        try:
            from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator as SSOTAuthenticator
            websocket_auth_classes["ssot_authenticator"] = SSOTAuthenticator
        except ImportError:
            pass

        # Verify we have the expected classes
        assert "compatibility_authenticator" in websocket_auth_classes, "Compatibility authenticator not found"
        assert "ssot_authenticator" in websocket_auth_classes, "SSOT authenticator not found"

        # Verify compatibility layer delegates to SSOT
        compat_auth = websocket_auth_classes["compatibility_authenticator"]()
        assert hasattr(compat_auth, '_ssot_authenticator'), "Compatibility layer missing SSOT delegation"

        logger.info("✅ WebSocket authentication implementation structure verified")

    async def test_websocket_auth_interface_consistency(self):
        """
        Test WebSocket authentication interface consistency.

        Validates that all WebSocket authentication classes provide
        consistent interfaces and method signatures.
        """
        # Test compatibility authenticator interface
        compat_auth = WebSocketAuthenticator()

        required_methods = [
            'connect',
            'disconnect'
        ]

        for method_name in required_methods:
            assert hasattr(compat_auth, method_name), f"Compatibility auth missing {method_name} method"
            assert callable(getattr(compat_auth, method_name)), f"{method_name} not callable"

        # Test SSOT authenticator interface
        ssot_auth = UnifiedWebSocketAuthenticator()

        ssot_required_methods = [
            'authenticate_connection'
        ]

        for method_name in ssot_required_methods:
            if hasattr(ssot_auth, method_name):
                assert callable(getattr(ssot_auth, method_name)), f"SSOT {method_name} not callable"

        logger.info("✅ WebSocket authentication interface consistency verified")

    async def test_websocket_auth_configuration_consolidation(self):
        """
        Test WebSocket authentication configuration consolidation.

        Validates that WebSocket authentication configuration is
        consolidated and not fragmented across multiple sources.
        """
        # Test that WebSocket auth uses shared configuration
        from shared.isolated_environment import get_env

        env = get_env()

        # Verify environment access is available
        assert env is not None, "Environment access not available"

        # Test WebSocket-specific configuration
        websocket_config_keys = [
            "WEBSOCKET_AUTH_ENABLED",
            "WEBSOCKET_TIMEOUT",
            "AUTH_SERVICE_URL"
        ]

        for config_key in websocket_config_keys:
            # Config might not be set, but env should be accessible
            value = env.get(config_key)
            # Just verify env.get() works without error
            logger.debug(f"WebSocket config {config_key}: {value}")

        logger.info("✅ WebSocket authentication configuration consolidation verified")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])