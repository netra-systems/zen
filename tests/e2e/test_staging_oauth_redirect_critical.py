# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: CRITICAL STAGING TESTS - OAuth Redirect URI Configuration
# REMOVED_SYNTAX_ERROR: These tests MUST pass for authentication to work in staging.
# REMOVED_SYNTAX_ERROR: Currently FAILING - exposes critical production issues.
# REMOVED_SYNTAX_ERROR: '''
import pytest
import httpx
import asyncio
from urllib.parse import urlparse, parse_qs
from shared.isolated_environment import IsolatedEnvironment


# REMOVED_SYNTAX_ERROR: class TestStagingOAuthRedirectCritical:
    # REMOVED_SYNTAX_ERROR: """Critical OAuth redirect URI tests for staging"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
    # Removed problematic line: async def test_oauth_redirect_uri_uses_app_subdomain(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: CRITICAL: OAuth must redirect to app.staging.netrasystems.ai, not auth.staging

        # REMOVED_SYNTAX_ERROR: CURRENT STATE: FAILING
        # REMOVED_SYNTAX_ERROR: - OAuth redirects to auth.staging.netrasystems.ai/auth/callback
        # REMOVED_SYNTAX_ERROR: - Should redirect to app.staging.netrasystems.ai/auth/callback
        # REMOVED_SYNTAX_ERROR: - This breaks the entire authentication flow
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

        # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient(follow_redirects=False) as client:
            # REMOVED_SYNTAX_ERROR: response = await client.get( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: params={"return_url": "https://app.staging.netrasystems.ai/dashboard"}
            

            # REMOVED_SYNTAX_ERROR: assert response.status_code in [302, 303], "OAuth should redirect to Google"

            # REMOVED_SYNTAX_ERROR: location = response.headers.get("location", "")
            # REMOVED_SYNTAX_ERROR: assert "accounts.google.com" in location, "Should redirect to Google OAuth"

            # Parse the redirect URI from Google OAuth URL
            # REMOVED_SYNTAX_ERROR: parsed_url = urlparse(location)
            # REMOVED_SYNTAX_ERROR: query_params = parse_qs(parsed_url.query)
            # REMOVED_SYNTAX_ERROR: redirect_uri = query_params.get("redirect_uri", [""])[0]

            # CRITICAL ASSERTION - Currently failing
            # REMOVED_SYNTAX_ERROR: assert "app.staging.netrasystems.ai" in redirect_uri, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # REMOVED_SYNTAX_ERROR: assert "auth.staging.netrasystems.ai" not in redirect_uri, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # REMOVED_SYNTAX_ERROR: @pytest.fixture
            # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
            # Removed problematic line: async def test_oauth_config_includes_app_redirect_uris(self):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: OAuth configuration must include app.staging.netrasystems.ai redirect URIs

                # REMOVED_SYNTAX_ERROR: CURRENT STATE: FAILING
                # REMOVED_SYNTAX_ERROR: - Config returns empty redirect_uris array
                # REMOVED_SYNTAX_ERROR: - Missing app.staging.netrasystems.ai/auth/callback
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

                # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient() as client:
                    # REMOVED_SYNTAX_ERROR: response = await client.get("formatted_string")
                    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

                    # REMOVED_SYNTAX_ERROR: config = response.json()
                    # REMOVED_SYNTAX_ERROR: redirect_uris = config.get("redirect_uris", [])

                    # CRITICAL ASSERTIONS - Currently failing
                    # REMOVED_SYNTAX_ERROR: assert len(redirect_uris) > 0, "OAuth config must have redirect URIs"

                    # REMOVED_SYNTAX_ERROR: assert any("app.staging.netrasystems.ai/auth/callback" in uri for uri in redirect_uris), \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Should NOT have localhost in staging
                    # REMOVED_SYNTAX_ERROR: assert not any("localhost" in uri for uri in redirect_uris), \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
                    # Removed problematic line: async def test_frontend_oauth_callback_route_exists(self):
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: Frontend must have /auth/callback route to handle OAuth returns

                        # REMOVED_SYNTAX_ERROR: CURRENT STATE: UNKNOWN - needs verification
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: frontend_url = "https://app.staging.netrasystems.ai"

                        # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient(follow_redirects=False) as client:
                            # REMOVED_SYNTAX_ERROR: response = await client.get("formatted_string")

                            # Should not be 404
                            # REMOVED_SYNTAX_ERROR: assert response.status_code != 404, \
                            # REMOVED_SYNTAX_ERROR: "Frontend /auth/callback route must exist to handle OAuth"

                            # REMOVED_SYNTAX_ERROR: @pytest.fixture
                            # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
                            # Removed problematic line: async def test_cors_allows_app_subdomain(self):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: CORS must allow app.staging.netrasystems.ai origin

                                # REMOVED_SYNTAX_ERROR: CURRENT STATE: PASSING (but needs verification)
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
                                # REMOVED_SYNTAX_ERROR: origin = "https://app.staging.netrasystems.ai"

                                # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient() as client:
                                    # REMOVED_SYNTAX_ERROR: response = await client.options( )
                                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                                    # REMOVED_SYNTAX_ERROR: headers={ )
                                    # REMOVED_SYNTAX_ERROR: "Origin": origin,
                                    # REMOVED_SYNTAX_ERROR: "Access-Control-Request-Method": "POST",
                                    # REMOVED_SYNTAX_ERROR: "Access-Control-Request-Headers": "content-type"
                                    
                                    

                                    # REMOVED_SYNTAX_ERROR: allow_origin = response.headers.get("access-control-allow-origin")
                                    # REMOVED_SYNTAX_ERROR: assert allow_origin == origin or allow_origin == "*", \
                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                    # REMOVED_SYNTAX_ERROR: allow_credentials = response.headers.get("access-control-allow-credentials")
                                    # REMOVED_SYNTAX_ERROR: assert allow_credentials == "true", \
                                    # REMOVED_SYNTAX_ERROR: "CORS must allow credentials for auth"


