"""Cloud Run environment-specific tests for auth service.

Tests Cloud Run environment variable detection, service naming patterns,
PR environment routing, and Cloud Run deployment-specific behaviors.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: Growth, Mid, and Enterprise (deployed customers)
2. Business Goal: Ensure seamless auth functionality in Google Cloud Run
3. Value Impact: Prevents auth failures in production Cloud Run deployments
4. Revenue Impact: Critical for customer retention and enterprise reliability
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.auth.environment_config import (
    EnvironmentAuthConfig, Environment, OAuthConfig
)


class TestCloudRunEnvironmentDetection:
    """Test Cloud Run environment detection via K_SERVICE and K_REVISION."""
    
    def test_cloud_run_staging_via_k_service(self):
        """Test Cloud Run staging detection via K_SERVICE variable."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-auth-staging",
            "K_REVISION": "netra-auth-staging-00001-abc"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert not config.is_pr_environment


    def test_cloud_run_production_via_k_service(self):
        """Test Cloud Run production detection via K_SERVICE variable."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-auth-prod",
            "K_REVISION": "netra-auth-prod-00005-xyz"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION
            assert not config.is_pr_environment


    def test_cloud_run_staging_via_k_revision_only(self):
        """Test Cloud Run staging detection via K_REVISION only."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-staging-auth-00002-def"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING


    def test_cloud_run_production_via_k_revision_only(self):
        """Test Cloud Run production detection via K_REVISION only."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-backend-prod-00010-ghi"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


    def test_cloud_run_pr_environment_detection(self):
        """Test Cloud Run PR environment detection with staging service."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-auth-staging-pr-42",
            "PR_NUMBER": "42"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment
            assert config.pr_number == "42"


    def test_cloud_run_pr_environment_via_service_name_pattern(self):
        """Test PR environment detection via service name containing 'staging'."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-netra-auth",
            "PR_NUMBER": "123"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment


class TestCloudRunServiceNamingPatterns:
    """Test various Cloud Run service naming patterns recognition."""
    
    def test_service_name_with_staging_prefix(self):
        """Test service names with staging prefix recognition."""
        staging_services = [
            "staging-netra-auth",
            "staging-netra-backend", 
            "staging-auth-service"
        ]
        for service_name in staging_services:
            with patch.dict(os.environ, {"K_SERVICE": service_name}, clear=True):
                config = EnvironmentAuthConfig()
                assert config.environment == Environment.STAGING


    def test_service_name_with_staging_suffix(self):
        """Test service names with staging suffix recognition."""
        staging_services = [
            "netra-auth-staging",
            "netra-backend-staging",
            "auth-service-staging"
        ]
        for service_name in staging_services:
            with patch.dict(os.environ, {"K_SERVICE": service_name}, clear=True):
                config = EnvironmentAuthConfig()
                assert config.environment == Environment.STAGING


    def test_service_name_with_staging_infix(self):
        """Test service names with staging in middle recognition."""
        staging_services = [
            "netra-staging-auth",
            "backend-staging-service",
            "api-staging-gateway"
        ]
        for service_name in staging_services:
            with patch.dict(os.environ, {"K_SERVICE": service_name}, clear=True):
                config = EnvironmentAuthConfig()
                assert config.environment == Environment.STAGING


    def test_production_service_name_patterns(self):
        """Test production service name patterns (no staging keyword)."""
        production_services = [
            "netra-auth",
            "netra-backend",
            "netra-api-gateway",
            "auth-service-prod"
        ]
        for service_name in production_services:
            with patch.dict(os.environ, {"K_SERVICE": service_name}, clear=True):
                config = EnvironmentAuthConfig()
                assert config.environment == Environment.PRODUCTION


    def test_case_insensitive_staging_detection(self):
        """Test case-insensitive staging keyword detection."""
        staging_variations = [
            "netra-STAGING-auth",
            "STAGING-netra-backend",
            "netra-Staging-service"
        ]
        for service_name in staging_variations:
            with patch.dict(os.environ, {"K_SERVICE": service_name}, clear=True):
                config = EnvironmentAuthConfig()
                assert config.environment == Environment.STAGING


class TestCloudRunPREnvironmentRouting:
    """Test PR environment routing and proxy configuration in Cloud Run."""
    
    def test_pr_environment_proxy_configuration(self):
        """Test PR environment uses proxy configuration correctly."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr-456",
            "PR_NUMBER": "456"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.use_proxy is True
            assert oauth_config.proxy_url == "https://auth.staging.netrasystems.ai"


    def test_pr_environment_redirect_uris_proxy_only(self):
        """Test PR environment redirect URIs point to proxy."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-netra-auth",
            "PR_NUMBER": "789"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            proxy_callback = "https://auth.staging.netrasystems.ai/callback"
            assert proxy_callback in oauth_config.redirect_uris


    def test_pr_environment_javascript_origins_include_pr_domain(self):
        """Test PR environment JavaScript origins include PR-specific domain."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-service",
            "PR_NUMBER": "321"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            pr_origin = "https://pr-321.staging.netrasystems.ai"
            pr_api_origin = "https://pr-321-api.staging.netrasystems.ai"
            assert pr_origin in oauth_config.javascript_origins
            assert pr_api_origin in oauth_config.javascript_origins


    def test_pr_environment_frontend_config_pr_data(self):
        """Test PR environment frontend config includes PR-specific data."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-auth-pr",
            "PR_NUMBER": "654",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_client"
        }, clear=True):
            config = EnvironmentAuthConfig()
            frontend_config = config.get_frontend_config()
            assert frontend_config["pr_number"] == "654"
            assert frontend_config["use_proxy"] is True
            assert frontend_config["proxy_url"] == "https://auth.staging.netrasystems.ai"


class TestCloudRunEnvironmentOverrides:
    """Test environment variable overrides in Cloud Run context."""
    
    def test_explicit_environment_override_cloud_run_staging(self):
        """Test explicit environment override takes precedence in Cloud Run staging."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-service",
            "ENVIRONMENT": "production"  # Override staging detection
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


    def test_explicit_environment_override_cloud_run_production(self):
        """Test explicit environment override in Cloud Run production."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "ENVIRONMENT": "staging"  # Override production detection
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING


    def test_testing_flag_overrides_cloud_run(self):
        """Test TESTING flag overrides Cloud Run environment detection."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-service",
            "TESTING": "true"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.TESTING


    def test_cloud_run_without_pr_number_not_pr_env(self):
        """Test staging Cloud Run without PR_NUMBER is not PR environment."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-netra-auth"
            # No PR_NUMBER set
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment is False


class TestCloudRunOAuthConfiguration:
    """Test OAuth configuration specific to Cloud Run environments."""
    
    def test_cloud_run_staging_oauth_credentials(self):
        """Test Cloud Run staging uses staging OAuth credentials."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-auth",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_cr_client",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_cr_secret"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "staging_cr_client"
            assert oauth_config.client_secret == "staging_cr_secret"


    def test_cloud_run_production_oauth_credentials(self):
        """Test Cloud Run production uses production OAuth credentials."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend",
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_cr_client",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod_cr_secret"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.client_id == "prod_cr_client"
            assert oauth_config.client_secret == "prod_cr_secret"


    def test_cloud_run_staging_redirect_uris(self):
        """Test Cloud Run staging redirect URIs include staging domains."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging-service"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            expected_uris = [
                "https://staging.netrasystems.ai/api/auth/callback",
                "https://api.staging.netrasystems.ai/auth/callback"
            ]
            for uri in expected_uris:
                assert uri in oauth_config.redirect_uris


    def test_cloud_run_production_redirect_uris(self):
        """Test Cloud Run production redirect URIs include production domains."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            expected_uris = [
                "https://api.netrasystems.ai/api/auth/callback",
                "https://netrasystems.ai/auth/callback"
            ]
            for uri in expected_uris:
                assert uri in oauth_config.redirect_uris


class TestCloudRunRevisionHandling:
    """Test Cloud Run revision-specific behavior."""
    
    def test_revision_contains_staging_keyword(self):
        """Test revision names containing staging keyword detection."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-staging-auth-00123-abcdef"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING


    def test_revision_production_pattern(self):
        """Test production revision pattern recognition."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-backend-prod-00456-ghijkl"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


    def test_revision_with_pr_suffix(self):
        """Test revision with PR suffix indicates staging."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-auth-pr-789-00001-mnopqr",
            "PR_NUMBER": "789"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.STAGING
            assert config.is_pr_environment is True


    def test_ambiguous_revision_defaults_production(self):
        """Test ambiguous revision names default to production."""
        with patch.dict(os.environ, {
            "K_REVISION": "netra-auth-service-00999-xyz123"
        }, clear=True):
            config = EnvironmentAuthConfig()
            assert config.environment == Environment.PRODUCTION


