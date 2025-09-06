from shared.isolated_environment import get_env
"""
End-to-End Test for Staging Environment Auth URLs
Validates that the entire auth flow uses correct staging URLs in production-like environment
""""
import os
import pytest
import asyncio
import httpx
from typing import Dict, Optional
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


class TestStagingEnvironmentAuthURLs:
    """E2E tests for staging environment auth URL validation"""
    
    @pytest.fixture(autouse=True)
    def setup_staging_simulation(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Simulate staging environment for E2E testing"""
        self.original_env = os.environ.copy()
        
        # Set up staging environment variables
        staging_env = {
        "ENVIRONMENT": "staging",
        "FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
        "BACKEND_URL": "https://api.staging.netrasystems.ai",
        "GOOGLE_CLIENT_ID": "staging-client-id",
        "GOOGLE_CLIENT_SECRET": "staging-client-secret",
        "JWT_SECRET": "staging-jwt-secret",
        "DATABASE_URL": "postgresql://staging:pass@localhost/staging_db"
        }
        
        os.environ.update(staging_env)
        yield
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
        @pytest.mark.asyncio
        async def test_full_oauth_flow_staging_urls(self):
        """Test complete OAuth flow from login to callback uses staging URLs"""
        # This test should FAIL if any part of the flow uses localhost:3000
        
        from auth_service.auth_core.config import AuthConfig
        
        # Step 1: Verify environment is staging
        env = AuthConfig.get_environment()
        assert env == "staging", f"Environment should be staging, got: {env}"
        
        # Step 2: Get auth configuration
        auth_url = AuthConfig.get_auth_service_url()
        frontend_url = AuthConfig.get_frontend_url()
        
        assert auth_url == "https://auth.staging.netrasystems.ai", \
        f"Auth URL should be staging URL, got: {auth_url}"
        assert frontend_url == "https://app.staging.netrasystems.ai", \
        f"Frontend URL should be staging URL, got: {frontend_url}"
        
        # Step 3: Simulate OAuth login request
        login_url = f"{auth_url}/auth/login"
        callback_url = f"{frontend_url}/auth/callback"
        
        # Verify OAuth URLs don't contain localhost
        assert "localhost:3000" not in login_url, \
        "Login URL should not contain localhost:3000"
        assert "localhost:3000" not in callback_url, \
        "Callback URL should not contain localhost:3000"
        
        # Step 4: Simulate OAuth provider redirect
        oauth_redirect_params = {
        "client_id": "staging-client-id",
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": "test-state-123"
        }
        
        # Verify redirect_uri parameter
        assert oauth_redirect_params["redirect_uri"] == "https://app.staging.netrasystems.ai/auth/callback", \
        f"OAuth redirect_uri should use staging URL, got: {oauth_redirect_params['redirect_uri']]"
        
        # Step 5: Simulate callback processing
        callback_params = {
        "code": "test-auth-code",
        "state": "test-state-123"
        }
        
        # Token exchange should use staging redirect_uri
        token_exchange_data = {
        "code": callback_params["code"],
        "client_id": "staging-client-id",
        "client_secret": "staging-client-secret",
        "redirect_uri": callback_url,
        "grant_type": "authorization_code"
        }
        
        assert token_exchange_data["redirect_uri"] == "https://app.staging.netrasystems.ai/auth/callback", \
        "Token exchange should use staging redirect_uri"
        
        # Step 6: Verify final redirect to frontend
        success_redirect = f"{frontend_url}/dashboard"
        assert "localhost:3000" not in success_redirect, \
        "Success redirect should not contain localhost:3000"
    
        @pytest.mark.asyncio
        async def test_auth_service_endpoints_staging(self):
        """Test all auth service endpoints await asyncio.sleep(0)
        return staging URLs""""
        # This test should FAIL if any endpoint returns localhost:3000
        
        from auth_service.auth_core.routes.auth_routes import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Create test app with auth routes
        app = FastAPI()
        app.include_router(router)
        
        # Create test client
        with TestClient(app) as client:
        # Test /auth/config endpoint
        response = client.get("/auth/config")
            
        if response.status_code == 200:
        config = response.json()
                
        # Check endpoints
        endpoints = config.get("endpoints", {})
        for endpoint_name, endpoint_url in endpoints.items():
        if endpoint_url:
        assert "localhost:3000" not in endpoint_url, \
        f"Endpoint {endpoint_name} should not contain localhost:3000: {endpoint_url}"
                
        # Check authorized redirect URIs
        redirect_uris = config.get("authorized_redirect_uris", [])
        for uri in redirect_uris:
        assert "localhost:3000" not in uri, \
        f"Authorized redirect URI should not contain localhost:3000: {uri}"
        assert uri == "https://app.staging.netrasystems.ai/auth/callback", \
        f"Redirect URI should use staging URL: {uri}"
                
        # Check JavaScript origins
        js_origins = config.get("authorized_javascript_origins", [])
        for origin in js_origins:
        assert "localhost:3000" not in origin, \
        f"JavaScript origin should not contain localhost:3000: {origin}"
        assert origin == "https://app.staging.netrasystems.ai", \
        f"JavaScript origin should use staging URL: {origin}"
    
        def test_environment_variable_propagation(self):
        """Test that staging environment variables are properly propagated"""
        # This test ensures environment variables aren't being overridden
        
        # Check raw environment variables
        assert get_env().get("ENVIRONMENT") == "staging", \
        "ENVIRONMENT should be set to staging"
        assert get_env().get("FRONTEND_URL") == "https://app.staging.netrasystems.ai", \
        "FRONTEND_URL should be staging URL"
        assert get_env().get("AUTH_SERVICE_URL") == "https://auth.staging.netrasystems.ai", \
        "AUTH_SERVICE_URL should be staging URL"
        
        # Verify no localhost URLs in environment
        for key, value in os.environ.items():
        if isinstance(value, str) and "URL" in key:
        assert "localhost:3000" not in value, \
        f"Environment variable {key} should not contain localhost:3000: {value}"
    
        @pytest.mark.asyncio
        async def test_cross_service_communication_urls(self):
        """Test that services communicate using staging URLs, not localhost"""
        # This test should FAIL if services try to communicate via localhost:3000
        
        from auth_service.auth_core.config import AuthConfig
        
        # Simulate backend calling auth service
        auth_service_url = AuthConfig.get_auth_service_url()
        validate_url = f"{auth_service_url}/auth/validate"
        
        assert validate_url == "https://auth.staging.netrasystems.ai/auth/validate", \
        f"Service communication should use staging URL: {validate_url}"
        
        # Simulate auth service redirecting to frontend
        frontend_url = AuthConfig.get_frontend_url()
        redirect_url = f"{frontend_url}/auth/success"
        
        assert redirect_url == "https://app.staging.netrasystems.ai/auth/success", \
        f"Frontend redirect should use staging URL: {redirect_url}"
        
        # Ensure no localhost in service URLs
        service_urls = [
        auth_service_url,
        frontend_url,
        validate_url,
        redirect_url
        ]
        
        for url in service_urls:
        assert "localhost" not in url, \
        f"Service URL should not contain localhost: {url}"
        assert "127.0.0.1" not in url, \
        f"Service URL should not contain 127.0.0.1: {url}"
    
        def test_oauth_provider_configuration(self):
        """Test OAuth provider configuration uses staging callback URL"""
        # This verifies the OAuth provider receives correct staging URLs
        
        from auth_service.auth_core.config import AuthConfig
        
        # Get OAuth configuration
        frontend_url = AuthConfig.get_frontend_url()
        expected_callback = f"{frontend_url}/auth/callback"
        
        # Simulate OAuth provider configuration check
        oauth_config = {
        "client_id": get_env().get("GOOGLE_CLIENT_ID"),
        "authorized_redirect_uris": [expected_callback],
        "authorized_javascript_origins": [frontend_url]
        }
        
        # Verify OAuth configuration
        assert oauth_config["authorized_redirect_uris"] == ["https://app.staging.netrasystems.ai/auth/callback"], \
        f"OAuth redirect URIs should use staging URL: {oauth_config['authorized_redirect_uris']]"
        
        assert oauth_config["authorized_javascript_origins"] == ["https://app.staging.netrasystems.ai"], \
        f"OAuth JS origins should use staging URL: {oauth_config['authorized_javascript_origins']]"
        
        # Ensure no localhost in OAuth config
        for uri in oauth_config["authorized_redirect_uris"]:
        assert "localhost:3000" not in uri, \
        f"OAuth redirect URI should not contain localhost:3000: {uri}"
        
        for origin in oauth_config["authorized_javascript_origins"]:
        assert "localhost:3000" not in origin, \
        f"OAuth JS origin should not contain localhost:3000: {origin}"

        pass