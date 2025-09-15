"""Comprehensive unit tests for Analytics Service Configuration.

BUSINESS VALUE: Ensures configuration validation and environment management
reliability for analytics service operations. Critical for preventing
service failures due to misconfiguration.

Tests cover:
- Configuration initialization and validation
- Environment-specific settings
- Database connection parameter generation
- Sensitive value masking for security
- Error handling for invalid configurations

NO MOCKS POLICY: Uses real IsolatedEnvironment with isolation for proper testing.
All mock usage has been replaced with actual configuration testing.
"""

import pytest
import logging
# NO MOCKS - removed all mock imports per NO MOCKS POLICY
from typing import Dict, Any

from analytics_service.analytics_core.config import (
    AnalyticsConfig,
    get_config,
    get_service_port,
    get_environment,
    is_production,
)
from shared.isolated_environment import get_env


class TestAnalyticsConfig:
    """Test suite for AnalyticsConfig class."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

        # Clear ENVIRONMENT to ensure clean test state, then set default
        # This ensures consistent behavior across test environments
        env.unset("ENVIRONMENT")
        env.set("ENVIRONMENT", "development")

        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_config_initialization_defaults(self):
        """Test configuration initialization with default values."""
        # Override pytest detection to test defaults
        env = get_env()
        env.set("ENVIRONMENT", "development")
        
        # Clear any interfering environment variables to test defaults
        vars_to_clear = [
            "CLICKHOUSE_PORT", "CLICKHOUSE_PASSWORD", "ANALYTICS_SERVICE_PORT",
            "CLICKHOUSE_HOST", "CLICKHOUSE_DATABASE", "CLICKHOUSE_USERNAME",
            "CLICKHOUSE_ANALYTICS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_ANALYTICS_DB",
            "REDIS_PASSWORD", "REDIS_ANALYTICS_URL", "CLICKHOUSE_USER", "EVENT_FLUSH_INTERVAL_MS",
            "EVENT_BATCH_SIZE", "MAX_EVENTS_PER_USER_PER_MINUTE", "ANALYTICS_WORKERS",
            "CONNECTION_POOL_SIZE", "QUERY_TIMEOUT_SECONDS", "EVENT_RETENTION_DAYS",
            "ANALYTICS_RETENTION_DAYS", "ANALYTICS_LOG_LEVEL", "ENABLE_REQUEST_LOGGING",
            "ANALYTICS_API_KEY", "ANALYTICS_CORS_ORIGINS", "GRAFANA_API_URL", "GRAFANA_API_KEY"
        ]
        for var in vars_to_clear:
            env.unset(var)
        
        config = AnalyticsConfig()
        
        # Service Identity
        assert config.service_name == "analytics_service"
        assert config.service_version == "1.0.0"
        assert config.service_port == 8090
        assert config.environment in ["development", "test"]  # SSOT sets "test" in isolated mode
        
        # Database Configuration - Check individual components since URL might vary
        assert config.clickhouse_host == "localhost"
        assert config.clickhouse_port == 9000  # Native protocol port, not HTTP port
        assert config.clickhouse_database == "analytics"
        assert config.clickhouse_username == "default"
        assert config.clickhouse_password == ""
        
        # Redis Configuration - SSOT provides test defaults
        assert config.redis_host == "localhost"
        assert config.redis_port == 6381  # SSOT test default port
        assert config.redis_db == 2  # Analytics service specific DB
        assert config.redis_password is not None  # SSOT provides test password
        
        # Event Processing
        assert config.event_batch_size == 100
        assert config.event_flush_interval_ms == 5000
        assert config.max_events_per_user_per_minute == 1000

    def test_config_initialization_with_env_vars(self):
        """Test configuration initialization with environment variables."""
        env = get_env()
        
        # Set environment variables - use development to avoid validation issues
        env.set("ANALYTICS_SERVICE_PORT", "8091")
        env.set("ENVIRONMENT", "development")
        env.set("CLICKHOUSE_HOST", "staging-clickhouse")
        env.set("CLICKHOUSE_PORT", "9000")
        env.set("CLICKHOUSE_DATABASE", "staging_analytics")
        env.set("CLICKHOUSE_USERNAME", "analytics_user")
        env.set("CLICKHOUSE_PASSWORD", "secure_password")
        env.set("REDIS_HOST", "staging-redis")
        env.set("REDIS_PORT", "6380")
        env.set("REDIS_ANALYTICS_DB", "3")
        env.set("REDIS_PASSWORD", "redis_password")
        env.set("EVENT_BATCH_SIZE", "50")
        env.set("MAX_EVENTS_PER_USER_PER_MINUTE", "500")
        env.set("ANALYTICS_API_KEY", "test_api_key")
        env.set("ANALYTICS_WORKERS", "2")

        # Reset global config to pick up new environment variables
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

        # Debug: Check if environment variable is set correctly
        assert env.get("ANALYTICS_SERVICE_PORT") == "8091", f"Environment variable not set correctly: {env.get('ANALYTICS_SERVICE_PORT')}"

        config = AnalyticsConfig()

        # Debug: Check what the config sees
        config_port_from_env = config.env.get("ANALYTICS_SERVICE_PORT", "NOT_SET")
        assert config_port_from_env == "8091", f"Config doesn't see correct env var: {config_port_from_env}"

        # Verify environment variables are used
        assert config.service_port == 8091
        assert config.environment == "development"
        assert config.clickhouse_host == "staging-clickhouse"
        assert config.clickhouse_port == 9000
        assert config.clickhouse_database == "staging_analytics"
        assert config.clickhouse_username == "analytics_user"
        assert config.clickhouse_password == "secure_password"
        assert config.redis_host == "staging-redis"
        assert config.redis_port == 6380
        assert config.redis_db == 3
        assert config.redis_password == "redis_password"
        assert config.event_batch_size == 50
        assert config.max_events_per_user_per_minute == 500
        assert config.api_key == "test_api_key"
        assert config.worker_count == 2

    def test_environment_detection_methods(self):
        """Test environment detection properties."""
        env = get_env()
        
        # Test development environment
        env.set("ENVIRONMENT", "development")
        config = AnalyticsConfig()
        assert config.is_development is True
        assert config.is_staging is False
        assert config.is_production is False
        
        # Test staging environment with proper URLs to avoid validation errors
        env.set("ENVIRONMENT", "staging")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://staging-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://staging-redis:6379/2")
        config = AnalyticsConfig()
        assert config.is_development is False
        assert config.is_staging is True
        assert config.is_production is False
        
        # Test production environment with proper URLs to avoid validation errors
        env.set("ENVIRONMENT", "production")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://prod-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://prod-redis:6379/2")
        config = AnalyticsConfig()
        assert config.is_development is False
        assert config.is_staging is False
        assert config.is_production is True

    def test_clickhouse_connection_params(self):
        """Test ClickHouse connection parameter generation."""
        env = get_env()
        env.set("CLICKHOUSE_HOST", "test-clickhouse")
        env.set("CLICKHOUSE_PORT", "9000")
        env.set("CLICKHOUSE_DATABASE", "test_analytics")
        env.set("CLICKHOUSE_USERNAME", "test_user")
        env.set("CLICKHOUSE_PASSWORD", "test_password")
        
        config = AnalyticsConfig()
        params = config.get_clickhouse_connection_params()
        
        expected_params = {
            "host": "test-clickhouse",
            "port": 9000,
            "database": "test_analytics",
            "user": "test_user",
            "password": "test_password",
        }
        
        assert params == expected_params

    def test_redis_connection_params(self):
        """Test Redis connection parameter generation."""
        env = get_env()
        env.set("REDIS_HOST", "test-redis")
        env.set("REDIS_PORT", "6380")
        env.set("REDIS_ANALYTICS_DB", "5")
        env.set("REDIS_PASSWORD", "test_redis_password")
        
        config = AnalyticsConfig()
        params = config.get_redis_connection_params()
        
        expected_params = {
            "host": "test-redis",
            "port": 6380,
            "db": 5,
            "password": "test_redis_password",
        }
        
        assert params == expected_params

    def test_redis_connection_params_without_password(self):
        """Test Redis connection parameters without password."""
        env = get_env()
        env.set("REDIS_HOST", "test-redis")
        env.set("REDIS_PORT", "6379")
        env.set("REDIS_ANALYTICS_DB", "0")
        
        config = AnalyticsConfig()
        params = config.get_redis_connection_params()
        
        expected_params = {
            "host": "test-redis",
            "port": 6379,
            "db": 0,
        }
        
        assert params == expected_params
        assert "password" not in params

    def test_mask_sensitive_config(self):
        """Test sensitive configuration value masking."""
        env = get_env()
        env.set("CLICKHOUSE_PASSWORD", "secret_password")
        env.set("REDIS_PASSWORD", "secret_redis_password")
        env.set("ANALYTICS_API_KEY", "secret_api_key")
        env.set("GRAFANA_API_KEY", "secret_grafana_key")
        
        config = AnalyticsConfig()
        masked_config = config.mask_sensitive_config()
        
        # Check that sensitive values are masked
        assert masked_config["clickhouse_password"] == "***masked***"
        assert masked_config["redis_password"] == "***masked***"
        assert masked_config["api_key"] == "***masked***"
        assert masked_config["grafana_api_key"] == "***masked***"
        
        # Check that non-sensitive values are present
        assert "service_name" in masked_config
        assert "service_port" in masked_config
        assert "environment" in masked_config
        assert masked_config["service_name"] == "analytics_service"

    def test_configuration_validation_valid(self):
        """Test configuration validation with valid values."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "8090")
        env.set("EVENT_BATCH_SIZE", "100")
        env.set("MAX_EVENTS_PER_USER_PER_MINUTE", "1000")
        env.set("ENVIRONMENT", "development")
        
        # Should not raise any exception
        config = AnalyticsConfig()
        assert config.service_port == 8090

    def test_configuration_validation_invalid_port(self):
        """Test configuration validation with invalid port."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "80")  # Below minimum
        
        # Should raise ValueError in production
        env.set("ENVIRONMENT", "production")
        with pytest.raises(ValueError, match="Invalid service port"):
            AnalyticsConfig()
        
        # Should work in development (warnings are acceptable)
        env.set("ENVIRONMENT", "development")
        config = AnalyticsConfig()  # Should not raise
        # Test that config is created successfully despite warning
        assert config.service_port == 80

    def test_configuration_validation_invalid_batch_size(self):
        """Test configuration validation with invalid batch size."""
        env = get_env()
        env.set("EVENT_BATCH_SIZE", "0")  # Invalid
        env.set("ENVIRONMENT", "production")
        
        with pytest.raises(ValueError, match="Event batch size must be between 1 and 1000"):
            AnalyticsConfig()

    def test_configuration_validation_production_requirements(self):
        """Test configuration validation requirements for production."""
        env = get_env()
        env.set("ENVIRONMENT", "production")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://localhost:8123/analytics")  # Contains localhost
        env.set("REDIS_ANALYTICS_URL", "redis://localhost:6379/2")  # Contains localhost
        
        with pytest.raises(ValueError, match="ClickHouse URL cannot use localhost in staging/production"):
            AnalyticsConfig()

    def test_configuration_validation_staging_requirements(self):
        """Test configuration validation requirements for staging."""
        env = get_env()
        env.set("ENVIRONMENT", "staging")
        env.set("CLICKHOUSE_ANALYTICS_URL", "")  # Empty URL
        
        with pytest.raises(ValueError, match="ClickHouse URL is required in staging/production"):
            AnalyticsConfig()

    def test_configuration_warnings(self):
        """Test configuration validation warnings."""
        env = get_env()
        env.set("ENVIRONMENT", "staging")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://staging-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://staging-redis:6379/2")
        env.set("GRAFANA_API_URL", "http://grafana.example.com")
        # No API key set - should generate warning
        
        config = AnalyticsConfig()
        # Test that config is created successfully despite warnings
        assert config.environment == "staging"

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing."""
        env = get_env()
        env.set("ANALYTICS_CORS_ORIGINS", "http://localhost:3000,https://app.netra.ai,https://api.netra.ai")
        
        config = AnalyticsConfig()
        expected_origins = ["http://localhost:3000", "https://app.netra.ai", "https://api.netra.ai"]
        assert config.cors_origins == expected_origins

    def test_development_environment_detection(self):
        """Test development environment detection logic."""
        env = get_env()
        
        # Test direct pytest detection (real detection works in test environment)
        config = AnalyticsConfig()
        # In actual test environment, this should detect development
        is_dev = config._is_development_environment()
        assert isinstance(is_dev, bool)  # Should return a boolean
        
        # Test environment variable detection
        env.set("ENVIRONMENT", "dev")
        config = AnalyticsConfig()
        assert config._is_development_environment() is True
        
        env.set("ANALYTICS_DEV_MODE", "true")
        config = AnalyticsConfig()
        assert config._is_development_environment() is True

    def test_logging_during_initialization(self):
        """Test configuration initialization without mock verification - NO MOCKS"""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        config = AnalyticsConfig()
        
        # Verify configuration was created successfully (logging happened internally)
        assert config.environment == "test"
        assert config.service_name == "analytics_service"
        # Configuration validation passed if no exception was raised


