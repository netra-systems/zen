"""
Unit tests for AuthEnvironment URL configuration.

This test suite ensures that auth service URLs are correctly generated
for all environments, preventing regressions like the staging URL issue.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent auth service failures in staging/production
- Value Impact: Ensures reliable authentication across all environments
- Strategic Impact: Prevents deployment failures and user authentication issues
"""

import pytest
import os
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

from auth_service.auth_core.auth_environment import AuthEnvironment


class TestAuthEnvironmentURLs:
    """Test suite for AuthEnvironment URL generation."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Clear environment before each test."""
    pass
        # Store original env vars
        self.original_env = os.environ.copy()
        
        # Store the original IsolatedEnvironment if it exists
        import sys
        if 'shared.isolated_environment' in sys.modules:
            # Force module reload to clear singleton
            del sys.modules['shared.isolated_environment']
        if 'auth_service.auth_core.auth_environment' in sys.modules:
            del sys.modules['auth_service.auth_core.auth_environment']
        
        yield
        
        # Restore original env vars
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_development_urls(self):
        """Test that development environment returns correct URLs."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_environment() == 'development'
            assert auth_env.get_frontend_url() == 'http://localhost:3000'
            assert auth_env.get_backend_url() == 'http://localhost:8000'
            assert auth_env.get_auth_service_url() == 'http://localhost:8081'
            assert auth_env.get_oauth_redirect_uri() == 'http://localhost:3000/auth/callback'
    
    def test_test_environment_urls(self):
        """Test that test environment returns correct URLs."""
    pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'test'}):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_environment() == 'test'
            assert auth_env.get_frontend_url() == 'http://localhost:3001'
            assert auth_env.get_backend_url() == 'http://localhost:8001'
            assert auth_env.get_auth_service_url() == 'http://127.0.0.1:8082'
            assert auth_env.get_oauth_redirect_uri() == 'http://localhost:3001/auth/callback'
    
    def test_staging_urls(self):
        """Test that staging environment returns correct URLs - CRITICAL."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_environment() == 'staging'
            assert auth_env.get_frontend_url() == 'https://app.staging.netrasystems.ai'
            assert auth_env.get_backend_url() == 'https://backend.staging.netrasystems.ai'
            assert auth_env.get_auth_service_url() == 'https://auth.staging.netrasystems.ai'
            assert auth_env.get_oauth_redirect_uri() == 'https://app.staging.netrasystems.ai/auth/callback'
    
    def test_production_urls(self):
        """Test that production environment returns correct URLs."""
    pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_environment() == 'production'
            assert auth_env.get_frontend_url() == 'https://app.netrasystems.ai'
            assert auth_env.get_backend_url() == 'https://backend.netrasystems.ai'
            assert auth_env.get_auth_service_url() == 'https://auth.netrasystems.ai'
            assert auth_env.get_oauth_redirect_uri() == 'https://app.netrasystems.ai/auth/callback'
    
    def test_url_overrides(self):
        """Test that explicit environment variables override defaults."""
        custom_env = {
            'ENVIRONMENT': 'staging',
            'FRONTEND_URL': 'https://custom-frontend.com',
            'BACKEND_URL': 'https://custom-backend.com',
            'AUTH_SERVICE_URL': 'https://custom-auth.com',
            'OAUTH_REDIRECT_URI': 'https://custom-frontend.com/custom/callback'
        }
        
        with patch.dict(os.environ, custom_env):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_frontend_url() == 'https://custom-frontend.com'
            assert auth_env.get_backend_url() == 'https://custom-backend.com'
            assert auth_env.get_auth_service_url() == 'https://custom-auth.com'
            assert auth_env.get_oauth_redirect_uri() == 'https://custom-frontend.com/custom/callback'
    
    def test_partial_overrides(self):
        """Test that partial overrides work correctly."""
    pass
        custom_env = {
            'ENVIRONMENT': 'staging',
            'FRONTEND_URL': 'https://override.staging.com'
            # Backend and auth should use defaults
        }
        
        with patch.dict(os.environ, custom_env):
            auth_env = AuthEnvironment()
            
            # Frontend is overridden
            assert auth_env.get_frontend_url() == 'https://override.staging.com'
            # Backend uses staging default
            assert auth_env.get_backend_url() == 'https://backend.staging.netrasystems.ai'
            # Auth uses staging default
            assert auth_env.get_auth_service_url() == 'https://auth.staging.netrasystems.ai'
            # OAuth redirect uses overridden frontend
            assert auth_env.get_oauth_redirect_uri() == 'https://override.staging.com/auth/callback'
    
    def test_auth_service_host_for_environments(self):
        """Test auth service host returns correct values per environment."""
        test_cases = [
            ('development', '0.0.0.0'),
            ('test', '127.0.0.1'),
            ('staging', 'auth.staging.netrasystems.ai'),
            ('production', 'auth.netrasystems.ai')
        ]
        
        for env, expected_host in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                auth_env = AuthEnvironment()
                actual_host = auth_env.get_auth_service_host()
                assert actual_host == expected_host, \
                    f"Environment {env}: expected host {expected_host}, got {actual_host}"
    
    def test_auth_service_port_for_environments(self):
        """Test auth service port returns correct values per environment."""
    pass
        test_cases = [
            ('development', 8081),
            ('test', 8082),
            ('staging', 8080),
            ('production', 8080)
        ]
        
        for env, expected_port in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                auth_env = AuthEnvironment()
                actual_port = auth_env.get_auth_service_port()
                assert actual_port == expected_port, \
                    f"Environment {env}: expected port {expected_port}, got {actual_port}"
    
    def test_oauth_redirect_follows_frontend(self):
        """Test that OAuth redirect URI always follows frontend URL."""
        test_cases = [
            ('development', 'http://localhost:3000/auth/callback'),
            ('staging', 'https://app.staging.netrasystems.ai/auth/callback'),
            ('production', 'https://app.netrasystems.ai/auth/callback')
        ]
        
        for env, expected_redirect in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                auth_env = AuthEnvironment()
                actual_redirect = auth_env.get_oauth_redirect_uri()
                assert actual_redirect == expected_redirect, \
                    f"Environment {env}: expected redirect {expected_redirect}, got {actual_redirect}"
    
    def test_unknown_environment_defaults(self):
        """Test that unknown environments fall back to safe defaults."""
    pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'custom-env'}):
            auth_env = AuthEnvironment()
            
            assert auth_env.get_environment() == 'custom-env'
            assert auth_env.get_frontend_url() == 'http://localhost:3000'
            assert auth_env.get_backend_url() == 'http://localhost:8000'
            # Should construct URL from host and port
            assert 'localhost' in auth_env.get_auth_service_url()
            assert auth_env.get_oauth_redirect_uri() == 'http://localhost:3000/auth/callback'
    
    def test_cors_origins_for_environments(self):
        """Test CORS origins are correctly set per environment."""
        test_cases = [
            ('development', ['http://localhost:3000', 'http://localhost:8000', 
                           'http://127.0.0.1:3000', 'http://127.0.0.1:8000']),
            ('staging', ['https://app.staging.netrasystems.ai', 'https://staging.netrasystems.ai']),
            ('production', ['https://netrasystems.ai', 'https://app.netrasystems.ai'])
        ]
        
        for env, expected_origins in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                auth_env = AuthEnvironment()
                actual_origins = auth_env.get_cors_origins()
                assert set(actual_origins) == set(expected_origins), \
                    f"Environment {env}: CORS origins mismatch"
    
    @pytest.mark.parametrize("env,expected_https", [
        ('production', True),
        ('staging', True),
        ('development', False),
        ('test', False)
    ])
    def test_url_protocol_consistency(self, env, expected_https):
        """Test that URL protocols are consistent per environment."""
    pass
        with patch.dict(os.environ, {'ENVIRONMENT': env}):
            auth_env = AuthEnvironment()
            
            frontend = auth_env.get_frontend_url()
            backend = auth_env.get_backend_url()
            auth = auth_env.get_auth_service_url()
            
            if expected_https:
                assert frontend.startswith('https://'), f"{env}: Frontend should use HTTPS"
                assert backend.startswith('https://'), f"{env}: Backend should use HTTPS"
                assert auth.startswith('https://'), f"{env}: Auth should use HTTPS"
            else:
                assert frontend.startswith('http://'), f"{env}: Frontend should use HTTP"
                assert backend.startswith('http://'), f"{env}: Backend should use HTTP"
                assert auth.startswith('http://'), f"{env}: Auth should use HTTP"


