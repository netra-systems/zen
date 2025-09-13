from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""Test OAuth configuration issues found in staging.



These tests reproduce the missing Google OAuth credentials issues that

prevent OAuth authentication flows from working in staging environment.



Based on staging audit findings:

- Missing GOOGLE_CLIENT_ID environment variable

- Missing GOOGLE_CLIENT_SECRET environment variable  

- OAuth configuration incomplete for staging deployment

"""



import pytest

import os

import asyncio

import aiohttp

import requests

from typing import Dict, List, Optional

from test_framework.environment_markers import staging_only, env_requires





env = get_env()

class TestOAuthConfiguration:

    """Test OAuth configuration and credential issues in staging."""



    @staging_only

    @env_requires(services=["auth_service"])

    @pytest.mark.auth

    @pytest.mark.e2e

    def test_google_oauth_client_id_missing_from_environment(self):

        """Test that GOOGLE_CLIENT_ID is missing from staging environment.

        

        This test SHOULD FAIL, demonstrating that the required Google OAuth

        Client ID environment variable is not configured in staging.

        

        Expected failure: GOOGLE_CLIENT_ID environment variable not set

        """

        # Check for various possible OAuth client ID variable names

        oauth_client_id_vars = [

            "GOOGLE_CLIENT_ID",

            "GOOGLE_OAUTH_CLIENT_ID", 

            "GOOGLE_OAUTH_CLIENT_ID_STAGING",

            "OAUTH_GOOGLE_CLIENT_ID"

        ]

        

        missing_credentials = []

        found_credentials = {}

        

        for var_name in oauth_client_id_vars:

            if not client_id:

                missing_credentials.append({

                    "variable": var_name,

                    "issue": "Environment variable not set",

                    "impact": "OAuth authentication will fail"

                })

            else:

                found_credentials[var_name] = {

                    "value": client_id[:20] + "..." if len(client_id) > 20 else client_id,

                    "length": len(client_id)

                }

        

        # This test SHOULD FAIL - expecting missing OAuth credentials

        assert len(missing_credentials) > 0, (

            f"Expected Google OAuth Client ID to be missing from staging environment "

            f"(causing authentication failures), but found credentials: {found_credentials}. "

            f"If credentials are configured, the OAuth issues may be in a different "

            f"configuration area."

        )

        

        # Verify the primary expected variable is missing

        assert not google_client_id, (

            f"Expected GOOGLE_CLIENT_ID to be missing (primary OAuth issue), "

            f"but found value: '{google_client_id[:10]}...' "

            f"This suggests the OAuth configuration issue has been resolved, "

            f"or the problem is in credential validation rather than availability."

        )



    @staging_only 

    @env_requires(services=["auth_service"])

    @pytest.mark.auth

    @pytest.mark.e2e

    def test_google_oauth_client_secret_missing_from_environment(self):

        """Test that GOOGLE_CLIENT_SECRET is missing from staging environment.

        

        This test should FAIL, demonstrating that the required Google OAuth

        Client Secret environment variable is not configured in staging.

        """

        # Check for various possible OAuth client secret variable names

        oauth_client_secret_vars = [

            "GOOGLE_CLIENT_SECRET",

            "GOOGLE_OAUTH_CLIENT_SECRET",

            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", 

            "OAUTH_GOOGLE_CLIENT_SECRET"

        ]

        

        missing_secrets = []

        found_secrets = {}

        

        for var_name in oauth_client_secret_vars:

            if not client_secret:

                missing_secrets.append({

                    "variable": var_name,

                    "issue": "Environment variable not set",

                    "security_impact": "OAuth token exchange impossible"

                })

            else:

                found_secrets[var_name] = {

                    "configured": True,

                    "length": len(client_secret),

                    "value_preview": "***" + client_secret[-4:] if len(client_secret) > 4 else "***"

                }

        

        # This test SHOULD FAIL - expecting missing OAuth secret

        assert len(missing_secrets) > 0, (

            f"Expected Google OAuth Client Secret to be missing from staging "

            f"(causing OAuth token exchange failures), but found configured secrets: "

            f"{list(found_secrets.keys())}. If secrets are configured, the OAuth "

            f"issue may be in credential validation or OAuth flow configuration."

        )

        

        # Verify the primary expected variable is missing  

        assert not google_client_secret, (

            f"Expected GOOGLE_CLIENT_SECRET to be missing (primary OAuth secret issue), "

            f"but secret is configured (length: {len(google_client_secret) if google_client_secret else 0}). "

            f"This suggests the OAuth secret configuration has been resolved."

        )



    @staging_only

    @env_requires(services=["auth_service"])

    @pytest.mark.auth

    @pytest.mark.e2e

    def test_oauth_configuration_incomplete_for_staging_deployment(self):

        """Test that OAuth configuration is incomplete for staging deployment.

        

        This test should FAIL, showing that even if some OAuth credentials exist,

        the overall configuration is incomplete for a functional OAuth flow.

        """

        # Required OAuth configuration for complete staging deployment

        required_oauth_config = {

            "client_credentials": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],

            "redirect_uris": ["GOOGLE_OAUTH_REDIRECT_URI", "OAUTH_CALLBACK_URL"],

            "scopes": ["GOOGLE_OAUTH_SCOPES", "OAUTH_SCOPES"],

            "environment": ["OAUTH_ENVIRONMENT", "STAGING_OAUTH_ENABLED"]

        }

        

        configuration_gaps = []

        

        for config_category, env_vars in required_oauth_config.items():

            category_missing = []

            

            for env_var in env_vars:

                    category_missing.append(env_var)

            

            if category_missing:

                configuration_gaps.append({

                    "category": config_category,

                    "missing_variables": category_missing,

                    "impact": f"{config_category.replace('_', ' ').title()} configuration incomplete"

                })

        

        # This test SHOULD FAIL - expecting incomplete OAuth configuration

        assert len(configuration_gaps) > 0, (

            f"Expected OAuth configuration to be incomplete for staging "

            f"(explaining authentication failures), but all required configuration "

            f"categories appear to be complete: {list(required_oauth_config.keys())}. "

            f"This suggests OAuth configuration issues have been resolved."

        )

        

        # Verify client credentials specifically are missing (primary issue)

        client_creds_missing = [

            gap for gap in configuration_gaps 

            if gap["category"] == "client_credentials"

        ]

        

        assert len(client_creds_missing) >= 1, (

            f"Expected client_credentials (GOOGLE_CLIENT_ID/SECRET) to be missing "

            f"(primary OAuth issue from audit), but got other configuration gaps: "

            f"{configuration_gaps}. Client credentials are the fundamental requirement."

        )



    @staging_only

    @env_requires(services=["auth_service"])

    @pytest.mark.auth

    @pytest.mark.e2e

    async def test_oauth_google_authorization_url_construction_fails(self):

        """Test that OAuth Google authorization URL construction fails.

        

        This test should FAIL, demonstrating that without proper OAuth credentials,

        the auth service cannot construct valid Google OAuth authorization URLs.

        """

        # Simulate OAuth authorization URL construction

        oauth_construction_failures = []

        

        # Required components for Google OAuth URL

        google_oauth_base = "https://accounts.google.com/o/oauth2/auth"

        required_params = {

            "response_type": "code",

            "state": "staging_test_state"

        }

        

        # Check each required parameter

        for param, value in required_params.items():

            if not value:

                oauth_construction_failures.append({

                    "parameter": param,

                    "issue": "Required OAuth parameter missing or empty",

                    "url_component": f"{param}={value}",

                    "impact": "Google OAuth authorization URL cannot be constructed"

                })

        

        # Test URL construction with available parameters

        try:

            oauth_url_params = "&".join([

                f"{param}={value}" for param, value in required_params.items() 

                if value

            ])

            

            if len(oauth_url_params) == 0:

                oauth_construction_failures.append({

                    "issue": "No valid OAuth parameters available",

                    "impact": "Cannot construct any OAuth URL"

                })

            elif len(oauth_construction_failures) > 0:

                oauth_construction_failures.append({

                    "issue": "Partial OAuth URL construction possible",

                    "available_params": [p for p, v in required_params.items() if v],

                    "missing_params": [p for p, v in required_params.items() if not v],

                    "impact": "OAuth flow will fail with incomplete URL"

                })

                

        except Exception as e:

            oauth_construction_failures.append({

                "issue": "OAuth URL construction error",

                "error": str(e),

                "impact": "OAuth URL generation completely broken"

            })

        

        # This test SHOULD FAIL - expecting OAuth URL construction failures

        assert len(oauth_construction_failures) > 0, (

            f"Expected OAuth authorization URL construction to fail due to missing "

            f"credentials (explaining staging authentication issues), but URL "

            f"construction appears to work with available parameters: "

            f"{[p for p, v in required_params.items() if v]}. "

            f"This suggests OAuth credential configuration is complete."

        )

        

        # Verify client_id specifically is causing URL construction failure

        client_id_failures = [

            f for f in oauth_construction_failures 

            if "client_id" in f.get("parameter", "") or "client_id" in str(f)

        ]

        

        assert len(client_id_failures) >= 1, (

            f"Expected GOOGLE_CLIENT_ID to be the primary cause of OAuth URL "

            f"construction failure, but got other OAuth construction issues: "

            f"{oauth_construction_failures}. Client ID is the most critical parameter."

        )



    @staging_only

    @pytest.mark.auth

    @pytest.mark.e2e

    async def test_oauth_token_exchange_endpoint_unreachable(self):

        """Test that OAuth token exchange fails due to configuration issues.

        

        This test should FAIL, showing that even if we could start an OAuth flow,

        the token exchange endpoint cannot be reached or configured properly.

        """

        # Google OAuth token exchange endpoint

        token_endpoint = "https://oauth2.googleapis.com/token"

        

        # Simulate token exchange attempt with missing/invalid credentials

        

        token_exchange_failures = []

        

        # Test 1: Missing credentials for token exchange

        if not client_id:

            token_exchange_failures.append({

                "issue": "GOOGLE_CLIENT_ID missing",

                "impact": "Cannot authenticate with Google OAuth token endpoint"

            })

        

        if not client_secret:

            token_exchange_failures.append({

                "issue": "GOOGLE_CLIENT_SECRET missing", 

                "impact": "Cannot authenticate token exchange request"

            })

        

        # Test 2: Attempt token exchange with available credentials (if any)

        if client_id and client_secret:

            try:

                # Simulate token exchange request (will fail with invalid auth code)

                token_data = {

                    "client_id": client_id,

                    "client_secret": client_secret,

                    "code": "test_auth_code_that_will_fail",

                    "grant_type": "authorization_code",

                }

                

                async with aiohttp.ClientSession() as session:

                    async with session.post(

                        token_endpoint, 

                        data=token_data,

                        timeout=aiohttp.ClientTimeout(total=5.0)

                    ) as response:

                        response_text = await response.text()

                        

                        if response.status == 400:

                            # Expected - invalid auth code, but credentials were accepted

                            token_exchange_failures.append({

                                "issue": "OAuth credentials may be valid but auth code invalid",

                                "status_code": response.status,

                                "response": response_text[:100],

                                "interpretation": "Credentials configured but OAuth flow incomplete"

                            })

                        elif response.status == 401:

                            # Invalid credentials

                            token_exchange_failures.append({

                                "issue": "OAuth credentials rejected by Google",

                                "status_code": response.status,

                                "impact": "GOOGLE_CLIENT_ID/SECRET are invalid"

                            })

                            

            except aiohttp.ClientError as e:

                token_exchange_failures.append({

                    "issue": "Network error during token exchange",

                    "error": str(e),

                    "impact": "OAuth token endpoint unreachable from staging"

                })

            except asyncio.TimeoutError:

                token_exchange_failures.append({

                    "issue": "Token exchange request timeout",

                    "impact": "Google OAuth endpoint not reachable within timeout"

                })

        

        # This test SHOULD FAIL - expecting token exchange issues

        assert len(token_exchange_failures) > 0, (

            f"Expected OAuth token exchange to fail due to configuration issues "

            f"(matching staging authentication failures), but no token exchange "

            f"problems detected. Client ID configured: {bool(client_id)}, "

            f"Client Secret configured: {bool(client_secret)}. "

            f"This suggests OAuth credentials are properly configured."

        )

        

        # Verify we found credential-related failures specifically

        credential_failures = [

            f for f in token_exchange_failures 

            if "CLIENT_ID" in f.get("issue", "") or "CLIENT_SECRET" in f.get("issue", "")

        ]

        

        assert len(credential_failures) >= 1, (

            f"Expected missing GOOGLE_CLIENT_ID/SECRET to be the primary cause "

            f"of token exchange failure, but got other issues: {token_exchange_failures}. "

            f"Credential availability is the fundamental OAuth requirement."

        )



    @staging_only

    @env_requires(services=["auth_service"])

    @pytest.mark.auth

    @pytest.mark.e2e

    def test_oauth_redirect_uri_misconfiguration(self):

        """Test OAuth redirect URI configuration issues in staging.

        

        This test should FAIL, showing that OAuth redirect URIs are not properly

        configured for the staging environment, causing OAuth callback failures.

        """

        # Expected OAuth redirect URIs for staging

        expected_redirect_uris = [

            "https://staging.netrasystems.ai/auth/google/callback",

            "http://localhost:3000/auth/google/callback",  # Development fallback

        ]

        

        redirect_uri_issues = []

        

        # Check configured redirect URI

        if not configured_redirect_uri:

            redirect_uri_issues.append({

                "issue": "GOOGLE_OAUTH_REDIRECT_URI not set",

                "impact": "OAuth callback URL undefined",

                "resolution": "Set redirect URI environment variable"

            })

        

        # Check redirect URI format and accessibility

        for uri in expected_redirect_uris:

            if uri:  # Skip empty URIs

                # Basic URI validation

                if not uri.startswith(("http://", "https://")):

                    redirect_uri_issues.append({

                        "uri": uri,

                        "issue": "Invalid URI scheme",

                        "impact": "Google OAuth will reject redirect URI"

                    })

                

                # Check for staging-appropriate URIs

                    redirect_uri_issues.append({

                        "uri": uri,

                        "issue": "Using localhost URI in non-development environment",

                        "impact": "OAuth callbacks will fail in staging deployment"

                    })

        

        # Check OAuth configuration consistency

        if auth_callback_url and configured_redirect_uri:

            if auth_callback_url != configured_redirect_uri:

                redirect_uri_issues.append({

                    "issue": "Inconsistent OAuth callback configuration",

                    "oauth_callback_url": auth_callback_url,

                    "google_redirect_uri": configured_redirect_uri,

                    "impact": "OAuth flow confusion between different redirect URIs"

                })

        

        # This test SHOULD FAIL - expecting redirect URI configuration issues

        assert len(redirect_uri_issues) > 0, (

            f"Expected OAuth redirect URI configuration issues in staging "

            f"(causing OAuth callback failures), but all redirect URIs appear "

            f"properly configured. Configured URI: '{configured_redirect_uri}', "

            f"Callback URL: '{auth_callback_url}'. "

            f"This suggests OAuth redirect configuration has been resolved."

        )

        

        # Verify missing redirect URI is the primary issue

        missing_uri_issues = [

            issue for issue in redirect_uri_issues 

            if "not set" in issue.get("issue", "")

        ]

        

        assert len(missing_uri_issues) >= 1, (

            f"Expected missing GOOGLE_OAUTH_REDIRECT_URI to be the primary issue "

            f"(preventing OAuth callbacks), but got other redirect URI problems: "

            f"{redirect_uri_issues}. Missing redirect URI is a fundamental OAuth requirement."

        )



    @staging_only

    @pytest.mark.auth

    @pytest.mark.e2e

    def test_oauth_scopes_configuration_incomplete(self):

        """Test that OAuth scopes are not properly configured for staging.

        

        This test should FAIL, showing that required OAuth scopes for Google

        authentication are missing or improperly configured.

        """

        # Required OAuth scopes for Google authentication

        required_scopes = [

            "openid",      # Required for OpenID Connect

            "email",       # Access to user email

            "profile"      # Access to user profile info

        ]

        

        # Additional scopes that might be needed

        optional_scopes = [

            "https://www.googleapis.com/auth/userinfo.email",

            "https://www.googleapis.com/auth/userinfo.profile"

        ]

        

        scope_configuration_issues = []

        

        # Check configured OAuth scopes

        if not configured_scopes_str:

            scope_configuration_issues.append({

                "issue": "GOOGLE_OAUTH_SCOPES environment variable not set",

                "impact": "OAuth will use default or no scopes",

                "required_scopes": required_scopes

            })

        else:

            # Parse configured scopes

            configured_scopes = [

                scope.strip() for scope in configured_scopes_str.split(" ")

                if scope.strip()

            ]

            

            # Check for missing required scopes

            missing_scopes = [

                scope for scope in required_scopes 

                if scope not in configured_scopes

            ]

            

            if missing_scopes:

                scope_configuration_issues.append({

                    "issue": "Missing required OAuth scopes",

                    "missing_scopes": missing_scopes,

                    "configured_scopes": configured_scopes,

                    "impact": "OAuth authentication may fail or provide insufficient user info"

                })

        

        # Check for alternative scope configuration variables

        alternative_scope_vars = ["OAUTH_SCOPES", "GOOGLE_SCOPES"]

        for var in alternative_scope_vars:

            if alt_scopes and not configured_scopes_str:

                scope_configuration_issues.append({

                    "issue": f"OAuth scopes configured in {var} but not GOOGLE_OAUTH_SCOPES",

                    "alternative_config": alt_scopes,

                    "impact": "Scope configuration inconsistency may cause OAuth failures"

                })

        

        # This test SHOULD FAIL - expecting OAuth scope configuration issues

        assert len(scope_configuration_issues) > 0, (

            f"Expected OAuth scope configuration to be incomplete in staging "

            f"(causing authentication scope failures), but scope configuration "

            f"appears complete. Configured scopes: '{configured_scopes_str}'. "

            f"This suggests OAuth scope configuration has been properly set up."

        )

        

        # Verify missing scopes environment variable is the primary issue

        missing_scope_env_issues = [

            issue for issue in scope_configuration_issues 

            if "not set" in issue.get("issue", "")

        ]

        

        assert len(missing_scope_env_issues) >= 1, (

            f"Expected GOOGLE_OAUTH_SCOPES environment variable to be missing "

            f"(primary OAuth configuration gap), but got other scope issues: "

            f"{scope_configuration_issues}. Missing scope configuration is "

            f"a fundamental OAuth setup requirement."

        )

