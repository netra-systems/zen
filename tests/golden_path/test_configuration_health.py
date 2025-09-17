"""
Emergency Golden Path Test: Configuration Health Core
Critical test for validating system configuration for Golden Path.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

# Use absolute imports as required by SSOT
from netra_backend.app.config import get_config
from netra_backend.app.core.configuration.validator import ConfigValidator
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestConfigurationHealth(SSotBaseTestCase):
    """Emergency test for core configuration validation that enables Golden Path system health."""
    
    def setUp(self):
        """Set up test environment with isolated configuration."""
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        
        # Set minimal required configuration
        self.env.set("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
        self.env.set("REDIS_HOST", "localhost")
        self.env.set("REDIS_PORT", "6379")
        self.env.set("JWT_SECRET", "test-secret-key")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081")
        
    def test_configuration_loads_successfully(self):
        """Test that system configuration loads without errors."""
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config)
        self.assertEqual(config.environment, "test")
        
    def test_database_configuration_valid(self):
        """Test that database configuration is properly set."""
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.database_url)
        self.assertIn("postgresql", config.database_url)
        
    def test_redis_configuration_valid(self):
        """Test that Redis configuration is properly set."""
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.redis_host)
        self.assertIsNotNone(config.redis_port)
        self.assertEqual(config.redis_host, "localhost")
        self.assertEqual(config.redis_port, 6379)
        
    def test_auth_configuration_valid(self):
        """Test that authentication configuration is properly set."""
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.jwt_secret)
        self.assertIsNotNone(config.auth_service_url)
        self.assertEqual(config.auth_service_url, "http://localhost:8081")
        
    def test_configuration_validator_passes(self):
        """Test that configuration validator passes for test environment."""
        # Arrange
        validator = ConfigValidator()
        config = get_config()
        
        # Act
        validation_result = validator.validate_configuration(config)
        
        # Assert
        self.assertTrue(validation_result.is_valid)
        self.assertEqual(len(validation_result.errors), 0)
        
    def test_missing_critical_configuration_detected(self):
        """Test that missing critical configuration is properly detected."""
        # Arrange - Remove critical config
        with patch.object(self.env, 'get', return_value=None):
            # Act & Assert
            with self.assertRaises(Exception) as context:
                config = get_config()
                
            self.assertIn("configuration", str(context.exception).lower())
            
    def test_environment_specific_configuration(self):
        """Test that environment-specific configuration works correctly."""
        # Test environment
        config = get_config()
        self.assertEqual(config.environment, "test")
        
        # Test development environment
        self.env.set("ENVIRONMENT", "development")
        with patch('netra_backend.app.config.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.environment = "development"
            mock_get_config.return_value = mock_config
            
            dev_config = get_config()
            self.assertEqual(dev_config.environment, "development")
            
    def test_configuration_caching_works(self):
        """Test that configuration is properly cached for performance."""
        # Act
        config1 = get_config()
        config2 = get_config()
        
        # Assert - Should be same instance due to caching
        self.assertIs(config1, config2)
        
    def test_websocket_configuration_valid(self):
        """Test that WebSocket configuration is properly set."""
        # Arrange
        self.env.set("WEBSOCKET_HOST", "localhost")
        self.env.set("WEBSOCKET_PORT", "8000")
        
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.websocket_host)
        self.assertIsNotNone(config.websocket_port)
        
    def test_llm_configuration_valid(self):
        """Test that LLM configuration is properly set."""
        # Arrange
        self.env.set("LLM_MODEL", "gpt-4")
        self.env.set("LLM_API_KEY", "test-api-key")
        
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.llm_model)
        self.assertEqual(config.llm_model, "gpt-4")
        
    def test_cors_configuration_valid(self):
        """Test that CORS configuration is properly set for frontend integration."""
        # Arrange
        self.env.set("FRONTEND_URL", "http://localhost:3000")
        
        # Act
        config = get_config()
        
        # Assert
        self.assertIsNotNone(config.frontend_url)
        self.assertEqual(config.frontend_url, "http://localhost:3000")
        
    def test_staging_configuration_validation(self):
        """Test that staging environment configuration can be validated."""
        # Arrange
        self.env.set("ENVIRONMENT", "staging")
        self.env.set("DATABASE_URL", "postgresql://staging_user:password@staging-db:5432/netra_staging")
        self.env.set("REDIS_HOST", "staging-redis")
        self.env.set("AUTH_SERVICE_URL", "https://staging.netrasystems.ai")
        
        # Act
        config = get_config()
        
        # Assert
        self.assertEqual(config.environment, "staging")
        self.assertIn("staging", config.database_url)
        self.assertIn("staging", config.auth_service_url)
        
    def test_configuration_secrets_handling(self):
        """Test that configuration properly handles secrets."""
        # Arrange
        secret_value = "super-secret-key-123"
        self.env.set("JWT_SECRET", secret_value)
        
        # Act
        config = get_config()
        
        # Assert
        self.assertEqual(config.jwt_secret, secret_value)
        
        # Verify secret is not exposed in string representation
        config_str = str(config)
        self.assertNotIn(secret_value, config_str)
        
    def test_configuration_validation_comprehensive(self):
        """Test comprehensive configuration validation for Golden Path readiness."""
        # Arrange
        validator = ConfigValidator()
        config = get_config()
        
        # Required for Golden Path
        required_configs = [
            'database_url',
            'redis_host', 
            'redis_port',
            'jwt_secret',
            'auth_service_url'
        ]
        
        # Act & Assert
        for config_name in required_configs:
            self.assertTrue(
                hasattr(config, config_name) and getattr(config, config_name) is not None,
                f"Missing required configuration: {config_name}"
            )
            
    def test_configuration_error_handling(self):
        """Test that configuration errors are properly handled and reported."""
        # Arrange - Set invalid configuration
        self.env.set("REDIS_PORT", "invalid-port")
        
        # Act & Assert
        with self.assertRaises(Exception) as context:
            config = get_config()
            # Attempt to access the invalid port config
            _ = config.redis_port
            
        self.assertIn("port", str(context.exception).lower())
        
    def test_configuration_environment_isolation(self):
        """Test that different environments have isolated configuration."""
        # Test environment
        test_config = get_config()
        
        # Change environment
        self.env.set("ENVIRONMENT", "development")
        self.env.set("DATABASE_URL", "postgresql://dev:dev@localhost:5432/dev_db")
        
        # Should get new configuration for development
        with patch('netra_backend.app.config._config_cache', {}):  # Clear cache
            dev_config = get_config()
            
        # Assert environments are different
        self.assertNotEqual(test_config.database_url, dev_config.database_url)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])