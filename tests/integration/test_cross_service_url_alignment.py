"""
Cross-service URL alignment tests.

Ensures that backend, auth, and frontend services all agree on URLs
and can communicate properly in all environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable reliable service-to-service communication
- Value Impact: Prevents authentication and service discovery failures
- Strategic Impact: Foundation for microservices architecture reliability
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestServiceURLAlignment:
    """Test that all services agree on URLs."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test environment."""
        self.original_env = os.environ.copy()
        self.modules_to_clear = [
            'auth_service.auth_core.auth_environment',
            'auth_service.auth_core.config',
            'netra_backend.app.clients.auth_client_config',
            'netra_backend.app.core.environment_constants',
            'netra_backend.app.core.backend_environment',
            'shared.isolated_environment'
        ]
        yield
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def _clear_module_cache(self):
        """Clear module cache to force reimport."""
        for module in self.modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
    
    def test_backend_knows_correct_auth_url(self):
        """Test that backend service knows the correct auth service URL."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                self._clear_module_cache()
                
                # Get auth service's own URL
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                auth_url = auth_env.get_auth_service_url()
                
                # Get backend's view of auth URL
                from netra_backend.app.clients.auth_client_config import load_auth_client_config
                backend_config = load_auth_client_config()
                backend_auth_url = backend_config.service_url
                
                # Log for debugging
                logger.info(f"{env} - Auth service URL: {auth_url}")
                logger.info(f"{env} - Backend view of auth: {backend_auth_url}")
                
                # They should match
                assert auth_url == backend_auth_url, \
                    f"{env}: URL mismatch - Auth: {auth_url}, Backend view: {backend_auth_url}"
    
    def test_auth_knows_correct_frontend_url(self):
        """Test that auth service knows the correct frontend URL for redirects."""
        environments = ['development', 'staging', 'production']
        
        expected_urls = {
            'development': 'http://localhost:3000',
            'staging': 'https://app.staging.netrasystems.ai',
            'production': 'https://app.netrasystems.ai'
        }
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                self._clear_module_cache()
                
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                frontend_url = auth_env.get_frontend_url()
                
                expected = expected_urls[env]
                assert frontend_url == expected, \
                    f"{env}: Auth has wrong frontend URL - got {frontend_url}, expected {expected}"
    
    def test_auth_knows_correct_backend_url(self):
        """Test that auth service knows the correct backend URL for callbacks."""
        environments = ['development', 'staging', 'production']
        
        expected_urls = {
            'development': 'http://localhost:8000',
            'staging': 'https://backend.staging.netrasystems.ai',
            'production': 'https://backend.netrasystems.ai'
        }
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                self._clear_module_cache()
                
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                backend_url = auth_env.get_backend_url()
                
                expected = expected_urls[env]
                assert backend_url == expected, \
                    f"{env}: Auth has wrong backend URL - got {backend_url}, expected {expected}"
    
    def test_service_url_consistency_matrix(self):
        """Test complete service URL consistency matrix."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                self._clear_module_cache()
                
                # Import all service configs
                from auth_service.auth_core.auth_environment import AuthEnvironment
                from netra_backend.app.clients.auth_client_config import (
                    load_auth_client_config, OAuthConfigGenerator
                )
                
                auth_env = AuthEnvironment()
                backend_auth_config = load_auth_client_config()
                oauth_gen = OAuthConfigGenerator()
                
                # Build URL matrix
                url_matrix = {
                    'auth_view': {
                        'frontend': auth_env.get_frontend_url(),
                        'backend': auth_env.get_backend_url(),
                        'auth': auth_env.get_auth_service_url()
                    },
                    'backend_view': {
                        'auth': backend_auth_config.service_url
                    }
                }
                
                logger.info(f"\n{env} URL Matrix:")
                logger.info(f"  Auth view of frontend: {url_matrix['auth_view']['frontend']}")
                logger.info(f"  Auth view of backend: {url_matrix['auth_view']['backend']}")
                logger.info(f"  Auth view of self: {url_matrix['auth_view']['auth']}")
                logger.info(f"  Backend view of auth: {url_matrix['backend_view']['auth']}")
                
                # Validate consistency
                self._validate_url_consistency(env, url_matrix)
    
    def _validate_url_consistency(self, env: str, url_matrix: Dict[str, Dict[str, str]]):
        """Validate URL consistency for an environment."""
        # All URLs should use same protocol in staging/production
        if env in ['staging', 'production']:
            all_urls = []
            for view in url_matrix.values():
                all_urls.extend(view.values())
            
            # All should be HTTPS
            for url in all_urls:
                assert url.startswith('https://'), \
                    f"{env}: URL not using HTTPS: {url}"
            
            # All should contain correct domain
            for url in all_urls:
                assert 'netrasystems.ai' in url, \
                    f"{env}: URL missing netrasystems.ai domain: {url}"
            
            # Staging URLs should contain 'staging'
            if env == 'staging':
                for url in all_urls:
                    assert 'staging' in url, \
                        f"Staging URL missing 'staging': {url}"


