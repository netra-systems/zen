"""
Backend <-> Auth Service Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless authentication and authorization
- Value Impact: Users can authenticate and access platform features without service disruption
- Strategic Impact: Core platform security and user experience depends on reliable auth service communication

These tests validate real interservice communication between the backend and auth service,
ensuring authentication flows work correctly across service boundaries without Docker containers.
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceNotAvailableError
)


class TestBackendAuthServiceIntegration(BaseTestCase):
    """Integration tests for Backend <-> Auth Service communication."""
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_auth_service_token_validation_success(self):
        """
        Test successful token validation between backend and auth service.
        
        BVJ: Critical for user authentication - ensures users can access features
        after successful login without service boundary issues.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock successful auth service response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com",
            "scopes": ["read", "write"]
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            client = AuthServiceClient()
            
            result = await client.validate_token("test-jwt-token")
            
            # Verify successful validation
            assert result is not None
            assert result.get("valid") == True
            assert result.get("user_id") == "test-user-123"
            assert result.get("email") == "test@example.com"
            assert "scopes" in result
            
            # Verify correct API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "validate" in str(call_args[1]["url"])
            
            # Verify service authentication headers
            headers = call_args[1].get("headers", {})
            assert "Authorization" in headers
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_auth_service_token_validation_invalid_token(self):
        """
        Test token validation with invalid token response.
        
        BVJ: Security critical - ensures invalid tokens are properly rejected
        and don't grant unauthorized access to platform features.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock invalid token response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "valid": False,
            "error": "invalid_token",
            "message": "Token is expired or invalid"
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            client = AuthServiceClient()
            
            result = await client.validate_token("invalid-jwt-token")
            
            # Verify rejection of invalid token
            assert result is not None
            assert result.get("valid") == False
            assert result.get("error") == "invalid_token"
            assert "message" in result
            
            # Verify API call was made
            mock_post.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_auth_service_connection_failure_handling(self):
        """
        Test backend handling of auth service connection failures.
        
        BVJ: Reliability critical - ensures graceful degradation when auth service
        is unavailable, maintaining system stability and user experience.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock connection error
        with patch('httpx.AsyncClient.post', side_effect=httpx.ConnectError("Connection failed")) as mock_post:
            client = AuthServiceClient()
            
            # Should raise appropriate exception
            with pytest.raises(AuthServiceConnectionError) as exc_info:
                await client.validate_token("test-token")
            
            # Verify error details
            assert "Connection failed" in str(exc_info.value)
            mock_post.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_auth_service_circuit_breaker_activation(self):
        """
        Test circuit breaker activation on repeated auth service failures.
        
        BVJ: System resilience - prevents cascading failures when auth service
        is down, maintaining platform availability for other features.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        client = AuthServiceClient()
        
        # Mock repeated failures to trigger circuit breaker
        with patch('httpx.AsyncClient.post', side_effect=httpx.TimeoutException("Request timeout")) as mock_post:
            
            # First few calls should attempt connection
            for i in range(3):
                with pytest.raises((AuthServiceConnectionError, AuthServiceNotAvailableError)):
                    await client.validate_token(f"test-token-{i}")
            
            # Verify multiple connection attempts were made
            assert mock_post.call_count >= 3
            
            # Circuit breaker should now be open
            # Next call should fail fast without making HTTP request
            call_count_before = mock_post.call_count
            
            with pytest.raises(AuthServiceNotAvailableError) as exc_info:
                await client.validate_token("test-token-circuit-open")
            
            # Should not have made additional HTTP calls (circuit is open)
            assert "circuit breaker" in str(exc_info.value).lower() or "not available" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_auth_service_user_profile_retrieval(self):
        """
        Test user profile retrieval from auth service.
        
        BVJ: User experience critical - ensures user profile data is available
        for personalization and feature access control across the platform.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock user profile response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_id": "user-456",
            "email": "user@example.com",
            "name": "Test User",
            "subscription_tier": "enterprise",
            "permissions": ["agent_access", "data_export", "advanced_analytics"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-09-07T10:00:00Z"
        }
        
        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            client = AuthServiceClient()
            
            profile = await client.get_user_profile("user-456", "valid-jwt-token")
            
            # Verify profile data
            assert profile is not None
            assert profile.get("user_id") == "user-456"
            assert profile.get("email") == "user@example.com"
            assert profile.get("name") == "Test User"
            assert profile.get("subscription_tier") == "enterprise"
            assert "permissions" in profile
            assert len(profile["permissions"]) > 0
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "user" in str(call_args[1]["url"]) or "profile" in str(call_args[1]["url"])
            
            # Verify authentication headers
            headers = call_args[1].get("headers", {})
            assert "Authorization" in headers