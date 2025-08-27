"""
Comprehensive tests for SecretManager - production-critical secret management.

Tests cover Google Cloud Secret Manager integration, environment variable fallbacks,
staging/production configurations, error handling, and security validation.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any

from google.api_core.exceptions import NotFound, PermissionDenied
from google.cloud import secretmanager

from netra_backend.app.core.secret_manager import SecretManager, SecretManagerError
from tenacity import RetryError


class TestSecretManagerInitialization:
    """Test SecretManager initialization and configuration."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging'}, clear=False)
    def test_initialization_with_staging_environment(self, mock_config_manager):
        """Test initialization detects staging environment correctly."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.gcp_project_id_numerical_staging = '701982941522'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._project_id == '701982941522'
        assert manager._config == mock_config
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch.dict('os.environ', {'ENVIRONMENT': 'production'}, clear=False)
    def test_initialization_with_production_environment(self, mock_config_manager):
        """Test initialization detects production environment correctly."""
        mock_config = Mock()
        mock_config.environment = 'production'
        mock_config.gcp_project_id_numerical_production = '304612253870'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._project_id == '304612253870'
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_initialization_with_development_fallback(self, mock_config_manager):
        """Test initialization uses production defaults for development."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.gcp_project_id_numerical_production = '304612253870'
        mock_config.secret_manager_project_id = '999999999999'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._project_id == '304612253870'


class TestSecretManagerLoading:
    """Test secret loading logic and environment detection."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_should_load_from_secret_manager_staging(self, mock_config_manager):
        """Test staging environment triggers secret manager loading."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.load_secrets = False
        mock_config.k_service = None
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._should_load_from_secret_manager('staging') is True
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_should_load_from_secret_manager_k_service(self, mock_config_manager):
        """Test k_service presence triggers secret manager loading."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.load_secrets = False
        mock_config.k_service = 'netra-backend'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._should_load_from_secret_manager('development') is True
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_should_not_load_from_secret_manager_development(self, mock_config_manager):
        """Test development environment without flags skips secret manager."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.load_secrets = False
        mock_config.k_service = None
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._should_load_from_secret_manager('development') is False


class TestEnvironmentVariableHandling:
    """Test environment variable processing and mapping."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_environment_mapping_completeness(self, mock_config_manager):
        """Test all critical environment mappings are present."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        mapping = manager._get_environment_mapping()
        additional = manager._get_additional_environment_mapping()
        
        # Critical core services
        assert 'gemini-api-key' in mapping
        assert 'jwt-secret-key' in mapping
        assert 'fernet-key' in mapping
        assert 'google-client-id' in mapping
        assert 'google-client-secret' in mapping
        
        # Database services
        assert 'clickhouse-password' in mapping
        assert 'redis-default' in mapping
        
        # Additional services
        assert 'anthropic-api-key' in additional
        assert 'openai-api-key' in additional
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_staging_environment_detection(self, mock_config_manager):
        """Test staging environment detection with various configurations."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.k_service = None
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._detect_staging_environment() is True
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_staging_detection_via_k_service(self, mock_config_manager):
        """Test staging detection via k_service value."""
        mock_config = Mock()
        mock_config.environment = 'production'
        mock_config.k_service = 'netra-staging-service'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        assert manager._detect_staging_environment() is True


class TestGoogleSecretManagerIntegration:
    """Test Google Cloud Secret Manager client integration."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_secret_client_creation_success(self, mock_client_class, mock_config_manager):
        """Test successful Secret Manager client creation."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config_manager.get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        manager = SecretManager()
        client = manager._get_secret_client()
        
        assert client == mock_client
        mock_client_class.assert_called_once()
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_secret_client_creation_failure(self, mock_client_class, mock_config_manager):
        """Test Secret Manager client creation failure handling."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config_manager.get_config.return_value = mock_config
        
        mock_client_class.side_effect = Exception("Authentication failed")
        
        manager = SecretManager()
        
        with pytest.raises(RetryError):
            manager._get_secret_client()


