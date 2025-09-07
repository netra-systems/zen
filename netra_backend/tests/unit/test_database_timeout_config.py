"""
Unit tests for database timeout configuration.

Tests environment-aware timeout settings and Cloud SQL optimizations.
"""

import pytest
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config,
    get_cloud_sql_optimized_config,
    is_cloud_sql_environment,
    get_progressive_retry_config,
    log_timeout_configuration
)


class TestDatabaseTimeoutConfig:
    """Test database timeout configuration functionality."""
    
    def test_development_timeout_config(self):
        """Test timeout configuration for development environment."""
        config = get_database_timeout_config("development")
        
        assert config["initialization_timeout"] == 30.0
        assert config["table_setup_timeout"] == 15.0
        assert config["connection_timeout"] == 20.0
        assert config["pool_timeout"] == 30.0
        assert config["health_check_timeout"] == 10.0
    
    def test_staging_timeout_config(self):
        """Test timeout configuration for staging environment."""
        config = get_database_timeout_config("staging")
        
        # Staging should have longer timeouts for Cloud SQL
        assert config["initialization_timeout"] == 60.0
        assert config["table_setup_timeout"] == 30.0
        assert config["connection_timeout"] == 45.0
        assert config["pool_timeout"] == 50.0
        assert config["health_check_timeout"] == 20.0
    
    def test_production_timeout_config(self):
        """Test timeout configuration for production environment."""
        config = get_database_timeout_config("production")
        
        # Production should have the longest timeouts for reliability
        assert config["initialization_timeout"] == 90.0
        assert config["table_setup_timeout"] == 45.0
        assert config["connection_timeout"] == 60.0
        assert config["pool_timeout"] == 70.0
        assert config["health_check_timeout"] == 30.0
    
    def test_test_timeout_config(self):
        """Test timeout configuration for test environment."""
        config = get_database_timeout_config("test")
        
        # Test should have the fastest timeouts
        assert config["initialization_timeout"] == 25.0
        assert config["table_setup_timeout"] == 10.0
        assert config["connection_timeout"] == 15.0
        assert config["pool_timeout"] == 20.0
        assert config["health_check_timeout"] == 5.0
    
    def test_unknown_environment_defaults_to_development(self):
        """Test that unknown environments default to development configuration."""
        config = get_database_timeout_config("unknown")
        dev_config = get_database_timeout_config("development")
        
        assert config == dev_config
    
    def test_case_insensitive_environment(self):
        """Test that environment names are case insensitive."""
        staging_lower = get_database_timeout_config("staging")
        staging_upper = get_database_timeout_config("STAGING")
        staging_mixed = get_database_timeout_config("Staging")
        
        assert staging_lower == staging_upper == staging_mixed


class TestCloudSQLOptimizedConfig:
    """Test Cloud SQL specific configuration optimizations."""
    
    def test_staging_cloud_sql_config(self):
        """Test Cloud SQL configuration for staging environment."""
        config = get_cloud_sql_optimized_config("staging")
        
        # Check connection arguments
        assert "connect_args" in config
        server_settings = config["connect_args"]["server_settings"]
        assert server_settings["application_name"] == "netra_staging"
        assert server_settings["tcp_keepalives_idle"] == "600"
        assert server_settings["tcp_keepalives_interval"] == "30"
        assert server_settings["tcp_keepalives_count"] == "3"
        
        # Check pool configuration
        pool_config = config["pool_config"]
        assert pool_config["pool_size"] == 15
        assert pool_config["max_overflow"] == 25
        assert pool_config["pool_timeout"] == 60.0
        assert pool_config["pool_recycle"] == 3600
        assert pool_config["pool_pre_ping"] is True
        assert pool_config["pool_reset_on_return"] == "rollback"
    
    def test_production_cloud_sql_config(self):
        """Test Cloud SQL configuration for production environment."""
        config = get_cloud_sql_optimized_config("production")
        
        server_settings = config["connect_args"]["server_settings"]
        assert server_settings["application_name"] == "netra_production"
        
        # Production should have same Cloud SQL optimizations as staging
        pool_config = config["pool_config"]
        assert pool_config["pool_size"] == 15
        assert pool_config["max_overflow"] == 25
    
    def test_development_config_smaller_pools(self):
        """Test that development uses smaller connection pools."""
        config = get_cloud_sql_optimized_config("development")
        
        pool_config = config["pool_config"]
        assert pool_config["pool_size"] == 5  # Smaller than staging/production
        assert pool_config["max_overflow"] == 10  # Smaller than staging/production
        assert pool_config["pool_timeout"] == 30.0  # Shorter than staging/production


