from unittest.mock import Mock, AsyncMock, patch, MagicMock
"""
Regression test for OAuth redirect URI bug.

This test ensures that the redirect_uri is always properly set when exchanging
authorization codes with Google OAuth. This prevents the 400 Bad Request error
that was occurring in production.

Bug: self._redirect_uri was being used directly instead of calling get_redirect_uri(),
which could result in sending None to Google's token endpoint.'

Fix: Always use self.get_redirect_uri() to ensure the redirect URI is properly set.
"""

import pytest
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.auth_core.auth_environment import AuthEnvironment
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


class TestOAuthRedirectURIRegression:
    """Test suite to prevent OAuth redirect URI regression."""

    @pytest.fixture
    def real_auth_env():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock auth environment."""
        pass
        env = Mock(spec=AuthEnvironment)
        env.get_environment.return_value = "staging"
        env.get_auth_service_url.return_value = "https://auth.staging.netrasystems.ai"
        env.get.return_value = None  # Default for most env vars
        return env

    @pytest.fixture
    def oauth_provider(self, mock_auth_env):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create an OAuth provider with mocked environment."""
        pass
        with patch('auth_service.auth_core.oauth.google_oauth.get_auth_env', return_value=mock_auth_env):
            provider = GoogleOAuthProvider()
            # Set client credentials as they would be in production
            provider._client_id = "test-client-id"
            provider._client_secret = "test-client-secret"
            return provider

        def test_redirect_uri_always_set_in_token_exchange(self, oauth_provider):
            """
            CRITICAL REGRESSION TEST: Ensure redirect_uri is always set when exchanging tokens.

            This test verifies that the OAuth provider always sends a valid redirect_uri
            to Google's token endpoint, even if get_redirect_uri() hasn't been called before.
            """
            pass
        # Mock the requests.post call to capture what's sent to Google'
            with patch('requests.post') as mock_post:
                mock_response = mock_response_instance  # Initialize appropriate service
                mock_response.json.return_value = {"access_token": "test-token"}
                mock_response.raise_for_status = raise_for_status_instance  # Initialize appropriate service
                mock_post.return_value = mock_response

            # Mock user info request
                with patch('requests.get') as mock_get:
                    mock_user_response = mock_user_response_instance  # Initialize appropriate service
                    mock_user_response.json.return_value = {
                    "email": "test@example.com",
                    "name": "Test User",
                    "id": "12345"
                    }
                    mock_user_response.raise_for_status = raise_for_status_instance  # Initialize appropriate service
                    mock_get.return_value = mock_user_response

                # Call exchange_code_for_user_info WITHOUT calling get_redirect_uri() first
                # This simulates the bug condition
                    result = oauth_provider.exchange_code_for_user_info("test-auth-code", "test-state")

                # Verify the token exchange request was made
                    mock_post.assert_called_once()

                # Get the data sent to Google's token endpoint'
                    call_args = mock_post.call_args
                    token_params = call_args[1]['data']

                # CRITICAL ASSERTION: redirect_uri must not be None
                    assert token_params['redirect_uri'] is not None, \
                    "redirect_uri was None in token exchange - REGRESSION DETECTED!"

                # Verify the redirect_uri has the correct format
                    assert token_params['redirect_uri'] == "https://auth.staging.netrasystems.ai/auth/callback", \
                    f"Unexpected redirect_uri: {token_params['redirect_uri']}"

                # Verify all required parameters are present
                    assert token_params['code'] == "test-auth-code"
                    assert token_params['client_id'] == "test-client-id"
                    assert token_params['client_secret'] == "test-client-secret"
                    assert token_params['grant_type'] == "authorization_code"

                    def test_redirect_uri_consistent_across_calls(self, oauth_provider):
                        """
                        Ensure redirect_uri is consistent between authorization URL and token exchange.

                        Google requires the redirect_uri to match exactly between the authorization
                        request and the token exchange request.
                        """
                        pass
        # Get authorization URL
                        auth_url = oauth_provider.get_authorization_url("test-state")

        # Extract redirect_uri from auth URL
                        import urllib.parse
                        parsed_url = urllib.parse.urlparse(auth_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        auth_redirect_uri = query_params.get('redirect_uri', [None])[0]

        # Now test token exchange
                        with patch('requests.post') as mock_post:
                            mock_response = mock_response_instance  # Initialize appropriate service
                            mock_response.json.return_value = {"access_token": "test-token"}
                            mock_response.raise_for_status = raise_for_status_instance  # Initialize appropriate service
                            mock_post.return_value = mock_response

                            with patch('requests.get') as mock_get:
                                mock_user_response = mock_user_response_instance  # Initialize appropriate service
                                mock_user_response.json.return_value = {
                                "email": "test@example.com",
                                "name": "Test User",
                                "id": "12345"
                                }
                                mock_user_response.raise_for_status = raise_for_status_instance  # Initialize appropriate service
                                mock_get.return_value = mock_user_response

                # Exchange code
                                oauth_provider.exchange_code_for_user_info("test-auth-code", "test-state")

                # Get the redirect_uri from token exchange
                                token_params = mock_post.call_args[1]['data']
                                token_redirect_uri = token_params['redirect_uri']

                # CRITICAL: Both redirect_uris must match exactly
                                assert auth_redirect_uri == token_redirect_uri, \
                                f"Redirect URI mismatch: auth={auth_redirect_uri}, token={token_redirect_uri}"

                                def test_redirect_uri_uses_ssot_path(self, oauth_provider):
                                    """
                                    Verify that redirect URI always uses the SSOT path: /auth/callback

                                    This ensures we don't accidentally revert to old paths like /auth/oauth/callback'
                                    or /oauth/callback which would cause authentication failures.
                                    """
                                    pass
                                    redirect_uri = oauth_provider.get_redirect_uri()

        # CRITICAL: Must use the standardized path
                                    assert redirect_uri.endswith("/auth/callback"), \
                                    f"Redirect URI not using SSOT path: {redirect_uri}"

        # Ensure it doesn't use deprecated paths'
                                    assert "/auth/oauth/callback" not in redirect_uri, \
                                    f"Using deprecated path /auth/oauth/callback: {redirect_uri}"
                                    assert not redirect_uri.endswith("/oauth/callback"), \
                                    f"Using incorrect path /oauth/callback: {redirect_uri}"

                                    def test_redirect_uri_environment_specific(self):
                                        """
                                        Test that redirect URI changes based on environment.

                                        This ensures proper environment isolation.
                                        """
                                        pass
                                        environments = [
                                        ("production", "https://auth.netrasystems.ai/auth/callback"),
                                        ("staging", "https://auth.staging.netrasystems.ai/auth/callback"),
                                        ("development", "http://localhost:8081/auth/callback"),
                                        ("test", "http://localhost:8081/auth/callback")
                                        ]

                                        for env_name, expected_uri in environments:
                                            mock_env = Mock(spec=AuthEnvironment)
                                            mock_env.get_environment.return_value = env_name

            # Set appropriate auth service URL based on environment
                                            if env_name == "production":
                                                mock_env.get_auth_service_url.return_value = "https://auth.netrasystems.ai"
                                            elif env_name == "staging":
                                                mock_env.get_auth_service_url.return_value = "https://auth.staging.netrasystems.ai"
                                            else:
                                                mock_env.get_auth_service_url.return_value = "http://localhost:8081"

                                                mock_env.get.return_value = None

                                                with patch('auth_service.auth_core.oauth.google_oauth.get_auth_env', return_value=mock_env):
                                                    provider = GoogleOAuthProvider()
                                                    redirect_uri = provider.get_redirect_uri()

                                                    assert redirect_uri == expected_uri, \
                                                    f"Wrong redirect URI for {env_name}: expected {expected_uri}, got {redirect_uri}"


                                                    if __name__ == "__main__":
    # Run the tests
                                                        pytest.main([__file__, "-v"])