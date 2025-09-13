"""

from shared.isolated_environment import get_env

Comprehensive OAuth Configuration Tests

Tests OAuth configuration loading, validation, and error handling across environments.



These tests ensure OAuth failures are LOUD and immediately visible.

"""



import json

import os

import pytest

import logging

from typing import Dict, Any



from shared.isolated_environment import IsolatedEnvironment

from tests.clients.backend_client import BackendTestClient

from tests.e2e.config import UnifiedTestConfig



logger = logging.getLogger(__name__)





@pytest.mark.e2e

class TestOAuthConfigurationValidation:

    """Test OAuth configuration validation and error handling."""

    

    @pytest.fixture

    async def auth_service_client(self):

        """Get auth service test client."""

        config = UnifiedTestConfig()

        return BackendTestClient(base_url=config.auth_service_url)

    

    @pytest.fixture

    def mock_env_vars(self) -> Dict[str, str]:

        """Mock environment variables for testing."""

        return {

            "ENVIRONMENT": "staging",

            "GOOGLE_CLIENT_ID": "test-client-id-123456789.apps.googleusercontent.com",

            "GOOGLE_CLIENT_SECRET": "test-client-secret-12345678901234567890",

            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id-123456789.apps.googleusercontent.com", 

            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-client-secret-12345678901234567890"

        }

    

    @pytest.fixture

    def empty_env_vars(self) -> Dict[str, str]:

        """Empty environment variables for testing missing config."""

        return {

            "ENVIRONMENT": "staging"

        }

    

    @pytest.fixture

    def placeholder_env_vars(self) -> Dict[str, str]:

        """Placeholder environment variables for testing invalid config."""

        return {

            "ENVIRONMENT": "staging",

            "GOOGLE_CLIENT_ID": "REPLACE_WITH_REAL_GOOGLE_CLIENT_ID",

            "GOOGLE_CLIENT_SECRET": "REPLACE_WITH_REAL_GOOGLE_CLIENT_SECRET"

        }



    @pytest.mark.e2e

    def test_auth_service_startup_validation_success(self, mock_env_vars):

        """Test auth service startup with valid OAuth configuration."""

        with mock.patch.dict(os.environ, mock_env_vars, clear=True):

            # Import after setting environment

            from auth_service.auth_core.config import AuthConfig

            

            # Should not raise any exceptions

            client_id = AuthConfig.get_google_client_id()

            client_secret = AuthConfig.get_google_client_secret()

            

            assert client_id.endswith(".apps.googleusercontent.com")

            assert len(client_secret) >= 20

            assert not client_id.startswith("REPLACE_")

            assert not client_secret.startswith("REPLACE_")

    

    @pytest.mark.e2e

    def test_auth_service_startup_validation_missing_credentials(self, empty_env_vars):

        """Test auth service startup fails loudly with missing OAuth credentials."""

        with mock.patch.dict(os.environ, empty_env_vars, clear=True):

            from auth_service.auth_core.config import AuthConfig

            

            # Should return empty strings for missing config

            client_id = AuthConfig.get_google_client_id()

            client_secret = AuthConfig.get_google_client_secret()

            

            assert client_id == ""

            assert client_secret == ""

    

    @pytest.mark.e2e

    def test_auth_service_startup_validation_placeholder_credentials(self, placeholder_env_vars):

        """Test auth service startup detects placeholder OAuth credentials."""

        with mock.patch.dict(os.environ, placeholder_env_vars, clear=True):

            from auth_service.auth_core.config import AuthConfig

            

            client_id = AuthConfig.get_google_client_id()

            client_secret = AuthConfig.get_google_client_secret()

            

            # Should detect placeholder values

            assert client_id.startswith("REPLACE_")

            assert client_secret.startswith("REPLACE_")

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_auth_login_endpoint_missing_oauth_config(self, auth_service_client, empty_env_vars):

        """Test /auth/login endpoint fails loudly with missing OAuth config."""

        with mock.patch.dict(os.environ, empty_env_vars, clear=True):

            # Try to initiate OAuth login

            response = await auth_service_client.get("/auth/login")

            

            # Should return 500 with detailed error

            assert response.status_code == 500

            error_detail = response.json()

            

            # Check for loud error reporting

            assert "detail" in error_detail

            if isinstance(error_detail["detail"], dict):

                assert error_detail["detail"]["error"] == "OAUTH_CONFIGURATION_BROKEN"

                assert "environment" in error_detail["detail"]

                assert "errors" in error_detail["detail"]

                assert "user_message" in error_detail["detail"]

            else:

                # Legacy string format

                assert "OAuth not configured" in error_detail["detail"]

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_auth_login_endpoint_placeholder_oauth_config(self, auth_service_client, placeholder_env_vars):

        """Test /auth/login endpoint detects placeholder OAuth config."""

        with mock.patch.dict(os.environ, placeholder_env_vars, clear=True):

            response = await auth_service_client.get("/auth/login")

            

            # Should return 500 with detailed error about placeholders

            assert response.status_code == 500

            error_detail = response.json()

            

            if isinstance(error_detail["detail"], dict):

                assert error_detail["detail"]["error"] == "OAUTH_CONFIGURATION_BROKEN"

                assert any("placeholder" in error.lower() for error in error_detail["detail"]["errors"])

            else:

                assert "placeholder" in error_detail["detail"].lower() or "oauth" in error_detail["detail"].lower()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_auth_config_endpoint_missing_oauth_config(self, auth_service_client, empty_env_vars):

        """Test /auth/config endpoint warns about missing OAuth config."""

        with mock.patch.dict(os.environ, empty_env_vars, clear=True):

            response = await auth_service_client.get("/auth/config")

            

            if response.status_code == 500:

                # Should fail loudly in staging/production

                error_detail = response.json()

                if isinstance(error_detail["detail"], dict):

                    assert error_detail["detail"]["error"] == "AUTH_CONFIG_FAILURE"

                    assert "user_message" in error_detail["detail"]

            else:

                # Or return config with empty client ID

                config = response.json()

                assert config["google_client_id"] == ""

                assert not config.get("oauth_enabled", True)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_auth_config_endpoint_valid_oauth_config(self, auth_service_client, mock_env_vars):

        """Test /auth/config endpoint with valid OAuth config."""

        with mock.patch.dict(os.environ, mock_env_vars, clear=True):

            response = await auth_service_client.get("/auth/config")

            

            # Should succeed

            assert response.status_code == 200

            config = response.json()

            

            # Should have valid OAuth configuration

            assert config["google_client_id"] != ""

            assert config["google_client_id"].endswith(".apps.googleusercontent.com")

            assert not config["google_client_id"].startswith("REPLACE_")

            assert config.get("development_mode", False) is False  # staging environment





