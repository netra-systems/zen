"""
E2E Tests for Staging API with Auth Bypass

This test suite demonstrates how to use the auth bypass mechanism
to run E2E tests against the staging environment without OAuth.
"""

import pytest
import httpx
import os
from typing import AsyncGenerator
from staging_auth_bypass import StagingAuthHelper


# Skip these tests if not running against staging
pytestmark = pytest.mark.skipif(
    os.getenv("ENVIRONMENT", "development") != "staging",
    reason="These tests only run against staging environment"
)


@pytest.fixture
async def auth_helper():
    """Provide auth helper for tests."""
    return StagingAuthHelper()


@pytest.fixture
async def authenticated_client(auth_helper) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an authenticated HTTP client for tests."""
    client = await auth_helper.get_authenticated_client()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_auth_bypass_works(auth_helper):
    """Test that auth bypass successfully generates tokens."""
    token = await auth_helper.get_test_token()
    assert token is not None
    assert len(token) > 20  # Basic sanity check
    
    # Verify the token is valid
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{auth_helper.staging_auth_url}/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") is True
        assert data.get("email") == "e2e-test@staging.netrasystems.ai"


@pytest.mark.asyncio
async def test_authenticated_health_check(authenticated_client):
    """Test that authenticated client can access health endpoint."""
    response = await authenticated_client.get("/auth/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_authenticated_user_info(authenticated_client):
    """Test that authenticated client can get user information."""
    response = await authenticated_client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data.get("email") == "e2e-test@staging.netrasystems.ai"
    assert data.get("id") is not None


@pytest.mark.asyncio
async def test_custom_test_user(auth_helper):
    """Test creating custom test user with specific permissions."""
    token = await auth_helper.get_test_token(
        email="custom-e2e@staging.netrasystems.ai",
        name="Custom E2E User",
        permissions=["read", "write", "admin"]
    )
    assert token is not None
    
    # Verify custom user details
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{auth_helper.staging_auth_url}/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == "custom-e2e@staging.netrasystems.ai"


@pytest.mark.asyncio
async def test_token_caching(auth_helper):
    """Test that auth helper properly caches tokens."""
    # Get first token
    token1 = await auth_helper.get_test_token()
    
    # Get second token (should be cached)
    token2 = await auth_helper.get_test_token()
    
    # Tokens should be identical due to caching
    assert token1 == token2
    
    # Clear cache and get new token
    auth_helper.token_cache = None
    auth_helper.token_expiry = None
    token3 = await auth_helper.get_test_token()
    
    # New token should be different
    assert token3 != token1


@pytest.mark.asyncio
async def test_invalid_bypass_key():
    """Test that invalid bypass key is rejected."""
    auth = StagingAuthHelper(bypass_key="invalid-key-12345")
    
    with pytest.raises(Exception) as exc_info:
        await auth.get_test_token()
    
    assert "401" in str(exc_info.value) or "Invalid" in str(exc_info.value)


@pytest.mark.asyncio 
async def test_api_endpoints_with_auth(authenticated_client):
    """Test various API endpoints with authenticated client."""
    # Test session endpoint
    response = await authenticated_client.get("/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    
    # Test token validation
    response = await authenticated_client.post(
        "/auth/validate",
        json={"token": "dummy-token", "token_type": "access"}  
    )
    # Should fail for invalid token
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_flow(auth_helper):
    """Test that refresh tokens work with auth bypass."""
    # Get initial tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{auth_helper.staging_auth_url}/auth/e2e/test-auth",
            headers={
                "X-E2E-Bypass-Key": auth_helper.bypass_key,
                "Content-Type": "application/json"
            },
            json={
                "email": "refresh-test@staging.netrasystems.ai",
                "name": "Refresh Test User"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        
        assert access_token is not None
        assert refresh_token is not None
        
        # Use refresh token to get new access token
        response = await client.post(
            f"{auth_helper.staging_auth_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        new_data = response.json()
        
        new_access_token = new_data.get("access_token")
        assert new_access_token is not None
        assert new_access_token != access_token  # Should be different


# Run tests if executed directly
if __name__ == "__main__":
    import sys
    import subprocess
    
    # Set environment to staging for testing
    os.environ["ENVIRONMENT"] = "staging"
    
    # Run pytest on this file
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)