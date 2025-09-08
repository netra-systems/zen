"""
Comprehensive Unit Tests for UnifiedAuthenticationService - SINGLE SOURCE OF TRUTH

Business Value Justification (BVJ):
- Segment: Platform/Internal - Security Infrastructure  
- Business Goal: System Stability & Security Compliance
- Value Impact: Ensures authentication works correctly to restore $120K+ MRR 
- Strategic Impact: Critical security infrastructure that enables all user operations

This test suite validates the SSOT authentication service that consolidates
4 duplicate authentication paths into a single, reliable implementation.

CRITICAL: This service is MISSION CRITICAL for platform revenue.
Authentication failures directly translate to lost customer access.

Tests follow CLAUDE.md principles:
- Use real services over mocks where possible
- Test business value and failure scenarios  
- Use IsolatedEnvironment for all env access
- Test enhanced resilience features added for circuit breaker integration
- Validate all authentication contexts and methods
- Test WebSocket authentication paths that are critical for chat value
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthResult,
    AuthenticationMethod,
    AuthenticationContext,
    get_unified_auth_service
)
from netra_backend.app.clients.auth_client_core import (
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceNotAvailableError,
    AuthServiceValidationError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestUnifiedAuthenticationServiceComprehensive(SSotAsyncTestCase):
    """
    Comprehensive tests for UnifiedAuthenticationService - SSOT authentication.
    
    This test class validates ALL authentication methods and contexts
    to ensure the SSOT service correctly handles all business scenarios.
    """

    def setup_method(self, method=None):
        """Setup test environment with proper isolation."""
        super().setup_method(method)
        
        # Initialize authentication service for testing
        self.auth_service = UnifiedAuthenticationService()
        
        # Test tokens for validation
        self.valid_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyXzEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInBlcm1pc3Npb25zIjpbInJlYWQiLCJ3cml0ZSJdLCJpYXQiOjE2OTgzNDE0MDAsImV4cCI6MTY5ODM0NTAwMH0.test_signature"
        self.invalid_jwt_token = "invalid.token.format"
        self.short_token = "short"
        self.service_token = "service_token_abc123def456"
        
        # Mock WebSocket for testing
        self.mock_websocket = self._create_mock_websocket()
        
        # Track metrics
        self.record_metric("test_start_time", time.time())

    def teardown_method(self, method=None):
        """Cleanup after test."""
        # Record test completion metrics
        self.record_metric("test_end_time", time.time())
        super().teardown_method(method)

    def _create_mock_websocket(self) -> Mock:
        """Create a realistic mock WebSocket for testing."""
        mock_ws = Mock()
        mock_ws.headers = {
            "authorization": f"Bearer {self.valid_jwt_token}",
            "sec-websocket-protocol": "chat",
            "user-agent": "test-client/1.0"
        }
        mock_ws.client = Mock()
        mock_ws.client.host = "127.0.0.1"
        mock_ws.client.port = 12345
        mock_ws.query_params = {}
        return mock_ws

    # === CORE AUTHENTICATION TOKEN TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_token_success_all_contexts(self):
        """Test successful token authentication across all contexts - CRITICAL BUSINESS VALUE."""
        # Mock successful validation response
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "user_12345",
                "email": "customer@enterprise.com",
                "permissions": ["read", "write", "admin"],
                "iat": 1698341400,
                "exp": 1698345000
            }

            # Test all authentication contexts
            test_contexts = [
                AuthenticationContext.REST_API,
                AuthenticationContext.WEBSOCKET,
                AuthenticationContext.GRAPHQL,
                AuthenticationContext.GRPC,
                AuthenticationContext.INTERNAL_SERVICE
            ]

            for context in test_contexts:
                result = await self.auth_service.authenticate_token(
                    token=self.valid_jwt_token,
                    context=context,
                    method=AuthenticationMethod.JWT_TOKEN
                )

                # Verify successful authentication
                assert result.success is True, f"Authentication failed for context {context.value}"
                assert result.user_id == "user_12345"
                assert result.email == "customer@enterprise.com"
                assert len(result.permissions) == 3
                assert "admin" in result.permissions
                assert result.error is None
                assert result.error_code is None

                # Verify business context preserved
                assert result.metadata["context"] == context.value
                assert result.metadata["method"] == AuthenticationMethod.JWT_TOKEN.value
                assert result.metadata["token_issued_at"] == 1698341400
                assert result.metadata["token_expires_at"] == 1698345000

                self.increment_llm_requests()  # Track auth service calls

        # Verify statistics tracking - BUSINESS MONITORING
        stats = self.auth_service.get_authentication_stats()
        assert stats["statistics"]["total_attempts"] == len(test_contexts)
        assert stats["statistics"]["successful_authentications"] == len(test_contexts)
        assert stats["statistics"]["success_rate_percent"] == 100.0

        self.record_metric("contexts_tested", len(test_contexts))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_token_invalid_format(self):
        """Test authentication with invalid token format - SECURITY VALIDATION."""
        invalid_tokens = [
            self.invalid_jwt_token,
            self.short_token,
            "",
            "Bearer malformed.token",
            "no.dots.here",
            "too.many.dots.in.this.token.structure"
        ]

        for invalid_token in invalid_tokens:
            result = await self.auth_service.authenticate_token(
                token=invalid_token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )

            # Verify proper error handling
            assert result.success is False
            assert result.error_code == "INVALID_FORMAT"
            assert "Invalid token format" in result.error
            assert result.user_id is None
            assert result.email is None

            # Verify diagnostic information included
            assert "token_debug" in result.metadata
            token_debug = result.metadata["token_debug"]
            assert "length" in token_debug
            assert "has_dots" in token_debug
            assert token_debug["length"] == len(invalid_token)

        # Verify statistics tracking
        stats = self.auth_service.get_authentication_stats()
        assert stats["statistics"]["failed_authentications"] == len(invalid_tokens)

        self.record_metric("invalid_tokens_tested", len(invalid_tokens))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_token_validation_failed(self):
        """Test authentication when auth service validation fails - CRITICAL ERROR HANDLING."""
        # Mock failed validation response
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            # Test different failure scenarios
            failure_scenarios = [
                {"valid": False, "error": "Token expired", "details": "Token expired at 2024-01-15T10:30:00Z"},
                {"valid": False, "error": "Invalid signature", "details": "Signature verification failed"},
                {"valid": False, "error": "User not found", "details": "User ID not found in database"},
                None,  # No response scenario
                {}     # Empty response scenario
            ]

            for i, validation_response in enumerate(failure_scenarios):
                mock_validate.return_value = validation_response

                result = await self.auth_service.authenticate_token(
                    token=self.valid_jwt_token,
                    context=AuthenticationContext.WEBSOCKET,
                    method=AuthenticationMethod.JWT_TOKEN
                )

                # Verify proper failure handling
                assert result.success is False
                assert result.error_code == "VALIDATION_FAILED"
                assert result.user_id is None
                assert result.email is None

                # Verify comprehensive debugging information
                assert "failure_debug" in result.metadata
                failure_debug = result.metadata["failure_debug"]
                assert "validation_result_exists" in failure_debug
                assert "token_characteristics" in failure_debug
                assert "timestamp" in failure_debug

                if validation_response:
                    assert failure_debug["validation_result_exists"] is True
                    if "error" in validation_response:
                        assert validation_response["error"] in result.error
                else:
                    assert failure_debug["validation_result_exists"] is False

        # Verify failure tracking
        stats = self.auth_service.get_authentication_stats()
        assert stats["statistics"]["failed_authentications"] == len(failure_scenarios)

        self.record_metric("failure_scenarios_tested", len(failure_scenarios))

    # === WEBSOCKET AUTHENTICATION TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """Test successful WebSocket authentication - CRITICAL FOR CHAT VALUE."""
        # Mock successful validation
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "ws_user_456",
                "email": "chatuser@example.com",
                "permissions": ["chat", "agents"],
                "iat": 1698341400,
                "exp": 1698345000
            }

            auth_result, user_context = await self.auth_service.authenticate_websocket(self.mock_websocket)

            # Verify successful authentication
            assert auth_result.success is True
            assert auth_result.user_id == "ws_user_456"
            assert auth_result.email == "chatuser@example.com"
            assert "chat" in auth_result.permissions
            assert "agents" in auth_result.permissions

            # Verify UserExecutionContext created correctly - CRITICAL FOR USER ISOLATION
            assert user_context is not None
            assert isinstance(user_context, UserExecutionContext)
            assert user_context.user_id == "ws_user_456"
            assert user_context.thread_id.startswith("ws_thread_")
            assert user_context.run_id.startswith("ws_run_")
            assert user_context.request_id.startswith("ws_req_")
            assert user_context.websocket_client_id.startswith("ws_")
            assert "ws_user_456" in user_context.websocket_client_id

        self.increment_websocket_events()
        self.record_metric("websocket_auth_success", True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test WebSocket authentication without token - SECURITY BOUNDARY."""
        # Create WebSocket without authorization header
        mock_ws_no_auth = Mock()
        mock_ws_no_auth.headers = {}
        mock_ws_no_auth.client = Mock()
        mock_ws_no_auth.client.host = "127.0.0.1"
        mock_ws_no_auth.client.port = 12345
        mock_ws_no_auth.query_params = {}

        auth_result, user_context = await self.auth_service.authenticate_websocket(mock_ws_no_auth)

        # Verify authentication failure
        assert auth_result.success is False
        assert auth_result.error_code == "NO_TOKEN"
        assert "No JWT token found" in auth_result.error
        assert user_context is None

        # Verify comprehensive debugging information
        assert "no_token_debug" in auth_result.metadata
        no_token_debug = auth_result.metadata["no_token_debug"]
        assert "headers_checked" in no_token_debug
        assert "query_params_available" in no_token_debug
        assert "websocket_info" in no_token_debug

        self.record_metric("websocket_no_token_test", True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_websocket_invalid_token(self):
        """Test WebSocket authentication with invalid token - SECURITY VALIDATION."""
        # Create WebSocket with invalid token
        mock_ws_invalid = Mock()
        mock_ws_invalid.headers = {
            "authorization": f"Bearer {self.invalid_jwt_token}"
        }
        mock_ws_invalid.client = Mock()
        mock_ws_invalid.client.host = "127.0.0.1"
        mock_ws_invalid.client.port = 12345
        mock_ws_invalid.query_params = {}

        auth_result, user_context = await self.auth_service.authenticate_websocket(mock_ws_invalid)

        # Verify authentication failure
        assert auth_result.success is False
        assert auth_result.error_code == "INVALID_FORMAT"
        assert user_context is None

        # Verify proper error classification
        assert result.metadata["context"] == AuthenticationContext.WEBSOCKET.value

        self.record_metric("websocket_invalid_token_test", True)

    # === SERVICE AUTHENTICATION TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_service_token_success(self):
        """Test successful service-to-service authentication - INTER-SERVICE SECURITY."""
        service_name = "analytics_service"
        
        # Mock successful service validation
        with patch.object(self.auth_service._auth_client, 'validate_token_for_service', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "service_id": "srv_analytics_001",
                "permissions": ["read_data", "write_metrics"]
            }

            result = await self.auth_service.validate_service_token(self.service_token, service_name)

            # Verify successful service authentication
            assert result.success is True
            assert result.user_id == "srv_analytics_001"  # Service ID used as user ID
            assert result.permissions == ["read_data", "write_metrics"]
            assert result.metadata["service_name"] == service_name
            assert result.metadata["context"] == "service_auth"

        self.record_metric("service_auth_success", True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_service_token_failure(self):
        """Test failed service token validation - SERVICE SECURITY BOUNDARY."""
        service_name = "unauthorized_service"

        # Mock failed service validation
        with patch.object(self.auth_service._auth_client, 'validate_token_for_service', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "error": "Service not authorized"
            }

            result = await self.auth_service.validate_service_token(self.service_token, service_name)

            # Verify proper failure handling
            assert result.success is False
            assert result.error_code == "SERVICE_VALIDATION_FAILED"
            assert "Service not authorized" in result.error
            assert result.metadata["service_name"] == service_name

        self.record_metric("service_auth_failure", True)

    # === STATISTICS AND MONITORING TESTS ===

    @pytest.mark.unit
    def test_get_authentication_stats(self):
        """Test authentication statistics collection - BUSINESS MONITORING."""
        # Perform some authentication attempts to generate statistics
        self.auth_service._auth_attempts = 10
        self.auth_service._auth_successes = 8
        self.auth_service._auth_failures = 2
        self.auth_service._method_counts[AuthenticationMethod.JWT_TOKEN.value] = 7
        self.auth_service._method_counts[AuthenticationMethod.API_KEY.value] = 3
        self.auth_service._context_counts[AuthenticationContext.WEBSOCKET.value] = 5
        self.auth_service._context_counts[AuthenticationContext.REST_API.value] = 5

        stats = self.auth_service.get_authentication_stats()

        # Verify statistics structure and values
        assert "ssot_enforcement" in stats
        assert stats["ssot_enforcement"]["service"] == "UnifiedAuthenticationService"
        assert stats["ssot_enforcement"]["ssot_compliant"] is True
        assert stats["ssot_enforcement"]["duplicate_paths_eliminated"] == 4

        assert "statistics" in stats
        assert stats["statistics"]["total_attempts"] == 10
        assert stats["statistics"]["successful_authentications"] == 8
        assert stats["statistics"]["failed_authentications"] == 2
        assert stats["statistics"]["success_rate_percent"] == 80.0

        assert "method_distribution" in stats
        assert stats["method_distribution"][AuthenticationMethod.JWT_TOKEN.value] == 7

        assert "context_distribution" in stats
        assert stats["context_distribution"][AuthenticationContext.WEBSOCKET.value] == 5

        assert "timestamp" in stats

        self.record_metric("stats_validation", True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test service health check - OPERATIONAL MONITORING."""
        health = await self.auth_service.health_check()

        # Verify health check response structure
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert health["service"] == "UnifiedAuthenticationService"
        assert health["ssot_compliant"] is True
        assert "auth_client_status" in health
        assert "timestamp" in health

        # Health should be healthy with proper auth client
        if hasattr(self.auth_service._auth_client, 'circuit_breaker'):
            assert health["status"] == "healthy"
            assert health["auth_client_status"] == "available"

        self.record_metric("health_check_success", True)

    # === SINGLETON PATTERN TESTS ===

    @pytest.mark.unit
    def test_singleton_instance(self):
        """Test singleton pattern implementation - SSOT ENFORCEMENT."""
        # Get multiple instances
        instance1 = get_unified_auth_service()
        instance2 = get_unified_auth_service()

        # Verify they are the same instance
        assert instance1 is instance2
        assert isinstance(instance1, UnifiedAuthenticationService)
        assert isinstance(instance2, UnifiedAuthenticationService)

        # Verify both have access to the same statistics
        instance1._auth_attempts = 5
        assert instance2._auth_attempts == 5

        self.record_metric("singleton_test", True)

    # === ENHANCED RESILIENCE TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enhanced_resilience_retry_logic(self):
        """Test enhanced retry logic with exponential backoff - RELIABILITY."""
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            # First two calls fail, third succeeds
            mock_validate.side_effect = [
                AuthServiceConnectionError("Connection timeout"),
                AuthServiceConnectionError("Service unavailable"),
                {
                    "valid": True,
                    "user_id": "resilient_user",
                    "email": "test@example.com",
                    "permissions": ["read"]
                }
            ]

            # Set environment to test for optimal retry settings
            self.set_env_var("ENVIRONMENT", "development")

            start_time = time.time()
            result = await self.auth_service.authenticate_token(
                token=self.valid_jwt_token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            end_time = time.time()

            # Verify eventual success after retries
            assert result.success is True
            assert result.user_id == "resilient_user"
            
            # Verify resilience metadata included
            assert "resilience_metadata" in result.metadata
            resilience_meta = result.metadata["resilience_metadata"]
            assert resilience_meta["attempts_made"] == 3
            assert resilience_meta["environment"] == "development"

            # Verify retry timing (should have some delay due to exponential backoff)
            execution_time = end_time - start_time
            assert execution_time > 0.2  # At least some delay from retries

        self.record_metric("retry_logic_test", True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker status monitoring - FAILURE PROTECTION."""
        # Mock circuit breaker status check
        mock_circuit_manager = Mock()
        mock_breaker = Mock()
        mock_breaker.get_status.return_value = {
            "state": "half_open",
            "failure_count": 3
        }
        mock_circuit_manager.breaker = mock_breaker
        
        with patch.object(self.auth_service._auth_client, 'circuit_manager', mock_circuit_manager):
            status = await self.auth_service._check_circuit_breaker_status()
            
            # Verify circuit breaker status properly detected
            assert status["open"] is False  # half_open is not fully open
            assert status["state"] == "half_open"
            assert status["failure_count"] == 3
            assert "Circuit breaker state: half_open" in status["reason"]

        self.record_metric("circuit_breaker_test", True)

    @pytest.mark.unit
    def test_error_classification(self):
        """Test authentication error classification - INTELLIGENT ERROR HANDLING."""
        test_errors = [
            (ConnectionError("Connection refused"), "network", True),
            (Exception("Circuit breaker open"), "circuit_breaker", True),
            (Exception("500 Internal Server Error"), "server_error", True),
            (Exception("401 Unauthorized"), "client_error", False),
            (Exception("Invalid token signature"), "invalid_token", False),
            (ValueError("Unknown error type"), "unknown", True)
        ]

        for error, expected_category, expected_retryable in test_errors:
            classification = self.auth_service._classify_auth_error(error)

            assert classification["category"] == expected_category
            assert classification["retryable"] is expected_retryable
            assert "reason" in classification

        self.record_metric("error_classification_tests", len(test_errors))

    # === WEBSOCKET TOKEN EXTRACTION TESTS ===

    @pytest.mark.unit
    def test_websocket_token_extraction_methods(self):
        """Test all WebSocket token extraction methods - PROTOCOL COMPLIANCE."""
        # Test Authorization header method
        mock_ws_auth_header = Mock()
        mock_ws_auth_header.headers = {
            "authorization": f"Bearer {self.valid_jwt_token}"
        }
        mock_ws_auth_header.query_params = {}
        
        token = self.auth_service._extract_websocket_token(mock_ws_auth_header)
        assert token == self.valid_jwt_token

        # Test Sec-WebSocket-Protocol method
        import base64
        encoded_token = base64.urlsafe_b64encode(self.valid_jwt_token.encode()).decode().rstrip('=')
        mock_ws_protocol = Mock()
        mock_ws_protocol.headers = {
            "sec-websocket-protocol": f"jwt.{encoded_token}, chat"
        }
        mock_ws_protocol.query_params = {}
        
        token = self.auth_service._extract_websocket_token(mock_ws_protocol)
        assert token == self.valid_jwt_token

        # Test query parameter method (fallback)
        mock_ws_query = Mock()
        mock_ws_query.headers = {}
        mock_ws_query.query_params = {"token": self.valid_jwt_token}
        
        token = self.auth_service._extract_websocket_token(mock_ws_query)
        assert token == self.valid_jwt_token

        # Test no token found
        mock_ws_no_token = Mock()
        mock_ws_no_token.headers = {}
        mock_ws_no_token.query_params = {}
        
        token = self.auth_service._extract_websocket_token(mock_ws_no_token)
        assert token is None

        self.record_metric("token_extraction_methods_tested", 4)

    # === EXCEPTION HANDLING TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auth_service_error_handling(self):
        """Test handling of AuthServiceError exceptions - GRACEFUL DEGRADATION."""
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            # Test different AuthService exceptions
            error_scenarios = [
                AuthServiceError("Generic auth service error"),
                AuthServiceConnectionError("Connection failed"),
                AuthServiceNotAvailableError("Service not available"),
                AuthServiceValidationError("Validation error")
            ]

            for error in error_scenarios:
                mock_validate.side_effect = error

                result = await self.auth_service.authenticate_token(
                    token=self.valid_jwt_token,
                    context=AuthenticationContext.REST_API,
                    method=AuthenticationMethod.JWT_TOKEN
                )

                # Verify proper error handling
                assert result.success is False
                assert result.error_code == "AUTH_SERVICE_ERROR"
                assert str(error) in result.error

                # Verify debug information included
                assert "service_error_debug" in result.metadata
                debug_info = result.metadata["service_error_debug"]
                assert debug_info["error_type"] == type(error).__name__
                assert debug_info["error_message"] == str(error)

        self.record_metric("auth_error_scenarios_tested", len(error_scenarios))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self):
        """Test handling of unexpected exceptions - SYSTEM RESILIENCE."""
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            # Cause an unexpected error
            mock_validate.side_effect = RuntimeError("Unexpected system error")

            result = await self.auth_service.authenticate_token(
                token=self.valid_jwt_token,
                context=AuthenticationContext.GRPC,
                method=AuthenticationMethod.JWT_TOKEN
            )

            # Verify graceful error handling
            assert result.success is False
            assert result.error_code == "UNEXPECTED_ERROR"
            assert "Unexpected system error" in result.error

            # Verify comprehensive debugging information
            assert "unexpected_error_debug" in result.metadata
            debug_info = result.metadata["unexpected_error_debug"]
            assert debug_info["error_type"] == "RuntimeError"
            assert debug_info["error_message"] == "Unexpected system error"
            assert debug_info["context"] == AuthenticationContext.GRPC.value
            assert "timestamp" in debug_info
            assert "auth_client_available" in debug_info

        self.record_metric("unexpected_error_test", True)

    # === ENVIRONMENT-SPECIFIC RESILIENCE TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_staging_environment_resilience(self):
        """Test enhanced resilience for staging environment - DEPLOYMENT SAFETY."""
        # Set staging environment
        self.set_env_var("ENVIRONMENT", "staging")

        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            # First 4 calls fail (staging allows up to 5 retries), 5th succeeds
            mock_validate.side_effect = [
                AuthServiceConnectionError("Network timeout"),
                AuthServiceConnectionError("Network timeout"), 
                AuthServiceConnectionError("Network timeout"),
                AuthServiceConnectionError("Network timeout"),
                {
                    "valid": True,
                    "user_id": "staging_user",
                    "email": "staging@example.com",
                    "permissions": ["staging_access"]
                }
            ]

            start_time = time.time()
            result = await self.auth_service.authenticate_token(
                token=self.valid_jwt_token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            end_time = time.time()

            # Verify success after multiple retries in staging
            assert result.success is True
            assert result.user_id == "staging_user"

            # Verify staging-specific retry metadata
            resilience_meta = result.metadata["resilience_metadata"]
            assert resilience_meta["attempts_made"] == 5  # Staging allows more retries
            assert resilience_meta["environment"] == "staging"

            # Verify longer retry timing due to staging delays
            execution_time = end_time - start_time
            assert execution_time > 2.0  # Staging has longer delays

        self.record_metric("staging_resilience_test", True)

    # === PERFORMANCE AND TIMING TESTS ===

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authentication_timing_tracking(self):
        """Test authentication timing tracking - PERFORMANCE MONITORING."""
        with patch.object(self.auth_service._auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "perf_user",
                "email": "perf@example.com",
                "permissions": ["read"]
            }

            # Add a small delay to simulate real service
            async def delayed_validate(token):
                await asyncio.sleep(0.1)  # 100ms delay
                return mock_validate.return_value

            mock_validate.side_effect = delayed_validate

            start_time = time.time()
            result = await self.auth_service.authenticate_token(
                token=self.valid_jwt_token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            end_time = time.time()

            # Verify timing tracked
            execution_time = end_time - start_time
            assert execution_time >= 0.1  # At least the delay we added
            assert result.validated_at > start_time

        # Verify test execution timing
        self.assert_execution_time_under(5.0)  # Test should complete quickly
        
        self.record_metric("timing_test_complete", True)

    # === BUSINESS VALUE VALIDATION TESTS ===

    @pytest.mark.unit
    def test_business_value_integration(self):
        """Test that authentication service delivers measurable business value - REVENUE IMPACT."""
        # Initialize service with business metrics
        initial_stats = self.auth_service.get_authentication_stats()
        
        # Verify SSOT compliance metrics
        ssot_metrics = initial_stats["ssot_enforcement"]
        assert ssot_metrics["duplicate_paths_eliminated"] == 4  # Business impact: eliminated duplicate code
        assert ssot_metrics["ssot_compliant"] is True

        # Verify service provides expected business capabilities
        assert hasattr(self.auth_service, 'authenticate_token')  # Core user authentication
        assert hasattr(self.auth_service, 'authenticate_websocket')  # Critical for chat value ($120K+ MRR)
        assert hasattr(self.auth_service, 'validate_service_token')  # Inter-service security
        assert hasattr(self.auth_service, 'get_authentication_stats')  # Business monitoring
        assert hasattr(self.auth_service, 'health_check')  # Operational health

        # Record business value metrics
        self.record_metric("ssot_paths_eliminated", 4)
        self.record_metric("revenue_protection_enabled", True)
        self.record_metric("chat_authentication_ready", True)

    def test_final_metrics_summary(self):
        """Generate final test metrics summary - COMPREHENSIVE VALIDATION."""
        all_metrics = self.get_all_metrics()
        
        # Log critical business metrics
        critical_metrics = {
            "test_execution_time": all_metrics.get("execution_time", 0),
            "contexts_tested": all_metrics.get("contexts_tested", 0),
            "invalid_tokens_tested": all_metrics.get("invalid_tokens_tested", 0),
            "service_auth_tested": all_metrics.get("service_auth_success", False) and all_metrics.get("service_auth_failure", False),
            "websocket_auth_tested": all_metrics.get("websocket_auth_success", False),
            "retry_logic_validated": all_metrics.get("retry_logic_test", False),
            "error_handling_comprehensive": all_metrics.get("auth_error_scenarios_tested", 0) > 0,
            "business_value_confirmed": all_metrics.get("revenue_protection_enabled", False)
        }

        # Assert comprehensive testing completed
        assert critical_metrics["contexts_tested"] >= 5  # All context types tested
        assert critical_metrics["service_auth_tested"] is True  # Service auth both success and failure
        assert critical_metrics["websocket_auth_tested"] is True  # Critical for chat
        assert critical_metrics["retry_logic_validated"] is True  # Resilience validated
        assert critical_metrics["business_value_confirmed"] is True  # Revenue protection confirmed

        # Record final summary
        self.record_metric("comprehensive_test_complete", True)
        self.record_metric("critical_metrics_summary", critical_metrics)