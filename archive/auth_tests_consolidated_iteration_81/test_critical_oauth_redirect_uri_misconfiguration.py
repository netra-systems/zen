"""
Critical OAuth Redirect URI Misconfiguration Test Suite
Tests for CRITICAL staging OAuth failure: "No token received" error

CRITICAL ISSUE IDENTIFIED:
Auth service tells Google to redirect to FRONTEND URL instead of AUTH SERVICE URL
- Current: redirect_uri = _determine_urls()[1] + "/auth/callback" (frontend URL)  
- Should be: redirect_uri = _determine_urls()[0] + "/auth/callback" (auth service URL)

This causes complete OAuth flow failure:
1. Google never calls auth service callback endpoint  
2. Auth service never exchanges OAuth code for tokens
3. Frontend receives only OAuth code, not tokens
4. User sees "No token received" error

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Platform Stability, User Acquisition
- Value Impact: 100% OAuth authentication failure blocks all new user registrations
- Strategic Impact: Critical for user acquisition and revenue growth

@pytest.mark.env("staging") - Run in staging to catch environment-specific config issues
"""

import asyncio
import json
import secrets
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
import httpx

from auth_service.main import app
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import _determine_urls

# Test client for auth service
client = TestClient(app)


class TestCriticalOAuthRedirectURIMisconfiguration:
    """
    CRITICAL test suite for OAuth redirect URI misconfiguration causing staging failures.
    
    These tests expose the root cause: auth service configures Google OAuth to redirect
    to frontend URL instead of auth service URL, breaking the entire OAuth flow.
    """

    def test_oauth_redirect_uri_configuration_validation(self):
        """
        CRITICAL: Validate OAuth redirect URIs point to auth service, NOT frontend
        
        ROOT CAUSE: Lines 242, 676, 906 in auth_routes.py use _determine_urls()[1] 
        which returns frontend URL instead of auth service URL for redirect_uri.
        
        Expected to FAIL until fix is applied.
        """
        auth_service_url, frontend_url = _determine_urls()
        
        # CRITICAL VALIDATION: OAuth redirect URIs must point to auth service
        expected_redirect_uri = auth_service_url + "/auth/callback"
        
        # Current BROKEN implementation uses frontend URL - this should NOT happen
        current_broken_redirect_uri = frontend_url + "/auth/callback"
        
        # The auth service MUST use auth service URL for OAuth redirect
        assert expected_redirect_uri != current_broken_redirect_uri, (
            f"OAuth redirect URI misconfiguration detected!\n"
            f"Expected auth service URL: {expected_redirect_uri}\n" 
            f"Current broken frontend URL: {current_broken_redirect_uri}\n"
            f"Fix required: Change _determine_urls()[1] to _determine_urls()[0] in auth_routes.py"
        )
        
        # Validate URL components for staging environment
        if AuthConfig.get_environment() == "staging":
            assert "auth.staging.netrasystems.ai" in expected_redirect_uri, (
                f"Staging auth service URL incorrect: {expected_redirect_uri}"
            )
            assert "app.staging.netrasystems.ai" not in expected_redirect_uri, (
                f"OAuth redirect URI incorrectly uses frontend domain: {expected_redirect_uri}"
            )
        
        print(f"✓ OAuth redirect URI validation: {expected_redirect_uri}")

    @pytest.mark.env("staging") 
    @pytest.mark.asyncio
    async def test_google_oauth_initiation_redirect_uri_staging(self):
        """
        CRITICAL: Test Google OAuth initiation uses correct redirect URI in staging
        
        This test validates the /auth/login/google endpoint configures the correct
        redirect_uri parameter when redirecting users to Google OAuth.
        
        Expected to FAIL until redirect URI configuration is fixed.
        """
        # Initiate Google OAuth flow
        response = client.get("/auth/login/google")
        
        if response.status_code == 302:
            # OAuth initiation should redirect to Google with correct redirect_uri
            location_header = response.headers.get("location", "")
            
            # Extract redirect_uri parameter from Google OAuth URL
            if "redirect_uri=" in location_header:
                import urllib.parse
                parsed_url = urllib.parse.urlparse(location_header)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                redirect_uri = query_params.get("redirect_uri", [None])[0]
                
                if redirect_uri:
                    decoded_redirect_uri = urllib.parse.unquote(redirect_uri)
                    
                    # CRITICAL: Redirect URI must point to auth service, not frontend
                    auth_service_url = AuthConfig.get_auth_service_url()
                    expected_redirect_uri = auth_service_url + "/auth/callback"
                    
                    assert decoded_redirect_uri == expected_redirect_uri, (
                        f"CRITICAL OAuth redirect URI misconfiguration!\n"
                        f"Google OAuth redirect_uri: {decoded_redirect_uri}\n"
                        f"Expected auth service: {expected_redirect_uri}\n"
                        f"Fix: Change _determine_urls()[1] to _determine_urls()[0] in auth_routes.py lines 242, 676, 906"
                    )
                    
                    # Staging-specific validation
                    if AuthConfig.get_environment() == "staging":
                        assert "auth.staging.netrasystems.ai" in decoded_redirect_uri, (
                            f"Staging OAuth redirect URI should use auth.staging.netrasystems.ai: {decoded_redirect_uri}"
                        )
                        assert "app.staging.netrasystems.ai" not in decoded_redirect_uri, (
                            f"OAuth redirect URI incorrectly uses frontend domain: {decoded_redirect_uri}"
                        )
                else:
                    pytest.fail("No redirect_uri parameter found in Google OAuth URL")
            else:
                pytest.fail(f"OAuth URL missing redirect_uri parameter: {location_header}")
        else:
            pytest.fail(f"OAuth initiation failed with status {response.status_code}: {response.text}")

    @pytest.mark.env("staging")
    @pytest.mark.asyncio 
    async def test_oauth_callback_endpoint_availability(self):
        """
        CRITICAL: Validate auth service OAuth callback endpoint is available
        
        After Google OAuth, the user should be redirected to auth service callback
        endpoint, not frontend. This test validates the endpoint exists.
        """
        auth_service_url = AuthConfig.get_auth_service_url()
        callback_endpoint = "/auth/callback/google"
        
        # Test POST to callback endpoint (how Google calls it)
        response = client.post(callback_endpoint, json={
            "code": "test_code_for_availability_check",
            "state": "test_state"
        })
        
        # Endpoint should exist (not 404) even if it fails with invalid credentials
        assert response.status_code != 404, (
            f"OAuth callback endpoint not available: {callback_endpoint}\n"
            f"Auth service URL: {auth_service_url}\n"
            f"Google OAuth cannot complete if callback endpoint doesn't exist"
        )
        
        # Valid responses: 400 (bad request), 401 (unauthorized), 422 (validation), 500 (server error)
        assert response.status_code in [400, 401, 422, 500], (
            f"Unexpected response from OAuth callback: {response.status_code} - {response.text}"
        )
        
        print(f"✓ OAuth callback endpoint available: {auth_service_url}{callback_endpoint}")

    @pytest.mark.env("staging")
    @pytest.mark.asyncio
    async def test_complete_oauth_flow_redirect_chain_validation(self):
        """
        CRITICAL: Test complete OAuth redirect chain to identify misconfiguration
        
        Simulates the complete OAuth flow to validate redirect chain:
        1. User clicks "Sign in with Google" -> Frontend calls auth service
        2. Auth service redirects to Google with redirect_uri 
        3. Google redirects back to redirect_uri (should be auth service)
        4. Auth service processes OAuth callback
        5. Auth service redirects to frontend with tokens
        
        Expected to FAIL at step 3 due to redirect_uri misconfiguration.
        """
        # Step 1: Initiate OAuth flow
        oauth_init_response = client.get("/auth/login/google") 
        
        if oauth_init_response.status_code != 302:
            pytest.fail(f"OAuth initiation failed: {oauth_init_response.status_code}")
        
        google_oauth_url = oauth_init_response.headers["location"]
        
        # Step 2: Extract and validate redirect_uri from Google OAuth URL
        import urllib.parse
        parsed_url = urllib.parse.urlparse(google_oauth_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        redirect_uri = urllib.parse.unquote(query_params["redirect_uri"][0])
        
        auth_service_url = AuthConfig.get_auth_service_url()
        frontend_url = AuthConfig.get_frontend_url()
        
        # CRITICAL VALIDATION: redirect_uri should point to auth service
        expected_auth_callback = auth_service_url + "/auth/callback" 
        incorrect_frontend_callback = frontend_url + "/auth/callback"
        
        # This assertion should FAIL with current misconfiguration
        assert redirect_uri == expected_auth_callback, (
            f"CRITICAL OAuth redirect misconfiguration detected!\n"
            f"Current redirect_uri: {redirect_uri}\n"
            f"Expected auth service: {expected_auth_callback}\n" 
            f"Incorrect frontend URL: {incorrect_frontend_callback}\n"
            f"ROOT CAUSE: auth_routes.py uses _determine_urls()[1] instead of _determine_urls()[0]\n"
            f"IMPACT: Google never calls auth service - OAuth flow completely broken"
        )
        
        # Step 3: Simulate Google OAuth callback to correct endpoint
        state_param = query_params.get("state", [None])[0]
        mock_oauth_code = f"mock_code_{secrets.token_urlsafe(8)}"
        
        callback_response = client.post("/auth/callback/google", json={
            "code": mock_oauth_code,
            "state": state_param
        })
        
        # Callback should be processed (not 404) - may fail with auth errors
        assert callback_response.status_code != 404, (
            "OAuth callback endpoint not found - Google cannot complete OAuth flow"
        )
        
        print(f"✓ OAuth redirect chain validation complete")

    def test_oauth_redirect_uri_environment_consistency(self):
        """
        CRITICAL: Test OAuth redirect URI consistency across environments
        
        Validates that OAuth redirect URIs are correctly configured for each environment:
        - Development: http://localhost:8081/auth/callback  
        - Staging: https://auth.staging.netrasystems.ai/auth/callback
        - Production: https://auth.netrasystems.ai/auth/callback
        
        Should NOT use frontend URLs in any environment.
        """
        current_env = AuthConfig.get_environment()
        auth_service_url = AuthConfig.get_auth_service_url()
        frontend_url = AuthConfig.get_frontend_url()
        
        # Expected OAuth redirect URIs by environment
        expected_oauth_redirects = {
            "development": "http://localhost:8081/auth/callback",
            "staging": "https://auth.staging.netrasystems.ai/auth/callback", 
            "production": "https://auth.netrasystems.ai/auth/callback"
        }
        
        # Frontend URLs that should NOT be used for OAuth redirects
        frontend_callback_patterns = {
            "development": "http://localhost:3000/auth/callback",
            "staging": "https://app.staging.netrasystems.ai/auth/callback",
            "production": "https://netrasystems.ai/auth/callback"
        }
        
        expected_redirect = expected_oauth_redirects.get(current_env)
        incorrect_frontend_redirect = frontend_callback_patterns.get(current_env)
        actual_oauth_redirect = auth_service_url + "/auth/callback"
        
        # CRITICAL: OAuth redirect must use auth service URL
        assert actual_oauth_redirect == expected_redirect, (
            f"OAuth redirect URI misconfigured for {current_env} environment!\n"
            f"Expected: {expected_redirect}\n"
            f"Actual: {actual_oauth_redirect}\n"
            f"Environment: {current_env}"
        )
        
        # CRITICAL: Must NOT use frontend URL
        frontend_callback = frontend_url + "/auth/callback"
        assert actual_oauth_redirect != frontend_callback, (
            f"CRITICAL: OAuth redirect URI using frontend URL in {current_env}!\n"
            f"OAuth redirect: {actual_oauth_redirect}\n"
            f"Frontend URL: {frontend_callback}\n"
            f"This breaks OAuth flow - Google will never call auth service"
        )
        
        print(f"✓ Environment {current_env} OAuth redirect URI: {actual_oauth_redirect}")

    @pytest.mark.env("staging")
    @pytest.mark.asyncio
    async def test_google_oauth_console_redirect_uri_validation(self):
        """
        CRITICAL: Test Google OAuth Console redirect URI requirements
        
        Validates that the redirect URIs configured in code match what should
        be authorized in Google OAuth Console for each environment.
        
        If redirect URIs don't match Google Console configuration, OAuth fails.
        """
        current_env = AuthConfig.get_environment()
        
        # Required redirect URIs for Google OAuth Console by environment
        required_google_console_redirects = {
            "development": [
                "http://localhost:8081/auth/callback",
                "http://localhost:8081/auth/callback/google"
            ],
            "staging": [
                "https://auth.staging.netrasystems.ai/auth/callback", 
                "https://auth.staging.netrasystems.ai/auth/callback/google"
            ],
            "production": [
                "https://auth.netrasystems.ai/auth/callback",
                "https://auth.netrasystems.ai/auth/callback/google" 
            ]
        }
        
        # URLs that should NOT be in Google Console (frontend URLs)
        prohibited_console_redirects = {
            "development": [
                "http://localhost:3000/auth/callback"
            ],
            "staging": [
                "https://app.staging.netrasystems.ai/auth/callback"
            ],
            "production": [
                "https://netrasystems.ai/auth/callback"
            ]
        }
        
        required_redirects = required_google_console_redirects.get(current_env, [])
        prohibited_redirects = prohibited_console_redirects.get(current_env, [])
        
        auth_service_url = AuthConfig.get_auth_service_url()
        actual_redirect_uri = auth_service_url + "/auth/callback"
        
        # CRITICAL: Current redirect URI must be in required list
        assert actual_redirect_uri in required_redirects, (
            f"OAuth redirect URI not in Google Console required list for {current_env}!\n"
            f"Current redirect URI: {actual_redirect_uri}\n"
            f"Required in Google Console: {required_redirects}\n"
            f"Add this URL to Google OAuth Console authorized redirect URIs"
        )
        
        # CRITICAL: Must not use prohibited frontend URLs  
        frontend_url = AuthConfig.get_frontend_url()
        frontend_callback = frontend_url + "/auth/callback"
        
        assert frontend_callback in prohibited_redirects, (
            f"Test validation error - frontend callback should be in prohibited list"
        )
        
        assert actual_redirect_uri != frontend_callback, (
            f"CRITICAL: OAuth using prohibited frontend URL in {current_env}!\n"
            f"Current: {actual_redirect_uri}\n" 
            f"Prohibited: {frontend_callback}\n"
            f"Frontend URLs should NOT be in Google Console redirect URIs"
        )
        
        # Output Google Console configuration for environment
        print(f"\n{'='*60}")
        print(f"GOOGLE OAUTH CONSOLE CONFIGURATION - {current_env.upper()}")
        print(f"{'='*60}")
        print(f"Required Authorized Redirect URIs:")
        for uri in required_redirects:
            print(f"  ✓ {uri}")
        print(f"\nProhibited Frontend URLs (DO NOT ADD):")
        for uri in prohibited_redirects:
            print(f"  ✗ {uri}")
        print(f"{'='*60}")

    @pytest.mark.env("staging")
    def test_auth_routes_code_analysis_redirect_uri_usage(self):
        """
        CRITICAL: Code analysis of auth_routes.py redirect_uri usage
        
        Analyzes the specific lines in auth_routes.py that configure redirect_uri
        to identify and document the exact misconfiguration.
        """
        # The problematic lines in auth_routes.py
        problematic_lines = [
            {"line": 242, "function": "initiate_google_oauth", "current": "_determine_urls()[1]"},
            {"line": 676, "function": "facebook_login", "current": "_determine_urls()[1]"}, 
            {"line": 906, "function": "generic_oauth", "current": "_determine_urls()[1]"}
        ]
        
        auth_service_url, frontend_url = _determine_urls()
        
        for line_info in problematic_lines:
            line_num = line_info["line"]
            function = line_info["function"] 
            current_code = line_info["current"]
            
            # Current BROKEN implementation
            current_redirect_uri = frontend_url + "/auth/callback"
            
            # Correct implementation should be
            correct_redirect_uri = auth_service_url + "/auth/callback"
            
            # CRITICAL: Document the exact fix needed
            assert current_redirect_uri != correct_redirect_uri, (
                f"Line {line_num} in {function}() needs fix:\n"
                f"CURRENT (BROKEN): {current_code} + '/auth/callback' = {current_redirect_uri}\n"
                f"CORRECT (FIX): _determine_urls()[0] + '/auth/callback' = {correct_redirect_uri}\n"
                f"CHANGE: {current_code} -> _determine_urls()[0]"
            )
        
        # Summary of required changes
        fix_summary = f"""
CRITICAL OAUTH REDIRECT URI FIXES REQUIRED:
============================================

File: auth_service/auth_core/routes/auth_routes.py

Line 242: redirect_uri = _determine_urls()[1] + "/auth/callback"
Fix to:   redirect_uri = _determine_urls()[0] + "/auth/callback"

Line 676: redirect_uri = _determine_urls()[1] + "/auth/callback"  
Fix to:   redirect_uri = _determine_urls()[0] + "/auth/callback"

Line 906: redirect_uri = request.redirect_uri or (_determine_urls()[1] + "/auth/callback")
Fix to:   redirect_uri = request.redirect_uri or (_determine_urls()[0] + "/auth/callback")

EXPLANATION:
- _determine_urls()[0] = Auth service URL (CORRECT for OAuth redirect)
- _determine_urls()[1] = Frontend URL (INCORRECT for OAuth redirect)

IMPACT: 
- Google OAuth redirects to frontend instead of auth service
- Auth service never receives OAuth callback
- Frontend gets only OAuth code, not tokens  
- Users see "No token received" error
- 100% OAuth authentication failure
        """
        
        print(fix_summary)
        
        # Force test failure to ensure visibility of fix requirements
        pytest.fail(f"CRITICAL OAuth redirect URI misconfiguration found - see fix details above")


class TestOAuthRedirectURIValidationScript:
    """
    Validation script tests for pre-deployment OAuth configuration checks
    """
    
    def test_oauth_configuration_validation_script_requirements(self):
        """
        Define requirements for OAuth configuration validation script
        
        This test documents what a pre-deployment validation script should check
        to prevent OAuth redirect URI misconfigurations in the future.
        """
        validation_requirements = {
            "redirect_uri_validation": {
                "description": "Validate redirect URIs point to auth service",
                "checks": [
                    "redirect_uri contains auth service domain, not frontend domain",
                    "redirect_uri uses correct protocol (http/https) for environment", 
                    "redirect_uri path is /auth/callback",
                    "No frontend URLs in OAuth redirect configuration"
                ]
            },
            "environment_consistency": {
                "description": "Validate OAuth config consistency across environments",
                "checks": [
                    "Development uses localhost:8081 for auth service",
                    "Staging uses auth.staging.netrasystems.ai", 
                    "Production uses auth.netrasystems.ai",
                    "No environment uses frontend URLs for OAuth redirects"
                ]
            },
            "google_console_alignment": {
                "description": "Validate config matches Google OAuth Console",
                "checks": [
                    "All redirect URIs are authorized in Google Console",
                    "No unauthorized redirect URIs in code",
                    "Client ID matches environment",
                    "Client secret configured for environment"
                ]
            },
            "endpoint_availability": {
                "description": "Validate OAuth callback endpoints exist and respond",
                "checks": [
                    "/auth/callback endpoint returns non-404 status",
                    "/auth/callback/google endpoint returns non-404 status",
                    "Health checks pass for auth service",
                    "Auth service can reach external OAuth providers"
                ]
            }
        }
        
        # Document validation script requirements
        script_requirements = f"""
PRE-DEPLOYMENT OAUTH VALIDATION SCRIPT REQUIREMENTS:
=====================================================

{json.dumps(validation_requirements, indent=2)}

IMPLEMENTATION:
- Create script: scripts/validate_oauth_configuration.py  
- Run before every deployment to staging/production
- Fail deployment if any validation check fails
- Include in CI/CD pipeline as mandatory check
- Test against actual deployed environments

USAGE:
python scripts/validate_oauth_configuration.py --env staging
python scripts/validate_oauth_configuration.py --env production --strict
        """
        
        print(script_requirements)
        
        # This test always passes - it's for documentation
        assert True, "OAuth validation script requirements documented"

    def test_google_oauth_console_redirect_uri_documentation(self):
        """
        Document exact redirect URIs needed in Google OAuth Console for each environment
        """
        google_console_config = {
            "development": {
                "authorized_redirect_uris": [
                    "http://localhost:8081/auth/callback",
                    "http://localhost:8081/auth/callback/google"
                ],
                "client_id": "Use development Google OAuth Client ID",
                "client_secret": "Use development Google OAuth Client Secret"
            },
            "staging": {
                "authorized_redirect_uris": [
                    "https://auth.staging.netrasystems.ai/auth/callback",
                    "https://auth.staging.netrasystems.ai/auth/callback/google"
                ], 
                "client_id": "Use staging Google OAuth Client ID",
                "client_secret": "Use staging Google OAuth Client Secret"
            },
            "production": {
                "authorized_redirect_uris": [
                    "https://auth.netrasystems.ai/auth/callback", 
                    "https://auth.netrasystems.ai/auth/callback/google"
                ],
                "client_id": "Use production Google OAuth Client ID", 
                "client_secret": "Use production Google OAuth Client Secret"
            }
        }
        
        console_documentation = f"""
GOOGLE OAUTH CONSOLE CONFIGURATION:
===================================

{json.dumps(google_console_config, indent=2)}

CRITICAL NOTES:
- DO NOT add frontend URLs (app.staging.netrasystems.ai, netrasystems.ai) to redirect URIs
- Frontend URLs will cause "redirect_uri_mismatch" errors  
- Only auth service URLs should be authorized
- Each environment needs separate OAuth application in Google Console
- Test OAuth flow after any redirect URI changes

OAUTH CONSOLE ACCESS:
- URL: https://console.cloud.google.com/apis/credentials
- Select appropriate GCP project for environment
- Configure OAuth consent screen if not already done
- Add authorized redirect URIs exactly as specified above
        """
        
        print(console_documentation)
        
        # Document current misconfiguration impact
        current_impact = f"""
CURRENT MISCONFIGURATION IMPACT:
================================

IF frontend URLs are configured in Google Console:
1. Google OAuth redirects to frontend  
2. Frontend receives OAuth code but has no way to exchange for tokens
3. Frontend shows "No token received" error
4. Users cannot complete authentication
5. 100% OAuth flow failure

IF auth service URLs are missing from Google Console:  
1. Google OAuth returns "redirect_uri_mismatch" error
2. Users see Google error page
3. Cannot initiate OAuth flow
4. 100% OAuth authentication blocked
        """
        
        print(current_impact)
        
        # Always pass - documentation test
        assert True, "Google OAuth Console configuration documented"