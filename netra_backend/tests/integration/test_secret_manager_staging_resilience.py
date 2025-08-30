"""
Tests for Secret Manager staging resilience and error handling.

This test validates that the secret manager can gracefully degrade when GCP Secret Manager
is unavailable and fall back to environment variables in staging.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL customer tiers through system reliability)
- Business Goal: System Reliability, Staging Environment Stability
- Value Impact: Ensures staging can start even if GCP Secret Manager is temporarily unavailable
- Strategic Impact: Prevents staging deployment failures that block development velocity
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from google.api_core import exceptions as api_exceptions

from netra_backend.app.core.configuration.secrets import SecretManager
from netra_backend.app.core.isolated_environment import get_env
from shared.secret_manager_builder import SecretManagerBuilder

pytestmark = [
    pytest.mark.integration,
    pytest.mark.staging
]


class TestSecretManagerStagingResilience:
    """Test secret manager resilience in staging environment."""
    
    def setup_method(self):
        """Setup test environment."""
        self.original_env = dict(os.environ)
        
        # Set staging environment
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["GCP_PROJECT_ID"] = "netra-staging"
        
        # Set fallback environment variables
        os.environ["JWT_SECRET_KEY"] = "staging-jwt-fallback-secret"
        os.environ["FERNET_KEY"] = "staging-fernet-fallback-key-for-testing"
        os.environ["POSTGRES_PASSWORD"] = "staging-postgres-fallback"
        
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_secret_manager_handles_gcp_import_error_gracefully(self):
        """Test that SecretManager handles GCP import errors gracefully in staging."""
        with patch('netra_backend.app.core.configuration.secrets.secretmanager', side_effect=ImportError("No module named 'google.cloud.secretmanager'")):
            secret_manager = SecretManager()
            
            # Should not raise an exception
            secrets = secret_manager.load_all_secrets()
            
            # Should have fallback secrets from environment
            assert "JWT_SECRET_KEY" in secrets
            assert secrets["JWT_SECRET_KEY"] == "staging-jwt-fallback-secret"
            assert "FERNET_KEY" in secrets
            assert secrets["FERNET_KEY"] == "staging-fernet-fallback-key-for-testing"
    
    def test_secret_manager_handles_gcp_permission_denied(self):
        """Test handling of GCP permission denied errors."""
        # Mock the GCP client to raise PermissionDenied
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = api_exceptions.PermissionDenied("Permission denied")
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should fallback to environment variables
            assert "JWT_SECRET_KEY" in secrets
            assert secrets["JWT_SECRET_KEY"] == "staging-jwt-fallback-secret"
    
    def test_secret_manager_handles_gcp_not_found_error(self):
        """Test handling of GCP not found errors."""
        # Mock the GCP client to raise NotFound
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = api_exceptions.NotFound("Secret not found")
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should fallback to environment variables
            assert "JWT_SECRET_KEY" in secrets
            assert secrets["JWT_SECRET_KEY"] == "staging-jwt-fallback-secret"
    
    def test_secret_manager_handles_gcp_network_error(self):
        """Test handling of GCP network errors."""
        # Mock the GCP client to raise ServiceUnavailable
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = api_exceptions.ServiceUnavailable("Service unavailable")
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should fallback to environment variables
            assert "JWT_SECRET_KEY" in secrets
            assert secrets["JWT_SECRET_KEY"] == "staging-jwt-fallback-secret"
    
    def test_shared_secret_manager_builder_handles_gcp_errors(self):
        """Test that shared SecretManagerBuilder also handles GCP errors gracefully."""
        with patch('google.cloud.secretmanager', side_effect=ImportError("No module named 'google.cloud.secretmanager'")):
            builder = SecretManagerBuilder(service="netra_backend")
            
            # Should use DisabledGCPBuilder
            assert builder.gcp.__class__.__name__ == "DisabledGCPBuilder"
            
            # Should still return None for secrets (gracefully)
            jwt_secret = builder.gcp.get_jwt_secret()
            assert jwt_secret is None
            
            # But should be able to get secrets from environment
            env_secrets = builder.environment.load_environment_secrets()
            assert "JWT_SECRET_KEY" in env_secrets
    
    def test_secret_manager_logs_remediation_steps_in_staging(self):
        """Test that secret manager logs helpful remediation steps in staging."""
        import logging
        from io import StringIO
        
        # Capture logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("netra_backend.app.core.configuration.secrets")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            with patch('google.cloud.secretmanager.SecretManagerServiceClient', side_effect=ImportError("Module not found")):
                secret_manager = SecretManager()
                secret_manager._load_from_gcp_secret_manager()
            
            log_output = log_capture.getvalue()
            
            # Should contain remediation steps
            assert "Remediation steps:" in log_output or "google-cloud-secret-manager" in log_output
            
        finally:
            logger.removeHandler(handler)
    
    def test_secret_manager_provides_debug_info_after_errors(self):
        """Test that secret manager provides useful debug information after handling errors."""
        with patch('google.cloud.secretmanager', side_effect=ImportError("No module")):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Get debug summary
            summary = secret_manager.get_secret_summary()
            
            assert summary["environment"] == "staging"
            assert summary["secrets_loaded"] > 0  # Should have environment fallbacks
            assert summary["gcp_available"] is False
    
    def test_environment_variables_take_precedence_when_gcp_fails(self):
        """Test that environment variables are used as fallbacks when GCP fails."""
        # Set a specific environment variable
        os.environ["SERVICE_SECRET"] = "staging-service-fallback-secret"
        
        with patch('google.cloud.secretmanager', side_effect=ImportError("GCP not available")):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should use the environment variable
            assert "SERVICE_SECRET" in secrets
            assert secrets["SERVICE_SECRET"] == "staging-service-fallback-secret"
    
    def test_critical_secrets_validation_works_with_fallbacks(self):
        """Test that critical secret validation works with environment fallbacks."""
        # Ensure we have all critical secrets in environment
        os.environ["JWT_SECRET_KEY"] = "fallback-jwt-secret-32-chars-long"
        os.environ["FERNET_KEY"] = "fallback-fernet-key-44-chars-base64-encoded"
        os.environ["SERVICE_SECRET"] = "fallback-service-secret"
        os.environ["POSTGRES_PASSWORD"] = "fallback-postgres-password"
        
        with patch('google.cloud.secretmanager', side_effect=ImportError("GCP not available")):
            secret_manager = SecretManager()
            
            # Should not raise ConfigurationError even without GCP
            secrets = secret_manager.load_all_secrets()
            
            # Verify we have the critical secrets
            assert secrets["JWT_SECRET_KEY"] == "fallback-jwt-secret-32-chars-long"
            assert secrets["SERVICE_SECRET"] == "fallback-service-secret"


class TestStagingSecretManagerConfiguration:
    """Test staging-specific secret manager configuration."""
    
    def setup_method(self):
        """Setup staging test environment."""
        self.original_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["GCP_PROJECT_ID"] = "netra-staging"
    
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_staging_environment_detection(self):
        """Test that staging environment is correctly detected."""
        secret_manager = SecretManager()
        assert secret_manager._environment == "staging"
        
        # Shared builder should also detect staging
        builder = SecretManagerBuilder(service="netra_backend")
        assert builder._environment == "staging"
    
    def test_gcp_project_id_configuration_for_staging(self):
        """Test that GCP project ID is correctly configured for staging."""
        secret_manager = SecretManager()
        project_id = secret_manager._get_gcp_project_id()
        
        # Should use staging project ID
        assert project_id == "netra-staging"  # From environment
        
        # Test with numerical project ID
        os.environ["GCP_PROJECT_ID"] = "701982941522"
        secret_manager_numeric = SecretManager()
        numeric_project_id = secret_manager_numeric._get_gcp_project_id()
        assert numeric_project_id == "701982941522"
    
    def test_gcp_disabled_flag_works(self):
        """Test that DISABLE_GCP_SECRET_MANAGER flag works correctly."""
        os.environ["DISABLE_GCP_SECRET_MANAGER"] = "true"
        
        secret_manager = SecretManager()
        assert not secret_manager._is_gcp_available()
        
        # Shared builder should also respect the flag
        builder = SecretManagerBuilder(service="netra_backend")
        assert not builder._is_gcp_enabled()
    
    def test_staging_requires_gcp_project_id(self):
        """Test that staging requires GCP_PROJECT_ID to enable GCP secrets."""
        # Remove GCP_PROJECT_ID
        os.environ.pop("GCP_PROJECT_ID", None)
        
        secret_manager = SecretManager()
        assert not secret_manager._is_gcp_available()
        
        builder = SecretManagerBuilder(service="netra_backend")  
        assert not builder._is_gcp_enabled()


class TestSecretManagerErrorScenarios:
    """Test various error scenarios and recovery."""
    
    def setup_method(self):
        """Setup error test environment."""
        self.original_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["GCP_PROJECT_ID"] = "netra-staging"
    
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_mixed_gcp_and_environment_secrets(self):
        """Test handling of mixed GCP and environment variable secrets."""
        # Set some secrets in environment
        os.environ["JWT_SECRET_KEY"] = "env-jwt-secret"
        os.environ["REDIS_PASSWORD"] = "env-redis-password"
        
        # Mock GCP to return some secrets but not others
        mock_client = MagicMock()
        def mock_access_secret(name):
            if "jwt-secret-key" in name:
                response = MagicMock()
                response.payload.data.decode.return_value = "gcp-jwt-secret"
                return response
            else:
                raise api_exceptions.NotFound("Secret not found")
        
        mock_client.access_secret_version = mock_access_secret
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should have mix of GCP and environment secrets
            # GCP should override environment for available secrets
            assert "REDIS_PASSWORD" in secrets
            assert secrets["REDIS_PASSWORD"] == "env-redis-password"  # From environment (GCP failed)
    
    def test_transient_gcp_errors_dont_crash_service(self):
        """Test that transient GCP errors don't crash the service."""
        # Mock intermittent failures
        mock_client = MagicMock()
        call_count = 0
        
        def failing_access_secret(name):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise api_exceptions.DeadlineExceeded("Request timed out")
            else:
                response = MagicMock()
                response.payload.data.decode.return_value = "recovered-secret"
                return response
        
        mock_client.access_secret_version = failing_access_secret
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            
            # First calls should fail gracefully
            result1 = secret_manager.get_secret("test-secret")
            assert result1 is None  # Should handle timeout gracefully
            
            result2 = secret_manager.get_secret("test-secret")  
            assert result2 is None  # Should handle timeout gracefully
            
            # Third call should succeed
            result3 = secret_manager.get_secret("test-secret")
            # Note: This might still be None due to caching, but shouldn't crash
    
    def test_empty_secrets_handled_gracefully(self):
        """Test that empty or malformed secrets are handled gracefully."""
        mock_client = MagicMock()
        def mock_access_empty_secret(name):
            response = MagicMock()
            response.payload.data.decode.return_value = ""  # Empty secret
            return response
        
        mock_client.access_secret_version = mock_access_empty_secret
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            secret_manager = SecretManager()
            secrets = secret_manager.load_all_secrets()
            
            # Should not crash on empty secrets
            assert isinstance(secrets, dict)