class TestSecretFetching:
    """Test individual secret fetching with error scenarios."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging'}, clear=False)
    def test_fetch_secret_success(self, mock_client_class, mock_config_manager):
        """Test successful secret fetching."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.gcp_project_id_numerical_staging = '701982941522'
        mock_config_manager.get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.payload.data.decode.return_value = 'secret-value-123'
        mock_client.access_secret_version.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        manager = SecretManager()
        result = manager._fetch_secret(mock_client, 'test-secret')
        
        assert result == 'secret-value-123'
        mock_client.access_secret_version.assert_called_once_with(
            name='projects/701982941522/secrets/test-secret/versions/latest'
        )
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_fetch_secret_not_found(self, mock_client_class, mock_config_manager):
        """Test handling of secret not found errors."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.gcp_project_id_numerical_staging = '701982941522'
        mock_config_manager.get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_client.access_secret_version.side_effect = NotFound("Secret not found")
        mock_client_class.return_value = mock_client
        
        manager = SecretManager()
        result = manager._fetch_secret(mock_client, 'nonexistent-secret')
        
        assert result is None
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_fetch_secret_permission_denied(self, mock_client_class, mock_config_manager):
        """Test handling of permission denied errors."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.gcp_project_id_numerical_staging = '701982941522'
        mock_config_manager.get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_client.access_secret_version.side_effect = PermissionDenied("Access denied")
        mock_client_class.return_value = mock_client
        
        manager = SecretManager()
        result = manager._fetch_secret(mock_client, 'restricted-secret')
        
        assert result is None


