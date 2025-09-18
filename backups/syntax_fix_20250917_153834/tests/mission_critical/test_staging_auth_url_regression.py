'''
Mission-critical regression tests for staging auth URL configuration.

This test suite specifically prevents the staging URL regression where
auth URLs were returning localhost instead of proper staging URLs.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures
- Value Impact: Ensures staging environment works for pre-production testing
- Strategic Impact: Critical for validating changes before production deployment

CRITICAL: These tests MUST pass before any deployment to staging.
'''

import pytest
import os
import sys
from typing import Dict, Any, List
import logging
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import IsolatedEnvironment

    # Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Fix Windows encoding
if sys.platform == 'win32':
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

        # Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStagingAuthURLRegression:
    """Critical regression tests for staging auth URL configuration bug."""

    @pytest.fixture
    def setup_method(self):
        """Setup test environment."""
        self.original_env = os.environ.copy()

    # Clear all URL-related env vars
        url_vars = [
        'ENVIRONMENT', 'FRONTEND_URL', 'BACKEND_URL',
        'AUTH_SERVICE_URL', 'OAUTH_REDIRECT_URI',
        'AUTH_SERVICE_HOST', 'AUTH_SERVICE_PORT'
    
        for var in url_vars:
        os.environ.pop(var, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_staging_never_returns_localhost(self):
        """CRITICAL: Staging must NEVER return localhost URLs."""
        pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        # Force fresh import
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']
        if 'auth_service.auth_core.config' in sys.modules:
        del sys.modules['auth_service.auth_core.config']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        from auth_service.auth_core.config import AuthConfig

        auth_env = AuthEnvironment()
        config = AuthConfig()

                # Get all URLs
        urls_to_check = {
        'frontend': auth_env.get_frontend_url(),
        'backend': auth_env.get_backend_url(),
        'auth_service': auth_env.get_auth_service_url(),
        'oauth_redirect': auth_env.get_oauth_redirect_uri(),
        'config_frontend': config.get_frontend_url(),
        'config_auth': config.get_auth_service_url()
                

                # Check each URL
        failures = []
        for name, url in urls_to_check.items():
        if 'localhost' in url or '127.0.0.1' in url or '0.0.0.0' in url:
        failures.append("formatted_string")

        assert not failures, f"Staging URLs contain localhost:
        " + "
        ".join(failures)

    def test_staging_urls_use_staging_subdomain(self):
        """CRITICAL: All staging URLs must use staging subdomain."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment

        auth_env = AuthEnvironment()

        # Expected URLs
        expected = {
        'frontend': 'https://app.staging.netrasystems.ai',
        'backend': 'https://api.staging.netrasystems.ai',
        'auth': 'https://auth.staging.netrasystems.ai',
        'oauth': 'https://app.staging.netrasystems.ai/auth/callback'
        

        # Actual URLs
        actual = {
        'frontend': auth_env.get_frontend_url(),
        'backend': auth_env.get_backend_url(),
        'auth': auth_env.get_auth_service_url(),
        'oauth': auth_env.get_oauth_redirect_uri()
        

        # Compare
        mismatches = []
        for key in expected:
        if actual[key] != expected[key]:
        mismatches.append("formatted_string")

        assert not mismatches, "Staging URL mismatches:
        " + "
        ".join(mismatches)

    def test_staging_auth_host_not_bind_address(self):
        """CRITICAL: Staging auth host must be proper domain, not bind address."""
        pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment

        auth_env = AuthEnvironment()
        host = auth_env.get_auth_service_host()

        # Must not be bind address
        assert host != '0.0.0.0', "Staging auth host is bind address 0.0.0.0"
        assert host != '127.0.0.1', "Staging auth host is localhost"

        # Must be staging domain
        assert host == 'auth.staging.netrasystems.ai', \
        "formatted_string"

    def test_staging_uses_https_protocol(self):
        """CRITICAL: Staging must use HTTPS for all services."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment

        auth_env = AuthEnvironment()

        urls = [
        auth_env.get_frontend_url(),
        auth_env.get_backend_url(),
        auth_env.get_auth_service_url()
        

        for url in urls:
        assert url.startswith('https://'), \
        "formatted_string"

    def test_staging_cors_origins_correct(self):
        """CRITICAL: Staging CORS origins must allow staging domains."""
        pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment

        auth_env = AuthEnvironment()
        cors_origins = auth_env.get_cors_origins()

        # Expected staging origins
        expected_origins = [
        'https://app.staging.netrasystems.ai',
        'https://staging.netrasystems.ai'
        

        for expected in expected_origins:
        assert expected in cors_origins, \
        "formatted_string"

            # Should NOT contain localhost
        for origin in cors_origins:
        assert 'localhost' not in origin, \
        "formatted_string"

        @pytest.fixture)
                # Test that overrides still work in staging
        ('FRONTEND_URL', 'https://custom.staging.com', 'should_use_override'),
        ('BACKEND_URL', 'https://api.custom.com', 'should_use_override'),
        ('AUTH_SERVICE_URL', 'https://auth.custom.com', 'should_use_override'),
                
    def test_staging_override_behavior(self, override_var, override_value, expected_behavior):
        """Test that staging respects explicit overrides."""
        env_vars = {
        'ENVIRONMENT': 'staging',
        override_var: override_value
    

        with patch.dict(os.environ, env_vars, clear=True):
        # Clear module cache
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        auth_env = AuthEnvironment()

            # Map override var to method
        method_map = {
        'FRONTEND_URL': 'get_frontend_url',
        'BACKEND_URL': 'get_backend_url',
        'AUTH_SERVICE_URL': 'get_auth_service_url'
            

        method = getattr(auth_env, method_map[override_var])
        actual_value = method()

        if expected_behavior == 'should_use_override':
        assert actual_value == override_value, \
        "formatted_string"


class TestStagingDeploymentReadiness:
        """Tests to ensure staging deployment will work correctly."""

    def test_staging_config_matches_deployment_expectations(self):
        """Test that staging config matches what deployment scripts expect."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment
        from deployment.secrets_config import SecretConfig

        auth_env = AuthEnvironment()

        # Verify environment detection
        assert auth_env.get_environment() == 'staging'
        assert auth_env.is_staging() is True

        # Verify URLs match deployment expectations
        frontend = auth_env.get_frontend_url()
        assert 'staging.netrasystems.ai' in frontend, \
        "Frontend URL doesn"t match staging deployment domain"

    def test_backend_client_staging_configuration(self):
        """Test that backend auth client is configured correctly for staging."""
        pass
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        # Clear module cache to force reimport
        modules_to_clear = [
        'netra_backend.app.clients.auth_client_config',
        'netra_backend.app.core.environment_constants',
        'shared.isolated_environment'
        
        for module in modules_to_clear:
        if module in sys.modules:
        del sys.modules[module]

        from netra_backend.app.clients.auth_client_config import load_auth_client_config

        config = load_auth_client_config()

                # Should point to staging auth service
        assert 'staging' in config.service_url or config.service_url.startswith('https://'), \
        "formatted_string"

    def test_oauth_redirect_consistency_staging(self):
        """Test OAuth redirect URI consistency in staging."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        from auth_service.auth_core.auth_environment import AuthEnvironment

        auth_env = AuthEnvironment()

        # Get OAuth redirect
        redirect_uri = auth_env.get_oauth_redirect_uri()
        frontend_url = auth_env.get_frontend_url()

        # Redirect should use frontend URL as base
        assert redirect_uri.startswith(frontend_url), \
        "formatted_string"t match frontend {frontend_url}"

        # Should end with standard callback path
        assert redirect_uri.endswith('/auth/callback'), \
        "formatted_string"t end with /auth/callback"

        # Should be HTTPS in staging
        assert redirect_uri.startswith('https://'), \
        "formatted_string"


class TestCriticalURLValidation:
        """Critical validation tests that must pass for deployment."""

    def test_all_environments_have_distinct_urls(self):
        """Test that each environment has distinct URLs."""
        environments = ['development', 'test', 'staging', 'production']
        url_sets = {}

        for env in environments:
        with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=True):
            # Clear module cache
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        auth_env = AuthEnvironment()

        url_sets[env] = {
        'frontend': auth_env.get_frontend_url(),
        'backend': auth_env.get_backend_url(),
        'auth': auth_env.get_auth_service_url()
                

                # Check that staging and production are different
        assert url_sets['staging'] != url_sets['production'], \
        "Staging and production have identical URLs!"

                # Check that staging contains 'staging' in all URLs
        for service, url in url_sets['staging'].items():
        if 'localhost' not in url:  # Skip this check for local envs
        assert 'staging' in url, \
        "formatted_string"

    def test_no_cross_environment_contamination(self):
        """Test that environments don't contaminate each other."""
        pass
    # Set production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        prod_env = AuthEnvironment()
        prod_url = prod_env.get_frontend_url()

            # Now set staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        staging_env = AuthEnvironment()
        staging_url = staging_env.get_frontend_url()

                    # They must be different
        assert prod_url != staging_url, \
        "formatted_string"

                    # Production should not contain 'staging'
        assert 'staging' not in prod_url, \
        "formatted_string"

                    # Staging should contain 'staging'
        assert 'staging' in staging_url, \
        "formatted_string"


    def test_smoke_staging_configuration():
        """Smoke test for staging configuration - run this before deployment."""
        logger.info("="*60)
        logger.info("STAGING CONFIGURATION SMOKE TEST")
        logger.info("="*60)

        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
        # Clear module cache
        if 'auth_service.auth_core.auth_environment' in sys.modules:
        del sys.modules['auth_service.auth_core.auth_environment']

        from auth_service.auth_core.auth_environment import AuthEnvironment
        auth_env = AuthEnvironment()

            # Collect all critical URLs
        critical_config = {
        'Environment': auth_env.get_environment(),
        'Frontend URL': auth_env.get_frontend_url(),
        'Backend URL': auth_env.get_backend_url(),
        'Auth Service URL': auth_env.get_auth_service_url(),
        'OAuth Redirect': auth_env.get_oauth_redirect_uri(),
        'Auth Host': auth_env.get_auth_service_host(),
        'Auth Port': auth_env.get_auth_service_port(),
        'Is Staging': auth_env.is_staging(),
        'Is Production': auth_env.is_production()
            

            # Log configuration
        logger.info(" )
        Staging Configuration:")
        for key, value in critical_config.items():
        logger.info("formatted_string")

                # Validation checks
        validations = []

                # Check environment
        if critical_config['Environment'] != 'staging':
        validations.append("formatted_string")

                    # Check URLs contain staging
        for key in ['Frontend URL', 'Backend URL', 'Auth Service URL']:
        if 'staging' not in str(critical_config[key]):
        validations.append("formatted_string")

                            # Check HTTPS
        for key in ['Frontend URL', 'Backend URL', 'Auth Service URL']:
        if not str(critical_config[key]).startswith('https://'):
        validations.append("formatted_string")

                                    # Check no localhost
        for key, value in critical_config.items():
        if 'URL' in key or 'Host' in key:
        if 'localhost' in str(value) or '127.0.0.1' in str(value) or '0.0.0.0' in str(value):
        validations.append("formatted_string")

                                                # Report results
        if validations:
        logger.error(" )
        VALIDATION FAILURES:")
        for validation in validations:
        logger.error("formatted_string")
        raise AssertionError("formatted_string")
        else:
        logger.info(" )
        [U+2713] All staging configuration validations passed!")
        logger.info("[U+2713] Safe to deploy to staging environment")

        logger.info("="*60)


        if __name__ == '__main__':
                                                                # Run smoke test first
        try:
        test_smoke_staging_configuration()
        print("")
        [U+2713] Smoke test passed - running full test suite...
        ")
        except AssertionError as e:
        print("formatted_string")
        sys.exit(1)

                                                                        # Run full test suite
        pass
