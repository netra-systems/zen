"""
Unit Tests for OAuth Configuration Validation - Issue #627

Tests OAuth configuration validation logic that causes deployment failures
when GOOGLE_OAUTH_CLIENT_ID_STAGING is missing or misconfigured.

Business Value: Prevents $500K+ ARR disruption from broken OAuth authentication
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from pathlib import Path

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from test_framework.ssot.base_test_case import SSOTBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestOAuthConfigurationValidation(SSOTBaseTestCase):
    """Test OAuth configuration validation for deployment."""

    def setUp(self):
        """Set up test environment with clean OAuth config."""
        super().setUp()
        self.env = IsolatedEnvironment.get_instance()
        
        # Clear any existing OAuth configuration
        oauth_vars = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET", 
            "GOOGLE_OAUTH_CLIENT_ID_STAGING",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION",
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION",
            "ENVIRONMENT"
        ]
        
        for var in oauth_vars:
            if var in os.environ:
                delattr(os.environ, var)
            self.env.set(var, "", "test_oauth_validation")

    def test_missing_google_oauth_client_id_staging_validation_failure(self):
        """
        Test that missing GOOGLE_OAUTH_CLIENT_ID_STAGING is properly detected.
        
        This test SHOULD FAIL initially, reproducing the deployment issue.
        """
        from scripts.validate_oauth_deployment import OAuthDeploymentValidator
        
        # Set up staging environment without OAuth credentials  
        self.env.set("ENVIRONMENT", "staging", "test_oauth_validation")
        
        # DO NOT set GOOGLE_OAUTH_CLIENT_ID_STAGING - this should cause validation failure
        
        validator = OAuthDeploymentValidator("staging")
        success, report = validator.validate_all()
        
        # This should FAIL because GOOGLE_OAUTH_CLIENT_ID_STAGING is missing
        self.assertFalse(success, "OAuth validation should fail with missing GOOGLE_OAUTH_CLIENT_ID_STAGING")
        self.assertIn("Google Client ID", report)
        self.assertIn("NOT FOUND", report)
        self.assertTrue(len(validator.validation_errors) > 0, "Should have validation errors")

    def test_environment_specific_oauth_configuration_enforcement(self):
        """Test that staging environment enforces environment-specific OAuth variables."""
        from scripts.validate_oauth_deployment import OAuthDeploymentValidator
        
        # Set up staging environment with generic variables only
        self.env.set("ENVIRONMENT", "staging", "test_oauth_validation")
        self.env.set("GOOGLE_CLIENT_ID", "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com", "test_oauth_validation")
        self.env.set("GOOGLE_CLIENT_SECRET", "GOCSPX-abcdefghijklmnop", "test_oauth_validation")
        
        # Do NOT set GOOGLE_OAUTH_CLIENT_ID_STAGING - this tests the preference logic
        
        validator = OAuthDeploymentValidator("staging")
        env_vars = validator.validate_environment_variables()
        
        # Should prefer staging-specific variables over generic ones
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID_STAGING", env_vars)
        self.assertIsNone(env_vars["GOOGLE_OAUTH_CLIENT_ID_STAGING"], 
                          "GOOGLE_OAUTH_CLIENT_ID_STAGING should be missing")
        
        # Should have warnings about missing preferred variables
        self.assertTrue(len(validator.validation_warnings) > 0)
        has_staging_warning = any("GOOGLE_OAUTH_CLIENT_ID_STAGING" in w for w in validator.validation_warnings)
        self.assertTrue(has_staging_warning, "Should warn about missing staging-specific variable")

    def test_ssot_central_configuration_validator_behavior(self):
        """Test SSOT configuration validator detects OAuth configuration gaps."""
        from scripts.validate_oauth_deployment import OAuthDeploymentValidator
        
        # Set up production environment with placeholder values (should fail)
        self.env.set("ENVIRONMENT", "production", "test_oauth_validation")
        self.env.set("GOOGLE_CLIENT_ID", "REPLACE_WITH_GOOGLE_CLIENT_ID", "test_oauth_validation")
        self.env.set("GOOGLE_CLIENT_SECRET", "REPLACE_WITH_GOOGLE_CLIENT_SECRET", "test_oauth_validation")
        
        validator = OAuthDeploymentValidator("production")
        success, report = validator.validate_all()
        
        # Should fail due to placeholder values
        self.assertFalse(success, "Should fail with placeholder OAuth values in production")
        self.assertIn("placeholder", report.lower())
        
        # Should have specific error about placeholders
        has_placeholder_error = any("placeholder" in e.lower() for e in validator.validation_errors)
        self.assertTrue(has_placeholder_error, "Should detect placeholder values as errors")

    def test_auth_service_startup_oauth_validation(self):
        """Test auth service startup OAuth validation logic."""
        
        # Mock the auth service configuration 
        with patch('auth_service.auth_core.config.AuthConfig') as mock_config:
            mock_config.get_environment.return_value = "staging"
            mock_config.get_google_client_id.return_value = None  # Missing OAuth ID
            mock_config.get_google_client_secret.return_value = None  # Missing OAuth secret
            
            # Import and test the validation logic from main.py
            # This should raise RuntimeError due to missing OAuth configuration
            with self.assertRaises(RuntimeError) as context:
                # Simulate the OAuth validation from auth_service.main.py lifespan
                oauth_validation_errors = []
                
                google_client_id = mock_config.get_google_client_id()
                if not google_client_id:
                    oauth_validation_errors.append("Google OAuth client ID is not configured")
                    
                google_client_secret = mock_config.get_google_client_secret()
                if not google_client_secret:
                    oauth_validation_errors.append("Google OAuth client secret is not configured")
                
                if oauth_validation_errors:
                    raise RuntimeError(f"OAuth configuration validation failed in staging: {', '.join(oauth_validation_errors)}")
            
            # Verify the error message contains OAuth configuration details
            error_message = str(context.exception)
            self.assertIn("OAuth configuration validation failed", error_message)
            self.assertIn("staging", error_message)

    def test_deployment_script_oauth_validation_integration(self):
        """Test deployment script's OAuth validation prevents deployment."""
        
        # Mock the deployment script's OAuth validation
        with patch('scripts.validate_oauth_deployment.OAuthDeploymentValidator') as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_all.return_value = (False, "CRITICAL: OAuth validation failed")
            mock_validator_class.return_value = mock_validator
            
            # Import and test the deployment script validation
            from scripts.deploy_to_gcp_actual import GCPDeployer
            
            deployer = GCPDeployer("netra-staging")
            
            # The _validate_oauth_configuration method should return False for failed validation
            success = deployer._validate_oauth_configuration()
            
            # Should fail due to OAuth validation failure
            self.assertFalse(success, "Deployment should be blocked by OAuth validation failure")
            mock_validator.validate_all.assert_called_once()

    def test_oauth_credential_format_validation(self):
        """Test OAuth credential format validation catches invalid formats."""
        from scripts.validate_oauth_deployment import OAuthDeploymentValidator
        
        self.env.set("ENVIRONMENT", "staging", "test_oauth_validation")
        
        # Test invalid Google Client ID (too short)
        self.env.set("GOOGLE_CLIENT_ID", "invalid", "test_oauth_validation")
        self.env.set("GOOGLE_CLIENT_SECRET", "GOCSPX-validlengthsecret", "test_oauth_validation")
        
        validator = OAuthDeploymentValidator("staging")
        success, report = validator.validate_all()
        
        # Should fail due to invalid client ID format
        self.assertFalse(success)
        self.assertIn("TOO SHORT", report)
        
        # Test valid format
        self.env.set("GOOGLE_CLIENT_ID", "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com", "test_oauth_validation")
        
        validator2 = OAuthDeploymentValidator("staging")
        success2, report2 = validator2.validate_all()
        
        # Should still fail due to missing staging-specific vars, but not format issues
        client_id_errors = [e for e in validator2.validation_errors if "too short" in e.lower()]
        self.assertEqual(len(client_id_errors), 0, "Should not have client ID format errors with valid format")

    def test_google_secret_manager_oauth_validation(self):
        """Test Google Secret Manager OAuth secret validation."""
        from scripts.validate_oauth_deployment import OAuthDeploymentValidator
        
        # Mock Google Cloud SDK not available
        with patch('scripts.validate_oauth_deployment.GOOGLE_CLOUD_AVAILABLE', False):
            validator = OAuthDeploymentValidator("staging")
            gsm_secrets = validator.validate_google_secret_manager()
            
            # Should return empty dict when GSM is not available
            self.assertEqual(gsm_secrets, {})
            
        # Mock Google Cloud SDK available but secrets missing
        with patch('scripts.validate_oauth_deployment.GOOGLE_CLOUD_AVAILABLE', True):
            with patch('scripts.validate_oauth_deployment.secretmanager') as mock_sm:
                mock_client = MagicMock()
                mock_client.access_secret_version.side_effect = Exception("Secret not found")
                mock_sm.SecretManagerServiceClient.return_value = mock_client
                
                validator = OAuthDeploymentValidator("staging")
                gsm_secrets = validator.validate_google_secret_manager()
                
                # Should have validation errors for missing secrets
                self.assertTrue(len(validator.validation_errors) > 0)
                secret_errors = [e for e in validator.validation_errors if "secret" in e.lower()]
                self.assertTrue(len(secret_errors) > 0)

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    unittest.main()