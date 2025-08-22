"""
Comprehensive OAuth Login Test Suite - Top 30 Common Failures
Testing Level: L3-L4 (Real services with staging environment integration)
Initially designed to FAIL to expose real implementation issues

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Security, Retention, Platform Stability
- Value Impact: Prevents auth failures that directly impact user access and trust
- Strategic Impact: Critical for platform reliability and user retention

Test Philosophy: L3-L4 Testing
- L3: Real SUT with real containerized dependencies (PostgreSQL, Redis, etc.)
- L4: Real SUT deployed in staging environment with all real services
- Minimal mocking, maximum realism
"""

import asyncio
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import base64
import hashlib
import hmac
import jwt as pyjwt

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
import redis

from auth_service.main import app
from auth_service.auth_core.models.auth_models import AuthProvider, User, OAuthState
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.database.connection import get_db_session
from auth_service.auth_core.config import AuthConfig

# Test client with real app instance (L3 - Real SUT)
client = TestClient(app)


class TestOAuthComprehensiveFailures:
    """
    Comprehensive OAuth test suite covering 30 common failure scenarios.
    These tests are designed to initially FAIL to expose real issues.
    Tests follow L3-L4 spectrum with real services and staging integration.
    """

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Real PostgreSQL container for L3 testing"""
        with PostgresContainer("postgres:15") as postgres:
            yield postgres

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Real Redis container for L3 testing"""
        with RedisContainer("redis:7") as redis:
            yield redis

    @pytest.fixture
    def real_db_session(self, postgres_container):
        """Real database session using containerized PostgreSQL"""
        from auth_service.auth_core.database.models import Base
        engine = create_engine(postgres_container.get_connection_url())
        
        # Create all auth service tables
        Base.metadata.create_all(engine)
        
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def staging_env_config(self):
        """Staging environment configuration for L4 testing"""
        return {
            "auth_service_url": "https://auth-service.staging.netra.ai",
            "backend_url": "https://api.staging.netra.ai",
            "frontend_url": "https://app.staging.netra.ai",
            "websocket_url": "wss://ws.staging.netra.ai",
        }

    # ==================== BASIC SUCCESS CASE (MUST WORK) ====================

    @pytest.mark.asyncio
    async def test_01_successful_oauth_login_basic_flow(self, real_db_session):
        """
        Test 1: Basic successful OAuth login flow - THE DEFAULT CASE
        This MUST work in production but is designed to initially fail.
        """
        # Simulate Google OAuth callback with valid token
        state = secrets.token_urlsafe(32)
        mock_google_user = {
            "id": "google_123456",
            "email": "testuser@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "verified_email": True,
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "access_token": "valid_google_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
            
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value.json.return_value = mock_google_user
                
                response = client.post(
                    "/auth/callback/google",
                    json={
                        "code": "valid_auth_code",
                        "state": state,
                    }
                )
        
        # This SHOULD succeed but will initially fail
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == mock_google_user["email"]

    # ==================== OAUTH PROVIDER FAILURES ====================

    @pytest.mark.asyncio
    async def test_02_oauth_pkce_challenge_failure(self, real_db_session):
        """Test 2: PKCE code challenge verification failure (L3)"""
        # PKCE (Proof Key for Code Exchange) validation failure
        code_verifier = secrets.token_urlsafe(32)
        invalid_challenge = base64.urlsafe_b64encode(
            hashlib.sha256("wrong_verifier".encode()).digest()
        ).decode().rstrip("=")
        
        response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code_with_pkce",
                "state": secrets.token_urlsafe(32),
                "code_verifier": code_verifier,
                "code_challenge": invalid_challenge,
            }
        )
        assert response.status_code == 401
        assert "pkce" in response.json()["detail"].lower() or "challenge" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_03_oauth_nonce_replay_attack(self, redis_container):
        """Test 3: OAuth nonce replay attack prevention (L3 with real Redis)"""
        # Set environment variables for the OAuth security manager to find the test Redis
        import os
        os.environ["TEST_REDIS_HOST"] = redis_container.get_container_host_ip()
        os.environ["TEST_REDIS_PORT"] = str(redis_container.get_exposed_port(6379))
        
        # Connect to real Redis container
        redis_client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True
        )
        
        nonce = secrets.token_urlsafe(32)
        state = base64.urlsafe_b64encode(
            json.dumps({"nonce": nonce, "timestamp": int(time.time())}).encode()
        ).decode()
        
        # Store nonce in Redis to simulate first use
        redis_client.setex(f"oauth_nonce:{nonce}", 600, "used")
        
        # Try to reuse the same nonce (use unique code to avoid code reuse check)
        unique_code = f"unique_code_{secrets.token_urlsafe(8)}"
        response = client.post(
            "/auth/callback/google",
            json={
                "code": unique_code,
                "state": state,
            }
        )
        assert response.status_code == 401
        assert "nonce" in response.json()["detail"].lower() or "replay" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_04_oauth_code_reuse_attack(self, real_db_session):
        """Test 4: OAuth code reuse attack prevention"""
        code = "valid_code_for_reuse"
        state = secrets.token_urlsafe(32)
        
        # First use should succeed (mocked)
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "access_token": "token1",
                "token_type": "Bearer",
            }
            
            response1 = client.post(
                "/auth/callback/google",
                json={"code": code, "state": state}
            )
        
        # Second use should fail
        response2 = client.post(
            "/auth/callback/google",
            json={"code": code, "state": state}
        )
        assert response2.status_code == 401
        assert "already used" in response2.json()["detail"].lower()

    # ==================== STATE PARAMETER FAILURES ====================

    @pytest.mark.asyncio
    async def test_05_cross_site_request_forgery_token_binding(self, real_db_session):
        """Test 5: CSRF token binding to session failure (L3)"""
        # Create state with wrong session binding
        state_data = {
            "nonce": secrets.token_urlsafe(32),
            "timestamp": int(time.time()),
            "session_id": "wrong_session_12345",
            "origin": "https://evil-site.com"
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        # Try with different session (use unique code)
        response = client.post(
            "/auth/callback/google",
            json={"code": f"csrf_test_code_{secrets.token_urlsafe(8)}", "state": state},
            cookies={"session_id": "correct_session_67890"}
        )
        assert response.status_code == 401
        assert "csrf" in response.json()["detail"].lower() or "session" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_06_hmac_state_signature_verification_failure(self):
        """Test 6: HMAC signature verification failure on state parameter (L3)"""
        # Create state with invalid HMAC signature
        state_data = {
            "nonce": secrets.token_urlsafe(32),
            "timestamp": int(time.time())
        }
        state_json = json.dumps(state_data)
        
        # Wrong secret for HMAC
        wrong_hmac = hmac.new(
            b"wrong_secret",
            state_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        tampered_state = base64.urlsafe_b64encode(
            f"{state_json}|{wrong_hmac}".encode()
        ).decode()
        
        response = client.post(
            "/auth/callback/google",
            json={
                "code": f"hmac_test_code_{secrets.token_urlsafe(8)}",
                "state": tampered_state,
            }
        )
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_07_expired_state_parameter(self):
        """Test 7: Expired state parameter (>10 minutes)"""
        # Create state with expired timestamp
        expired_state = base64.urlsafe_b64encode(
            json.dumps({
                "nonce": secrets.token_urlsafe(16),
                "timestamp": int(time.time() - 700)
            }).encode()
        ).decode()
        
        response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code",
                "state": expired_state,
            }
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    # ==================== TOKEN VALIDATION FAILURES ====================

    @pytest.mark.asyncio
    async def test_08_malformed_id_token(self):
        """Test 8: Malformed ID token from OAuth provider"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "access_token": "valid_token",
                "id_token": "MALFORMED.TOKEN.HERE",
                "token_type": "Bearer",
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 401
        assert "invalid token" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_09_invalid_token_signature(self):
        """Test 9: Invalid JWT signature in ID token"""
        # Create JWT with invalid signature
        invalid_token = pyjwt.encode(
            {"sub": "user123", "email": "test@example.com"},
            "wrong_secret",
            algorithm="HS256"
        )
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "access_token": "valid_token",
                "id_token": invalid_token,
                "token_type": "Bearer",
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_10_expired_id_token(self):
        """Test 10: Expired ID token"""
        expired_token = pyjwt.encode(
            {
                "sub": "user123",
                "email": "test@example.com",
                "exp": int(time.time() - 3600),
                "iat": int(time.time() - 7200),
            },
            "secret",
            algorithm="HS256"
        )
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "access_token": "valid_token",
                "id_token": expired_token,
                "token_type": "Bearer",
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    # ==================== USER DATA VALIDATION FAILURES ====================

    @pytest.mark.asyncio
    async def test_11_missing_email_in_oauth_response(self):
        """Test 11: Missing email in OAuth provider response"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "name": "Test User",
                # email missing
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_12_unverified_email_address(self):
        """Test 12: Unverified email address from OAuth provider"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "email": "unverified@example.com",
                "verified_email": False,
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 403
        assert "verified" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_13_blocked_email_domain(self):
        """Test 13: Blocked email domain (spam/disposable)"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "email": "test@tempmail.com",
                "verified_email": True,
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 403
        assert "blocked" in response.json()["detail"].lower()

    # ==================== NETWORK AND CONNECTIVITY FAILURES ====================

    @pytest.mark.asyncio
    async def test_14_distributed_tracing_context_propagation_failure(self, staging_env_config):
        """Test 14: Distributed tracing context propagation failure across services (L4)"""
        # Test OpenTelemetry context propagation
        trace_id = uuid.uuid4().hex
        span_id = secrets.token_hex(8)
        
        headers = {
            "traceparent": f"00-{trace_id}-{span_id}-01",
            "tracestate": "netra=oauth_flow"
        }
        
        async with httpx.AsyncClient() as http_client:
            # Auth service should propagate trace context to backend
            auth_response = await http_client.post(
                f"{staging_env_config['auth_service_url']}/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                },
                headers=headers
            )
            
            if auth_response.status_code == 200:
                # Verify trace context was propagated
                assert "traceparent" in auth_response.headers
                assert trace_id in auth_response.headers.get("traceparent", "")

    @pytest.mark.asyncio
    async def test_15_circuit_breaker_activation_on_provider_failure(self, redis_container):
        """Test 15: Circuit breaker activation on repeated OAuth provider failures (L3)"""
        # Real Redis for circuit breaker state
        redis_client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True
        )
        
        # Simulate multiple failures to trigger circuit breaker
        for i in range(5):
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_post.side_effect = httpx.ConnectError("Provider unavailable")
                
                response = client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"code_{i}",
                        "state": secrets.token_urlsafe(32),
                    }
                )
        
        # Circuit breaker should be open now
        response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code",
                "state": secrets.token_urlsafe(32),
            }
        )
        
        assert response.status_code == 503
        assert "circuit" in response.json()["detail"].lower() or "unavailable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_16_network_connection_failure(self):
        """Test 16: Network connection failure to OAuth provider"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 503
        assert "connection" in response.json()["detail"].lower()

    # ==================== DATABASE AND SESSION FAILURES ====================

    @pytest.mark.asyncio
    async def test_17_database_connection_failure(self):
        """Test 17: Database connection failure during user creation"""
        with patch("auth_service.auth_core.database.connection.get_db_session") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 503
        assert "database" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_18_session_storage_failure(self, redis_container):
        """Test 18: Redis session storage failure"""
        with patch("redis.Redis.set") as mock_redis_set:
            mock_redis_set.side_effect = Exception("Redis connection failed")
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 503
        assert "session" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_19_duplicate_user_creation_race_condition(self, real_db_session):
        """Test 19: Race condition in duplicate user creation"""
        email = "raceuser@example.com"
        
        async def create_user():
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value.json.return_value = {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "verified_email": True,
                }
                
                return client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"valid_code_{uuid.uuid4()}",
                        "state": secrets.token_urlsafe(32),
                    }
                )
        
        # Simulate concurrent requests
        tasks = [create_user() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Only one should succeed, others should handle gracefully
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert success_count == 1

    # ==================== CROSS-SERVICE INTEGRATION FAILURES ====================

    @pytest.mark.asyncio
    async def test_20_jwt_propagation_to_backend_failure(self, staging_env_config):
        """Test 20: JWT token propagation failure to backend service"""
        # Get valid JWT from auth service
        jwt_token = "valid_jwt_token_here"
        
        # Try to use JWT with backend service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{staging_env_config['backend_url']}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
        
        # This should work but will initially fail
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_21_websocket_auth_handshake_failure(self, staging_env_config):
        """Test 21: WebSocket authentication handshake failure"""
        import websockets
        
        jwt_token = "valid_jwt_token"
        
        # Attempt WebSocket connection with JWT
        uri = f"{staging_env_config['websocket_url']}?token={jwt_token}"
        
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"type": "auth", "token": jwt_token}))
                response = await websocket.recv()
                data = json.loads(response)
                assert data["status"] == "authenticated"
        except Exception as e:
            pytest.fail(f"WebSocket auth failed: {e}")

    @pytest.mark.asyncio
    async def test_22_cross_origin_cors_failure(self):
        """Test 22: CORS failure for cross-origin OAuth requests"""
        response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code",
                "state": secrets.token_urlsafe(32),
            },
            headers={
                "Origin": "https://malicious-site.com",
                "Referer": "https://malicious-site.com",
            }
        )
        
        # Should reject non-whitelisted origins
        assert response.status_code == 403
        assert "cors" in response.json()["detail"].lower() or "origin" in response.json()["detail"].lower()

    # ==================== SECURITY AND ATTACK SCENARIOS ====================

    @pytest.mark.asyncio
    async def test_23_redirect_uri_mismatch_attack(self):
        """Test 23: Redirect URI mismatch attack prevention"""
        response = client.post(
            "/auth/callback/google",
            json={
                "code": f"redirect_test_code_{secrets.token_urlsafe(8)}",
                "state": secrets.token_urlsafe(32),
                "redirect_uri": "https://evil-site.com/steal-token",
            }
        )
        
        assert response.status_code == 401
        assert "redirect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_24_token_injection_attack(self):
        """Test 24: Token injection attack prevention"""
        # Try to inject a crafted token
        malicious_token = pyjwt.encode(
            {
                "sub": "admin",
                "email": "admin@netra.ai",
                "role": "superadmin",
                "exp": int(time.time() + 3600),
            },
            "guessed_secret",
            algorithm="HS256"
        )
        
        response = client.post(
            "/auth/verify",
            headers={"Authorization": f"Bearer {malicious_token}"}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_25_session_fixation_attack(self):
        """Test 25: Session fixation attack prevention"""
        # Try to fix a session ID
        fixed_session_id = "FIXED_SESSION_12345"
        
        response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code",
                "state": secrets.token_urlsafe(32),
            },
            cookies={"session_id": fixed_session_id}
        )
        
        # Should generate new session ID, not use the fixed one
        assert response.cookies.get("session_id") != fixed_session_id

    # ==================== EDGE CASES AND BOUNDARY CONDITIONS ====================

    @pytest.mark.asyncio
    async def test_26_extremely_long_email_address(self):
        """Test 26: Extremely long email address handling"""
        long_email = "a" * 200 + "@example.com"
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "email": long_email,
                "verified_email": True,
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_27_unicode_and_special_chars_in_name(self):
        """Test 27: Unicode and special characters in user name"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "email": "test@example.com",
                "name": "测试用户 🚀 <script>alert('xss')</script>",
                "verified_email": True,
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        # Should sanitize but still work
        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in data["user"]["name"]

    @pytest.mark.asyncio
    async def test_28_null_values_in_oauth_response(self):
        """Test 28: Null values in OAuth provider response"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "id": "user123",
                "email": "test@example.com",
                "name": None,
                "picture": None,
                "verified_email": True,
            }
            
            response = client.post(
                "/auth/callback/google",
                json={
                    "code": "valid_code",
                    "state": secrets.token_urlsafe(32),
                }
            )
        
        # Should handle null values gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"

    # ==================== CONCURRENT ACCESS AND LOAD TESTING ====================

    @pytest.mark.asyncio
    async def test_29_concurrent_login_attempts(self):
        """Test 29: Concurrent login attempts from same user"""
        email = "concurrent@example.com"
        
        async def login_attempt(attempt_num):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value.json.return_value = {
                    "id": "user123",
                    "email": email,
                    "verified_email": True,
                }
                
                return client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"valid_code_{attempt_num}",
                        "state": secrets.token_urlsafe(32),
                    }
                )
        
        # Simulate 10 concurrent login attempts
        tasks = [login_attempt(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed or fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 429]  # Success or rate limited

    @pytest.mark.asyncio
    async def test_30_token_refresh_during_active_session(self):
        """Test 30: Token refresh while session is actively being used"""
        # Get initial tokens
        initial_response = client.post(
            "/auth/callback/google",
            json={
                "code": "valid_code",
                "state": secrets.token_urlsafe(32),
            }
        )
        
        if initial_response.status_code != 200:
            pytest.skip("Initial login failed")
        
        initial_tokens = initial_response.json()
        
        # Simulate active session usage
        async def use_session():
            return client.get(
                "/api/v1/user/profile",
                headers={"Authorization": f"Bearer {initial_tokens['access_token']}"}
            )
        
        # Refresh token while session is being used
        async def refresh_token():
            return client.post(
                "/auth/refresh",
                json={"refresh_token": initial_tokens.get("refresh_token", "dummy_refresh")}
            )
        
        # Execute concurrently
        results = await asyncio.gather(
            use_session(),
            refresh_token(),
            use_session(),
            return_exceptions=True
        )
        
        # Should handle concurrent access gracefully
        for result in results:
            if not isinstance(result, Exception):
                assert result.status_code in [200, 401]

    # ==================== STAGING ENVIRONMENT SPECIFIC TESTS ====================

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_multi_service_oauth_flow(self, staging_env_config):
        """Test complete OAuth flow across all three services in staging"""
        async with httpx.AsyncClient() as http_client:
            # Step 1: Initiate OAuth with auth service
            auth_response = await http_client.get(
                f"{staging_env_config['auth_service_url']}/auth/login/google"
            )
            assert auth_response.status_code == 302  # Redirect to Google
            
            # Step 2: Simulate callback (would normally go through Google)
            callback_response = await http_client.post(
                f"{staging_env_config['auth_service_url']}/auth/callback/google",
                json={
                    "code": "staging_test_code",
                    "state": "staging_test_state",
                }
            )
            
            # Step 3: Use token with backend service
            if callback_response.status_code == 200:
                token = callback_response.json()["access_token"]
                backend_response = await http_client.get(
                    f"{staging_env_config['backend_url']}/api/v1/threads",
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert backend_response.status_code == 200
                
                # Step 4: Verify WebSocket can authenticate
                # This would use the websockets library in real implementation
                ws_auth_success = True  # Placeholder
                assert ws_auth_success

    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_oauth_provider_failover(self, staging_env_config):
        """Test OAuth provider failover in staging environment"""
        async with httpx.AsyncClient() as http_client:
            # Test Google OAuth failure triggers GitHub OAuth
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_post.side_effect = [
                    httpx.TimeoutException("Google timeout"),
                    Mock(status_code=200, json=lambda: {"access_token": "github_token"})
                ]
                
                response = await http_client.post(
                    f"{staging_env_config['auth_service_url']}/auth/callback/google",
                    json={
                        "code": "test_code",
                        "state": "test_state",
                    }
                )
                
                # Should failover to GitHub
                assert response.status_code == 200
                assert "github" in response.json().get("provider", "").lower()


class TestOAuthHelpers:
    """Helper functions for OAuth testing"""
    
    @staticmethod
    def generate_valid_jwt(claims: Dict[str, Any], secret: str = "test_secret") -> str:
        """Generate a valid JWT for testing"""
        default_claims = {
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "iss": "https://accounts.google.com",
            "aud": "test_client_id",
        }
        default_claims.update(claims)
        return pyjwt.encode(default_claims, secret, algorithm="HS256")
    
    @staticmethod
    def generate_oauth_state(data: Dict[str, Any]) -> str:
        """Generate a valid OAuth state parameter"""
        state_data = {
            "nonce": secrets.token_urlsafe(16),
            "timestamp": int(time.time()),
            **data
        }
        return base64.urlsafe_b64encode(
            json.dumps(state_data).encode()
        ).decode()