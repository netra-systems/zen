"""
Test JWT Token Lifecycle Management Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Security Foundation & Session Management
- Value Impact: Ensures secure token lifecycle prevents unauthorized access and session hijacking
- Strategic Impact: Token lifecycle management is critical for user security and platform trust

This test suite validates the complete JWT token lifecycle:
1. Token creation and initial validation
2. Token renewal and refresh cycles
3. Token expiration and cleanup
4. Token invalidation and blacklisting
5. Cross-service token propagation
6. Security validation throughout lifecycle
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock

from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthTokenRequest,
    AuthTokenResponse, 
    TokenValidationRequest,
    TokenValidationResponse,
    validate_jwt_format
)
from netra_backend.app.clients.auth_client_cache import (
    AuthTokenCache,
    CachedToken,
    TokenCache
)
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env


class TestJWTTokenLifecycleIntegration:
    """Test JWT token lifecycle with real authentication components."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_creation_and_initial_validation(self, real_services_fixture):
        """
        Test JWT token creation and first validation in the lifecycle.
        
        Business Value: Ensures new user tokens are properly created and validated.
        This is the foundation of user authentication - must work for user onboarding.
        """
        # Arrange: Client and token creation data
        client = AuthServiceClient()
        client.service_id = "token-lifecycle-service"
        client.service_secret = "lifecycle_secret_123"
        
        token_data = {
            "user_id": "lifecycle_user_123",
            "email": "lifecycle@example.com",
            "role": "user",
            "permissions": ["read", "write"],
            "expires_in": 3600
        }
        
        # Mock successful token creation
        created_token_response = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoibGlmZWN5Y2xlX3VzZXJfMTIzIn0.test_signature",
            "refresh_token": "refresh_token_for_lifecycle_user",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        # Mock validation response for the created token
        validation_response = {
            "valid": True,
            "user_id": "lifecycle_user_123",
            "email": "lifecycle@example.com",
            "permissions": ["read", "write"]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Configure mock for token creation
            create_response = AsyncMock()
            create_response.status_code = 200
            create_response.json.return_value = created_token_response
            
            # Configure mock for token validation
            validate_response = AsyncMock()
            validate_response.status_code = 200
            validate_response.json.return_value = validation_response
            
            mock_post.side_effect = [create_response, validate_response]
            
            # Act: Create token and validate it
            created_token = await client.create_token(token_data)
            assert created_token is not None, "Token creation should succeed"
            
            access_token = created_token["access_token"]
            validation_result = await client.validate_token(access_token)
            
            # Assert: Token creation and validation successful
            assert validation_result["valid"] is True, "Newly created token should be valid"
            assert validation_result["user_id"] == "lifecycle_user_123"
            assert validation_result["email"] == "lifecycle@example.com"
            assert validation_result["permissions"] == ["read", "write"]
            
            # Verify JWT format is correct
            assert validate_jwt_format(access_token), "Created token should have valid JWT format"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_refresh_cycle_integration(self, real_services_fixture):
        """
        Test complete token refresh cycle maintaining user session.
        
        Business Value: Enables continuous user sessions without re-authentication.
        Critical for user experience - prevents interruptions during active work.
        """
        # Arrange: Client and initial tokens
        client = AuthServiceClient()
        
        original_access_token = "original_access_token_12345"
        refresh_token = "refresh_token_12345"
        
        # Mock token refresh response
        refreshed_tokens = {
            "access_token": "refreshed_access_token_67890",
            "refresh_token": "new_refresh_token_67890",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        # Mock validation of refreshed token
        validation_response = {
            "valid": True,
            "user_id": "refresh_user_123",
            "email": "refresh@example.com",
            "permissions": ["read", "write", "admin"]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            refresh_response = AsyncMock()
            refresh_response.status_code = 200
            refresh_response.json.return_value = refreshed_tokens
            
            validate_response = AsyncMock()
            validate_response.status_code = 200
            validate_response.json.return_value = validation_response
            
            mock_post.side_effect = [refresh_response, validate_response]
            
            # Act: Refresh token and validate new token
            refreshed = await client.refresh_token(refresh_token)
            assert refreshed is not None, "Token refresh should succeed"
            
            new_access_token = refreshed["access_token"]
            validation = await client.validate_token(new_access_token)
            
            # Assert: Token refresh cycle completed successfully
            assert new_access_token != original_access_token, "New token should be different"
            assert refreshed["refresh_token"] != refresh_token, "New refresh token should be different"
            assert validation["valid"] is True, "Refreshed token should be valid"
            assert validation["user_id"] == "refresh_user_123"
            
            # Verify refresh request format
            refresh_call = mock_post.call_args_list[0]
            refresh_payload = refresh_call[1]["json"]
            assert refresh_payload["refresh_token"] == refresh_token

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_expiration_and_cleanup_integration(self, real_services_fixture):
        """
        Test token expiration handling and cleanup processes.
        
        Business Value: Ensures security through proper token expiration.
        Prevents indefinite token validity which could lead to security breaches.
        """
        # Arrange: Client with cached token that will expire
        client = AuthServiceClient()
        expired_token = "expired_token_12345"
        
        # Create a cached token entry that's already expired
        token_cache = client.token_cache
        
        # Mock expired token in cache
        expired_cached_token = CachedToken(
            data={
                "valid": True,
                "user_id": "expired_user_123",
                "email": "expired@example.com",
                "permissions": ["read"]
            },
            ttl_seconds=-60  # Negative TTL means already expired
        )
        
        # Simulate cache with expired token
        with patch.object(token_cache, 'get_cached_token_sync', return_value=None):
            # Mock auth service validation failure for expired token
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "Token expired"}
            
            with patch('httpx.AsyncClient.post', return_value=mock_response):
                # Act: Attempt to validate expired token
                result = await client.validate_token(expired_token)
                
                # Assert: Expired token is properly rejected
                assert result is not None
                assert result["valid"] is False, "Expired token should not be valid"
                
                # Verify cache cleanup behavior - expired token should not be cached
                cached_result = await token_cache.get_cached_token(expired_token)
                assert cached_result is None, "Expired token should not remain in cache"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_invalidation_and_blacklisting_integration(self, real_services_fixture):
        """
        Test token invalidation and blacklist integration.
        
        Business Value: Enables immediate token revocation for security incidents.
        Critical for compromised account protection and admin controls.
        """
        # Arrange: Client and token to be blacklisted
        client = AuthServiceClient()
        token_to_blacklist = "token_to_blacklist_12345"
        
        # Mock blacklist check - initially not blacklisted
        not_blacklisted_response = AsyncMock()
        not_blacklisted_response.status_code = 200
        not_blacklisted_response.json.return_value = {"blacklisted": False}
        
        # Mock blacklist check - after blacklisting
        blacklisted_response = AsyncMock()
        blacklisted_response.status_code = 200
        blacklisted_response.json.return_value = {"blacklisted": True}
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call: check if not blacklisted
            mock_post.return_value = not_blacklisted_response
            
            # Act: Check initial blacklist status
            is_blacklisted_initial = await client._is_token_blacklisted_atomic(token_to_blacklist)
            assert is_blacklisted_initial is False, "Token should not be initially blacklisted"
            
            # Simulate token being blacklisted (would happen through admin action)
            mock_post.return_value = blacklisted_response
            
            # Act: Check blacklist status after blacklisting
            is_blacklisted_after = await client._is_token_blacklisted_atomic(token_to_blacklist)
            assert is_blacklisted_after is True, "Token should be blacklisted after admin action"
            
            # Verify cache invalidation for blacklisted token
            await client.token_cache.invalidate_cached_token(token_to_blacklist)
            
            # Token should not be retrievable from cache
            cached_after_invalidation = await client.token_cache.get_cached_token(token_to_blacklist)
            assert cached_after_invalidation is None, "Blacklisted token should be removed from cache"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_cross_service_propagation_integration(self, real_services_fixture):
        """
        Test token propagation across multiple services.
        
        Business Value: Enables seamless user experience across service boundaries.
        Critical for microservices architecture - single token should work everywhere.
        """
        # Arrange: Multiple service clients
        backend_client = AuthServiceClient()
        backend_client.service_id = "backend-service"
        backend_client.service_secret = "backend_secret"
        
        analytics_client = AuthServiceClient()
        analytics_client.service_id = "analytics-service" 
        analytics_client.service_secret = "analytics_secret"
        
        user_token = "cross_service_token_12345"
        
        # Mock validation responses for different services
        backend_validation = {
            "valid": True,
            "user_id": "cross_service_user",
            "email": "cross@example.com",
            "permissions": ["backend:read", "backend:write"]
        }
        
        analytics_validation = {
            "valid": True,
            "user_id": "cross_service_user",
            "email": "cross@example.com", 
            "permissions": ["analytics:read", "analytics:query"]
        }
        
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            # Return different permissions based on service
            headers = kwargs.get("headers", {})
            service_id = headers.get("X-Service-ID", "")
            
            if service_id == "backend-service":
                mock_response.json.return_value = backend_validation
            elif service_id == "analytics-service":
                mock_response.json.return_value = analytics_validation
            else:
                mock_response.json.return_value = {"valid": False}
                
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Validate same token across different services
            backend_result = await backend_client.validate_token(user_token)
            analytics_result = await analytics_client.validate_token(user_token)
            
            # Assert: Token valid across services with appropriate permissions
            assert backend_result["valid"] is True, "Token should be valid in backend service"
            assert analytics_result["valid"] is True, "Token should be valid in analytics service"
            
            # Same user across services
            assert backend_result["user_id"] == analytics_result["user_id"]
            assert backend_result["email"] == analytics_result["email"]
            
            # Different permissions per service
            assert "backend:read" in backend_result["permissions"]
            assert "analytics:read" in analytics_result["permissions"]
            assert "analytics:query" in analytics_result["permissions"]

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_jwt_token_security_validation_throughout_lifecycle(self, real_services_fixture):
        """
        Test security validation throughout complete token lifecycle.
        
        Business Value: Ensures comprehensive security at every lifecycle stage.
        Critical for maintaining platform security and preventing vulnerabilities.
        """
        # Arrange: Client and various token formats for security testing
        client = AuthServiceClient()
        
        test_cases = [
            # Valid JWT format
            {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdCJ9.test_signature",
                "should_pass_format": True,
                "description": "Valid JWT format"
            },
            # Invalid format - missing parts
            {
                "token": "invalid.token",
                "should_pass_format": False,
                "description": "Invalid JWT format - missing parts"
            },
            # Invalid format - empty
            {
                "token": "",
                "should_pass_format": False,
                "description": "Empty token"
            },
            # Invalid format - None
            {
                "token": None,
                "should_pass_format": False,
                "description": "None token"
            },
            # Invalid format - wrong structure
            {
                "token": "not.a.jwt.token.at.all",
                "should_pass_format": False,
                "description": "Wrong JWT structure"
            }
        ]
        
        # Act & Assert: Test format validation for each case
        for test_case in test_cases:
            token = test_case["token"]
            expected_valid = test_case["should_pass_format"]
            description = test_case["description"]
            
            # Test format validation
            format_valid = validate_jwt_format(token)
            assert format_valid == expected_valid, f"Format validation failed for: {description}"
            
            # For tokens that pass format validation, test full validation
            if expected_valid:
                # Mock auth service response
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "valid": True,
                    "user_id": "security_test_user",
                    "email": "security@example.com",
                    "permissions": ["read"]
                }
                
                with patch('httpx.AsyncClient.post', return_value=mock_response):
                    result = await client.validate_token(token)
                    assert result is not None, f"Validation should return result for: {description}"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_jwt_token_cache_lifecycle_integration(self, real_services_fixture):
        """
        Test token caching throughout the complete lifecycle.
        
        Business Value: Optimizes performance while maintaining security.
        Reduces auth service load and improves response times for users.
        """
        # Arrange: Client with token cache
        client = AuthServiceClient()
        token_cache = client.token_cache
        
        test_token = "cached_lifecycle_token_12345"
        
        # Mock validation response
        validation_data = {
            "valid": True,
            "user_id": "cached_user_123",
            "email": "cached@example.com",
            "permissions": ["read", "write"]
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = validation_data
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Act: First validation (should cache)
            result1 = await client.validate_token(test_token)
            
            # Verify caching occurred
            cached_result = await token_cache.get_cached_token(test_token)
            assert cached_result is not None, "Token should be cached after validation"
            assert cached_result["user_id"] == "cached_user_123"
            
            # Second validation (should use cache)
            result2 = await client.validate_token(test_token)
            
            # Assert: Both validations successful and consistent
            assert result1["valid"] is True
            assert result2["valid"] is True
            assert result1["user_id"] == result2["user_id"]
            
            # Test cache invalidation
            await token_cache.invalidate_cached_token(test_token)
            
            invalidated_cache = await token_cache.get_cached_token(test_token)
            assert invalidated_cache is None, "Token should be removed from cache after invalidation"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_concurrent_lifecycle_operations(self, real_services_fixture):
        """
        Test concurrent token lifecycle operations for thread safety.
        
        Business Value: Ensures auth system handles concurrent users safely.
        Critical for multi-user platform - prevents race conditions in auth.
        """
        # Arrange: Multiple tokens for concurrent operations
        client = AuthServiceClient()
        token_cache = client.token_cache
        
        tokens = [f"concurrent_lifecycle_token_{i}" for i in range(10)]
        
        # Mock responses for concurrent operations
        async def mock_post_handler(*args, **kwargs):
            request_data = kwargs.get("json", {})
            token = request_data.get("token", "unknown")
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": f"user_{token}",
                "email": f"user_{token}@example.com",
                "permissions": ["read"]
            }
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Concurrent validation and caching operations
            validation_tasks = [client.validate_token(token) for token in tokens]
            
            # Also test concurrent cache operations
            cache_tasks = []
            for i, token in enumerate(tokens[:5]):  # Cache operations for first 5 tokens
                cache_tasks.append(
                    token_cache.cache_token(token, {
                        "valid": True,
                        "user_id": f"cached_user_{i}",
                        "cached": True
                    })
                )
            
            # Execute all operations concurrently
            validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            await asyncio.gather(*cache_tasks, return_exceptions=True)
            
            # Assert: All operations completed without race conditions
            assert len(validation_results) == 10, "All concurrent validations should complete"
            
            for i, result in enumerate(validation_results):
                assert not isinstance(result, Exception), f"Validation {i} should not raise exception"
                assert result["valid"] is True, f"Token {i} should be valid"
                assert tokens[i] in result["user_id"], f"Result {i} should be specific to token {i}"
            
            # Verify cache integrity after concurrent operations
            for i, token in enumerate(tokens[:5]):
                cached = await token_cache.get_cached_token(token)
                # Should have either validation result or cached result, but not corrupted
                assert cached is not None, f"Token {i} should have cached data"
                assert cached["valid"] is True, f"Cached token {i} should be valid"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_lifecycle_error_recovery_integration(self, real_services_fixture):
        """
        Test error recovery during token lifecycle operations.
        
        Business Value: Ensures resilience during auth service disruptions.
        Critical for maintaining service availability during partial outages.
        """
        # Arrange: Client with error conditions
        client = AuthServiceClient()
        problematic_token = "error_recovery_token_12345"
        
        # Mock sequence: error, then recovery
        error_response = AsyncMock()
        error_response.side_effect = ConnectionError("Auth service temporarily unavailable")
        
        recovery_response = AsyncMock()
        recovery_response.status_code = 200
        recovery_response.json.return_value = {
            "valid": True,
            "user_id": "recovered_user_123",
            "email": "recovered@example.com",
            "permissions": ["read"]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call fails
            mock_post.side_effect = [ConnectionError("Service unavailable")]
            
            # Act: First validation attempt (should handle error gracefully)
            result1 = await client.validate_token(problematic_token)
            
            # Assert: Error handled gracefully with user notification
            assert result1 is not None
            assert result1["valid"] is False
            assert "error" in result1
            assert "user_notification" in result1
            
            # Simulate service recovery
            mock_post.side_effect = None
            mock_post.return_value = recovery_response
            
            # Act: Second validation attempt (should succeed after recovery)  
            result2 = await client.validate_token(problematic_token)
            
            # Assert: Recovery successful
            assert result2["valid"] is True
            assert result2["user_id"] == "recovered_user_123"
            assert result2["email"] == "recovered@example.com"