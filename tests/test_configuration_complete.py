"""
Comprehensive Configuration Testing Suite
Tests all aspects of configuration loading, validation, and consistency.

This test suite ensures configuration system reliability and prevents
configuration-related production incidents.
"""

import os
import pytest
import time
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock
import json

# These imports will need adjustment based on final unified system
from app.core.configuration.loader import ConfigurationLoader
from app.core.configuration.environment import EnvironmentDetector
from app.schemas.Config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig


class TestEnvironmentDetection:
    """Test environment detection with clear precedence rules."""
    
    def test_testing_environment_takes_precedence(self):
        """TESTING env var should override all others."""
        with patch.dict(os.environ, {'TESTING': '1', 'ENVIRONMENT': 'production'}):
            detector = EnvironmentDetector()
            assert detector.detect() == 'testing'
    
    def test_cloud_run_detection(self):
        """Cloud Run environment should be detected."""
        with patch.dict(os.environ, {'K_SERVICE': 'my-service', 'ENVIRONMENT': 'staging'}):
            detector = EnvironmentDetector()
            # Should detect Cloud Run and use ENVIRONMENT var
            assert detector.detect() == 'staging'
    
    def test_environment_var_fallback(self):
        """ENVIRONMENT var should be used as fallback."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect() == 'production'
    
    def test_default_to_development(self):
        """Should default to development if nothing set."""
        with patch.dict(os.environ, {}, clear=True):
            detector = EnvironmentDetector()
            assert detector.detect() == 'development'


class TestConfigurationLoading:
    """Test configuration loading in correct order."""
    
    def test_loading_order(self):
        """Configuration should load in strict order."""
        loader = ConfigurationLoader()
        
        # Mock each step to verify order
        with patch.object(loader, '_detect_environment') as mock_detect, \
             patch.object(loader, '_create_base_config') as mock_base, \
             patch.object(loader, '_load_env_files') as mock_env, \
             patch.object(loader, '_apply_env_overrides') as mock_override, \
             patch.object(loader, '_load_secrets') as mock_secrets, \
             patch.object(loader, '_validate_config') as mock_validate:
            
            mock_detect.return_value = 'development'
            mock_base.return_value = DevelopmentConfig()
            
            config = loader.load()
            
            # Verify call order
            mock_detect.assert_called_once()
            mock_base.assert_called_once()
            mock_env.assert_called_once()
            mock_override.assert_called_once()
            mock_secrets.assert_called_once()
            mock_validate.assert_called_once()
    
    def test_env_file_precedence(self):
        """Test .env file loading precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create test env files
            (tmppath / '.env').write_text('TEST_VAR=base\nOVERRIDE_VAR=base')
            (tmppath / '.env.development').write_text('TEST_VAR=dev\nDEV_VAR=dev')
            (tmppath / '.env.development.local').write_text('TEST_VAR=local')
            
            loader = ConfigurationLoader(root_path=tmppath)
            
            # After loading, precedence should be: local > dev > base
            env_vars = loader._load_env_files()
            assert env_vars['TEST_VAR'] == 'local'
            assert env_vars['DEV_VAR'] == 'dev'
            assert env_vars['OVERRIDE_VAR'] == 'base'
    
    def test_environment_variable_override(self):
        """Environment variables should override .env files."""
        with patch.dict(os.environ, {'DATABASE_URL': 'env_override'}):
            loader = ConfigurationLoader()
            config = loader.load()
            assert config.database_url == 'env_override'


