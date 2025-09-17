"""
Comprehensive Unit Tests for Unified WebSocket Authentication - SSOT Implementation

Business Value Protection: $500K+ ARR WebSocket functionality comprehensive testing
Addresses Issue #714 Phase 1A: Authentication & Event Validation Tests

This test suite provides comprehensive coverage for the unified WebSocket authentication
module, focusing on the highest-impact uncovered code paths identified in coverage analysis.

Key Test Areas:
1. JWT token validation flows and error handling
2. User context extraction and isolation
3. Authentication error scenarios and recovery
4. WebSocket handshake authentication
5. E2E context detection and security modes
6. Environment configuration validation
7. Auth service health monitoring

Coverage Target: unified_websocket_auth.py (currently 10.17% -> target 80%+)
"""

import asyncio
import json
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from datetime import datetime, timezone

import pytest
from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import target module
from netra_backend.app.websocket_core.unified_websocket_auth import (
    extract_e2e_context_from_websocket,
    WebSocketAuthResult,
    UnifiedWebSocketAuthenticator,
    get_websocket_authenticator,
    authenticate_websocket_ssot,
    authenticate_websocket_connection,
    create_authenticated_user_context,
    _validate_critical_environment_configuration,
    _extract_token_from_websocket,
    _validate_auth_service_health
)

