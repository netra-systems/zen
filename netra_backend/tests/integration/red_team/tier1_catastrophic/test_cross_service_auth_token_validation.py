from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
RED TEAM TEST 1: Cross-Service Auth Token Validation

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real integration issues.
This test validates that tokens from auth service are properly validated by the backend service.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Security, Trust, Platform Stability
- Value Impact: Critical auth failures directly impact user access and platform trust
- Strategic Impact: Core security foundation for all customer interactions

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real authentication integration gaps)
"""

import asyncio
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
import jwt as pyjwt
import pytest
import redis.asyncio as redis
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.database import get_db_session
from netra_backend.app.services.user_auth_service import UserAuthService
from netra_backend.app.redis_manager import RedisManager


class TestCrossServiceAuthTokenValidation:
    """
    RED TEAM TEST 1: Cross-Service Authentication Token Validation
    
    Tests the critical path of token exchange between auth service and backend.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_redis_connection(self):
        """Real Redis connection for testing - will fail if Redis not available."""
        config = get_unified_config()
        
        # Use REAL Redis connection - no mocks
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.database,
            decode_responses=True,
            username=config.redis.username or "",
            password=config.redis.password or "",
            socket_connect_timeout=10,
            socket_timeout=5
        )
        
        try:
            # Test real connection - will fail if Redis unavailable
            await redis_client.ping()
            yield redis_client
        except Exception as e:
            pytest.fail(f"CRITICAL: Real Redis connection failed: {e}")
        finally:
            await redis_client.close()

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        # Use REAL application instance
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_01_auth_service_token_generation_fails(self, real_redis_connection, real_database_session):
        """
        Test 1A: Auth Service Token Generation (EXPECTED TO FAIL)
        
        Tests that the auth service can generate valid JWT tokens.
        This will likely FAIL because:
        1. Auth service may not be running
        2. JWT secrets may not be configured
        3. Token generation logic may be incomplete
        """
        # Try to connect to REAL auth service
        auth_service_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:8001")
        
        async with httpx.AsyncClient() as client:
            try:
                # Test auth service health - will fail if service not running
                health_response = await client.get(f"{auth_service_url}/health")
                assert health_response.status_code == 200, "Auth service must be running for this test"
                
                # Mock OAuth callback to get token from REAL auth service
                oauth_callback_data = {
                    "code": f"test_oauth_code_{secrets.token_urlsafe(16)}",
                    "state": secrets.token_urlsafe(32)
                }
                
                # This will likely FAIL - auth service may not handle this properly
                token_response = await client.post(
                    f"{auth_service_url}/auth/callback/google",
                    json=oauth_callback_data
                )
                
                # FAILURE EXPECTED HERE
                assert token_response.status_code == 200, f"Auth service token generation failed: {token_response.text}"
                
                token_data = token_response.json()
                assert "access_token" in token_data, "Auth service must return access_token"
                assert "refresh_token" in token_data, "Auth service must return refresh_token"
                
                # Validate JWT structure - will likely fail
                access_token = token_data["access_token"]
                decoded_token = pyjwt.decode(access_token, options={"verify_signature": False})
                
                assert "user_id" in decoded_token, "Token must contain user_id claim"
                assert "email" in decoded_token, "Token must contain email claim"
                assert "exp" in decoded_token, "Token must contain expiration claim"
                
            except httpx.ConnectError:
                pytest.fail("CRITICAL FAILURE: Auth service is not running - cannot test token validation")
            except Exception as e:
                pytest.fail(f"Auth service token generation failed: {e}")

    @pytest.mark.asyncio
    async def test_02_backend_token_validation_fails(self, real_test_client, real_database_session):
        """
        Test 1B: Backend Token Validation (EXPECTED TO FAIL)
        
        Tests that the backend can validate tokens from auth service.
        This will likely FAIL because:
        1. JWT validation logic may be incomplete
        2. Secret keys may not match between services
        3. Token validation middleware may not be working
        """
        # Generate a test JWT token (simulating auth service)
        test_payload = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "iss": "auth-service",
            "aud": "netra-backend"
        }
        
        # Use test JWT secret - will likely fail if secrets don't match
        jwt_secret = get_env().get("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        test_token = pyjwt.encode(test_payload, jwt_secret, algorithm="HS256")
        
        # Try to access protected endpoint with token - will likely fail
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Test various protected endpoints
        protected_endpoints = [
            "/api/threads",
            "/api/user/profile", 
            "/api/agents",
            "/health/detailed"
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = real_test_client.get(endpoint, headers=auth_headers)
                
                # FAILURE EXPECTED HERE
                assert response.status_code != 401, f"Token validation failed for {endpoint}: {response.text}"
                assert response.status_code != 403, f"Token authorization failed for {endpoint}: {response.text}"
                
            except Exception as e:
                pytest.fail(f"Backend token validation failed for {endpoint}: {e}")

    @pytest.mark.asyncio
    async def test_03_token_expiration_handling_fails(self, real_test_client):
        """
        Test 1C: Expired Token Handling (EXPECTED TO FAIL)
        
        Tests that expired tokens are properly rejected.
        Will likely FAIL because expiration validation may not be implemented.
        """
        # Create an expired token
        expired_payload = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
            "iss": "auth-service",
            "aud": "netra-backend"
        }
        
        jwt_secret = get_env().get("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        expired_token = pyjwt.encode(expired_payload, jwt_secret, algorithm="HS256")
        
        auth_headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Try to access protected endpoint with expired token
        response = real_test_client.get("/api/threads", headers=auth_headers)
        
        # FAILURE EXPECTED HERE - expired tokens should be rejected
        assert response.status_code == 401, f"Expired token was accepted (should be rejected): {response.text}"
        
        error_data = response.json()
        assert "expired" in error_data.get("detail", "").lower(), "Error should mention token expiration"

    @pytest.mark.asyncio
    async def test_04_malformed_token_handling_fails(self, real_test_client):
        """
        Test 1D: Malformed Token Handling (EXPECTED TO FAIL)
        
        Tests that malformed tokens are properly rejected.
        Will likely FAIL because malformed token validation may not be robust.
        """
        malformed_tokens = [
            "malformed.token.here",
            "Bearer.invalid.token",
            "not-a-jwt-at-all",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            None
        ]
        
        for malformed_token in malformed_tokens:
            if malformed_token is None:
                headers = {}
            else:
                headers = {"Authorization": f"Bearer {malformed_token}"}
                
            response = real_test_client.get("/api/threads", headers=headers)
            
            # FAILURE EXPECTED HERE - malformed tokens should be rejected
            assert response.status_code == 401, f"Malformed token '{malformed_token}' was accepted: {response.text}"

    @pytest.mark.asyncio
    async def test_05_cross_service_jwt_secret_consistency_fails(self, real_redis_connection, real_database_session):
        """
        Test 1E: JWT Secret Consistency Between Services (EXPECTED TO FAIL)
        
        Tests that auth service and backend use the same JWT secrets.
        Will likely FAIL because secrets may not be synchronized.
        """
        # Try to get JWT secrets from both services
        auth_service_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:8001")
        backend_url = get_env().get("BACKEND_URL", "http://localhost:8000")
        
        # Create test token with known secret
        test_secret = "consistent-test-secret-key-123456789"
        test_payload = {
            "user_id": "test-user-123",
            "email": "test@example.com", 
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        test_token = pyjwt.encode(test_payload, test_secret, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            try:
                # Test if auth service can validate this token
                auth_validation_response = await client.post(
                    f"{auth_service_url}/auth/validate",
                    headers={"Authorization": f"Bearer {test_token}"}
                )
                
                # Test if backend can validate the same token  
                backend_validation_response = await client.get(
                    f"{backend_url}/health/detailed",
                    headers={"Authorization": f"Bearer {test_token}"}
                )
                
                # FAILURE EXPECTED HERE - services likely use different secrets
                assert auth_validation_response.status_code == backend_validation_response.status_code, \
                    f"Services handle same token differently: auth={auth_validation_response.status_code}, backend={backend_validation_response.status_code}"
                    
            except httpx.ConnectError as e:
                pytest.fail(f"Service connection failed - cannot test secret consistency: {e}")

    @pytest.mark.asyncio
    async def test_06_token_user_context_propagation_fails(self, real_test_client, real_database_session):
        """
        Test 1F: User Context Propagation (EXPECTED TO FAIL)
        
        Tests that user context from token is properly propagated to business logic.
        Will likely FAIL because context propagation may not be implemented.
        """
        # Create token with specific user context
        user_context = {
            "user_id": str(uuid.uuid4()),
            "email": "context-test@example.com",
            "role": "premium_user",
            "organization_id": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        jwt_secret = get_env().get("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        context_token = pyjwt.encode(user_context, jwt_secret, algorithm="HS256")
        
        auth_headers = {"Authorization": f"Bearer {context_token}"}
        
        # Try to create a thread (should use user context)
        thread_data = {
            "title": "Test Thread for Context Propagation",
            "description": "Testing user context propagation"
        }
        
        response = real_test_client.post("/api/threads", json=thread_data, headers=auth_headers)
        
        # FAILURE EXPECTED HERE - user context may not be propagated
        if response.status_code == 200:
            thread_response = response.json()
            
            # Verify user context was used
            assert thread_response.get("user_id") == user_context["user_id"], \
                "User ID from token not propagated to thread creation"
            assert thread_response.get("organization_id") == user_context["organization_id"], \
                "Organization ID from token not propagated to thread creation"
        else:
            pytest.fail(f"Thread creation failed with valid token: {response.text}")

    @pytest.mark.asyncio
    async def test_07_concurrent_token_validation_fails(self, real_test_client):
        """
        Test 1G: Concurrent Token Validation Load (EXPECTED TO FAIL)
        
        Tests that token validation can handle concurrent requests.
        Will likely FAIL because validation may not be thread-safe or may have performance issues.
        """
        # Create multiple test tokens
        tokens = []
        jwt_secret = get_env().get("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        
        for i in range(20):
            payload = {
                "user_id": f"concurrent-user-{i}",
                "email": f"concurrent{i}@example.com",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time())
            }
            token = pyjwt.encode(payload, jwt_secret, algorithm="HS256")
            tokens.append(token)

        async def validate_token(token: str) -> tuple:
            """Validate a single token and return result."""
            headers = {"Authorization": f"Bearer {token}"}
            response = real_test_client.get("/api/threads", headers=headers)
            return (response.status_code, token[:20])

        # Run concurrent validations
        tasks = [validate_token(token) for token in tokens]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # FAILURE EXPECTED HERE - concurrent validation may fail
        successful_validations = 0
        failed_validations = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_validations.append(f"Exception: {result}")
            else:
                status_code, token_prefix = result
                if status_code in [200, 201]:
                    successful_validations += 1
                else:
                    failed_validations.append(f"Status {status_code} for token {token_prefix}")
        
        # At least 90% should succeed for this to pass
        success_rate = successful_validations / len(tokens)
        assert success_rate >= 0.9, f"Concurrent validation failed: {success_rate*100:.1f}% success rate. Failures: {failed_validations[:5]}"

    @pytest.mark.asyncio
    async def test_08_token_refresh_integration_fails(self, real_redis_connection):
        """
        Test 1H: Token Refresh Integration (EXPECTED TO FAIL)
        
        Tests that token refresh works between auth service and backend.
        Will likely FAIL because refresh token logic may not be implemented.
        """
        auth_service_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:8001")
        
        # Store a refresh token in Redis (simulating auth service)
        refresh_token = secrets.token_urlsafe(64)
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "refresh-test@example.com",
            "issued_at": int(time.time())
        }
        
        # Store refresh token data in Redis
        await real_redis_connection.set(
            f"refresh_token:{refresh_token}",
            json.dumps(user_data),
            ex=7 * 24 * 3600  # 7 days
        )
        
        async with httpx.AsyncClient() as client:
            try:
                # Try to refresh token using auth service
                refresh_response = await client.post(
                    f"{auth_service_url}/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                # FAILURE EXPECTED HERE - refresh endpoint may not exist
                assert refresh_response.status_code == 200, f"Token refresh failed: {refresh_response.text}"
                
                refresh_data = refresh_response.json()
                assert "access_token" in refresh_data, "Refresh response must contain new access_token"
                
                # Verify new token works with backend
                new_token = refresh_data["access_token"]
                auth_headers = {"Authorization": f"Bearer {new_token}"}
                
                backend_response = TestClient(app).get("/api/threads", headers=auth_headers)
                assert backend_response.status_code != 401, "Refreshed token not accepted by backend"
                
            except httpx.ConnectError:
                pytest.fail("Auth service not available for refresh token test")

# Additional helper class for token testing utilities
class RedTeamTokenTestUtils:
    """Utility methods for Red Team token testing."""
    
    @staticmethod
    def generate_test_jwt(payload: Dict[str, Any], secret: str = None) -> str:
        """Generate a test JWT token."""
        if secret is None:
            secret = get_env().get("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        
        default_payload = {
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "iss": "auth-service",
            "aud": "netra-backend"
        }
        default_payload.update(payload)
        
        return pyjwt.encode(default_payload, secret, algorithm="HS256")
    
    @staticmethod
    async def verify_redis_connection(redis_client) -> bool:
        """Verify Redis connection is working."""
        try:
            await redis_client.ping()
            return True
        except Exception:
            return False
    
    @staticmethod 
    async def verify_database_connection(db_session) -> bool:
        """Verify database connection is working."""
        try:
            await db_session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
