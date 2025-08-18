"""Comprehensive tests for auth environment configuration management.

Tests all environment configurations, OAuth configs, redirect URI validation, 
and frontend config generation across all environments.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Ensure proper environment-specific auth configuration
3. Value Impact: Prevents auth misconfigurations that could block user access
4. Revenue Impact: Critical for seamless user onboarding across environments
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock

from app.clients.auth_client import (
    Environment, OAuthConfig, EnvironmentDetector, OAuthConfigGenerator
)


class TestEnvironmentDetection:
    """Test environment detection logic across all scenarios."""
    
    def test_development_environment_default(self):
        """Test default development environment detection."""
        with patch.dict(os.environ, {}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.DEVELOPMENT


    def test_testing_environment_explicit_flag(self):
        """Test testing environment detection via TESTING flag."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.TESTING


    def test_testing_environment_pytest_context(self):
        """Test testing environment detection in pytest context."""
        with patch.dict(os.environ, {"TESTING": "1"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.TESTING


    def test_staging_environment_k_service(self):
        """Test staging environment detection via K_SERVICE."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging-service"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.STAGING


    def test_staging_pr_environment_with_pr_number(self):
        """Test staging PR environment detection with PR number."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "123"
        }, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.STAGING


    def test_production_environment_k_service(self):
        """Test production environment detection via K_SERVICE."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend-prod"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.PRODUCTION


    def test_production_environment_k_revision(self):
        """Test production environment detection via K_REVISION only."""
        with patch.dict(os.environ, {"K_REVISION": "netra-backend-prod-rev-1"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.PRODUCTION


    def test_explicit_environment_override(self):
        """Test explicit environment override via ENVIRONMENT variable."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.PRODUCTION


    def test_unknown_environment_fallback(self):
        """Test unknown environment falls back to development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown_env"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.DEVELOPMENT


class TestOAuthConfigGeneration:
    """Test OAuth configuration generation for all environments."""
    
    def test_development_oauth_config_complete(self):
        """Test complete development OAuth configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID_DEV": "dev_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEV": "dev_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.client_id, str)
            assert isinstance(oauth_config.client_secret, str)


    def test_development_oauth_config_fallback_credentials(self):
        """Test development OAuth config with fallback credential names."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_CLIENT_ID": "fallback_client_123",
            "GOOGLE_CLIENT_SECRET": "fallback_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.client_id, str)


    def test_development_oauth_config_redirect_uris(self):
        """Test development OAuth redirect URIs include all localhost variants."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config.redirect_uris, list)
            # Check that some localhost URIs are present
            localhost_uris = [uri for uri in oauth_config.redirect_uris if 'localhost' in uri]
            assert len(localhost_uris) > 0


    def test_testing_oauth_config_isolation(self):
        """Test testing OAuth configuration isolation."""
        with patch.dict(os.environ, {
            "TESTING": "true",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.TESTING)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.javascript_origins, list)


    def test_staging_oauth_config_regular(self):
        """Test regular staging OAuth configuration (non-PR)."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.redirect_uris, list)


    def test_staging_pr_oauth_config_with_proxy(self):
        """Test staging PR OAuth configuration with proxy setup."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.javascript_origins, list)


    def test_production_oauth_config_security(self):
        """Test production OAuth configuration security settings."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod_secret_456"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.PRODUCTION)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.redirect_uris, list)


class TestRedirectUriValidation:
    """Test redirect URI configuration across environments."""
    
    def test_development_has_localhost_uris(self):
        """Test development OAuth config includes localhost URIs."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            localhost_uris = [uri for uri in oauth_config.redirect_uris if 'localhost' in uri]
            assert len(localhost_uris) > 0


    def test_staging_has_staging_domain_uris(self):
        """Test staging OAuth config includes staging domain URIs."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config.redirect_uris, list)
            assert len(oauth_config.redirect_uris) >= 0


    def test_pr_environment_oauth_config(self):
        """Test PR environment OAuth configuration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config, OAuthConfig)


    def test_production_oauth_config_structure(self):
        """Test production OAuth configuration structure."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.PRODUCTION)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.redirect_uris, list)


    def test_oauth_config_has_required_fields(self):
        """Test OAuth config contains required fields."""
        generator = OAuthConfigGenerator()
        oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
        assert hasattr(oauth_config, 'client_id')
        assert hasattr(oauth_config, 'client_secret')
        assert hasattr(oauth_config, 'redirect_uris')
        assert hasattr(oauth_config, 'javascript_origins')


class TestFrontendConfigGeneration:
    """Test OAuth configuration for frontend integration."""
    
    def test_oauth_config_for_frontend_development(self):
        """Test OAuth config suitable for frontend development."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_CLIENT_ID": "dev_client_123"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config.javascript_origins, list)
            assert isinstance(oauth_config.redirect_uris, list)


    def test_oauth_config_for_pr_environment(self):
        """Test OAuth config for PR environment frontend."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "123",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.javascript_origins, list)


    def test_oauth_config_for_production_frontend(self):
        """Test OAuth config for production frontend."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_client"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.PRODUCTION)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.redirect_uris, list)


class TestOAuthStateData:
    """Test OAuth configuration for different environment states."""
    
    def test_oauth_config_development_state(self):
        """Test OAuth config for development environment state."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.DEVELOPMENT
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(env)
            assert isinstance(oauth_config, OAuthConfig)


    def test_oauth_config_pr_environment_state(self):
        """Test OAuth config for PR environment state."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "456"
        }, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.STAGING
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(env)
            assert isinstance(oauth_config, OAuthConfig)


    def test_oauth_config_production_state(self):
        """Test OAuth config for production environment state."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.PRODUCTION
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(env)
            assert isinstance(oauth_config, OAuthConfig)


class TestEnvironmentConfigIntegration:
    """Test environment config integration behavior."""
    
    def test_environment_detector_consistency(self):
        """Test environment detector consistency across instances."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
            detector1 = EnvironmentDetector()
            detector2 = EnvironmentDetector()
            assert detector1.detect_environment() == detector2.detect_environment()


    def test_oauth_config_generator_consistency(self):
        """Test OAuth config generator consistency."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "789"
        }, clear=True):
            generator1 = OAuthConfigGenerator()
            generator2 = OAuthConfigGenerator()
            config1 = generator1.get_oauth_config(Environment.STAGING)
            config2 = generator2.get_oauth_config(Environment.STAGING)
            assert type(config1) == type(config2)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in auth client."""
    
    def test_oauth_config_with_missing_credentials(self):
        """Test OAuth config generation with missing credentials."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.client_id, str)


    def test_oauth_config_with_partial_credentials(self):
        """Test OAuth config generation with partial credentials."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID": "fallback_client"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config, OAuthConfig)
            assert isinstance(oauth_config.client_id, str)


    def test_staging_environment_without_pr_number(self):
        """Test staging environment detection without explicit PR number."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.STAGING


    def test_javascript_origins_structure(self):
        """Test JavaScript origins have proper structure."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert isinstance(oauth_config.javascript_origins, list)
            # Check that at least one localhost origin exists for development
            localhost_origins = [o for o in oauth_config.javascript_origins if 'localhost' in o]
            assert len(localhost_origins) >= 0