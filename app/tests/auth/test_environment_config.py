"""Tests for environment-specific OAuth configuration."""

import os
import pytest
from unittest.mock import patch

from app.clients.auth_client import Environment, OAuthConfig, EnvironmentDetector, OAuthConfigGenerator


class TestEnvironmentAuthConfig:
    """Test environment-specific auth configuration."""
    
    def test_development_environment_detection(self):
        """Test development environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.DEVELOPMENT
    
    def test_testing_environment_detection(self):
        """Test testing environment detection."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.TESTING
    
    def test_staging_pr_environment_detection(self):
        """Test staging PR environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "42"
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
    
    def test_production_environment_detection(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "ENVIRONMENT": "production"
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.PRODUCTION
    
    def test_development_oauth_config(self):
        """Test development OAuth configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID_DEV": "dev-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEV": "dev-secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            
            assert oauth_config.client_id == "dev-client-id"
            assert oauth_config.client_secret == "dev-secret"
    
    def test_staging_pr_oauth_config(self):
        """Test staging PR environment OAuth configuration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            
            assert oauth_config.client_id == "staging-client-id"
            assert oauth_config.client_secret == "staging-secret"
    
    def test_production_oauth_config(self):
        """Test production OAuth configuration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "ENVIRONMENT": "production",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod-secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.PRODUCTION)
            
            assert oauth_config.client_id == "prod-client-id"
            assert oauth_config.client_secret == "prod-secret"
    
    def test_validate_redirect_uri(self):
        """Test redirect URI validation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.DEVELOPMENT)
            
            # Valid development URI
            valid_uris = oauth_config.redirect_uris
            assert any("localhost" in uri for uri in valid_uris)
            
            # Test basic OAuth config structure
            assert isinstance(oauth_config.redirect_uris, list)
    
    def test_validate_redirect_uri_with_proxy(self):
        """Test redirect URI validation with proxy."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
        }, clear=True):
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            
            # Test OAuth config structure
            assert isinstance(oauth_config.redirect_uris, list)
            assert isinstance(oauth_config.javascript_origins, list)
    
    def test_frontend_config(self):
        """Test frontend configuration generation."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id",
        }, clear=True):
            generator = OAuthConfigGenerator()
            frontend_config = generator.get_frontend_config(Environment.STAGING)
            
            assert frontend_config["environment"] == "staging"
            assert frontend_config["google_client_id"] == "staging-client-id"
    
    def test_oauth_state_data(self):
        """Test OAuth state data generation."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
            
            # Test basic environment detection functionality
            generator = OAuthConfigGenerator()
            oauth_config = generator.get_oauth_config(Environment.STAGING)
            assert isinstance(oauth_config, OAuthConfig)