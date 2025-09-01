from shared.isolated_environment import get_env
"""
env = get_env()
Integration tests for SecretManagerBuilder.

Tests the unified secret management system across different environments
and ensures proper functionality for all sub-builders.
"""

import os
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from shared.secret_manager_builder import (
    SecretManagerBuilder,
    SecretInfo,
    SecretValidationResult,
    get_secret_manager,
    load_secrets_for_service,
    get_jwt_secret
)


class TestSecretManagerBuilderIntegration:
    """Integration tests for SecretManagerBuilder."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Save original environment
        self.original_env = env.get_all()
        
        # Set test environment variables
        env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-chars-min', "test")
        env.set('POSTGRES_PASSWORD', 'test-postgres-password', "test")
        env.set('REDIS_PASSWORD', 'test-redis-password', "test")
        env.set('FERNET_KEY', 'test-fernet-key-32-chars-exactly-required', "test")
        env.set('ANTHROPIC_API_KEY', 'sk-ant-test-key', "test")
        
        yield
        
        # Restore environment
        env.clear()
        env.update(self.original_env, "test")
    
    def test_development_environment_detection(self):
        """Test that development environment is properly detected."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        assert builder._environment == 'development'
        assert builder.development.should_allow_fallback() is True
    
    def test_staging_environment_detection(self):
        """Test that staging environment is properly detected."""
        env.set('ENVIRONMENT', 'staging', "test")
        env.set('K_SERVICE', 'netra-staging-service', "test")
        
        builder = SecretManagerBuilder()
        assert builder._environment == 'staging'
        assert builder.development.should_allow_fallback() is False
    
    def test_production_environment_detection(self):
        """Test that production environment is properly detected."""
        env.set('ENVIRONMENT', 'production', "test")
        env.set('K_SERVICE', 'netra-production-service', "test")
        
        builder = SecretManagerBuilder()
        assert builder._environment == 'production'
        assert builder.development.should_allow_fallback() is False
    
    def test_load_all_secrets_development(self):
        """Test loading all secrets in development environment."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        secrets = builder.load_all_secrets()
        
        # Check critical secrets are loaded
        assert 'JWT_SECRET_KEY' in secrets
        assert secrets['JWT_SECRET_KEY'] == 'test-jwt-secret-key-32-chars-min'
        assert 'POSTGRES_PASSWORD' in secrets
        assert 'REDIS_PASSWORD' in secrets
        assert 'FERNET_KEY' in secrets
        assert 'ANTHROPIC_API_KEY' in secrets
    
    def test_get_individual_secret(self):
        """Test getting individual secrets with caching."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        
        # Get secret (should cache it)
        jwt_secret = builder.get_secret('JWT_SECRET_KEY')
        assert jwt_secret == 'test-jwt-secret-key-32-chars-min'
        
        # Get from cache (should be faster)
        start_time = time.time()
        cached_secret = builder.get_secret('JWT_SECRET_KEY', use_cache=True)
        cache_time = time.time() - start_time
        
        assert cached_secret == jwt_secret
        assert cache_time < 0.01  # Should be very fast from cache (< 10ms)
    
    def test_secret_validation_development(self):
        """Test secret validation in development."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        validation_result = builder.validate_configuration()
        
        # Should be valid in development even with test values
        assert validation_result.is_valid is True
        assert validation_result.placeholder_count == 0
    
    def test_secret_validation_production_strict(self):
        """Test strict validation for production environment."""
        env.set('ENVIRONMENT', 'production', "test")
        env.set('JWT_SECRET_KEY', 'placeholder', "test")  # Invalid for production
        
        builder = SecretManagerBuilder()
        secrets = {'JWT_SECRET_KEY': 'placeholder'}
        
        validation_result = builder.validation.validate_critical_secrets(secrets)
        
        assert validation_result.is_valid is False
        assert validation_result.placeholder_count > 0
        assert 'JWT_SECRET_KEY' in validation_result.critical_failures
    
    def test_cache_builder_functionality(self):
        """Test the cache builder's TTL and invalidation."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        
        # Cache a secret with short TTL
        builder.cache.cache_secret('TEST_SECRET', 'test_value', ttl_minutes=0.01)  # 0.6 seconds
        
        # Should be available immediately
        assert builder.cache.get_cached_secret('TEST_SECRET') == 'test_value'
        
        # Wait for expiration
        time.sleep(1)
        
        # Should be expired
        assert builder.cache.get_cached_secret('TEST_SECRET') is None
        
        # Test invalidation
        builder.cache.cache_secret('TEST_SECRET_2', 'test_value_2', ttl_minutes=60)
        assert builder.cache.get_cached_secret('TEST_SECRET_2') == 'test_value_2'
        
        builder.cache.invalidate_cache('TEST_SECRET_2')
        assert builder.cache.get_cached_secret('TEST_SECRET_2') is None
    
    def test_auth_builder_jwt_secret(self):
        """Test auth builder JWT secret retrieval."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        jwt_secret = builder.auth.get_jwt_secret()
        
        assert jwt_secret == 'test-jwt-secret-key-32-chars-min'
        assert len(jwt_secret) >= 32  # Minimum security requirement
    
    def test_encryption_builder(self):
        """Test encryption/decryption functionality."""
        env.set('ENVIRONMENT', 'development', "test")
        env.set('FERNET_KEY', 'YXqyWl7T7vwLMjnYGk6QCzN4-ivKsaVqyb5L6DwGVoM=', "test")  # Valid Fernet key
        
        builder = SecretManagerBuilder()
        
        # Test encryption and decryption
        original_value = 'my-secret-password'
        encrypted = builder.encryption.encrypt_secret(original_value)
        
        assert encrypted != original_value  # Should be encrypted
        
        decrypted = builder.encryption.decrypt_secret(encrypted)
        assert decrypted == original_value  # Should decrypt correctly
    
    def test_development_fallbacks(self):
        """Test development fallback mechanisms."""
        env.set('ENVIRONMENT', 'development', "test")
        
        # Remove JWT_SECRET_KEY from environment
        if 'JWT_SECRET_KEY' in os.environ:
            env.delete('JWT_SECRET_KEY', "test")
        
        builder = SecretManagerBuilder()
        
        # Should get development fallback or from other sources
        jwt_secret = builder.auth.get_jwt_secret()
        # In development, should get a JWT secret (even if from fallback)
        assert jwt_secret is not None
        assert len(jwt_secret) >= 16  # Should have minimum length
    
    @patch('shared.secret_manager_builder.SecretManagerBuilder.GCPSecretBuilder._get_secret_client')
    def test_gcp_secret_retrieval(self, mock_client):
        """Test GCP secret retrieval with mocked client."""
        env.set('ENVIRONMENT', 'staging', "test")
        
        # Mock GCP client
        mock_secret_client = MagicMock()
        mock_client.return_value = mock_secret_client
        
        # Mock secret response
        mock_response = Mock()
        mock_response.payload.data.decode.return_value = 'gcp-jwt-secret-value'
        mock_secret_client.access_secret_version.return_value = mock_response
        
        builder = SecretManagerBuilder()
        secret = builder.gcp.get_secret('jwt-secret-key')
        
        assert secret == 'gcp-jwt-secret-value'
    
    def test_service_specific_configuration(self):
        """Test service-specific secret loading."""
        env.set('ENVIRONMENT', 'development', "test")
        
        # Test for netra_backend
        backend_builder = SecretManagerBuilder(service='netra_backend')
        assert backend_builder.service == 'netra_backend'
        
        backend_secrets = backend_builder.load_all_secrets()
        assert 'JWT_SECRET_KEY' in backend_secrets
        
        # Test for auth_service
        auth_builder = SecretManagerBuilder(service='auth_service')
        assert auth_builder.service == 'auth_service'
        
        auth_secrets = auth_builder.load_all_secrets()
        assert 'JWT_SECRET_KEY' in auth_secrets
    
    def test_backward_compatibility_functions(self):
        """Test backward compatibility wrapper functions."""
        env.set('ENVIRONMENT', 'development', "test")
        
        # Test get_secret_manager
        manager = get_secret_manager('shared')
        assert isinstance(manager, SecretManagerBuilder)
        
        # Test load_secrets_for_service
        secrets = load_secrets_for_service('shared')
        assert isinstance(secrets, dict)
        assert len(secrets) > 0
        
        # Test get_jwt_secret
        jwt = get_jwt_secret('shared')
        assert jwt == 'test-jwt-secret-key-32-chars-min'
    
    def test_debug_info_comprehensive(self):
        """Test comprehensive debug information."""
        env.set('ENVIRONMENT', 'development', "test")
        
        builder = SecretManagerBuilder()
        debug_info = builder.get_debug_info()
        
        assert 'environment' in debug_info
        assert debug_info['environment'] == 'development'
        assert 'service' in debug_info
        assert 'gcp_connectivity' in debug_info
        assert 'validation' in debug_info
        assert 'cache_stats' in debug_info
        assert 'features' in debug_info
    
    def test_multi_environment_consistency(self):
        """Test that secrets are consistent across environment switches."""
        # Start in development
        env.set('ENVIRONMENT', 'development', "test")
        dev_builder = SecretManagerBuilder()
        dev_jwt = dev_builder.auth.get_jwt_secret()
        
        # Switch to staging (simulated)
        env.set('ENVIRONMENT', 'staging', "test")
        staging_builder = SecretManagerBuilder()
        
        # In real staging, would get from GCP, but in test gets from env
        staging_jwt = staging_builder.auth.get_jwt_secret()
        
        # Both should have valid JWT secrets
        assert len(dev_jwt) >= 32
        assert len(staging_jwt) >= 32
    
    def test_secret_info_dataclass(self):
        """Test SecretInfo dataclass functionality."""
        secret_info = SecretInfo(
            name='TEST_SECRET',
            value='test_value',
            source='environment',
            environment='development',
            cached_at=datetime.now(timezone.utc),
            ttl_minutes=60,
            encrypted=False,
            audit_logged=True
        )
        
        assert secret_info.name == 'TEST_SECRET'
        assert secret_info.value == 'test_value'
        assert secret_info.source == 'environment'
        assert secret_info.ttl_minutes == 60
    
    def test_performance_load_time(self):
        """Test that secret loading meets performance requirements."""
        env.set('ENVIRONMENT', 'development', "test")
        
        start_time = time.time()
        builder = SecretManagerBuilder()
        secrets = builder.load_all_secrets()
        load_time_ms = (time.time() - start_time) * 1000
        
        # Should load in under 100ms for development
        assert load_time_ms < 100, f"Load time {load_time_ms}ms exceeds 100ms target"
        assert len(secrets) > 0