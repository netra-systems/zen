"""
Integration Tests for Configuration Loading and Environment Handling

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Ensure reliable configuration management across environments
- Value Impact: Configuration stability directly impacts system uptime and deployment success
- Strategic Impact: Robust configuration handling enables multi-environment operations

This test suite validates:
1. Configuration loading from multiple sources (env vars, files, defaults)
2. Environment-specific configuration handling
3. Configuration validation and error handling
4. Cross-service configuration consistency
5. Configuration caching and reload mechanisms
6. Security and sensitive data handling
7. Docker vs non-Docker configuration scenarios
"""

import pytest
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, Mock

from netra_backend.app.core.config import get_settings, get_config, reload_config
from netra_backend.app.core.configuration.base import get_unified_config, config_manager
from netra_backend.app.core.config_validator import ConfigValidator
from netra_backend.app.schemas.config import AppConfig
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.fixtures.configuration_test_fixtures import isolated_config_env
from test_framework.ssot.configuration_validator import validate_test_config, is_service_enabled
from shared.isolated_environment import get_env, IsolatedEnvironment


@pytest.mark.integration
@pytest.mark.real_services
class TestConfigurationLoadingIntegration:
    """Integration tests for configuration loading with real environment scenarios."""
    
    @pytest.fixture
    def clean_config_cache(self):
        """Clean configuration cache before and after tests."""
        # Clear caches
        get_settings.cache_clear()
        if hasattr(config_manager, 'clear_cache'):
            config_manager.clear_cache()
        
        yield
        
        # Clear caches after test
        get_settings.cache_clear()
        if hasattr(config_manager, 'clear_cache'):
            config_manager.clear_cache()
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file for testing."""
        config_content = """
        DATABASE_URL=postgresql://test:test@localhost:5434/integration_test
        REDIS_URL=redis://localhost:6381/0
        JWT_SECRET_KEY=integration_test_secret_key_12345
        SERVICE_SECRET=integration_test_service_secret
        ENVIRONMENT=testing
        TESTING=1
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(config_content.strip())
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except:
            pass
    
    async def test_configuration_loading_from_environment(self, clean_config_cache):
        """Test configuration loading from environment variables."""
        # Set test environment variables
        test_env_vars = {
            "DATABASE_URL": "postgresql://envtest:envtest@localhost:5434/env_test_db",
            "REDIS_URL": "redis://localhost:6381/1",
            "JWT_SECRET_KEY": "env_jwt_secret_key_testing",
            "SERVICE_SECRET": "env_service_secret_testing",
            "ENVIRONMENT": "testing",
            "TESTING": "1"
        }
        
        with patch.dict(os.environ, test_env_vars, clear=False):
            config = get_unified_config()
            
            assert isinstance(config, AppConfig)
            assert config.database_url == test_env_vars["DATABASE_URL"]
            assert config.redis_url == test_env_vars["REDIS_URL"]
            assert config.jwt_secret_key == test_env_vars["JWT_SECRET_KEY"]
            assert config.service_secret == test_env_vars["SERVICE_SECRET"]
    
    async def test_configuration_loading_with_file_override(self, temp_config_file, clean_config_cache):
        """Test configuration loading with file overriding environment."""
        # Set environment variables
        env_vars = {
            "DATABASE_URL": "postgresql://env:env@localhost:5432/env_db",
            "JWT_SECRET_KEY": "env_jwt_secret"
        }
        
        # Load from file (should override environment)
        with patch.dict(os.environ, env_vars, clear=False):
            # Mock file loading (actual implementation may vary)
            with patch.object(Path, 'read_text', return_value=Path(temp_config_file).read_text()):
                config = get_unified_config()
                
                # File values should take precedence
                assert "integration_test" in config.database_url
                assert "integration_test_secret_key" in config.jwt_secret_key
    
    async def test_configuration_validation_success(self, clean_config_cache):
        """Test successful configuration validation."""
        valid_config_vars = {
            "DATABASE_URL": "postgresql://valid:valid@localhost:5434/valid_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "valid_jwt_secret_key_with_sufficient_length",
            "SERVICE_SECRET": "valid_service_secret_key_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "test_backend",
            "POSTGRES_DB": "backend_test_db"
        }
        
        with patch.dict(os.environ, valid_config_vars, clear=False):
            # Should not raise exception
            config = get_unified_config()
            assert isinstance(config, AppConfig)
            
            # Test configuration validation
            validate_test_config("backend", skip_on_failure=False)
    
    async def test_configuration_validation_failures(self, clean_config_cache):
        """Test configuration validation with invalid values."""
        invalid_config_vars = {
            "DATABASE_URL": "invalid_url",
            "JWT_SECRET_KEY": "short",  # Too short
            "ENVIRONMENT": "invalid_env",
            "TESTING": "0",  # Inconsistent with environment
            "POSTGRES_PORT": "invalid_port"
        }
        
        with patch.dict(os.environ, invalid_config_vars, clear=False):
            # Configuration validation should detect errors
            with pytest.raises(RuntimeError) as exc_info:
                validate_test_config("backend", skip_on_failure=False)
            
            error_message = str(exc_info.value)
            assert "validation failed" in error_message.lower()
    
    async def test_environment_specific_configuration_loading(self, clean_config_cache):
        """Test environment-specific configuration handling."""
        environments = [
            ("development", {"CLICKHOUSE_REQUIRED": "false", "DEBUG": "true"}),
            ("staging", {"CLICKHOUSE_REQUIRED": "false", "DEBUG": "false"}),
            ("testing", {"CLICKHOUSE_REQUIRED": "false", "DEBUG": "true"}),
        ]
        
        for env_name, env_specific_vars in environments:
            base_vars = {
                "DATABASE_URL": f"postgresql://test:test@localhost:5434/{env_name}_db",
                "REDIS_URL": "redis://localhost:6381/0",
                "JWT_SECRET_KEY": f"{env_name}_jwt_secret_key_sufficient_length",
                "SERVICE_SECRET": f"{env_name}_service_secret_sufficient_length",
                "ENVIRONMENT": env_name,
                "TESTING": "1" if env_name == "testing" else "0"
            }
            base_vars.update(env_specific_vars)
            
            with patch.dict(os.environ, base_vars, clear=False):
                config = get_unified_config()
                
                assert isinstance(config, AppConfig)
                assert env_name in config.database_url
                
                # Test environment-specific service enablement
                clickhouse_enabled = is_service_enabled("clickhouse")
                # ClickHouse should be disabled in all test environments
                assert not clickhouse_enabled or env_specific_vars["CLICKHOUSE_REQUIRED"] == "true"
    
    async def test_configuration_caching_behavior(self, clean_config_cache):
        """Test configuration caching and reload behavior."""
        initial_vars = {
            "DATABASE_URL": "postgresql://initial:initial@localhost:5434/initial_db",
            "JWT_SECRET_KEY": "initial_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "initial_service_secret_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1"
        }
        
        with patch.dict(os.environ, initial_vars, clear=False):
            # First load - should cache
            config1 = get_settings()
            config2 = get_settings()
            
            # Should be the same instance due to caching
            assert config1 is config2
            assert "initial" in config1.database_url
        
        # Change environment and reload
        updated_vars = initial_vars.copy()
        updated_vars["DATABASE_URL"] = "postgresql://updated:updated@localhost:5434/updated_db"
        
        with patch.dict(os.environ, updated_vars, clear=False):
            # Without reload, should still have cached version
            config3 = get_settings()
            assert config3 is config1  # Still cached
            
            # After reload, should get new values
            reload_config()
            config4 = get_settings()
            
            assert config4 is not config1  # New instance
            assert "updated" in config4.database_url
    
    async def test_cross_service_configuration_consistency(self, clean_config_cache):
        """Test configuration consistency across different services."""
        shared_config_vars = {
            "JWT_SECRET_KEY": "shared_jwt_secret_key_for_all_services",
            "SERVICE_SECRET": "shared_service_secret_for_all_services", 
            "ENVIRONMENT": "testing",
            "TESTING": "1",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381"
        }
        
        # Backend-specific configuration
        backend_vars = shared_config_vars.copy()
        backend_vars.update({
            "DATABASE_URL": "postgresql://backend:backend@localhost:5434/backend_test_db",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "test_backend",
            "POSTGRES_DB": "backend_test_db"
        })
        
        with patch.dict(os.environ, backend_vars, clear=False):
            backend_config = get_unified_config()
            
            # Test backend configuration
            assert isinstance(backend_config, AppConfig)
            assert backend_config.jwt_secret_key == shared_config_vars["JWT_SECRET_KEY"]
            assert "backend_test_db" in backend_config.database_url
            
            # Validate backend-specific configuration
            validate_test_config("backend", skip_on_failure=False)
        
        # Auth service configuration (simulate different service)
        auth_vars = shared_config_vars.copy()
        auth_vars.update({
            "DATABASE_URL": "postgresql://auth:auth@localhost:5435/auth_test_db",
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5435",
            "POSTGRES_USER": "test_auth",
            "POSTGRES_DB": "auth_test_db"
        })
        
        # Clear cache for auth service simulation
        get_settings.cache_clear()
        
        with patch.dict(os.environ, auth_vars, clear=False):
            # Simulate auth service configuration loading
            auth_config = get_unified_config()
            
            assert isinstance(auth_config, AppConfig)
            assert auth_config.jwt_secret_key == shared_config_vars["JWT_SECRET_KEY"]  # Shared secret
            assert "auth_test_db" in auth_config.database_url
            
            # Validate auth-specific configuration
            validate_test_config("auth", skip_on_failure=False)
    
    async def test_docker_vs_non_docker_configuration_handling(self, clean_config_cache):
        """Test Docker vs non-Docker configuration scenarios."""
        # Non-Docker configuration
        non_docker_vars = {
            "DATABASE_URL": "postgresql://local:local@localhost:5434/local_test_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "local_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "local_service_secret_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1",
            "POSTGRES_HOST": "localhost",
            "REDIS_HOST": "localhost",
            "USE_DOCKER_MODE": "false"
        }
        
        with patch.dict(os.environ, non_docker_vars, clear=False):
            local_config = get_unified_config()
            
            assert isinstance(local_config, AppConfig)
            assert "localhost" in local_config.database_url
            
            # Validate non-Docker configuration
            validate_test_config("backend", skip_on_failure=False)
        
        # Docker configuration
        get_settings.cache_clear()
        
        docker_vars = {
            "DATABASE_URL": "postgresql://docker:docker@test-postgres:5432/docker_test_db",
            "REDIS_URL": "redis://test-redis:6379/0",
            "JWT_SECRET_KEY": "docker_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "docker_service_secret_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1",
            "POSTGRES_HOST": "test-postgres",
            "REDIS_HOST": "test-redis",
            "USE_DOCKER_MODE": "true"
        }
        
        with patch.dict(os.environ, docker_vars, clear=False):
            docker_config = get_unified_config()
            
            assert isinstance(docker_config, AppConfig)
            assert "test-postgres" in docker_config.database_url
            
            # Validate Docker configuration
            validate_test_config("backend", skip_on_failure=False)
    
    async def test_configuration_security_and_sensitive_data(self, clean_config_cache):
        """Test handling of sensitive configuration data."""
        sensitive_vars = {
            "DATABASE_URL": "postgresql://sensitive:sensitive_pass@localhost:5434/secure_db",
            "JWT_SECRET_KEY": "very_secure_jwt_secret_key_with_sufficient_length_for_security",
            "SERVICE_SECRET": "very_secure_service_secret_key_with_sufficient_length",
            "OAUTH_CLIENT_SECRET": "oauth_client_secret_very_secure",
            "ENVIRONMENT": "testing",
            "TESTING": "1"
        }
        
        with patch.dict(os.environ, sensitive_vars, clear=False):
            config = get_unified_config()
            
            # Configuration should load sensitive data
            assert isinstance(config, AppConfig)
            assert len(config.jwt_secret_key) >= 32  # Minimum security requirement
            assert len(config.service_secret) >= 32
            
            # Test that sensitive data is not logged (if logging is implemented)
            # This would require integration with actual logging system
            
            # Validate that sensitive configuration meets security requirements
            validate_test_config("backend", skip_on_failure=False)
    
    async def test_configuration_error_handling_and_recovery(self, clean_config_cache):
        """Test configuration error handling and recovery mechanisms."""
        # Test missing required configuration
        incomplete_vars = {
            "ENVIRONMENT": "testing",
            "TESTING": "1"
            # Missing DATABASE_URL, JWT_SECRET_KEY, etc.
        }
        
        with patch.dict(os.environ, incomplete_vars, clear=True):
            # Configuration should handle missing values gracefully
            try:
                config = get_unified_config()
                # Should either provide defaults or fail gracefully
                assert isinstance(config, AppConfig)
            except Exception as e:
                # If it fails, the error should be informative
                assert "configuration" in str(e).lower() or "missing" in str(e).lower()
        
        # Test recovery with complete configuration
        complete_vars = {
            "DATABASE_URL": "postgresql://recovery:recovery@localhost:5434/recovery_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "recovery_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "recovery_service_secret_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1"
        }
        
        get_settings.cache_clear()
        
        with patch.dict(os.environ, complete_vars, clear=False):
            # Should recover and work normally
            recovered_config = get_unified_config()
            
            assert isinstance(recovered_config, AppConfig)
            assert "recovery" in recovered_config.database_url
            
            # Validation should pass after recovery
            validate_test_config("backend", skip_on_failure=False)
    
    async def test_configuration_with_service_specific_settings(self, clean_config_cache):
        """Test configuration with service-specific settings and overrides."""
        base_vars = {
            "DATABASE_URL": "postgresql://base:base@localhost:5434/base_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "base_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "base_service_secret_sufficient_length",
            "ENVIRONMENT": "testing",
            "TESTING": "1"
        }
        
        # Test analytics service specific settings
        analytics_vars = base_vars.copy()
        analytics_vars.update({
            "CLICKHOUSE_ENABLED": "true",
            "CLICKHOUSE_HOST": "localhost",
            "CLICKHOUSE_PORT": "8125",
            "CLICKHOUSE_DATABASE": "analytics_test_db",
            "ANALYTICS_ENABLED": "true",
            "POSTGRES_DB": "analytics_test_db"
        })
        
        with patch.dict(os.environ, analytics_vars, clear=False):
            analytics_config = get_unified_config()
            
            assert isinstance(analytics_config, AppConfig)
            
            # Test service-specific enablement
            clickhouse_enabled = is_service_enabled("clickhouse")
            assert clickhouse_enabled  # Should be enabled for analytics
            
            # Validate analytics-specific configuration
            validate_test_config("analytics", skip_on_failure=False)
        
        # Test backend service (ClickHouse optional)
        get_settings.cache_clear()
        
        backend_vars = base_vars.copy()
        backend_vars.update({
            "CLICKHOUSE_ENABLED": "false",
            "POSTGRES_DB": "backend_test_db"
        })
        
        with patch.dict(os.environ, backend_vars, clear=False):
            backend_config = get_unified_config()
            
            assert isinstance(backend_config, AppConfig)
            
            # ClickHouse should be disabled for backend
            clickhouse_enabled = is_service_enabled("clickhouse")
            assert not clickhouse_enabled
            
            # Validate backend-specific configuration
            validate_test_config("backend", skip_on_failure=False)
    
    async def test_configuration_reload_with_changed_environment(self, clean_config_cache):
        """Test configuration reload when environment changes significantly."""
        # Start with development environment
        dev_vars = {
            "DATABASE_URL": "postgresql://dev:dev@localhost:5434/dev_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "dev_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "dev_service_secret_sufficient_length",
            "ENVIRONMENT": "development",
            "TESTING": "0",
            "DEBUG": "true"
        }
        
        with patch.dict(os.environ, dev_vars, clear=False):
            dev_config = get_settings()
            
            assert isinstance(dev_config, AppConfig)
            assert "dev" in dev_config.database_url
        
        # Change to staging environment
        staging_vars = {
            "DATABASE_URL": "postgresql://staging:staging@localhost:5434/staging_db",
            "REDIS_URL": "redis://localhost:6381/1", 
            "JWT_SECRET_KEY": "staging_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "staging_service_secret_sufficient_length",
            "ENVIRONMENT": "staging",
            "TESTING": "0",
            "DEBUG": "false"
        }
        
        with patch.dict(os.environ, staging_vars, clear=False):
            # Reload configuration for new environment
            reload_config()
            staging_config = get_settings()
            
            assert staging_config is not dev_config  # Should be new instance
            assert "staging" in staging_config.database_url
            
            # Environment-specific behavior should change
            # (Implementation would depend on actual environment-specific logic)
            
        # Change back to testing environment
        test_vars = {
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
            "REDIS_URL": "redis://localhost:6381/2",
            "JWT_SECRET_KEY": "test_jwt_secret_key_sufficient_length",
            "SERVICE_SECRET": "test_service_secret_sufficient_length", 
            "ENVIRONMENT": "testing",
            "TESTING": "1",
            "DEBUG": "true"
        }
        
        with patch.dict(os.environ, test_vars, clear=False):
            reload_config()
            test_config = get_settings()
            
            assert test_config is not staging_config
            assert "test" in test_config.database_url
            
            # Test configuration should pass validation
            validate_test_config("backend", skip_on_failure=False)