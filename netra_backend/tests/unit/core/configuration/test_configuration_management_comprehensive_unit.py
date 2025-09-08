"""
Comprehensive Unit Tests for Configuration Management

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Prevent configuration-related system failures and outages
- Value Impact: Configuration reliability directly impacts system uptime and user experience
- Strategic Impact: Stable configuration management enables multi-environment deployments

This test suite validates:
1. Configuration loading and validation
2. Environment-specific configuration handling
3. Configuration caching and reload mechanisms
4. Error handling for missing or invalid configurations
5. Configuration security and validation
6. Multi-service configuration coordination
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, Optional

from netra_backend.app.core.config import get_settings, get_config, reload_config
from netra_backend.app.schemas.config import AppConfig
from test_framework.ssot.configuration_validator import (
    TestConfigurationValidator, 
    validate_test_config, 
    is_service_enabled,
    get_service_port
)
from shared.isolated_environment import get_env


class TestConfigurationManagementUnit:
    """Unit tests for configuration management systems."""
    
    @pytest.mark.unit
    def test_get_settings_returns_app_config(self):
        """Test get_settings returns valid AppConfig instance."""
        config = get_settings()
        
        assert isinstance(config, AppConfig)
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'redis_url')
        assert hasattr(config, 'jwt_secret_key')
    
    @pytest.mark.unit
    def test_get_config_alias_works(self):
        """Test get_config is proper alias for get_settings."""
        config1 = get_settings()
        config2 = get_config()
        
        # Should be the same due to caching
        assert config1 is config2
        assert isinstance(config1, AppConfig)
        assert isinstance(config2, AppConfig)
    
    @pytest.mark.unit
    @patch('netra_backend.app.core.config.get_unified_config')
    def test_get_settings_fallback_on_exception(self, mock_get_unified_config):
        """Test get_settings falls back to default AppConfig on exception."""
        mock_get_unified_config.side_effect = Exception("Configuration error")
        
        # Clear the cache first
        get_settings.cache_clear()
        
        config = get_settings()
        
        assert isinstance(config, AppConfig)
        mock_get_unified_config.assert_called_once()
    
    @pytest.mark.unit
    @patch('netra_backend.app.core.config.reload_unified_config')
    def test_reload_config_success(self, mock_reload_unified_config):
        """Test successful configuration reload."""
        # Setup cache with a value
        config1 = get_settings()
        
        # Reload configuration
        reload_config()
        
        # Verify reload was called and cache was cleared
        mock_reload_unified_config.assert_called_once()
        
        # New call should create fresh instance
        config2 = get_settings()
        assert isinstance(config2, AppConfig)
    
    @pytest.mark.unit
    @patch('netra_backend.app.core.config.reload_unified_config')
    def test_reload_config_graceful_failure(self, mock_reload_unified_config):
        """Test reload_config handles failures gracefully."""
        mock_reload_unified_config.side_effect = Exception("Reload failed")
        
        # Should not raise exception
        reload_config()
        
        # Cache should still be cleared
        config = get_settings()
        assert isinstance(config, AppConfig)
    
    @pytest.mark.unit
    def test_configuration_validator_initialization(self):
        """Test configuration validator initializes properly."""
        validator = TestConfigurationValidator()
        
        assert validator.env is not None
        assert validator.REQUIRED_TEST_VARS is not None
        assert validator.VALID_ENVIRONMENTS is not None
        assert validator.SERVICE_CONFIGS is not None
        assert validator.SERVICE_FLAGS is not None
        assert validator.PORT_ALLOCATION is not None
    
    @pytest.mark.unit
    def test_configuration_validator_required_test_vars(self):
        """Test configuration validator checks required variables."""
        validator = TestConfigurationValidator()
        
        # Mock environment with missing variables
        with patch.object(validator.env, 'get', return_value=None):
            is_valid, errors = validator.validate_test_environment()
            
            assert not is_valid
            assert any("Missing required test variables" in error for error in errors)
            assert any("REMEDY" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_valid_environment_values(self):
        """Test configuration validator accepts valid environment values."""
        validator = TestConfigurationValidator()
        
        valid_environments = ["testing", "test", "staging", "development", "dev"]
        
        for env_value in valid_environments:
            with patch.object(validator.env, 'get', side_effect=lambda key, default=None:
                            env_value if key == "ENVIRONMENT" else "1" if key == "TESTING" else "test"):
                
                is_valid, errors = validator.validate_test_environment()
                env_errors = [error for error in errors if "Invalid ENVIRONMENT value" in error]
                assert len(env_errors) == 0  # Should not have environment value errors
    
    @pytest.mark.unit
    def test_configuration_validator_invalid_environment_values(self):
        """Test configuration validator rejects invalid environment values."""
        validator = TestConfigurationValidator()
        
        invalid_environments = ["prod", "production", "live", ""]
        
        for env_value in invalid_environments:
            with patch.object(validator.env, 'get', side_effect=lambda key, default=None:
                            env_value if key == "ENVIRONMENT" else "test"):
                
                is_valid, errors = validator.validate_test_environment()
                env_errors = [error for error in errors if "Invalid ENVIRONMENT value" in error]
                assert len(env_errors) > 0
                assert any("REMEDY: Set ENVIRONMENT to 'testing'" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_testing_flag_consistency(self):
        """Test validator checks TESTING flag consistency with ENVIRONMENT."""
        validator = TestConfigurationValidator()
        
        # Test inconsistent flags
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "ENVIRONMENT": "testing",
            "TESTING": "0",  # Inconsistent!
            "JWT_SECRET_KEY": "test",
            "SERVICE_SECRET": "test"
        }.get(key, default)):
            
            is_valid, errors = validator.validate_test_environment()
            
            consistency_errors = [error for error in errors if "Inconsistent TESTING flag" in error]
            assert len(consistency_errors) > 0
            assert any("REMEDY: Set TESTING=1" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_database_url_validation(self):
        """Test database URL validation functionality."""
        validator = TestConfigurationValidator()
        
        # Test valid PostgreSQL URL
        valid_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch.object(validator.env, 'get', return_value=valid_url):
            is_valid, errors = validator.validate_database_configuration("backend")
            
            # Should not have URL format errors
            url_errors = [error for error in errors if "Invalid database URL" in error]
            assert len(url_errors) == 0
    
    @pytest.mark.unit
    def test_configuration_validator_invalid_database_url(self):
        """Test database URL validation rejects invalid URLs."""
        validator = TestConfigurationValidator()
        
        invalid_urls = [
            "invalid://url",
            "postgresql://",
            "postgresql://user@localhost",  # Missing database
            "mysql://user:pass@localhost:3306/db"  # Invalid scheme
        ]
        
        for invalid_url in invalid_urls:
            with patch.object(validator.env, 'get', return_value=invalid_url):
                is_valid, errors = validator.validate_database_configuration("backend")
                
                # Should have URL validation errors
                url_errors = [error for error in errors if any(keyword in error for keyword in 
                             ["Invalid database URL", "missing", "Invalid", "REMEDY"])]
                assert len(url_errors) > 0
    
    @pytest.mark.unit
    def test_configuration_validator_service_port_allocation(self):
        """Test service port allocation validation."""
        validator = TestConfigurationValidator()
        
        # Test expected ports for different services
        backend_port = validator.get_service_port("backend", "postgres")
        auth_port = validator.get_service_port("auth", "postgres")
        analytics_port = validator.get_service_port("analytics", "postgres")
        
        assert backend_port == 5434
        assert auth_port == 5435
        assert analytics_port == 5436
        
        # Test Redis port calculation
        backend_redis = validator.get_service_port("backend", "redis")
        assert backend_redis == 6434  # PostgreSQL port + 1000
    
    @pytest.mark.unit
    def test_configuration_validator_service_enabled_logic(self):
        """Test service enabled/disabled logic."""
        validator = TestConfigurationValidator()
        
        # Test ClickHouse disabled by default
        with patch.object(validator.env, 'get', return_value="false"):
            assert not validator.is_service_enabled("clickhouse")
        
        # Test explicit enable
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None:
                        "true" if key == "CLICKHOUSE_ENABLED" else "false"):
            assert validator.is_service_enabled("clickhouse")
        
        # Test explicit disable overrides enable
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "CLICKHOUSE_ENABLED": "true",
            "TEST_DISABLE_CLICKHOUSE": "true"
        }.get(key, "false")):
            assert not validator.is_service_enabled("clickhouse")
    
    @pytest.mark.unit
    def test_configuration_validator_docker_mode_detection(self):
        """Test Docker mode detection logic."""
        validator = TestConfigurationValidator()
        
        # Test Docker mode detection with service names
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "POSTGRES_HOST": "test-postgres",
            "REDIS_HOST": "test-redis"
        }.get(key, "localhost")):
            
            is_docker = validator._detect_docker_mode()
            assert is_docker is True
        
        # Test non-Docker mode detection
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "POSTGRES_HOST": "localhost", 
            "REDIS_HOST": "localhost"
        }.get(key, "localhost")):
            
            is_docker = validator._detect_docker_mode()
            assert is_docker is False
    
    @pytest.mark.unit
    def test_configuration_validator_docker_config_consistency(self):
        """Test Docker configuration consistency validation."""
        validator = TestConfigurationValidator()
        
        # Test Docker mode with correct service names
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "POSTGRES_HOST": "test-postgres",
            "REDIS_HOST": "test-redis"
        }.get(key, "localhost")):
            
            is_valid, errors = validator.validate_docker_configuration(use_docker=True)
            
            # Should not have Docker configuration errors
            docker_errors = [error for error in errors if "Docker mode" in error]
            assert len(docker_errors) == 0
    
    @pytest.mark.unit
    def test_configuration_validator_service_flag_conflicts(self):
        """Test service flag conflict detection."""
        validator = TestConfigurationValidator()
        
        # Test conflicting service flags
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "REDIS_ENABLED": "true",
            "TEST_DISABLE_REDIS": "true"  # Conflict!
        }.get(key, "false")):
            
            is_valid, errors = validator.validate_service_flags()
            
            # Should detect flag conflicts
            conflict_errors = [error for error in errors if "Conflicting" in error and "redis" in error.lower()]
            assert len(conflict_errors) > 0
            assert any("REMEDY" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_global_flag_conflicts(self):
        """Test global flag conflict detection."""
        validator = TestConfigurationValidator()
        
        # Test conflicting global flags
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "USE_REAL_SERVICES": "true",
            "SKIP_MOCKS": "true"  # Conflict!
        }.get(key, "false")):
            
            is_valid, errors = validator.validate_service_flags()
            
            # Should detect global flag conflicts
            conflict_errors = [error for error in errors if "Cannot use real services and skip mocks" in error]
            assert len(conflict_errors) > 0
    
    @pytest.mark.unit
    def test_validate_test_config_helper_function(self):
        """Test validate_test_config helper function."""
        # Mock a successful validation
        with patch('test_framework.ssot.configuration_validator.get_config_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.validate_test_environment.return_value = (True, [])
            mock_validator.validate_database_configuration.return_value = (True, [])
            mock_validator.validate_service_flags.return_value = (True, [])
            mock_validator.validate_docker_configuration.return_value = (True, [])
            mock_get_validator.return_value = mock_validator
            
            # Should not raise exception
            validate_test_config("backend", skip_on_failure=False)
            
            # Verify all validation methods were called
            mock_validator.validate_test_environment.assert_called_once_with("backend")
            mock_validator.validate_database_configuration.assert_called_once_with("backend")
            mock_validator.validate_service_flags.assert_called_once()
            mock_validator.validate_docker_configuration.assert_called_once()
    
    @pytest.mark.unit
    def test_validate_test_config_failure_handling(self):
        """Test validate_test_config handles failures appropriately."""
        with patch('test_framework.ssot.configuration_validator.get_config_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.validate_test_environment.return_value = (False, ["Environment error"])
            mock_validator.validate_database_configuration.return_value = (True, [])
            mock_validator.validate_service_flags.return_value = (True, [])
            mock_validator.validate_docker_configuration.return_value = (True, [])
            mock_get_validator.return_value = mock_validator
            
            # Should raise RuntimeError when skip_on_failure=False
            with pytest.raises(RuntimeError) as exc_info:
                validate_test_config("backend", skip_on_failure=False)
            
            assert "Test configuration validation failed" in str(exc_info.value)
            assert "Environment error" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_is_service_enabled_helper_function(self):
        """Test is_service_enabled helper function."""
        with patch('test_framework.ssot.configuration_validator.get_config_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.is_service_enabled.return_value = True
            mock_get_validator.return_value = mock_validator
            
            result = is_service_enabled("redis")
            
            assert result is True
            mock_validator.is_service_enabled.assert_called_once_with("redis")
    
    @pytest.mark.unit
    def test_get_service_port_helper_function(self):
        """Test get_service_port helper function."""
        with patch('test_framework.ssot.configuration_validator.get_config_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.get_service_port.return_value = 5434
            mock_get_validator.return_value = mock_validator
            
            result = get_service_port("backend", "postgres")
            
            assert result == 5434
            mock_validator.get_service_port.assert_called_once_with("backend", "postgres")
    
    @pytest.mark.unit
    def test_configuration_validator_singleton_behavior(self):
        """Test configuration validator singleton behavior."""
        from test_framework.ssot.configuration_validator import get_config_validator
        
        validator1 = get_config_validator()
        validator2 = get_config_validator()
        
        # Should be the same instance
        assert validator1 is validator2
        assert isinstance(validator1, TestConfigurationValidator)
    
    @pytest.mark.unit
    def test_configuration_validator_port_conflict_detection(self):
        """Test port conflict detection in validator."""
        validator = TestConfigurationValidator()
        
        # Test port conflict detection
        conflicting_port = 5434  # Allocated to backend
        errors = validator._validate_port_allocation(conflicting_port, "auth")
        
        # Should detect conflict
        conflict_errors = [error for error in errors if "Port conflict" in error]
        assert len(conflict_errors) > 0
        assert any("allocated to 'backend'" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_service_specific_validation(self):
        """Test service-specific configuration validation."""
        validator = TestConfigurationValidator()
        
        # Test analytics service requiring ClickHouse
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "CLICKHOUSE_ENABLED": "false"
        }.get(key, default)):
            
            errors = validator._validate_service_config("analytics")
            
            # Should detect ClickHouse requirement violation
            ch_errors = [error for error in errors if "requires ClickHouse" in error]
            assert len(ch_errors) > 0
            assert any("REMEDY: Set CLICKHOUSE_ENABLED=true" in error for error in errors)
    
    @pytest.mark.unit
    def test_configuration_validator_database_name_validation(self):
        """Test database name validation for services."""
        validator = TestConfigurationValidator()
        
        # Test database name pattern validation
        with patch.object(validator.env, 'get', side_effect=lambda key, default=None: {
            "POSTGRES_DB": "wrong_db_name"  # Doesn't contain expected pattern
        }.get(key, default)):
            
            errors = validator._validate_service_config("backend")
            
            # Should detect database name mismatch
            db_errors = [error for error in errors if "Database name mismatch" in error]
            assert len(db_errors) > 0
            assert any("backend_test_db" in error for error in errors)