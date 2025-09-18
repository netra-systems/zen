"""
CRITICAL STAGING TESTS - OAuth Redirect URI Configuration"""
Currently FAILING - exposes critical production issues."""
import pytest
import httpx
import asyncio
from urllib.parse import urlparse, parse_qs
from shared.isolated_environment import IsolatedEnvironment

"""
    """Critical OAuth redirect URI tests for staging"""

    @pytest.fixture
    @pytest.mark.critical"""
    """
    CRITICAL: OAuth must redirect to app.staging.netrasystems.ai, not auth.staging

    CURRENT STATE: FAILING
    - OAuth redirects to auth.staging.netrasystems.ai/auth/callback"""
    - This breaks the entire authentication flow""""""
    auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

    async with httpx.AsyncClient(follow_redirects=False) as client:
    response = await client.get( )
    "formatted_string",
    params={"return_url": "https://app.staging.netrasystems.ai/dashboard"}
            

    assert response.status_code in [302, 303], "OAuth should redirect to Google"

    location = response.headers.get("location", "")
    assert "accounts.google.com" in location, "Should redirect to Google OAuth"

            Parse the redirect URI from Google OAuth URL
    parsed_url = urlparse(location)
    query_params = parse_qs(parsed_url.query)
    redirect_uri = query_params.get("redirect_uri", [""])[0]

            # CRITICAL ASSERTION - Currently failing
    assert "app.staging.netrasystems.ai" in redirect_uri, \
    "formatted_string"

    assert "auth.staging.netrasystems.ai" not in redirect_uri, \
    "formatted_string"

    @pytest.fixture
    @pytest.mark.critical
    async def test_oauth_config_includes_app_redirect_uris(self):
    """
    OAuth configuration must include app.staging.netrasystems.ai redirect URIs

    CURRENT STATE: FAILING"""
    - Missing app.staging.netrasystems.ai/auth/callback""""""
    auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

    async with httpx.AsyncClient() as client:
    response = await client.get("formatted_string")
    assert response.status_code == 200

    config = response.json()
                    # CRITICAL ASSERTIONS - Currently failing
    assert len(redirect_uris) > 0, "OAuth config must have redirect URIs"

    assert any("app.staging.netrasystems.ai/auth/callback" in uri for uri in redirect_uris), \
    "formatted_string"

                    # Should NOT have localhost in staging
    assert not any("localhost" in uri for uri in redirect_uris), \
    "formatted_string"

    @pytest.fixture
    @pytest.mark.critical
    async def test_frontend_oauth_callback_route_exists(self):
    """
    Frontend must have /auth/callback route to handle OAuth returns"""
    CURRENT STATE: UNKNOWN - needs verification""""""
    frontend_url = "https://app.staging.netrasystems.ai"

    async with httpx.AsyncClient(follow_redirects=False) as client:
    response = await client.get("formatted_string")

                            # Should not be 404
    assert response.status_code != 404, \
    "Frontend /auth/callback route must exist to handle OAuth"

    @pytest.fixture
    @pytest.mark.critical
    async def test_cors_allows_app_subdomain(self):
    """
    CORS must allow app.staging.netrasystems.ai origin"""
    CURRENT STATE: PASSING (but needs verification)""""""
    auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
    origin = "https://app.staging.netrasystems.ai"

    async with httpx.AsyncClient() as client:
    response = await client.options( )
    "formatted_string",
headers={"Origin": origin,}
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type"
                                    
                                    

    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin == origin or allow_origin == "*", \
    "formatted_string"

    allow_credentials = response.headers.get("access-control-allow-credentials")
    assert allow_credentials == "true", \
    "CORS must allow credentials for auth"


class TestStagingAuthenticationE2E:
    """End-to-end authentication flow tests"""

    @pytest.fixture
    @pytest.mark.integration"""
    """
    Test complete OAuth flow using app.staging.netrasystems.ai

    CURRENT STATE: FAILING"""
    - Frontend can"t handle callback"""
    pass
        # This would require browser automation to fully test
        # but we can verify the configuration is correct"""
    auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
    frontend_url = "https://app.staging.netrasystems.ai"

    async with httpx.AsyncClient(follow_redirects=False) as client:
            # 1. Frontend initiates OAuth
    response = await client.get( )
    "formatted_string",
    params={"return_url": "formatted_string"},
    headers={"Referer": "formatted_string"}
            

    assert response.status_code in [302, 303]

            # 2. Verify Google OAuth URL has correct redirect_uri
    location = response.headers.get("location", "")
    assert "redirect_uri=" in location
    assert "app.staging.netrasystems.ai" in location, \
    "OAuth must use app.staging subdomain for callback"

    @pytest.fixture
    @pytest.mark.critical
    async def test_backend_accepts_tokens_from_auth_service(self):
    """
    Backend must accept and validate tokens from auth service

    CURRENT STATE: Needs verification"""
    - Token validation must work cross-service"""
    pass
                # This requires a valid token to test properly
                # We're checking the configuration is correct"""
    backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"

    async with httpx.AsyncClient() as client:
                    # Try with a dummy token to see error type
    response = await client.get( )
    "formatted_string",
    headers={"Authorization": "Bearer dummy_token"}
                    

                    # Should be 401 (invalid token), not 403 (forbidden)
    assert response.status_code == 401, \
                    # Removed problematic line: f"Error executing agent: {e}"


class TestStagingEnvironmentConfiguration:
    """Test environment-specific configuration"""

    @pytest.fixture
    @pytest.mark.critical"""
        """
        OAuth secrets must be properly configured in staging"""
        CURRENT STATE: Needs verification via Secret Manager"""
        pass
    # These would be checked via GCP Secret Manager"""
        "google-oauth-client-id-staging",
        "google-oauth-client-secret-staging",
        "oauth-hmac-secret-staging"
    

    # In real test, would verify these exist in Secret Manager
    # For now, we mark this as needing manual verification
        pytest.skip("Requires Secret Manager access to verify")

        @pytest.fixture
        @pytest.mark.critical
    async def test_no_dev_endpoints_in_staging(self):
        """
        Dev endpoints must be disabled in staging"""
        CURRENT STATE: PASSING""""""
        auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

        async with httpx.AsyncClient() as client:
        response = await client.post( )
        "formatted_string",
        json={"email": "dev@example.com", "password": "dev123"}
            

        assert response.status_code == 403, \
        "formatted_string"

        assert "forbidden" in response.text.lower(), \
        "Should explicitly state dev login is forbidden"


            # Pytest configuration for staging tests
        pytest_plugins = ["pytest_asyncio"]


    def pytest_configure(config):
        """Configure pytest with staging markers""""""
        "markers", "env(name): mark test to run only in specific environment"
    
        config.addinivalue_line( )
        "markers", "critical: mark test as critical for production"
    
        config.addinivalue_line( )
        "markers", "integration: mark test as integration test"
    


        if __name__ == "__main__":
        # Run critical failing tests to demonstrate issues
        print("Running critical staging OAuth tests...")
        print("These tests SHOULD be passing but are currently FAILING")
        print("This exposes critical authentication issues in staging )
        ")

import subprocess
        result = subprocess.run( )
        ["python", "-m", "pytest", __file__, "-v", "-m", "critical"],
        capture_output=True,
        text=True
        

        print(result.stdout)
        if result.returncode != 0:
        print(" )
        [CRITICAL] Tests are failing - authentication is broken in staging!")
        print("The test suite correctly identifies these issues.")
        else:
        print(" )
        [OK] All critical tests passing")
        pass
