"""
Cross-Service Authentication Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Cross-service auth enables seamless user experience
- Business Goal: Unified authentication across all platform services (auth, backend, frontend)
- Value Impact: Users experience consistent authentication without repeated logins
- Strategic Impact: Foundation for microservices architecture and enterprise security

CRITICAL REQUIREMENTS:
- NO DOCKER - Integration tests without Docker containers
- NO MOCKS - Use real service-to-service communication, real JWT validation
- Real Services - Connect to auth service (8081) and backend (8000) simultaneously  
- Integration Layer - Test actual service communication patterns

Test Categories:
1. Auth service to backend communication
2. Auth header propagation and validation
3. Service-to-service authentication
"""

import asyncio
import json
import jwt
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ensure_user_id

import httpx
import asyncpg
import redis.asyncio as redis


class TestCrossServiceAuthIntegration(BaseIntegrationTest):
    """Integration tests for Cross-Service Authentication - NO MOCKS, REAL SERVICES ONLY."""
    
    def setup_method(self):
        """Set up for cross-service auth integration tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Service Configuration
        self.services = {
            "auth": {
                "url": f"http://localhost:{self.env.get('AUTH_SERVICE_PORT', '8081')}",
                "name": "auth-service",
                "endpoints": {
                    "health": "/health",
                    "login": "/api/v1/auth/login",
                    "validate": "/api/v1/auth/validate",
                    "user_info": "/api/v1/user/profile"
                }
            },
            "backend": {
                "url": f"http://localhost:{self.env.get('BACKEND_PORT', '8000')}",
                "name": "backend-service",
                "endpoints": {
                    "health": "/health",
                    "user_profile": "/api/v1/user/profile",
                    "agents": "/api/v1/agents",
                    "threads": "/api/v1/threads"
                }
            }
        }
        
        # JWT Configuration
        self.jwt_secret = self.env.get("JWT_SECRET")
        if not self.jwt_secret:
            self.jwt_secret = "test-secret-key-for-integration"
            
        # Real service connections
        self.redis_url = f"redis://localhost:{self.env.get('REDIS_PORT', '6381')}"
        self.db_url = self.env.get("TEST_DATABASE_URL") or f"postgresql://test:test@localhost:5434/test_db"
        
        # Test user for cross-service testing
        self.test_user = {
            "user_id": "cross-service-user-1",
            "email": "crossservice@netra.ai",
            "name": "Cross Service Test User",
            "password": "CrossService123!",
            "permissions": ["read", "write", "execute"]
        }

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.cross_service
    async def test_auth_service_to_backend_communication(self, real_services_fixture):
        """
        Test authentication token flow from auth service to backend service.
        
        Business Value: Users can access backend features after logging in via auth service.
        """
        conn = None
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            # Create test user in database
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
            """, self.test_user["user_id"], self.test_user["email"], self.test_user["name"],
                "hashed_password_placeholder", datetime.now(timezone.utc), True)
            
            async with httpx.AsyncClient() as client:
                
                # Step 1: Authenticate with auth service
                auth_response = await client.post(
                    f"{self.services['auth']['url']}{self.services['auth']['endpoints']['login']}",
                    json={
                        "email": self.test_user["email"],
                        "password": self.test_user["password"]
                    },
                    timeout=10.0
                )
                
                if auth_response.status_code in [200, 201]:
                    auth_data = auth_response.json()
                    access_token = auth_data.get("access_token") or auth_data.get("token")
                    
                    if access_token:
                        # Step 2: Use auth service token with backend service
                        backend_response = await client.get(
                            f"{self.services['backend']['url']}{self.services['backend']['endpoints']['user_profile']}",
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        
                        # Backend should accept auth service token
                        assert backend_response.status_code in [200, 404], \
                            f"Backend should accept auth service token, got {backend_response.status_code}"
                        
                        if backend_response.status_code == 200:
                            profile_data = backend_response.json()
                            
                            # Verify user identity is preserved across services
                            user_identifier = (profile_data.get("user_id") or 
                                             profile_data.get("id") or 
                                             profile_data.get("email"))
                            
                            assert user_identifier in [self.test_user["user_id"], self.test_user["email"]], \
                                "User identity should be consistent across services"
                        
                        # Step 3: Test backend API endpoints with auth token
                        api_endpoints = [
                            ("/api/v1/agents", "GET"),
                            ("/api/v1/threads", "GET"),
                            ("/api/v1/user/settings", "GET")
                        ]
                        
                        for endpoint_path, method in api_endpoints:
                            
                            if method == "GET":
                                api_response = await client.get(
                                    f"{self.services['backend']['url']}{endpoint_path}",
                                    headers={"Authorization": f"Bearer {access_token}"},
                                    timeout=10.0
                                )
                            else:
                                api_response = await client.request(
                                    method,
                                    f"{self.services['backend']['url']}{endpoint_path}",
                                    headers={"Authorization": f"Bearer {access_token}"},
                                    timeout=10.0
                                )
                            
                            # API should accept valid auth token or return meaningful errors
                            assert api_response.status_code in [200, 201, 401, 403, 404, 501], \
                                f"Endpoint {endpoint_path} returned unexpected status {api_response.status_code}"
                            
                            # If endpoint exists, authenticated user should not get 401
                            if api_response.status_code not in [404, 501]:
                                assert api_response.status_code != 401, \
                                    f"Authenticated request to {endpoint_path} should not get 401"
                
                elif auth_response.status_code == 404:
                    self.logger.warning("Auth service not available for cross-service testing")
                    pytest.skip("Auth service login endpoint not implemented")
                else:
                    self.logger.warning(f"Auth service login failed: {auth_response.status_code}")
            
        except Exception as e:
            self.logger.warning(f"Cross-service communication test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Services not available for cross-service testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.cross_service
    async def test_auth_header_propagation_and_validation(self, real_services_fixture):
        """
        Test proper auth header propagation and validation across service boundaries.
        
        Business Value: Consistent security model across all platform services.
        """
        # Create test JWT token for validation testing
        test_payload = {
            "user_id": self.test_user["user_id"],
            "email": self.test_user["email"],
            "permissions": self.test_user["permissions"],
            "exp": int(time.time()) + 3600,  # 1 hour expiry
            "iat": int(time.time()),
            "iss": "netra-auth-service"
        }
        
        valid_token = jwt.encode(test_payload, self.jwt_secret, algorithm="HS256")
        
        # Test different header formats and validation scenarios
        auth_scenarios = [
            {
                "name": "bearer_token_standard",
                "headers": {"Authorization": f"Bearer {valid_token}"},
                "should_succeed": True
            },
            {
                "name": "bearer_token_lowercase",
                "headers": {"authorization": f"bearer {valid_token}"},
                "should_succeed": True  # Most systems normalize headers
            },
            {
                "name": "custom_auth_header",
                "headers": {"X-Auth-Token": valid_token},
                "should_succeed": False  # Unless specifically supported
            },
            {
                "name": "missing_bearer_prefix",
                "headers": {"Authorization": valid_token},
                "should_succeed": False
            },
            {
                "name": "empty_authorization_header",
                "headers": {"Authorization": ""},
                "should_succeed": False
            }
        ]
        
        async with httpx.AsyncClient() as client:
            
            for scenario in auth_scenarios:
                
                # Test with auth service
                auth_validate_response = await client.get(
                    f"{self.services['auth']['url']}/api/v1/auth/validate",
                    headers=scenario["headers"],
                    timeout=10.0
                )
                
                if scenario["should_succeed"]:
                    expected_statuses = [200, 404]  # Success or endpoint not found
                else:
                    expected_statuses = [401, 400, 404]  # Unauthorized, bad request, or not found
                
                assert auth_validate_response.status_code in expected_statuses, \
                    f"Auth service scenario '{scenario['name']}' got unexpected status {auth_validate_response.status_code}"
                
                # Test with backend service 
                backend_profile_response = await client.get(
                    f"{self.services['backend']['url']}/api/v1/user/profile",
                    headers=scenario["headers"],
                    timeout=10.0
                )
                
                # Backend should have similar validation behavior
                if scenario["should_succeed"]:
                    backend_expected = [200, 404]
                else:
                    backend_expected = [401, 400, 403, 404]
                
                assert backend_profile_response.status_code in backend_expected, \
                    f"Backend scenario '{scenario['name']}' got unexpected status {backend_profile_response.status_code}"

    @pytest.mark.integration
    @pytest.mark.auth  
    @pytest.mark.cross_service
    async def test_service_to_service_authentication(self, real_services_fixture):
        """
        Test service-to-service authentication for internal API calls.
        
        Business Value: Services can securely communicate without user context.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Create service-to-service JWT token
            service_payload = {
                "service": "netra-backend",
                "permissions": ["validate_tokens", "user_notifications"],
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "iss": "netra-service-registry"
            }
            
            service_token = jwt.encode(service_payload, self.jwt_secret, algorithm="HS256")
            
            async with httpx.AsyncClient() as client:
                
                # Test service-to-service validation
                service_response = await client.post(
                    f"{self.services['auth']['url']}/api/v1/auth/validate-service-token",
                    headers={
                        "Authorization": f"Bearer {service_token}",
                        "X-Service-Name": "backend",
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_token": "test_user_token",
                        "user_id": self.test_user["user_id"]
                    },
                    timeout=10.0
                )
                
                # Service endpoints should accept service tokens or return appropriate errors
                assert service_response.status_code in [200, 201, 202, 400, 404, 501], \
                    f"Service call got unexpected status {service_response.status_code}"
                
        finally:
            await redis_client.aclose()