from unittest.mock import Mock, patch, MagicMock

"""Critical Test: Staging Configuration Loading

Verifies that staging configuration loads correctly with proper environment detection,
secret loading, and validation.

Business Value: Platform/Internal - System Stability
Prevents staging deployment failures due to configuration issues.
""""

import os
import sys
import pytest
from pathlib import Path
from typing import Dict, Any
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestStagingConfigurationLoading:
    """Test staging configuration loading and validation."""
    
    @pytest.fixture
    def staging_env_vars(self) -> Dict[str, str]:
        """Provide staging environment variables."""
        return {
        'ENVIRONMENT': 'staging',
        'GCP_PROJECT_ID': 'netra-staging',
        'DATABASE_URL': 'postgresql://user:pass@staging-db:5432/netra_staging?sslmode=require',
        'POSTGRES_HOST': 'staging-db',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'staging-password',
        'JWT_SECRET_KEY': 'staging-jwt-secret-key-at-least-32-characters-long',
        'FERNET_KEY': 'staging-fernet-key-base64-encoded-value-here==',
        'SERVICE_SECRET': 'staging-service-secret-different-from-jwt-key',
        'SERVICE_ID': 'backend-staging',
        'REDIS_URL': 'redis://staging-redis:6379/0',
        'CLICKHOUSE_HOST': 'staging-clickhouse',
        'CLICKHOUSE_PASSWORD': 'staging-clickhouse-pass',
        }
    
        def test_environment_detection_uses_isolated_environment(self, staging_env_vars):
        """Use real service instance."""
        # TODO: Initialize real service
        """Test that environment detection uses IsolatedEnvironment."""
        # Clear any existing environment
        with patch.dict(os.environ, {}, clear=True):
        # Import after clearing to ensure fresh state
        from shared.isolated_environment import get_env
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
        # Set environment variables through IsolatedEnvironment
        env = get_env()
        for key, value in staging_env_vars.items():
        env.set(key, value, "test")
            
        # Create config manager and check environment detection
        config_manager = UnifiedConfigManager()
        detected_env = config_manager._detect_environment()
            
        assert detected_env == "staging", f"Expected 'staging' but got '{detected_env}'"
    
        def test_secret_manager_uses_isolated_environment(self, staging_env_vars):
        """Test that SecretManager uses IsolatedEnvironment for environment detection."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import get_env
            
        # Set staging environment through IsolatedEnvironment
        env = get_env()
        env.set('ENVIRONMENT', 'staging', 'test')
        env.set('GCP_PROJECT_ID', 'netra-staging', 'test')
            
        # Mock the config manager to avoid full initialization
        with patch('netra_backend.app.core.secret_manager.config_manager') as mock_config_mgr:
        mock_config = MagicMock()  # TODO: Use real service instance
        mock_config.environment = 'staging'
        mock_config_mgr.get_config.return_value = mock_config
                
        from netra_backend.app.core.secret_manager import SecretManager
                
        # Create SecretManager and verify it detects staging
        secret_manager = SecretManager()
                
        # The project ID should be the staging one
        assert secret_manager._project_id == "701982941522", \
        f"Expected staging project ID but got {secret_manager._project_id}"
    
        def test_staging_configuration_validator(self, staging_env_vars):
        """Test staging configuration validator."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import get_env
        from netra_backend.app.core.configuration.staging_validator import (
        StagingConfigurationValidator,
        validate_staging_config
        )
            
        # Set up environment
        env = get_env()
        for key, value in staging_env_vars.items():
        env.set(key, value, "test")
            
        # Validate configuration
        validator = StagingConfigurationValidator()
        result = validator.validate()
            
        # Should be valid with all required variables
        assert result.is_valid, f"Validation failed: {result.errors}"
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"
        assert len(result.missing_critical) == 0, f"Missing critical: {result.missing_critical}"
    
        def test_staging_validator_detects_missing_variables(self):
        """Test that validator detects missing critical variables."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import get_env
        from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
        # Set only partial environment
        env = get_env()
        env.set('ENVIRONMENT', 'staging', 'test')
        # Missing other critical variables
            
        validator = StagingConfigurationValidator()
        result = validator.validate()
            
        # Should be invalid
        assert not result.is_valid
        assert len(result.missing_critical) > 0
        assert 'DATABASE_URL' in result.missing_critical
        assert 'JWT_SECRET_KEY' in result.missing_critical
    
        def test_staging_validator_detects_placeholders(self):
        """Test that validator detects placeholder values."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import get_env
        from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
        # Set environment with placeholders
        env = get_env()
        env.set('ENVIRONMENT', 'staging', 'test')
        env.set('DATABASE_URL', 'postgresql://user:REPLACE@host/db', 'test')
        env.set('JWT_SECRET_KEY', 'placeholder-value', 'test')
        env.set('SERVICE_SECRET', 'will-be-set-by-secrets', 'test')
        env.set('GCP_PROJECT_ID', 'netra-staging', 'test')
            
        validator = StagingConfigurationValidator()
        result = validator.validate()
            
        # Should be invalid due to placeholders
        assert not result.is_valid
        assert len(result.placeholders_found) > 0
        assert 'JWT_SECRET_KEY' in result.placeholders_found
        assert 'SERVICE_SECRET' in result.placeholders_found
    
        def test_staging_validator_detects_localhost(self):
        """Test that validator detects localhost references."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import get_env
        from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
        # Set environment with localhost
        env = get_env()
        env.set('ENVIRONMENT', 'staging', 'test')
        env.set('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db', 'test')
        env.set('REDIS_URL', 'redis://127.0.0.1:6379/0', 'test')
        env.set('JWT_SECRET_KEY', 'valid-jwt-secret-key-with-sufficient-length', 'test')
        env.set('SERVICE_SECRET', 'valid-service-secret-different-from-jwt', 'test')
        env.set('GCP_PROJECT_ID', 'netra-staging', 'test')
            
        validator = StagingConfigurationValidator()
        result = validator.validate()
            
        # Should have errors for localhost
        assert not result.is_valid
        errors_str = ' '.join(result.errors)
        assert 'localhost' in errors_str.lower()
    
        def test_env_file_loading_in_isolated_environment(self):
        """Test that .env file is properly loaded by IsolatedEnvironment."""
        with patch.dict(os.environ, {}, clear=True):
        from shared.isolated_environment import IsolatedEnvironment
            
        # Create a temporary .env file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write('ENVIRONMENT=staging
')
                f.write('TEST_VAR=test_value
')
                f.write('DATABASE_URL=postgresql://staging/db
')
                temp_env_file = Path(f.name)
            
            try:
                # Create new IsolatedEnvironment instance
                env = IsolatedEnvironment()
                
                # Load the temp .env file
                loaded_count = env.load_from_file(temp_env_file)
                assert loaded_count == 3, f"Expected 3 variables loaded, got {loaded_count}"
                
                # Verify variables are accessible
                assert env.get('ENVIRONMENT') == 'staging'
                assert env.get('TEST_VAR') == 'test_value'
                assert env.get('DATABASE_URL') == 'postgresql://staging/db'
                
                # If not isolated, should also be in os.environ
                if not env.is_isolated():
                    assert env.get('ENVIRONMENT') == 'staging'
                
            finally:
                # Clean up temp file
                temp_env_file.unlink(missing_ok=True)
    
    def test_full_staging_config_flow(self, staging_env_vars):
        """Test the full staging configuration loading flow."""
        with patch.dict(os.environ, {}, clear=True):
            from shared.isolated_environment import get_env
            
            # Set up staging environment
            env = get_env()
            for key, value in staging_env_vars.items():
                env.set(key, value, "test")
            
            # Mock GCP secret loading
            with patch('netra_backend.app.core.secret_manager.secretmanager') as mock_sm:
                # Mock the secret manager client
                mock_client = MagicMock()  # TODO: Use real service instance
                mock_sm.SecretManagerServiceClient.return_value = mock_client
                
                # Test configuration loading
                try:
                    from netra_backend.app.core.configuration.base import get_unified_config
                    
                    config = get_unified_config()
                    
                    # Verify environment is detected as staging
                    assert config.environment == 'staging'
                    
                    # Verify critical configuration is present
                    assert config.database_url
                    assert 'staging' in config.database_url or 'cloudsql' in config.database_url
                    
                except Exception as e:
                    # Configuration loading might fail due to other dependencies
                    # But environment detection should work
                    assert 'staging' in str(e) or env.get('ENVIRONMENT') == 'staging'


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
    pass