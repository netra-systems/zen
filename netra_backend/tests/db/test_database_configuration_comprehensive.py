"""
Comprehensive Unit Tests for Database Configuration Management

Business Value Justification (BVJ):
- Segment: Platform/All Environments
- Business Goal: Reliable database configuration across all deployment environments
- Value Impact: Prevents database connection failures that would break $500K+ ARR operations
- Revenue Impact: Configuration reliability enables seamless deployments and zero-downtime operations

This test suite validates Database Configuration as the SINGLE SOURCE OF TRUTH for database settings.
Critical for golden path: environment setup → database connections → data persistence → business operations.

SSOT Compliance:
- Tests the ONLY source for database configuration management
- Validates environment-specific configuration isolation
- Ensures unified configuration system integration
- Verifies configuration validation and error detection

Golden Path Configuration Coverage:
- Development environment database connections (local PostgreSQL, Redis, ClickHouse)
- Staging environment configuration (secure connections, VPC configuration)
- Production environment settings (SSL, connection pooling, performance optimization)
- Multi-environment isolation (configuration doesn't leak between environments)
- Configuration validation (early detection of misconfigurations)
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from netra_backend.app.core.configuration.database import (
    DatabaseConfigManager,
    get_database_config_manager,
    get_database_url,
    validate_database_connection,
    populate_database_config
)


class TestDatabaseConfigManagerSSO:
    """Test Database Configuration Manager as Single Source of Truth for database settings."""
    
    @pytest.fixture
    def config_manager(self):
        """Create fresh DatabaseConfigManager instance for testing."""
        return DatabaseConfigManager()
    
    @pytest.fixture
    def mock_unified_config(self):
        """Mock unified configuration for testing."""
        mock_config = Mock()
        mock_config.database_url = "postgresql://user:pass@localhost:5432/netra_db"
        mock_config.redis = Mock()
        mock_config.redis.host = "localhost"
        mock_config.redis.port = 6379
        mock_config.redis.db = 0
        mock_config.redis.password = None
        mock_config.redis.ssl = False
        mock_config.clickhouse_native = Mock()
        mock_config.clickhouse_native.host = "localhost"
        mock_config.clickhouse_native.port = 8123
        mock_config.clickhouse_native.user = "default"
        mock_config.clickhouse_native.password = "password"
        mock_config.clickhouse_native.database = "netra_analytics"
        return mock_config
    
    @pytest.mark.unit
    def test_config_manager_initialization(self, config_manager):
        """Test proper initialization of configuration manager.
        
        BVJ: Ensures configuration manager starts in clean state for reliable operations.
        Golden Path: Configuration manager must initialize properly for environment setup.
        """
        assert config_manager._config is None
        assert config_manager._cached_config == {}
        assert hasattr(config_manager, 'get_config')
        assert hasattr(config_manager, 'get_database_url')
        assert hasattr(config_manager, 'validate_database_config')
    
    @pytest.mark.unit
    def test_unified_config_integration(self, config_manager, mock_unified_config):
        """Test integration with unified configuration system.
        
        BVJ: Ensures SSOT compliance by using unified configuration as single source.
        Golden Path: All configuration must flow through unified configuration system.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config', 
                  return_value=mock_unified_config):
            
            # Test configuration retrieval
            config = config_manager.get_config()
            assert config == mock_unified_config
            
            # Test configuration caching
            config2 = config_manager.get_config()
            assert config2 is config  # Should be same cached instance
    
    @pytest.mark.unit
    def test_database_url_extraction(self, config_manager, mock_unified_config):
        """Test database URL extraction for different environments.
        
        BVJ: Ensures correct database connections for each deployment environment.
        Golden Path: Environment-specific database URLs enable proper data isolation.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test database URL retrieval
            database_url = config_manager.get_database_url()
            assert database_url == "postgresql://user:pass@localhost:5432/netra_db"
            
            # Test environment parameter (should use same config for backward compatibility)
            database_url_env = config_manager.get_database_url("development")
            assert database_url_env == database_url
    
    @pytest.mark.unit
    def test_redis_configuration_extraction(self, config_manager, mock_unified_config):
        """Test Redis configuration extraction and formatting.
        
        BVJ: Ensures Redis caching works properly for performance optimization.
        Golden Path: Redis configuration enables fast data access for chat functionality.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test Redis configuration retrieval
            redis_config = config_manager.get_redis_config()
            
            expected_redis_config = {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None,
                'ssl': False
            }
            
            assert redis_config == expected_redis_config
    
    @pytest.mark.unit
    def test_redis_configuration_with_ssl(self, config_manager):
        """Test Redis configuration with SSL settings for production.
        
        BVJ: Ensures secure Redis connections for production data protection.
        Golden Path: Production Redis must use secure connections for data safety.
        """
        # Setup Redis config with SSL
        mock_config = Mock()
        mock_config.redis = Mock()
        mock_config.redis.host = "redis.production.com"
        mock_config.redis.port = 6380
        mock_config.redis.db = 1
        mock_config.redis.password = "secure_redis_password"
        mock_config.redis.ssl = True
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            redis_config = config_manager.get_redis_config()
            
            assert redis_config['host'] == "redis.production.com"
            assert redis_config['port'] == 6380
            assert redis_config['db'] == 1
            assert redis_config['password'] == "secure_redis_password"
            assert redis_config['ssl'] == True
    
    @pytest.mark.unit
    def test_clickhouse_configuration_extraction(self, config_manager, mock_unified_config):
        """Test ClickHouse configuration extraction for analytics.
        
        BVJ: Ensures ClickHouse analytics work properly for business intelligence.
        Golden Path: ClickHouse configuration enables data-driven business decisions.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test ClickHouse configuration retrieval
            clickhouse_config = config_manager.get_clickhouse_config()
            
            expected_clickhouse_config = {
                'host': 'localhost',
                'port': 8123,
                'user': 'default',
                'password': 'password',
                'database': 'netra_analytics'
            }
            
            assert clickhouse_config == expected_clickhouse_config
    
    @pytest.mark.unit
    def test_configuration_validation_success(self, config_manager, mock_unified_config):
        """Test successful database configuration validation.
        
        BVJ: Ensures configuration errors are caught before deployment.
        Golden Path: Valid configuration prevents runtime database connection failures.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test successful validation
            is_valid = config_manager.validate_database_config()
            assert is_valid == True
    
    @pytest.mark.unit
    def test_configuration_validation_missing_url(self, config_manager):
        """Test configuration validation with missing database URL.
        
        BVJ: Prevents deployments with missing critical configuration.
        Golden Path: Missing configuration must be detected before causing outages.
        """
        # Setup config with missing database URL
        mock_config = Mock()
        mock_config.database_url = None
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            # Test validation failure
            is_valid = config_manager.validate_database_config()
            assert is_valid == False
    
    @pytest.mark.unit
    def test_configuration_validation_invalid_url_format(self, config_manager):
        """Test configuration validation with invalid URL format.
        
        BVJ: Prevents runtime errors from malformed database URLs.
        Golden Path: Invalid URLs must be caught in configuration validation.
        """
        # Setup config with invalid URL format
        mock_config = Mock()
        mock_config.database_url = "not-a-valid-url"
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            # Test validation failure
            is_valid = config_manager.validate_database_config()
            assert is_valid == False
    
    @pytest.mark.unit
    def test_complete_database_configuration_population(self, config_manager, mock_unified_config):
        """Test complete database configuration population for all services.
        
        BVJ: Provides complete configuration overview for operational monitoring.
        Golden Path: Complete configuration enables comprehensive system health monitoring.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test complete configuration population
            complete_config = config_manager.populate_database_config()
            
            # Verify structure and content
            assert 'postgresql' in complete_config
            assert 'redis' in complete_config
            assert 'clickhouse' in complete_config
            
            # Verify PostgreSQL config
            postgresql_config = complete_config['postgresql']
            assert postgresql_config['url'] == "postgresql://user:pass@localhost:5432/netra_db"
            assert postgresql_config['valid'] == True
            
            # Verify Redis config
            redis_config = complete_config['redis']
            assert redis_config['host'] == 'localhost'
            assert redis_config['port'] == 6379
            
            # Verify ClickHouse config
            clickhouse_config = complete_config['clickhouse']
            assert clickhouse_config['host'] == 'localhost'
            assert clickhouse_config['port'] == 8123
    
    @pytest.mark.unit
    def test_configuration_error_handling(self, config_manager):
        """Test configuration error handling and recovery.
        
        BVJ: Ensures graceful handling of configuration errors.
        Golden Path: Configuration errors must not crash system startup.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  side_effect=Exception("Configuration error")):
            
            # Test error handling in configuration population
            complete_config = config_manager.populate_database_config()
            
            # Should return empty config on error
            assert complete_config == {}
    
    @pytest.mark.unit
    def test_postgres_url_internal_method(self, config_manager, mock_unified_config):
        """Test internal PostgreSQL URL method for backward compatibility.
        
        BVJ: Ensures existing log messages and interfaces continue to work.
        Golden Path: Backward compatibility prevents breaking existing integrations.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config):
            
            # Test internal method
            postgres_url = config_manager._get_postgres_url()
            assert postgres_url == "postgresql://user:pass@localhost:5432/netra_db"
            
            # Test with environment parameter
            postgres_url_env = config_manager._get_postgres_url("production")
            assert postgres_url_env == postgres_url
    
    @pytest.mark.unit
    def test_redis_config_populate_with_logging(self, config_manager, mock_unified_config):
        """Test Redis configuration population with proper logging format.
        
        BVJ: Ensures operational visibility into Redis configuration.
        Golden Path: Proper logging enables troubleshooting of Redis connection issues.
        """
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_unified_config), \
             patch('netra_backend.app.core.configuration.database.logger') as mock_logger:
            
            # Test Redis configuration with logging
            redis_config = config_manager._populate_redis_config("development")
            
            # Verify logging was called with proper format
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert "Redis Configuration" in log_call
            assert "development" in log_call
            assert "redis://localhost:6379/0" in log_call
            assert "No SSL" in log_call


class TestDatabaseConfigurationModuleFunctions:
    """Test module-level database configuration functions for convenience interface."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager for testing module functions."""
        manager = Mock()
        manager.get_database_url.return_value = "postgresql://test:test@localhost:5432/test_db"
        manager.validate_database_config.return_value = True
        manager.populate_database_config.return_value = {
            'postgresql': {'url': 'test_url', 'valid': True},
            'redis': {'host': 'localhost', 'port': 6379},
            'clickhouse': {'host': 'localhost', 'port': 8123}
        }
        return manager
    
    @pytest.mark.unit
    def test_get_database_config_manager_function(self):
        """Test module-level database config manager factory function.
        
        BVJ: Provides convenient access to configuration manager.
        Golden Path: Simple function interface enables easy configuration access.
        """
        manager = get_database_config_manager()
        
        assert isinstance(manager, DatabaseConfigManager)
        assert hasattr(manager, 'get_database_url')
        assert hasattr(manager, 'validate_database_config')
    
    @pytest.mark.unit
    def test_module_get_database_url_function(self, mock_config_manager):
        """Test module-level get database URL convenience function.
        
        BVJ: Enables quick database URL access without manager instantiation.
        Golden Path: Convenient interface reduces code complexity in components.
        """
        with patch('netra_backend.app.core.configuration.database.get_database_config_manager',
                  return_value=mock_config_manager):
            
            # Test convenience function
            database_url = get_database_url()
            assert database_url == "postgresql://test:test@localhost:5432/test_db"
            
            # Test with environment parameter
            database_url_env = get_database_url("staging")
            mock_config_manager.get_database_url.assert_called_with("staging")
    
    @pytest.mark.unit
    def test_module_validate_database_connection_function(self, mock_config_manager):
        """Test module-level validate database connection convenience function.
        
        BVJ: Enables easy configuration validation without manager complexity.
        Golden Path: Simple validation interface improves deployment reliability.
        """
        with patch('netra_backend.app.core.configuration.database.get_database_config_manager',
                  return_value=mock_config_manager):
            
            # Test convenience function
            is_valid = validate_database_connection()
            assert is_valid == True
            
            # Test with environment parameter
            is_valid_env = validate_database_connection("production")
            mock_config_manager.validate_database_config.assert_called_with("production")
    
    @pytest.mark.unit
    def test_module_populate_database_config_function(self, mock_config_manager):
        """Test module-level populate database config convenience function.
        
        BVJ: Provides complete configuration overview through simple interface.
        Golden Path: Easy configuration access improves operational monitoring.
        """
        with patch('netra_backend.app.core.configuration.database.get_database_config_manager',
                  return_value=mock_config_manager):
            
            # Test convenience function
            config = populate_database_config()
            
            assert 'postgresql' in config
            assert 'redis' in config
            assert 'clickhouse' in config
            
            # Test with environment parameter
            config_env = populate_database_config("staging")
            mock_config_manager.populate_database_config.assert_called_with("staging")


