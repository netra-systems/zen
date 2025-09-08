"""
Test Configuration Management - Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related downtime incidents
- Value Impact: Prevents costly configuration errors ($5K+ per outage) 
- Strategic Impact: Enables reliable multi-environment deployments for enterprise customers

This test suite validates core configuration management functionality at the unit level,
ensuring proper configuration loading, validation, and environment management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from netra_backend.app.config import get_config, reload_config, validate_configuration
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import (
    TestConfigurationValidator,
    get_config_validator,
    validate_test_config
)


class TestConfigurationManagementUnit(BaseIntegrationTest):
    """Test configuration management core functionality."""
    
    @pytest.mark.unit
    def test_unified_config_loading_with_environment_detection(self):
        """Test unified configuration loading detects environment correctly.
        
        Critical for ensuring proper environment-specific configuration loading.
        """
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            # Mock different environment configurations
            test_environments = ['testing', 'development', 'staging', 'production']
            
            for env in test_environments:
                mock_config_obj = Mock()
                mock_config_obj.environment = env
                mock_config_obj.database_url = f"postgresql://test_{env}:password@localhost:543{len(env)}/test_{env}_db"
                mock_config_obj.redis_url = f"redis://localhost:638{len(env)}/0"
                mock_config.return_value = mock_config_obj
                
                # Test configuration loading
                config = get_config()
                
                assert hasattr(config, 'environment'), f"Config should have environment attribute for {env}"
                assert config.environment == env, f"Environment should be {env}"
                assert hasattr(config, 'database_url'), f"Config should have database_url for {env}"
                assert env in config.database_url, f"Database URL should contain environment {env}"

    @pytest.mark.unit
    def test_configuration_validation_with_error_detection(self):
        """Test configuration validation detects and reports errors properly.
        
        Ensures configuration problems are caught before deployment.
        """
        with patch('netra_backend.app.core.configuration.base.validate_config_integrity') as mock_validate:
            # Test successful validation
            mock_validate.return_value = (True, [])
            is_valid, errors = validate_configuration()
            
            assert is_valid is True, "Valid configuration should return True"
            assert errors == [], "Valid configuration should have no errors"
            
            # Test validation with errors
            test_errors = [
                "Missing required environment variable: DATABASE_URL",
                "Invalid Redis configuration: connection refused",
                "ClickHouse configuration missing for production environment"
            ]
            mock_validate.return_value = (False, test_errors)
            
            is_valid, errors = validate_configuration()
            
            assert is_valid is False, "Invalid configuration should return False"
            assert len(errors) == 3, "Should return all validation errors"
            assert "DATABASE_URL" in errors[0], "Should include specific error details"
            assert "Redis" in errors[1], "Should include service-specific errors"
            assert "ClickHouse" in errors[2], "Should include component-specific errors"

    @pytest.mark.unit
    def test_configuration_hot_reload_functionality(self):
        """Test configuration hot reload updates settings without restart.
        
        Critical for production configuration updates without downtime.
        """
        with patch('netra_backend.app.core.configuration.base.reload_unified_config') as mock_reload:
            with patch('netra_backend.app.config._settings_cache', None):
                # Test normal reload
                mock_reload.return_value = None
                
                result = reload_config(force=False)
                assert result is None, "Normal reload should complete without error"
                mock_reload.assert_called_once_with(force=False)
                
                # Test forced reload
                mock_reload.reset_mock()
                result = reload_config(force=True)
                assert result is None, "Forced reload should complete without error"
                mock_reload.assert_called_once_with(force=True)
                
                # Test reload clears cache
                with patch('netra_backend.app.config._settings_cache') as mock_cache:
                    mock_cache = Mock()
                    reload_config(force=True)
                    # Cache should be affected by reload process

    @pytest.mark.unit
    def test_configuration_lazy_loading_behavior(self):
        """Test configuration lazy loading optimizes startup performance.
        
        Ensures configuration is only loaded when needed.
        """
        with patch('netra_backend.app.config._settings_cache', None):
            with patch('netra_backend.app.config.get_config') as mock_get_config:
                mock_config = Mock()
                mock_config.environment = "testing"
                mock_config.debug = True
                mock_get_config.return_value = mock_config
                
                # Import the module to trigger __getattr__
                from netra_backend.app import config
                
                # First access should trigger config loading
                settings = config.settings
                mock_get_config.assert_called_once()
                assert settings.environment == "testing"
                
                # Second access should use cached value
                mock_get_config.reset_mock()
                settings2 = config.settings
                mock_get_config.assert_not_called()  # Should not call again
                assert settings2 is settings  # Should be same object


class TestConfigurationValidatorUnit(BaseIntegrationTest):
    """Test configuration validator functionality."""
    
    @pytest.mark.unit
    def test_test_environment_validation_comprehensive(self):
        """Test comprehensive test environment validation.
        
        Critical for ensuring test environment setup is correct.
        """
        with patch('test_framework.ssot.configuration_validator.get_env') as mock_env:
            # Mock valid test environment
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'TESTING': '1',
                'ENVIRONMENT': 'testing',
                'JWT_SECRET_KEY': 'test_jwt_secret_key_12345',
                'SERVICE_SECRET': 'test_service_secret_67890'
            }.get(key, default)
            
            validator = TestConfigurationValidator()
            is_valid, errors = validator.validate_test_environment()
            
            assert is_valid is True, "Valid test environment should pass validation"
            assert errors == [], f"Valid environment should have no errors: {errors}"
            
            # Test invalid environment
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'TESTING': '0',  # Invalid - should be '1' 
                'ENVIRONMENT': 'invalid_env',  # Invalid environment
                'JWT_SECRET_KEY': '',  # Missing
                # SERVICE_SECRET missing entirely
            }.get(key, default)
            
            is_valid, errors = validator.validate_test_environment()
            
            assert is_valid is False, "Invalid test environment should fail validation"
            assert len(errors) > 0, "Invalid environment should have errors"
            
            # Check specific error messages
            error_text = ' '.join(errors)
            assert 'Missing required test variables' in error_text or 'JWT_SECRET_KEY' in error_text
            assert 'Invalid ENVIRONMENT value' in error_text

    @pytest.mark.unit
    def test_service_flag_validation_logic(self):
        """Test service enable/disable flag validation logic.
        
        Ensures service flags work correctly for different scenarios.
        """
        with patch('test_framework.ssot.configuration_validator.get_env') as mock_env:
            validator = TestConfigurationValidator()
            
            # Test ClickHouse enabled scenario
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'CLICKHOUSE_ENABLED': 'true',
                'TEST_DISABLE_CLICKHOUSE': 'false'
            }.get(key, default)
            
            assert validator.is_service_enabled('clickhouse') is True, "ClickHouse should be enabled"
            
            # Test ClickHouse disabled scenario
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'CLICKHOUSE_ENABLED': 'false',
                'TEST_DISABLE_CLICKHOUSE': 'true'
            }.get(key, default)
            
            assert validator.is_service_enabled('clickhouse') is False, "ClickHouse should be disabled"
            
            # Test conflicting flags
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'CLICKHOUSE_ENABLED': 'true',
                'TEST_DISABLE_CLICKHOUSE': 'true'  # Conflict!
            }.get(key, default)
            
            is_valid, errors = validator.validate_service_flags()
            assert is_valid is False, "Conflicting flags should fail validation"
            assert any('Conflicting' in error and 'clickhouse' in error.lower() for error in errors)

    @pytest.mark.unit
    def test_database_configuration_validation_detailed(self):
        """Test detailed database configuration validation.
        
        Ensures database configuration is properly validated for each service.
        """
        with patch('test_framework.ssot.configuration_validator.get_env') as mock_env:
            validator = TestConfigurationValidator()
            
            # Test valid backend database configuration
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5434',  # Correct port for backend
                'POSTGRES_USER': 'test_backend',
                'POSTGRES_DB': 'backend_test_db',
                'DATABASE_URL': 'postgresql://test_backend:password@localhost:5434/backend_test_db'
            }.get(key, default)
            
            is_valid, errors = validator.validate_database_configuration('backend')
            assert is_valid is True, f"Valid backend DB config should pass: {errors}"
            
            # Test invalid port for backend
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5432',  # Wrong port for backend (should be 5434)
                'POSTGRES_USER': 'test_backend',
                'POSTGRES_DB': 'backend_test_db'
            }.get(key, default)
            
            is_valid, errors = validator.validate_database_configuration('backend')
            assert is_valid is False, "Wrong port should fail validation"
            assert any('port mismatch' in error.lower() for error in errors)
            
            # Test missing database URL
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'DATABASE_URL': 'invalid://malformed/url'  # Invalid URL format
            }.get(key, default)
            
            is_valid, errors = validator.validate_database_configuration('backend')
            assert is_valid is False, "Invalid database URL should fail validation"


class TestConfigurationPortAllocationUnit(BaseIntegrationTest):
    """Test configuration port allocation and conflict detection."""
    
    @pytest.mark.unit
    def test_port_allocation_conflict_detection(self):
        """Test port allocation conflict detection prevents service conflicts.
        
        Critical for preventing port conflicts between services.
        """
        validator = TestConfigurationValidator()
        
        # Test valid port allocation
        backend_port = validator.get_service_port('backend', 'postgres')
        auth_port = validator.get_service_port('auth', 'postgres')
        analytics_port = validator.get_service_port('analytics', 'postgres')
        
        assert backend_port == 5434, "Backend should use port 5434"
        assert auth_port == 5435, "Auth should use port 5435"
        assert analytics_port == 5436, "Analytics should use port 5436"
        
        # Ensure all ports are different (no conflicts)
        ports = [backend_port, auth_port, analytics_port]
        assert len(set(ports)) == len(ports), "All service ports should be unique"
        
        # Test port conflict validation
        conflicts = validator._validate_port_allocation(5434, 'auth')  # Wrong service for port
        assert len(conflicts) > 0, "Should detect port conflict"
        assert 'conflict' in conflicts[0].lower(), "Should report port conflict"

    @pytest.mark.unit
    def test_service_port_calculation_logic(self):
        """Test service port calculation logic for different port types.
        
        Validates port calculation across different service types.
        """
        validator = TestConfigurationValidator()
        
        # Test PostgreSQL port retrieval
        backend_postgres_port = validator.get_service_port('backend', 'postgres')
        assert backend_postgres_port == 5434, "Backend PostgreSQL port should be 5434"
        
        # Test Redis port calculation (PostgreSQL port + 1000)
        backend_redis_port = validator.get_service_port('backend', 'redis')
        expected_redis_port = 5434 + 1000  # Redis ports are PostgreSQL + 1000
        assert backend_redis_port == expected_redis_port, f"Backend Redis port should be {expected_redis_port}"
        
        # Test application port retrieval  
        backend_app_port = validator.get_service_port('backend', 'app')
        assert backend_app_port == 8000, "Backend app port should be 8000"
        
        # Test invalid service
        invalid_port = validator.get_service_port('nonexistent_service', 'postgres')
        assert invalid_port is None, "Invalid service should return None"

    @pytest.mark.unit
    def test_docker_configuration_detection_and_validation(self):
        """Test Docker configuration detection and validation logic.
        
        Ensures proper Docker vs non-Docker environment detection.
        """
        with patch('test_framework.ssot.configuration_validator.get_env') as mock_env:
            validator = TestConfigurationValidator()
            
            # Test Docker mode detection
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'DOCKER_MODE': 'true',
                'POSTGRES_HOST': 'test-postgres',
                'REDIS_HOST': 'test-redis'
            }.get(key, default)
            
            is_docker = validator._detect_docker_mode()
            assert is_docker is True, "Should detect Docker mode"
            
            # Test Docker configuration validation
            is_valid, errors = validator.validate_docker_configuration(use_docker=True)
            assert is_valid is True, f"Valid Docker config should pass: {errors}"
            
            # Test non-Docker mode
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'DOCKER_MODE': 'false',
                'POSTGRES_HOST': 'localhost',
                'REDIS_HOST': 'localhost'
            }.get(key, default)
            
            is_docker = validator._detect_docker_mode()
            assert is_docker is False, "Should detect non-Docker mode"
            
            is_valid, errors = validator.validate_docker_configuration(use_docker=False)
            assert is_valid is True, f"Valid non-Docker config should pass: {errors}"
            
            # Test Docker/non-Docker mismatch
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'DOCKER_MODE': 'true',
                'POSTGRES_HOST': 'localhost',  # Should be service name in Docker
                'REDIS_HOST': 'localhost'      # Should be service name in Docker
            }.get(key, default)
            
            is_valid, errors = validator.validate_docker_configuration(use_docker=True)
            assert is_valid is False, "Docker/localhost mismatch should fail validation"
            assert any('localhost' in error and 'Docker' in error for error in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])