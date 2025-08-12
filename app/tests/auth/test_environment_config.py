"""Tests for environment-specific OAuth configuration."""

import os
import pytest
from unittest.mock import patch

from app.auth.environment_config import EnvironmentAuthConfig, Environment, OAuthConfig


class TestEnvironmentAuthConfig:
    """Test environment-specific auth configuration."""
    
    def test_development_environment_detection(self):
        """Test development environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.DEVELOPMENT
            assert not config.is_pr_environment
    
    def test_testing_environment_detection(self):
        """Test testing environment detection."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.TESTING
            assert not config.is_pr_environment
    
    def test_staging_pr_environment_detection(self):
        """Test staging PR environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "42"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment
            assert config.pr_number == "42"
    
    def test_production_environment_detection(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "ENVIRONMENT": "production"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION
            assert not config.is_pr_environment
    
    def test_development_oauth_config(self):
        """Test development OAuth configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID_DEV": "dev-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEV": "dev-secret"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            
            assert oauth_config.client_id == "dev-client-id"
            assert oauth_config.client_secret == "dev-secret"
            assert oauth_config.allow_dev_login
            assert oauth_config.allow_mock_auth
            assert not oauth_config.use_proxy
            assert "http://localhost:8000/api/auth/callback" in oauth_config.redirect_uris
    
    def test_staging_pr_oauth_config(self):
        """Test staging PR environment OAuth configuration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-secret"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            
            assert oauth_config.client_id == "staging-client-id"
            assert oauth_config.client_secret == "staging-secret"
            assert not oauth_config.allow_dev_login
            assert not oauth_config.allow_mock_auth
            assert oauth_config.use_proxy
            assert oauth_config.proxy_url == "https://auth.staging.netrasystems.ai"
            assert "https://auth.staging.netrasystems.ai/callback" in oauth_config.redirect_uris
    
    def test_production_oauth_config(self):
        """Test production OAuth configuration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "ENVIRONMENT": "production",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod-secret"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            
            assert oauth_config.client_id == "prod-client-id"
            assert oauth_config.client_secret == "prod-secret"
            assert not oauth_config.allow_dev_login
            assert not oauth_config.allow_mock_auth
            assert not oauth_config.use_proxy
            assert "https://api.netrasystems.ai/api/auth/callback" in oauth_config.redirect_uris
    
    def test_validate_redirect_uri(self):
        """Test redirect URI validation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            
            # Valid development URI
            assert config.validate_redirect_uri("http://localhost:8000/api/auth/callback")
            
            # Invalid URI
            assert not config.validate_redirect_uri("https://malicious.com/callback")
    
    def test_validate_redirect_uri_with_proxy(self):
        """Test redirect URI validation with proxy."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
        }, clear=True):
            config = EnvironmentAuthConfig()
            
            # Valid proxy URI
            assert config.validate_redirect_uri("https://auth.staging.netrasystems.ai/callback")
            
            # Invalid URI
            assert not config.validate_redirect_uri("https://pr-42.staging.netrasystems.ai/callback")
    
    def test_frontend_config(self):
        """Test frontend configuration generation."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id",
        }, clear=True):
            config = EnvironmentAuthConfig()
            frontend_config = config.get_frontend_config()
            
            assert frontend_config["environment"] == "staging"
            assert frontend_config["google_client_id"] == "staging-client-id"
            assert frontend_config["pr_number"] == "42"
            assert frontend_config["use_proxy"]
            assert frontend_config["proxy_url"] == "https://auth.staging.netrasystems.ai"
    
    def test_oauth_state_data(self):
        """Test OAuth state data generation."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42",
        }, clear=True):
            config = EnvironmentAuthConfig()
            state_data = config.get_oauth_state_data()
            
            assert state_data["environment"] == "staging"
            assert state_data["pr_number"] == "42"
            assert "timestamp" in state_data
            assert isinstance(state_data["timestamp"], int)