"""
Regression test for OAuth redirect URI bug.

This test ensures that the redirect_uri is always properly set when exchanging
authorization codes with Google OAuth. This prevents the 400 Bad Request error
that was occurring in production.

Bug: self._redirect_uri was being used directly instead of calling get_redirect_uri(),
which could result in sending None to Google's token endpoint.

Fix: Always use self.get_redirect_uri() to ensure the redirect URI is properly set.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent OAuth authentication failures
- Value Impact: Prevents user login failures and support tickets
- Strategic Impact: Core authentication flow reliability
"""
import json
import pytest
from typing import Dict, Any
from unittest.mock import patch, MagicMock, Mock
from urllib.parse import urlparse, parse_qs
from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.auth_core.auth_environment import get_auth_env

@pytest.fixture
def oauth_provider_factory():
    """Factory to create OAuth provider with mocked environment for testing."""

    def _create_provider(environment='test') -> GoogleOAuthProvider:
        mock_env = Mock()
        mock_env.get_environment.return_value = environment
        if environment == 'production':
            mock_env.get_auth_service_url.return_value = 'https://auth.netrasystems.ai'
        elif environment == 'staging':
            mock_env.get_auth_service_url.return_value = 'https://auth.staging.netrasystems.ai'
        else:
            mock_env.get_auth_service_url.return_value = 'http://localhost:8081'
        mock_env.get.return_value = None
        with patch('auth_service.auth_core.oauth.google_oauth.get_auth_env', return_value=mock_env):
            provider = GoogleOAuthProvider()
            provider._client_id = 'test-client-id'
            provider._client_secret = 'test-client-secret'
            return provider
    return _create_provider

def test_redirect_uri_always_set_in_token_exchange(oauth_provider_factory):
    """
    CRITICAL REGRESSION TEST: Ensure redirect_uri is always set when exchanging tokens.

    This test verifies that the OAuth provider always sends a valid redirect_uri
    to Google's token endpoint, even if get_redirect_uri() hasn't been called before.
    """
    oauth_provider = oauth_provider_factory(environment='test')
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test-token'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        with patch('requests.get') as mock_get:
            mock_user_response = MagicMock()
            mock_user_response.json.return_value = {'email': 'test@example.com', 'name': 'Test User', 'id': '12345'}
            mock_user_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_user_response
            result = oauth_provider.exchange_code_for_user_info('test-auth-code', 'test-state')
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            token_params = call_args[1]['data']
            assert token_params['redirect_uri'] is not None, 'redirect_uri was None in token exchange - REGRESSION DETECTED!'
            assert token_params['redirect_uri'] == 'http://localhost:8081/auth/callback', f"Unexpected redirect_uri: {token_params['redirect_uri']}"
            assert token_params['code'] == 'test-auth-code'
            assert token_params['client_id'] == 'test-client-id'
            assert token_params['client_secret'] == 'test-client-secret'
            assert token_params['grant_type'] == 'authorization_code'

def test_redirect_uri_consistent_across_calls(oauth_provider_factory):
    """
    Ensure redirect_uri is consistent between authorization URL and token exchange.

    Google requires the redirect_uri to match exactly between the authorization
    request and the token exchange request.
    """
    oauth_provider = oauth_provider_factory(environment='test')
    auth_url = oauth_provider.get_authorization_url('test-state')
    parsed_url = urlparse(auth_url)
    query_params = parse_qs(parsed_url.query)
    auth_redirect_uri = query_params.get('redirect_uri', [None])[0]
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test-token'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        with patch('requests.get') as mock_get:
            mock_user_response = MagicMock()
            mock_user_response.json.return_value = {'email': 'test@example.com', 'name': 'Test User', 'id': '12345'}
            mock_user_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_user_response
            oauth_provider.exchange_code_for_user_info('test-auth-code', 'test-state')
            token_params = mock_post.call_args[1]['data']
            token_redirect_uri = token_params['redirect_uri']
            assert auth_redirect_uri == token_redirect_uri, f'Redirect URI mismatch: auth={auth_redirect_uri}, token={token_redirect_uri}'

def test_redirect_uri_uses_ssot_path(oauth_provider_factory):
    """
    Verify that redirect URI always uses the SSOT path: /auth/callback

    This ensures we don't accidentally revert to old paths like /auth/oauth/callback
    or /oauth/callback which would cause authentication failures.
    """
    oauth_provider = oauth_provider_factory(environment='test')
    redirect_uri = oauth_provider.get_redirect_uri()
    assert redirect_uri.endswith('/auth/callback'), f'Redirect URI not using SSOT path: {redirect_uri}'
    assert '/auth/oauth/callback' not in redirect_uri, f'Using deprecated path /auth/oauth/callback: {redirect_uri}'
    assert not redirect_uri.endswith('/oauth/callback'), f'Using incorrect path /oauth/callback: {redirect_uri}'

def test_redirect_uri_environment_specific(oauth_provider_factory):
    """
    Test that redirect URI changes based on environment.

    This ensures proper environment isolation.
    """
    environments = [('production', 'https://auth.netrasystems.ai/auth/callback'), ('staging', 'https://auth.staging.netrasystems.ai/auth/callback'), ('development', 'http://localhost:8081/auth/callback'), ('test', 'http://localhost:8081/auth/callback')]
    for env_name, expected_uri in environments:
        provider = oauth_provider_factory(environment=env_name)
        redirect_uri = provider.get_redirect_uri()
        assert redirect_uri == expected_uri, f'Wrong redirect URI for {env_name}: expected {expected_uri}, got {redirect_uri}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')