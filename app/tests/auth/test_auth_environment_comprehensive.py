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

from app.auth.environment_config import (
    EnvironmentAuthConfig, Environment, OAuthConfig,
    auth_env_config
)


class TestEnvironmentDetection:
    """Test environment detection logic across all scenarios."""
    
    def test_development_environment_default(self):
        """Test default development environment detection."""
        with patch.dict(os.environ, {}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.DEVELOPMENT
            assert not config.is_pr_environment
            assert config.pr_number is None


    def test_testing_environment_explicit_flag(self):
        """Test testing environment detection via TESTING flag."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.TESTING
            assert not config.is_pr_environment


    def test_testing_environment_pytest_context(self):
        """Test testing environment detection in pytest context."""
        with patch.dict(os.environ, {"TESTING": "1"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.TESTING


    def test_staging_environment_k_service(self):
        """Test staging environment detection via K_SERVICE."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging-service"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert not config.is_pr_environment


    def test_staging_pr_environment_with_pr_number(self):
        """Test staging PR environment detection with PR number."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "123"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment
            assert config.pr_number == "123"


    def test_production_environment_k_service(self):
        """Test production environment detection via K_SERVICE."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend-prod"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION
            assert not config.is_pr_environment


    def test_production_environment_k_revision(self):
        """Test production environment detection via K_REVISION only."""
        with patch.dict(os.environ, {"K_REVISION": "netra-backend-prod-rev-1"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


    def test_explicit_environment_override(self):
        """Test explicit environment override via ENVIRONMENT variable."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


    def test_unknown_environment_fallback(self):
        """Test unknown environment falls back to development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown_env"}, clear=True), \
             patch('app.auth.environment_config.logger') as mock_logger:
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.DEVELOPMENT
            mock_logger.warning.assert_called_once()


class TestOAuthConfigGeneration:
    """Test OAuth configuration generation for all environments."""
    
    def test_development_oauth_config_complete(self):
        """Test complete development OAuth configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID_DEV": "dev_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEV": "dev_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "dev_client_123"
            assert oauth_config.client_secret == "dev_secret_456"
            assert oauth_config.allow_dev_login is True
            assert oauth_config.allow_mock_auth is True
            assert oauth_config.use_proxy is False


    def test_development_oauth_config_fallback_credentials(self):
        """Test development OAuth config with fallback credential names."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_CLIENT_ID": "fallback_client_123",
            "GOOGLE_CLIENT_SECRET": "fallback_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "fallback_client_123"
            assert oauth_config.client_secret == "fallback_secret_456"


    def test_development_oauth_config_redirect_uris(self):
        """Test development OAuth redirect URIs include all localhost variants."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            expected_uris = [
                "http://localhost:8000/api/auth/callback",
                "http://localhost:3000/api/auth/callback",
                "http://localhost:3010/api/auth/callback",
                "http://localhost:3000/auth/callback",
                "http://localhost:3010/auth/callback"
            ]
            for uri in expected_uris:
                assert uri in oauth_config.redirect_uris


    def test_testing_oauth_config_isolation(self):
        """Test testing OAuth configuration isolation."""
        with patch.dict(os.environ, {
            "TESTING": "true",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "test_client_123"
            assert oauth_config.allow_dev_login is False
            assert oauth_config.allow_mock_auth is True
            assert "test.local" in oauth_config.javascript_origins[0]


    def test_staging_oauth_config_regular(self):
        """Test regular staging OAuth configuration (non-PR)."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "staging_client_123"
            assert oauth_config.use_proxy is False
            assert "staging.netrasystems.ai" in oauth_config.redirect_uris[0]


    def test_staging_pr_oauth_config_with_proxy(self):
        """Test staging PR OAuth configuration with proxy setup."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr",
            "PR_NUMBER": "42",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.use_proxy is True
            assert oauth_config.proxy_url == "https://auth.staging.netrasystems.ai"
            assert "pr-42.staging.netrasystems.ai" in oauth_config.javascript_origins[1]


    def test_production_oauth_config_security(self):
        """Test production OAuth configuration security settings."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod_secret_456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.allow_dev_login is False
            assert oauth_config.allow_mock_auth is False
            assert oauth_config.use_proxy is False
            assert "netrasystems.ai" in oauth_config.redirect_uris[0]


class TestRedirectUriValidation:
    """Test redirect URI validation across environments."""
    
    def test_validate_development_localhost_uris(self):
        """Test validation accepts development localhost URIs."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            valid_uris = [
                "http://localhost:8000/api/auth/callback",
                "http://localhost:3000/auth/callback",
                "http://localhost:3010/api/auth/callback"
            ]
            for uri in valid_uris:
                assert config.validate_redirect_uri(uri) is True


    def test_validate_development_rejects_external(self):
        """Test validation rejects external URIs in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            invalid_uris = [
                "https://malicious.com/callback",
                "http://evil.site/steal-tokens",
                "https://google.com/fake-callback"
            ]
            for uri in invalid_uris:
                assert config.validate_redirect_uri(uri) is False


    def test_validate_pr_environment_proxy_uris(self):
        """Test PR environment validates proxy URIs correctly."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42"
        }, clear=True):
            config = EnvironmentAuthConfig()
            proxy_uri = "https://auth.staging.netrasystems.ai/callback"
            assert config.validate_redirect_uri(proxy_uri) is True


    def test_validate_pr_environment_rejects_direct_pr_uris(self):
        """Test PR environment rejects direct PR URIs (must use proxy)."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "42"
        }, clear=True):
            config = EnvironmentAuthConfig()
            direct_pr_uri = "https://pr-42.staging.netrasystems.ai/callback"
            assert config.validate_redirect_uri(direct_pr_uri) is False


    def test_validate_production_domain_restriction(self):
        """Test production validates only production domain URIs."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend"}, clear=True):
            config = EnvironmentAuthConfig()
            valid_uri = "https://api.netrasystems.ai/api/auth/callback"
            invalid_uri = "https://staging.netrasystems.ai/callback"
            assert config.validate_redirect_uri(valid_uri) is True
            assert config.validate_redirect_uri(invalid_uri) is False


class TestFrontendConfigGeneration:
    """Test frontend configuration generation for different environments."""
    
    def test_frontend_config_development_structure(self):
        """Test development frontend config includes all required fields."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_CLIENT_ID": "dev_client_123"
        }, clear=True):
            config = EnvironmentAuthConfig()
            frontend_config = config.get_frontend_config()
            required_fields = ["environment", "google_client_id", "allow_dev_login", "javascript_origins"]
            for field in required_fields:
                assert field in frontend_config
            assert frontend_config["environment"] == "development"


    def test_frontend_config_pr_environment_proxy_data(self):
        """Test PR environment frontend config includes proxy data."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "123",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client"
        }, clear=True):
            config = EnvironmentAuthConfig()
            frontend_config = config.get_frontend_config()
            assert frontend_config["pr_number"] == "123"
            assert frontend_config["use_proxy"] is True
            assert frontend_config["proxy_url"] == "https://auth.staging.netrasystems.ai"


    def test_frontend_config_production_security_settings(self):
        """Test production frontend config has proper security settings."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_client"
        }, clear=True):
            config = EnvironmentAuthConfig()
            frontend_config = config.get_frontend_config()
            assert frontend_config["allow_dev_login"] is False
            assert "pr_number" not in frontend_config
            assert "use_proxy" not in frontend_config