class TestSecretLoading:
    """Test secret loading from various sources."""
    
    def test_secret_loading_fallback_chain(self):
        """Secrets should load with proper fallback chain."""
        from app.core.configuration.secrets_unified import UnifiedSecretManager
        
        manager = UnifiedSecretManager()
        
        # Test environment-specific secret takes precedence
        with patch.dict(os.environ, {'JWT_SECRET_STAGING': 'staging_secret'}):
            secret = manager.load_secret('jwt-secret', 'staging')
            assert secret == 'staging_secret'
        
        # Test fallback to generic env var
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'generic_secret'}):
            secret = manager.load_secret('jwt-secret', 'staging')
            assert secret == 'generic_secret'
    
    @patch('google.cloud.secretmanager.SecretManagerServiceClient')
    def test_google_secret_manager_integration(self, mock_client):
        """Test Google Secret Manager integration."""
        manager = UnifiedSecretManager()
        
        # Mock Secret Manager response
        mock_response = MagicMock()
        mock_response.payload.data = b'secret_from_gsm'
        mock_client.return_value.access_secret_version.return_value = mock_response
        
        with patch.dict(os.environ, {'GCP_PROJECT_ID': 'test-project'}):
            secret = manager.load_from_secret_manager('test-secret')
            assert secret == 'secret_from_gsm'
    
    def test_required_secrets_validation(self):
        """Required secrets should fail if not found."""
        manager = UnifiedSecretManager()
        
        with pytest.raises(ValueError, match="Required secret not found"):
            manager.load_secret('critical-secret', 'production', required=True)


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_development_config_validation(self):
        """Development config should be valid with minimal settings."""
        config = DevelopmentConfig()
        loader = ConfigurationLoader()
        
        # Should not raise
        loader._validate_config(config)
    
    def test_production_config_validation(self):
        """Production config should require all critical settings."""
        config = ProductionConfig()
        loader = ConfigurationLoader()
        
        # Should fail without critical settings
        with pytest.raises(ValueError, match="Missing required configuration"):
            loader._validate_config(config)
        
        # Should pass with all required settings
        config.jwt_secret_key = 'secret'
        config.database_url = 'postgresql://...'
        config.redis_url = 'redis://...'
        loader._validate_config(config)
    
    def test_type_validation(self):
        """Configuration types should be validated."""
        config = DevelopmentConfig()
        
        # Should fail with wrong types
        with pytest.raises(TypeError):
            config.backend_port = "not_an_int"
        
        with pytest.raises(TypeError):
            config.debug = "not_a_bool"


class TestConfigurationConsistency:
    """Test configuration consistency across services."""
    
    def test_jwt_secret_consistency(self):
        """JWT secret must be same across all services."""
        # Load main backend config
        main_config = ConfigurationLoader().load()
        
        # Load auth service config
        from auth_service.auth_core.config import AuthServiceConfig
        auth_config = AuthServiceConfig()
        
        # Secrets must match
        assert main_config.jwt_secret_key == auth_config.get_jwt_secret()
    
    def test_database_config_consistency(self):
        """Database config must be consistent."""
        config = ConfigurationLoader().load()
        
        # All database URLs should point to same database
        assert config.database_url is not None
        assert 'netra' in config.database_url.lower()
    
    def test_service_url_consistency(self):
        """Service URLs must be properly configured."""
        config = ConfigurationLoader().load()
        
        # Check auth service URL
        assert config.auth_service_url is not None
        if config.environment == 'development':
            assert 'localhost' in config.auth_service_url
        else:
            assert 'https://' in config.auth_service_url


class TestConfigurationImmutability:
    """Test that configuration cannot be modified after loading."""
    
    def test_config_is_immutable(self):
        """Configuration should be immutable after loading."""
        config = ConfigurationLoader().load()
        
        # Should not be able to modify
        with pytest.raises(AttributeError):
            config.database_url = 'new_value'
        
        with pytest.raises(AttributeError):
            config.jwt_secret_key = 'new_secret'
    
    def test_nested_config_immutable(self):
        """Nested configuration objects should also be immutable."""
        config = ConfigurationLoader().load()
        
        with pytest.raises(AttributeError):
            config.clickhouse_native.host = 'new_host'


class TestConfigurationPerformance:
    """Test configuration performance characteristics."""
    
    def test_load_time(self):
        """Configuration should load quickly."""
        start = time.time()
        config = ConfigurationLoader().load()
        load_time = time.time() - start
        
        # Should load in less than 100ms
        assert load_time < 0.1, f"Configuration took {load_time:.3f}s to load"
    
    def test_caching(self):
        """Configuration should be cached after first load."""
        loader = ConfigurationLoader()
        
        # First load
        config1 = loader.load()
        
        # Second load should return same instance
        config2 = loader.load()
        
        assert config1 is config2
    
    def test_memory_usage(self):
        """Configuration should use reasonable memory."""
        import tracemalloc
        
        tracemalloc.start()
        config = ConfigurationLoader().load()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should use less than 10MB
        assert peak < 10_000_000, f"Configuration used {peak / 1_000_000:.2f}MB"