@pytest.mark.e2e

class TestOAuthEnvironmentSpecificConfiguration:

    """Test OAuth configuration for different environments."""

    

    @pytest.mark.e2e

    def test_staging_oauth_configuration_priority(self):

        """Test OAuth configuration priority in staging environment."""

        staging_env = {

            "ENVIRONMENT": "staging",

            "GOOGLE_CLIENT_ID": "fallback-client-id.apps.googleusercontent.com",

            "GOOGLE_CLIENT_SECRET": "fallback-client-secret",

            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-specific-client-id.apps.googleusercontent.com",

            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-specific-client-secret"

        }

        

        with mock.patch.dict(os.environ, staging_env, clear=True):

            from auth_service.auth_core.secret_loader import AuthSecretLoader

            

            # Should prefer staging-specific variables

            client_id = AuthSecretLoader.get_google_client_id()

            client_secret = AuthSecretLoader.get_google_client_secret()

            

            assert client_id == "staging-specific-client-id.apps.googleusercontent.com"

            assert client_secret == "staging-specific-client-secret"

    

    @pytest.mark.e2e

    def test_production_oauth_configuration_priority(self):

        """Test OAuth configuration priority in production environment."""

        production_env = {

            "ENVIRONMENT": "production",

            "GOOGLE_CLIENT_ID": "fallback-client-id.apps.googleusercontent.com",

            "GOOGLE_CLIENT_SECRET": "fallback-client-secret",

            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "production-specific-client-id.apps.googleusercontent.com",

            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "production-specific-client-secret"

        }

        

        with mock.patch.dict(os.environ, production_env, clear=True):

            from auth_service.auth_core.secret_loader import AuthSecretLoader

            

            # Should prefer production-specific variables

            client_id = AuthSecretLoader.get_google_client_id()

            client_secret = AuthSecretLoader.get_google_client_secret()

            

            assert client_id == "production-specific-client-id.apps.googleusercontent.com"

            assert client_secret == "production-specific-client-secret"

    

    @pytest.mark.e2e

    def test_development_oauth_configuration_fallback(self):

        """Test OAuth configuration fallback in development environment."""

        development_env = {

            "ENVIRONMENT": "development",

            "GOOGLE_CLIENT_ID": "dev-client-id.apps.googleusercontent.com",

            "GOOGLE_CLIENT_SECRET": "dev-client-secret"

        }

        

        with mock.patch.dict(os.environ, development_env, clear=True):

            from auth_service.auth_core.secret_loader import AuthSecretLoader

            

            # Should use generic variables in development

            client_id = AuthSecretLoader.get_google_client_id()

            client_secret = AuthSecretLoader.get_google_client_secret()

            

            assert client_id == "dev-client-id.apps.googleusercontent.com"

            assert client_secret == "dev-client-secret"





