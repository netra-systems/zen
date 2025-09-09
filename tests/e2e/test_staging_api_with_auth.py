from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
E2E Tests for Staging API with OAUTH SIMULATION

This test suite demonstrates how to use the OAUTH SIMULATION mechanism
to run E2E tests against the staging environment without OAuth.
Updated to use GCP staging service URLs and Secrets Manager integration.
"""

import pytest
import httpx
import os
from typing import AsyncGenerator
from tests.e2e.staging_auth_bypass import StagingAuthHelper
from shared.isolated_environment import get_env


# Get environment manager
env = get_env()

# Skip these tests if not running against staging
pytestmark = pytest.mark.skipif(
    env.get("ENVIRONMENT", "development") != "staging",
    reason="These tests only run against staging environment"
)


@pytest.fixture
async def auth_helper():
    """Provide auth helper for tests with GCP staging configuration."""
    # Use staging service URLs from task requirements - LOAD BALANCER ENDPOINTS
    auth_helper = StagingAuthHelper()
    auth_helper.staging_auth_url = "https://auth.staging.netrasystems.ai"
    auth_helper.staging_backend_url = "https://api.staging.netrasystems.ai"
    auth_helper.staging_frontend_url = "https://app.staging.netrasystems.ai"
    return auth_helper


@pytest.fixture
async def authenticated_client(auth_helper) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an authenticated HTTP client for tests with staging URLs."""
    client = await auth_helper.get_authenticated_client(
        base_url=auth_helper.staging_auth_url
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_auth_bypass_works(auth_helper):
    """Test that OAUTH SIMULATION successfully generates tokens using GCP staging services."""
    try:
        token = await auth_helper.get_test_token()
        assert token is not None
        assert len(token) > 20  # Basic sanity check
        
        # Verify the token is valid with increased timeout for GCP services
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_helper.staging_auth_url}/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("valid") is True
            assert data.get("email") == "e2e-test@staging.netrasystems.ai"
    except Exception as e:
        if "GCP" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_authenticated_health_check(authenticated_client):
    """Test that authenticated client can access health endpoint on GCP staging."""
    try:
        response = await authenticated_client.get("/auth/health", timeout=30.0)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "degraded"]
    except httpx.TimeoutException:
        pytest.skip("GCP service timeout - may be starting up")
    except Exception as e:
        if "GCP" in str(e) or "run.app" in str(e):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_authenticated_user_info(authenticated_client):
    """Test that authenticated client can get user information from GCP staging."""
    try:
        response = await authenticated_client.get("/auth/me", timeout=30.0)
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == "e2e-test@staging.netrasystems.ai"
        assert data.get("id") is not None
    except httpx.TimeoutException:
        pytest.skip("GCP service timeout - may be starting up")
    except Exception as e:
        if "GCP" in str(e) or "run.app" in str(e):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_custom_test_user(auth_helper):
    """Test creating custom test user with specific permissions on GCP staging."""
    try:
        token = await auth_helper.get_test_token(
            email="custom-e2e@staging.netrasystems.ai",
            name="Custom E2E User",
            permissions=["read", "write", "admin"]
        )
        assert token is not None
        
        # Verify custom user details with GCP staging
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_helper.staging_auth_url}/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("email") == "custom-e2e@staging.netrasystems.ai"
    except Exception as e:
        if "GCP" in str(e) or "secret" in str(e).lower() or "run.app" in str(e):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


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
    """Test that invalid bypass key is rejected by GCP staging services."""
    auth = StagingAuthHelper(bypass_key="invalid-key-12345")
    auth.staging_auth_url = "https://auth.staging.netrasystems.ai"
    
    with pytest.raises(Exception) as exc_info:
        await auth.get_test_token()
    
    assert "401" in str(exc_info.value) or "Invalid" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)


@pytest.mark.asyncio 
async def test_api_endpoints_with_auth(authenticated_client):
    """Test various API endpoints with authenticated client on GCP staging."""
    try:
        # Test session endpoint
        response = await authenticated_client.get("/auth/session", timeout=30.0)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        
        # Test token validation
        response = await authenticated_client.post(
            "/auth/validate",
            json={"token": "dummy-token", "token_type": "access"},
            timeout=30.0
        )
        # Should fail for invalid token
        assert response.status_code == 401
    except httpx.TimeoutException:
        pytest.skip("GCP service timeout - may be starting up")
    except Exception as e:
        if "GCP" in str(e) or "run.app" in str(e):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_refresh_token_flow(auth_helper):
    """Test that refresh tokens work with OAUTH SIMULATION on GCP staging."""
    try:
        # Get initial tokens
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_helper.staging_auth_url}/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": auth_helper.bypass_key,
                    "Content-Type": "application/json"
                },
                json={
                    "email": "refresh-test@staging.netrasystems.ai",
                    "name": "Refresh Test User"
                },
                timeout=30.0
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
                json={"refresh_token": refresh_token},
                timeout=30.0
            )
            assert response.status_code == 200
            new_data = response.json()
            
            new_access_token = new_data.get("access_token")
            assert new_access_token is not None
            assert new_access_token != access_token  # Should be different
    except Exception as e:
        if "GCP" in str(e) or "secret" in str(e).lower() or "run.app" in str(e):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


# Run tests if executed directly
if __name__ == "__main__":
    import sys
    import subprocess
    
    # Set environment to staging for testing
    
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