class TestCloudRunSecuritySettings:
    """Test security settings specific to Cloud Run deployments."""
    
    def test_cloud_run_staging_security_settings(self):
        """Test Cloud Run staging has appropriate security settings."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging-auth"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.allow_dev_login is False
            assert oauth_config.allow_mock_auth is False


    def test_cloud_run_production_security_settings(self):
        """Test Cloud Run production has strict security settings."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend"}, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.allow_dev_login is False
            assert oauth_config.allow_mock_auth is False
            assert oauth_config.use_proxy is False


    def test_cloud_run_pr_security_with_proxy(self):
        """Test Cloud Run PR environment security with proxy."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-netra-pr",
            "PR_NUMBER": "111"
        }, clear=True):
            config = EnvironmentAuthConfig()
            oauth_config = config.get_oauth_config()
            assert oauth_config.allow_dev_login is False
            assert oauth_config.allow_mock_auth is False
            assert oauth_config.use_proxy is True


class TestCloudRunLoggingAndMonitoring:
    """Test logging and monitoring in Cloud Run environments."""
    
    def test_cloud_run_environment_logging(self):
        """Test Cloud Run environment detection includes proper logging."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-service",
            "PR_NUMBER": "999"
        }, clear=True), \
             patch('app.auth.environment_config.logger') as mock_logger:
            config = EnvironmentAuthConfig()
            config.get_oauth_config()  # Trigger logging
            
            # Should log environment detection and PR info
            assert any("staging" in str(call) for call in mock_logger.info.call_args_list)


    def test_cloud_run_production_logging(self):
        """Test Cloud Run production environment logging."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend"}, clear=True), \
             patch('app.auth.environment_config.logger') as mock_logger:
            config = EnvironmentAuthConfig()
            config.get_oauth_config()
            
            # Should log environment info
            mock_logger.info.assert_called()


class TestCloudRunEdgeCases:
    """Test edge cases specific to Cloud Run deployments."""
    
    def test_empty_k_service_variable(self):
        """Test empty K_SERVICE variable handling."""
        with patch.dict(os.environ, {"K_SERVICE": ""}, clear=True):
            config = EnvironmentAuthConfig()
            # Should fall back to development
            assert config.environment == Environment.DEVELOPMENT


    def test_k_service_and_k_revision_mismatch(self):
        """Test handling when K_SERVICE and K_REVISION suggest different environments."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-service",  # Suggests staging
            "K_REVISION": "netra-backend-prod-123"  # Suggests production
        }, clear=True):
            config = EnvironmentAuthConfig()
            # K_SERVICE should take precedence
            assert config.environment == Environment.STAGING


    def test_malformed_pr_number_handling(self):
        """Test handling of malformed PR_NUMBER in Cloud Run."""
        with patch.dict(os.environ, {
            "K_SERVICE": "staging-netra-auth",
            "PR_NUMBER": "not-a-number"
        }, clear=True):
            config = EnvironmentAuthConfig()
            # Should still detect staging but handle PR number gracefully
            assert config.environment == Environment.STAGING
            assert config.pr_number == "not-a-number"  # Store as-is