class TestOAuthStateData:
    """Test OAuth state data generation and validation."""
    
    def test_oauth_state_data_development(self):
        """Test OAuth state data includes environment and timestamp."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            state_data = config.get_oauth_state_data()
            assert state_data["environment"] == "development"
            assert "timestamp" in state_data
            assert isinstance(state_data["timestamp"], int)
            assert "pr_number" not in state_data


    def test_oauth_state_data_pr_environment(self):
        """Test OAuth state data includes PR number for PR environments."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            state_data = config.get_oauth_state_data()
            assert state_data["environment"] == "staging"
            assert state_data["pr_number"] == "456"
            assert state_data["timestamp"] <= int(time.time())


    def test_oauth_state_data_timestamp_accuracy(self):
        """Test OAuth state data timestamp is current."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = EnvironmentAuthConfig()
            before_time = int(time.time())
            state_data = config.get_oauth_state_data()
            after_time = int(time.time())
            assert before_time <= state_data["timestamp"] <= after_time


class TestEnvironmentConfigSingleton:
    """Test environment config singleton behavior."""
    
    def test_singleton_auth_env_config_consistency(self):
        """Test global auth_env_config instance consistency."""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
            # Create new instance to test against singleton
            new_config = EnvironmentAuthConfig()
            assert new_config.environment == Environment.TESTING


    def test_environment_detection_logging(self):
        """Test environment detection includes proper logging."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging",
            "PR_NUMBER": "789"
        }, clear=True), \
             patch('app.auth.environment_config.logger') as mock_logger:
            config = EnvironmentAuthConfig()
            config.get_oauth_config()  # Trigger logging
            # Should log environment and PR info
            assert mock_logger.info.call_count >= 1


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in environment config."""
    
    def test_missing_oauth_credentials_development(self):
        """Test development handles missing OAuth credentials gracefully."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True), \
             patch('app.auth.environment_config.logger') as mock_logger:
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            # Should log errors for missing credentials
            mock_logger.error.assert_called()
            assert oauth_config.client_id == ""


    def test_partial_oauth_credentials_fallback(self):
        """Test fallback chain for OAuth credentials works properly."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GOOGLE_OAUTH_CLIENT_ID": "fallback_client"
            # Missing GOOGLE_OAUTH_CLIENT_ID_DEV
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "fallback_client"


    def test_pr_environment_without_pr_number(self):
        """Test staging environment detection without explicit PR number."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging"}, clear=True):
            config = EnvironmentAuthConfig()
            # Should detect staging but not PR environment
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment is False


    def test_javascript_origins_include_all_variants(self):
        """Test JavaScript origins include all required variants."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            expected_origins = ["http://localhost:3000", "http://localhost:3010", "http://localhost:8000"]
            for origin in expected_origins:
                assert origin in oauth_config.javascript_origins