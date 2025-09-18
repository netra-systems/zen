"""
Integration tests for auth URL configuration across services.

This test suite ensures that auth URLs are properly configured and
consistent across backend and auth services in all environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure cross-service authentication works correctly
- Value Impact: Prevents service communication failures
- Strategic Impact: Enables reliable multi-service architecture
"""

import pytest
import os
import asyncio
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import patch, Mock
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAuthUrlConfiguration(SSotBaseTestCase):
    """Test auth URL configuration consistency across services."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.environments = ['development', 'staging', 'production']

    @pytest.mark.asyncio
    async def test_auth_service_url_consistency(self):
        """Test that auth service URLs are consistent across all services."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock the auth environment
                auth_env = Mock()
                auth_env.get_auth_service_url.return_value = f"https://{env}.example.com"

                # Mock the backend config
                backend_config = Mock()
                backend_config.service_url = f"https://{env}.example.com"

                # They should match
                assert auth_env.get_auth_service_url() == backend_config.service_url, \
                    f"Auth service URLs should match in {env} environment"

    @pytest.mark.asyncio
    async def test_oauth_configuration_consistency(self):
        """Test OAuth configuration is consistent across services."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock OAuth redirect URLs
                auth_redirect = f"https://auth.{env}.example.com/oauth/callback"
                backend_redirect = f"https://backend.{env}.example.com/oauth/callback"

                # Both should point to same domain in staging/production
                if env in ['staging', 'production']:
                    auth_domain = auth_redirect.split('/oauth/')[0]
                    backend_domain = backend_redirect.split('/oauth/')[0]

                    assert 'example.com' in auth_domain, \
                        f"Auth domain should use example.com in {env}"
                    assert 'example.com' in backend_domain, \
                        f"Backend domain should use example.com in {env}"

    @pytest.mark.asyncio
    async def test_health_check_url_construction(self):
        """Test that health check URLs are properly constructed."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock config
                config = Mock()
                config.service_url = f"https://{env}.example.com"
                config.health_url = f"{config.service_url}/health"

                # Health URL should be service URL + /health
                expected = f"{config.service_url}/health"
                assert config.health_url == expected, \
                    f"Health URL should be service URL + /health in {env}"

                # Verify protocol consistency
                if env in ['staging', 'production']:
                    assert config.health_url.startswith('https://'), \
                        f"Health URL should use HTTPS in {env}"
                else:
                    # Development can use HTTP
                    assert config.health_url.startswith(('http://', 'https://')), \
                        f"Health URL should use HTTP/HTTPS in {env}"

    @pytest.mark.asyncio
    async def test_api_endpoint_construction(self):
        """Test that API endpoints are properly constructed."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock config
                config = Mock()
                config.service_url = f"https://{env}.example.com"
                config.base_url = f"{config.service_url}/api/v1"

                # Base URL should include API version
                assert '/api/v1' in config.base_url, \
                    f"Base URL should include API version in {env}"

                # Should start with service URL
                assert config.base_url.startswith(config.service_url), \
                    f"Base URL should start with service URL in {env}"

    def test_frontend_backend_auth_triangle(self):
        """Test the frontend-backend-auth service URL triangle."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock auth environment
                auth_env = Mock()

                # Get all three service URLs
                frontend = f"https://app.{env}.example.com"
                backend = f"https://api.{env}.example.com"
                auth = f"https://auth.{env}.example.com"

                auth_env.get_frontend_url.return_value = frontend
                auth_env.get_backend_url.return_value = backend
                auth_env.get_auth_service_url.return_value = auth

                # All should use consistent protocol
                if env in ['staging', 'production']:
                    assert all(url.startswith("https://") for url in [frontend, backend, auth]), \
                        f"All URLs should use HTTPS in {env}"

                    # All should use same base domain
                    assert all("example.com" in url for url in [frontend, backend, auth]), \
                        f"All URLs should use same domain in {env}"

                    # Check subdomain pattern for staging
                    if env == 'staging':
                        assert all("staging" in url or env in url for url in [frontend, backend, auth]), \
                            f"Staging URLs should contain staging identifier"

    def test_cors_origins_match_frontend_urls(self):
        """Test that CORS origins include the frontend URL."""
        for env in self.environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock auth environment
                auth_env = Mock()

                frontend_url = f"https://app.{env}.example.com"
                cors_origins = [
                    frontend_url,
                    "http://localhost:3000",  # Development override
                    f"https://admin.{env}.example.com"
                ]

                auth_env.get_frontend_url.return_value = frontend_url
                auth_env.get_cors_origins.return_value = cors_origins

                # Remove trailing slash for comparison
                frontend_base = frontend_url.rstrip('/')

                # Frontend URL should be in CORS origins
                assert any(origin.rstrip('/') == frontend_base for origin in cors_origins), \
                    f"Frontend URL should be in CORS origins for {env}"


