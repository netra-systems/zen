# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical Test: OAuth Redirect URI Configuration
# REMOVED_SYNTAX_ERROR: This test verifies that the auth service uses the correct redirect URI for OAuth callbacks
# REMOVED_SYNTAX_ERROR: '''
import os
import sys
import pytest
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env

# Setup test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import _determine_urls
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


# REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: @pytest.mark.oauth
# REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: class TestOAuthRedirectURIConfiguration:
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: CRITICAL BUG: Auth service tells Google to redirect to frontend URL instead of auth service URL

    # REMOVED_SYNTAX_ERROR: Root Cause:
        # REMOVED_SYNTAX_ERROR: - Auth service uses frontend URL + /auth/callback as redirect_uri (line 242, 676, 906 in auth_routes.py)
        # REMOVED_SYNTAX_ERROR: - Google redirects to frontend, which expects tokens but doesn"t get them
        # REMOVED_SYNTAX_ERROR: - Auth service callback endpoint never gets hit

        # REMOVED_SYNTAX_ERROR: Expected Flow:
            # REMOVED_SYNTAX_ERROR: 1. User clicks login -> auth service generates OAuth URL with auth service callback
            # REMOVED_SYNTAX_ERROR: 2. Google redirects to auth service callback with code
            # REMOVED_SYNTAX_ERROR: 3. Auth service exchanges code for tokens
            # REMOVED_SYNTAX_ERROR: 4. Auth service redirects to frontend with tokens

            # REMOVED_SYNTAX_ERROR: Actual Flow (BROKEN):
                # REMOVED_SYNTAX_ERROR: 1. User clicks login -> auth service generates OAuth URL with FRONTEND callback
                # REMOVED_SYNTAX_ERROR: 2. Google redirects to FRONTEND with code (auth service never sees it)
                # REMOVED_SYNTAX_ERROR: 3. Frontend expects tokens but only has code
                # REMOVED_SYNTAX_ERROR: 4. Authentication fails
                # REMOVED_SYNTAX_ERROR: '''

                # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_oauth_redirect_uri_must_point_to_auth_service(self):
    # REMOVED_SYNTAX_ERROR: """Test that OAuth redirect URI points to auth service, not frontend"""
    # Setup environment for staging
    # REMOVED_SYNTAX_ERROR: with patch.dict(get_env().get_all(), { ))
    # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'staging',
    # REMOVED_SYNTAX_ERROR: 'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
    # REMOVED_SYNTAX_ERROR: 'FRONTEND_URL': 'https://app.staging.netrasystems.ai'
    # REMOVED_SYNTAX_ERROR: }):
        # REMOVED_SYNTAX_ERROR: auth_url, frontend_url = _determine_urls()

        # CRITICAL: The redirect URI must point to the AUTH SERVICE
        # so it can exchange the OAuth code for tokens
        # REMOVED_SYNTAX_ERROR: expected_redirect_uri = "formatted_string"

        # This is what's currently happening (WRONG)
        # REMOVED_SYNTAX_ERROR: actual_redirect_uri = "formatted_string"

        # This test MUST FAIL in current implementation
        # REMOVED_SYNTAX_ERROR: assert expected_redirect_uri != actual_redirect_uri, \
        # REMOVED_SYNTAX_ERROR: f"CRITICAL BUG CONFIRMED: Auth service is using frontend URL for OAuth callback. " \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_oauth_login_generates_correct_redirect_uri(self):
    # REMOVED_SYNTAX_ERROR: """Test that /auth/login endpoint generates correct redirect URI"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from fastapi.testclient import TestClient
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.main import app

    # REMOVED_SYNTAX_ERROR: client = TestClient(app)

    # REMOVED_SYNTAX_ERROR: with patch.dict(get_env().get_all(), { ))
    # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'staging',
    # REMOVED_SYNTAX_ERROR: 'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
    # REMOVED_SYNTAX_ERROR: 'FRONTEND_URL': 'https://app.staging.netrasystems.ai',
    # REMOVED_SYNTAX_ERROR: 'GOOGLE_CLIENT_ID': 'test-client-id',
    # REMOVED_SYNTAX_ERROR: 'GOOGLE_CLIENT_SECRET': 'test-secret'
    # REMOVED_SYNTAX_ERROR: }):
        # Attempt to initiate OAuth login
        # REMOVED_SYNTAX_ERROR: response = client.get("/auth/login", follow_redirects=False)

        # Check the redirect location
        # REMOVED_SYNTAX_ERROR: if response.status_code == 302:
            # REMOVED_SYNTAX_ERROR: location = response.headers.get('location', '')

            # Extract redirect_uri parameter
            # REMOVED_SYNTAX_ERROR: if 'redirect_uri=' in location:
                # REMOVED_SYNTAX_ERROR: import urllib.parse
                # REMOVED_SYNTAX_ERROR: parsed = urllib.parse.urlparse(location)
                # REMOVED_SYNTAX_ERROR: params = urllib.parse.parse_qs(parsed.query)
                # REMOVED_SYNTAX_ERROR: redirect_uri = params.get('redirect_uri', [''])[0]

                # CRITICAL: Must use auth service URL
                # REMOVED_SYNTAX_ERROR: assert redirect_uri.startswith('https://auth.staging.netrasystems.ai'), \
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert redirect_uri == 'https://auth.staging.netrasystems.ai/auth/callback', \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_google_oauth_console_configuration_matches(self):
    # REMOVED_SYNTAX_ERROR: """Test that the redirect URI matches what should be in Google OAuth console"""
    # Document what needs to be configured in Google OAuth Console
    # REMOVED_SYNTAX_ERROR: staging_auth_callback = "https://auth.staging.netrasystems.ai/auth/callback"
    # REMOVED_SYNTAX_ERROR: production_auth_callback = "https://auth.netrasystems.ai/auth/callback"

    # These should be the ONLY authorized redirect URIs in Google Console
    # REMOVED_SYNTAX_ERROR: authorized_redirect_uris = [ )
    # REMOVED_SYNTAX_ERROR: staging_auth_callback,
    # REMOVED_SYNTAX_ERROR: production_auth_callback,
    # REMOVED_SYNTAX_ERROR: "http://localhost:8000/auth/callback",  # Local development
    

    # REMOVED_SYNTAX_ERROR: assert staging_auth_callback in authorized_redirect_uris, \
    # REMOVED_SYNTAX_ERROR: f"Staging auth callback must be authorized in Google OAuth Console"

    # Verify frontend callbacks should NOT be authorized
    # REMOVED_SYNTAX_ERROR: incorrect_uris = [ )
    # REMOVED_SYNTAX_ERROR: "https://app.staging.netrasystems.ai/auth/callback",  # WRONG
    # REMOVED_SYNTAX_ERROR: "https://app.netrasystems.ai/auth/callback",  # WRONG
    

    # REMOVED_SYNTAX_ERROR: for uri in incorrect_uris:
        # REMOVED_SYNTAX_ERROR: assert uri not in authorized_redirect_uris, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run the test to demonstrate the failure
            # REMOVED_SYNTAX_ERROR: test = TestOAuthRedirectURIConfiguration()

            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: " + "="*80)
            # REMOVED_SYNTAX_ERROR: print("CRITICAL OAUTH CONFIGURATION BUG TEST")
            # REMOVED_SYNTAX_ERROR: print("="*80)

            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: test.test_oauth_redirect_uri_must_point_to_auth_service()
                # REMOVED_SYNTAX_ERROR: print("ERROR: Test unexpectedly passed - bug might be fixed")
                # REMOVED_SYNTAX_ERROR: except AssertionError as e:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                    # REMOVED_SYNTAX_ERROR: print(" )
                    # REMOVED_SYNTAX_ERROR: This confirms the OAuth redirect URI bug exists!")

                    # REMOVED_SYNTAX_ERROR: print(" )
                    # REMOVED_SYNTAX_ERROR: REQUIRED FIX:")
                    # REMOVED_SYNTAX_ERROR: print("1. Change auth_routes.py lines 242, 676, 906 to use AUTH SERVICE URL")
                    # REMOVED_SYNTAX_ERROR: print("2. Update Google OAuth Console to authorize auth service URLs")
                    # REMOVED_SYNTAX_ERROR: print("3. Ensure auth service redirects to frontend after processing")
                    # REMOVED_SYNTAX_ERROR: print("="*80)
                    # REMOVED_SYNTAX_ERROR: pass