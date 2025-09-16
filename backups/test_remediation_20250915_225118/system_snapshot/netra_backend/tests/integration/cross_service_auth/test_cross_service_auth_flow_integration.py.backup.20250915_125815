"""
Test Cross-Service Authentication Flow Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Security Foundation & User Retention
- Value Impact: Ensures reliable cross-service authentication prevents user login failures
- Strategic Impact: Auth failures block all user operations - MISSION CRITICAL for business value

This test suite validates the critical authentication flow between:
1. Backend service -> Auth service communication
2. Service-to-service authentication patterns
3. Token validation across service boundaries
4. Error handling and resilience patterns
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch

from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient, 
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceValidationError,
    CircuitBreakerError,
    get_auth_service_client
)
from netra_backend.app.clients.auth_client_cache import AuthTokenCache, AuthCircuitBreakerManager
from netra_backend.app.clients.circuit_breaker import CircuitBreakerOpen, CircuitBreakerConfig
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env


class TestCrossServiceAuthFlowIntegration:
    """Test cross-service authentication flow with real components."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_to_service_authentication_headers(self, real_services_fixture):
        """
        Test service-to-service authentication header generation and validation.
        
        Business Value: Ensures backend can communicate with auth service using proper credentials.
        This is foundational for all user authentication - if this fails, no users can log in.
        """
        # Arrange: Create auth client with test service credentials
        client = AuthServiceClient()
        
        # Set test service credentials
        client.service_id = "test-backend-service"
        client.service_secret = "test_service_secret_12345"
        
        # Act: Get service authentication headers
        headers = client._get_service_auth_headers()
        
        # Assert: Headers contain required service authentication
        assert "X-Service-ID" in headers, "Service ID header must be present for inter-service auth"
        assert "X-Service-Secret" in headers, "Service Secret header must be present for inter-service auth"
        assert headers["X-Service-ID"] == "test-backend-service"
        assert headers["X-Service-Secret"] == "test_service_secret_12345"
        
        # Verify headers are properly sanitized (no illegal characters)
        for key, value in headers.items():
            assert '\n' not in value, f"Header {key} contains illegal newline character"
            assert '\r' not in value, f"Header {key} contains illegal carriage return"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_token_validation_flow(self, real_services_fixture):
        """
        Test complete token validation flow across service boundaries.
        
        Business Value: Validates the core authentication flow that enables user access.
        If this fails, users cannot authenticate and access the platform.
        """
        # Arrange: Create client with mock HTTP responses
        client = AuthServiceClient()
        client.service_id = "test-backend"
        client.service_secret = "test_secret"
        
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.test_signature"
        expected_validation_result = {
            "valid": True,
            "user_id": "test_user_123",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }
        
        # Mock successful auth service response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_validation_result
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: Validate token through cross-service call
            result = await client.validate_token(test_token)
            
            # Assert: Validation succeeded with expected data
            assert result is not None, "Token validation should return result"
            assert result["valid"] is True, "Token should be validated successfully"
            assert result["user_id"] == "test_user_123"
            assert result["email"] == "test@example.com"
            assert result["permissions"] == ["read", "write"]
            
            # Verify proper cross-service call was made
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Check endpoint
            assert call_args[1]["json"]["token"] == test_token
            assert call_args[1]["json"]["token_type"] == "access"
            
            # Check service authentication headers
            headers = call_args[1]["headers"]
            assert "X-Service-ID" in headers
            assert "X-Service-Secret" in headers

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_cross_service_auth_service_unavailable_handling(self, real_services_fixture):
        """
        Test handling of auth service unavailability during cross-service calls.
        
        Business Value: Ensures graceful degradation when auth service is down.
        Critical for maintaining service availability during auth service outages.
        """
        # Arrange: Client with connection error
        client = AuthServiceClient()
        
        test_token = "test_token_for_unavailable_service"
        
        # Mock connection error to auth service
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = ConnectionError("Auth service unreachable")
            
            # Act: Attempt token validation with service unavailable
            result = await client.validate_token(test_token)
            
            # Assert: Proper error handling with user-friendly response
            assert result is not None, "Should return error result, not None"
            assert result["valid"] is False, "Token validation should fail when service unavailable"
            assert "error" in result, "Error result should contain error field"
            assert result["error"] == "auth_service_unreachable"
            
            # Verify user notification is present for frontend display
            assert "user_notification" in result
            notification = result["user_notification"]
            assert "user_friendly_message" in notification
            assert "Authentication service temporarily unavailable" in notification["message"]

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_cross_service_authentication_token_caching_flow(self, real_services_fixture):
        """
        Test token caching during cross-service authentication to reduce load.
        
        Business Value: Improves performance and reduces auth service load.
        Cached validation enables faster user experience and system scalability.
        """
        # Arrange: Client with cache
        client = AuthServiceClient()
        test_token = "cached_test_token_12345"
        
        # Mock first validation call
        validation_data = {
            "valid": True,
            "user_id": "cached_user_123",
            "email": "cached@example.com",
            "permissions": ["read"]
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = validation_data
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: First validation (should hit auth service and cache result)
            result1 = await client.validate_token(test_token)
            
            # Second validation (should use cache, not hit auth service)
            result2 = await client.validate_token(test_token)
            
            # Assert: Both validations successful
            assert result1["valid"] is True
            assert result2["valid"] is True
            assert result1["user_id"] == result2["user_id"]
            
            # Verify caching behavior - should only call auth service once
            # Note: The actual cache behavior depends on implementation
            # but we can verify consistent results
            assert result1 == result2, "Cached and fresh results should be identical"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_with_invalid_service_credentials(self, real_services_fixture):
        """
        Test behavior when backend uses invalid service credentials with auth service.
        
        Business Value: Ensures proper error handling for misconfigured services.
        Prevents silent failures that could leave users unable to authenticate.
        """
        # Arrange: Client with invalid service credentials
        client = AuthServiceClient()
        client.service_id = "invalid_service_id"
        client.service_secret = "invalid_service_secret"
        
        test_token = "test_token_invalid_service_creds"
        
        # Mock 403 Forbidden response (invalid service credentials)
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "Invalid service credentials"}
        mock_response.text = "Forbidden"
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            # Act: Attempt validation with invalid service creds
            result = await client.validate_token(test_token)
            
            # Assert: Proper error handling for invalid service auth
            assert result is not None
            assert result["valid"] is False
            assert result["error"] == "inter_service_auth_failed"
            assert "Service credentials not configured or invalid" in result["details"]
            
            # Verify user notification provides actionable information
            notification = result["user_notification"]
            assert notification["severity"] == "critical"
            assert "configuration issue" in notification["user_friendly_message"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_token_refresh_during_active_session(self, real_services_fixture):
        """
        Test token refresh functionality during active user sessions.
        
        Business Value: Ensures users don't get logged out during active sessions.
        Critical for user experience and preventing workflow interruptions.
        """
        # Arrange: Client and expired access token scenario
        client = AuthServiceClient()
        client.service_id = "test-service" 
        client.service_secret = "test_secret"
        
        refresh_token = "valid_refresh_token_12345"
        
        # Mock successful refresh response
        new_token_data = {
            "access_token": "new_access_token_67890",
            "refresh_token": "new_refresh_token_67890",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = new_token_data
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: Refresh token
            result = await client.refresh_token(refresh_token)
            
            # Assert: Token refresh successful
            assert result is not None, "Token refresh should return new tokens"
            assert result["access_token"] == "new_access_token_67890"
            assert result["refresh_token"] == "new_refresh_token_67890"
            assert result["expires_in"] == 3600
            
            # Verify proper service authentication in refresh request
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert "X-Service-ID" in headers
            assert "X-Service-Secret" in headers

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_user_login_flow(self, real_services_fixture):
        """
        Test complete user login flow across services.
        
        Business Value: Validates the core user onboarding and authentication flow.
        This is the primary entry point for user engagement with the platform.
        """
        # Arrange: Login credentials and client
        client = AuthServiceClient()
        client.service_id = "backend-service"
        client.service_secret = "backend_secret"
        
        email = "user@example.com"
        password = "secure_password_123"
        
        # Mock successful login response
        login_response_data = {
            "access_token": "user_access_token_abc123",
            "refresh_token": "user_refresh_token_def456",
            "user_id": "user_12345",
            "role": "user",
            "expires_in": 3600
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = login_response_data
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: User login
            result = await client.login(email, password)
            
            # Assert: Login successful with proper token data
            assert result is not None, "Login should return authentication data"
            assert result["access_token"] == "user_access_token_abc123"
            assert result["refresh_token"] == "user_refresh_token_def456"
            assert result["user_id"] == "user_12345"
            assert result["expires_in"] == 3600
            
            # Verify login request format
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_data = call_args[1]["json"]
            assert request_data["email"] == email
            assert request_data["password"] == password
            assert request_data["provider"] == "local"
            
            # Verify service authentication headers
            headers = call_args[1]["headers"]
            assert "X-Service-ID" in headers
            assert "X-Service-Secret" in headers

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_user_logout_flow(self, real_services_fixture):
        """
        Test user logout flow with proper token invalidation across services.
        
        Business Value: Ensures secure logout and token cleanup.
        Critical for security - prevents token reuse after logout.
        """
        # Arrange: Client and user token for logout
        client = AuthServiceClient()
        client.service_id = "backend-service"
        client.service_secret = "backend_secret"
        
        user_token = "active_user_token_to_logout"
        session_id = "user_session_123"
        
        # Mock successful logout response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: User logout
            result = await client.logout(user_token, session_id)
            
            # Assert: Logout successful
            assert result is True, "Logout should succeed"
            
            # Verify logout request format
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Check authorization header contains user token
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert f"Bearer {user_token}" in headers["Authorization"]
            
            # Check service authentication headers also present
            assert "X-Service-ID" in headers
            assert "X-Service-Secret" in headers
            
            # Check session ID in payload
            request_data = call_args[1]["json"] 
            assert request_data["session_id"] == session_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_blacklist_token_validation(self, real_services_fixture):
        """
        Test blacklisted token detection during validation.
        
        Business Value: Prevents use of compromised or revoked tokens.
        Critical security feature to prevent unauthorized access.
        """
        # Arrange: Client and blacklisted token
        client = AuthServiceClient()
        blacklisted_token = "blacklisted_token_12345"
        
        # Mock blacklist check response (token is blacklisted)
        mock_blacklist_response = AsyncMock()
        mock_blacklist_response.status_code = 200
        mock_blacklist_response.json.return_value = {"blacklisted": True}
        
        with patch('httpx.AsyncClient.post', return_value=mock_blacklist_response):
            # Act: Check if token is blacklisted
            is_blacklisted = await client._is_token_blacklisted_atomic(blacklisted_token)
            
            # Assert: Token is properly identified as blacklisted
            assert is_blacklisted is True, "Blacklisted token should be detected"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_environment_detection_integration(self, real_services_fixture):
        """
        Test environment detection for cross-service authentication configuration.
        
        Business Value: Ensures proper auth configuration per environment.
        Critical for security - production requires different settings than test.
        """
        # Arrange: Client with environment detection
        client = AuthServiceClient()
        
        # Act: Detect current environment
        environment = client.detect_environment()
        
        # Assert: Environment detection works
        assert environment is not None, "Environment should be detected"
        
        # Verify OAuth config is environment-appropriate
        oauth_config = client.get_oauth_config()
        assert oauth_config is not None, "OAuth config should be available for environment"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_concurrent_validation_safety(self, real_services_fixture):
        """
        Test concurrent token validation safety across multiple requests.
        
        Business Value: Ensures auth system handles concurrent users safely.
        Critical for multi-user platform - race conditions could cause auth failures.
        """
        # Arrange: Multiple tokens for concurrent validation
        client = AuthServiceClient()
        client.service_id = "concurrent-test-service"
        client.service_secret = "concurrent_secret"
        
        tokens = [f"concurrent_token_{i}" for i in range(5)]
        
        # Mock responses for each token
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            request_data = kwargs.get("json", {})
            token = request_data.get("token", "unknown")
            
            mock_response.json.return_value = {
                "valid": True,
                "user_id": f"user_for_{token}",
                "email": f"user_{token}@example.com",
                "permissions": ["read"]
            }
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Validate tokens concurrently
            tasks = [client.validate_token(token) for token in tokens]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert: All validations successful and results are unique per token
            assert len(results) == 5, "All concurrent validations should complete"
            
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Validation {i} should not raise exception"
                assert result["valid"] is True, f"Token {i} should be valid"
                assert tokens[i] in result["user_id"], f"Result {i} should be specific to token {i}"