# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Cross-service URL alignment tests.

# REMOVED_SYNTAX_ERROR: Ensures that backend, auth, and frontend services all agree on URLs
# REMOVED_SYNTAX_ERROR: and can communicate properly in all environments.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Enable reliable service-to-service communication
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents authentication and service discovery failures
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Foundation for microservices architecture reliability
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Tuple
    # REMOVED_SYNTAX_ERROR: import logging
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: logging.basicConfig(level=logging.INFO)
    # REMOVED_SYNTAX_ERROR: logger = logging.getLogger(__name__)


# REMOVED_SYNTAX_ERROR: class TestServiceURLAlignment:
    # REMOVED_SYNTAX_ERROR: """Test that all services agree on URLs."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Setup test environment."""
    # REMOVED_SYNTAX_ERROR: self.original_env = os.environ.copy()
    # REMOVED_SYNTAX_ERROR: self.modules_to_clear = [ )
    # REMOVED_SYNTAX_ERROR: 'auth_service.auth_core.auth_environment',
    # REMOVED_SYNTAX_ERROR: 'auth_service.auth_core.config',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.clients.auth_client_config',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.core.environment_constants',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.core.backend_environment',
    # REMOVED_SYNTAX_ERROR: 'shared.isolated_environment'
    
    # REMOVED_SYNTAX_ERROR: yield
    # REMOVED_SYNTAX_ERROR: os.environ.clear()
    # REMOVED_SYNTAX_ERROR: os.environ.update(self.original_env)

# REMOVED_SYNTAX_ERROR: def _clear_module_cache(self):
    # REMOVED_SYNTAX_ERROR: """Clear module cache to force reimport."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: for module in self.modules_to_clear:
        # REMOVED_SYNTAX_ERROR: if module in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[module]

# REMOVED_SYNTAX_ERROR: def test_backend_knows_correct_auth_url(self):
    # REMOVED_SYNTAX_ERROR: """Test that backend service knows the correct auth service URL."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # REMOVED_SYNTAX_ERROR: self._clear_module_cache()

            # Get auth service's own URL
            # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
            # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
            # REMOVED_SYNTAX_ERROR: auth_url = auth_env.get_auth_service_url()

            # Get backend's view of auth URL
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_config import load_auth_client_config
            # REMOVED_SYNTAX_ERROR: backend_config = load_auth_client_config()
            # REMOVED_SYNTAX_ERROR: backend_auth_url = backend_config.service_url

            # Log for debugging
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # They should match
            # REMOVED_SYNTAX_ERROR: assert auth_url == backend_auth_url, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_auth_knows_correct_frontend_url(self):
    # REMOVED_SYNTAX_ERROR: """Test that auth service knows the correct frontend URL for redirects."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: expected_urls = { )
    # REMOVED_SYNTAX_ERROR: 'development': 'http://localhost:3000',
    # REMOVED_SYNTAX_ERROR: 'staging': 'https://app.staging.netrasystems.ai',
    # REMOVED_SYNTAX_ERROR: 'production': 'https://app.netrasystems.ai'
    

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # REMOVED_SYNTAX_ERROR: self._clear_module_cache()

            # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
            # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
            # REMOVED_SYNTAX_ERROR: frontend_url = auth_env.get_frontend_url()

            # REMOVED_SYNTAX_ERROR: expected = expected_urls[env]
            # REMOVED_SYNTAX_ERROR: assert frontend_url == expected, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_auth_knows_correct_backend_url(self):
    # REMOVED_SYNTAX_ERROR: """Test that auth service knows the correct backend URL for callbacks."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: expected_urls = { )
    # REMOVED_SYNTAX_ERROR: 'development': 'http://localhost:8000',
    # REMOVED_SYNTAX_ERROR: 'staging': 'https://backend.staging.netrasystems.ai',
    # REMOVED_SYNTAX_ERROR: 'production': 'https://backend.netrasystems.ai'
    

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # REMOVED_SYNTAX_ERROR: self._clear_module_cache()

            # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
            # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
            # REMOVED_SYNTAX_ERROR: backend_url = auth_env.get_backend_url()

            # REMOVED_SYNTAX_ERROR: expected = expected_urls[env]
            # REMOVED_SYNTAX_ERROR: assert backend_url == expected, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_service_url_consistency_matrix(self):
    # REMOVED_SYNTAX_ERROR: """Test complete service URL consistency matrix."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # REMOVED_SYNTAX_ERROR: self._clear_module_cache()

            # Import all service configs
            # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_config import ( )
            # REMOVED_SYNTAX_ERROR: load_auth_client_config, OAuthConfigGenerator
            

            # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
            # REMOVED_SYNTAX_ERROR: backend_auth_config = load_auth_client_config()
            # REMOVED_SYNTAX_ERROR: oauth_gen = OAuthConfigGenerator()

            # Build URL matrix
            # REMOVED_SYNTAX_ERROR: url_matrix = { )
            # REMOVED_SYNTAX_ERROR: 'auth_view': { )
            # REMOVED_SYNTAX_ERROR: 'frontend': auth_env.get_frontend_url(),
            # REMOVED_SYNTAX_ERROR: 'backend': auth_env.get_backend_url(),
            # REMOVED_SYNTAX_ERROR: 'auth': auth_env.get_auth_service_url()
            # REMOVED_SYNTAX_ERROR: },
            # REMOVED_SYNTAX_ERROR: 'backend_view': { )
            # REMOVED_SYNTAX_ERROR: 'auth': backend_auth_config.service_url
            
            

            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # Validate consistency
            # REMOVED_SYNTAX_ERROR: self._validate_url_consistency(env, url_matrix)

