"""OAuth Configuration Issues - Failing Tests

Tests that replicate OAuth configuration warnings and issues found in staging.
These tests are designed to FAIL to demonstrate current problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and OAuth authentication availability
- Value Impact: Ensures OAuth flows work correctly in staging/production
- Strategic Impact: Prevents authentication breakdowns affecting all user tiers

Key Issues to Test:
1. OAuth configuration warnings - GOOGLE_CLIENT_ID vs GOOGLE_OAUTH_CLIENT_ID_STAGING naming mismatch
2. Environment-specific OAuth variable handling
3. OAuth secret validation and fallback behavior
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.secret_loader import AuthSecretLoader
import pytest


class TestOAuthConfigurationWarnings:
    """Test OAuth configuration warnings and naming mismatches."""
    
    def test_staging_oauth_client_id_naming_mismatch_fails(self):
        """Test that OAuth configuration correctly reads GOOGLE_OAUTH_CLIENT_ID_STAGING.
        
        ISSUE: Currently expects GOOGLE_CLIENT_ID but staging uses GOOGLE_OAUTH_CLIENT_ID_STAGING
        This test FAILS to demonstrate the naming mismatch problem.
        """
        # Simulate staging environment with staging-specific OAuth variables
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'staging-client-secret-67890',
            # NOTE: GOOGLE_CLIENT_ID is NOT set - this is the mismatch
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # This SHOULD work but currently FAILS due to naming mismatch
            client_id = AuthSecretLoader.get_google_client_id()
            
            # EXPECTED: Should return the staging-specific client ID
            # ACTUAL: Returns empty string because it looks for GOOGLE_CLIENT_ID
            assert client_id == 'staging-client-id-12345', \
                f"Expected staging client ID 'staging-client-id-12345', but got: '{client_id}'"
            
            # This test will FAIL because the current code doesn't properly handle
            # the GOOGLE_OAUTH_CLIENT_ID_STAGING variable
    
    def test_staging_oauth_client_secret_naming_mismatch_fails(self):
        """Test that OAuth configuration correctly reads GOOGLE_OAUTH_CLIENT_SECRET_STAGING.
        
        ISSUE: Similar to client ID, secret has naming mismatch
        This test FAILS to demonstrate the naming mismatch problem.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'staging-client-secret-67890',
            # NOTE: GOOGLE_CLIENT_SECRET is NOT set - this is the mismatch
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            client_secret = AuthSecretLoader.get_google_client_secret()
            
            # EXPECTED: Should return the staging-specific client secret
            # ACTUAL: Returns empty string because it looks for GOOGLE_CLIENT_SECRET
            assert client_secret == 'staging-client-secret-67890', \
                f"Expected staging client secret, but got: '{client_secret}'"
            
            # This test will FAIL because the current code doesn't properly handle
            # the GOOGLE_OAUTH_CLIENT_SECRET_STAGING variable
    
    def test_oauth_configuration_warnings_not_logged_with_staging_vars_fails(self):
        """Test that warnings are not logged when staging-specific variables are set.
        
        ISSUE: System logs warnings even when staging-specific OAuth vars are properly set
        This test FAILS to demonstrate the warning logic problem.
        """
        import logging
        from io import StringIO
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        
        # Get the auth_service logger
        logger = logging.getLogger('auth_service.auth_core.secret_loader')
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'valid-staging-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'valid-staging-client-secret-67890',
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # This should NOT generate warnings since staging vars are properly set
            client_id = AuthSecretLoader.get_google_client_id()
            client_secret = AuthSecretLoader.get_google_client_secret()
            
            log_output = log_capture.getvalue()
            
            # EXPECTED: No warnings should be logged
            # ACTUAL: Warnings are still logged due to fallback logic issues
            assert "No Google Client ID found" not in log_output, \
                f"Should not warn when GOOGLE_OAUTH_CLIENT_ID_STAGING is set. Log output: {log_output}"
            
            assert "No Google Client Secret found" not in log_output, \
                f"Should not warn when GOOGLE_OAUTH_CLIENT_SECRET_STAGING is set. Log output: {log_output}"
            
            # This test will FAIL because warnings are still generated
            # even when staging-specific variables are properly configured
    
    def test_github_oauth_similar_naming_issue_fails(self):
        """Test similar naming issue with GitHub OAuth variables.
        
        ISSUE: Similar pattern exists for GitHub OAuth - staging-specific vars not handled
        This test FAILS to demonstrate the same pattern with GitHub.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GITHUB_OAUTH_CLIENT_ID_STAGING': 'staging-github-client-id',
            'GITHUB_OAUTH_CLIENT_SECRET_STAGING': 'staging-github-client-secret',
            # NOTE: GITHUB_CLIENT_ID/SECRET are NOT set
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # If there were GitHub OAuth support, this would have the same issue
            # For now, we test that the pattern exists and would fail
            
            # Simulate GitHub OAuth configuration (if it existed)
            # This demonstrates the same pattern would fail for GitHub
            github_client_id = os.getenv('GITHUB_CLIENT_ID', '')  # Current pattern
            github_staging_client_id = os.getenv('GITHUB_OAUTH_CLIENT_ID_STAGING', '')  # What we need
            
            # Current code would look for GITHUB_CLIENT_ID and find nothing
            assert github_client_id != '', \
                "Current pattern would fail to find GitHub client ID in staging"
            
            # This test FAILS because the same naming pattern issue applies to GitHub
            # and other OAuth providers
    
    def test_oauth_config_endpoint_returns_empty_client_id_fails(self):
        """Test that /auth/config endpoint fails when OAuth variables are misconfigured.
        
        ISSUE: Config endpoint returns empty client_id due to naming mismatch
        This test FAILS to demonstrate the endpoint returning invalid config.
        """
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'valid-staging-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'valid-staging-client-secret-67890',
            # NOTE: Generic GOOGLE_CLIENT_ID/SECRET not set
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            response = client.get("/auth/config")
            
            assert response.status_code == 200
            config_data = response.json()
            
            # EXPECTED: Should return the staging-specific client ID
            # ACTUAL: Returns empty string due to naming mismatch
            assert config_data["google_client_id"] == "valid-staging-client-id-12345", \
                f"Expected staging client ID in config, got: {config_data.get('google_client_id', 'MISSING')}"
            
            # EXPECTED: Should not be in development mode
            assert not config_data["development_mode"], \
                "Should not be in development mode when ENVIRONMENT=staging"
            
            # This test will FAIL because the config endpoint returns empty client_id
            # due to the OAuth variable naming mismatch

    def test_oauth_fallback_chain_priority_fails(self):
        """Test that OAuth fallback chain has correct priority.
        
        ISSUE: Environment-specific variables should have higher priority than generic ones
        This test FAILS to demonstrate incorrect priority handling.
        """
        # Set both generic and environment-specific variables
        mixed_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLIENT_ID': 'generic-client-id',
            'GOOGLE_CLIENT_SECRET': 'generic-client-secret',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-specific-client-id',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'staging-specific-client-secret',
        }
        
        with patch.dict(os.environ, mixed_env, clear=True):
            client_id = AuthSecretLoader.get_google_client_id()
            client_secret = AuthSecretLoader.get_google_client_secret()
            
            # EXPECTED: Should prefer staging-specific variables over generic ones
            # ACTUAL: Current implementation has incorrect priority
            assert client_id == 'staging-specific-client-id', \
                f"Should prefer GOOGLE_OAUTH_CLIENT_ID_STAGING over GOOGLE_CLIENT_ID, got: {client_id}"
            
            assert client_secret == 'staging-specific-client-secret', \
                f"Should prefer GOOGLE_OAUTH_CLIENT_SECRET_STAGING over GOOGLE_CLIENT_SECRET, got: {client_secret}"
            
            # This test will FAIL because the fallback chain doesn't prioritize
            # environment-specific variables correctly


class TestStagingSpecificOAuthIssues:
    """Test staging-specific OAuth configuration issues."""
    
    def test_cloud_run_secret_manager_integration_fails(self):
        """Test OAuth configuration from Cloud Run Secret Manager.
        
        ISSUE: Secret Manager integration doesn't handle staging-specific secret names
        This test FAILS to demonstrate Secret Manager integration issues.
        """
        # Simulate Cloud Run environment with Secret Manager
        cloud_run_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',
            'GCP_PROJECT_ID': 'netra-staging',
            # Secrets should be loaded from Secret Manager
        }
        
        with patch.dict(os.environ, cloud_run_env, clear=True):
            with patch.object(AuthSecretLoader, '_load_from_secret_manager') as mock_secret_manager:
                # Mock Secret Manager to return staging-specific secrets
                mock_secret_manager.side_effect = lambda secret_name: {
                    'staging-google-client-id': 'sm-staging-client-id-12345',
                    'staging-google-client-secret': 'sm-staging-client-secret-67890'
                }.get(secret_name)
                
                client_id = AuthSecretLoader.get_google_client_id()
                client_secret = AuthSecretLoader.get_google_client_secret()
                
                # EXPECTED: Should load from Secret Manager with correct staging secret names
                # ACTUAL: Secret Manager integration doesn't use correct naming pattern
                assert client_id == 'sm-staging-client-id-12345', \
                    f"Should load staging client ID from Secret Manager, got: {client_id}"
                
                # Verify correct secret names were requested
                expected_calls = [
                    'staging-google-client-id',
                    'staging-google-client-secret'
                ]
                actual_calls = [call[0][0] for call in mock_secret_manager.call_args_list]
                
                for expected_call in expected_calls:
                    assert expected_call in actual_calls, \
                        f"Should request secret '{expected_call}' from Secret Manager. Actual calls: {actual_calls}"
                
                # This test will FAIL because Secret Manager integration
                # doesn't use the correct staging-specific secret names
    
    def test_oauth_config_validation_in_staging_startup_fails(self):
        """Test OAuth validation during staging startup.
        
        ISSUE: Startup validation fails due to OAuth configuration naming mismatch
        This test FAILS to demonstrate startup validation issues.
        """
        from auth_service.main import app
        
        staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'valid-staging-client-id',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'valid-staging-client-secret',
            'PORT': '8080',
            'K_SERVICE': 'netra-auth-staging'
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Simulate the startup validation that occurs in main.py
            try:
                google_client_id = AuthConfig.get_google_client_id()
                google_client_secret = AuthConfig.get_google_client_secret()
                
                # EXPECTED: Startup validation should pass with staging-specific variables
                # ACTUAL: Validation fails due to empty client ID/secret
                assert google_client_id != '', \
                    "Startup should find valid Google Client ID in staging"
                
                assert len(google_client_id) >= 50, \
                    f"Google Client ID should be valid length, got {len(google_client_id)} chars"
                
                assert google_client_secret != '', \
                    "Startup should find valid Google Client Secret in staging"
                
                assert len(google_client_secret) >= 20, \
                    f"Google Client Secret should be valid length, got {len(google_client_secret)} chars"
                
            except Exception as e:
                # EXPECTED: Should not raise exceptions with valid staging config
                # ACTUAL: Raises exceptions due to missing OAuth configuration
                pytest.fail(f"Startup OAuth validation failed with valid staging config: {e}")
                
            # This test will FAIL because startup validation doesn't find
            # the staging-specific OAuth variables


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])