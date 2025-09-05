class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
    pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
    pass
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
    return self.messages_sent.copy()

"""
Regression tests for configuration secret loading.

This test suite ensures that critical secrets like SERVICE_SECRET, JWT_SECRET_KEY,
and other authentication credentials are properly loaded from environment variables
into the configuration objects for staging and production environments.

CRITICAL INCIDENT: September 2025
- SERVICE_SECRET and other secrets were not being loaded from environment
- This caused authentication failures in staging/production
- Root cause: Config classes lacked methods to load secrets from environment
- Fix: Added _load_secrets_from_environment() to staging/production configs

This test prevents regression of this critical issue.
"""

import pytest
import os
from netra_backend.app.schemas.config import (
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
import asyncio
    StagingConfig,
    ProductionConfig,
    NetraTestingConfig,
    DevelopmentConfig
)


class TestSecretLoadingRegression:
    """Test suite to prevent regression of secret loading issues."""
    
    def test_staging_config_loads_service_secret(self):
        """Test that StagingConfig loads SERVICE_SECRET from environment."""
        # Mock environment with secrets
        mock_env = {
            'ENVIRONMENT': 'staging',
            'SERVICE_SECRET': 'test-service-secret-32-chars-minimum',
            'SERVICE_ID': 'backend',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-minimum',
            'SECRET_KEY': 'test-secret-key-32-chars-minimum',
            'FERNET_KEY': 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'POSTGRES_PASSWORD': 'test-password'
        }
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            # Configure mock to return our test environment
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            # Create staging config
            config = StagingConfig()
            
            # CRITICAL ASSERTIONS: These must all pass
            assert config.service_secret == 'test-service-secret-32-chars-minimum', \
                "SERVICE_SECRET not loaded from environment!"
            assert config.service_id == 'backend', \
                "SERVICE_ID not loaded from environment!"
            assert config.jwt_secret_key == 'test-jwt-secret-key-32-chars-minimum', \
                "JWT_SECRET_KEY not loaded from environment!"
            assert config.secret_key == 'test-secret-key-32-chars-minimum', \
                "SECRET_KEY not loaded from environment!"
            assert config.fernet_key == 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', \
                "FERNET_KEY not loaded from environment!"
    
    def test_production_config_loads_service_secret(self):
        """Test that ProductionConfig loads SERVICE_SECRET from environment."""
    pass
        # Mock environment with secrets
        mock_env = {
            'ENVIRONMENT': 'production',
            'SERVICE_SECRET': 'prod-service-secret-32-chars-minimum',
            'SERVICE_ID': 'backend-prod',
            'JWT_SECRET_KEY': 'prod-jwt-secret-key-32-chars-minimum',
            'SECRET_KEY': 'prod-secret-key-32-chars-minimum',
            'FERNET_KEY': 'ProdFernetKey_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=',
            'DATABASE_URL': 'postgresql://prod:prod@prod-host/prod',
            'POSTGRES_PASSWORD': 'prod-password'
        }
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            # Configure mock to return our test environment
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            # Create production config
            config = ProductionConfig()
            
            # CRITICAL ASSERTIONS: These must all pass
            assert config.service_secret == 'prod-service-secret-32-chars-minimum', \
                "SERVICE_SECRET not loaded from environment in production!"
            assert config.service_id == 'backend-prod', \
                "SERVICE_ID not loaded from environment in production!"
            assert config.jwt_secret_key == 'prod-jwt-secret-key-32-chars-minimum', \
                "JWT_SECRET_KEY not loaded from environment in production!"
            assert config.secret_key == 'prod-secret-key-32-chars-minimum', \
                "SECRET_KEY not loaded from environment in production!"
            assert config.fernet_key == 'ProdFernetKey_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', \
                "FERNET_KEY not loaded from environment in production!"
    
    def test_staging_config_has_load_secrets_method(self):
        """Test that StagingConfig has the _load_secrets_from_environment method."""
        assert hasattr(StagingConfig, '_load_secrets_from_environment'), \
            "StagingConfig missing _load_secrets_from_environment method!"
        
        # Verify it's callable
        config = StagingConfig.__new__(StagingConfig)
        assert callable(getattr(config, '_load_secrets_from_environment', None)), \
            "_load_secrets_from_environment is not callable!"
    
    def test_production_config_has_load_secrets_method(self):
        """Test that ProductionConfig has the _load_secrets_from_environment method."""
    pass
        assert hasattr(ProductionConfig, '_load_secrets_from_environment'), \
            "ProductionConfig missing _load_secrets_from_environment method!"
        
        # Verify it's callable
        config = ProductionConfig.__new__(ProductionConfig)
        assert callable(getattr(config, '_load_secrets_from_environment', None)), \
            "_load_secrets_from_environment is not callable!"
    
    def test_secrets_loaded_before_database_url(self):
        """Test that secrets are loaded BEFORE database URL construction.
        
        This is critical because database password might come from secrets.
        """
    pass
        mock_env = {
            'ENVIRONMENT': 'staging',
            'SERVICE_SECRET': 'test-secret',
            'POSTGRES_PASSWORD': 'secret-password',
            'DATABASE_URL': 'postgresql://user:secret-password@host/db'
        }
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            # Track method call order
            call_order = []
            
            # Patch the methods to track call order
            original_load_secrets = StagingConfig._load_secrets_from_environment
            original_load_db = StagingConfig._load_database_url_from_unified_config_staging
            
            def track_secrets(self, data):
    pass
                call_order.append('secrets')
                return original_load_secrets(self, data)
            
            def track_db(self, data):
    pass
                call_order.append('database')
                return original_load_db(self, data)
            
            with patch.object(StagingConfig, '_load_secrets_from_environment', track_secrets):
                with patch.object(StagingConfig, '_load_database_url_from_unified_config_staging', track_db):
                    config = StagingConfig()
                    
                    # Verify secrets were loaded before database
                    assert call_order == ['secrets', 'database'], \
                        f"Wrong method call order: {call_order}. Secrets must be loaded before database!"
    
    def test_missing_service_secret_logs_warning(self):
        """Test that missing SERVICE_SECRET is logged but doesn't crash."""
        mock_env = {
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            with patch('netra_backend.app.schemas.config.logging.getLogger') as mock_logger:
                logger_instance = Magic                mock_logger.return_value = logger_instance
                
                # Create config without SERVICE_SECRET
                config = StagingConfig()
                
                # Should not have service_secret set
                assert config.service_secret is None
                
                # Should have logged the missing secret
                logger_instance.info.assert_any_call('SERVICE_ID configured: False')
                logger_instance.info.assert_any_call('SERVICE_SECRET configured: False')
    
    def test_all_critical_secrets_are_loaded(self):
        """Test that ALL critical secrets defined in the code are loaded."""
    pass
        # This list must match what's in the _load_secrets_from_environment method
        critical_secrets = [
            ('SERVICE_SECRET', 'service_secret'),
            ('SERVICE_ID', 'service_id'),
            ('JWT_SECRET_KEY', 'jwt_secret_key'),
            ('SECRET_KEY', 'secret_key'),
            ('FERNET_KEY', 'fernet_key'),
        ]
        
        # Create environment with all critical secrets
        mock_env = {'ENVIRONMENT': 'staging'}
        for env_name, _ in critical_secrets:
            mock_env[env_name] = f'test-value-for-{env_name}'
        mock_env['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            config = StagingConfig()
            
            # Verify each critical secret was loaded
            for env_name, config_name in critical_secrets:
                actual_value = getattr(config, config_name, None)
                expected_value = f'test-value-for-{env_name}'
                assert actual_value == expected_value, \
                    f"{config_name} not loaded correctly! Expected {expected_value}, got {actual_value}"


class TestGoogleSecretManagerIntegration:
    """Test that secrets from Google Secret Manager are properly loaded."""
    
    @pytest.mark.integration
    def test_gsm_secrets_are_loaded_in_gcp_environment(self):
        """Test that in GCP environment, secrets from GSM are loaded.
        
        This test simulates the GCP Cloud Run environment where secrets
        are mounted as environment variables by the deployment process.
        """
    pass
        # Simulate GCP environment where GSM secrets are mounted as env vars
        mock_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'netra-staging',
            # These would be mounted by Cloud Run from GSM
            'SERVICE_SECRET': 'gsm-service-secret-value',
            'SERVICE_ID': 'gsm-service-id-value',
            'JWT_SECRET_KEY': 'gsm-jwt-secret-value',
            'SECRET_KEY': 'gsm-secret-key-value',
            'FERNET_KEY': 'gsm-fernet-key-value',
            'DATABASE_URL': 'postgresql://gsm:gsm@gsm-host/gsm-db'
        }
        
        with patch('netra_backend.app.schemas.config.get_env') as mock_get_env:
            mock_env_obj = Magic            mock_env_obj.get = lambda key, default=None: mock_env.get(key, default)
            mock_env_obj.__contains__ = lambda key: key in mock_env
            mock_env_obj.as_dict = lambda: mock_env
            mock_get_env.return_value = mock_env_obj
            
            config = StagingConfig()
            
            # All GSM secrets should be loaded
            assert config.service_secret == 'gsm-service-secret-value'
            assert config.service_id == 'gsm-service-id-value'
            assert config.jwt_secret_key == 'gsm-jwt-secret-value'
            assert config.secret_key == 'gsm-secret-key-value'
            assert config.fernet_key == 'gsm-fernet-key-value'


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])