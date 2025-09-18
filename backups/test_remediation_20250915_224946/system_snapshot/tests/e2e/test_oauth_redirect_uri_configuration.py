'''
Critical Test: OAuth Redirect URI Configuration
This test verifies that the auth service uses the correct redirect URI for OAuth callbacks
'''
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


@pytest.mark.critical
@pytest.mark.oauth
@pytest.mark.e2e
class TestOAuthRedirectURIConfiguration:
    '''
    CRITICAL BUG: Auth service tells Google to redirect to frontend URL instead of auth service URL

    Root Cause:
    - Auth service uses frontend URL + /auth/callback as redirect_uri (line 242, 676, 906 in auth_routes.py)
    - Google redirects to frontend, which expects tokens but doesn"t get them
    - Auth service callback endpoint never gets hit

    Expected Flow:
    1. User clicks login -> auth service generates OAuth URL with auth service callback
    2. Google redirects to auth service callback with code
    3. Auth service exchanges code for tokens
    4. Auth service redirects to frontend with tokens

    Actual Flow (BROKEN):
    1. User clicks login -> auth service generates OAuth URL with FRONTEND callback
    2. Google redirects to FRONTEND with code (auth service never sees it)
    3. Frontend expects tokens but only has code
    4. Authentication fails
    '''

    @pytest.mark.e2e
    def test_oauth_redirect_uri_must_point_to_auth_service(self):
        """Test that OAuth redirect URI points to auth service, not frontend"""
    # Setup environment for staging
        with patch.dict(get_env().get_all(), { ))
        'ENVIRONMENT': 'staging',
        'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
        'FRONTEND_URL': 'https://app.staging.netrasystems.ai'
        }):
        auth_url, frontend_url = _determine_urls()

        # CRITICAL: The redirect URI must point to the AUTH SERVICE
        # so it can exchange the OAuth code for tokens
        expected_redirect_uri = "formatted_string"

        # This is what's currently happening (WRONG)
        actual_redirect_uri = "formatted_string"

        # This test MUST FAIL in current implementation
        assert expected_redirect_uri != actual_redirect_uri, \
        f"CRITICAL BUG CONFIRMED: Auth service is using frontend URL for OAuth callback. " \
        "formatted_string"

        @pytest.mark.e2e
    def test_oauth_login_generates_correct_redirect_uri(self):
        """Test that /auth/login endpoint generates correct redirect URI"""
        pass
        from fastapi.testclient import TestClient
        from auth_service.auth_core.main import app

        client = TestClient(app)

        with patch.dict(get_env().get_all(), { ))
        'ENVIRONMENT': 'staging',
        'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
        'FRONTEND_URL': 'https://app.staging.netrasystems.ai',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-secret'
        }):
        # Attempt to initiate OAuth login
        response = client.get("/auth/login", follow_redirects=False)

        # Check the redirect location
        if response.status_code == 302:
        location = response.headers.get('location', '')

            # Extract redirect_uri parameter
        if 'redirect_uri=' in location:
        import urllib.parse
        parsed = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(parsed.query)
        redirect_uri = params.get('redirect_uri', [''])[0]

                # CRITICAL: Must use auth service URL
        assert redirect_uri.startswith('https://auth.staging.netrasystems.ai'), \
        "formatted_string"
        assert redirect_uri == 'https://auth.staging.netrasystems.ai/auth/callback', \
        "formatted_string"

        @pytest.mark.e2e
    def test_google_oauth_console_configuration_matches(self):
        """Test that the redirect URI matches what should be in Google OAuth console"""
    # Document what needs to be configured in Google OAuth Console
        staging_auth_callback = "https://auth.staging.netrasystems.ai/auth/callback"
        production_auth_callback = "https://auth.netrasystems.ai/auth/callback"

    # These should be the ONLY authorized redirect URIs in Google Console
        authorized_redirect_uris = [ )
        staging_auth_callback,
        production_auth_callback,
        "http://localhost:8000/auth/callback",  # Local development
    

        assert staging_auth_callback in authorized_redirect_uris, \
        f"Staging auth callback must be authorized in Google OAuth Console"

    # Verify frontend callbacks should NOT be authorized
        incorrect_uris = [ )
        "https://app.staging.netrasystems.ai/auth/callback",  # WRONG
        "https://app.netrasystems.ai/auth/callback",  # WRONG
    

        for uri in incorrect_uris:
        assert uri not in authorized_redirect_uris, \
        "formatted_string"


        if __name__ == "__main__":
            # Run the test to demonstrate the failure
        test = TestOAuthRedirectURIConfiguration()

        print(" )
        " + "="*80)
        print("CRITICAL OAUTH CONFIGURATION BUG TEST")
        print("="*80)

        try:
        test.test_oauth_redirect_uri_must_point_to_auth_service()
        print("ERROR: Test unexpectedly passed - bug might be fixed")
        except AssertionError as e:
        print("formatted_string")
        print(" )
        This confirms the OAuth redirect URI bug exists!")

        print(" )
        REQUIRED FIX:")
        print("1. Change auth_routes.py lines 242, 676, 906 to use AUTH SERVICE URL")
        print("2. Update Google OAuth Console to authorize auth service URLs")
        print("3. Ensure auth service redirects to frontend after processing")
        print("="*80)
        pass