class TestCloudSQLEnvironmentDetection:
    """Test Cloud SQL environment detection."""
    
    def test_staging_is_cloud_sql_environment(self):
        """Test that staging is detected as Cloud SQL environment."""
        assert is_cloud_sql_environment("staging") is True
    
    def test_production_is_cloud_sql_environment(self):
        """Test that production is detected as Cloud SQL environment."""
        assert is_cloud_sql_environment("production") is True
    
    def test_development_is_not_cloud_sql_environment(self):
        """Test that development is not detected as Cloud SQL environment."""
        assert is_cloud_sql_environment("development") is False
    
    def test_test_is_not_cloud_sql_environment(self):
        """Test that test is not detected as Cloud SQL environment."""
        assert is_cloud_sql_environment("test") is False
    
    def test_case_insensitive_cloud_sql_detection(self):
        """Test that Cloud SQL detection is case insensitive."""
        assert is_cloud_sql_environment("STAGING") is True
        assert is_cloud_sql_environment("Staging") is True
        assert is_cloud_sql_environment("PRODUCTION") is True


class TestProgressiveRetryConfig:
    """Test progressive retry configuration for database connections."""
    
    def test_cloud_sql_retry_config(self):
        """Test retry configuration for Cloud SQL environments."""
        staging_config = get_progressive_retry_config("staging")
        
        assert staging_config["max_retries"] == 5
        assert staging_config["base_delay"] == 2.0
        assert staging_config["max_delay"] == 30.0
        assert staging_config["exponential_base"] == 2
        assert staging_config["jitter"] is True
        
        production_config = get_progressive_retry_config("production")
        assert production_config == staging_config  # Same config for Cloud SQL
    
    def test_local_retry_config(self):
        """Test retry configuration for local environments."""
        dev_config = get_progressive_retry_config("development")
        
        assert dev_config["max_retries"] == 3
        assert dev_config["base_delay"] == 1.0
        assert dev_config["max_delay"] == 10.0
        assert dev_config["exponential_base"] == 2
        assert dev_config["jitter"] is True
        
        test_config = get_progressive_retry_config("test")
        assert test_config == dev_config  # Same config for local environments


class TestTimeoutConfigurationLogging:
    """Test timeout configuration logging functionality."""
    
    def test_log_timeout_configuration_does_not_raise(self):
        """Test that logging timeout configuration doesn't raise exceptions."""
        # This should not raise any exceptions
        try:
            log_timeout_configuration("staging")
            log_timeout_configuration("development")
            log_timeout_configuration("production")
            log_timeout_configuration("test")
        except Exception as e:
            pytest.fail(f"log_timeout_configuration raised an exception: {e}")
    
    def test_log_unknown_environment(self):
        """Test logging configuration for unknown environment."""
        try:
            log_timeout_configuration("unknown")
        except Exception as e:
            pytest.fail(f"log_timeout_configuration raised an exception for unknown environment: {e}")


@pytest.mark.parametrize("environment,expected_init_timeout", [
    ("development", 30.0),
    ("test", 25.0),
    ("staging", 60.0),
    ("production", 90.0),
    ("unknown", 30.0),  # Should default to development
])
def test_initialization_timeout_by_environment(environment, expected_init_timeout):
    """Test initialization timeout values for different environments."""
    config = get_database_timeout_config(environment)
    assert config["initialization_timeout"] == expected_init_timeout


@pytest.mark.parametrize("environment,is_cloud_sql", [
    ("development", False),
    ("test", False),
    ("staging", True),
    ("production", True),
    ("unknown", False),
])
def test_cloud_sql_detection_by_environment(environment, is_cloud_sql):
    """Test Cloud SQL detection for different environments."""
    assert is_cloud_sql_environment(environment) == is_cloud_sql