class TestOAuthURLAlignment:
    """Test OAuth configuration alignment across services."""
    
    def test_oauth_redirect_uri_alignment(self):
        """Test that OAuth redirect URIs are aligned."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Clear module cache
                for module in ['auth_service.auth_core.auth_environment',
                             'netra_backend.app.clients.auth_client_config']:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # Get auth service OAuth redirect
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                auth_redirect = auth_env.get_oauth_redirect_uri()
                
                # Get backend OAuth config
                from netra_backend.app.clients.auth_client_config import OAuthConfigGenerator
                oauth_gen = OAuthConfigGenerator()
                backend_oauth = oauth_gen.generate(env)
                backend_redirect = backend_oauth.get('google', {}).get('redirect_uri', '')
                
                logger.info(f"{env} OAuth redirects:")
                logger.info(f"  Auth service: {auth_redirect}")
                logger.info(f"  Backend config: {backend_redirect}")
                
                # Both should use same base domain
                auth_domain = auth_redirect.split('/auth/')[0]
                backend_domain = backend_redirect.split('/auth/')[0]
                
                # In production/staging, domains should match pattern
                if env in ['staging', 'production']:
                    assert 'netrasystems.ai' in auth_domain, \
                        f"{env}: Auth OAuth redirect missing netrasystems.ai"
    
    def test_oauth_client_id_alignment(self):
        """Test that OAuth client IDs are configured consistently."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            # Set up OAuth credentials
            oauth_env = {
                'ENVIRONMENT': env,
                f'GOOGLE_OAUTH_CLIENT_ID_{env.upper()}': f'test-client-id-{env}',
                f'GOOGLE_OAUTH_CLIENT_SECRET_{env.upper()}': f'test-secret-{env}'
            }
            
            with patch.dict(os.environ, oauth_env, clear=True):
                # Clear module cache
                if 'auth_service.auth_core.auth_environment' in sys.modules:
                    del sys.modules['auth_service.auth_core.auth_environment']
                
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                
                client_id = auth_env.get_oauth_google_client_id()
                
                # Should get environment-specific client ID
                if env in ['staging', 'production']:
                    expected = f'test-client-id-{env}'
                    assert client_id == expected, \
                        f"{env}: Wrong OAuth client ID - got '{client_id}', expected '{expected}'"