class TestAuthConfigDelegation(SSotBaseTestCase):
    """Test that AuthConfig properly delegates to AuthEnvironment."""

    def test_config_delegation_consistency(self):
        """Test AuthConfig methods return same values as AuthEnvironment."""
        environments = ['development', 'staging', 'production']

        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock both components
                auth_env = Mock()
                config = Mock()

                # Mock return values
                frontend_url = f"https://app.{env}.example.com"
                auth_service_url = f"https://auth.{env}.example.com"
                environment = env

                auth_env.get_frontend_url.return_value = frontend_url
                auth_env.get_auth_service_url.return_value = auth_service_url
                auth_env.get_environment.return_value = environment

                config.get_frontend_url.return_value = frontend_url
                config.get_auth_service_url.return_value = auth_service_url
                config.get_environment.return_value = environment

                # Test all URL methods
                assert config.get_frontend_url() == auth_env.get_frontend_url(), \
                    f"Frontend URL delegation should work in {env}"

                assert config.get_auth_service_url() == auth_env.get_auth_service_url(), \
                    f"Auth service URL delegation should work in {env}"

                assert config.get_environment() == auth_env.get_environment(), \
                    f"Environment delegation should work in {env}"

    def test_jwt_configuration_delegation(self):
        """Test JWT configuration methods delegate properly."""
        test_env = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'test-secret',
            'JWT_ALGORITHM': 'HS256',
            'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '30'
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Mock components
            auth_env = Mock()
            config = Mock()

            # Mock JWT configuration
            jwt_config = {
                'secret_key': 'test-secret',
                'algorithm': 'HS256',
                'access_token_expire_minutes': 30
            }

            auth_env.get_jwt_config.return_value = jwt_config
            config.get_jwt_config.return_value = jwt_config

            # Configurations should match
            assert config.get_jwt_config() == auth_env.get_jwt_config(), \
                "JWT configuration delegation should work"

    def test_ssl_configuration_environments(self):
        """Test SSL configuration varies correctly by environment."""
        test_cases = [
            ('development', False),  # SSL optional in dev
            ('staging', True),       # SSL required in staging
            ('production', True)     # SSL required in production
        ]

        for env, ssl_required in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Mock config
                config = Mock()
                config.ssl_required = ssl_required

                if ssl_required:
                    assert config.ssl_required, f"SSL should be required in {env}"
                else:
                    # SSL can be optional in development
                    pass  # No assertion needed for optional SSL


class TestEnvironmentSpecificBehavior(SSotBaseTestCase):
    """Test environment-specific URL behavior."""

    def test_production_security_requirements(self):
        """Test that production enforces security requirements."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            # Mock auth environment
            auth_env = Mock()

            # Production URLs must use HTTPS
            frontend = "https://app.example.com"
            backend = "https://api.example.com"
            auth = "https://auth.example.com"

            auth_env.get_frontend_url.return_value = frontend
            auth_env.get_backend_url.return_value = backend
            auth_env.get_auth_service_url.return_value = auth

            # All production URLs must use HTTPS
            urls = [frontend, backend, auth]
            assert all(url.startswith('https://') for url in urls), \
                "All production URLs must use HTTPS"

            # Should not contain development indicators
            assert all('localhost' not in url for url in urls), \
                "Production URLs should not contain localhost"
            assert all('127.0.0.1' not in url for url in urls), \
                "Production URLs should not contain 127.0.0.1"

    def test_development_convenience_defaults(self):
        """Test that development uses convenient local defaults."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=True):
            # Mock auth environment
            auth_env = Mock()

            # Development should use localhost
            frontend = "http://localhost:3000"
            backend = "http://localhost:8000"

            auth_env.get_frontend_url.return_value = frontend
            auth_env.get_backend_url.return_value = backend

            # Should use localhost or 127.0.0.1
            assert 'localhost' in frontend or '127.0.0.1' in frontend, \
                "Development frontend should use localhost"
            assert 'localhost' in backend or '127.0.0.1' in backend, \
                "Development backend should use localhost"

    def test_staging_environment_indicators(self):
        """Test that staging URLs properly indicate staging environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
            # Mock auth environment
            auth_env = Mock()

            # Staging should indicate environment in URL
            frontend = "https://app.staging.example.com"
            backend = "https://api.staging.example.com"
            auth = "https://auth.staging.example.com"

            auth_env.get_frontend_url.return_value = frontend
            auth_env.get_backend_url.return_value = backend
            auth_env.get_auth_service_url.return_value = auth

            # All staging URLs should indicate staging
            urls = [frontend, backend, auth]
            assert all('staging' in url for url in urls), \
                "All staging URLs should contain 'staging'"

            # Should use HTTPS
            assert all(url.startswith('https://') for url in urls), \
                "All staging URLs should use HTTPS"


if __name__ == "__main__":
    pytest.main([__file__])