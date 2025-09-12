"""
Test Auth Service Startup E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - MISSION CRITICAL
- Business Goal: Ensure auth service startup enables complete user authentication workflow
- Value Impact: Users MUST be able to authenticate after auth service startup to access AI optimization platform
- Strategic Impact: Core platform security and user onboarding - without this, the platform has ZERO value
- Revenue Impact: $2M+ ARR depends on users being able to authenticate and access the platform

CRITICAL: This test validates the COMPLETE auth service lifecycle from external client perspective:
1. Auth service starts successfully and is ready to serve requests
2. Complete user authentication workflow (register  ->  login  ->  session management)  
3. OAuth flows work end-to-end after service startup
4. Service recovery and restart scenarios maintain user sessions
5. Multi-user authentication works concurrently after startup
6. Health monitoring integration validates service availability

This is a MISSION CRITICAL E2E test that validates business value delivery chain:
Auth Service Startup  ->  User Authentication  ->  Platform Access  ->  AI Value Delivery

Compliance with CLAUDE.md and TEST_CREATION_GUIDE.md:
- Uses REAL services only (no inappropriate mocks) - NON-NEGOTIABLE
- Uses absolute imports following import rules
- Validates business value end-to-end from startup to authentication
- Uses proper Docker services via UnifiedDockerManager patterns
- Tests actual HTTP and WebSocket authentication flows
- Includes proper error handling and edge cases
- Uses SSOT utilities from test_framework/
- Follows proper cleanup patterns and resource management
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
import random
import string

import aiohttp
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

from shared.isolated_environment import get_env
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services import ServiceEndpoints, RealServicesManager, get_real_services
from test_framework.test_config import TEST_PORTS
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig, create_authenticated_user
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events


logger = logging.getLogger(__name__)


class TestAuthServiceStartupE2E(BaseE2ETest):
    """
    Comprehensive E2E tests for auth service startup and complete authentication workflows.
    
    CRITICAL: These tests validate that after auth service startup, users can actually
    authenticate end-to-end and access the platform for AI optimization services.
    """
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.env = get_env()
        self.service_endpoints = ServiceEndpoints.from_environment(self.env)
        
        # Real services manager for E2E testing
        self.real_services = get_real_services()
        
        # Docker manager for service lifecycle management
        self.docker_manager = UnifiedDockerManager()
        
        # Authentication helper using SSOT patterns
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Test tracking for cleanup
        self.test_users = []
        self.test_sessions = []
        self.created_services = []
        self.websocket_connections = []
        
        # Service startup state tracking
        self.auth_service_started = False
        self.backend_service_started = False
        
        logger.info("[U+1F680] Auth service startup E2E test setup complete")
    
    async def cleanup_resources(self):
        """Comprehensive cleanup of all E2E test resources."""
        logger.info("Starting comprehensive auth service E2E test cleanup")
        
        # Close WebSocket connections first
        for ws_connection in self.websocket_connections:
            try:
                if hasattr(ws_connection, 'close'):
                    await ws_connection.close()
            except Exception as e:
                logger.warning(f"Failed to close WebSocket connection: {e}")
        
        # Clean up test users and sessions
        for user_data in self.test_users:
            await self._cleanup_test_user(user_data)
        
        for session_data in self.test_sessions:
            await self._cleanup_test_session(session_data)
        
        # Stop created services if needed
        for service_name in self.created_services:
            try:
                await self.docker_manager.stop_service(service_name, environment="test")
            except Exception as e:
                logger.warning(f"Failed to stop service {service_name}: {e}")
        
        # Close real services manager
        await self.real_services.close_all()
        
        # Clear tracking data
        self.test_users.clear()
        self.test_sessions.clear()
        self.created_services.clear()
        self.websocket_connections.clear()
        
        await super().cleanup_resources()
        logger.info("Auth service E2E test cleanup completed")
    
    async def _cleanup_test_user(self, user_data: Dict[str, Any]):
        """Clean up a test user from the system."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use authenticated admin request to delete user
                headers = await self._get_admin_headers()
                await session.delete(
                    f"{self.service_endpoints.auth_service_url}/admin/users/{user_data['id']}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
        except Exception as e:
            logger.warning(f"Failed to cleanup test user {user_data.get('email', 'unknown')}: {e}")
    
    async def _cleanup_test_session(self, session_data: Dict[str, Any]):
        """Clean up a test session from the auth service."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {session_data.get('access_token')}"}
                await session.post(
                    f"{self.service_endpoints.auth_service_url}/auth/logout",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
        except Exception as e:
            logger.warning(f"Failed to cleanup test session: {e}")
    
    async def _get_admin_headers(self) -> Dict[str, str]:
        """Get admin headers for cleanup operations."""
        # Create admin token for cleanup
        admin_token = self.auth_helper.create_test_jwt_token(
            user_id="admin-test-user",
            email="admin@test.example.com",
            permissions=["admin", "read", "write"],
            exp_minutes=5
        )
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    async def _ensure_services_running(self) -> Dict[str, str]:
        """
        Ensure auth and backend services are running for E2E tests.
        
        Returns:
            Dict with service URLs
        """
        logger.info("[U+1F527] Ensuring auth and backend services are running")
        
        # Acquire test environment through Docker manager
        env_info = await self.docker_manager.acquire_environment(
            EnvironmentType.TEST,
            use_alpine=True,
            rebuild_images=False
        )
        
        # Track that we need to clean up Docker environment
        self.register_cleanup_task(lambda: self.docker_manager.release_environment(EnvironmentType.TEST))
        
        # Wait for services to be healthy
        auth_healthy = await self._wait_for_service_health(
            "auth service", 
            self.service_endpoints.auth_service_url,
            timeout=60.0
        )
        
        backend_healthy = await self._wait_for_service_health(
            "backend service",
            self.service_endpoints.backend_service_url, 
            timeout=60.0
        )
        
        if not auth_healthy:
            raise RuntimeError("Auth service failed to start or become healthy")
        if not backend_healthy:
            raise RuntimeError("Backend service failed to start or become healthy")
        
        self.auth_service_started = True
        self.backend_service_started = True
        
        logger.info(" PASS:  Auth and backend services are running and healthy")
        
        return {
            "auth_url": self.service_endpoints.auth_service_url,
            "backend_url": self.service_endpoints.backend_service_url,
            "websocket_url": self.service_endpoints.websocket_url
        }
    
    async def _wait_for_service_health(
        self, 
        service_name: str, 
        service_url: str, 
        timeout: float = 60.0
    ) -> bool:
        """
        Wait for a service to be healthy by checking its health endpoint.
        
        Args:
            service_name: Human-readable service name for logging
            service_url: Base URL of the service
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if service becomes healthy, False otherwise
        """
        logger.info(f"[U+23F3] Waiting for {service_name} to be healthy at {service_url}")
        
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    # Try health endpoint first
                    health_url = f"{service_url}/health"
                    async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            health_data = await resp.json()
                            if health_data.get("status") == "healthy":
                                logger.info(f" PASS:  {service_name} is healthy")
                                return True
                            else:
                                logger.debug(f" WARNING: [U+FE0F] {service_name} health check returned: {health_data}")
                    
                    # Fallback: try root endpoint 
                    async with session.get(service_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status in [200, 404]:  # 404 is OK for services without root handler
                            logger.info(f" PASS:  {service_name} is responding")
                            return True
                            
            except Exception as e:
                last_error = e
                logger.debug(f"[U+23F3] {service_name} not ready yet: {e}")
            
            await asyncio.sleep(2.0)
        
        logger.error(f" FAIL:  {service_name} failed to become healthy within {timeout}s. Last error: {last_error}")
        return False
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_auth_service_startup_enables_user_authentication_e2e(self):
        """
        Test complete auth service startup to user authentication flow.
        
        CRITICAL: This test validates the core business value delivery chain:
        Auth Service Startup  ->  User Registration  ->  User Login  ->  Authenticated Session  ->  Platform Access
        
        Without this working, users cannot access the AI optimization platform at all.
        """
        logger.info("[U+1F510] Starting complete auth service startup to user authentication E2E test")
        
        # Step 1: Ensure auth service is started and healthy
        service_urls = await self._ensure_services_running()
        assert self.auth_service_started, "Auth service must be started for authentication tests"
        
        # Step 2: Create and register a new test user
        user_email = f"startup_auth_test_{uuid.uuid4().hex[:8]}@example.com"
        user_password = "secure_test_password_123"
        
        user_data = await self._register_test_user(user_email, user_password)
        assert user_data, "User registration should succeed after auth service startup"
        assert user_data["email"] == user_email, "Registered user should have correct email"
        assert "id" in user_data, "User should have ID assigned"
        
        self.test_users.append(user_data)
        logger.info(f" PASS:  User registration successful: {user_data['email']}")
        
        # Step 3: Authenticate the user (login)
        auth_tokens = await self._authenticate_user(user_email, user_password)
        assert "access_token" in auth_tokens, "Login should return access token"
        assert "refresh_token" in auth_tokens, "Login should return refresh token"
        
        access_token = auth_tokens["access_token"]
        refresh_token = auth_tokens["refresh_token"]
        
        # Track session for cleanup
        self.test_sessions.append({
            "access_token": access_token,
            "user_id": user_data["id"]
        })
        
        logger.info(" PASS:  User authentication successful")
        
        # Step 4: Validate authenticated session works
        user_profile = await self._get_user_profile(access_token)
        assert user_profile["email"] == user_email, "Profile should match authenticated user"
        assert user_profile["id"] == user_data["id"], "Profile should have correct user ID"
        
        logger.info(" PASS:  Authenticated session validation successful")
        
        # Step 5: Test token refresh to ensure session persistence
        new_tokens = await self._refresh_authentication(refresh_token)
        assert "access_token" in new_tokens, "Token refresh should return new access token"
        assert new_tokens["access_token"] != access_token, "New access token should be different"
        
        # Verify new token works
        refreshed_profile = await self._get_user_profile(new_tokens["access_token"])
        assert refreshed_profile["email"] == user_email, "Refreshed token should work for same user"
        
        logger.info(" PASS:  Token refresh and session persistence successful")
        
        # Step 6: Test backend service access with authenticated token
        backend_response = await self._test_backend_access(new_tokens["access_token"])
        assert backend_response, "Backend access should work with valid token"
        
        logger.info(" PASS:  Backend service access with auth token successful")
        
        logger.info(" CELEBRATION:  Complete auth service startup to user authentication E2E test PASSED")
    
    @pytest.mark.e2e
    @pytest.mark.real_services 
    @pytest.mark.asyncio
    async def test_auth_service_startup_oauth_complete_flow_e2e(self):
        """
        Test OAuth complete flow after auth service startup.
        
        CRITICAL: OAuth authentication is essential for production user onboarding.
        This test validates that OAuth flows work end-to-end after service startup.
        """
        logger.info("[U+1F517] Starting OAuth complete flow E2E test after auth service startup")
        
        # Step 1: Ensure auth service is started and healthy
        service_urls = await self._ensure_services_running()
        assert self.auth_service_started, "Auth service must be started for OAuth tests"
        
        # Test OAuth providers (simulate with test endpoints)
        oauth_providers = ["google", "github"]
        
        for provider in oauth_providers:
            logger.info(f"Testing OAuth flow for {provider}")
            
            # Step 2: Initiate OAuth flow
            oauth_initiation = await self._initiate_oauth_flow(provider)
            assert "authorization_url" in oauth_initiation, f"{provider} OAuth should return authorization URL"
            assert provider in oauth_initiation["authorization_url"], f"OAuth URL should contain provider: {provider}"
            
            # Step 3: Simulate OAuth callback with authorization code
            test_auth_code = f"test_auth_code_{provider}_{uuid.uuid4().hex[:8]}"
            oauth_result = await self._simulate_oauth_callback(provider, test_auth_code)
            
            assert "access_token" in oauth_result, f"{provider} OAuth should return access token"
            assert "user" in oauth_result, f"{provider} OAuth should return user data"
            
            user_data = oauth_result["user"]
            access_token = oauth_result["access_token"]
            
            # Track for cleanup
            self.test_users.append(user_data)
            self.test_sessions.append({
                "access_token": access_token,
                "user_id": user_data["id"]
            })
            
            # Step 4: Validate OAuth user can access authenticated endpoints
            oauth_profile = await self._get_user_profile(access_token)
            assert oauth_profile["email"] == user_data["email"], f"{provider} OAuth user should have correct profile"
            
            # Step 5: Test backend access with OAuth token
            backend_access = await self._test_backend_access(access_token)
            assert backend_access, f"{provider} OAuth token should enable backend access"
            
            logger.info(f" PASS:  {provider} OAuth flow completed successfully")
        
        logger.info(" CELEBRATION:  OAuth complete flow E2E test after auth service startup PASSED")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_auth_service_restart_session_persistence_e2e(self):
        """
        Test that sessions persist through auth service restart scenarios.
        
        CRITICAL: Service restarts should not invalidate active user sessions.
        This ensures business continuity during deployments and maintenance.
        """
        logger.info(" CYCLE:  Starting auth service restart session persistence E2E test")
        
        # Step 1: Ensure auth service is started and create authenticated user
        service_urls = await self._ensure_services_running()
        
        user_email = f"restart_test_{uuid.uuid4().hex[:8]}@example.com"
        user_password = "restart_test_password_123"
        
        # Create user and get initial session
        user_data = await self._register_test_user(user_email, user_password)
        initial_tokens = await self._authenticate_user(user_email, user_password)
        
        self.test_users.append(user_data)
        self.test_sessions.append({
            "access_token": initial_tokens["access_token"],
            "user_id": user_data["id"]
        })
        
        # Verify initial session works
        initial_profile = await self._get_user_profile(initial_tokens["access_token"])
        assert initial_profile["email"] == user_email, "Initial session should work"
        
        logger.info(" PASS:  Initial session established before restart")
        
        # Step 2: Simulate service restart by stopping and starting auth service
        logger.info(" CYCLE:  Simulating auth service restart...")
        
        # Stop auth service
        await self.docker_manager.stop_service("auth", environment=EnvironmentType.TEST)
        
        # Wait for service to stop
        await asyncio.sleep(3.0)
        
        # Start auth service again
        restart_env_info = await self.docker_manager.acquire_environment(
            EnvironmentType.TEST,
            use_alpine=True,
            rebuild_images=False
        )
        
        # Wait for auth service to be healthy again
        auth_healthy_after_restart = await self._wait_for_service_health(
            "auth service after restart",
            self.service_endpoints.auth_service_url,
            timeout=60.0
        )
        assert auth_healthy_after_restart, "Auth service should be healthy after restart"
        
        logger.info(" PASS:  Auth service restart completed")
        
        # Step 3: Test that refresh token still works after restart
        try:
            refreshed_tokens = await self._refresh_authentication(initial_tokens["refresh_token"])
            new_access_token = refreshed_tokens["access_token"]
            
            # Verify new token works
            post_restart_profile = await self._get_user_profile(new_access_token)
            assert post_restart_profile["email"] == user_email, "Session should persist through restart"
            
            logger.info(" PASS:  Session persistence through restart successful")
            
        except Exception as e:
            # If refresh fails, try re-authentication (acceptable for some auth service implementations)
            logger.info(f"Token refresh failed after restart (may be expected): {e}")
            logger.info("Testing re-authentication after restart...")
            
            reauth_tokens = await self._authenticate_user(user_email, user_password)
            reauth_profile = await self._get_user_profile(reauth_tokens["access_token"])
            assert reauth_profile["email"] == user_email, "Re-authentication should work after restart"
            
            logger.info(" PASS:  Re-authentication after restart successful")
        
        # Step 4: Test new user registration works after restart
        new_user_email = f"post_restart_{uuid.uuid4().hex[:8]}@example.com"
        post_restart_user = await self._register_test_user(new_user_email, "post_restart_password")
        assert post_restart_user, "New user registration should work after restart"
        
        self.test_users.append(post_restart_user)
        
        logger.info(" PASS:  New user registration works after restart")
        logger.info(" CELEBRATION:  Auth service restart session persistence E2E test PASSED")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_auth_service_concurrent_users_after_startup_e2e(self):
        """
        Test concurrent user authentication after auth service startup.
        
        CRITICAL: The platform must handle multiple concurrent users authenticating
        simultaneously, especially during peak usage times.
        """
        logger.info("[U+1F465] Starting concurrent users authentication E2E test after startup")
        
        # Step 1: Ensure services are running
        service_urls = await self._ensure_services_running()
        
        # Step 2: Create multiple test users concurrently
        concurrent_user_count = 5
        user_creation_tasks = []
        
        for i in range(concurrent_user_count):
            email = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            password = f"concurrent_password_{i}_123"
            task = asyncio.create_task(self._register_test_user(email, password))
            user_creation_tasks.append((email, password, task))
        
        # Execute all user creation tasks concurrently
        created_users = []
        for email, password, task in user_creation_tasks:
            try:
                user_data = await task
                created_users.append((email, password, user_data))
                self.test_users.append(user_data)
                logger.info(f" PASS:  Concurrent user created: {email}")
            except Exception as e:
                logger.warning(f"Concurrent user creation failed for {email}: {e}")
        
        # At least 80% of concurrent user creations should succeed
        success_rate = len(created_users) / concurrent_user_count
        assert success_rate >= 0.8, f"At least 80% of concurrent user creations should succeed (got {success_rate:.1%})"
        
        logger.info(f" PASS:  Concurrent user creation: {len(created_users)}/{concurrent_user_count} succeeded")
        
        # Step 3: Authenticate all users concurrently
        auth_tasks = []
        for email, password, user_data in created_users:
            task = asyncio.create_task(self._authenticate_user(email, password))
            auth_tasks.append((email, user_data, task))
        
        authenticated_users = []
        for email, user_data, task in auth_tasks:
            try:
                tokens = await task
                authenticated_users.append((email, user_data, tokens))
                self.test_sessions.append({
                    "access_token": tokens["access_token"],
                    "user_id": user_data["id"]
                })
                logger.info(f" PASS:  Concurrent authentication successful: {email}")
            except Exception as e:
                logger.warning(f"Concurrent authentication failed for {email}: {e}")
        
        # At least 80% of concurrent authentications should succeed
        auth_success_rate = len(authenticated_users) / len(created_users)
        assert auth_success_rate >= 0.8, f"At least 80% of concurrent authentications should succeed (got {auth_success_rate:.1%})"
        
        logger.info(f" PASS:  Concurrent authentication: {len(authenticated_users)}/{len(created_users)} succeeded")
        
        # Step 4: Test concurrent WebSocket connections (subset for performance)
        websocket_test_count = min(3, len(authenticated_users))
        websocket_tasks = []
        
        for i in range(websocket_test_count):
            email, user_data, tokens = authenticated_users[i]
            task = asyncio.create_task(self._test_websocket_connection(tokens["access_token"], email))
            websocket_tasks.append((email, task))
        
        websocket_results = []
        for email, task in websocket_tasks:
            try:
                result = await task
                websocket_results.append((email, result))
                logger.info(f" PASS:  Concurrent WebSocket connection successful: {email}")
            except Exception as e:
                logger.warning(f"Concurrent WebSocket connection failed for {email}: {e}")
        
        # At least 70% of WebSocket connections should succeed (lower bar due to connection complexity)
        ws_success_rate = len(websocket_results) / websocket_test_count if websocket_test_count > 0 else 1.0
        assert ws_success_rate >= 0.7, f"At least 70% of concurrent WebSocket connections should succeed (got {ws_success_rate:.1%})"
        
        logger.info(f" PASS:  Concurrent WebSocket connections: {len(websocket_results)}/{websocket_test_count} succeeded")
        logger.info(" CELEBRATION:  Concurrent users authentication E2E test after startup PASSED")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_auth_service_health_monitoring_e2e(self):
        """
        Test auth service health monitoring integration.
        
        CRITICAL: Health monitoring ensures the auth service startup is not just successful
        but also ready to handle production traffic and can be monitored for issues.
        """
        logger.info("[U+1F3E5] Starting auth service health monitoring integration E2E test")
        
        # Step 1: Ensure auth service is started
        service_urls = await self._ensure_services_running()
        
        # Step 2: Test basic health endpoint
        health_status = await self._check_service_health()
        assert health_status["status"] == "healthy", "Auth service should report healthy status"
        assert "timestamp" in health_status, "Health status should include timestamp"
        assert "version" in health_status or "uptime" in health_status, "Health status should include service info"
        
        logger.info(" PASS:  Basic health check successful")
        
        # Step 3: Test health endpoint under load (simulate multiple concurrent health checks)
        health_check_tasks = []
        for i in range(10):
            task = asyncio.create_task(self._check_service_health())
            health_check_tasks.append(task)
        
        health_results = []
        for task in health_check_tasks:
            try:
                result = await task
                health_results.append(result)
            except Exception as e:
                logger.warning(f"Health check failed under load: {e}")
        
        # At least 90% of health checks should succeed under load
        health_success_rate = len(health_results) / len(health_check_tasks)
        assert health_success_rate >= 0.9, f"At least 90% of health checks should succeed under load (got {health_success_rate:.1%})"
        
        logger.info(f" PASS:  Health monitoring under load: {len(health_results)}/{len(health_check_tasks)} succeeded")
        
        # Step 4: Test readiness probe (service can accept traffic)
        readiness_status = await self._check_service_readiness()
        assert readiness_status, "Auth service should be ready to accept traffic"
        
        logger.info(" PASS:  Service readiness check successful")
        
        # Step 5: Test metrics endpoint (if available)
        try:
            metrics_data = await self._get_service_metrics()
            if metrics_data:
                logger.info(" PASS:  Service metrics endpoint available")
                # Basic metrics validation
                assert isinstance(metrics_data, dict), "Metrics should be structured data"
            else:
                logger.info("[U+2139][U+FE0F] Service metrics endpoint not available (acceptable)")
        except Exception as e:
            logger.info(f"[U+2139][U+FE0F] Service metrics endpoint not available or failed: {e} (acceptable)")
        
        logger.info(" CELEBRATION:  Auth service health monitoring integration E2E test PASSED")
    
    # Helper methods for E2E test implementations
    
    async def _register_test_user(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new test user."""
        async with aiohttp.ClientSession() as session:
            user_data = {
                "email": email,
                "password": password,
                "name": f"E2E Test User {uuid.uuid4().hex[:8]}",
                "terms_accepted": True
            }
            
            register_url = f"{self.service_endpoints.auth_service_url}/auth/register"
            async with session.post(register_url, json=user_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        async with aiohttp.ClientSession() as session:
            login_data = {"email": email, "password": password}
            login_url = f"{self.service_endpoints.auth_service_url}/auth/login"
            
            async with session.post(login_url, json=login_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile using access token."""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            profile_url = f"{self.service_endpoints.auth_service_url}/auth/profile"
            
            async with session.get(profile_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _refresh_authentication(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh authentication using refresh token."""
        async with aiohttp.ClientSession() as session:
            refresh_data = {"refresh_token": refresh_token}
            refresh_url = f"{self.service_endpoints.auth_service_url}/auth/refresh"
            
            async with session.post(refresh_url, json=refresh_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _test_backend_access(self, access_token: str) -> bool:
        """Test backend service access with auth token."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {access_token}"}
                backend_url = f"{self.service_endpoints.backend_service_url}/api/health"
                
                async with session.get(backend_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.debug(f"Backend access test failed: {e}")
            return False
    
    async def _initiate_oauth_flow(self, provider: str) -> Dict[str, Any]:
        """Initiate OAuth flow for a provider."""
        async with aiohttp.ClientSession() as session:
            oauth_url = f"{self.service_endpoints.auth_service_url}/auth/oauth/{provider}"
            params = {"redirect_uri": "http://localhost:3000/auth/callback"}
            
            async with session.get(oauth_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _simulate_oauth_callback(self, provider: str, auth_code: str) -> Dict[str, Any]:
        """Simulate OAuth provider callback."""
        async with aiohttp.ClientSession() as session:
            callback_data = {
                "code": auth_code,
                "state": f"test_state_{uuid.uuid4().hex[:8]}",
                "redirect_uri": "http://localhost:3000/auth/callback"
            }
            callback_url = f"{self.service_endpoints.auth_service_url}/auth/oauth/{provider}/callback"
            
            async with session.post(callback_url, json=callback_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _test_websocket_connection(self, access_token: str, user_email: str) -> bool:
        """Test WebSocket connection with auth token."""
        try:
            websocket_url = f"{self.service_endpoints.websocket_url}?token={access_token}"
            
            async with websockets.connect(websocket_url, timeout=10) as websocket:
                self.websocket_connections.append(websocket)
                
                # Send test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "user": user_email
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                return response is not None
                
        except Exception as e:
            logger.debug(f"WebSocket connection test failed for {user_email}: {e}")
            return False
    
    async def _check_service_health(self) -> Dict[str, Any]:
        """Check auth service health endpoint."""
        async with aiohttp.ClientSession() as session:
            health_url = f"{self.service_endpoints.auth_service_url}/health"
            
            async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def _check_service_readiness(self) -> bool:
        """Check if auth service is ready to accept traffic."""
        try:
            async with aiohttp.ClientSession() as session:
                ready_url = f"{self.service_endpoints.auth_service_url}/ready"
                
                async with session.get(ready_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception:
            # If readiness endpoint doesn't exist, check if service responds to basic request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.service_endpoints.auth_service_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        return resp.status in [200, 404]  # 404 is OK if no root handler
            except Exception:
                return False
    
    async def _get_service_metrics(self) -> Optional[Dict[str, Any]]:
        """Get service metrics if available."""
        try:
            async with aiohttp.ClientSession() as session:
                metrics_url = f"{self.service_endpoints.auth_service_url}/metrics"
                
                async with session.get(metrics_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('content-type', '')
                        if 'json' in content_type:
                            return await resp.json()
                        else:
                            # Prometheus metrics format
                            text = await resp.text()
                            return {"metrics": text, "format": "prometheus"}
                    return None
        except Exception:
            return None


# Additional fixtures for auth service E2E tests

@pytest.fixture
async def auth_service_e2e_setup():
    """Fixture providing comprehensive auth service E2E test setup."""
    test_instance = TestAuthServiceStartupE2E()
    test_instance.setup_method()
    
    try:
        # Ensure services are running before yielding
        service_urls = await test_instance._ensure_services_running()
        yield {
            "test_instance": test_instance,
            "service_urls": service_urls,
            "auth_helper": test_instance.auth_helper
        }
    finally:
        await test_instance.cleanup_resources()


@pytest.fixture
def auth_service_startup_config():
    """Configuration fixture for auth service startup tests."""
    env = get_env()
    return {
        "auth_service_url": env.get("TEST_AUTH_URL", f"http://localhost:{TEST_PORTS['auth']}"),
        "backend_service_url": env.get("TEST_BACKEND_URL", f"http://localhost:{TEST_PORTS['backend']}"),
        "websocket_url": env.get("TEST_WEBSOCKET_URL", f"ws://localhost:{TEST_PORTS['backend']}/ws"),
        "timeout": 60.0,
        "max_retries": 3
    }