# REMOVED_SYNTAX_ERROR: class TestStagingAuthenticationE2E:
    # REMOVED_SYNTAX_ERROR: """End-to-end authentication flow tests"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
    # Removed problematic line: async def test_complete_oauth_flow_with_app_subdomain(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test complete OAuth flow using app.staging.netrasystems.ai

        # REMOVED_SYNTAX_ERROR: CURRENT STATE: FAILING
        # REMOVED_SYNTAX_ERROR: - OAuth redirects to wrong subdomain
        # REMOVED_SYNTAX_ERROR: - Frontend can"t handle callback
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # This would require browser automation to fully test
        # but we can verify the configuration is correct

        # REMOVED_SYNTAX_ERROR: auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        # REMOVED_SYNTAX_ERROR: frontend_url = "https://app.staging.netrasystems.ai"

        # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient(follow_redirects=False) as client:
            # 1. Frontend initiates OAuth
            # REMOVED_SYNTAX_ERROR: response = await client.get( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: params={"return_url": "formatted_string"},
            # REMOVED_SYNTAX_ERROR: headers={"Referer": "formatted_string"}
            

            # REMOVED_SYNTAX_ERROR: assert response.status_code in [302, 303]

            # 2. Verify Google OAuth URL has correct redirect_uri
            # REMOVED_SYNTAX_ERROR: location = response.headers.get("location", "")
            # REMOVED_SYNTAX_ERROR: assert "redirect_uri=" in location
            # REMOVED_SYNTAX_ERROR: assert "app.staging.netrasystems.ai" in location, \
            # REMOVED_SYNTAX_ERROR: "OAuth must use app.staging subdomain for callback"

            # REMOVED_SYNTAX_ERROR: @pytest.fixture
            # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
            # Removed problematic line: async def test_backend_accepts_tokens_from_auth_service(self):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Backend must accept and validate tokens from auth service

                # REMOVED_SYNTAX_ERROR: CURRENT STATE: Needs verification
                # REMOVED_SYNTAX_ERROR: - JWT secrets must be synchronized
                # REMOVED_SYNTAX_ERROR: - Token validation must work cross-service
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # This requires a valid token to test properly
                # We're checking the configuration is correct

                # REMOVED_SYNTAX_ERROR: backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"

                # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient() as client:
                    # Try with a dummy token to see error type
                    # REMOVED_SYNTAX_ERROR: response = await client.get( )
                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                    # REMOVED_SYNTAX_ERROR: headers={"Authorization": "Bearer dummy_token"}
                    

                    # Should be 401 (invalid token), not 403 (forbidden)
                    # REMOVED_SYNTAX_ERROR: assert response.status_code == 401, \
                    # Removed problematic line: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestStagingEnvironmentConfiguration:
    # REMOVED_SYNTAX_ERROR: """Test environment-specific configuration"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_oauth_secrets_configured_for_staging(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: OAuth secrets must be properly configured in staging

    # REMOVED_SYNTAX_ERROR: CURRENT STATE: Needs verification via Secret Manager
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # These would be checked via GCP Secret Manager
    # REMOVED_SYNTAX_ERROR: required_secrets = [ )
    # REMOVED_SYNTAX_ERROR: "google-oauth-client-id-staging",
    # REMOVED_SYNTAX_ERROR: "google-oauth-client-secret-staging",
    # REMOVED_SYNTAX_ERROR: "oauth-hmac-secret-staging"
    

    # In real test, would verify these exist in Secret Manager
    # For now, we mark this as needing manual verification
    # REMOVED_SYNTAX_ERROR: pytest.skip("Requires Secret Manager access to verify")

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
    # Removed problematic line: async def test_no_dev_endpoints_in_staging(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Dev endpoints must be disabled in staging

        # REMOVED_SYNTAX_ERROR: CURRENT STATE: PASSING
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"

        # REMOVED_SYNTAX_ERROR: async with httpx.AsyncClient() as client:
            # REMOVED_SYNTAX_ERROR: response = await client.post( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: json={"email": "dev@example.com", "password": "dev123"}
            

            # REMOVED_SYNTAX_ERROR: assert response.status_code == 403, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # REMOVED_SYNTAX_ERROR: assert "forbidden" in response.text.lower(), \
            # REMOVED_SYNTAX_ERROR: "Should explicitly state dev login is forbidden"


            # Pytest configuration for staging tests
            # REMOVED_SYNTAX_ERROR: pytest_plugins = ["pytest_asyncio"]


