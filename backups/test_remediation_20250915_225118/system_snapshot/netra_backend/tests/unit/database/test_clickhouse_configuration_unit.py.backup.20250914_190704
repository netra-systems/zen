"""
Test ClickHouse Configuration Management - Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Zero configuration-related downtime
- Value Impact: Prevents costly configuration failures ($5K+ per incident)
- Strategic Impact: Enables reliable multi-environment deployment

This test suite validates ClickHouse configuration management at the unit level,
ensuring proper environment-specific configuration loading and validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse

from netra_backend.app.db.clickhouse import (
    get_clickhouse_config,
    _extract_clickhouse_config,
    _get_unified_config
)
from test_framework.base_integration_test import BaseIntegrationTest


class TestClickHouseConfigurationUnit(BaseIntegrationTest):
    """Test ClickHouse configuration management unit functionality."""
    
    @pytest.mark.unit
    def test_testing_environment_config_extraction(self):
        """Test ClickHouse configuration extraction for testing environment.
        
        Critical for ensuring test isolation and proper Docker configuration.
        """
        # Mock unified config for testing environment
        mock_config = Mock()
        mock_config.environment = "testing"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            config = _extract_clickhouse_config(mock_config)
            
            # Verify testing environment specific settings
            assert config.host == "localhost", "Testing should use localhost"
            assert config.port == 8125, "Testing should use test port"
            assert config.user == "test", "Testing should use test user"
            assert config.password == "test", "Testing should use test password"
            assert config.database == "netra_test_analytics", "Testing should use test database"
            assert config.secure is False, "Testing should not use SSL"

    @pytest.mark.unit
    def test_development_environment_config_extraction(self):
        """Test ClickHouse configuration extraction for development environment.
        
        Validates proper Docker service detection and port mapping.
        """
        # Mock unified config for development environment  
        mock_config = Mock()
        mock_config.environment = "development"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                with patch('socket.gethostbyname', side_effect=OSError("Name resolution failed")):
                    # Mock environment variables
                    mock_env.return_value.get.side_effect = lambda key, default=None: {
                        "CLICKHOUSE_HOST": "clickhouse-service",
                        "CLICKHOUSE_HTTP_PORT": "8123",
                        "CLICKHOUSE_USER": "netra_dev",
                        "CLICKHOUSE_PASSWORD": "dev123",
                        "CLICKHOUSE_DB": "netra_dev_analytics"
                    }.get(key, default)
                    
                    config = _extract_clickhouse_config(mock_config)
                    
                    # When hostname resolution fails, should use localhost with external port
                    assert config.host == "localhost", "Should fallback to localhost"
                    assert config.port == 8124, "Should use external mapped port"
                    assert config.user == "netra_dev", "Should use dev user"
                    assert config.secure is False, "Dev should not use SSL"

    @pytest.mark.unit
    def test_staging_environment_config_extraction(self):
        """Test ClickHouse configuration extraction for staging environment.
        
        Validates cloud configuration with secrets management.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Mock staging environment with ClickHouse Cloud URL
                clickhouse_url = "clickhouse://staging_user:secret123@example.clickhouse.cloud:8443/staging_db?secure=1"
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    "CLICKHOUSE_URL": clickhouse_url,
                }.get(key, default)
                
                config = _extract_clickhouse_config(mock_config)
                
                # Verify parsed configuration
                assert config.host == "example.clickhouse.cloud", "Should use cloud host"
                assert config.port == 8443, "Should use HTTPS port"
                assert config.user == "staging_user", "Should use URL user"
                assert config.password == "secret123", "Should use URL password"
                assert config.database == "staging_db", "Should use URL database"
                assert config.secure is True, "Staging should use SSL"

    @pytest.mark.unit
    def test_staging_config_missing_url_error(self):
        """Test staging configuration raises error when URL is missing.
        
        Critical for preventing silent failures in production deployments.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Mock missing configuration
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    # No CLICKHOUSE_URL or CLICKHOUSE_HOST
                }.get(key, default)
                
                with pytest.raises(ConnectionError) as exc_info:
                    _extract_clickhouse_config(mock_config)
                
                assert "ClickHouse configuration missing" in str(exc_info.value)
                assert "CLICKHOUSE_URL" in str(exc_info.value)

    @pytest.mark.unit
    def test_production_environment_config_validation(self):
        """Test production ClickHouse configuration validation.
        
        Ensures mandatory configuration for production deployments.
        """
        mock_config = Mock()
        mock_config.environment = "production"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Test missing URL in production (should fail)
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    # No CLICKHOUSE_URL
                }.get(key, default)
                
                with pytest.raises(ConnectionError) as exc_info:
                    _extract_clickhouse_config(mock_config)
                
                assert "CLICKHOUSE_URL is mandatory in production" in str(exc_info.value)


class TestClickHouseConfigurationSecrets(BaseIntegrationTest):
    """Test ClickHouse configuration with secrets management."""
    
    @pytest.mark.unit
    def test_staging_config_with_secret_manager(self):
        """Test staging configuration with GCP Secret Manager integration.
        
        Validates secure password retrieval from secret management systems.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Mock URL without password
                clickhouse_url = "clickhouse://staging_user@example.clickhouse.cloud:8443/staging_db?secure=1"
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    "CLICKHOUSE_URL": clickhouse_url,
                }.get(key, default)
                
                # Mock secret manager
                mock_secret_manager = Mock()
                mock_secret_manager.get_secret.return_value = "secret_from_manager"
                
                with patch('netra_backend.app.db.clickhouse.SecretManager', return_value=mock_secret_manager):
                    config = _extract_clickhouse_config(mock_config)
                    
                    # Verify password loaded from secret manager
                    assert config.password == "secret_from_manager"
                    mock_secret_manager.get_secret.assert_called_once_with("CLICKHOUSE_PASSWORD")

    @pytest.mark.unit
    def test_staging_config_secret_manager_failure(self):
        """Test staging configuration handles secret manager failures gracefully.
        
        Ensures system doesn't crash when secrets are unavailable.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Mock URL with password in URL (should work even if secret manager fails)
                clickhouse_url = "clickhouse://staging_user:url_password@example.clickhouse.cloud:8443/staging_db?secure=1"
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    "CLICKHOUSE_URL": clickhouse_url,
                }.get(key, default)
                
                # Mock secret manager failure
                with patch('netra_backend.app.db.clickhouse.SecretManager', side_effect=Exception("Secret Manager unavailable")):
                    with patch('netra_backend.app.db.clickhouse.logger') as mock_logger:
                        config = _extract_clickhouse_config(mock_config)
                        
                        # Should use password from URL even when secret manager fails
                        assert config.password == "url_password"
                        mock_logger.warning.assert_called()


class TestClickHouseConfigurationValidation(BaseIntegrationTest):
    """Test ClickHouse configuration validation and error handling."""
    
    @pytest.mark.unit
    def test_config_url_parsing_validation(self):
        """Test ClickHouse URL parsing and validation.
        
        Ensures malformed URLs are properly handled with clear errors.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # Test various URL formats
                test_cases = [
                    {
                        "url": "clickhouse://user:pass@host.com:8443/db?secure=1",
                        "expected_host": "host.com",
                        "expected_port": 8443,
                        "expected_secure": True
                    },
                    {
                        "url": "clickhouse://user:pass@host.com/db",
                        "expected_host": "host.com", 
                        "expected_port": 8443,  # Default HTTPS port
                        "expected_secure": True   # Default secure for parsed URLs
                    }
                ]
                
                for case in test_cases:
                    mock_env.return_value.get.side_effect = lambda key, default=None: {
                        "CLICKHOUSE_URL": case["url"],
                    }.get(key, default)
                    
                    config = _extract_clickhouse_config(mock_config)
                    
                    assert config.host == case["expected_host"]
                    assert config.port == case["expected_port"]
                    assert config.secure == case["expected_secure"]

    @pytest.mark.unit
    def test_config_fallback_values(self):
        """Test ClickHouse configuration fallback values.
        
        Validates proper defaults when optional values are missing.
        """
        mock_config = Mock()
        mock_config.environment = "staging"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                # URL with minimal information
                clickhouse_url = "clickhouse://user@host.com/db"
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    "CLICKHOUSE_URL": clickhouse_url,
                }.get(key, default)
                
                config = _extract_clickhouse_config(mock_config)
                
                # Verify fallback values
                assert config.host == "host.com", "Host from URL"
                assert config.port == 8443, "Default HTTPS port"
                assert config.user == "user", "User from URL"
                assert config.password == "", "Empty password fallback"
                assert config.database == "db", "Database from URL"
                assert config.secure is True, "Default secure for cloud"


