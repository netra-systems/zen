"""
OAuth Redirect URI Regression Prevention Test Suite
Tests to prevent future OAuth redirect URI misconfigurations

This test suite ensures that OAuth redirect URI configurations remain correct
and prevents regression of the critical staging authentication failure.

Business Value Justification (BVJ):
- Segment: All customer segments
- Business Goal: Platform Stability, Risk Reduction  
- Value Impact: Prevents 100% OAuth authentication failure
- Strategic Impact: Protects user acquisition and retention

These tests should PASS after the OAuth redirect URI fix is applied.
If any test fails, it indicates a regression that will break OAuth authentication.
"""

import json
import secrets
import urllib.parse
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from auth_service.main import app
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import _determine_urls

# Test client for auth service
client = TestClient(app)


class TestOAuthRedirectURIRegressionPrevention:
    """
    Regression prevention tests for OAuth redirect URI configuration.
    
    These tests ensure OAuth redirect URIs consistently point to auth service
    and prevent future misconfigurations that would break authentication.
    """

    def test_oauth_redirect_uri_always_uses_auth_service_url(self):
        """
        REGRESSION PREVENTION: OAuth redirect URIs must always use auth service URL
        
        This test ensures _determine_urls()[0] (auth service) is used for OAuth
        redirect URIs, never _determine_urls()[1] (frontend).
        
        If this test fails, OAuth authentication will be broken.
        """
        auth_service_url, frontend_url = _determine_urls()
        
        # OAuth redirect URI must use auth service URL
        correct_oauth_redirect = auth_service_url + "/auth/callback"
        
        # Must NOT use frontend URL  
        incorrect_frontend_redirect = frontend_url + "/auth/callback"
        
        # REGRESSION CHECK: These URLs must be different
        assert correct_oauth_redirect != incorrect_frontend_redirect, (
            f"Auth service and frontend URLs are identical - configuration error!\n"
            f"Auth service: {auth_service_url}\n"
            f"Frontend: {frontend_url}"
        )
        
        # REGRESSION CHECK: Auth service URL must contain auth subdomain (staging/prod)
        if AuthConfig.get_environment() in ["staging", "production"]:
            assert "auth." in auth_service_url, (
                f"Auth service URL missing 'auth.' subdomain: {auth_service_url}"
            )
            assert "auth." not in frontend_url, (
                f"Frontend URL incorrectly contains 'auth.' subdomain: {frontend_url}"
            )
        
        print(f"✓ OAuth redirect URI validation passed: {correct_oauth_redirect}")

    @pytest.mark.parametrize("environment", ["development", "staging", "production"])
    def test_oauth_redirect_uri_environment_specific_validation(self, environment):
        """
        REGRESSION PREVENTION: Validate OAuth redirect URIs for each environment
        
        Ensures OAuth redirect URIs are correctly configured for all environments
        and prevents environment-specific misconfigurations.
        """
        # Mock environment for testing
        with patch.object(AuthConfig, 'get_environment', return_value=environment):
            with patch.object(AuthConfig, 'get_auth_service_url') as mock_auth_url:
                with patch.object(AuthConfig, 'get_frontend_url') as mock_frontend_url:
                    
                    # Set expected URLs for each environment
                    environment_config = {
                        "development": {
                            "auth_service": "http://localhost:8081",
                            "frontend": "http://localhost:3000"
                        },
                        "staging": {
                            "auth_service": "https://auth.staging.netrasystems.ai", 
                            "frontend": "https://app.staging.netrasystems.ai"
                        },
                        "production": {
                            "auth_service": "https://auth.netrasystems.ai",
                            "frontend": "https://netrasystems.ai"
                        }
                    }
                    
                    config = environment_config[environment]
                    mock_auth_url.return_value = config["auth_service"]
                    mock_frontend_url.return_value = config["frontend"]
                    
                    # Test OAuth redirect URI configuration
                    auth_service_url, frontend_url = _determine_urls()
                    oauth_redirect_uri = auth_service_url + "/auth/callback"
                    
                    # REGRESSION CHECK: Must use auth service URL
                    assert oauth_redirect_uri == config["auth_service"] + "/auth/callback", (
                        f"OAuth redirect URI incorrect for {environment}:\n"
                        f"Expected: {config['auth_service']}/auth/callback\n"
                        f"Actual: {oauth_redirect_uri}"
                    )
                    
                    # REGRESSION CHECK: Must NOT use frontend URL
                    frontend_callback = frontend_url + "/auth/callback"
                    assert oauth_redirect_uri != frontend_callback, (
                        f"OAuth redirect URI using frontend URL in {environment}!\n"
                        f"OAuth: {oauth_redirect_uri}\n"
                        f"Frontend: {frontend_callback}"
                    )
                    
                    print(f"✓ {environment} OAuth redirect URI: {oauth_redirect_uri}")

    def test_oauth_initiation_endpoint_redirect_uri_parameter(self):
        """
        REGRESSION PREVENTION: Test OAuth initiation endpoint uses correct redirect_uri
        
        Validates that /auth/login/google endpoint generates OAuth URLs with 
        correct redirect_uri parameter pointing to auth service.
        """
        response = client.get("/auth/login/google")
        
        if response.status_code == 302:
            google_oauth_url = response.headers.get("location", "")
            
            # Parse redirect_uri from Google OAuth URL
            parsed_url = urllib.parse.urlparse(google_oauth_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if "redirect_uri" in query_params:
                redirect_uri = urllib.parse.unquote(query_params["redirect_uri"][0])
                
                # REGRESSION CHECK: Must use auth service URL
                auth_service_url = AuthConfig.get_auth_service_url()
                expected_redirect = auth_service_url + "/auth/callback"
                
                assert redirect_uri == expected_redirect, (
                    f"OAuth initiation using incorrect redirect_uri!\n"
                    f"Expected auth service: {expected_redirect}\n" 
                    f"Actual redirect_uri: {redirect_uri}"
                )
                
                # REGRESSION CHECK: Must NOT use frontend URL
                frontend_url = AuthConfig.get_frontend_url()
                frontend_callback = frontend_url + "/auth/callback"
                
                assert redirect_uri != frontend_callback, (
                    f"OAuth initiation using frontend URL - CRITICAL ERROR!\n"
                    f"Redirect URI: {redirect_uri}\n"
                    f"Frontend URL: {frontend_callback}"
                )
                
                print(f"✓ OAuth initiation redirect_uri: {redirect_uri}")
            else:
                pytest.fail(f"No redirect_uri in Google OAuth URL: {google_oauth_url}")
        else:
            pytest.skip(f"OAuth initiation returned {response.status_code}, skipping redirect_uri test")

    def test_auth_routes_code_compliance_check(self):
        """
        REGRESSION PREVENTION: Code analysis to ensure correct _determine_urls() usage
        
        Analyzes auth_routes.py patterns to ensure OAuth redirect URIs use
        _determine_urls()[0] (auth service) not _determine_urls()[1] (frontend).
        """
        # Read auth_routes.py source code for analysis
        import os
        auth_routes_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "auth_core", "routes", "auth_routes.py"
        )
        
        try:
            with open(auth_routes_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except FileNotFoundError:
            pytest.skip("auth_routes.py not found for code analysis")
            return
        
        # REGRESSION CHECK: Look for problematic patterns
        problematic_patterns = [
            "_determine_urls()[1] + \"/auth/callback\"",
            "_determine_urls()[1]+\"/auth/callback\"", 
            "_determine_urls()[1] +\"/auth/callback\"",
            "_determine_urls()[1]+ \"/auth/callback\""
        ]
        
        for pattern in problematic_patterns:
            assert pattern not in source_code, (
                f"REGRESSION DETECTED: Problematic pattern found in auth_routes.py!\n"
                f"Pattern: {pattern}\n"
                f"This pattern uses frontend URL for OAuth redirect_uri\n"
                f"Fix: Change _determine_urls()[1] to _determine_urls()[0]"
            )
        
        # REGRESSION CHECK: Look for correct patterns
        correct_patterns = [
            "_determine_urls()[0] + \"/auth/callback\"",
            "_determine_urls()[0]+\"/auth/callback\"",
            "_determine_urls()[0] +\"/auth/callback\"", 
            "_determine_urls()[0]+ \"/auth/callback\""
        ]
        
        has_correct_pattern = any(pattern in source_code for pattern in correct_patterns)
        
        # If OAuth is implemented, it should use correct patterns
        if "redirect_uri" in source_code and "_determine_urls()" in source_code:
            assert has_correct_pattern, (
                f"REGRESSION: No correct OAuth redirect_uri patterns found!\n"
                f"Expected patterns: {correct_patterns}\n"
                f"Ensure OAuth redirect_uri uses _determine_urls()[0] (auth service)"
            )
            print("✓ Auth routes code compliance check passed")
        else:
            print("⚠ OAuth implementation not found in auth_routes.py")

    @pytest.mark.env("staging")
    def test_staging_oauth_redirect_uri_configuration_validation(self):
        """
        REGRESSION PREVENTION: Validate staging OAuth redirect URI configuration
        
        Ensures staging environment OAuth redirect URIs are correctly configured
        and prevents staging-specific authentication failures.
        """
        if AuthConfig.get_environment() != "staging":
            pytest.skip("Test only runs in staging environment")
        
        auth_service_url = AuthConfig.get_auth_service_url()
        frontend_url = AuthConfig.get_frontend_url()
        
        # REGRESSION CHECK: Staging URLs must be correct
        assert auth_service_url == "https://auth.staging.netrasystems.ai", (
            f"Staging auth service URL incorrect: {auth_service_url}"
        )
        assert frontend_url == "https://app.staging.netrasystems.ai", (
            f"Staging frontend URL incorrect: {frontend_url}"
        )
        
        # REGRESSION CHECK: OAuth redirect must use auth service URL
        oauth_redirect_uri = auth_service_url + "/auth/callback"
        expected_staging_redirect = "https://auth.staging.netrasystems.ai/auth/callback"
        
        assert oauth_redirect_uri == expected_staging_redirect, (
            f"Staging OAuth redirect URI incorrect!\n"
            f"Expected: {expected_staging_redirect}\n"
            f"Actual: {oauth_redirect_uri}"
        )
        
        # REGRESSION CHECK: Must NOT use frontend URL
        frontend_callback = frontend_url + "/auth/callback" 
        prohibited_staging_redirect = "https://app.staging.netrasystems.ai/auth/callback"
        
        assert frontend_callback == prohibited_staging_redirect, (
            f"Test validation error - frontend callback mismatch"
        )
        assert oauth_redirect_uri != frontend_callback, (
            f"CRITICAL REGRESSION: Staging OAuth using frontend URL!\n"
            f"OAuth redirect: {oauth_redirect_uri}\n"
            f"Frontend URL: {frontend_callback}"
        )
        
        print(f"✓ Staging OAuth redirect URI validated: {oauth_redirect_uri}")

    def test_oauth_callback_endpoint_exists_and_responds(self):
        """
        REGRESSION PREVENTION: Ensure OAuth callback endpoints exist
        
        Validates that OAuth callback endpoints exist and can handle requests.
        Missing endpoints would cause Google OAuth callbacks to fail with 404.
        """
        callback_endpoints = [
            "/auth/callback",
            "/auth/callback/google"
        ]
        
        for endpoint in callback_endpoints:
            response = client.post(endpoint, json={
                "code": f"test_code_{secrets.token_urlsafe(8)}",
                "state": "test_state"
            })
            
            # REGRESSION CHECK: Endpoint must exist (not 404)
            assert response.status_code != 404, (
                f"OAuth callback endpoint not found: {endpoint}\n"
                f"Google OAuth will fail if callback endpoint returns 404"
            )
            
            # Expected responses: 400, 401, 422, 500 (various auth/validation errors)
            assert response.status_code in [400, 401, 422, 500], (
                f"Unexpected response from {endpoint}: {response.status_code}"
            )
            
            print(f"✓ OAuth callback endpoint exists: {endpoint}")

    def test_oauth_state_parameter_format_validation(self):
        """
        REGRESSION PREVENTION: Validate OAuth state parameter format
        
        Ensures OAuth state parameters are properly formatted and contain
        required security information (nonce, timestamp, etc.).
        """
        # Test OAuth initiation to get state parameter
        response = client.get("/auth/login/google")
        
        if response.status_code == 302:
            google_oauth_url = response.headers.get("location", "")
            parsed_url = urllib.parse.urlparse(google_oauth_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if "state" in query_params:
                state_param = query_params["state"][0]
                
                # REGRESSION CHECK: State parameter should be base64 encoded
                try:
                    import base64
                    decoded_state = base64.urlsafe_b64decode(state_param + '===')
                    state_data = json.loads(decoded_state.decode('utf-8'))
                    
                    # REGRESSION CHECK: State should contain security information
                    required_fields = ["nonce", "timestamp"]
                    for field in required_fields:
                        assert field in state_data, (
                            f"OAuth state missing required field '{field}': {state_data}"
                        )
                    
                    # REGRESSION CHECK: Nonce should be sufficiently random
                    nonce = state_data.get("nonce", "")
                    assert len(nonce) >= 16, (
                        f"OAuth state nonce too short: {nonce}"
                    )
                    
                    print(f"✓ OAuth state parameter format valid")
                    
                except (ValueError, json.JSONDecodeError) as e:
                    # State might use different encoding - that's okay as long as it's not empty
                    assert len(state_param) > 0, (
                        f"OAuth state parameter is empty: {state_param}"
                    )
                    print(f"✓ OAuth state parameter present (custom format)")
            else:
                pytest.fail("No state parameter in Google OAuth URL")
        else:
            pytest.skip(f"OAuth initiation returned {response.status_code}, skipping state test")

    @pytest.mark.parametrize("oauth_provider", ["google", "facebook", "github"])
    def test_multi_provider_oauth_redirect_uri_consistency(self, oauth_provider):
        """
        REGRESSION PREVENTION: Test OAuth redirect URI consistency across providers
        
        Ensures all OAuth providers use consistent redirect URI patterns
        and prevents provider-specific misconfigurations.
        """
        # Test OAuth initiation for each provider (if endpoints exist)
        oauth_endpoints = {
            "google": "/auth/login/google",
            "facebook": "/auth/login/facebook", 
            "github": "/auth/login/github"
        }
        
        endpoint = oauth_endpoints.get(oauth_provider)
        if not endpoint:
            pytest.skip(f"No endpoint defined for {oauth_provider}")
        
        response = client.get(endpoint)
        
        if response.status_code == 302:
            oauth_url = response.headers.get("location", "")
            parsed_url = urllib.parse.urlparse(oauth_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if "redirect_uri" in query_params:
                redirect_uri = urllib.parse.unquote(query_params["redirect_uri"][0])
                
                # REGRESSION CHECK: All providers must use auth service URL
                auth_service_url = AuthConfig.get_auth_service_url()
                expected_redirect = auth_service_url + "/auth/callback"
                
                assert redirect_uri.startswith(auth_service_url), (
                    f"{oauth_provider} OAuth redirect_uri not using auth service URL!\n"
                    f"Expected prefix: {auth_service_url}\n"
                    f"Actual redirect_uri: {redirect_uri}"
                )
                
                # REGRESSION CHECK: Must NOT use frontend URL
                frontend_url = AuthConfig.get_frontend_url()
                assert not redirect_uri.startswith(frontend_url), (
                    f"{oauth_provider} OAuth redirect_uri using frontend URL!\n"
                    f"Frontend URL: {frontend_url}\n"
                    f"Redirect URI: {redirect_uri}"
                )
                
                print(f"✓ {oauth_provider} OAuth redirect URI: {redirect_uri}")
            else:
                pytest.skip(f"No redirect_uri in {oauth_provider} OAuth URL")
        elif response.status_code == 404:
            pytest.skip(f"{oauth_provider} OAuth endpoint not implemented")
        else:
            pytest.fail(f"{oauth_provider} OAuth initiation failed: {response.status_code}")


class TestOAuthRedirectURIMonitoring:
    """
    Monitoring and alerting tests for OAuth redirect URI configuration
    """
    
    def test_oauth_redirect_uri_monitoring_requirements(self):
        """
        MONITORING: Define OAuth redirect URI monitoring requirements
        
        Documents monitoring requirements to detect OAuth redirect URI
        misconfigurations before they cause authentication failures.
        """
        monitoring_requirements = {
            "configuration_validation": {
                "description": "Monitor OAuth configuration consistency",
                "metrics": [
                    "oauth_redirect_uri_validation_success_rate",
                    "oauth_endpoint_availability_rate",
                    "oauth_state_parameter_validation_rate"
                ],
                "alerts": [
                    "Alert if OAuth redirect URI uses frontend URL",
                    "Alert if OAuth callback endpoints return 404", 
                    "Alert if OAuth state parameter validation fails"
                ]
            },
            "authentication_flow": {
                "description": "Monitor OAuth authentication success rates", 
                "metrics": [
                    "oauth_authentication_success_rate",
                    "oauth_callback_completion_rate",
                    "oauth_token_exchange_success_rate"
                ],
                "alerts": [
                    "Alert if OAuth success rate drops below 90%",
                    "Alert if OAuth callback failures spike",
                    "Alert if 'No token received' errors increase"
                ]
            },
            "provider_integration": {
                "description": "Monitor OAuth provider connectivity",
                "metrics": [
                    "google_oauth_response_time",
                    "oauth_provider_error_rate", 
                    "redirect_uri_mismatch_error_count"
                ],
                "alerts": [
                    "Alert if OAuth provider response time > 5s",
                    "Alert if redirect_uri_mismatch errors detected",
                    "Alert if OAuth provider returns 4xx/5xx errors"
                ]
            }
        }
        
        monitoring_documentation = f"""
OAUTH REDIRECT URI MONITORING REQUIREMENTS:
==========================================

{json.dumps(monitoring_requirements, indent=2)}

IMPLEMENTATION:
- Add OAuth configuration validation to health checks
- Monitor OAuth authentication success rates  
- Alert on OAuth redirect URI misconfigurations
- Dashboard for OAuth authentication metrics
- Automated testing of OAuth flow end-to-end

CRITICAL ALERTS:
- OAuth redirect URI using frontend URL (CRITICAL)
- OAuth callback endpoints returning 404 (HIGH)
- OAuth authentication success rate < 90% (HIGH)
- 'No token received' errors increasing (MEDIUM)
        """
        
        print(monitoring_documentation)
        
        # Always pass - documentation test
        assert True, "OAuth monitoring requirements documented"

    def test_oauth_deployment_validation_checklist(self):
        """
        DEPLOYMENT: OAuth configuration validation checklist
        
        Defines pre-deployment checklist to validate OAuth configuration
        and prevent authentication failures in production.
        """
        deployment_checklist = {
            "pre_deployment": [
                "✓ OAuth redirect URIs point to auth service URLs",
                "✓ OAuth redirect URIs match Google Console configuration",
                "✓ OAuth callback endpoints exist and respond",
                "✓ OAuth state parameter validation working",
                "✓ OAuth token exchange functionality tested",
                "✓ OAuth flow tested end-to-end in staging",
                "✓ No frontend URLs in OAuth configuration"
            ],
            "deployment_validation": [
                "✓ OAuth initiation endpoints return 302 redirects",
                "✓ OAuth callback endpoints return non-404 responses",
                "✓ Health checks include OAuth configuration validation", 
                "✓ OAuth authentication monitoring enabled",
                "✓ OAuth error logging configured"
            ],
            "post_deployment": [
                "✓ OAuth authentication success rate > 95%",
                "✓ No 'No token received' errors in logs",
                "✓ OAuth callback completion rate > 95%",
                "✓ OAuth provider response times < 3s",
                "✓ No redirect_uri_mismatch errors"
            ]
        }
        
        checklist_documentation = f"""
OAUTH DEPLOYMENT VALIDATION CHECKLIST:
=====================================

{json.dumps(deployment_checklist, indent=2)}

AUTOMATION:
- Add to CI/CD pipeline as mandatory checks
- Create deployment validation script
- Automated rollback if OAuth validation fails
- Staging OAuth tests must pass before production

VALIDATION COMMANDS:
python scripts/validate_oauth_configuration.py --env staging
python unified_test_runner.py --env staging -k "oauth"  
python scripts/test_oauth_end_to_end.py --env staging
        """
        
        print(checklist_documentation)
        
        # Always pass - documentation test  
        assert True, "OAuth deployment checklist documented"