"""Auth client integration tests for unit testing.

Tests the integration with the external auth service via auth client.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

IMPORTANT: These tests only test the integration with auth client.
The actual auth logic is tested in the separate auth service, not here.

Business Value Justification (BVJ):
1. Segment: Growth, Mid, and Enterprise
2. Business Goal: Ensure reliable auth client integration
3. Value Impact: Prevents auth failures in production
4. Revenue Impact: Critical for customer retention
"""

from unittest.mock import AsyncMock, MagicMock, patch
import os
import pytest
from app.clients.auth_client import (
    Environment, OAuthConfig, EnvironmentDetector, OAuthConfigGenerator,
    auth_client, AuthServiceClient
)


class TestAuthClientIntegration:
    """Test auth client integration functionality."""
    
    def test_environment_detector_instantiation(self):
        """Test environment detector can be instantiated."""
        detector = EnvironmentDetector()
        assert detector is not None
        assert hasattr(detector, 'detect_environment')
            
    def test_oauth_config_generator_instantiation(self):
        """Test OAuth config generator can be instantiated."""
        generator = OAuthConfigGenerator()
        assert generator is not None
        assert hasattr(generator, 'get_oauth_config')
                
    def test_environment_enum_values(self):
        """Test Environment enum has required values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
            
    def test_oauth_config_dataclass_structure(self):
        """Test OAuthConfig has required structure."""
        config = OAuthConfig()
        assert hasattr(config, 'client_id')
        assert hasattr(config, 'client_secret')
        assert hasattr(config, 'redirect_uris')
        assert hasattr(config, 'javascript_origins')
            
    def test_development_environment_detection(self):
        """Test development environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.DEVELOPMENT
            
    def test_staging_environment_detection(self):
        """Test staging environment detection."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-staging"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
                
    def test_production_environment_detection(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.PRODUCTION
            
    def test_oauth_config_generation_development(self):
        """Test OAuth config generation for development."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.DEVELOPMENT)
        assert isinstance(config, OAuthConfig)
        assert isinstance(config.client_id, str)
            
    def test_oauth_config_generation_staging(self):
        """Test OAuth config generation for staging."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.STAGING)
        assert isinstance(config, OAuthConfig)
        assert isinstance(config.client_secret, str)
            
    def test_oauth_config_generation_production(self):
        """Test OAuth config generation for production."""
        generator = OAuthConfigGenerator()
        config = generator.get_oauth_config(Environment.PRODUCTION)
        assert isinstance(config, OAuthConfig)
        assert isinstance(config.redirect_uris, list)
            
    def test_frontend_config_development(self):
        """Test frontend config generation for development."""
        generator = OAuthConfigGenerator()
        config = generator.get_frontend_config(Environment.DEVELOPMENT)
        assert isinstance(config, dict)
        assert "environment" in config
            
    def test_frontend_config_staging(self):
        """Test frontend config generation for staging."""
        generator = OAuthConfigGenerator()
        config = generator.get_frontend_config(Environment.STAGING)
        assert isinstance(config, dict)
        assert config["environment"] == "staging"
                
    def test_frontend_config_production(self):
        """Test frontend config generation for production."""
        generator = OAuthConfigGenerator()
        config = generator.get_frontend_config(Environment.PRODUCTION)
        assert isinstance(config, dict)
        assert config["environment"] == "production"
            
    @pytest.mark.asyncio
    async def test_auth_client_instance_exists(self):
        """Test auth client instance is available."""
        assert auth_client is not None
        assert isinstance(auth_client, AuthServiceClient)
                
    @pytest.mark.asyncio
    async def test_auth_client_methods_exist(self):
        """Test auth client has expected methods."""
        assert hasattr(auth_client, 'validate_token')
        assert hasattr(auth_client, 'create_user')
        assert hasattr(auth_client, 'authenticate_user')
            
    def test_oauth_config_lists_initialized(self):
        """Test OAuth config lists are properly initialized."""
        config = OAuthConfig()
        assert isinstance(config.redirect_uris, list)
        assert isinstance(config.javascript_origins, list)
            
    def test_environment_detection_with_empty_env(self):
        """Test environment detection with empty environment."""
        with patch.dict(os.environ, {}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env in [Environment.DEVELOPMENT, Environment.STAGING]
            
    def test_environment_detection_with_testing_flag(self):
        """Test environment detection with TESTING flag."""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.TESTING
        
    def test_oauth_config_with_environment_vars(self):
        """Test OAuth config with environment variables."""
        with patch.dict(os.environ, {
            "GOOGLE_OAUTH_CLIENT_ID_DEV": "test_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEV": "test_secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            config = generator.get_oauth_config(Environment.DEVELOPMENT)
            assert config.client_id == "test_client_id"
        
    def test_pr_environment_detection_integration(self):
        """Test PR environment detection integration."""
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-staging-pr-123",
            "PR_NUMBER": "123"
        }, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
            
    def test_case_insensitive_environment_handling(self):
        """Test case insensitive environment variable handling."""
        with patch.dict(os.environ, {"ENVIRONMENT": "STAGING"}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect_environment() == Environment.STAGING
            
    def test_malformed_environment_variable_fallback(self):
        """Test malformed environment variable handling."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env == Environment.DEVELOPMENT  # Should fall back
        
    def test_empty_k_service_fallback(self):
        """Test empty K_SERVICE variable falls back properly."""
        with patch.dict(os.environ, {"K_SERVICE": ""}, clear=True):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env in [Environment.DEVELOPMENT, Environment.STAGING]
            
    def test_oauth_config_structure_validation(self):
        """Test OAuth config structure validation."""
        generator = OAuthConfigGenerator()
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
            config = generator.get_oauth_config(env)
            assert hasattr(config, 'client_id')
            assert hasattr(config, 'client_secret')
            assert hasattr(config, 'redirect_uris')
            assert hasattr(config, 'javascript_origins')
            
    def test_frontend_config_structure_validation(self):
        """Test frontend config structure validation."""
        generator = OAuthConfigGenerator()
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
            config = generator.get_frontend_config(env)
            assert isinstance(config, dict)
            assert "environment" in config
            
    @pytest.mark.asyncio
    async def test_auth_client_mock_validation(self):
        """Test auth client can be mocked for testing."""
        with patch.object(auth_client, 'validate_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"valid": True, "user_id": "test123"}
            result = await auth_client.validate_token("test_token")
            assert result["valid"] is True
            
    def test_oauth_config_with_staging_credentials(self):
        """Test OAuth config with staging credentials."""
        with patch.dict(os.environ, {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging_secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            config = generator.get_oauth_config(Environment.STAGING)
            assert config.client_id == "staging_id"
            
    def test_oauth_config_with_production_credentials(self):
        """Test OAuth config with production credentials."""
        with patch.dict(os.environ, {
            "GOOGLE_OAUTH_CLIENT_ID_PROD": "prod_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_PROD": "prod_secret"
        }, clear=True):
            generator = OAuthConfigGenerator()
            config = generator.get_oauth_config(Environment.PRODUCTION)
            assert config.client_id == "prod_id"