# REMOVED_SYNTAX_ERROR: def _validate_url_consistency(self, env: str, url_matrix: Dict[str, Dict[str, str]]):
    # REMOVED_SYNTAX_ERROR: """Validate URL consistency for an environment."""
    # All URLs should use same protocol in staging/production
    # REMOVED_SYNTAX_ERROR: if env in ['staging', 'production']:
        # REMOVED_SYNTAX_ERROR: all_urls = []
        # REMOVED_SYNTAX_ERROR: for view in url_matrix.values():
            # REMOVED_SYNTAX_ERROR: all_urls.extend(view.values())

            # All should be HTTPS
            # REMOVED_SYNTAX_ERROR: for url in all_urls:
                # REMOVED_SYNTAX_ERROR: assert url.startswith('https://'), \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # All should contain correct domain
                # REMOVED_SYNTAX_ERROR: for url in all_urls:
                    # REMOVED_SYNTAX_ERROR: assert 'netrasystems.ai' in url, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Staging URLs should contain 'staging'
                    # REMOVED_SYNTAX_ERROR: if env == 'staging':
                        # REMOVED_SYNTAX_ERROR: for url in all_urls:
                            # REMOVED_SYNTAX_ERROR: assert 'staging' in url, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestOAuthURLAlignment:
    # REMOVED_SYNTAX_ERROR: """Test OAuth configuration alignment across services."""

# REMOVED_SYNTAX_ERROR: def test_oauth_redirect_uri_alignment(self):
    # REMOVED_SYNTAX_ERROR: """Test that OAuth redirect URIs are aligned."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear module cache
            # REMOVED_SYNTAX_ERROR: for module in ['auth_service.auth_core.auth_environment',
            # REMOVED_SYNTAX_ERROR: 'netra_backend.app.clients.auth_client_config']:
                # REMOVED_SYNTAX_ERROR: if module in sys.modules:
                    # REMOVED_SYNTAX_ERROR: del sys.modules[module]

                    # Get auth service OAuth redirect
                    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
                    # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
                    # REMOVED_SYNTAX_ERROR: auth_redirect = auth_env.get_oauth_redirect_uri()

                    # Get backend OAuth config
                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_config import OAuthConfigGenerator
                    # REMOVED_SYNTAX_ERROR: oauth_gen = OAuthConfigGenerator()
                    # REMOVED_SYNTAX_ERROR: backend_oauth = oauth_gen.generate(env)
                    # REMOVED_SYNTAX_ERROR: backend_redirect = backend_oauth.get('google', {}).get('redirect_uri', '')

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                    # Both should use same base domain
                    # REMOVED_SYNTAX_ERROR: auth_domain = auth_redirect.split('/auth/')[0]
                    # REMOVED_SYNTAX_ERROR: backend_domain = backend_redirect.split('/auth/')[0]

                    # In production/staging, domains should match pattern
                    # REMOVED_SYNTAX_ERROR: if env in ['staging', 'production']:
                        # REMOVED_SYNTAX_ERROR: assert 'netrasystems.ai' in auth_domain, \
                        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_oauth_client_id_alignment(self):
    # REMOVED_SYNTAX_ERROR: """Test that OAuth client IDs are configured consistently."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # Set up OAuth credentials
        # REMOVED_SYNTAX_ERROR: oauth_env = { )
        # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': env,
        # REMOVED_SYNTAX_ERROR: 'formatted_string': 'formatted_string',
        # REMOVED_SYNTAX_ERROR: 'formatted_string': 'formatted_string'
        

        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, oauth_env, clear=True):
            # Clear module cache
            # REMOVED_SYNTAX_ERROR: if 'auth_service.auth_core.auth_environment' in sys.modules:
                # REMOVED_SYNTAX_ERROR: del sys.modules['auth_service.auth_core.auth_environment']

                # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
                # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()

                # REMOVED_SYNTAX_ERROR: client_id = auth_env.get_oauth_google_client_id()

                # Should get environment-specific client ID
                # REMOVED_SYNTAX_ERROR: if env in ['staging', 'production']:
                    # REMOVED_SYNTAX_ERROR: expected = 'formatted_string'
                    # REMOVED_SYNTAX_ERROR: assert client_id == expected, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestCORSAlignment:
    # REMOVED_SYNTAX_ERROR: """Test CORS configuration alignment."""

