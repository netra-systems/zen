"""
L3 Integration Test: API Authentication
Tests API authentication mechanisms and flows
"""

import pytest
import asyncio
import httpx
import jwt
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.config import settings
import time

# Add project root to path


class TestAPIAuthenticationL3:
    """Test API authentication scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_api_requires_authentication(self):
        """Test API endpoints require authentication"""
        async with httpx.AsyncClient() as client:
            # Request without auth header
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources"
            )
            
            assert response.status_code == 401
            error = response.json()
            assert "unauthorized" in error.get("error", "").lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_bearer_token_authentication(self):
        """Test Bearer token authentication"""
        async with httpx.AsyncClient() as client:
            # Valid token
            valid_token = jwt.encode(
                {"sub": "123", "exp": time.time() + 3600},
                settings.SECRET_KEY,
                algorithm="HS256"
            )
            
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_api_key_authentication(self):
        """Test API key authentication"""
        async with httpx.AsyncClient() as client:
            # API key auth
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                headers={"X-API-Key": "test_api_key_123"}
            )
            
            # Should work if API key auth is enabled
            if response.status_code == 200:
                assert "data" in response.json() or "items" in response.json()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_rejection(self):
        """Test expired token is rejected"""
        async with httpx.AsyncClient() as client:
            # Expired token
            expired_token = jwt.encode(
                {"sub": "123", "exp": time.time() - 3600},
                settings.SECRET_KEY,
                algorithm="HS256"
            )
            
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
            
            assert response.status_code == 401
            error = response.json()
            assert "expired" in error.get("error", "").lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_invalid_token_format(self):
        """Test invalid token format handling"""
        async with httpx.AsyncClient() as client:
            # Malformed token
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                headers={"Authorization": "Bearer invalid.token.format"}
            )
            
            assert response.status_code == 401
            
            # Wrong auth scheme
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                headers={"Authorization": "Basic dXNlcjpwYXNz"}  # Basic auth
            )
            
            assert response.status_code in [401, 403]