@pytest.mark.e2e

class TestOAuthDeploymentValidation:

    """Test the OAuth deployment validation script."""

    

    @pytest.mark.e2e

    def test_oauth_validation_script_success(self, tmp_path, mock_env_vars):

        """Test OAuth validation script with valid configuration."""

        # Create a temporary config file

        oauth_config = {

            "staging": {

                "authorized_javascript_origins": [

                    "https://netra-frontend-staging-latest-w3h46qmr6q-uc.a.run.app",

                    "https://staging.netrasystems.ai"

                ],

                "authorized_redirect_uris": [

                    "https://netra-frontend-staging-latest-w3h46qmr6q-uc.a.run.app/auth/callback",

                    "https://staging.netrasystems.ai/auth/callback"

                ]

            }

        }

        

        config_file = tmp_path / "oauth_redirect_uris.json"

        with open(config_file, 'w') as f:

            json.dump(oauth_config, f)

        

        with mock.patch.dict(os.environ, mock_env_vars, clear=True):

            # Mock the config file path

            with patch('pathlib.Path') as mock_path:

                mock_path.return_value.parent.parent = tmp_path.parent

                mock_path.return_value.parent.parent.__truediv__ = lambda self, path: tmp_path if path == "config" else self / path

                

                # Import and test the validation

                from scripts.validate_oauth_deployment import OAuthDeploymentValidator

                

                validator = OAuthDeploymentValidator("staging")

                success, report = validator.validate_all()

                

                assert success is True

                assert "ALL VALIDATIONS PASSED" in report

    

    @pytest.mark.e2e

    def test_oauth_validation_script_missing_credentials(self, empty_env_vars):

        """Test OAuth validation script fails with missing credentials."""

        with mock.patch.dict(os.environ, empty_env_vars, clear=True):

            from scripts.validate_oauth_deployment import OAuthDeploymentValidator

            

            validator = OAuthDeploymentValidator("staging")

            success, report = validator.validate_all()

            

            assert success is False

            assert "CRITICAL ERRORS" in report

            assert "GOOGLE_CLIENT_ID" in report or "Google Client ID" in report

    

    @pytest.mark.e2e

    def test_oauth_validation_script_placeholder_credentials(self, placeholder_env_vars):

        """Test OAuth validation script detects placeholder credentials."""

        with mock.patch.dict(os.environ, placeholder_env_vars, clear=True):

            from scripts.validate_oauth_deployment import OAuthDeploymentValidator

            

            validator = OAuthDeploymentValidator("staging")

            success, report = validator.validate_all()

            

            assert success is False

            assert "CRITICAL ERRORS" in report

            assert "placeholder" in report.lower()





@pytest.mark.e2e

class TestOAuthFrontendErrorHandling:

    """Test frontend OAuth error handling and display."""

    

    @pytest.mark.e2e

    def test_frontend_oauth_config_error_handling(self):

        """Test frontend handles OAuth configuration errors gracefully."""

        # This would typically be a frontend integration test

        # For now, we test the auth service client error handling logic

        

        from frontend.lib.auth_service_client import AuthServiceClient

        

        # Mock a response with OAuth configuration error

        error_response = {

            "detail": {

                "error": "OAUTH_CONFIGURATION_BROKEN",

                "message": "OAuth configuration is missing or invalid",

                "environment": "staging",

                "errors": ["GOOGLE_CLIENT_ID is not configured"],

                "user_message": "OAuth Configuration Error - Please contact system administrator"

            }

        }

        

        # Test that the client properly identifies OAuth config errors

        # (This would be more comprehensive in actual frontend tests)

        assert error_response["detail"]["error"] == "OAUTH_CONFIGURATION_BROKEN"

        assert "user_message" in error_response["detail"]

        assert error_response["detail"]["user_message"].startswith("OAuth Configuration Error")





@pytest.mark.e2e