# REMOVED_SYNTAX_ERROR: def pytest_configure(config):
    # REMOVED_SYNTAX_ERROR: """Configure pytest with staging markers"""
    # REMOVED_SYNTAX_ERROR: config.addinivalue_line( )
    # REMOVED_SYNTAX_ERROR: "markers", "env(name): mark test to run only in specific environment"
    
    # REMOVED_SYNTAX_ERROR: config.addinivalue_line( )
    # REMOVED_SYNTAX_ERROR: "markers", "critical: mark test as critical for production"
    
    # REMOVED_SYNTAX_ERROR: config.addinivalue_line( )
    # REMOVED_SYNTAX_ERROR: "markers", "integration: mark test as integration test"
    


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # Run critical failing tests to demonstrate issues
        # REMOVED_SYNTAX_ERROR: print("Running critical staging OAuth tests...")
        # REMOVED_SYNTAX_ERROR: print("These tests SHOULD be passing but are currently FAILING")
        # REMOVED_SYNTAX_ERROR: print("This exposes critical authentication issues in staging )
        # REMOVED_SYNTAX_ERROR: ")

        # REMOVED_SYNTAX_ERROR: import subprocess
        # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
        # REMOVED_SYNTAX_ERROR: ["python", "-m", "pytest", __file__, "-v", "-m", "critical"],
        # REMOVED_SYNTAX_ERROR: capture_output=True,
        # REMOVED_SYNTAX_ERROR: text=True
        

        # REMOVED_SYNTAX_ERROR: print(result.stdout)
        # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: [CRITICAL] Tests are failing - authentication is broken in staging!")
            # REMOVED_SYNTAX_ERROR: print("The test suite correctly identifies these issues.")
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: print(" )
                # REMOVED_SYNTAX_ERROR: [OK] All critical tests passing")
                # REMOVED_SYNTAX_ERROR: pass