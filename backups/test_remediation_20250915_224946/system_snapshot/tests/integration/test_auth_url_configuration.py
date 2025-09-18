"""
Integration tests for auth URL configuration across services.

This test suite ensures that auth URLs are properly configured and
consistent across backend and auth services in all environments.

Business Value Justification (BVJ):"""
- Business Goal: Ensure cross-service authentication works correctly"""
- Strategic Impact: Enables reliable multi-service architecture"""

import pytest
import os
import asyncio
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

    # Import both auth and backend configurations
from auth_service.auth_core.auth_environment import AuthEnvironment
from auth_service.auth_core.config import AuthConfig
from netra_backend.app.clients.auth_client_config import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
AuthClientConfig, OAuthConfigGenerator, load_auth_client_config
    """
"""
    """Integration tests for auth URL configuration.""""""
    @pytest.fixture"""
        """Setup test environment."""
        self.original_env = os.environ.copy()
        yield
        os.environ.clear()
        os.environ.update(self.original_env)"""
@pytest.mark.asyncio"""
"""Test that backend and auth service agree on auth service URL."""
pass
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Get auth service's own URL
auth_env = AuthEnvironment()
auth_service_url = auth_env.get_auth_service_url()

                # Get backend's view of auth service URL
backend_config = load_auth_client_config()
backend_auth_url = backend_config.service_url"""
                # They should match"""
"formatted_string"

@pytest.mark.asyncio
    async def test_oauth_configuration_consistency(self):
"""Test OAuth configuration is consistent across services."""
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                            # Get auth service OAuth config
auth_env = AuthEnvironment()
auth_redirect = auth_env.get_oauth_redirect_uri()

                            # Get backend OAuth config
oauth_gen = OAuthConfigGenerator()
backend_oauth = oauth_gen.generate(env)

                            # Redirect URIs should be related (backend may have different path)
google_config = backend_oauth.get('google', {})
backend_redirect = google_config.get('redirect_uri', '')

                            # Both should point to same domain
auth_domain = auth_redirect.split('/auth/')[0]
backend_domain = backend_redirect.split('/auth/')[0]
"""
if env in ['staging', 'production']:"""
"formatted_string"
assert 'netrasystems.ai' in backend_domain, \
"formatted_string"

@pytest.mark.asyncio
    async def test_health_check_url_construction(self):
"""Test that health check URLs are properly constructed."""
pass
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
config = load_auth_client_config()"""
"""
expected = "formatted_string"
assert health_url == expected, \
"formatted_string"

                                            # Verify protocol consistency
if env in ['staging', 'production']:
assert health_url.startswith('https://'), \
"formatted_string"
else:
assert health_url.startswith('http://'), \
"formatted_string"

@pytest.mark.asyncio
    async def test_api_endpoint_construction(self):
"""Test that API endpoints are properly constructed."""
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
config = load_auth_client_config()
base_url = config.base_url"""
                                                                # Base URL should include API version"""
"formatted_string"

                                                                # Should start with service URL
assert base_url.startswith(config.service_url), \
"formatted_string"t start with service URL"

def test_frontend_backend_auth_triangle(self):
"""Test the frontend-backend-auth service URL triangle."""
pass
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
auth_env = AuthEnvironment()

            # Get all three service URLs
frontend = auth_env.get_frontend_url()"""
if env in ['staging', 'production']:"""
"formatted_string"

                # All should use same base domain
assert all('netrasystems.ai' in url for url in [frontend, backend, auth]), \
"formatted_string"

                # Check subdomain pattern
if env == 'staging':
assert all('staging' in url for url in [frontend, backend, auth]), \
f"Staging: All services should have 'staging' in URL"
else:
assert all(url.startswith('http://') for url in [frontend, backend, auth]), \
"formatted_string"

def test_cors_origins_match_frontend_urls(self):
"""Test that CORS origins include the frontend URL."""
environments = ['development', 'staging', 'production']

for env in environments:
with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
auth_env = AuthEnvironment()

frontend_url = auth_env.get_frontend_url()
            # Remove trailing slash for comparison
frontend_base = frontend_url.rstrip('/')"""
            # Frontend URL should be in CORS origins"""
"formatted_string"