# Import dependencies for mocking
from netra_backend.app.services.unified_authentication_service import (
    AuthResult, AuthenticationContext, AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, ensure_user_id


class UnifiedWebSocketAuthAuthenticationTests(SSotAsyncTestCase):
    """Test suite for unified WebSocket authentication functionality."""

    def setup_method(self, method):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)

        # Use SSOT mock factory for consistent mocking
        self.mock_factory = SSotMockFactory()

        # Create common test data
        self.test_user_id = "user_123"
        self.test_thread_id = "thread_456"
        self.test_token = "valid_jwt_token_here"
        self.test_websocket_id = "ws_789"

        # Mock WebSocket for testing
        self.mock_websocket = self.mock_factory.create_mock_websocket(
            state=WebSocketState.CONNECTING,
            headers={"authorization": f"Bearer {self.test_token}"}
        )

        # Reset environment state for each test
        self.env_patches = []

    def teardown_method(self, method):
        """Clean up test resources."""
        # Clean up environment patches
        for patch_obj in self.env_patches:
            if hasattr(patch_obj, 'stop'):
                patch_obj.stop()
        self.env_patches.clear()

        super().teardown_method(method)

    def _patch_environment(self, env_vars: Dict[str, str]):
        """Helper to patch environment variables for testing."""
        import shared.isolated_environment

        def mock_get_env():
            return env_vars

        patcher = patch.object(shared.isolated_environment, 'get_env', side_effect=mock_get_env)
        patch_obj = patcher.start()
        self.env_patches.append(patcher)
        return patch_obj

    def test_extract_e2e_context_production_security(self):
        """Test E2E context extraction blocks bypass in production environments."""
        # Setup production environment
        prod_env = {
            "ENVIRONMENT": "production",
            "GOOGLE_CLOUD_PROJECT": "netra-production",
            "E2E_TESTING": "1",  # Should be ignored in production
            "DEMO_MODE": "1"     # Should be ignored in production
        }
        self._patch_environment(prod_env)

        # Create WebSocket with E2E headers (should be blocked)
        headers = {
            "x-test-mode": "true",
            "x-e2e-testing": "enabled"
        }
        websocket = self.mock_factory.create_mock_websocket(headers=headers)

        # Test E2E context extraction
        context = extract_e2e_context_from_websocket(websocket)

        # In production, context should be None (no bypass allowed)
        self.assertIsNone(context, "Production environment should never allow E2E bypass")

    def test_extract_e2e_context_development_permissive(self):
        """Test E2E context extraction allows bypass in development environments."""
        # Setup development environment
        dev_env = {
            "ENVIRONMENT": "development",
            "GOOGLE_CLOUD_PROJECT": "netra-dev",
            "E2E_TESTING": "1",
            "DEMO_MODE": "1"
        }
        self._patch_environment(dev_env)

        # Create WebSocket with E2E headers
        headers = {
            "x-test-mode": "true",
            "x-e2e-testing": "enabled"
        }
        websocket = self.mock_factory.create_mock_websocket(headers=headers)

        # Test E2E context extraction
        context = extract_e2e_context_from_websocket(websocket)

        # In development, context should be available
        self.assertIsNotNone(context, "Development environment should allow E2E bypass")
        self.assertTrue(context["is_e2e_testing"])
        self.assertTrue(context["demo_mode_enabled"])

    def test_extract_e2e_context_environment_validation_failure(self):
        """Test E2E context handling when environment validation fails."""
        # Setup environment with missing critical variables
        invalid_env = {
            # Missing ENVIRONMENT, GOOGLE_CLOUD_PROJECT, etc.
        }
        self._patch_environment(invalid_env)

        websocket = self.mock_factory.create_mock_websocket()

        # Mock environment validation to fail
        with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "errors": ["Missing ENVIRONMENT variable", "Missing GOOGLE_CLOUD_PROJECT"]
            }

            # Should still attempt to extract context but log errors
            context = extract_e2e_context_from_websocket(websocket)

            # Validation should be called
            mock_validate.assert_called_once()

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service')
    async def test_websocket_auth_result_creation(self, mock_auth_service):
        """Test WebSocketAuthResult object creation and properties."""
        # Create test auth result
        auth_result = WebSocketAuthResult(
            success=True,
            user_id=self.test_user_id,
            websocket_id=self.test_websocket_id,
            thread_id=self.test_thread_id,
            token_data={"sub": self.test_user_id, "exp": time.time() + 3600},
            execution_context=None,
            error_message=None,
            auth_method=AuthenticationMethod.JWT_TOKEN
        )

        # Verify properties
        self.assertTrue(auth_result.success)
        self.assertEqual(auth_result.user_id, self.test_user_id)
        self.assertEqual(auth_result.websocket_id, self.test_websocket_id)
        self.assertEqual(auth_result.thread_id, self.test_thread_id)
        self.assertEqual(auth_result.auth_method, AuthenticationMethod.JWT_TOKEN)
        self.assertIsNotNone(auth_result.token_data)
        self.assertIsNone(auth_result.error_message)

    async def test_websocket_auth_result_failure_case(self):
        """Test WebSocketAuthResult for authentication failure scenarios."""
        # Create failed auth result
        auth_result = WebSocketAuthResult(
            success=False,
            user_id=None,
            websocket_id=self.test_websocket_id,
            thread_id=None,
            token_data=None,
            execution_context=None,
            error_message="Invalid JWT token",
            auth_method=None
        )

        # Verify failure properties
        self.assertFalse(auth_result.success)
        self.assertIsNone(auth_result.user_id)
        self.assertIsNone(auth_result.thread_id)
        self.assertIsNone(auth_result.token_data)
        self.assertEqual(auth_result.error_message, "Invalid JWT token")
        self.assertIsNone(auth_result.auth_method)

    @patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_auth_service_health')
    async def test_unified_websocket_authenticator_init(self, mock_health_check):
        """Test UnifiedWebSocketAuthenticator initialization."""
        # Mock health check
        mock_health_check.return_value = {"healthy": True, "services": ["auth", "jwt"]}

        # Create authenticator instance
        authenticator = UnifiedWebSocketAuthenticator()

        # Verify initialization
        self.assertIsNotNone(authenticator)

        # Health check should be called during init
        mock_health_check.assert_called_once()

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service')
    @patch('netra_backend.app.websocket_core.unified_websocket_auth._extract_token_from_websocket')
    async def test_authenticate_websocket_valid_token(self, mock_extract_token, mock_auth_service):
        """Test WebSocket authentication with valid JWT token."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Mock token extraction
        mock_extract_token.return_value = self.test_token

        # Mock auth service
        mock_service = AsyncMock()
        mock_auth_service.return_value = mock_service

        # Mock successful authentication
        mock_service.authenticate_token.return_value = AuthResult(
            success=True,
            user_id=self.test_user_id,
            token_data={"sub": self.test_user_id, "exp": time.time() + 3600},
            error_message=None
        )

        # Test authentication
        authenticator = UnifiedWebSocketAuthenticator()
        result = await authenticator.authenticate_websocket(self.mock_websocket, self.test_thread_id)

        # Verify successful authentication
        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.user_id, self.test_user_id)
        self.assertEqual(result.thread_id, self.test_thread_id)

        # Verify service calls
        mock_extract_token.assert_called_once_with(self.mock_websocket)
        mock_service.authenticate_token.assert_called_once()

    @patch('netra_backend.app.websocket_core.unified_websocket_auth._extract_token_from_websocket')
    async def test_authenticate_websocket_missing_token(self, mock_extract_token):
        """Test WebSocket authentication with missing token."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Mock missing token
        mock_extract_token.return_value = None

        # Test authentication
        authenticator = UnifiedWebSocketAuthenticator()
        result = await authenticator.authenticate_websocket(self.mock_websocket, self.test_thread_id)

        # Verify authentication failure
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("token", result.error_message.lower())

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service')
    @patch('netra_backend.app.websocket_core.unified_websocket_auth._extract_token_from_websocket')
    async def test_authenticate_websocket_invalid_token(self, mock_extract_token, mock_auth_service):
        """Test WebSocket authentication with invalid JWT token."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Mock token extraction
        mock_extract_token.return_value = "invalid_token"

        # Mock auth service with failure
        mock_service = AsyncMock()
        mock_auth_service.return_value = mock_service
        mock_service.authenticate_token.return_value = AuthResult(
            success=False,
            user_id=None,
            token_data=None,
            error_message="Token validation failed"
        )

        # Test authentication
        authenticator = UnifiedWebSocketAuthenticator()
        result = await authenticator.authenticate_websocket(self.mock_websocket, self.test_thread_id)

        # Verify authentication failure
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Token validation failed")

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.extract_e2e_context_from_websocket')
    async def test_authenticate_websocket_e2e_bypass(self, mock_e2e_context):
        """Test WebSocket authentication with E2E testing bypass."""
        # Setup E2E context
        mock_e2e_context.return_value = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "detection_method": {"via_environment": True}
        }

        # Test authentication with E2E bypass
        authenticator = UnifiedWebSocketAuthenticator()
        result = await authenticator.authenticate_websocket(self.mock_websocket, self.test_thread_id)

        # Verify E2E bypass authentication
        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.auth_method, AuthenticationMethod.E2E_BYPASS)

    async def test_create_authenticated_user_context(self):
        """Test creation of authenticated user execution context."""
        # Create test auth result
        auth_result = WebSocketAuthResult(
            success=True,
            user_id=self.test_user_id,
            websocket_id=self.test_websocket_id,
            thread_id=self.test_thread_id,
            token_data={"sub": self.test_user_id},
            execution_context=None,
            error_message=None,
            auth_method=AuthenticationMethod.JWT_TOKEN
        )

        # Mock user context creation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.UserExecutionContext') as mock_context_class:
            mock_context = Mock()
            mock_context_class.return_value = mock_context

            # Test context creation
            context = create_authenticated_user_context(auth_result, self.mock_websocket)

            # Verify context creation
            self.assertEqual(context, mock_context)
            mock_context_class.assert_called_once()


    def test_validate_critical_environment_configuration_valid(self):
        """Test critical environment configuration validation with valid config."""
        # Setup valid environment
        valid_env = {
            "ENVIRONMENT": "development",
            "GOOGLE_CLOUD_PROJECT": "netra-dev",
            "JWT_SECRET_KEY": "test_secret"
        }
        self._patch_environment(valid_env)

        # Test validation
        result = _validate_critical_environment_configuration()

        # Verify valid configuration
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_critical_environment_configuration_invalid(self):
        """Test critical environment configuration validation with missing config."""
        # Setup invalid environment (missing critical variables)
        invalid_env = {}
        self._patch_environment(invalid_env)

        # Test validation
        result = _validate_critical_environment_configuration()

        # Verify invalid configuration detected
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_extract_token_from_websocket_authorization_header(self):
        """Test token extraction from WebSocket Authorization header."""
        # Create WebSocket with Authorization header
        headers = {"authorization": f"Bearer {self.test_token}"}
        websocket = self.mock_factory.create_mock_websocket(headers=headers)

        # Test token extraction
        token = _extract_token_from_websocket(websocket)

        # Verify token extracted correctly
        self.assertEqual(token, self.test_token)

    def test_extract_token_from_websocket_query_param(self):
        """Test token extraction from WebSocket query parameters."""
        # Create WebSocket with token in query params
        websocket = self.mock_factory.create_mock_websocket()
        websocket.query_params = {"token": self.test_token}

        # Test token extraction
        token = _extract_token_from_websocket(websocket)

        # Verify token extracted from query params
        self.assertEqual(token, self.test_token)

    def test_extract_token_from_websocket_no_token(self):
        """Test token extraction when no token is present."""
        # Create WebSocket without token
        websocket = self.mock_factory.create_mock_websocket()

        # Test token extraction
        token = _extract_token_from_websocket(websocket)

        # Verify no token found
        self.assertIsNone(token)

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.auth_client')
    def test_validate_auth_service_health_healthy(self, mock_auth_client):
        """Test auth service health validation when services are healthy."""
        # Mock healthy auth client
        mock_auth_client.health_check.return_value = {"status": "healthy"}

        # Test health validation
        result = _validate_auth_service_health()

        # Verify healthy status
        self.assertTrue(result["healthy"])
        self.assertIn("auth", result["services"])

    @patch('netra_backend.app.websocket_core.unified_websocket_auth.auth_client')
    def test_validate_auth_service_health_unhealthy(self, mock_auth_client):
        """Test auth service health validation when services are unhealthy."""
        # Mock unhealthy auth client
        mock_auth_client.health_check.side_effect = Exception("Service unavailable")

        # Test health validation
        result = _validate_auth_service_health()

        # Verify unhealthy status detected
        self.assertFalse(result["healthy"])
        self.assertIn("errors", result)

    async def test_authenticate_websocket_ssot_function(self):
        """Test the SSOT authenticate_websocket_ssot function."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Mock authenticator
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_websocket_authenticator') as mock_get_auth:
            mock_authenticator = AsyncMock()
            mock_get_auth.return_value = mock_authenticator

            mock_result = WebSocketAuthResult(
                success=True,
                user_id=self.test_user_id,
                websocket_id=self.test_websocket_id,
                thread_id=self.test_thread_id,
                token_data={"sub": self.test_user_id},
                execution_context=None,
                error_message=None,
                auth_method=AuthenticationMethod.JWT_TOKEN
            )
            mock_authenticator.authenticate_websocket.return_value = mock_result

            # Test SSOT function
            result = await authenticate_websocket_ssot(self.mock_websocket, self.test_thread_id)

            # Verify SSOT function works correctly
            self.assertEqual(result, mock_result)
            mock_authenticator.authenticate_websocket.assert_called_once_with(
                self.mock_websocket, self.test_thread_id
            )

    async def test_authenticate_websocket_connection_function(self):
        """Test the authenticate_websocket_connection wrapper function."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Mock the SSOT function
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_ssot:
            mock_result = WebSocketAuthResult(
                success=True,
                user_id=self.test_user_id,
                websocket_id=self.test_websocket_id,
                thread_id=self.test_thread_id,
                token_data={"sub": self.test_user_id},
                execution_context=None,
                error_message=None,
                auth_method=AuthenticationMethod.JWT_TOKEN
            )
            mock_ssot.return_value = mock_result

            # Test wrapper function
            result = await authenticate_websocket_connection(self.mock_websocket, self.test_thread_id)

            # Verify wrapper delegates to SSOT function
            self.assertEqual(result, mock_result)
            mock_ssot.assert_called_once_with(self.mock_websocket, self.test_thread_id)

    def test_get_websocket_authenticator_singleton(self):
        """Test that get_websocket_authenticator returns consistent instance."""
        # Get authenticator instance twice
        auth1 = get_websocket_authenticator()
        auth2 = get_websocket_authenticator()

        # Verify same instance returned (singleton pattern)
        self.assertEqual(auth1, auth2)
        self.assertIsInstance(auth1, UnifiedWebSocketAuthenticator)

    async def test_user_isolation_between_websocket_sessions(self):
        """Test that user contexts are properly isolated between WebSocket sessions."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Create two different WebSocket connections
        ws1 = self.mock_factory.create_mock_websocket(
            headers={"authorization": "Bearer token1"}
        )
        ws2 = self.mock_factory.create_mock_websocket(
            headers={"authorization": "Bearer token2"}
        )

        # Mock different auth results for each connection
        with patch('netra_backend.app.websocket_core.unified_websocket_auth._extract_token_from_websocket') as mock_extract:
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_service:

                def side_effect_extract(ws):
                    if ws == ws1:
                        return "token1"
                    elif ws == ws2:
                        return "token2"
                    return None

                mock_extract.side_effect = side_effect_extract

                mock_auth = AsyncMock()
                mock_service.return_value = mock_auth

                def side_effect_auth(token):
                    if token == "token1":
                        return AuthResult(True, "user1", {"sub": "user1"}, None)
                    elif token == "token2":
                        return AuthResult(True, "user2", {"sub": "user2"}, None)
                    return AuthResult(False, None, None, "Invalid token")

                mock_auth.authenticate_token.side_effect = side_effect_auth

                # Authenticate both connections
                authenticator = UnifiedWebSocketAuthenticator()
                result1 = await authenticator.authenticate_websocket(ws1, "thread1")
                result2 = await authenticator.authenticate_websocket(ws2, "thread2")

                # Verify user isolation
                self.assertTrue(result1.success)
                self.assertTrue(result2.success)
                self.assertEqual(result1.user_id, "user1")
                self.assertEqual(result2.user_id, "user2")
                self.assertNotEqual(result1.user_id, result2.user_id)

    async def test_concurrent_authentication_thread_safety(self):
        """Test concurrent WebSocket authentication for thread safety."""
        # Setup environment
        self._patch_environment({"ENVIRONMENT": "development"})

        # Create multiple WebSocket connections
        websockets = [
            self.mock_factory.create_mock_websocket(
                headers={"authorization": f"Bearer token_{i}"}
            )
            for i in range(5)
        ]

        # Mock authentication for concurrent requests
        with patch('netra_backend.app.websocket_core.unified_websocket_auth._extract_token_from_websocket') as mock_extract:
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_service:

                mock_extract.side_effect = lambda ws: f"token_{websockets.index(ws)}"

                mock_auth = AsyncMock()
                mock_service.return_value = mock_auth
                mock_auth.authenticate_token.return_value = AuthResult(
                    True, "user_test", {"sub": "user_test"}, None
                )

                # Authenticate all connections concurrently
                authenticator = UnifiedWebSocketAuthenticator()
                tasks = [
                    authenticator.authenticate_websocket(ws, f"thread_{i}")
                    for i, ws in enumerate(websockets)
                ]

                results = await asyncio.gather(*tasks)

                # Verify all authentications succeeded
                for result in results:
                    self.assertTrue(result.success)
                    self.assertEqual(result.user_id, "user_test")

                # Verify service was called for each request
                self.assertEqual(mock_auth.authenticate_token.call_count, len(websockets))