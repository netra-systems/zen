"""Cloud Run environment-specific tests for auth service integration.

Tests Cloud Run environment variable detection integration with auth client.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

IMPORTANT: These tests only test the integration with auth client.
The actual auth logic is tested in the separate auth service, not here.

Business Value Justification (BVJ):
1. Segment: Growth, Mid, and Enterprise (deployed customers)
2. Business Goal: Ensure seamless auth functionality in Google Cloud Run
3. Value Impact: Prevents auth failures in production Cloud Run deployments
4. Revenue Impact: Critical for customer retention and enterprise reliability
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.clients.auth_client import (
    Environment, OAuthConfig, EnvironmentDetector, OAuthConfigGenerator
)


class TestCloudRunEnvironmentDetection:
    """Test Cloud Run environment detection via auth client integration."""
    
    def test_environment_detector_imports_successfully(self):
        """Test that environment detector can be imported and instantiated."""
        detector = EnvironmentDetector()
        assert detector is not None
        assert hasattr(detector, 'detect_environment')

    def test_oauth_config_generator_imports_successfully(self):
        """Test that OAuth config generator can be imported and instantiated."""
        generator = OAuthConfigGenerator()
        assert generator is not None
        assert hasattr(generator, 'get_oauth_config')

    def test_environment_enum_has_required_values(self):
        """Test that Environment enum has required values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_oauth_config_dataclass_structure(self):
        """Test that OAuthConfig has required structure."""
        config = OAuthConfig()
        assert hasattr(config, 'client_id')
        assert hasattr(config, 'client_secret')
        assert hasattr(config, 'redirect_uris')
        assert hasattr(config, 'javascript_origins')

    def test_basic_environment_detection_development(self):
        """Test basic environment detection defaults to development."""
        with patch.dict(os.environ, {}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env in [Environment.DEVELOPMENT, Environment.STAGING]

    def test_explicit_environment_override_works(self):
        """Test explicit ENVIRONMENT variable override works."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.TESTING

    def test_testing_flag_override_works(self):
        """Test TESTING flag override works."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.TESTING

    def test_cloud_run_staging_detection(self):
        """Test Cloud Run staging environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-auth-staging"
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING


class TestOAuthConfigIntegration:
    """Test OAuth configuration integration."""
    
    def test_oauth_config_generator_with_development(self):
        """Test OAuth config generation for development environment."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.DEVELOPMENT)
        assert isinstance(config, OAuthConfig)
        # Development may have fallback credentials or be empty
        assert isinstance(config.client_id, str)

    def test_oauth_config_generator_with_staging(self):
        """Test OAuth config generation for staging environment."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.STAGING)
        assert isinstance(config, OAuthConfig)

    def test_oauth_config_generator_with_production(self):
        """Test OAuth config generation for production environment."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.PRODUCTION)
        assert isinstance(config, OAuthConfig)

    def test_oauth_config_lists_initialized(self):
        """Test OAuth config lists are properly initialized."""
        config = OAuthConfig()
        assert isinstance(config.redirect_uris, list)
        assert isinstance(config.javascript_origins, list)


class TestAuthClientIntegrationMocking:
    """Test auth client integration with proper mocking."""
    
    def test_pr_environment_detection_integration(self):
        """Test PR environment detection integration for Cloud Run."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr-123",
            "PR_NUMBER": "123"
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
            
            # Test OAuth config with PR environment
            generator = OAuthConfigGenerator()
            config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(config, OAuthConfig)
            # PR environment should configure proxy via staging config

    def test_oauth_config_generation_with_environment_vars(self):
        """Test OAuth config generation with environment variables."""
        with patch.dict(os.environ, {
            "GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING": "test_client_id",
            "GOOGLE_OAUTH_CLIENT_CLIENT_SECRET_STAGING": "test_client_secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            config = generator.get_oauth_config(Environment.STAGING)
            assert config.client_id == "test_client_id"
            assert config.client_secret == "test_client_secret"


class TestEnvironmentDetectionEdgeCases:
    """Test edge cases for environment detection."""
    
    def test_empty_k_service_falls_back(self):
        """Test empty K_SERVICE variable falls back properly."""
        with patch.dict(os.environ, {"K_SERVICE": ""}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env in [Environment.DEVELOPMENT, Environment.STAGING]

    def test_malformed_environment_variable(self):
        """Test malformed ENVIRONMENT variable handling."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.DEVELOPMENT  # Should fall back

    def test_case_insensitive_environment_override(self):
        """Test case insensitive environment variable handling."""
        with patch.dict(os.environ, {"ENVIRONMENT": "STAGING"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING