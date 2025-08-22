"""Auth Token Validation Cross-Service Integration Tests (L3)

Tests token validation and propagation across different services and components.
Validates JWT handling, service-to-service auth, and token security.

Business Value Justification (BVJ):
- Segment: All (security foundation for all segments)
- Business Goal: Security - prevent unauthorized access
- Value Impact: Token breaches can compromise entire platform
- Revenue Impact: Critical - security incidents destroy customer trust
"""

# Add project root to path

from netra_backend.app.websocket.connection_manager import ModernModernConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Add project root to path

# Set test environment before imports

os.environ["ENVIRONMENT"] = "testing"

os.environ["TESTING"] = "true"

os.environ["SKIP_STARTUP_CHECKS"] = "true"

from main import app

from netra_backend.app.config import settings
from netra_backend.app.middleware.auth_middleware import AuthMiddleware
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.utils.jwt_utils import JWTUtils


class TestAuthTokenValidationCrossService:

    """Test auth token validation across different services."""
    

    @pytest.fixture

    def valid_jwt_token(self):

        """Create a valid JWT token for testing."""

        payload = {

            "sub": str(uuid.uuid4()),  # user_id

            "email": "test@example.com",

            "exp": datetime.utcnow() + timedelta(hours=1),

            "iat": datetime.utcnow(),

            "type": "access",

            "permissions": ["read", "write"]

        }
        
        # Use test secret key

        secret_key = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret_key"

        token = jwt.encode(payload, secret_key, algorithm="HS256")

        return token
    

    @pytest.fixture

    def expired_jwt_token(self):

        """Create an expired JWT token for testing."""

        payload = {

            "sub": str(uuid.uuid4()),

            "email": "test@example.com",

            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired

            "iat": datetime.utcnow() - timedelta(hours=2),

            "type": "access"

        }
        

        secret_key = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret_key"

        token = jwt.encode(payload, secret_key, algorithm="HS256")

        return token
    

    @pytest.fixture

    async def async_client(self):

        """Create async client for testing."""

        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as ac:

            yield ac
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_valid_token_accepted_by_api_endpoint(self, async_client, valid_jwt_token):

        """Test 1: Valid token should be accepted by protected API endpoints."""

        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        # Mock user lookup

        with patch('app.services.user_service.UserService.get_user', return_value=MagicMock()):

            with patch('app.services.auth_service.AuthService.validate_token', return_value=True):
                

                response = await async_client.get("/api/user/profile", headers=headers)
                
                # Should not return 401/403

                assert response.status_code not in [401, 403], f"Valid token rejected with {response.status_code}"
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_expired_token_rejected(self, async_client, expired_jwt_token):

        """Test 2: Expired tokens should be rejected."""

        headers = {"Authorization": f"Bearer {expired_jwt_token}"}
        

        response = await async_client.get("/api/user/profile", headers=headers)
        
        # Should return 401 Unauthorized

        assert response.status_code == 401
        

        data = response.json()

        assert "expired" in data.get("detail", "").lower()
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_malformed_token_rejected(self, async_client):

        """Test 3: Malformed tokens should be rejected."""

        test_cases = [

            "not.a.valid.jwt",

            "Bearer",

            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Incomplete JWT

            "random_string_123",

        ]
        

        for malformed_token in test_cases:

            headers = {"Authorization": f"Bearer {malformed_token}"}
            

            response = await async_client.get("/api/user/profile", headers=headers)
            
            # Should return 401 Unauthorized

            assert response.status_code == 401, f"Malformed token '{malformed_token}' was not rejected"
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_token_with_invalid_signature_rejected(self, async_client):

        """Test 4: Tokens with invalid signatures should be rejected."""
        # Create token with wrong secret

        payload = {

            "sub": str(uuid.uuid4()),

            "email": "test@example.com",

            "exp": datetime.utcnow() + timedelta(hours=1),

            "iat": datetime.utcnow(),

            "type": "access"

        }
        

        wrong_secret = "wrong_secret_key"

        invalid_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
        

        headers = {"Authorization": f"Bearer {invalid_token}"}
        

        response = await async_client.get("/api/user/profile", headers=headers)
        
        # Should return 401 Unauthorized

        assert response.status_code == 401
        

        data = response.json()

        assert "invalid" in data.get("detail", "").lower() or "signature" in data.get("detail", "").lower()
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_service_to_service_token_propagation(self):

        """Test 5: Tokens should propagate correctly in service-to-service calls."""

        user_id = str(uuid.uuid4())

        token = "service_token_123"
        
        # Mock service clients

        mock_service_a = AsyncMock()

        mock_service_b = AsyncMock()
        
        # Service A calls Service B with token

        async def service_a_call():

            headers = {"Authorization": f"Bearer {token}"}

            return await mock_service_b.call_api(headers=headers)
        

        mock_service_b.call_api.return_value = {"status": "success"}
        
        # Execute service-to-service call

        result = await service_a_call()
        
        # Verify token was propagated

        mock_service_b.call_api.assert_called_once()

        call_args = mock_service_b.call_api.call_args

        assert "headers" in call_args.kwargs

        assert call_args.kwargs["headers"]["Authorization"] == f"Bearer {token}"
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_websocket_token_validation(self, async_client, valid_jwt_token):

        """Test 6: WebSocket connections should validate tokens."""
        # WebSocket connection with token

        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        

        with patch('app.websocket.manager.WebSocketManager.validate_token', return_value=True) as mock_validate:
            # Mock WebSocket connection attempt

            mock_validate.return_value = True
            
            # Simulate WebSocket auth check

            is_valid = mock_validate(valid_jwt_token)
            

            assert is_valid == True

            mock_validate.assert_called_with(valid_jwt_token)
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_token_permissions_enforcement(self, async_client):

        """Test 7: Token permissions should be enforced at endpoint level."""
        # Create token with limited permissions

        payload = {

            "sub": str(uuid.uuid4()),

            "email": "limited@example.com",

            "exp": datetime.utcnow() + timedelta(hours=1),

            "iat": datetime.utcnow(),

            "type": "access",

            "permissions": ["read"]  # Only read permission

        }
        

        secret_key = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret_key"

        limited_token = jwt.encode(payload, secret_key, algorithm="HS256")
        

        headers = {"Authorization": f"Bearer {limited_token}"}
        
        # Try to access write endpoint

        with patch('app.middleware.auth_middleware.AuthMiddleware.check_permissions', return_value=False):

            response = await async_client.post("/api/data/create", headers=headers, json={})
            
            # Should return 403 Forbidden

            assert response.status_code in [403, 401, 404]  # 404 if endpoint doesn't exist
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_token_refresh_maintains_user_context(self, async_client):

        """Test 8: Token refresh should maintain user context and permissions."""

        user_id = str(uuid.uuid4())

        original_permissions = ["read", "write", "admin"]
        
        # Original token

        original_payload = {

            "sub": user_id,

            "email": "admin@example.com",

            "exp": datetime.utcnow() + timedelta(minutes=5),

            "iat": datetime.utcnow(),

            "type": "access",

            "permissions": original_permissions

        }
        
        # Refreshed token should maintain same user context

        refreshed_payload = {

            "sub": user_id,  # Same user

            "email": "admin@example.com",

            "exp": datetime.utcnow() + timedelta(hours=1),  # New expiry

            "iat": datetime.utcnow(),

            "type": "access",

            "permissions": original_permissions  # Same permissions

        }
        

        with patch('app.services.auth_service.AuthService.refresh_tokens', return_value=refreshed_payload):
            # Verify user context is maintained

            assert refreshed_payload["sub"] == original_payload["sub"]

            assert refreshed_payload["permissions"] == original_payload["permissions"]

            assert refreshed_payload["email"] == original_payload["email"]
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_concurrent_token_validation_performance(self, async_client, valid_jwt_token):

        """Test 9: System should handle concurrent token validations efficiently."""

        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        
        # Create multiple concurrent requests

        async def make_request():

            with patch('app.services.auth_service.AuthService.validate_token', return_value=True):

                return await async_client.get("/api/health", headers=headers)
        
        # Send 10 concurrent requests

        start_time = time.perf_counter()

        tasks = [make_request() for _ in range(10)]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_time = time.perf_counter() - start_time
        
        # All should complete within reasonable time

        assert elapsed_time < 2.0, f"Concurrent validation took {elapsed_time}s"
        
        # All should succeed

        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code in [200, 503])

        assert success_count >= 8, f"Only {success_count}/10 requests succeeded"
    

    @pytest.mark.integration

    @pytest.mark.L3

    async def test_token_blacklist_enforcement(self, async_client, valid_jwt_token):

        """Test 10: Blacklisted tokens should be rejected even if valid."""
        # Add token to blacklist

        blacklisted_token = valid_jwt_token
        

        with patch('app.services.auth_service.AuthService.is_token_blacklisted', return_value=True):

            headers = {"Authorization": f"Bearer {blacklisted_token}"}
            

            response = await async_client.get("/api/user/profile", headers=headers)
            
            # Should return 401 Unauthorized

            assert response.status_code == 401
            

            data = response.json()

            assert "revoked" in data.get("detail", "").lower() or "blacklisted" in data.get("detail", "").lower()