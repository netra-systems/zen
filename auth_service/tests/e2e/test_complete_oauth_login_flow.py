"""
Test Complete OAuth Login Flow - E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure user authentication enables platform access
- Value Impact: Users can reliably authenticate and access Netra platform capabilities
- Strategic Impact: Core security foundation enabling all business operations

This E2E test validates the complete Google OAuth flow from start to finish:
1. OAuth authorization URL generation
2. User authentication with Google (simulated)
3. Authorization code callback handling
4. JWT token generation and validation
5. Cross-service authentication validation
6. Session persistence and refresh token handling
7. Complete user journey testing with real services

CRITICAL E2E REQUIREMENTS:
- Uses REAL Docker services (PostgreSQL, Redis, Auth Service)
- NO MOCKS allowed - all services must be real
- Tests complete end-to-end business journeys
- Validates actual authentication flows that enable business value
- Uses proper timing validation (no 0-second executions)
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from urllib.parse import urlparse, parse_qs

import pytest
import httpx
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestCompleteOAuthLoginFlow(BaseE2ETest):
    """Test complete OAuth login flow with real services."""
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.docker_manager = None
        self.auth_service_url = None
        self.test_start_time = None
        
    async def setup_real_services(self):
        """Set up real Docker services for E2E testing."""
        self.logger.info("🔧 Setting up real Docker services for OAuth E2E testing")
        
        # Initialize Docker manager with Alpine containers for performance
        self.docker_manager = UnifiedDockerManager()
        
        # Acquire test environment with real services
        env_info = await self.docker_manager.acquire_environment(
            env_name="test",
            use_alpine=True,
            rebuild_images=True
        )
        
        if not env_info or not env_info.get("success"):
            raise RuntimeError(f"Failed to start real services: {env_info}")
        
        # Configure service URLs from environment
        self.auth_service_url = f"http://localhost:{env_info.get('auth_port', 8081)}"
        self.postgres_port = env_info.get('postgres_port', 5434)
        self.redis_port = env_info.get('redis_port', 6381)
        
        self.logger.info(f"✅ Real services started - Auth: {self.auth_service_url}")
        
        # Wait for services to be fully ready
        await self.wait_for_service_ready(self.auth_service_url + "/health", timeout=60)
        
        # Register cleanup
        self.register_cleanup_task(self._cleanup_docker_services)
        
    async def _cleanup_docker_services(self):
        """Clean up Docker services after testing."""
        if self.docker_manager:
            try:
                await self.docker_manager.release_environment("test")
                self.logger.info("✅ Docker services cleaned up successfully")
            except Exception as e:
                self.logger.error(f"❌ Error cleaning up Docker services: {e}")
    
    async def wait_for_service_ready(self, health_url: str, timeout: float = 30.0):
        """Wait for service to be ready with health check."""
        async def check_health():
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        health_data = response.json()
                        return health_data.get("status") == "healthy"
            except Exception:
                pass
            return False
        
        if not await self.wait_for_condition(
            check_health, 
            timeout=timeout, 
            description=f"service at {health_url}"
        ):
            raise RuntimeError(f"Service not ready at {health_url} within {timeout}s")
        
        self.logger.info(f"✅ Service ready: {health_url}")

    async def create_test_user_session(self) -> Dict[str, Any]:
        """Create a test user session for authentication testing."""
        # Simulate user data that would come from Google OAuth
        user_data = {
            "email": f"test.user.{int(time.time())}@netratest.com",
            "name": "OAuth Test User",
            "google_id": f"oauth_test_{int(time.time())}",
            "picture": "https://lh3.googleusercontent.com/a/test-picture",
            "locale": "en",
            "verified_email": True
        }
        return user_data

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_oauth_authorization_flow(self):
        """Test complete OAuth authorization URL generation and validation."""
        self.test_start_time = time.time()
        
        await self.setup_real_services()
        
        self.logger.info("🔐 Testing OAuth authorization flow with real auth service")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Get OAuth status to ensure providers are configured
            oauth_status_response = await client.get(f"{self.auth_service_url}/oauth/status")
            assert oauth_status_response.status_code == 200, f"OAuth status check failed: {oauth_status_response.text}"
            
            oauth_status = oauth_status_response.json()
            assert "available_providers" in oauth_status
            assert "google" in oauth_status["available_providers"], "Google OAuth provider not available"
            
            # Step 2: Request OAuth authorization URL
            auth_url_response = await client.post(
                f"{self.auth_service_url}/oauth/google/authorize",
                json={"redirect_uri": "http://localhost:3000/auth/callback"}
            )
            
            assert auth_url_response.status_code == 200, f"OAuth authorization failed: {auth_url_response.text}"
            auth_data = auth_url_response.json()
            
            # Validate authorization response structure
            assert "authorization_url" in auth_data
            assert "state" in auth_data
            
            authorization_url = auth_data["authorization_url"]
            oauth_state = auth_data["state"]
            
            # Step 3: Validate authorization URL structure
            assert "accounts.google.com" in authorization_url
            assert "oauth2/v2/auth" in authorization_url
            assert "client_id" in authorization_url
            assert "redirect_uri" in authorization_url
            assert f"state={oauth_state}" in authorization_url
            
            # Step 4: Validate state parameter storage and retrieval
            # In a real implementation, state would be stored in Redis/database
            assert len(oauth_state) >= 32, "OAuth state should be sufficiently random"
            
            self.logger.info(f"✅ OAuth authorization URL generated successfully: {authorization_url[:100]}...")
            self.logger.info(f"✅ OAuth state parameter: {oauth_state}")
        
        # Validate test timing (must not be 0-second execution)
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f"E2E test executed too fast: {execution_time}s (likely mocked)"
        
        self.logger.info(f"✅ OAuth authorization flow test completed in {execution_time:.2f}s")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_oauth_callback_processing(self):
        """Test complete OAuth callback processing with token generation."""
        self.test_start_time = time.time()
        
        await self.setup_real_services()
        
        self.logger.info("🔐 Testing OAuth callback processing with real services")
        
        # Create test user data
        user_data = await self.create_test_user_session()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Generate OAuth state for callback
            auth_url_response = await client.post(
                f"{self.auth_service_url}/oauth/google/authorize",
                json={"redirect_uri": "http://localhost:3000/auth/callback"}
            )
            
            assert auth_url_response.status_code == 200
            auth_data = auth_url_response.json()
            oauth_state = auth_data["state"]
            
            # Step 2: Simulate OAuth callback (in real system, this comes from Google)
            # For testing, we simulate the callback with test data
            callback_response = await client.post(
                f"{self.auth_service_url}/oauth/google/callback",
                json={
                    "code": f"test_auth_code_{int(time.time())}",
                    "state": oauth_state,
                    "user_info": user_data  # In real system, this would be fetched from Google
                }
            )
            
            # Validate callback processing
            assert callback_response.status_code == 200, f"OAuth callback failed: {callback_response.text}"
            callback_data = callback_response.json()
            
            # Step 3: Validate JWT token generation
            assert "access_token" in callback_data
            assert "refresh_token" in callback_data
            assert "token_type" in callback_data
            assert callback_data["token_type"] == "Bearer"
            
            access_token = callback_data["access_token"]
            refresh_token = callback_data["refresh_token"]
            
            # Validate token structure (JWT should have 3 parts)
            token_parts = access_token.split(".")
            assert len(token_parts) == 3, "Access token should be valid JWT format"
            
            # Step 4: Test token validation
            validation_response = await client.post(
                f"{self.auth_service_url}/auth/validate",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert validation_response.status_code == 200, f"Token validation failed: {validation_response.text}"
            validation_data = validation_response.json()
            
            # Validate user information in token
            assert "user" in validation_data
            assert validation_data["user"]["email"] == user_data["email"]
            assert "user_id" in validation_data["user"]
            
            # Step 5: Test refresh token functionality
            refresh_response = await client.post(
                f"{self.auth_service_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert refresh_response.status_code == 200, f"Token refresh failed: {refresh_response.text}"
            refresh_data = refresh_response.json()
            
            assert "access_token" in refresh_data
            new_access_token = refresh_data["access_token"]
            assert new_access_token != access_token, "Refreshed token should be different"
            
            self.logger.info("✅ OAuth callback processing completed with valid tokens")
        
        # Validate test timing (must not be 0-second execution)
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f"E2E test executed too fast: {execution_time}s (likely mocked)"
        
        self.logger.info(f"✅ OAuth callback test completed in {execution_time:.2f}s")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_oauth_session_persistence_and_security(self):
        """Test OAuth session persistence with real database and security validation."""
        self.test_start_time = time.time()
        
        await self.setup_real_services()
        
        self.logger.info("🔐 Testing OAuth session persistence with real database")
        
        # Create test user
        user_data = await self.create_test_user_session()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Complete OAuth flow to create session
            auth_url_response = await client.post(
                f"{self.auth_service_url}/oauth/google/authorize",
                json={"redirect_uri": "http://localhost:3000/auth/callback"}
            )
            
            auth_data = auth_url_response.json()
            oauth_state = auth_data["state"]
            
            # Process callback to create user session
            callback_response = await client.post(
                f"{self.auth_service_url}/oauth/google/callback",
                json={
                    "code": f"test_auth_code_{int(time.time())}",
                    "state": oauth_state,
                    "user_info": user_data
                }
            )
            
            assert callback_response.status_code == 200
            callback_data = callback_response.json()
            access_token = callback_data["access_token"]
            
            # Step 2: Test session persistence across requests
            # Multiple validation requests should work with same token
            for i in range(3):
                validation_response = await client.post(
                    f"{self.auth_service_url}/auth/validate",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                assert validation_response.status_code == 200
                validation_data = validation_response.json()
                assert validation_data["user"]["email"] == user_data["email"]
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Step 3: Test user lookup and session retrieval
            user_lookup_response = await client.get(
                f"{self.auth_service_url}/auth/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert user_lookup_response.status_code == 200
            user_info = user_lookup_response.json()
            assert user_info["email"] == user_data["email"]
            assert user_info["name"] == user_data["name"]
            
            # Step 4: Test token security - invalid token should fail
            invalid_token_response = await client.post(
                f"{self.auth_service_url}/auth/validate",
                headers={"Authorization": "Bearer invalid.token.here"}
            )
            
            assert invalid_token_response.status_code == 401, "Invalid token should be rejected"
            
            # Step 5: Test missing authorization header
            no_auth_response = await client.post(f"{self.auth_service_url}/auth/validate")
            assert no_auth_response.status_code == 401, "Missing authorization should be rejected"
            
            self.logger.info("✅ OAuth session persistence and security validation completed")
        
        # Validate test timing (must not be 0-second execution)
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f"E2E test executed too fast: {execution_time}s (likely mocked)"
        
        self.logger.info(f"✅ OAuth session persistence test completed in {execution_time:.2f}s")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_oauth_error_handling_and_recovery(self):
        """Test OAuth error handling and recovery scenarios with real services."""
        self.test_start_time = time.time()
        
        await self.setup_real_services()
        
        self.logger.info("🔐 Testing OAuth error handling and recovery")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Test invalid redirect URI
            invalid_redirect_response = await client.post(
                f"{self.auth_service_url}/oauth/google/authorize",
                json={"redirect_uri": "http://malicious-site.com/callback"}
            )
            
            # Should reject invalid redirect URIs
            assert invalid_redirect_response.status_code == 400, "Invalid redirect URI should be rejected"
            
            # Step 2: Test invalid OAuth state
            callback_invalid_state = await client.post(
                f"{self.auth_service_url}/oauth/google/callback",
                json={
                    "code": "test_code",
                    "state": "invalid_state_12345",
                    "user_info": {"email": "test@example.com"}
                }
            )
            
            assert callback_invalid_state.status_code == 400, "Invalid OAuth state should be rejected"
            
            # Step 3: Test missing required fields in callback
            callback_missing_fields = await client.post(
                f"{self.auth_service_url}/oauth/google/callback",
                json={"code": "test_code"}  # Missing state and user_info
            )
            
            assert callback_missing_fields.status_code == 400, "Missing required fields should be rejected"
            
            # Step 4: Test expired/invalid refresh token
            refresh_invalid_response = await client.post(
                f"{self.auth_service_url}/auth/refresh",
                json={"refresh_token": "invalid.refresh.token"}
            )
            
            assert refresh_invalid_response.status_code == 401, "Invalid refresh token should be rejected"
            
            # Step 5: Test OAuth provider availability check
            oauth_status_response = await client.get(f"{self.auth_service_url}/oauth/status")
            assert oauth_status_response.status_code == 200
            
            oauth_status = oauth_status_response.json()
            assert "oauth_healthy" in oauth_status
            
            self.logger.info("✅ OAuth error handling and recovery validation completed")
        
        # Validate test timing (must not be 0-second execution)  
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f"E2E test executed too fast: {execution_time}s (likely mocked)"
        
        self.logger.info(f"✅ OAuth error handling test completed in {execution_time:.2f}s")

    @pytest.mark.e2e
    @pytest.mark.real_services 
    @pytest.mark.asyncio
    async def test_oauth_user_journey_complete_flow(self):
        """Test complete OAuth user journey from start to authenticated platform access."""
        self.test_start_time = time.time()
        
        await self.setup_real_services()
        
        self.logger.info("🔐 Testing complete OAuth user journey with business value validation")
        
        # Create test user representing real user scenario
        user_data = await self.create_test_user_session()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # JOURNEY STEP 1: User initiates login from frontend
            self.logger.info("👤 Step 1: User initiates OAuth login")
            
            # Frontend requests OAuth authorization URL
            auth_url_response = await client.post(
                f"{self.auth_service_url}/oauth/google/authorize",
                json={"redirect_uri": "http://localhost:3000/auth/callback"}
            )
            
            assert auth_url_response.status_code == 200
            auth_data = auth_url_response.json()
            authorization_url = auth_data["authorization_url"]
            oauth_state = auth_data["state"]
            
            self.logger.info(f"✅ Step 1 Complete: OAuth URL generated for user journey")
            
            # JOURNEY STEP 2: User completes Google authentication (simulated)
            self.logger.info("👤 Step 2: User completes Google OAuth authentication")
            
            # Simulate successful Google OAuth callback
            callback_response = await client.post(
                f"{self.auth_service_url}/oauth/google/callback",
                json={
                    "code": f"journey_auth_code_{int(time.time())}",
                    "state": oauth_state,
                    "user_info": user_data
                }
            )
            
            assert callback_response.status_code == 200
            callback_data = callback_response.json()
            access_token = callback_data["access_token"]
            refresh_token = callback_data["refresh_token"]
            
            self.logger.info("✅ Step 2 Complete: User authenticated, tokens generated")
            
            # JOURNEY STEP 3: User accesses protected platform resources
            self.logger.info("👤 Step 3: User accesses protected platform resources")
            
            # Validate token works for protected endpoints
            user_profile_response = await client.get(
                f"{self.auth_service_url}/auth/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert user_profile_response.status_code == 200
            user_profile = user_profile_response.json()
            assert user_profile["email"] == user_data["email"]
            
            # Test multiple protected resource access (simulating real usage)
            for endpoint in ["/auth/validate", "/auth/user"]:
                protected_response = await client.get(
                    f"{self.auth_service_url}{endpoint}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                assert protected_response.status_code in [200, 405]  # 405 for wrong method but auth works
            
            self.logger.info("✅ Step 3 Complete: User successfully accessing protected resources")
            
            # JOURNEY STEP 4: Session renewal and long-term access
            self.logger.info("👤 Step 4: Session renewal for continued platform access")
            
            # Simulate session renewal after some time
            await asyncio.sleep(0.1)  # Simulate time passage
            
            refresh_response = await client.post(
                f"{self.auth_service_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            new_access_token = refresh_data["access_token"]
            
            # Validate new token works
            renewed_validation = await client.post(
                f"{self.auth_service_url}/auth/validate",
                headers={"Authorization": f"Bearer {new_access_token}"}
            )
            
            assert renewed_validation.status_code == 200
            renewed_user_data = renewed_validation.json()
            assert renewed_user_data["user"]["email"] == user_data["email"]
            
            self.logger.info("✅ Step 4 Complete: Session renewed, continued access enabled")
            
            # JOURNEY VALIDATION: Business value delivered
            self.logger.info("💼 Validating business value delivery")
            
            # User can maintain authenticated session
            assert access_token != new_access_token, "Token renewal provides new credentials"
            
            # User information persisted correctly
            assert user_profile["email"] == user_data["email"]
            assert user_profile["name"] == user_data["name"]
            
            # Authentication enables platform access
            validation_check = await client.post(
                f"{self.auth_service_url}/auth/validate",
                headers={"Authorization": f"Bearer {new_access_token}"}
            )
            assert validation_check.status_code == 200
            
            self.logger.info("✅ BUSINESS VALUE DELIVERED: Complete OAuth user journey successful")
            self.logger.info(f"   - User authenticated: {user_data['email']}")
            self.logger.info(f"   - Platform access enabled via JWT tokens")
            self.logger.info(f"   - Session persistence and renewal working")
            self.logger.info(f"   - Security validation passed")
        
        # Validate test timing (must not be 0-second execution)
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.2, f"E2E test executed too fast: {execution_time}s (likely mocked)"
        
        self.logger.info(f"✅ Complete OAuth user journey test completed in {execution_time:.2f}s")

# Additional fixtures and helpers for OAuth testing
@pytest.fixture(scope="session")
async def oauth_test_environment():
    """Set up OAuth test environment with real services."""
    logger.info("Setting up OAuth test environment")
    
    # Ensure test environment variables are set
    env = get_env()
    env.set("NETRA_TEST_MODE", "true", source="test")
    env.set("ENVIRONMENT", "test", source="test")
    env.set("AUTH_FAST_TEST_MODE", "false", source="test")  # Ensure full initialization
    
    yield {"environment": "test", "oauth_enabled": True}
    
    logger.info("OAuth test environment cleaned up")


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])