from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Redis Connection Warning Staging Regression Tests

Tests to replicate Redis connection issues found in GCP staging audit:
- Warning about Redis connection on localhost
- Should use proper connection configuration for staging environment
- Redis connection configuration not environment-aware

Business Value: Prevents cache and session management failures costing $30K+ MRR  
Critical for session persistence and caching performance.

Root Cause from Staging Audit:
- Redis connections attempting to connect to localhost instead of proper staging Redis
- Connection configuration not environment-specific
- Warnings appearing in staging logs about incorrect Redis host

These tests will FAIL initially to confirm the issues exist, then PASS after fixes.
"""

import os
import pytest
import redis
from typing import Dict, Any, List

from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler
from netra_backend.app.core.configuration.base import UnifiedConfigManager


@pytest.mark.staging
@pytest.mark.critical
class TestRedisConnectionWarningsRegression:
    """Tests that replicate Redis connection warning issues from staging audit"""

    def test_redis_localhost_connection_warning_regression(self):
        """
        REGRESSION TEST: Redis connecting to localhost instead of staging Redis
        
        This test should FAIL initially to confirm localhost connection issue.
        Root cause: Redis configuration using localhost in staging environment.
        
        Expected failure: Redis attempting to connect to localhost
        """
        # Arrange - Mock staging environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'REDIS_HOST': 'localhost',  # This is the problematic config
            'REDIS_PORT': '6379'
        }, clear=False):
            
            # Act - Try to create Redis connection
            try:
                redis_handler = RedisConnectionHandler()
                connection_info = redis_handler.get_connection_info()
                
                # This should FAIL - localhost should not be used in staging
                if connection_info.get('host') == 'localhost':
                    pytest.fail("Redis using localhost in staging environment (confirms the bug)")
                elif connection_info.get('host') == '127.0.0.1':
                    pytest.fail("Redis using 127.0.0.1 in staging environment (confirms the bug)")
                else:
                    # If not localhost, should be proper staging Redis host
                    assert 'staging' in connection_info.get('host', '').lower() or \
                           'redis' in connection_info.get('host', '').lower(), \
                           f"Unexpected Redis host: {connection_info.get('host')}"
                           
            except AttributeError:
                # Expected failure - connection handler doesn't exist or method missing
                pytest.fail("Redis connection handler missing or incomplete")

    def test_redis_environment_specific_configuration_missing_regression(self):
        """
        REGRESSION TEST: Redis configuration not environment-aware
        
        This test should FAIL initially if environment-specific config is missing.
        Root cause: Same Redis config used across all environments.
        
        Expected failure: Redis config doesn't change based on environment
        """
        # Arrange - Test different environments should use different Redis configs
        environment_configs = [
            {
                'env': 'development',
                'expected_patterns': ['localhost', '127.0.0.1', 'redis-dev'],
                'should_allow_localhost': True
            },
            {
                'env': 'staging', 
                'expected_patterns': ['redis-staging', 'staging-redis', 'redis.staging'],
                'should_allow_localhost': False
            },
            {
                'env': 'production',
                'expected_patterns': ['redis-prod', 'production-redis', 'redis.production'],
                'should_allow_localhost': False
            }
        ]
        
        # Act & Assert - Check environment-specific Redis configuration
        config_issues = []
        
        for env_config in environment_configs:
            env_name = env_config['env']
            expected_patterns = env_config['expected_patterns']
            should_allow_localhost = env_config['should_allow_localhost']
            
            with patch.dict(os.environ, {'ENVIRONMENT': env_name}, clear=False):
                try:
                    config = UnifiedConfig()
                    redis_host = getattr(config, 'redis_host', None)
                    
                    if redis_host is None:
                        config_issues.append(f"Environment {env_name}: Redis host not configured")
                        continue
                    
                    # Check if localhost is being used inappropriately
                    is_localhost = redis_host in ['localhost', '127.0.0.1']
                    
                    if is_localhost and not should_allow_localhost:
                        config_issues.append(f"Environment {env_name}: Using localhost ({redis_host}) inappropriately")
                    
                    # Check if proper environment-specific host is used
                    if not is_localhost:
                        host_matches_env = any(pattern in redis_host.lower() for pattern in expected_patterns)
                        if not host_matches_env:
                            config_issues.append(f"Environment {env_name}: Host {redis_host} doesn't match expected patterns {expected_patterns}")
                            
                except AttributeError as e:
                    config_issues.append(f"Environment {env_name}: Configuration error - {e}")
        
        # This should FAIL if configuration is not environment-aware
        if config_issues:
            pytest.fail(f"Redis configuration not environment-specific: {config_issues}")

    def test_redis_connection_pool_configuration_warnings_regression(self):
        """
        REGRESSION TEST: Redis connection pool not properly configured for staging
        
        This test should FAIL initially if connection pool settings cause warnings.
        Root cause: Connection pool settings not optimized for staging environment.
        
        Expected failure: Suboptimal connection pool configuration
        """
        # Arrange - Check Redis connection pool configuration
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=False):
            
            try:
                redis_handler = RedisConnectionHandler()
                
                # Get connection pool settings
                pool_config = redis_handler.get_connection_pool_config()
                
                # Act & Assert - Check pool configuration
                pool_issues = []
                
                # Check max_connections (should be reasonable for staging)
                max_connections = pool_config.get('max_connections', 0)
                if max_connections <= 0:
                    pool_issues.append("max_connections not set or invalid")
                elif max_connections > 100:
                    pool_issues.append(f"max_connections too high for staging: {max_connections}")
                
                # Check connection timeout
                socket_timeout = pool_config.get('socket_timeout', 0)
                if socket_timeout <= 0:
                    pool_issues.append("socket_timeout not set")
                elif socket_timeout > 30:
                    pool_issues.append(f"socket_timeout too high: {socket_timeout}s")
                
                # Check retry configuration  
                retry_on_timeout = pool_config.get('retry_on_timeout', None)
                if retry_on_timeout is None:
                    pool_issues.append("retry_on_timeout not configured")
                
                # This should FAIL if pool configuration has issues
                if pool_issues:
                    pytest.fail(f"Redis connection pool configuration issues: {pool_issues}")
                    
            except AttributeError:
                # Expected failure - connection pool methods don't exist
                pytest.fail("Redis connection pool configuration methods missing")

    def test_redis_health_check_localhost_warning_regression(self):
        """
        REGRESSION TEST: Redis health check connects to localhost in staging
        
        This test should FAIL initially if health checks use localhost.
        Root cause: Health check configuration separate from main Redis config.
        
        Expected failure: Health check using localhost connection
        """
        # Arrange - Mock staging environment with Redis health check
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'TESTING': '0'
        }, clear=False):
            
            # Mock Redis client to capture connection attempts
            with patch('redis.Redis') as mock_redis:
                mock_instance = MagicNone  # TODO: Use real service instance
                mock_redis.return_value = mock_instance
                
                # Act - Perform Redis health check
                try:
                    redis_handler = RedisConnectionHandler()
                    is_healthy = redis_handler.health_check()
                    
                    # Check what host was used for the connection
                    if mock_redis.called:
                        call_args = mock_redis.call_args
                        if call_args:
                            # Check positional and keyword arguments
                            args, kwargs = call_args
                            host = kwargs.get('host', args[0] if args else None)
                            
                            # This should FAIL if localhost is used for health check
                            if host in ['localhost', '127.0.0.1']:
                                pytest.fail(f"Redis health check using localhost ({host}) in staging")
                    
                except AttributeError:
                    # Expected failure - health_check method doesn't exist
                    pytest.fail("Redis health check method missing")

    def test_redis_connection_string_parsing_regression(self):
        """
        REGRESSION TEST: Redis connection string not properly parsed for staging
        
        This test should FAIL initially if connection string parsing has issues.
        Root cause: Connection string format not compatible with staging environment.
        
        Expected failure: Redis connection string parsing errors
        """
        # Arrange - Test various Redis connection string formats that might cause issues
        connection_string_scenarios = [
            {
                'url': 'redis://localhost:6379/0',
                'environment': 'staging',
                'should_fail': True,  # localhost in staging should fail
                'error': 'localhost not allowed in staging'
            },
            {
                'url': 'redis://127.0.0.1:6379/0', 
                'environment': 'staging',
                'should_fail': True,  # 127.0.0.1 in staging should fail
                'error': '127.0.0.1 not allowed in staging'
            },
            {
                'url': 'redis://redis-staging:6379/0',
                'environment': 'staging', 
                'should_fail': False,  # proper staging host should work
                'error': None
            }
        ]
        
        # Act & Assert - Test connection string parsing
        parsing_failures = []
        
        for scenario in connection_string_scenarios:
            url = scenario['url']
            env = scenario['environment']
            should_fail = scenario['should_fail']
            expected_error = scenario['error']
            
            with patch.dict(os.environ, {
                'ENVIRONMENT': env,
                'REDIS_URL': url
            }, clear=False):
                
                try:
                    redis_handler = RedisConnectionHandler()
                    parsed_config = redis_handler.parse_connection_string(url)
                    
                    # Check if parsing should have failed but didn't
                    if should_fail and parsed_config:
                        host = parsed_config.get('host')
                        if host in ['localhost', '127.0.0.1'] and env == 'staging':
                            parsing_failures.append(f"Connection string parsing allowed {host} in staging")
                            
                except (ValueError, AttributeError) as e:
                    if not should_fail:
                        parsing_failures.append(f"Connection string parsing failed unexpectedly for {url}: {e}")
        
        # This should FAIL if connection string parsing has issues
        if parsing_failures:
            pytest.fail(f"Redis connection string parsing issues: {parsing_failures}")


@pytest.mark.staging
@pytest.mark.critical
class TestRedisEnvironmentConfigurationRegression:
    """Tests Redis environment-specific configuration issues"""

    def test_redis_failover_configuration_missing_regression(self):
        """
        REGRESSION TEST: Redis failover not configured for staging
        
        This test should FAIL initially if failover configuration is missing.
        Root cause: Single Redis instance without failover in staging.
        
        Expected failure: Redis failover/sentinel configuration missing
        """
        # Arrange - Check for Redis failover configuration in staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=False):
            
            try:
                redis_handler = RedisConnectionHandler()
                
                # Check for failover/sentinel configuration
                has_failover = redis_handler.has_failover_configured()
                sentinel_config = redis_handler.get_sentinel_config()
                
                # This should FAIL if failover is not configured
                if not has_failover:
                    pytest.fail("Redis failover not configured for staging environment")
                
                if not sentinel_config or len(sentinel_config.get('sentinels', [])) == 0:
                    pytest.fail("Redis sentinel configuration missing for staging")
                    
            except AttributeError:
                # Expected failure - failover methods don't exist
                pytest.fail("Redis failover configuration methods missing")

    def test_redis_ssl_tls_configuration_regression(self):
        """
        REGRESSION TEST: Redis SSL/TLS not configured for staging
        
        This test should FAIL initially if SSL/TLS is not properly configured.
        Root cause: Insecure Redis connections in staging environment.
        
        Expected failure: Redis SSL/TLS configuration missing or incorrect
        """
        # Arrange - Check Redis SSL/TLS configuration for staging
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'REDIS_SSL': 'true'  # Should require SSL in staging
        }, clear=False):
            
            try:
                redis_handler = RedisConnectionHandler()
                connection_config = redis_handler.get_connection_config()
                
                # Act & Assert - Check SSL configuration
                ssl_config = connection_config.get('ssl_config', {})
                
                ssl_issues = []
                
                # Check if SSL is enabled
                if not connection_config.get('ssl', False):
                    ssl_issues.append("SSL not enabled for staging Redis")
                
                # Check SSL certificate configuration
                if ssl_config and not ssl_config.get('ca_certs'):
                    ssl_issues.append("SSL CA certificates not configured")
                
                # Check SSL verification
                if ssl_config and ssl_config.get('cert_reqs') != 'required':
                    ssl_issues.append("SSL certificate verification not required")
                
                # This should FAIL if SSL configuration has issues
                if ssl_issues:
                    pytest.fail(f"Redis SSL/TLS configuration issues: {ssl_issues}")
                    
            except AttributeError:
                # Expected failure - SSL configuration methods don't exist
                pytest.fail("Redis SSL/TLS configuration methods missing")

    def test_redis_monitoring_configuration_regression(self):
        """
        REGRESSION TEST: Redis monitoring not configured for staging
        
        This test should FAIL initially if monitoring is not set up.
        Root cause: No Redis metrics or monitoring in staging environment.
        
        Expected failure: Redis monitoring configuration missing
        """
        # Arrange - Check Redis monitoring configuration
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=False):
            
            try:
                redis_handler = RedisConnectionHandler()
                
                # Check for monitoring configuration
                monitoring_config = redis_handler.get_monitoring_config()
                metrics_enabled = redis_handler.are_metrics_enabled()
                
                # Act & Assert - Check monitoring setup
                monitoring_issues = []
                
                if not metrics_enabled:
                    monitoring_issues.append("Redis metrics not enabled")
                
                if not monitoring_config.get('health_check_interval'):
                    monitoring_issues.append("Redis health check interval not configured")
                
                if not monitoring_config.get('connection_pool_monitoring'):
                    monitoring_issues.append("Redis connection pool monitoring not enabled")
                
                # This should FAIL if monitoring is not configured
                if monitoring_issues:
                    pytest.fail(f"Redis monitoring configuration issues: {monitoring_issues}")
                    
            except AttributeError:
                # Expected failure - monitoring methods don't exist
                pytest.fail("Redis monitoring configuration methods missing")