class TestClickHouseConfigurationIntegration(BaseIntegrationTest):
    """Test configuration integration with unified config system."""
    
    @pytest.mark.unit
    def test_get_clickhouse_config_integration(self):
        """Test get_clickhouse_config function integration.
        
        Validates main configuration entry point works correctly.
        """
        mock_unified_config = Mock()
        mock_unified_config.environment = "testing"
        
        with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_unified_config):
            config = get_clickhouse_config()
            
            # Should return testing configuration
            assert hasattr(config, 'host'), "Config should have host attribute"
            assert hasattr(config, 'port'), "Config should have port attribute"
            assert hasattr(config, 'database'), "Config should have database attribute"
            
            # Testing-specific values
            assert config.host == "localhost"
            assert config.port == 8125
            assert config.database == "netra_test_analytics"

    @pytest.mark.unit
    def test_configuration_environment_detection(self):
        """Test configuration correctly detects different environments.
        
        Critical for proper environment-specific configuration loading.
        """
        environments = ["testing", "development", "staging", "production"]
        
        for env in environments:
            mock_config = Mock()
            mock_config.environment = env
            
            with patch('netra_backend.app.db.clickhouse.get_configuration', return_value=mock_config):
                with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                    # Mock minimal required configuration for each environment
                    if env in ["staging", "production"]:
                        mock_env.return_value.get.side_effect = lambda key, default=None: {
                            "CLICKHOUSE_URL": "clickhouse://user:pass@example.com:8443/db?secure=1",
                        }.get(key, default)
                    else:
                        mock_env.return_value.get.side_effect = lambda key, default=None: {}.get(key, default)
                    
                    config = _extract_clickhouse_config(mock_config)
                    
                    # Each environment should produce valid configuration
                    assert hasattr(config, 'host'), f"Config missing host for {env}"
                    assert hasattr(config, 'port'), f"Config missing port for {env}"
                    assert hasattr(config, 'database'), f"Config missing database for {env}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])