# REMOVED_SYNTAX_ERROR: def test_cors_includes_all_service_urls(self):
    # REMOVED_SYNTAX_ERROR: """Test that CORS origins include all service URLs."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear module cache
            # REMOVED_SYNTAX_ERROR: if 'auth_service.auth_core.auth_environment' in sys.modules:
                # REMOVED_SYNTAX_ERROR: del sys.modules['auth_service.auth_core.auth_environment']

                # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
                # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()

                # REMOVED_SYNTAX_ERROR: frontend_url = auth_env.get_frontend_url()
                # REMOVED_SYNTAX_ERROR: cors_origins = auth_env.get_cors_origins()

                # Frontend URL should be in CORS origins
                # REMOVED_SYNTAX_ERROR: frontend_base = frontend_url.rstrip('/')

                # Check if any CORS origin matches frontend
                # REMOVED_SYNTAX_ERROR: found = False
                # REMOVED_SYNTAX_ERROR: for origin in cors_origins:
                    # REMOVED_SYNTAX_ERROR: if origin.rstrip('/') == frontend_base:
                        # REMOVED_SYNTAX_ERROR: found = True
                        # REMOVED_SYNTAX_ERROR: break

                        # REMOVED_SYNTAX_ERROR: assert found, \
                        # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestHealthCheckURLs:
    # REMOVED_SYNTAX_ERROR: """Test health check URL construction."""

# REMOVED_SYNTAX_ERROR: def test_health_check_urls_correct(self):
    # REMOVED_SYNTAX_ERROR: """Test that health check URLs are correctly constructed."""
    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']

    # REMOVED_SYNTAX_ERROR: expected_health_urls = { )
    # REMOVED_SYNTAX_ERROR: 'development': 'http://localhost:8081/health',
    # REMOVED_SYNTAX_ERROR: 'staging': 'https://auth.staging.netrasystems.ai/health',
    # REMOVED_SYNTAX_ERROR: 'production': 'https://auth.netrasystems.ai/health'
    

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear module cache
            # REMOVED_SYNTAX_ERROR: if 'netra_backend.app.clients.auth_client_config' in sys.modules:
                # REMOVED_SYNTAX_ERROR: del sys.modules['netra_backend.app.clients.auth_client_config']

                # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_config import load_auth_client_config
                # REMOVED_SYNTAX_ERROR: config = load_auth_client_config()

                # REMOVED_SYNTAX_ERROR: health_url = config.health_url
                # REMOVED_SYNTAX_ERROR: expected = expected_health_urls.get(env)

                # REMOVED_SYNTAX_ERROR: if expected:
                    # REMOVED_SYNTAX_ERROR: assert health_url == expected, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestEnvironmentIsolation:
    # REMOVED_SYNTAX_ERROR: """Test that environments are properly isolated."""

