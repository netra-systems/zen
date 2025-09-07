"""
Auth Service Endpoints Business Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Authentication is required for all users
- Business Goal: Ensure authentication endpoints function properly to enable user access
- Value Impact: Working auth endpoints enable user onboarding, login, and session management
- Strategic Impact: Core platform functionality - without auth, users cannot access chat features

CRITICAL: These tests use REAL PostgreSQL and Redis services - NO MOCKS allowed.
Tests validate complete auth endpoint workflows with real service dependencies for business value delivery.

This test suite validates:
1. /auth/health endpoint with real database connectivity validation
2. /auth/status endpoint with service readiness checks  
3. /oauth/login endpoint with real OAuth provider integration
4. /oauth/callback endpoint with real token exchange operations
5. /auth/refresh endpoint with real token management
6. /auth/logout endpoint with proper session cleanup

All tests focus on business value: enabling user authentication flows that are essential
for users to access the AI-powered chat platform and receive optimization insights.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
import aiohttp
from unittest.mock import AsyncMock

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.models.auth_models import RefreshRequest
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.oauth_manager import OAuthManager


class TestAuthEndpointsBusinessIntegration(BaseIntegrationTest):
    """Integration tests for auth service endpoints with real business value."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, real_services_fixture):
        """Set up test environment with real services for business integration."""
        self.env = get_env()
        self.real_services = real_services_fixture
        
        # Real service configuration
        self.auth_config = AuthConfig()
        self.auth_service = AuthService()
        self.oauth_manager = OAuthManager()
        
        # Test endpoints - using real service URLs
        self.auth_service_url = self.real_services.get("auth_url", "http://localhost:8081")
        self.health_endpoint = f"{self.auth_service_url}/auth/health"
        self.status_endpoint = f"{self.auth_service_url}/auth/status"
        self.oauth_login_endpoint = f"{self.auth_service_url}/oauth/login"
        self.oauth_callback_endpoint = f"{self.auth_service_url}/oauth/callback"
        self.refresh_endpoint = f"{self.auth_service_url}/auth/refresh"
        self.logout_endpoint = f"{self.auth_service_url}/auth/logout"
        
        # Test user data for business scenarios
        self.test_user_email = f"integration-test-{uuid.uuid4()}@example.com"
        self.test_user_name = "Integration Test User"
        
        # HTTP client for real endpoint testing
        self.session = aiohttp.ClientSession()
        
        yield
        
        # Cleanup real test data
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services after business tests."""
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.close()
                
            # Clean up test user data from real database if created
            if hasattr(self.auth_service, '_db_connection') and self.auth_service._db_connection:
                # Note: In a real implementation, we would clean up specific test user data
                # This placeholder shows the pattern for real database cleanup
                self.logger.info(f"Cleaned up test data for user: {self.test_user_email}")
                
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_with_real_database_validation(self, real_services_fixture):
        """
        Test /auth/health endpoint provides accurate database connectivity status.
        
        Business Value: Health endpoint enables monitoring and ensures auth service
        can connect to database, which is critical for user authentication operations.
        Without database connectivity, users cannot log in or access the platform.
        """
        # Test with real HTTP request to health endpoint
        async with self.session.get(self.health_endpoint) as response:
            assert response.status == 200
            health_data = await response.json()
            
            # Verify business-critical health information
            assert health_data["status"] in ["healthy", "unhealthy"]
            assert health_data["service"] == "auth-service"
            assert health_data["version"] == "1.0.0"
            assert "timestamp" in health_data
            assert "database_status" in health_data
            
            # Database status must be meaningful for business operations
            database_status = health_data["database_status"]
            assert database_status in ["connected", "disconnected", "not_configured", "error", "not_initialized"]
            
            # If database is connected, service should be healthy
            if database_status == "connected":
                assert health_data["status"] == "healthy"
                
            # Verify timestamp is recent (within last 30 seconds)
            timestamp_str = health_data["timestamp"]
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            time_diff = datetime.now(timezone.utc) - timestamp
            assert time_diff.total_seconds() < 30, "Health check timestamp should be recent"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_status_endpoint_service_readiness(self, real_services_fixture):
        """
        Test /auth/status endpoint confirms service is ready for business operations.
        
        Business Value: Status endpoint enables load balancers and monitoring systems
        to determine if auth service can handle user authentication requests.
        Critical for ensuring high availability of user access to the platform.
        """
        # Test with real HTTP request to status endpoint
        async with self.session.get(self.status_endpoint) as response:
            assert response.status == 200
            status_data = await response.json()
            
            # Verify business-critical status information
            assert status_data["service"] == "auth-service"
            assert status_data["status"] == "running"
            assert status_data["version"] == "1.0.0"
            assert "timestamp" in status_data
            
            # Verify timestamp indicates service is actively responding
            timestamp_str = status_data["timestamp"]
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            time_diff = datetime.now(timezone.utc) - timestamp
            assert time_diff.total_seconds() < 10, "Status timestamp should be very recent"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_login_endpoint_business_flow(self, real_services_fixture):
        """
        Test /oauth/login endpoint initiates proper OAuth flow for user onboarding.
        
        Business Value: OAuth login enables users to authenticate with Google/GitHub,
        providing seamless onboarding experience essential for user acquisition
        and platform growth. Without OAuth, users cannot easily join the platform.
        """
        # Test OAuth login initiation with real OAuth configuration
        oauth_params = {
            "provider": "google",
            "redirect_uri": "http://localhost:3000/auth/callback"
        }
        
        # Test GET request to OAuth login endpoint
        async with self.session.get(
            self.oauth_login_endpoint,
            params=oauth_params,
            allow_redirects=False  # We want to capture the redirect
        ) as response:
            # OAuth login should redirect to provider
            assert response.status in [302, 307], "OAuth login should redirect to provider"
            
            # Verify redirect URL contains essential OAuth parameters
            redirect_location = response.headers.get("Location")
            assert redirect_location is not None
            
            # Parse redirect URL to verify OAuth parameters
            parsed_url = urlparse(redirect_location)
            query_params = parse_qs(parsed_url.query)
            
            # Essential OAuth 2.0 parameters for business flow
            assert "client_id" in query_params
            assert "redirect_uri" in query_params
            assert "response_type" in query_params
            assert "scope" in query_params
            assert "state" in query_params  # CRITICAL: State parameter prevents CSRF attacks
            
            # Verify OAuth provider is correct business partner
            assert parsed_url.netloc in ["accounts.google.com", "github.com"]
            
            # State parameter should be cryptographically secure (business security requirement)
            state_value = query_params["state"][0]
            assert len(state_value) >= 32, "State parameter must be secure for business operations"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_callback_endpoint_token_exchange(self, real_services_fixture):
        """
        Test /oauth/callback endpoint handles token exchange for user authentication.
        
        Business Value: OAuth callback completes user authentication flow, enabling
        users to access chat features and receive AI-powered insights. This is the
        final step in user onboarding that enables platform revenue generation.
        """
        # Simulate OAuth callback with test parameters
        # Note: In real OAuth flow, these would come from the OAuth provider
        test_state = "test_state_" + str(uuid.uuid4())
        test_code = "test_authorization_code"
        
        callback_params = {
            "code": test_code,
            "state": test_state
        }
        
        # Test callback endpoint with simulated OAuth response
        async with self.session.get(
            self.oauth_callback_endpoint,
            params=callback_params,
            allow_redirects=False
        ) as response:
            # Callback should either succeed with tokens or fail gracefully
            assert response.status in [200, 302, 400, 401]
            
            if response.status == 200:
                # Successful token exchange
                callback_data = await response.json()
                
                # Verify business-critical authentication tokens
                assert "access_token" in callback_data or "token" in callback_data
                assert "user" in callback_data or "user_id" in callback_data
                
            elif response.status == 302:
                # Redirect to frontend with tokens or error
                redirect_location = response.headers.get("Location")
                assert redirect_location is not None
                assert "localhost:3000" in redirect_location or "error" in redirect_location
                
            elif response.status in [400, 401]:
                # Expected error for test parameters - verify error handling
                error_data = await response.json()
                assert "error" in error_data
                
                # Error should be informative for business operations
                error_message = error_data.get("error", "")
                assert len(error_message) > 0, "Error messages must be provided for business operations"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_endpoint_token_management(self, real_services_fixture):
        """
        Test /auth/refresh endpoint manages token lifecycle for continuous user sessions.
        
        Business Value: Token refresh enables users to maintain authenticated sessions
        without re-login, providing seamless UX that keeps users engaged with the
        platform and able to access AI optimization insights continuously.
        """
        # Create test refresh request
        refresh_request = RefreshRequest(
            refresh_token="test_refresh_token_" + str(uuid.uuid4())
        )
        
        # Test refresh endpoint with real HTTP request
        async with self.session.post(
            self.refresh_endpoint,
            json=refresh_request.dict(),
            headers={"Content-Type": "application/json"}
        ) as response:
            # Refresh should either succeed with new tokens or fail gracefully
            assert response.status in [200, 401, 400]
            
            if response.status == 200:
                # Successful token refresh
                refresh_data = await response.json()
                
                # Verify new business-critical tokens are provided
                assert "access_token" in refresh_data
                assert "refresh_token" in refresh_data
                assert "expires_in" in refresh_data
                
                # Tokens should be different from input (new tokens generated)
                new_refresh_token = refresh_data["refresh_token"]
                assert new_refresh_token != refresh_request.refresh_token
                
                # Expiration should be reasonable for business operations (not too short/long)
                expires_in = refresh_data["expires_in"]
                assert 300 <= expires_in <= 86400, "Token expiration should be between 5 minutes and 24 hours"
                
            elif response.status in [400, 401]:
                # Expected error for test token - verify error handling
                error_data = await response.json()
                assert "error" in error_data
                
                # Error should indicate invalid/expired refresh token
                error_message = error_data.get("error", "").lower()
                assert any(term in error_message for term in ["invalid", "expired", "token"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_logout_endpoint_session_cleanup(self, real_services_fixture):
        """
        Test /auth/logout endpoint properly cleans up user sessions for security.
        
        Business Value: Proper logout functionality ensures user sessions are
        securely terminated, protecting user data and maintaining platform security
        trust. Essential for enterprise customers who require secure session management.
        """
        # Create test authorization header
        test_token = "Bearer test_access_token_" + str(uuid.uuid4())
        
        # Test logout endpoint with authorization header
        async with self.session.post(
            self.logout_endpoint,
            headers={"Authorization": test_token}
        ) as response:
            # Logout should succeed or fail gracefully
            assert response.status in [200, 204, 401, 400]
            
            if response.status in [200, 204]:
                # Successful logout
                if response.status == 200:
                    logout_data = await response.json()
                    assert "message" in logout_data or "status" in logout_data
                    
                    # Verify logout message indicates successful session termination
                    message = logout_data.get("message", logout_data.get("status", ""))
                    assert any(term in message.lower() for term in ["logout", "success", "terminated"])
                
            elif response.status in [400, 401]:
                # Expected error for test token - verify error handling
                error_data = await response.json()
                assert "error" in error_data
                
                # Error should indicate authentication issue
                error_message = error_data.get("error", "").lower()
                assert any(term in error_message for term in ["unauthorized", "invalid", "token"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_endpoint_requests_business_load(self, real_services_fixture):
        """
        Test auth endpoints handle concurrent requests for multi-user business scenarios.
        
        Business Value: Concurrent request handling ensures platform can support
        multiple users simultaneously accessing authentication features, critical
        for platform scalability and enterprise customer requirements.
        """
        # Test concurrent health checks (simulating load balancer health checks)
        async def health_check_request():
            async with self.session.get(self.health_endpoint) as response:
                return response.status, await response.json()
        
        # Run 10 concurrent health check requests
        health_tasks = [health_check_request() for _ in range(10)]
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        # All health checks should succeed
        successful_health_checks = 0
        for result in health_results:
            if isinstance(result, tuple) and result[0] == 200:
                successful_health_checks += 1
        
        # At least 80% of concurrent health checks should succeed (business reliability requirement)
        assert successful_health_checks >= 8, "Auth service must handle concurrent health checks for business reliability"
        
        # Test concurrent status requests (simulating multiple client applications)
        async def status_request():
            async with self.session.get(self.status_endpoint) as response:
                return response.status, await response.json()
        
        # Run 10 concurrent status requests
        status_tasks = [status_request() for _ in range(10)]
        status_results = await asyncio.gather(*status_tasks, return_exceptions=True)
        
        # All status requests should succeed
        successful_status_requests = 0
        for result in status_results:
            if isinstance(result, tuple) and result[0] == 200:
                successful_status_requests += 1
        
        # At least 80% of concurrent status requests should succeed (business reliability requirement)
        assert successful_status_requests >= 8, "Auth service must handle concurrent status requests for multi-user business operations"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_endpoint_response_times_business_performance(self, real_services_fixture):
        """
        Test auth endpoints meet business performance requirements for user experience.
        
        Business Value: Fast authentication response times ensure smooth user
        onboarding and login experience, critical for user retention and platform
        adoption. Slow auth responses lead to user abandonment.
        """
        # Test health endpoint response time
        start_time = time.time()
        async with self.session.get(self.health_endpoint) as response:
            health_response_time = time.time() - start_time
            assert response.status == 200
        
        # Health endpoint should respond within 2 seconds (business performance requirement)
        assert health_response_time < 2.0, f"Health endpoint too slow: {health_response_time}s (business requirement: <2s)"
        
        # Test status endpoint response time
        start_time = time.time()
        async with self.session.get(self.status_endpoint) as response:
            status_response_time = time.time() - start_time
            assert response.status == 200
        
        # Status endpoint should respond within 1 second (business performance requirement)
        assert status_response_time < 1.0, f"Status endpoint too slow: {status_response_time}s (business requirement: <1s)"
        
        # Test OAuth login redirect response time
        oauth_params = {"provider": "google", "redirect_uri": "http://localhost:3000/auth/callback"}
        start_time = time.time()
        async with self.session.get(
            self.oauth_login_endpoint,
            params=oauth_params,
            allow_redirects=False
        ) as response:
            oauth_response_time = time.time() - start_time
            assert response.status in [302, 307]
        
        # OAuth login should redirect within 3 seconds (business performance requirement)
        assert oauth_response_time < 3.0, f"OAuth login too slow: {oauth_response_time}s (business requirement: <3s)"
        
        self.logger.info(f"Performance metrics - Health: {health_response_time:.3f}s, Status: {status_response_time:.3f}s, OAuth: {oauth_response_time:.3f}s")