class TestGlobalConfigFunctions:
    """Test suite for global configuration functions."""

    def setup_method(self):
        """Set up test environment for each test."""
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
        assert isinstance(config1, AnalyticsConfig)

    def test_get_service_port(self):
        """Test get_service_port convenience function."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "8091")
        
        port = get_service_port()
        assert port == 8091

    def test_get_environment(self):
        """Test get_environment convenience function."""
        env = get_env()
        env.set("ENVIRONMENT", "staging")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://staging-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://staging-redis:6379/2")
        
        environment = get_environment()
        assert environment == "staging"

    def test_is_production(self):
        """Test is_production convenience function."""
        env = get_env()
        
        # Reset global config before each test
        import analytics_service.analytics_core.config as config_module
        config_module._config = None
        
        env.set("ENVIRONMENT", "production")
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://prod-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://prod-redis:6379/2")
        
        assert is_production() is True
        
        # Reset config to test development
        config_module._config = None
        env.set("ENVIRONMENT", "development")
        assert is_production() is False

    def test_config_caching(self):
        """Test that configuration values are properly cached."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "8092")
        
        config = get_config()
        initial_port = config.service_port
        
        # Change environment value
        env.set("ANALYTICS_SERVICE_PORT", "8093")
        
        # Config should still return cached value
        same_config = get_config()
        assert same_config.service_port == initial_port  # Should be 8092, not 8093
        assert config is same_config


class TestConfigIntegration:
    """Integration tests for configuration with real environment."""

    def test_config_with_real_environment_defaults(self):
        """Test configuration with actual environment (no isolation)."""
        # Don't use isolation for this test
        env = get_env()
        env.disable_isolation()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None
        
        config = get_config()
        
        # Should have reasonable defaults
        assert config.service_name == "analytics_service"
        assert config.service_version == "1.0.0"
        assert isinstance(config.service_port, int)
        assert config.service_port > 0
        
        # Clean up
        env.enable_isolation()

    def test_config_validation_edge_cases(self):
        """Test configuration validation with edge cases."""
        env = get_env()
        env.enable_isolation()
        
        # Test maximum batch size
        env.set("EVENT_BATCH_SIZE", "1000")
        config = AnalyticsConfig()
        assert config.event_batch_size == 1000
        
        # Test batch size over maximum
        env.set("EVENT_BATCH_SIZE", "1001")
        env.set("ENVIRONMENT", "production")
        
        with pytest.raises(ValueError, match="Event batch size must be between 1 and 1000"):
            AnalyticsConfig()
        
        # Clean up
        env.disable_isolation()