class TestCORSAlignment:
    """Test CORS configuration alignment."""
    
    def test_cors_includes_all_service_urls(self):
        """Test that CORS origins include all service URLs."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Clear module cache
                if 'auth_service.auth_core.auth_environment' in sys.modules:
                    del sys.modules['auth_service.auth_core.auth_environment']
                
                from auth_service.auth_core.auth_environment import AuthEnvironment
                auth_env = AuthEnvironment()
                
                frontend_url = auth_env.get_frontend_url()
                cors_origins = auth_env.get_cors_origins()
                
                # Frontend URL should be in CORS origins
                frontend_base = frontend_url.rstrip('/')
                
                # Check if any CORS origin matches frontend
                found = False
                for origin in cors_origins:
                    if origin.rstrip('/') == frontend_base:
                        found = True
                        break
                
                assert found, \
                    f"{env}: Frontend URL {frontend_url} not in CORS origins {cors_origins}"


class TestHealthCheckURLs:
    """Test health check URL construction."""
    
    def test_health_check_urls_correct(self):
        """Test that health check URLs are correctly constructed."""
        environments = ['development', 'staging', 'production']
        
        expected_health_urls = {
            'development': 'http://localhost:8081/health',
            'staging': 'https://auth.staging.netrasystems.ai/health',
            'production': 'https://auth.netrasystems.ai/health'
        }
        
        for env in environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
                # Clear module cache
                if 'netra_backend.app.clients.auth_client_config' in sys.modules:
                    del sys.modules['netra_backend.app.clients.auth_client_config']
                
                from netra_backend.app.clients.auth_client_config import load_auth_client_config
                config = load_auth_client_config()
                
                health_url = config.health_url
                expected = expected_health_urls.get(env)
                
                if expected:
                    assert health_url == expected, \
                        f"{env}: Health URL mismatch - got {health_url}, expected {expected}"


class TestEnvironmentIsolation:
    """Test that environments are properly isolated."""
    
    def test_no_production_urls_in_staging(self):
        """Test that staging doesn't accidentally use production URLs."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
            # Clear module cache
            modules = [
                'auth_service.auth_core.auth_environment',
                'netra_backend.app.clients.auth_client_config'
            ]
            for module in modules:
                if module in sys.modules:
                    del sys.modules[module]
            
            from auth_service.auth_core.auth_environment import AuthEnvironment
            auth_env = AuthEnvironment()
            
            # Get all URLs
            urls = [
                auth_env.get_frontend_url(),
                auth_env.get_backend_url(),
                auth_env.get_auth_service_url(),
                auth_env.get_oauth_redirect_uri()
            ]
            
            # Check none contain production patterns
            for url in urls:
                # Should not have production domain without staging
                if 'netrasystems.ai' in url:
                    assert 'staging' in url, \
                        f"Staging URL looks like production: {url}"
                
                # Should not be exactly the production URL
                assert url not in [
                    'https://app.netrasystems.ai',
                    'https://backend.netrasystems.ai',
                    'https://auth.netrasystems.ai'
                ], f"Staging is using production URL: {url}"
    
    def test_no_staging_urls_in_production(self):
        """Test that production doesn't accidentally use staging URLs."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            # Clear module cache
            if 'auth_service.auth_core.auth_environment' in sys.modules:
                del sys.modules['auth_service.auth_core.auth_environment']
            
            from auth_service.auth_core.auth_environment import AuthEnvironment
            auth_env = AuthEnvironment()
            
            # Get all URLs
            urls = [
                auth_env.get_frontend_url(),
                auth_env.get_backend_url(),
                auth_env.get_auth_service_url(),
                auth_env.get_oauth_redirect_uri()
            ]
            
            # Check none contain staging
            for url in urls:
                assert 'staging' not in url, \
                    f"Production URL contains 'staging': {url}"


def test_comprehensive_url_alignment_report():
    """Generate comprehensive URL alignment report."""
    logger.info("\n" + "="*60)
    logger.info("COMPREHENSIVE URL ALIGNMENT REPORT")
    logger.info("="*60)
    
    environments = ['development', 'staging', 'production']
    report = {}
    
    for env in environments:
        with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear all cached modules
            modules = [
                'auth_service.auth_core.auth_environment',
                'auth_service.auth_core.config',
                'netra_backend.app.clients.auth_client_config',
                'shared.isolated_environment'
            ]
            for module in modules:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Import services
            from auth_service.auth_core.auth_environment import AuthEnvironment
            from auth_service.auth_core.config import AuthConfig
            from netra_backend.app.clients.auth_client_config import load_auth_client_config
            
            auth_env = AuthEnvironment()
            auth_config = AuthConfig()
            backend_config = load_auth_client_config()
            
            # Collect URLs
            report[env] = {
                'Auth Service': {
                    'Frontend URL': auth_env.get_frontend_url(),
                    'Backend URL': auth_env.get_backend_url(),
                    'Auth URL': auth_env.get_auth_service_url(),
                    'OAuth Redirect': auth_env.get_oauth_redirect_uri()
                },
                'Auth Config': {
                    'Frontend URL': auth_config.get_frontend_url(),
                    'Auth URL': auth_config.get_auth_service_url()
                },
                'Backend Client': {
                    'Auth Service URL': backend_config.service_url,
                    'Health URL': backend_config.health_url,
                    'Base URL': backend_config.base_url
                }
            }
    
    # Print report
    for env, services in report.items():
        logger.info(f"\n{env.upper()} Environment:")
        for service, urls in services.items():
            logger.info(f"  {service}:")
            for name, url in urls.items():
                logger.info(f"    {name}: {url}")
    
    # Validate alignment
    logger.info("\n" + "-"*60)
    logger.info("VALIDATION RESULTS:")
    
    all_valid = True
    for env in environments:
        env_data = report[env]
        
        # Check Auth Service vs Auth Config alignment
        auth_frontend = env_data['Auth Service']['Frontend URL']
        config_frontend = env_data['Auth Config']['Frontend URL']
        if auth_frontend != config_frontend:
            logger.error(f"{env}: Frontend URL mismatch between AuthEnvironment and AuthConfig")
            all_valid = False
        
        # Check auth service URL alignment
        auth_self = env_data['Auth Service']['Auth URL']
        backend_view = env_data['Backend Client']['Auth Service URL']
        if auth_self != backend_view:
            logger.error(f"{env}: Auth URL mismatch - Auth: {auth_self}, Backend: {backend_view}")
            all_valid = False
    
    if all_valid:
        logger.info("✓ All service URLs are properly aligned!")
    else:
        logger.error("✗ Service URL misalignment detected!")
        raise AssertionError("Service URLs are not properly aligned")
    
    logger.info("="*60)


if __name__ == '__main__':
    # Run comprehensive report first
    try:
        test_comprehensive_url_alignment_report()
    except AssertionError as e:
        print(f"\nAlignment report failed: {e}")
        sys.exit(1)
    
    # Run full test suite
    pytest.main([__file__, '-v', '--tb=short'])