class TestAuthConfigDelegation:
        """Test that AuthConfig properly delegates to AuthEnvironment."""

    def test_config_delegation_consistency(self):
    # Removed problematic line: '''Test AuthConfig methods await asyncio.sleep(0)
        return same values as AuthEnvironment.'''
        environments = ['development', 'staging', 'production']

        for env in environments:
        with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
        auth_env = AuthEnvironment()
        config = AuthConfig()"""
            # Test all URL methods"""
        "formatted_string"

        assert config.get_auth_service_url() == auth_env.get_auth_service_url(), \
        "formatted_string"

        assert config.get_environment() == auth_env.get_environment(), \
        "formatted_string"

    def test_jwt_configuration_delegation(self):
        """Test JWT configuration methods delegate properly."""
        pass
        with patch.dict(os.environ, { ))
        'ENVIRONMENT': 'staging',
        'JWT_SECRET_KEY': 'test-secret',
        'JWT_ALGORITHM': 'HS256',
        'JWT_EXPIRATION_MINUTES': '30'
        }, clear=True):
        auth_env = AuthEnvironment()
        config = AuthConfig()

        assert config.get_jwt_secret() == auth_env.get_jwt_secret_key()
        assert config.get_jwt_algorithm() == auth_env.get_jwt_algorithm()
        assert config.get_jwt_access_expiry_minutes() == auth_env.get_jwt_expiration_minutes()"""
"""
        """Test environment-specific behaviors and defaults."""
"""
        """Test staging-specific configuration requirements."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        auth_env = AuthEnvironment()

        # Staging should have specific characteristics
        assert auth_env.is_staging() is True
        assert auth_env.is_production() is False
        assert auth_env.is_development() is False"""
        # URLs should be staging-specific"""
        assert 'app.staging' in frontend, "Staging frontend should have app.staging subdomain"

        backend = auth_env.get_backend_url()
        assert 'backend.staging' in backend, "Staging backend should have backend.staging subdomain"

        auth = auth_env.get_auth_service_url()
        assert 'auth.staging' in auth, "Staging auth should have auth.staging subdomain"

    def test_production_security_requirements(self):
        """Test that production enforces security requirements."""
        pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
        auth_env = AuthEnvironment()
"""
        frontend = auth_env.get_frontend_url()"""
        "Production must use HTTPS for all services"

        # Production should not contain staging references
        assert 'staging' not in frontend
        assert 'staging' not in backend
        assert 'staging' not in auth

        # Production should not use localhost
        assert 'localhost' not in frontend
        assert 'localhost' not in backend
        assert 'localhost' not in auth

    def test_development_convenience_defaults(self):
        """Test that development uses convenient local defaults."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=True):
        auth_env = AuthEnvironment()

        # Development should use localhost
        frontend = auth_env.get_frontend_url()
        assert 'localhost' in frontend or '127.0.0.1' in frontend
        assert 'localhost' in backend or '127.0.0.1' in backend

        # Development uses different ports
        assert ':3000' in frontend  # Frontend port
        assert ':8000' in backend   # Backend port
        assert ':8081' in auth_env.get_auth_service_url()  # Auth port"""
"""
        """Test various URL override scenarios."""
"""
        """Test that partial overrides maintain consistency."""
        with patch.dict(os.environ, { ))
        'ENVIRONMENT': 'staging',
        'FRONTEND_URL': 'https://custom.staging.com'
    # Let backend and auth use defaults
        }, clear=True):
        auth_env = AuthEnvironment()

        # Frontend is overridden
        assert auth_env.get_frontend_url() == 'https://custom.staging.com'

        # OAuth redirect should use custom frontend
        assert auth_env.get_oauth_redirect_uri() == 'https://custom.staging.com/auth/callback'

        # Backend and auth should still use staging defaults
        assert auth_env.get_backend_url() == 'https://api.staging.netrasystems.ai'"""
"""
        """Test complete URL override scenario."""
        pass
        with patch.dict(os.environ, { ))
        'ENVIRONMENT': 'staging',
        'FRONTEND_URL': 'https://app.custom.com',
        'BACKEND_URL': 'https://api.custom.com',
        'AUTH_SERVICE_URL': 'https://auth.custom.com',
        'OAUTH_REDIRECT_URI': 'https://app.custom.com/oauth/callback'
        }, clear=True):
        auth_env = AuthEnvironment()

        # All should use custom URLs
        assert auth_env.get_frontend_url() == 'https://app.custom.com'
        assert auth_env.get_backend_url() == 'https://api.custom.com'
        assert auth_env.get_auth_service_url() == 'https://auth.custom.com'
        assert auth_env.get_oauth_redirect_uri() == 'https://app.custom.com/oauth/callback'


        if __name__ == '__main__':"""
        pytest.main([__file__, '-v', '--tb=short'])"""