class TestAuthEnvironmentURLRegression:
    """Specific regression tests for the staging URL bug."""
    
    def test_staging_urls_not_localhost(self):
        """Regression test: Ensure staging never returns localhost URLs."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            auth_env = AuthEnvironment()
            
            frontend = auth_env.get_frontend_url()
            backend = auth_env.get_backend_url()
            auth = auth_env.get_auth_service_url()
            
            # None should contain localhost
            assert 'localhost' not in frontend, "Staging frontend URL contains localhost"
            assert 'localhost' not in backend, "Staging backend URL contains localhost"
            assert 'localhost' not in auth, "Staging auth URL contains localhost"
            assert '127.0.0.1' not in auth, "Staging auth URL contains 127.0.0.1"
    
    def test_staging_urls_use_staging_subdomain(self):
        """Regression test: Ensure staging URLs use staging subdomain."""
    pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            auth_env = AuthEnvironment()
            
            frontend = auth_env.get_frontend_url()
            backend = auth_env.get_backend_url()
            auth = auth_env.get_auth_service_url()
            
            # All should contain 'staging'
            assert 'staging' in frontend, "Staging frontend URL missing 'staging' subdomain"
            assert 'staging' in backend, "Staging backend URL missing 'staging' subdomain"
            assert 'staging' in auth, "Staging auth URL missing 'staging' subdomain"
    
    def test_production_urls_no_staging(self):
        """Ensure production URLs never contain staging references."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            auth_env = AuthEnvironment()
            
            frontend = auth_env.get_frontend_url()
            backend = auth_env.get_backend_url()
            auth = auth_env.get_auth_service_url()
            
            # None should contain staging
            assert 'staging' not in frontend, "Production frontend URL contains 'staging'"
            assert 'staging' not in backend, "Production backend URL contains 'staging'"
            assert 'staging' not in auth, "Production auth URL contains 'staging'"
    
    def test_oauth_redirect_matches_frontend_domain(self):
        """Regression test: OAuth redirect must match frontend domain."""
    pass
        environments = ['development', 'test', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                auth_env = AuthEnvironment()
                
                frontend = auth_env.get_frontend_url()
                redirect = auth_env.get_oauth_redirect_uri()
                
                # Redirect should start with frontend URL
                assert redirect.startswith(frontend), \
                    f"{env}: OAuth redirect {redirect} doesn't match frontend {frontend}"
                
                # Redirect should end with /auth/callback
                assert redirect.endswith('/auth/callback'), \
                    f"{env}: OAuth redirect {redirect} doesn't end with /auth/callback"


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])