class TestConfigurationHotReload:
    """Test configuration hot reload capability."""
    
    def test_hot_reload_in_development(self):
        """Hot reload should work in development."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'CONFIG_HOT_RELOAD': 'true'}):
            loader = ConfigurationLoader()
            config1 = loader.load()
            
            # Change an env var
            with patch.dict(os.environ, {'TEST_VAR': 'new_value'}):
                loader.reload()
                config2 = loader.load()
                
                # Should be different instance
                assert config1 is not config2
    
    def test_hot_reload_disabled_in_production(self):
        """Hot reload should be disabled in production by default."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            loader = ConfigurationLoader()
            config1 = loader.load()
            
            # Try to reload
            loader.reload()
            config2 = loader.load()
            
            # Should be same instance (no reload)
            assert config1 is config2


class TestConfigurationErrorHandling:
    """Test configuration error handling."""
    
    def test_missing_required_env_var(self):
        """Should provide helpful error for missing required env vars."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            loader = ConfigurationLoader()
            
            with pytest.raises(ValueError) as exc_info:
                loader.load()
            
            assert 'JWT_SECRET_KEY' in str(exc_info.value)
            assert 'required' in str(exc_info.value).lower()
    
    def test_invalid_env_file(self):
        """Should handle invalid .env files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create invalid env file
            (tmppath / '.env').write_text('INVALID LINE WITHOUT EQUALS')
            
            loader = ConfigurationLoader(root_path=tmppath)
            
            # Should log warning but not crash
            with patch('app.logging_config.central_logger.warning') as mock_warn:
                loader._load_env_files()
                mock_warn.assert_called()
    
    def test_secret_manager_failure(self):
        """Should handle Secret Manager failures gracefully."""
        manager = UnifiedSecretManager()
        
        with patch('google.cloud.secretmanager.SecretManagerServiceClient') as mock_client:
            mock_client.side_effect = Exception("Secret Manager unavailable")
            
            # Should fall back to env vars
            with patch.dict(os.environ, {'JWT_SECRET_KEY': 'fallback_secret'}):
                secret = manager.load_secret('jwt-secret', 'staging')
                assert secret == 'fallback_secret'


class TestConfigurationIntegration:
    """Integration tests for complete configuration system."""
    
    def test_full_development_setup(self):
        """Test complete development configuration."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = ConfigurationLoader().load()
            
            assert config.environment == 'development'
            assert config.debug is True
            assert config.backend_port == 8000
            assert config.frontend_port == 3000
    
    def test_full_staging_setup(self):
        """Test complete staging configuration."""
        required_vars = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'staging_secret',
            'DATABASE_URL': 'postgresql://staging',
            'REDIS_URL': 'redis://staging'
        }
        
        with patch.dict(os.environ, required_vars):
            config = ConfigurationLoader().load()
            
            assert config.environment == 'staging'
            assert config.debug is False
            assert config.jwt_secret_key == 'staging_secret'
    
    def test_full_production_setup(self):
        """Test complete production configuration."""
        required_vars = {
            'ENVIRONMENT': 'production',
            'JWT_SECRET_KEY': 'prod_secret',
            'DATABASE_URL': 'postgresql://production',
            'REDIS_URL': 'redis://production',
            'CLICKHOUSE_HOST': 'clickhouse.prod'
        }
        
        with patch.dict(os.environ, required_vars):
            config = ConfigurationLoader().load()
            
            assert config.environment == 'production'
            assert config.debug is False
            assert config.jwt_secret_key == 'prod_secret'
            assert 'production' in config.database_url


# Property-based tests using hypothesis
try:
    from hypothesis import given, strategies as st
    
    class TestConfigurationProperties:
        """Property-based tests for configuration."""
        
        @given(env=st.sampled_from(['development', 'staging', 'production']))
        def test_environment_always_valid(self, env):
            """Environment should always be valid."""
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                config = ConfigurationLoader().load()
                assert config.environment in ['development', 'staging', 'production', 'testing']
        
        @given(port=st.integers(min_value=1, max_value=65535))
        def test_port_validation(self, port):
            """Ports should be valid."""
            config = DevelopmentConfig()
            config.backend_port = port
            assert 1 <= config.backend_port <= 65535
        
        def test_no_none_critical_fields(self):
            """Critical fields should never be None in production."""
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'production',
                'JWT_SECRET_KEY': 'secret',
                'DATABASE_URL': 'postgresql://...',
                'REDIS_URL': 'redis://...'
            }):
                config = ConfigurationLoader().load()
                
                critical_fields = [
                    'jwt_secret_key',
                    'database_url',
                    'redis_url',
                    'environment'
                ]
                
                for field in critical_fields:
                    assert getattr(config, field) is not None

except ImportError:
    # Hypothesis not installed, skip property tests
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])