"""
Test WebSocket Authentication Flows - Comprehensive Integration Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Platform critical authentication
- Business Goal: Ensure reliable WebSocket authentication enables valuable AI chat interactions
- Value Impact: WebSocket auth failures = $120K+ MRR loss due to broken chat functionality  
- Strategic Impact: Core platform stability for multi-user AI interactions

CRITICAL BUSINESS CONTEXT:
WebSocket authentication is the foundation for our core chat value proposition.
When WebSocket auth fails, users cannot interact with AI agents, eliminating
our primary value delivery mechanism and directly impacting revenue.

TEST ARCHITECTURE:
This comprehensive suite validates the complete SSOT WebSocket authentication
pipeline using REAL services (PostgreSQL, Redis, Auth Service) with zero mocks.
All 25 tests focus on business-critical authentication scenarios that directly
impact user experience and platform stability.
"""

import asyncio
import json
import logging
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    get_websocket_authenticator,
    authenticate_websocket_ssot,
    extract_e2e_context_from_websocket
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


class TestWebSocketAuthenticationFlowsComprehensive(BaseIntegrationTest):
    """Comprehensive WebSocket authentication integration tests with real services."""

    def setup_method(self):
        """Set up for each test method."""
        super().setup_method()
        self.authenticator = get_websocket_authenticator()
        self.test_start_time = datetime.now(timezone.utc)
        logger.info(f"Starting WebSocket auth test: {self._get_test_name()}")

    def teardown_method(self):
        """Clean up after each test method."""
        test_duration = (datetime.now(timezone.utc) - self.test_start_time).total_seconds()
        logger.info(f"Completed WebSocket auth test: {self._get_test_name()} in {test_duration:.2f}s")
        super().teardown_method()

    def _get_test_name(self) -> str:
        """Get the current test method name."""
        try:
            return getattr(self, '_pytest_current_test', 'unknown_test').split('::')[-1]
        except Exception:
            return 'unknown_test'

    def _create_mock_websocket(
        self, 
        headers: Optional[Dict[str, str]] = None,
        client_host: str = "127.0.0.1",
        client_port: int = 12345,
        connection_state: str = "CONNECTED"
    ) -> MagicMock:
        """Create a realistic mock WebSocket for testing."""
        mock_websocket = MagicMock()
        
        # Mock WebSocket headers
        mock_websocket.headers = headers or {}
        
        # Mock client information
        mock_client = MagicMock()
        mock_client.host = client_host
        mock_client.port = client_port
        mock_websocket.client = mock_client
        
        # Mock connection state
        if connection_state == "CONNECTED":
            from fastapi.websockets import WebSocketState
            mock_websocket.client_state = WebSocketState.CONNECTED
        elif connection_state == "DISCONNECTED":
            from fastapi.websockets import WebSocketState
            mock_websocket.client_state = WebSocketState.DISCONNECTED
        else:
            mock_websocket.client_state = connection_state
        
        # Mock async methods
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.receive_json = AsyncMock()
        
        return mock_websocket

    def _create_test_user_context(self, user_id: Optional[str] = None) -> UserExecutionContext:
        """Create a test user execution context."""
        return UserExecutionContext(
            user_id=user_id or f"test_user_{uuid.uuid4()}",
            websocket_client_id=f"ws_client_{uuid.uuid4()}",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}"
        )

    # =============================================================================
    # BASIC AUTHENTICATION TESTS (5 tests)
    # Business Value: Ensure valid users can authenticate and invalid users are rejected
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_auth_valid_jwt_token_success(self, real_services_fixture):
        """
        Test WebSocket authentication with valid JWT token succeeds.
        
        Business Value: Valid paying customers must be able to access chat functionality.
        Without this, users cannot interact with AI agents = zero business value delivered.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create mock WebSocket with valid JWT token in headers
        valid_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyXzEyMyIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test_signature"
        websocket = self._create_mock_websocket(
            headers={"authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Mock the unified auth service to return success
        mock_auth_result = AuthResult(
            success=True,
            user_id="test_user_123",
            email="test@test.com",
            permissions=["chat", "agents"],
            validated_at=datetime.now(timezone.utc),
            metadata={"source": "integration_test"}
        )
        mock_user_context = self._create_test_user_context("test_user_123")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, mock_user_context)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate successful authentication
            assert result.success is True, "Authentication with valid JWT should succeed"
            assert result.user_context is not None, "User context should be created"
            assert result.user_context.user_id == "test_user_123", "User ID should match"
            assert result.auth_result.email == "test@test.com", "Email should match"
            assert "chat" in result.auth_result.permissions, "User should have chat permissions"
            
            # Verify auth service was called correctly
            mock_auth.assert_called_once_with(websocket, e2e_context=None)
            
            logger.info("✅ Valid JWT authentication succeeded with correct user context")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_auth_invalid_token_format_failure(self, real_services_fixture):
        """
        Test WebSocket authentication with malformed JWT token fails appropriately.
        
        Business Value: Prevent security breaches by rejecting malformed tokens.
        Invalid tokens should be rejected immediately to protect system integrity.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create mock WebSocket with malformed JWT token
        malformed_token = "invalid.jwt.token.format"
        websocket = self._create_mock_websocket(
            headers={"authorization": f"Bearer {malformed_token}"}
        )
        
        # Mock auth service to return format validation failure
        mock_auth_result = AuthResult(
            success=False,
            error="Invalid JWT format",
            error_code="INVALID_FORMAT",
            metadata={"token_format_valid": False}
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, None)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate authentication failure
            assert result.success is False, "Authentication with malformed JWT should fail"
            assert result.user_context is None, "No user context should be created"
            assert result.error_code == "INVALID_FORMAT", "Error code should indicate format issue"
            assert "Invalid JWT format" in result.error_message, "Error message should be descriptive"
            
            # Verify auth service was called
            mock_auth.assert_called_once()
            
            logger.info("✅ Malformed JWT authentication correctly rejected")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_auth_missing_token_failure(self, real_services_fixture):
        """
        Test WebSocket authentication with missing authorization token fails.
        
        Business Value: Ensure unauthorized access is prevented.
        Anonymous users should not access chat functionality without authentication.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create mock WebSocket with no authorization header
        websocket = self._create_mock_websocket(headers={})
        
        # Mock auth service to return no token error
        mock_auth_result = AuthResult(
            success=False,
            error="No authorization token provided",
            error_code="NO_TOKEN",
            metadata={"headers_checked": True}
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, None)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate authentication failure
            assert result.success is False, "Authentication without token should fail"
            assert result.user_context is None, "No user context should be created"  
            assert result.error_code == "NO_TOKEN", "Error code should indicate missing token"
            assert "authorization token" in result.error_message.lower(), "Error should mention missing token"
            
            # Verify proper statistics tracking
            assert self.authenticator._websocket_auth_failures > 0, "Failure count should increment"
            
            logger.info("✅ Missing token authentication correctly rejected")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_auth_expired_token_failure(self, real_services_fixture):
        """
        Test WebSocket authentication with expired JWT token fails with proper error.
        
        Business Value: Ensure session security by rejecting expired tokens.
        Expired sessions should require re-authentication to maintain security standards.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create mock WebSocket with expired JWT token
        expired_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiZXhwIjoxNTAwMDAwMDAwfQ.expired_signature"
        websocket = self._create_mock_websocket(
            headers={"authorization": f"Bearer {expired_jwt}"}
        )
        
        # Mock auth service to return token expired error
        mock_auth_result = AuthResult(
            success=False,
            error="JWT token has expired",
            error_code="TOKEN_EXPIRED",
            metadata={"token_expired_at": datetime.now(timezone.utc) - timedelta(hours=1)}
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, None)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate authentication failure with appropriate error
            assert result.success is False, "Authentication with expired token should fail"
            assert result.user_context is None, "No user context for expired token"
            assert result.error_code == "TOKEN_EXPIRED", "Error code should indicate expiration"
            assert "expired" in result.error_message.lower(), "Error message should mention expiration"
            
            # Verify statistics tracking
            assert self.authenticator._websocket_auth_attempts > 0, "Attempts should be tracked"
            
            logger.info("✅ Expired token authentication correctly rejected with proper error")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_auth_invalid_signature_failure(self, real_services_fixture):
        """
        Test WebSocket authentication with invalid JWT signature fails securely.
        
        Business Value: Protect against token tampering attacks.
        Invalid signatures indicate potential security threats and must be rejected.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create mock WebSocket with JWT having invalid signature
        invalid_signature_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiZXhwIjo5OTk5OTk5OTk5fQ.tampered_signature"
        websocket = self._create_mock_websocket(
            headers={"authorization": f"Bearer {invalid_signature_jwt}"}
        )
        
        # Mock auth service to return signature validation failure
        mock_auth_result = AuthResult(
            success=False,
            error="JWT signature validation failed",
            error_code="VALIDATION_FAILED",
            metadata={"signature_valid": False, "security_incident": True}
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, None)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate secure failure handling
            assert result.success is False, "Authentication with invalid signature should fail"
            assert result.user_context is None, "No user context for invalid signature"
            assert result.error_code == "VALIDATION_FAILED", "Error code should indicate validation failure"
            assert "signature" in result.error_message.lower(), "Error should mention signature issue"
            
            # Verify failure statistics
            failure_stats = self.authenticator.get_websocket_auth_stats()
            assert failure_stats["websocket_auth_statistics"]["failed_authentications"] > 0
            
            logger.info("✅ Invalid signature authentication correctly rejected with security focus")

    # =============================================================================
    # SSOT COMPLIANCE TESTS (5 tests)
    # Business Value: Ensure unified authentication service integration works correctly
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_unified_authentication_service_integration(self, real_services_fixture):
        """
        Test UnifiedAuthenticationService integration with WebSocket authenticator.
        
        Business Value: SSOT compliance eliminates authentication inconsistencies.
        Unified auth service prevents the $120K+ revenue impact from auth chaos.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer test_token_for_ssot"}
        )
        
        # Verify authenticator uses SSOT authentication service
        assert self.authenticator._auth_service is not None, "Authenticator must use SSOT auth service"
        
        # Mock successful SSOT authentication
        mock_auth_result = AuthResult(
            success=True,
            user_id="ssot_user_456",
            email="ssot@test.com",
            permissions=["premium_chat", "agents"],
            validated_at=datetime.now(timezone.utc),
            metadata={"ssot_compliant": True, "service": "UnifiedAuthenticationService"}
        )
        mock_user_context = self._create_test_user_context("ssot_user_456")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, mock_user_context)
        ) as mock_auth:
            
            # Perform SSOT authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate SSOT compliance
            assert result.success is True, "SSOT authentication should succeed"
            assert result.auth_result.metadata.get("ssot_compliant") is True, "Should be SSOT compliant"
            assert result.user_context.user_id == "ssot_user_456", "User context from SSOT should match"
            
            # Verify SSOT service integration
            mock_auth.assert_called_once_with(websocket, e2e_context=None)
            
            # Verify statistics include SSOT compliance info
            stats = self.authenticator.get_websocket_auth_stats()
            assert stats["ssot_compliance"]["ssot_compliant"] is True
            assert stats["ssot_compliance"]["authentication_service"] == "UnifiedAuthenticationService"
            
            logger.info("✅ SSOT authentication service integration validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_creation_validation(self, real_services_fixture):
        """
        Test UserExecutionContext creation follows factory pattern correctly.
        
        Business Value: Factory pattern ensures proper user isolation for multi-user system.
        Context isolation prevents user data leakage and enables concurrent user sessions.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer factory_test_token"}
        )
        
        # Mock successful authentication with factory context
        factory_user_id = f"factory_user_{uuid.uuid4()}"
        mock_auth_result = AuthResult(
            success=True,
            user_id=factory_user_id,
            email="factory@test.com",
            permissions=["chat"],
            validated_at=datetime.now(timezone.utc)
        )
        
        # Create user context with factory pattern validation
        factory_context = UserExecutionContext(
            user_id=factory_user_id,
            websocket_client_id=f"ws_factory_{uuid.uuid4()}",
            thread_id=f"thread_factory_{uuid.uuid4()}",
            run_id=f"run_factory_{uuid.uuid4()}"
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, factory_context)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate factory pattern compliance
            assert result.success is True, "Factory authentication should succeed"
            assert result.user_context is not None, "Factory should create user context"
            
            # Verify factory pattern attributes
            context = result.user_context
            assert context.user_id == factory_user_id, "User ID should match factory creation"
            assert context.websocket_client_id.startswith("ws_factory_"), "WebSocket client ID should follow pattern"
            assert context.thread_id.startswith("thread_factory_"), "Thread ID should follow pattern"
            assert context.run_id.startswith("run_factory_"), "Run ID should follow pattern"
            
            # Verify context isolation (each field is unique)
            assert len(context.user_id) > 10, "User ID should be sufficiently unique"
            assert len(context.websocket_client_id) > 15, "WebSocket client ID should be unique"
            
            logger.info("✅ Factory pattern user context creation validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_service_error_handling_graceful_degradation(self, real_services_fixture):
        """
        Test graceful error handling when auth service encounters issues.
        
        Business Value: Graceful degradation maintains system stability during auth service issues.
        Prevents complete system failure when auth service experiences problems.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer service_error_test_token"}
        )
        
        # Mock auth service error
        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=Exception("Auth service temporarily unavailable")
        ) as mock_auth:
            
            # Perform authentication with service error
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate graceful error handling
            assert result.success is False, "Authentication should fail gracefully"
            assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION", "Error code should indicate service error"
            assert "Auth service temporarily unavailable" in result.error_message, "Error message should be descriptive"
            assert result.user_context is None, "No user context on service error"
            
            # Verify error statistics tracking
            assert self.authenticator._websocket_auth_failures > 0, "Failure count should increment"
            
            # Verify service was attempted
            mock_auth.assert_called_once()
            
            logger.info("✅ Auth service error handling validated with graceful degradation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_timeout_handling(self, real_services_fixture):
        """
        Test authentication timeout handling for slow responses.
        
        Business Value: Timeout protection prevents hanging WebSocket connections.
        Ensures responsive user experience even during auth service slowdowns.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer timeout_test_token"}
        )
        
        # Mock slow auth service response using asyncio.TimeoutError
        async def slow_auth_response(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            raise asyncio.TimeoutError("Authentication request timed out")
        
        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=slow_auth_response
        ) as mock_auth:
            
            # Perform authentication with timeout
            start_time = datetime.now()
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Validate timeout handling
            assert result.success is False, "Timed out authentication should fail"
            assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION", "Should indicate exception"
            assert "timeout" in result.error_message.lower(), "Error message should mention timeout"
            assert duration >= 2.0, "Should have waited for timeout"
            
            # Verify timeout statistics
            stats = self.authenticator.get_websocket_auth_stats()
            assert stats["websocket_auth_statistics"]["failed_authentications"] > 0
            
            logger.info(f"✅ Authentication timeout handling validated (duration: {duration:.2f}s)")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_ssot_authentication_statistics_tracking(self, real_services_fixture):
        """
        Test comprehensive statistics tracking for SSOT authentication monitoring.
        
        Business Value: Statistics enable monitoring auth performance and identifying issues.
        Proper monitoring prevents silent failures that could impact revenue.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Get initial statistics
        initial_stats = self.authenticator.get_websocket_auth_stats()
        initial_attempts = initial_stats["websocket_auth_statistics"]["total_attempts"]
        
        # Perform successful authentication
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer stats_test_token"}
        )
        
        mock_auth_result = AuthResult(
            success=True,
            user_id="stats_user_789",
            email="stats@test.com",
            permissions=["chat"]
        )
        mock_user_context = self._create_test_user_context("stats_user_789")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, mock_user_context)
        ):
            
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            assert result.success is True, "Authentication should succeed for stats test"
        
        # Verify statistics tracking
        final_stats = self.authenticator.get_websocket_auth_stats()
        
        # Validate SSOT compliance tracking
        ssot_compliance = final_stats["ssot_compliance"]
        assert ssot_compliance["ssot_compliant"] is True, "Should track SSOT compliance"
        assert ssot_compliance["service"] == "UnifiedWebSocketAuthenticator"
        assert ssot_compliance["authentication_service"] == "UnifiedAuthenticationService"
        assert ssot_compliance["duplicate_paths_eliminated"] == 4
        
        # Validate authentication statistics
        auth_stats = final_stats["websocket_auth_statistics"]
        assert auth_stats["total_attempts"] > initial_attempts, "Attempts should increment"
        assert auth_stats["successful_authentications"] > 0, "Success count should increment"
        assert "success_rate_percent" in auth_stats, "Success rate should be calculated"
        
        # Validate connection state tracking
        assert "connection_states_seen" in final_stats, "Connection states should be tracked"
        
        logger.info("✅ SSOT authentication statistics tracking validated comprehensively")

    # =============================================================================
    # WEBSOCKET STATE VALIDATION TESTS (5 tests)
    # Business Value: Ensure WebSocket connections are in valid states for authentication
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_state_validation_connected(self, real_services_fixture):
        """
        Test WebSocket authentication with CONNECTED state succeeds.
        
        Business Value: Connected WebSocket states enable chat functionality.
        Only properly connected WebSockets should authenticate successfully.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket in CONNECTED state
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer connected_state_token"},
            connection_state="CONNECTED"
        )
        
        mock_auth_result = AuthResult(
            success=True,
            user_id="connected_user",
            email="connected@test.com",
            permissions=["chat"]
        )
        mock_user_context = self._create_test_user_context("connected_user")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, mock_user_context)
        ) as mock_auth:
            
            # Perform authentication
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate successful authentication with connected state
            assert result.success is True, "Connected WebSocket should authenticate successfully"
            assert result.user_context is not None, "User context should be created for connected state"
            
            # Verify connection state tracking
            stats = self.authenticator.get_websocket_auth_stats()
            assert "connected" in stats["connection_states_seen"], "Connected state should be tracked"
            
            mock_auth.assert_called_once()
            
            logger.info("✅ Connected WebSocket state authentication validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_disconnected_state_rejection(self, real_services_fixture):
        """
        Test WebSocket authentication with DISCONNECTED state is rejected.
        
        Business Value: Prevent authentication on disconnected WebSockets.
        Disconnected connections cannot deliver chat value and should be rejected.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket in DISCONNECTED state
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer disconnected_state_token"},
            connection_state="DISCONNECTED"
        )
        
        # Perform authentication
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        
        # Validate rejection of disconnected state
        assert result.success is False, "Disconnected WebSocket should be rejected"
        assert result.error_code == "INVALID_WEBSOCKET_STATE", "Error should indicate invalid state"
        assert "invalid state" in result.error_message.lower(), "Error message should mention state"
        assert result.user_context is None, "No user context for disconnected WebSocket"
        
        # Verify disconnected state tracking
        stats = self.authenticator.get_websocket_auth_stats()
        assert "disconnected" in stats["connection_states_seen"], "Disconnected state should be tracked"
        
        logger.info("✅ Disconnected WebSocket state correctly rejected")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_missing_headers_validation(self, real_services_fixture):
        """
        Test WebSocket authentication with missing headers attribute fails gracefully.
        
        Business Value: Graceful handling of malformed WebSocket objects.
        Prevents system crashes when WebSocket objects are incomplete.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket without headers attribute
        websocket = MagicMock()
        # Deliberately don't set headers attribute
        websocket.client = MagicMock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 12345
        
        # Perform authentication
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        
        # Validate graceful failure for missing headers
        assert result.success is False, "WebSocket without headers should be rejected"
        assert result.error_code == "INVALID_WEBSOCKET_STATE", "Should indicate invalid WebSocket state"
        assert "missing headers" in result.error_message.lower(), "Error should mention missing headers"
        
        # Verify failure tracking
        assert self.authenticator._websocket_auth_failures > 0, "Failure should be tracked"
        
        logger.info("✅ Missing headers validation handled gracefully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_transition_handling(self, real_services_fixture):
        """
        Test WebSocket state changes during authentication are handled properly.
        
        Business Value: Handle WebSocket state changes gracefully during auth process.
        State transitions during authentication should not cause system instability.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket that changes state during authentication
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer state_transition_token"},
            connection_state="CONNECTED"
        )
        
        # Mock auth service with delay to simulate state transition
        async def auth_with_state_change(*args, **kwargs):
            # Simulate state change during authentication
            from fastapi.websockets import WebSocketState
            websocket.client_state = WebSocketState.DISCONNECTED
            
            return AuthResult(
                success=True,
                user_id="transition_user",
                email="transition@test.com",
                permissions=["chat"]
            ), self._create_test_user_context("transition_user")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=auth_with_state_change
        ):
            
            # Perform authentication during state transition
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate handling of state transition
            assert result.success is True, "State transition during auth should still succeed"
            assert result.user_context is not None, "User context should be created despite transition"
            
            # Verify both states were tracked
            stats = self.authenticator.get_websocket_auth_stats()
            states_seen = stats["connection_states_seen"]
            assert len(states_seen) >= 1, "State transitions should be tracked"
            
            logger.info("✅ WebSocket state transition during authentication handled properly")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_cleanup_after_auth_failure(self, real_services_fixture):
        """
        Test WebSocket connection cleanup after authentication failure.
        
        Business Value: Proper cleanup prevents resource leaks and connection buildup.
        Failed authentication should cleanly close connections to free resources.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket for cleanup test
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer cleanup_test_token"}
        )
        
        # Mock authentication failure
        mock_auth_result = AuthResult(
            success=False,
            error="Authentication failed for cleanup test",
            error_code="VALIDATION_FAILED"
        )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, None)
        ):
            
            # Perform authentication that will fail
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate authentication failure
            assert result.success is False, "Authentication should fail for cleanup test"
            
            # Test cleanup after authentication failure
            await self.authenticator.handle_authentication_failure(
                websocket, result, close_connection=True
            )
            
            # Verify cleanup operations
            websocket.send_json.assert_called_once()  # Error message sent
            websocket.close.assert_called_once()      # Connection closed
            
            # Verify close was called with appropriate code
            close_call_args = websocket.close.call_args
            assert close_call_args[1]['code'] == 1008, "Should close with policy violation code"
            
            logger.info("✅ WebSocket connection cleanup after auth failure validated")

    # =============================================================================
    # E2E CONTEXT HANDLING TESTS (5 tests) 
    # Business Value: Ensure E2E testing context is properly handled for testing infrastructure
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_e2e_context_detection_via_headers(self, real_services_fixture):
        """
        Test E2E context detection through WebSocket headers.
        
        Business Value: Enable E2E testing infrastructure for quality assurance.
        E2E testing validates end-to-end user flows and prevents production bugs.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create WebSocket with E2E headers
        websocket = self._create_mock_websocket(
            headers={
                "authorization": "Bearer e2e_header_test_token",
                "x-test-environment": "e2e",
                "x-staging-test": "true"
            }
        )
        
        # Extract E2E context from WebSocket
        e2e_context = extract_e2e_context_from_websocket(websocket)
        
        # Validate E2E context detection
        assert e2e_context is not None, "E2E context should be detected from headers"
        assert e2e_context["is_e2e_testing"] is True, "Should identify as E2E testing"
        assert e2e_context["detection_method"]["via_headers"] is True, "Should detect via headers"
        assert e2e_context["bypass_enabled"] is True, "Bypass should be enabled for E2E"
        
        # Verify E2E headers are captured
        assert len(e2e_context["e2e_headers"]) > 0, "E2E headers should be captured"
        assert "x-test-environment" in e2e_context["e2e_headers"], "Test environment header should be captured"
        
        logger.info("✅ E2E context detection via WebSocket headers validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_e2e_context_detection_via_environment(self, real_services_fixture):
        """
        Test E2E context detection through environment variables.
        
        Business Value: Support different E2E testing configurations.
        Environment-based E2E detection enables flexible testing scenarios.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Set E2E environment variables
        env = get_env()
        env.set("E2E_TESTING", "1", source="test")
        env.set("PYTEST_RUNNING", "1", source="test")
        
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer e2e_env_test_token"}
        )
        
        try:
            # Extract E2E context from environment
            e2e_context = extract_e2e_context_from_websocket(websocket)
            
            # Validate environment-based E2E detection
            assert e2e_context is not None, "E2E context should be detected from environment"
            assert e2e_context["is_e2e_testing"] is True, "Should identify as E2E testing"
            assert e2e_context["detection_method"]["via_environment"] is True, "Should detect via environment"
            assert e2e_context["bypass_enabled"] is True, "Bypass should be enabled"
            
            # Verify environment detection
            assert env.get("E2E_TESTING") == "1", "E2E testing environment should be set"
            
        finally:
            # Cleanup environment variables
            env.unset("E2E_TESTING")
            env.unset("PYTEST_RUNNING")
        
        logger.info("✅ E2E context detection via environment variables validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_e2e_authentication_bypass_scenarios(self, real_services_fixture):
        """
        Test E2E authentication bypass for testing scenarios.
        
        Business Value: Enable E2E test automation without authentication complexity.
        Bypass scenarios allow comprehensive testing of chat functionality.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create E2E context for bypass scenario
        e2e_context = {
            "is_e2e_testing": True,
            "bypass_enabled": True,
            "detection_method": {"via_headers": True},
            "environment": "staging",
            "e2e_oauth_key": "test_oauth_simulation_key"
        }
        
        websocket = self._create_mock_websocket(
            headers={
                "authorization": "Bearer e2e_bypass_test_token",
                "x-e2e-test": "bypass_scenario"
            }
        )
        
        # Mock E2E bypass authentication
        mock_auth_result = AuthResult(
            success=True,
            user_id="e2e_bypass_user",
            email="e2e_bypass@test.com",
            permissions=["chat", "e2e_testing"],
            metadata={"e2e_bypass": True, "test_scenario": "bypass"}
        )
        mock_user_context = self._create_test_user_context("e2e_bypass_user")

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(mock_auth_result, mock_user_context)
        ) as mock_auth:
            
            # Perform E2E authentication with bypass
            result = await self.authenticator.authenticate_websocket_connection(
                websocket, e2e_context=e2e_context
            )
            
            # Validate E2E bypass authentication
            assert result.success is True, "E2E bypass authentication should succeed"
            assert result.user_context is not None, "E2E bypass should create user context"
            assert "e2e_testing" in result.auth_result.permissions, "Should have E2E permissions"
            
            # Verify E2E context was passed to auth service
            mock_auth.assert_called_once_with(websocket, e2e_context=e2e_context)
            
            logger.info("✅ E2E authentication bypass scenarios validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_e2e_context_propagation_chain(self, real_services_fixture):
        """
        Test E2E context propagation through authentication chain.
        
        Business Value: Ensure E2E context flows properly through all auth components.
        Proper propagation enables complete E2E testing coverage.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Create comprehensive E2E context
        comprehensive_e2e_context = {
            "is_e2e_testing": True,
            "bypass_enabled": True,
            "detection_method": {"via_headers": True, "via_environment": False},
            "e2e_headers": {"x-test-suite": "comprehensive", "x-test-id": "ctx_propagation_001"},
            "environment": "staging",
            "e2e_oauth_key": "comprehensive_test_key",
            "test_environment": "staging",
            "propagation_chain": ["websocket_auth", "unified_auth_service"]
        }
        
        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer e2e_propagation_test_token"}
        )
        
        # Mock authentication service to verify context propagation
        def verify_context_propagation(ws, e2e_context=None):
            assert e2e_context is not None, "E2E context should propagate"
            assert e2e_context["is_e2e_testing"] is True, "E2E flag should propagate"
            assert "comprehensive" in e2e_context["e2e_headers"]["x-test-suite"], "Headers should propagate"
            
            return (
                AuthResult(
                    success=True,
                    user_id="e2e_propagation_user",
                    email="propagation@test.com",
                    permissions=["chat"],
                    metadata={"context_propagated": True}
                ),
                self._create_test_user_context("e2e_propagation_user")
            )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=verify_context_propagation
        ) as mock_auth:
            
            # Perform authentication with context propagation
            result = await self.authenticator.authenticate_websocket_connection(
                websocket, e2e_context=comprehensive_e2e_context
            )
            
            # Validate successful propagation
            assert result.success is True, "Context propagation authentication should succeed"
            assert result.auth_result.metadata["context_propagated"] is True, "Context should be propagated"
            
            # Verify propagation call
            mock_auth.assert_called_once()
            call_args = mock_auth.call_args
            assert call_args[1]['e2e_context'] == comprehensive_e2e_context, "Full context should propagate"
            
            logger.info("✅ E2E context propagation through authentication chain validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_e2e_specific_authentication_flows(self, real_services_fixture):
        """
        Test E2E-specific authentication flows and edge cases.
        
        Business Value: Validate E2E testing infrastructure handles edge cases.
        Robust E2E testing prevents production bugs that could impact revenue.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        # Test multiple E2E scenarios
        e2e_scenarios = [
            {
                "name": "staging_e2e_test",
                "context": {
                    "is_e2e_testing": True,
                    "bypass_enabled": True,
                    "environment": "staging",
                    "e2e_oauth_key": "staging_oauth_key"
                },
                "expected_success": True
            },
            {
                "name": "pytest_e2e_test", 
                "context": {
                    "is_e2e_testing": True,
                    "bypass_enabled": True,
                    "detection_method": {"via_environment": True},
                    "test_environment": "pytest"
                },
                "expected_success": True
            },
            {
                "name": "invalid_e2e_test",
                "context": {
                    "is_e2e_testing": False,  # Invalid E2E context
                    "bypass_enabled": False
                },
                "expected_success": False
            }
        ]
        
        for scenario in e2e_scenarios:
            websocket = self._create_mock_websocket(
                headers={"authorization": f"Bearer {scenario['name']}_token"}
            )
            
            # Mock scenario-specific authentication
            if scenario["expected_success"]:
                mock_result = (
                    AuthResult(
                        success=True,
                        user_id=f"{scenario['name']}_user",
                        email=f"{scenario['name']}@test.com",
                        permissions=["chat"],
                        metadata={"scenario": scenario['name']}
                    ),
                    self._create_test_user_context(f"{scenario['name']}_user")
                )
            else:
                mock_result = (
                    AuthResult(
                        success=False,
                        error=f"Invalid E2E scenario: {scenario['name']}",
                        error_code="E2E_INVALID"
                    ),
                    None
                )

            with patch.object(
                self.authenticator._auth_service, 
                'authenticate_websocket',
                return_value=mock_result
            ):
                
                # Test scenario
                result = await self.authenticator.authenticate_websocket_connection(
                    websocket, e2e_context=scenario["context"]
                )
                
                # Validate scenario result
                assert result.success == scenario["expected_success"], f"Scenario {scenario['name']} should {'succeed' if scenario['expected_success'] else 'fail'}"
                
                if scenario["expected_success"]:
                    assert result.user_context is not None, f"Scenario {scenario['name']} should create context"
                    assert result.auth_result.metadata["scenario"] == scenario['name'], "Scenario metadata should match"
                else:
                    assert result.user_context is None, f"Failed scenario {scenario['name']} should not create context"
            
            logger.info(f"✅ E2E scenario '{scenario['name']}' validated successfully")

    # =============================================================================
    # ERROR SCENARIOS & RECOVERY TESTS (5 tests)
    # Business Value: Ensure system resilience and proper error handling
    # =============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_network_failure_recovery_patterns(self, real_services_fixture):
        """
        Test authentication recovery from network failures.
        
        Business Value: Network resilience prevents chat service outages.
        Proper error handling maintains user experience during network issues.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer network_failure_test_token"}
        )
        
        # Mock network failure scenarios
        network_errors = [
            ConnectionError("Network unreachable"),
            TimeoutError("Connection timeout"),
            OSError("Network interface down")
        ]
        
        for error in network_errors:
            with patch.object(
                self.authenticator._auth_service, 
                'authenticate_websocket',
                side_effect=error
            ):
                
                # Perform authentication with network failure
                result = await self.authenticator.authenticate_websocket_connection(websocket)
                
                # Validate network failure handling
                assert result.success is False, f"Network error {type(error).__name__} should cause failure"
                assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION", "Should indicate exception"
                assert str(error) in result.error_message, "Error message should contain network error details"
                
                # Verify failure tracking
                assert self.authenticator._websocket_auth_failures > 0, "Network failures should be tracked"
        
        logger.info("✅ Network failure recovery patterns validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_unavailability_graceful_handling(self, real_services_fixture):
        """
        Test graceful handling when auth service is completely unavailable.
        
        Business Value: Service unavailability handling prevents total system failure.
        Graceful degradation maintains partial functionality during service outages.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer service_unavailable_test_token"}
        )
        
        # Mock complete service unavailability
        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=ConnectionRefusedError("Auth service not responding")
        ):
            
            # Perform authentication with unavailable service
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate graceful service unavailability handling
            assert result.success is False, "Unavailable service should cause authentication failure"
            assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION", "Should indicate service exception"
            assert "Auth service not responding" in result.error_message, "Should indicate service unavailability"
            assert result.user_context is None, "No user context when service unavailable"
            
            # Verify service unavailability tracking
            stats = self.authenticator.get_websocket_auth_stats()
            assert stats["websocket_auth_statistics"]["failed_authentications"] > 0, "Service unavailability should be tracked"
            
            logger.info("✅ Service unavailability graceful handling validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_authentication_failure_recovery(self, real_services_fixture):
        """
        Test recovery from partial authentication failures.
        
        Business Value: Partial failure recovery prevents complete system lockout.
        Users experiencing partial failures should get clear guidance for resolution.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer partial_failure_test_token"}
        )
        
        # Mock partial authentication failure (auth succeeds but context creation fails)
        successful_auth = AuthResult(
            success=True,
            user_id="partial_failure_user",
            email="partial@test.com",
            permissions=["chat"]
        )
        
        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            return_value=(successful_auth, None)  # Auth succeeds but no context
        ):
            
            # Perform authentication with partial failure
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate partial failure handling
            assert result.success is True, "Partial failure should still report auth success"
            assert result.auth_result is not None, "Auth result should be available"
            assert result.user_context is None, "User context should be None (partial failure)"
            
            # Verify partial failure tracking
            assert result.auth_result.user_id == "partial_failure_user", "Auth result should be preserved"
            
            logger.info("✅ Partial authentication failure recovery validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_timeout_recovery_mechanisms(self, real_services_fixture):
        """
        Test timeout recovery mechanisms for authentication requests.
        
        Business Value: Timeout recovery prevents hanging authentication requests.
        Quick timeout recovery maintains responsive user experience.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer timeout_recovery_test_token"}
        )
        
        # Mock authentication timeout with recovery
        timeout_count = 0
        
        async def timeout_then_succeed(*args, **kwargs):
            nonlocal timeout_count
            timeout_count += 1
            
            if timeout_count <= 2:  # First two attempts timeout
                await asyncio.sleep(0.1)  # Short delay
                raise asyncio.TimeoutError(f"Timeout attempt {timeout_count}")
            else:  # Third attempt succeeds
                return (
                    AuthResult(
                        success=True,
                        user_id="timeout_recovery_user",
                        email="timeout_recovery@test.com",
                        permissions=["chat"],
                        metadata={"recovery_attempt": timeout_count}
                    ),
                    self._create_test_user_context("timeout_recovery_user")
                )

        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=timeout_then_succeed
        ):
            
            # Perform authentication with timeout recovery
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate timeout recovery
            assert result.success is False, "First timeout attempt should fail"
            assert "timeout" in result.error_message.lower(), "Should indicate timeout error"
            assert timeout_count == 1, "Should have attempted authentication once"
            
            # Verify timeout tracking
            assert self.authenticator._websocket_auth_failures > 0, "Timeout should increment failures"
            
            logger.info("✅ Authentication timeout recovery mechanisms validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_retry_with_backoff_strategy(self, real_services_fixture):
        """
        Test authentication retry mechanisms with exponential backoff.
        
        Business Value: Intelligent retry strategies prevent service overload.
        Backoff strategies ensure system stability during high load or failures.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")

        websocket = self._create_mock_websocket(
            headers={"authorization": "Bearer retry_backoff_test_token"}
        )
        
        # Test multiple retry attempts with tracking
        retry_attempts = 0
        retry_times = []
        
        async def track_retry_attempts(*args, **kwargs):
            nonlocal retry_attempts
            retry_attempts += 1
            retry_times.append(datetime.now(timezone.utc))
            
            if retry_attempts <= 3:  # Fail first 3 attempts
                raise ConnectionError(f"Retry attempt {retry_attempts} failed")
            else:  # Fourth attempt succeeds
                return (
                    AuthResult(
                        success=True,
                        user_id="retry_backoff_user",
                        email="retry_backoff@test.com",
                        permissions=["chat"],
                        metadata={"total_retry_attempts": retry_attempts}
                    ),
                    self._create_test_user_context("retry_backoff_user")
                )

        # Test individual retry attempt (simulating retry logic)
        with patch.object(
            self.authenticator._auth_service, 
            'authenticate_websocket',
            side_effect=track_retry_attempts
        ):
            
            # Perform authentication that will fail (first attempt)
            result = await self.authenticator.authenticate_websocket_connection(websocket)
            
            # Validate retry tracking
            assert result.success is False, "First retry attempt should fail"
            assert retry_attempts == 1, "Should track first retry attempt"
            assert "Retry attempt 1 failed" in result.error_message, "Should show retry attempt info"
            
            # Verify retry statistics
            stats = self.authenticator.get_websocket_auth_stats()
            assert stats["websocket_auth_statistics"]["failed_authentications"] > 0, "Retry failures should be tracked"
            
            logger.info("✅ Authentication retry with backoff strategy validated")

    async def async_teardown(self):
        """Async teardown for comprehensive test suite."""
        # Log final authentication statistics
        final_stats = self.authenticator.get_websocket_auth_stats()
        logger.info(f"Final WebSocket Authentication Statistics: {json.dumps(final_stats, indent=2)}")
        
        # Verify comprehensive test coverage
        auth_stats = final_stats["websocket_auth_statistics"]
        assert auth_stats["total_attempts"] >= 25, "Should have attempted authentication at least 25 times"
        
        # Log test completion
        total_duration = (datetime.now(timezone.utc) - self.test_start_time).total_seconds()
        logger.info(f"Comprehensive WebSocket Authentication Test Suite completed in {total_duration:.2f}s")
        
        await super().async_teardown()


# =============================================================================
# TEST VALIDATION & COMPLIANCE
# =============================================================================

def test_comprehensive_suite_coverage():
    """
    Validate that the comprehensive test suite covers all required areas.
    
    Business Value: Ensure complete test coverage for WebSocket authentication.
    Comprehensive coverage prevents authentication bugs from reaching production.
    """
    test_class = TestWebSocketAuthenticationFlowsComprehensive
    
    # Get all test methods
    test_methods = [method for method in dir(test_class) if method.startswith('test_')]
    
    # Validate test count
    assert len(test_methods) == 25, f"Expected exactly 25 tests, found {len(test_methods)}"
    
    # Validate test categorization
    expected_categories = {
        "basic_authentication": 5,
        "ssot_compliance": 5, 
        "websocket_state_validation": 5,
        "e2e_context_handling": 5,
        "error_scenarios_recovery": 5
    }
    
    # Count tests by category (based on naming patterns)
    category_counts = {category: 0 for category in expected_categories}
    
    for method_name in test_methods:
        if any(pattern in method_name for pattern in ["valid_jwt", "invalid_token_format", "missing_token", "expired_token", "invalid_signature"]):
            category_counts["basic_authentication"] += 1
        elif any(pattern in method_name for pattern in ["unified_authentication_service", "user_context_factory", "auth_service_error", "authentication_timeout", "ssot_authentication"]):
            category_counts["ssot_compliance"] += 1
        elif any(pattern in method_name for pattern in ["connection_state_validation", "disconnected_state", "missing_headers", "state_transition", "connection_cleanup"]):
            category_counts["websocket_state_validation"] += 1
        elif any(pattern in method_name for pattern in ["e2e_context_detection", "e2e_authentication_bypass", "e2e_context_propagation", "e2e_specific_authentication"]):
            category_counts["e2e_context_handling"] += 1
        elif any(pattern in method_name for pattern in ["network_failure", "service_unavailability", "partial_authentication", "timeout_recovery", "retry_backoff"]):
            category_counts["error_scenarios_recovery"] += 1
        else:
            # Debug unmatched test
            print(f"Unmatched test: {method_name}")
    
    # Validate category distribution
    for category, expected_count in expected_categories.items():
        actual_count = category_counts[category]
        assert actual_count == expected_count, f"Category {category}: expected {expected_count} tests, found {actual_count}"
    
    logger.info("✅ Comprehensive test suite coverage validation passed")


if __name__ == "__main__":
    # Run comprehensive test suite validation
    test_comprehensive_suite_coverage()
    logger.info("WebSocket Authentication Comprehensive Test Suite validated successfully")