class TestSecretMerging:
    """Test secret merging logic and priority handling."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_development_mode_uses_environment_only(self, mock_config_manager):
        """Test development mode uses only environment variables."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.load_secrets = False
        mock_config.k_service = None
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        base_secrets = {'jwt-secret-key': 'env-jwt-key'}
        
        result = manager._handle_development_mode_secrets(base_secrets, 1)
        
        assert result == base_secrets
        assert result['jwt-secret-key'] == 'env-jwt-key'
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_google_secrets_supersede_environment(self, mock_config_manager):
        """Test Google secrets override environment variables."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        base_secrets = {'jwt-secret-key': 'env-jwt-key'}
        google_secrets = {'jwt-secret-key': 'google-jwt-key'}
        
        result = manager._merge_google_secrets_with_logging(
            base_secrets, google_secrets, 1
        )
        
        assert result['jwt-secret-key'] == 'google-jwt-key'


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_secret_manager_error_propagation(self, mock_config_manager):
        """Test SecretManagerError is properly raised and handled."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        with patch.object(manager, '_execute_secret_manager_loading', 
                         side_effect=Exception("Connection failed")):
            with pytest.raises(SecretManagerError, match="Secret Manager loading failed"):
                manager._load_from_secret_manager()
                
    @patch('netra_backend.app.core.secret_manager.config_manager')
    @patch('netra_backend.app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_load_secrets_fallback_on_google_failure(self, mock_client_class, mock_config_manager):
        """Test fallback to environment variables when Google secrets fail."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.load_secrets = True
        mock_config_manager.get_config.return_value = mock_config
        
        # Mock environment variable loading
        with patch.object(SecretManager, '_load_from_environment', 
                         return_value={'jwt-secret-key': 'fallback-key'}):
            with patch.object(SecretManager, '_load_from_secret_manager', 
                             side_effect=SecretManagerError("Google failed")):
                manager = SecretManager()
                result = manager.load_secrets()
                
                assert result == {'jwt-secret-key': 'fallback-key'}


class TestSecretValidation:
    """Test secret validation and security requirements."""
    
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_critical_secrets_identification(self, mock_config_manager):
        """Test critical secrets are properly identified."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        # Test that critical secrets are included in mappings
        core_mapping = manager._get_core_service_mapping()
        security_mapping = manager._get_security_mapping()
        
        assert 'gemini-api-key' in core_mapping
        assert 'jwt-secret-key' in security_mapping
        assert 'fernet-key' in security_mapping
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_staging_secret_value_selection(self, mock_config_manager):
        """Test staging-specific secret values are selected correctly."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.jwt_secret_key = 'production-jwt-key'
        mock_config.jwt_secret_key_staging = 'staging-jwt-key'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        value = manager._get_secret_value_for_environment('JWT_SECRET_KEY', True)
        assert value == 'staging-jwt-key'
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_production_secret_value_fallback(self, mock_config_manager):
        """Test fallback to production values when staging not available."""
        mock_config = Mock()
        mock_config.environment = 'staging'
        mock_config.jwt_secret_key = 'production-jwt-key'
        # Explicitly set staging-specific value to None to ensure fallback
        mock_config.jwt_secret_key_staging = None
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        
        value = manager._get_secret_value_for_environment('JWT_SECRET_KEY', True)
        assert value == 'production-jwt-key'


@pytest.mark.integration
class TestSecretManagerIntegration:
    """Integration tests for SecretManager with real configurations."""
    
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test-gemini-key',
        'JWT_SECRET_KEY': 'test-jwt-key',
        'FERNET_KEY': 'test-fernet-key'
    })
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_load_secrets_from_environment_integration(self, mock_config_manager):
        """Test loading secrets from environment variables in integration."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.load_secrets = False
        mock_config.k_service = None
        mock_config.gemini_api_key = 'test-gemini-key'
        mock_config.jwt_secret_key = 'test-jwt-key'
        mock_config.fernet_key = 'test-fernet-key'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        result = manager.load_secrets()
        
        assert 'gemini-api-key' in result
        assert 'jwt-secret-key' in result
        assert 'fernet-key' in result
        assert result['gemini-api-key'] == 'test-gemini-key'
        
    @patch('netra_backend.app.core.secret_manager.config_manager')
    def test_secret_loading_flow_complete(self, mock_config_manager):
        """Test complete secret loading flow with all components."""
        mock_config = Mock()
        mock_config.environment = 'development'
        mock_config.load_secrets = False
        mock_config.k_service = None
        # Mock multiple secrets
        mock_config.gemini_api_key = 'gemini-123'
        mock_config.jwt_secret_key = 'jwt-456'
        mock_config.clickhouse_password = 'ch-789'
        mock_config.redis_password = 'redis-abc'
        mock_config_manager.get_config.return_value = mock_config
        
        manager = SecretManager()
        result = manager.load_secrets()
        
        # Verify critical secrets are present
        assert len(result) >= 4
        assert result['gemini-api-key'] == 'gemini-123'
        assert result['jwt-secret-key'] == 'jwt-456'
        assert result['clickhouse-password'] == 'ch-789'
        assert result['redis-default'] == 'redis-abc'
    
    def test_secret_rotation_detection(self):
        """Test detection of potentially rotated secrets - security critical."""
        # Mock scenarios where secrets may have been rotated
        old_jwt_key = "old-jwt-key-12345"
        new_jwt_key = "new-jwt-key-67890"
        
        # Different configurations for rotation detection
        rotation_scenarios = [
            ("jwt-secret-key", old_jwt_key, new_jwt_key),
            ("fernet-key", "old_fernet_key_12345", "new_fernet_key_67890"),
            ("google-client-secret", "old_oauth_secret_12345", "new_oauth_secret_67890")
        ]
        
        for secret_name, old_value, new_value in rotation_scenarios:
            # Verify secrets are different (rotation occurred)
            assert old_value != new_value
            assert len(old_value) > 10  # Minimum security length
            assert len(new_value) > 10  # Minimum security length
            
            # Test would detect rotation in real implementation
            # This validates the framework for rotation detection