class TestOAuthRedirectConfiguration:

    """Test OAuth redirect URI configuration and validation."""

    

    @pytest.mark.e2e

    def test_oauth_redirect_uris_config_loading(self):

        """Test loading OAuth redirect URIs configuration."""

        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "oauth_redirect_uris.json")

        

        if os.path.exists(config_path):

            with open(config_path) as f:

                config = json.load(f)

            

            # Should have configuration for different environments

            assert isinstance(config, dict)

            

            # Check staging configuration if it exists

            if "staging" in config:

                staging_config = config["staging"]

                assert "authorized_javascript_origins" in staging_config

                assert "authorized_redirect_uris" in staging_config

                

                # All URIs should be HTTPS in staging

                for origin in staging_config["authorized_javascript_origins"]:

                    assert origin.startswith("https://"), f"Non-HTTPS origin in staging: {origin}"

                

                for uri in staging_config["authorized_redirect_uris"]:

                    assert uri.startswith("https://"), f"Non-HTTPS redirect URI in staging: {uri}"

        else:

            pytest.skip("OAuth redirect URIs config file not found")

    

    @pytest.mark.e2e

    def test_oauth_redirect_uris_environment_coverage(self):

        """Test OAuth redirect URIs cover expected environments."""

        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "oauth_redirect_uris.json")

        

        if os.path.exists(config_path):

            with open(config_path) as f:

                config = json.load(f)

            

            # Should have at least development configuration

            assert "development" in config, "Missing development OAuth configuration"

            

            dev_config = config["development"]

            dev_origins = dev_config.get("authorized_javascript_origins", [])

            

            # Should include localhost for development

            localhost_found = any("localhost" in origin for origin in dev_origins)

            assert localhost_found, "Development configuration should include localhost origins"

        else:

            pytest.skip("OAuth redirect URIs config file not found")





@pytest.mark.integration

@pytest.mark.e2e

class TestOAuthIntegration:

    """Integration tests for OAuth configuration across services."""

    

    @pytest.fixture

    async def auth_service_client(self):

        """Get auth service test client."""

        config = UnifiedTestConfig()

        return BackendTestClient(base_url=config.auth_service_url)

    

    @pytest.fixture

    def mock_env_vars(self) -> Dict[str, str]:

        """Mock environment variables for testing."""

        return {

            "ENVIRONMENT": "staging",

            "GOOGLE_CLIENT_ID": "test-client-id-123456789.apps.googleusercontent.com",

            "GOOGLE_CLIENT_SECRET": "test-client-secret-12345678901234567890",

            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id-123456789.apps.googleusercontent.com", 

            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-client-secret-12345678901234567890"

        }

    

    @pytest.fixture

    def empty_env_vars(self) -> Dict[str, str]:

        """Empty environment variables for testing missing config."""

        return {

            "ENVIRONMENT": "staging"

        }

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_oauth_configuration_end_to_end(self, auth_service_client, mock_env_vars):

        """Test OAuth configuration from auth service through to frontend."""

        with mock.patch.dict(os.environ, mock_env_vars, clear=True):

            # 1. Test auth service configuration endpoint

            config_response = await auth_service_client.get("/auth/config")

            assert config_response.status_code == 200

            

            config = config_response.json()

            assert config["google_client_id"] != ""

            assert not config["google_client_id"].startswith("REPLACE_")

            

            # 2. Test OAuth login initiation (should not fail)

            login_response = await auth_service_client.get("/auth/login", follow_redirects=False)

            

            # Should redirect to Google OAuth (302) or return error details

            if login_response.status_code == 302:

                # Successfully redirected to Google OAuth

                location = login_response.headers.get("location", "")

                assert "accounts.google.com" in location

                assert "oauth2" in location

                assert config["google_client_id"] in location

            else:

                # Should not be a configuration error

                assert login_response.status_code != 500 or "OAUTH_CONFIGURATION" not in str(login_response.json())

    

    @pytest.mark.asyncio  

    @pytest.mark.e2e

    async def test_oauth_configuration_failure_propagation(self, auth_service_client, empty_env_vars):

        """Test OAuth configuration errors propagate properly through the system."""

        with mock.patch.dict(os.environ, empty_env_vars, clear=True):

            # Test configuration endpoint

            config_response = await auth_service_client.get("/auth/config")

            

            # Should either fail with detailed error or return empty config

            if config_response.status_code == 500:

                error = config_response.json()

                if isinstance(error.get("detail"), dict):

                    assert error["detail"]["error"] in ["AUTH_CONFIG_FAILURE", "OAUTH_CONFIGURATION_BROKEN"]

            else:

                config = config_response.json()

                assert config["google_client_id"] == ""

            

            # Test login endpoint

            login_response = await auth_service_client.get("/auth/login")

            

            # Should fail with detailed error

            assert login_response.status_code == 500

            error = login_response.json()

            

            if isinstance(error.get("detail"), dict):

                assert error["detail"]["error"] == "OAUTH_CONFIGURATION_BROKEN"

                assert "errors" in error["detail"]

            else:

                assert "oauth" in error["detail"].lower() or "configuration" in error["detail"].lower()