class TestDatabaseConfigurationEnvironmentHandling:
    """Test database configuration handling across different environments."""
    
    @pytest.mark.unit
    def test_development_environment_configuration(self):
        """Test development environment configuration handling.
        
        BVJ: Ensures development environment has proper database connections.
        Golden Path: Development must work reliably for engineering productivity.
        """
        mock_config = Mock()
        mock_config.database_url = "postgresql://dev:dev@localhost:5432/netra_dev"
        mock_config.redis = Mock()
        mock_config.redis.host = "localhost"
        mock_config.redis.port = 6379
        mock_config.redis.ssl = False
        mock_config.clickhouse_native = Mock()
        mock_config.clickhouse_native.host = "localhost"
        mock_config.clickhouse_native.port = 8123
        
        manager = DatabaseConfigManager()
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config("development")
            
            # Verify development-specific settings
            assert "postgresql://dev:dev@localhost:5432/netra_dev" in config['postgresql']['url']
            assert config['redis']['host'] == 'localhost'
            assert config['redis']['ssl'] == False
            assert config['clickhouse']['host'] == 'localhost'
    
    @pytest.mark.unit
    def test_staging_environment_configuration(self):
        """Test staging environment configuration handling.
        
        BVJ: Ensures staging environment mirrors production for accurate testing.
        Golden Path: Staging must validate production-like configuration.
        """
        mock_config = Mock()
        mock_config.database_url = "postgresql://staging:staging@staging-db:5432/netra_staging"
        mock_config.redis = Mock()
        mock_config.redis.host = "staging-redis"
        mock_config.redis.port = 6379
        mock_config.redis.ssl = True  # Staging uses SSL
        mock_config.clickhouse_native = Mock()
        mock_config.clickhouse_native.host = "staging-clickhouse"
        mock_config.clickhouse_native.port = 8443  # Secure port
        
        manager = DatabaseConfigManager()
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config("staging")
            
            # Verify staging-specific settings
            assert "staging-db" in config['postgresql']['url']
            assert config['redis']['host'] == 'staging-redis'
            assert config['redis']['ssl'] == True
            assert config['clickhouse']['host'] == 'staging-clickhouse'
    
    @pytest.mark.unit
    def test_production_environment_configuration(self):
        """Test production environment configuration handling.
        
        BVJ: Ensures production environment has secure, optimized configuration.
        Golden Path: Production must have secure connections and optimal performance.
        """
        mock_config = Mock()
        mock_config.database_url = "postgresql://prod:secure_password@prod-db:5432/netra_prod?sslmode=require"
        mock_config.redis = Mock()
        mock_config.redis.host = "prod-redis.internal"
        mock_config.redis.port = 6380  # Secure Redis port
        mock_config.redis.ssl = True
        mock_config.redis.password = "secure_redis_password"
        mock_config.clickhouse_native = Mock()
        mock_config.clickhouse_native.host = "clickhouse.prod.internal"
        mock_config.clickhouse_native.port = 8443
        mock_config.clickhouse_native.password = "secure_clickhouse_password"
        
        manager = DatabaseConfigManager()
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config("production")
            
            # Verify production-specific settings
            assert "sslmode=require" in config['postgresql']['url']
            assert config['redis']['host'] == 'prod-redis.internal'
            assert config['redis']['ssl'] == True
            assert config['redis']['password'] == 'secure_redis_password'
            assert config['clickhouse']['host'] == 'clickhouse.prod.internal'
            assert config['clickhouse']['password'] == 'secure_clickhouse_password'
    
    @pytest.mark.unit
    def test_environment_isolation_validation(self):
        """Test that environment configurations are properly isolated.
        
        BVJ: Prevents configuration leakage between environments.
        Golden Path: Environment isolation prevents production data exposure.
        """
        dev_config = Mock()
        dev_config.database_url = "postgresql://dev:dev@localhost:5432/netra_dev"
        
        prod_config = Mock()  
        prod_config.database_url = "postgresql://prod:secure@prod-db:5432/netra_prod"
        
        manager = DatabaseConfigManager()
        
        # Test development configuration
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=dev_config):
            dev_url = manager.get_database_url("development")
            assert "netra_dev" in dev_url
            assert "localhost" in dev_url
        
        # Test production configuration (different manager instance)
        manager2 = DatabaseConfigManager()
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=prod_config):
            prod_url = manager2.get_database_url("production")
            assert "netra_prod" in prod_url
            assert "prod-db" in prod_url
            
            # Verify isolation
            assert dev_url != prod_url
            assert "dev" not in prod_url
            assert "prod" not in dev_url


