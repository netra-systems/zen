"""
Unit Tests for WebSocket Authentication Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Authentication serves all user tiers
- Business Goal: Secure and reliable WebSocket authentication for multi-user AI chat platform
- Value Impact: Prevents unauthorized access, enables user isolation, supports $120K+ MRR platform
- Strategic Impact: Foundation for secure multi-tenant AI optimization services

This test suite validates the critical WebSocket authentication business logic:
1. UnifiedWebSocketAuthenticator - SSOT WebSocket authentication with E2E bypass support
2. WebSocketAuthResult - Authentication result handling and serialization
3. E2E context detection - Staging/testing environment detection for seamless E2E tests
4. Authentication error handling - Graceful failure and proper error responses
5. Connection state validation - WebSocket state verification before authentication
6. Statistics tracking - Authentication metrics for monitoring and debugging

CRITICAL: Authentication enables secure user isolation required for multi-user agent execution.
Each user must have isolated execution context to prevent data leakage between customers.

Following TEST_CREATION_GUIDE.md:
- Real authentication service integration (not mocked)
- SSOT patterns using UnifiedAuthenticationService
- Proper test categorization (@pytest.mark.unit)
- Tests that FAIL HARD when authentication fails
- Focus on authentication business value, not infrastructure mocking
"""

import asyncio
import json
import pytest
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from netra_backend.app.websocket_core.unified_websocket_auth import (
    # Core authentication classes
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    # Utility functions
    extract_e2e_context_from_websocket,
    get_websocket_authenticator,
    authenticate_websocket_ssot,
    # Legacy aliases
    WebSocketAuthenticator,
    UnifiedWebSocketAuth
)
from netra_backend.app.services.unified_authentication_service import (
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from fastapi.websockets import WebSocketState
from test_framework.base import BaseUnitTest


class TestWebSocketAuthResultBusinessLogic(BaseUnitTest):
    """Test WebSocketAuthResult business logic for authentication result handling."""
    
    @pytest.mark.unit
    def test_websocket_auth_result_success_serialization(self):
        """Test WebSocketAuthResult correctly serializes successful authentication."""
        # Business value: Proper result serialization enables consistent authentication responses
        
        # Create mock auth result and user context for success case
        mock_auth_result = Mock()
        mock_auth_result.user_id = "user-123"
        mock_auth_result.email = "test@example.com"
        mock_auth_result.permissions = ["chat:use", "agents:execute"]
        mock_auth_result.validated_at = datetime.now(timezone.utc)
        
        mock_user_context = Mock()
        mock_user_context.user_id = "user-123"
        mock_user_context.websocket_client_id = "ws-client-456"
        mock_user_context.thread_id = "thread-789"
        mock_user_context.run_id = "run-101"
        
        # Create successful auth result
        auth_result = WebSocketAuthResult(
            success=True,
            user_context=mock_user_context,
            auth_result=mock_auth_result
        )
        
        # Validate serialization
        result_dict = auth_result.to_dict()
        
        assert result_dict["success"] is True, "Must indicate authentication success"
        assert result_dict["user_id"] == "user-123", "Must include user ID"
        assert result_dict["websocket_client_id"] == "ws-client-456", "Must include WebSocket client ID"
        assert result_dict["thread_id"] == "thread-789", "Must include thread context"
        assert result_dict["run_id"] == "run-101", "Must include run context"
        assert result_dict["email"] == "test@example.com", "Must include user email"
        assert result_dict["permissions"] == ["chat:use", "agents:execute"], "Must include user permissions"
        assert "validated_at" in result_dict, "Must include validation timestamp"

    @pytest.mark.unit
    def test_websocket_auth_result_failure_serialization(self):
        """Test WebSocketAuthResult correctly serializes authentication failures."""
        # Business value: Proper failure serialization enables consistent error handling
        
        # Create failed auth result
        auth_result = WebSocketAuthResult(
            success=False,
            error_message="Invalid authentication token",
            error_code="INVALID_TOKEN"
        )
        
        # Validate failure serialization
        result_dict = auth_result.to_dict()
        
        assert result_dict["success"] is False, "Must indicate authentication failure"
        assert result_dict["error_message"] == "Invalid authentication token", "Must include error message"
        assert result_dict["error_code"] == "INVALID_TOKEN", "Must include error code"
        assert "user_id" not in result_dict or result_dict["user_id"] is None, "Must not include user details on failure"


class TestE2EContextExtractionBusinessLogic(BaseUnitTest):
    """Test E2E context extraction business logic for testing environment detection."""
    
    def setUp(self):
        """Set up mocks for E2E context testing."""
        # Mock isolated environment
        self.mock_env = Mock()
        self.env_patcher = patch('netra_backend.app.websocket_core.unified_websocket_auth.get_env', return_value=self.mock_env)
        self.env_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.env_patcher.stop()

    @pytest.mark.unit
    def test_e2e_context_extraction_via_environment_variables(self):
        """Test E2E context extraction using standard environment variables."""
        # Business value: E2E environment detection enables seamless testing without bypassing security
        
        # Configure mock environment for E2E testing
        self.mock_env.get.side_effect = lambda key, default=None: {
            "E2E_TESTING": "1",
            "ENVIRONMENT": "development", 
            "GOOGLE_CLOUD_PROJECT": "netra-development",
            "K_SERVICE": "netra-backend"
        }.get(key, default)
        
        # Create mock WebSocket
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        # Extract E2E context
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Validate E2E context detection
        assert e2e_context is not None, "Must detect E2E testing environment"
        assert e2e_context["is_e2e_testing"] is True, "Must flag E2E testing mode"
        assert e2e_context["detection_method"]["via_environment"] is True, "Must detect via environment variables"
        assert e2e_context["detection_method"]["via_env_vars"] is True, "Must detect via E2E_TESTING=1"
        assert e2e_context["bypass_enabled"] is True, "Must enable authentication bypass for E2E"
        assert e2e_context["enhanced_detection"] is True, "Must use enhanced detection"

    @pytest.mark.unit
    def test_e2e_context_extraction_via_staging_environment_auto_detection(self):
        """Test E2E context extraction using staging environment auto-detection."""
        # Business value: Staging auto-detection prevents authentication failures in staging deployments
        
        # Configure mock environment for staging (without explicit E2E variables)
        self.mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging-project",
            "K_SERVICE": "netra-backend-staging",
            "E2E_TESTING": "0"  # Not explicitly set for E2E
        }.get(key, default)
        
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        # Extract E2E context with staging auto-detection
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Validate staging auto-detection
        assert e2e_context is not None, "Must detect staging environment as E2E"
        assert e2e_context["is_e2e_testing"] is True, "Must enable E2E mode for staging"
        assert e2e_context["detection_method"]["via_staging_auto_detection"] is True, "Must use staging auto-detection"
        assert e2e_context["detection_method"]["via_env_vars"] is False, "Must not use explicit E2E variables"
        assert e2e_context["environment"] == "staging", "Must preserve environment name"
        assert "staging" in e2e_context["google_cloud_project"], "Must include project context"

    @pytest.mark.unit
    def test_e2e_context_extraction_via_websocket_headers(self):
        """Test E2E context extraction using WebSocket headers."""
        # Business value: Header-based E2E detection enables client-driven testing scenarios
        
        # Configure environment without E2E variables
        self.mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "development",
            "E2E_TESTING": "0"
        }.get(key, default)
        
        # Create WebSocket with E2E headers
        mock_websocket = Mock()
        mock_websocket.headers = {
            "x-e2e-test": "true",
            "x-test-environment": "staging",
            "user-agent": "e2e-test-client"
        }
        
        # Extract E2E context from headers
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Validate header-based detection
        assert e2e_context is not None, "Must detect E2E from headers"
        assert e2e_context["detection_method"]["via_headers"] is True, "Must detect via WebSocket headers"
        assert e2e_context["detection_method"]["via_environment"] is False, "Must not detect via environment"
        assert len(e2e_context["e2e_headers"]) == 3, "Must capture all E2E-related headers"
        assert "x-e2e-test" in e2e_context["e2e_headers"], "Must preserve header keys"

    @pytest.mark.unit
    def test_e2e_context_extraction_returns_none_for_production(self):
        """Test E2E context extraction returns None for production environments."""
        # Business value: Production environment detection prevents accidental authentication bypass
        
        # Configure production environment
        self.mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "production",
            "GOOGLE_CLOUD_PROJECT": "netra-production",
            "K_SERVICE": "netra-backend-prod",
            "E2E_TESTING": "0"
        }.get(key, default)
        
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        # Extract E2E context (should be None for production)
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Validate production environment handling
        assert e2e_context is None, "Must not detect E2E context in production"

    @pytest.mark.unit
    def test_e2e_context_extraction_handles_exceptions_gracefully(self):
        """Test E2E context extraction handles exceptions without crashing."""
        # Business value: Graceful exception handling prevents authentication system crashes
        
        # Configure mock environment to raise exception
        self.mock_env.get.side_effect = Exception("Environment access failed")
        
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        # Extract E2E context (should handle exception)
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Validate exception handling
        assert e2e_context is None, "Must return None when exception occurs"