# REMOVED_SYNTAX_ERROR: def test_no_production_urls_in_staging(self):
    # REMOVED_SYNTAX_ERROR: """Test that staging doesn't accidentally use production URLs."""
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        # Clear module cache
        # REMOVED_SYNTAX_ERROR: modules = [ )
        # REMOVED_SYNTAX_ERROR: 'auth_service.auth_core.auth_environment',
        # REMOVED_SYNTAX_ERROR: 'netra_backend.app.clients.auth_client_config'
        
        # REMOVED_SYNTAX_ERROR: for module in modules:
            # REMOVED_SYNTAX_ERROR: if module in sys.modules:
                # REMOVED_SYNTAX_ERROR: del sys.modules[module]

                # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
                # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()

                # Get all URLs
                # REMOVED_SYNTAX_ERROR: urls = [ )
                # REMOVED_SYNTAX_ERROR: auth_env.get_frontend_url(),
                # REMOVED_SYNTAX_ERROR: auth_env.get_backend_url(),
                # REMOVED_SYNTAX_ERROR: auth_env.get_auth_service_url(),
                # REMOVED_SYNTAX_ERROR: auth_env.get_oauth_redirect_uri()
                

                # Check none contain production patterns
                # REMOVED_SYNTAX_ERROR: for url in urls:
                    # Should not have production domain without staging
                    # REMOVED_SYNTAX_ERROR: if 'netrasystems.ai' in url:
                        # REMOVED_SYNTAX_ERROR: assert 'staging' in url, \
                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                        # Should not be exactly the production URL
                        # REMOVED_SYNTAX_ERROR: assert url not in [ )
                        # REMOVED_SYNTAX_ERROR: 'https://app.netrasystems.ai',
                        # REMOVED_SYNTAX_ERROR: 'https://backend.netrasystems.ai',
                        # REMOVED_SYNTAX_ERROR: 'https://auth.netrasystems.ai'
                        # REMOVED_SYNTAX_ERROR: ], "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_no_staging_urls_in_production(self):
    # REMOVED_SYNTAX_ERROR: """Test that production doesn't accidentally use staging URLs."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
        # Clear module cache
        # REMOVED_SYNTAX_ERROR: if 'auth_service.auth_core.auth_environment' in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules['auth_service.auth_core.auth_environment']

            # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
            # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()

            # Get all URLs
            # REMOVED_SYNTAX_ERROR: urls = [ )
            # REMOVED_SYNTAX_ERROR: auth_env.get_frontend_url(),
            # REMOVED_SYNTAX_ERROR: auth_env.get_backend_url(),
            # REMOVED_SYNTAX_ERROR: auth_env.get_auth_service_url(),
            # REMOVED_SYNTAX_ERROR: auth_env.get_oauth_redirect_uri()
            

            # Check none contain staging
            # REMOVED_SYNTAX_ERROR: for url in urls:
                # REMOVED_SYNTAX_ERROR: assert 'staging' not in url, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: def test_comprehensive_url_alignment_report():
    # REMOVED_SYNTAX_ERROR: """Generate comprehensive URL alignment report."""
    # REMOVED_SYNTAX_ERROR: logger.info(" )
    # REMOVED_SYNTAX_ERROR: " + "="*60)
    # REMOVED_SYNTAX_ERROR: logger.info("COMPREHENSIVE URL ALIGNMENT REPORT")
    # REMOVED_SYNTAX_ERROR: logger.info("="*60)

    # REMOVED_SYNTAX_ERROR: environments = ['development', 'staging', 'production']
    # REMOVED_SYNTAX_ERROR: report = {}

    # REMOVED_SYNTAX_ERROR: for env in environments:
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear all cached modules
            # REMOVED_SYNTAX_ERROR: modules = [ )
            # REMOVED_SYNTAX_ERROR: 'auth_service.auth_core.auth_environment',
            # REMOVED_SYNTAX_ERROR: 'auth_service.auth_core.config',
            # REMOVED_SYNTAX_ERROR: 'netra_backend.app.clients.auth_client_config',
            # REMOVED_SYNTAX_ERROR: 'shared.isolated_environment'
            
            # REMOVED_SYNTAX_ERROR: for module in modules:
                # REMOVED_SYNTAX_ERROR: if module in sys.modules:
                    # REMOVED_SYNTAX_ERROR: del sys.modules[module]

                    # Import services
                    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.auth_environment import AuthEnvironment
                    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.config import AuthConfig
                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_config import load_auth_client_config

                    # REMOVED_SYNTAX_ERROR: auth_env = AuthEnvironment()
                    # REMOVED_SYNTAX_ERROR: auth_config = AuthConfig()
                    # REMOVED_SYNTAX_ERROR: backend_config = load_auth_client_config()

                    # Collect URLs
                    # REMOVED_SYNTAX_ERROR: report[env] = { )
                    # REMOVED_SYNTAX_ERROR: 'Auth Service': { )
                    # REMOVED_SYNTAX_ERROR: 'Frontend URL': auth_env.get_frontend_url(),
                    # REMOVED_SYNTAX_ERROR: 'Backend URL': auth_env.get_backend_url(),
                    # REMOVED_SYNTAX_ERROR: 'Auth URL': auth_env.get_auth_service_url(),
                    # REMOVED_SYNTAX_ERROR: 'OAuth Redirect': auth_env.get_oauth_redirect_uri()
                    # REMOVED_SYNTAX_ERROR: },
                    # REMOVED_SYNTAX_ERROR: 'Auth Config': { )
                    # REMOVED_SYNTAX_ERROR: 'Frontend URL': auth_config.get_frontend_url(),
                    # REMOVED_SYNTAX_ERROR: 'Auth URL': auth_config.get_auth_service_url()
                    # REMOVED_SYNTAX_ERROR: },
                    # REMOVED_SYNTAX_ERROR: 'Backend Client': { )
                    # REMOVED_SYNTAX_ERROR: 'Auth Service URL': backend_config.service_url,
                    # REMOVED_SYNTAX_ERROR: 'Health URL': backend_config.health_url,
                    # REMOVED_SYNTAX_ERROR: 'Base URL': backend_config.base_url
                    
                    

                    # Print report
                    # REMOVED_SYNTAX_ERROR: for env, services in report.items():
                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                        # REMOVED_SYNTAX_ERROR: for service, urls in services.items():
                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                            # REMOVED_SYNTAX_ERROR: for name, url in urls.items():
                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                # Validate alignment
                                # REMOVED_SYNTAX_ERROR: logger.info(" )
                                # REMOVED_SYNTAX_ERROR: " + "-"*60)
                                # REMOVED_SYNTAX_ERROR: logger.info("VALIDATION RESULTS:")

                                # REMOVED_SYNTAX_ERROR: all_valid = True
                                # REMOVED_SYNTAX_ERROR: for env in environments:
                                    # REMOVED_SYNTAX_ERROR: env_data = report[env]

                                    # Check Auth Service vs Auth Config alignment
                                    # REMOVED_SYNTAX_ERROR: auth_frontend = env_data['Auth Service']['Frontend URL']
                                    # REMOVED_SYNTAX_ERROR: config_frontend = env_data['Auth Config']['Frontend URL']
                                    # REMOVED_SYNTAX_ERROR: if auth_frontend != config_frontend:
                                        # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                        # REMOVED_SYNTAX_ERROR: all_valid = False

                                        # Check auth service URL alignment
                                        # REMOVED_SYNTAX_ERROR: auth_self = env_data['Auth Service']['Auth URL']
                                        # REMOVED_SYNTAX_ERROR: backend_view = env_data['Backend Client']['Auth Service URL']
                                        # REMOVED_SYNTAX_ERROR: if auth_self != backend_view:
                                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                            # REMOVED_SYNTAX_ERROR: all_valid = False

                                            # REMOVED_SYNTAX_ERROR: if all_valid:
                                                # REMOVED_SYNTAX_ERROR: logger.info("✓ All service URLs are properly aligned!")
                                                # REMOVED_SYNTAX_ERROR: else:
                                                    # REMOVED_SYNTAX_ERROR: logger.error("✗ Service URL misalignment detected!")
                                                    # REMOVED_SYNTAX_ERROR: raise AssertionError("Service URLs are not properly aligned")

                                                    # REMOVED_SYNTAX_ERROR: logger.info("="*60)


                                                    # REMOVED_SYNTAX_ERROR: if __name__ == '__main__':
                                                        # Run comprehensive report first
                                                        # REMOVED_SYNTAX_ERROR: try:
                                                            # REMOVED_SYNTAX_ERROR: test_comprehensive_url_alignment_report()
                                                            # REMOVED_SYNTAX_ERROR: except AssertionError as e:
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                # REMOVED_SYNTAX_ERROR: sys.exit(1)

                                                                # Run full test suite
                                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, '-v', '--tb=short'])
                                                                # REMOVED_SYNTAX_ERROR: pass