class TestDatabaseConfigurationBusinessScenarios:
    """Test business-critical database configuration scenarios for golden path validation."""
    
    @pytest.mark.unit
    def test_database_connection_configuration_for_user_data(self):
        """Test database configuration for user data operations.
        
        BVJ: Ensures user data is properly stored and retrieved - core business function.
        Golden Path: User registration → profile storage → authentication data persistence.
        """
        manager = DatabaseConfigManager()
        
        # Setup configuration optimized for user data operations
        mock_config = Mock()
        mock_config.database_url = "postgresql://netra_app:app_password@user-data-db:5432/netra_users?pool_size=20&max_overflow=30"
        mock_config.redis = Mock()
        mock_config.redis.host = "user-cache-redis"
        mock_config.redis.port = 6379
        mock_config.redis.db = 0  # User session cache
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config()
            
            # Verify user data optimized configuration
            postgres_url = config['postgresql']['url']
            assert "user-data-db" in postgres_url
            assert "pool_size=20" in postgres_url
            assert config['redis']['host'] == 'user-cache-redis'
            assert config['redis']['db'] == 0  # User session cache
    
    @pytest.mark.unit
    def test_database_configuration_for_chat_conversations(self):
        """Test database configuration for chat conversation storage.
        
        BVJ: Chat conversations are 90% of platform value - must be reliable.
        Golden Path: User messages → conversation threads → agent responses → persistent storage.
        """
        manager = DatabaseConfigManager()
        
        # Setup configuration optimized for conversation data
        mock_config = Mock()
        mock_config.database_url = "postgresql://chat_service:chat_password@conversation-db:5432/netra_conversations?pool_size=50&max_overflow=100"
        mock_config.redis = Mock()
        mock_config.redis.host = "conversation-cache-redis"
        mock_config.redis.port = 6379
        mock_config.redis.db = 1  # Conversation cache
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config()
            
            # Verify conversation optimized configuration
            postgres_url = config['postgresql']['url']
            assert "conversation-db" in postgres_url
            assert "pool_size=50" in postgres_url  # Higher pool for chat load
            assert config['redis']['host'] == 'conversation-cache-redis'
            assert config['redis']['db'] == 1  # Separate cache namespace
    
    @pytest.mark.unit
    def test_database_configuration_for_analytics_and_insights(self):
        """Test database configuration for analytics data collection.
        
        BVJ: Analytics drive business decisions and optimization - must be accurate.
        Golden Path: User interactions → usage analytics → ClickHouse storage → business insights.
        """
        manager = DatabaseConfigManager()
        
        # Setup configuration optimized for analytics
        mock_config = Mock()
        mock_config.database_url = "postgresql://analytics:analytics_password@analytics-db:5432/netra_analytics"
        mock_config.clickhouse_native = Mock()
        mock_config.clickhouse_native.host = "analytics-clickhouse.internal"
        mock_config.clickhouse_native.port = 8443  # Secure analytics
        mock_config.clickhouse_native.user = "analytics_user"
        mock_config.clickhouse_native.password = "analytics_password"
        mock_config.clickhouse_native.database = "netra_business_intelligence"
        
        with patch('netra_backend.app.core.configuration.database.get_unified_config',
                  return_value=mock_config):
            
            config = manager.populate_database_config()
            
            # Verify analytics optimized configuration
            assert "analytics-db" in config['postgresql']['url']
            clickhouse_config = config['clickhouse']
            assert clickhouse_config['host'] == 'analytics-clickhouse.internal'
            assert clickhouse_config['port'] == 8443
            assert clickhouse_config['database'] == 'netra_business_intelligence'
            assert clickhouse_config['user'] == 'analytics_user'
    
    @pytest.mark.unit
    def test_configuration_validation_for_deployment_readiness(self):
        """Test configuration validation for deployment readiness.
        
        BVJ: Prevents deployments with invalid configurations - protects business continuity.
        Golden Path: Configuration validation → deployment approval → stable operations.
        """
        manager = DatabaseConfigManager()
        
        # Test various configuration scenarios for deployment readiness
        test_scenarios = [
            {
                'name': 'valid_production_config',
                'database_url': 'postgresql://user:pass@prod-db:5432/netra?sslmode=require',
                'expected_valid': True
            },
            {
                'name': 'missing_database_url',
                'database_url': None,
                'expected_valid': False
            },
            {
                'name': 'invalid_url_format',
                'database_url': 'not-a-database-url',
                'expected_valid': False
            },
            {
                'name': 'missing_ssl_in_production',
                'database_url': 'postgresql://user:pass@prod-db:5432/netra',
                'expected_valid': True  # SSL checking is URL format validation, not SSL requirement
            }
        ]
        
        for scenario in test_scenarios:
            mock_config = Mock()
            mock_config.database_url = scenario['database_url']
            
            with patch('netra_backend.app.core.configuration.database.get_unified_config',
                      return_value=mock_config):
                
                is_valid = manager.validate_database_config()
                assert is_valid == scenario['expected_valid'], f"Scenario {scenario['name']} failed"
    
    @pytest.mark.unit
    def test_configuration_error_detection_and_reporting(self):
        """Test configuration error detection and reporting for operations.
        
        BVJ: Enables rapid detection and resolution of configuration issues.
        Golden Path: Configuration errors → clear error messages → quick resolution.
        """
        manager = DatabaseConfigManager()
        
        # Test error scenarios
        error_scenarios = [
            {
                'error_type': 'connection_error',
                'side_effect': ConnectionError("Database unreachable"),
                'expected_result': {}
            },
            {
                'error_type': 'configuration_missing',
                'side_effect': KeyError("Missing configuration key"),
                'expected_result': {}
            },
            {
                'error_type': 'permission_error',
                'side_effect': PermissionError("Access denied"),
                'expected_result': {}
            }
        ]
        
        for scenario in error_scenarios:
            with patch('netra_backend.app.core.configuration.database.get_unified_config',
                      side_effect=scenario['side_effect']):
                
                # Should handle error gracefully
                config = manager.populate_database_config()
                assert config == scenario['expected_result']
    
    @pytest.mark.unit
    def test_multi_environment_configuration_consistency(self):
        """Test configuration consistency across multiple environments.
        
        BVJ: Ensures consistent behavior across development, staging, and production.
        Golden Path: Consistent configuration → predictable behavior → reduced operational issues.
        """
        environments = ['development', 'staging', 'production']
        base_urls = {
            'development': 'postgresql://dev:dev@localhost:5432/netra_dev',
            'staging': 'postgresql://staging:staging@staging-db:5432/netra_staging', 
            'production': 'postgresql://prod:secure@prod-db:5432/netra_prod?sslmode=require'
        }
        
        for env in environments:
            manager = DatabaseConfigManager()
            
            mock_config = Mock()
            mock_config.database_url = base_urls[env]
            mock_config.redis = Mock()
            mock_config.redis.host = f"{env}-redis"
            mock_config.redis.port = 6379
            mock_config.redis.ssl = (env in ['staging', 'production'])
            
            with patch('netra_backend.app.core.configuration.database.get_unified_config',
                      return_value=mock_config):
                
                config = manager.populate_database_config(env)
                
                # Verify environment-specific consistency
                assert env in config['postgresql']['url'] or 'localhost' in config['postgresql']['url']
                assert config['redis']['host'] == f"{env}-redis"
                assert config['redis']['ssl'] == (env in ['staging', 'production'])
                assert config['postgresql']['valid'] == True