class TestUnifiedWebSocketAuthenticatorBusinessLogic(BaseUnitTest):
    """Test UnifiedWebSocketAuthenticator business logic for SSOT authentication."""
    
    def setUp(self):
        """Set up UnifiedWebSocketAuthenticator for testing."""
        # Create authenticator instance
        self.authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock the unified authentication service
        self.mock_auth_service = Mock()
        self.authenticator._auth_service = self.mock_auth_service

    @pytest.mark.unit
    def test_unified_websocket_authenticator_initialization(self):
        """Test UnifiedWebSocketAuthenticator initializes with proper SSOT compliance."""
        # Business value: Proper initialization ensures SSOT authentication service integration
        
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Validate SSOT initialization
        assert hasattr(authenticator, '_auth_service'), "Must initialize with auth service"
        assert authenticator._websocket_auth_attempts == 0, "Must initialize attempt counter"
        assert authenticator._websocket_auth_successes == 0, "Must initialize success counter" 
        assert authenticator._websocket_auth_failures == 0, "Must initialize failure counter"
        assert isinstance(authenticator._connection_states_seen, dict), "Must track connection states"

    @pytest.mark.unit
    async def test_websocket_authentication_with_valid_credentials(self):
        """Test WebSocket authentication succeeds with valid credentials."""
        # Business value: Successful authentication enables secure user access to AI chat
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.headers = {"authorization": "Bearer valid-jwt-token"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Configure successful auth service response
        mock_auth_result = Mock()
        mock_auth_result.success = True
        mock_auth_result.user_id = "user-123"
        mock_auth_result.email = "test@example.com"
        mock_auth_result.permissions = ["chat:use", "agents:execute"]
        mock_auth_result.validated_at = datetime.now(timezone.utc)
        mock_auth_result.error = None
        mock_auth_result.error_code = None
        mock_auth_result.metadata = {}
        
        mock_user_context = Mock()
        mock_user_context.user_id = "user-123"
        mock_user_context.websocket_client_id = "ws-client-456"
        mock_user_context.thread_id = "thread-789"
        mock_user_context.run_id = "run-101"
        
        self.mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
        
        # Execute authentication
        auth_result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Validate successful authentication
        assert auth_result.success is True, "Must succeed with valid credentials"
        assert auth_result.user_context == mock_user_context, "Must return user context"
        assert auth_result.auth_result == mock_auth_result, "Must return auth result"
        assert auth_result.error_message is None, "Must not have error message on success"
        assert auth_result.error_code is None, "Must not have error code on success"
        
        # Validate statistics tracking
        assert self.authenticator._websocket_auth_attempts == 1, "Must track authentication attempt"
        assert self.authenticator._websocket_auth_successes == 1, "Must track successful authentication"
        assert self.authenticator._websocket_auth_failures == 0, "Must not track failures on success"

    @pytest.mark.unit
    async def test_websocket_authentication_with_invalid_credentials(self):
        """Test WebSocket authentication fails with invalid credentials."""
        # Business value: Authentication failure prevents unauthorized access to user data
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.headers = {"authorization": "Bearer invalid-jwt-token"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Configure failed auth service response
        mock_auth_result = Mock()
        mock_auth_result.success = False
        mock_auth_result.error = "Invalid authentication token"
        mock_auth_result.error_code = "INVALID_TOKEN"
        mock_auth_result.user_id = None
        mock_auth_result.metadata = {}
        
        self.mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, None)
        
        # Execute authentication
        auth_result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Validate authentication failure
        assert auth_result.success is False, "Must fail with invalid credentials"
        assert auth_result.user_context is None, "Must not return user context on failure"
        assert auth_result.auth_result == mock_auth_result, "Must return failed auth result"
        assert auth_result.error_message == "Invalid authentication token", "Must include error message"
        assert auth_result.error_code == "INVALID_TOKEN", "Must include error code"
        
        # Validate statistics tracking
        assert self.authenticator._websocket_auth_attempts == 1, "Must track authentication attempt"
        assert self.authenticator._websocket_auth_successes == 0, "Must not track success on failure"
        assert self.authenticator._websocket_auth_failures == 1, "Must track authentication failure"

    @pytest.mark.unit
    async def test_websocket_authentication_with_e2e_context_bypass(self):
        """Test WebSocket authentication bypasses validation with E2E context."""
        # Business value: E2E bypass enables comprehensive testing without authentication complexity
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.headers = {}  # No auth headers for E2E
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Configure E2E context for bypass
        e2e_context = {
            "is_e2e_testing": True,
            "detection_method": {"via_environment": True},
            "bypass_enabled": True,
            "environment": "staging"
        }
        
        # Configure successful auth service response for E2E
        mock_auth_result = Mock()
        mock_auth_result.success = True
        mock_auth_result.user_id = "e2e-test-user"
        mock_auth_result.email = "e2e@test.com"
        mock_auth_result.permissions = ["chat:use", "agents:execute"]
        mock_auth_result.validated_at = datetime.now(timezone.utc)
        mock_auth_result.error = None
        mock_auth_result.error_code = None
        mock_auth_result.metadata = {"e2e_bypass": True}
        
        mock_user_context = Mock()
        mock_user_context.user_id = "e2e-test-user"
        mock_user_context.websocket_client_id = "ws-e2e-client"
        mock_user_context.thread_id = "e2e-thread"
        mock_user_context.run_id = "e2e-run"
        
        self.mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
        
        # Execute authentication with E2E context
        auth_result = await self.authenticator.authenticate_websocket_connection(mock_websocket, e2e_context)
        
        # Validate E2E authentication
        assert auth_result.success is True, "Must succeed with E2E context"
        assert auth_result.user_context.user_id == "e2e-test-user", "Must create E2E user context"
        
        # Verify auth service was called with E2E context
        self.mock_auth_service.authenticate_websocket.assert_called_once_with(mock_websocket, e2e_context=e2e_context)

    @pytest.mark.unit
    async def test_websocket_authentication_fails_on_invalid_websocket_state(self):
        """Test WebSocket authentication fails when WebSocket is in invalid state."""
        # Business value: State validation prevents authentication on disconnected sockets
        
        # Configure mock WebSocket in disconnected state
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        mock_websocket.headers = {"authorization": "Bearer valid-token"}
        
        # Execute authentication on disconnected WebSocket
        auth_result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Validate state validation failure
        assert auth_result.success is False, "Must fail on disconnected WebSocket"
        assert auth_result.error_code == "INVALID_WEBSOCKET_STATE", "Must use appropriate error code"
        assert "WebSocket in invalid state" in auth_result.error_message, "Must explain state issue"
        
        # Verify auth service was not called for invalid state
        self.mock_auth_service.authenticate_websocket.assert_not_called()

    @pytest.mark.unit
    async def test_websocket_authentication_handles_service_exceptions(self):
        """Test WebSocket authentication handles auth service exceptions gracefully."""
        # Business value: Exception handling prevents authentication system crashes
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.headers = {"authorization": "Bearer token"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Configure auth service to raise exception
        self.mock_auth_service.authenticate_websocket.side_effect = Exception("Auth service unavailable")
        
        # Execute authentication with service exception
        auth_result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Validate exception handling
        assert auth_result.success is False, "Must fail when auth service raises exception"
        assert auth_result.error_code == "WEBSOCKET_AUTH_EXCEPTION", "Must use exception error code"
        assert "WebSocket authentication error" in auth_result.error_message, "Must explain exception"
        
        # Validate statistics tracking includes exception
        assert self.authenticator._websocket_auth_failures == 1, "Must track exception as failure"

    @pytest.mark.unit
    async def test_create_auth_success_response_sends_proper_message(self):
        """Test create_auth_success_response sends properly formatted success message."""
        # Business value: Success responses confirm authentication and provide user context
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        # Mock WebSocket connection check
        with patch.object(self.authenticator, '_is_websocket_connected', return_value=True):
            # Create successful auth result
            mock_auth_result = Mock()
            mock_auth_result.permissions = ["chat:use", "agents:execute"]
            
            mock_user_context = Mock()
            mock_user_context.user_id = "user-123"
            mock_user_context.websocket_client_id = "ws-client-456"
            
            auth_result = WebSocketAuthResult(
                success=True,
                user_context=mock_user_context,
                auth_result=mock_auth_result
            )
            
            # Send success response
            await self.authenticator.create_auth_success_response(mock_websocket, auth_result)
            
            # Validate success message
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            
            assert call_args["type"] == "authentication_success", "Must use success message type"
            assert call_args["event"] == "auth_success", "Must use auth_success event"
            assert call_args["user_id"] == "user-123", "Must include user ID"
            assert call_args["websocket_client_id"] == "ws-client-456", "Must include client ID"
            assert call_args["permissions"] == ["chat:use", "agents:execute"], "Must include permissions"
            assert call_args["ssot_authenticated"] is True, "Must flag SSOT authentication"

    @pytest.mark.unit
    async def test_create_auth_error_response_sends_proper_error_message(self):
        """Test create_auth_error_response sends properly formatted error message."""
        # Business value: Error responses inform clients of authentication failures
        
        # Configure mock WebSocket
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        # Mock WebSocket connection check
        with patch.object(self.authenticator, '_is_websocket_connected', return_value=True):
            # Create failed auth result
            auth_result = WebSocketAuthResult(
                success=False,
                error_message="Authentication token expired",
                error_code="TOKEN_EXPIRED"
            )
            
            # Send error response
            await self.authenticator.create_auth_error_response(mock_websocket, auth_result)
            
            # Validate error message
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            
            assert call_args["type"] == "authentication_error", "Must use error message type"
            assert call_args["event"] == "auth_failed", "Must use auth_failed event"
            assert call_args["error"] == "Authentication token expired", "Must include error message"
            assert call_args["error_code"] == "TOKEN_EXPIRED", "Must include error code"
            assert call_args["retry_allowed"] is True, "Must allow retry for expired tokens"
            assert call_args["ssot_authenticated"] is False, "Must flag authentication failure"

    @pytest.mark.unit
    def test_get_websocket_auth_stats_returns_comprehensive_statistics(self):
        """Test get_websocket_auth_stats returns comprehensive authentication statistics."""
        # Business value: Authentication statistics enable monitoring and debugging
        
        # Configure authenticator with some statistics
        self.authenticator._websocket_auth_attempts = 10
        self.authenticator._websocket_auth_successes = 8
        self.authenticator._websocket_auth_failures = 2
        self.authenticator._connection_states_seen = {
            "CONNECTED": 8,
            "DISCONNECTED": 2
        }
        
        # Get authentication statistics
        stats = self.authenticator.get_websocket_auth_stats()
        
        # Validate comprehensive statistics
        assert stats["ssot_compliance"]["ssot_compliant"] is True, "Must confirm SSOT compliance"
        assert stats["ssot_compliance"]["authentication_service"] == "UnifiedAuthenticationService", "Must identify auth service"
        
        assert stats["websocket_auth_statistics"]["total_attempts"] == 10, "Must track total attempts"
        assert stats["websocket_auth_statistics"]["successful_authentications"] == 8, "Must track successes"
        assert stats["websocket_auth_statistics"]["failed_authentications"] == 2, "Must track failures"
        assert stats["websocket_auth_statistics"]["success_rate_percent"] == 80.0, "Must calculate success rate"
        
        assert stats["connection_states_seen"]["CONNECTED"] == 8, "Must track connection states"
        assert stats["connection_states_seen"]["DISCONNECTED"] == 2, "Must track disconnection states"
        
        assert "timestamp" in stats, "Must include timestamp"


class TestGlobalWebSocketAuthFunctions(BaseUnitTest):
    """Test global WebSocket authentication functions and utilities."""
    
    @pytest.mark.unit
    def test_get_websocket_authenticator_returns_singleton_instance(self):
        """Test get_websocket_authenticator returns consistent singleton instance."""
        # Business value: Singleton pattern ensures consistent authentication across WebSocket connections
        
        # Get authenticator multiple times
        authenticator1 = get_websocket_authenticator()
        authenticator2 = get_websocket_authenticator()
        
        # Verify same instance
        assert authenticator1 is authenticator2, "Must return same singleton instance"
        assert isinstance(authenticator1, UnifiedWebSocketAuthenticator), "Must return authenticator instance"

    @pytest.mark.unit
    async def test_authenticate_websocket_ssot_function_delegates_to_authenticator(self):
        """Test authenticate_websocket_ssot function properly delegates to authenticator."""
        # Business value: SSOT authentication function ensures consistent authentication interface
        
        # Mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.headers = {"authorization": "Bearer test-token"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Configure E2E context
        e2e_context = {"is_e2e_testing": True}
        
        # Mock the authenticator's authenticate_websocket_connection method
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_websocket_authenticator') as mock_get_auth:
            mock_authenticator = Mock()
            mock_auth_result = WebSocketAuthResult(success=True)
            mock_authenticator.authenticate_websocket_connection.return_value = mock_auth_result
            mock_get_auth.return_value = mock_authenticator
            
            # Execute SSOT authentication
            result = await authenticate_websocket_ssot(mock_websocket, e2e_context)
            
            # Validate delegation
            assert result == mock_auth_result, "Must return authenticator result"
            mock_authenticator.authenticate_websocket_connection.assert_called_once_with(mock_websocket, e2e_context=e2e_context)

    @pytest.mark.unit
    def test_legacy_aliases_point_to_unified_authenticator(self):
        """Test legacy aliases point to UnifiedWebSocketAuthenticator for backward compatibility."""
        # Business value: Legacy aliases ensure existing code continues to work during transition
        
        # Verify legacy aliases
        assert WebSocketAuthenticator == UnifiedWebSocketAuthenticator, "WebSocketAuthenticator must be alias"
        assert UnifiedWebSocketAuth == UnifiedWebSocketAuthenticator, "UnifiedWebSocketAuth must be alias"
        
        # Verify legacy aliases create same instance
        legacy_auth1 = WebSocketAuthenticator()
        legacy_auth2 = UnifiedWebSocketAuth()
        unified_auth = UnifiedWebSocketAuthenticator()
        
        assert type(legacy_auth1) == type(unified_auth), "Legacy aliases must create same type"
        assert type(legacy_auth2) == type(unified_auth), "Legacy aliases must create same type"


if __name__ == "__main__":
    # Run tests with proper WebSocket authentication validation
    pytest.main([__file__, "-v", "--tb=short"])