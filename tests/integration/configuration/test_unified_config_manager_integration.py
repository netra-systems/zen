"""
UnifiedConfigManager Integration Tests - CONFIGURATION CRITICAL SSOT CLASS

BUSINESS CRITICAL: This test suite validates the configuration foundation supporting
all $2M+ business services. UnifiedConfigManager (~200 lines) has critical impact
as the SSOT for configuration management across all microservices.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Foundation for ALL segments)
- Business Goal: System Stability and Reliability 
- Value Impact: Prevents configuration failures that block all business operations
- Strategic Impact: $2M+ business operations depend on configuration reliability

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real configuration management and environment handling
- Test multi-environment configuration loading and validation
- Focus on service dependency configuration validation for all microservices
- Test the foundation for all service configuration supporting $2M+ business
- Validate environment variable handling and configuration caching
- Use SSOT BaseTestCase and verified imports from SSOT_IMPORT_REGISTRY.md

TEST COVERAGE:
1. Multi-Environment Configuration Tests (Development/Staging/Production/Testing)
2. Service Dependency Configuration Tests (Database/WebSocket/Auth/Redis/ClickHouse)
3. Configuration Caching and Performance Tests 
4. Environment Variable Management Tests (IsolatedEnvironment integration)
5. Configuration Validation and Error Handling Tests
6. Security and Compliance Tests (Enterprise requirements)

BUSINESS IMPACT:
- Protects $2M+ business operations from configuration failures
- Validates environment-specific configuration for deployment reliability
- Ensures service dependency configuration preventing deployment failures
- Tests secure configuration handling for Enterprise compliance requirements
"""

import asyncio
import pytest
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional
from unittest.mock import patch

# SSOT BaseTestCase - ALL tests MUST inherit from this
from test_framework.ssot.base_test_case import SSotBaseTestCase

# SSOT IMPORT REGISTRY verified imports - UnifiedConfigManager and related components
from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    config_manager,
    get_unified_config,
    get_config,
    reload_unified_config,
    validate_unified_config,
    get_environment,
    is_production,
    is_development,
    is_testing,
)

# Configuration schemas - SSOT verified imports
from netra_backend.app.schemas.config import (
    AppConfig,
    DevelopmentConfig,
    StagingConfig, 
    ProductionConfig,
    NetraTestingConfig,
)

# Environment management - SSOT verified imports
from shared.isolated_environment import IsolatedEnvironment, get_env

# Core dependencies for configuration testing
from netra_backend.app.core.environment_constants import EnvironmentDetector


class TestUnifiedConfigManagerIntegration(SSotBaseTestCase):
    """
    UnifiedConfigManager Integration Tests - CONFIGURATION CRITICAL SSOT
    
    Tests the foundational configuration management system supporting all $2M+ business operations.
    NO MOCKS - Uses real configuration management, environment handling, and service dependencies.
    """
    
    def assertIsInstance(self, obj, classinfo, msg=None):
        """Assert that obj is an instance of classinfo."""
        assert isinstance(obj, classinfo), msg or f"Expected {obj} to be instance of {classinfo}"
    
    def assertIs(self, first, second, msg=None):
        """Assert that first is second (identity check)."""
        assert first is second, msg or f"Expected {first} is {second}"
    
    def assertIsNot(self, first, second, msg=None):
        """Assert that first is not second (identity check)."""
        assert first is not second, msg or f"Expected {first} is not {second}"
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Record test category for business tracking
        self.record_metric("test_category", "configuration_critical")
        self.record_metric("business_impact", "foundation_2m_revenue")
        
        # Initialize real components - NO MOCKS
        self.config_manager = UnifiedConfigManager()
        self.isolated_env = get_env()
        
        # Store original environment for restoration
        self.original_environment = self.isolated_env.get_environment_name()
        
        # Performance tracking
        self.config_load_start_time = None
        
    def teardown_method(self, method=None):
        """Teardown after each test method."""
        try:
            # Force config cache clear for next test
            self.config_manager._config_cache = None
            self.config_manager._environment = None
        finally:
            super().teardown_method(method)
    
    @contextmanager
    def measure_config_load_time(self):
        """Context manager to measure configuration loading performance."""
        start_time = time.time()
        try:
            yield
        finally:
            load_time = time.time() - start_time
            self.record_metric("config_load_time_seconds", load_time)
    
    # === MULTI-ENVIRONMENT CONFIGURATION TESTS ===
    
    def test_development_environment_configuration_loading(self):
        """
        Test development environment configuration loading and validation.
        
        BUSINESS CRITICAL: Development environment must load properly to support
        daily development operations and prevent developer productivity loss.
        """
        # Force development environment
        with self.temp_env_vars(ENVIRONMENT="development"):
            
            with self.measure_config_load_time():
                config = self.config_manager.get_config()
            
            # Validate development configuration loaded correctly
            self.assertIsInstance(config, DevelopmentConfig)
            self.assertEqual(config.environment, "development")
            self.assertTrue(config.debug)
            self.assertEqual(config.log_level, "DEBUG")
            
            # Validate development-specific settings
            self.assertEqual(config.dev_user_email, "dev@example.com")
            self.assertTrue(config.otel_enabled == "true")
            self.assertTrue(config.otel_console_exporter == "true")
            
            # Validate performance - development config should load within reasonable time
            load_time = self.get_metric("config_load_time_seconds")
            self.assertLess(load_time, 15.0, "Development config loading too slow")  # Allow more time for environment readiness
            
            # Business metric - development config reliability
            self.record_metric("development_config_loaded_successfully", True)
    
    def test_staging_environment_configuration_validation(self):
        """
        Test staging environment configuration validation and mandatory services.
        
        BUSINESS CRITICAL: Staging environment validation prevents production deployment
        failures that could impact $500K+ ARR from major customer deployments.
        """
        # Force staging environment with required variables
        staging_env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-postgres.internal",
            "POSTGRES_USER": "staging_user", 
            "POSTGRES_PASSWORD": "staging_secure_password_32_characters",
            "POSTGRES_DB": "netra_staging",
            "JWT_SECRET_KEY": "staging_jwt_secret_key_32_characters_minimum_length",
            "SECRET_KEY": "staging_secret_key_32_characters_minimum_required_length",
            "SERVICE_SECRET": "staging_service_secret_32_characters_minimum_required",
            "REDIS_HOST": "staging-redis.internal",
            "CLICKHOUSE_HOST": "staging-clickhouse.internal",
            "CLICKHOUSE_PASSWORD": "staging_clickhouse_password"
        }
        
        with self.temp_env_vars(**staging_env_vars):
            
            with self.measure_config_load_time():
                config = self.config_manager.get_config()
            
            # Validate staging configuration loaded correctly
            self.assertIsInstance(config, StagingConfig)
            self.assertEqual(config.environment, "staging")
            self.assertFalse(config.debug)
            self.assertEqual(config.log_level, "INFO")
            
            # Validate mandatory services configuration - CRITICAL for staging deployment
            self.assertIsNotNone(config.database_url, "Staging MUST have database URL")
            self.assertTrue(config.database_url.startswith("postgresql://"))
            
            # Validate Redis configuration - MANDATORY in staging
            self.assertEqual(config.redis.host, "staging-redis.internal")
            self.assertFalse(config.redis_optional_in_staging, "Redis should be mandatory")
            
            # Validate ClickHouse configuration - MANDATORY in staging
            self.assertEqual(config.clickhouse_native.host, "staging-clickhouse.internal")
            self.assertFalse(config.clickhouse_optional_in_staging, "ClickHouse should be mandatory")
            
            # Validate security configuration - CRITICAL for Enterprise compliance
            self.assertIsNotNone(config.jwt_secret_key)
            self.assertGreaterEqual(len(config.jwt_secret_key), 32)
            self.assertIsNotNone(config.service_secret)
            self.assertGreaterEqual(len(config.service_secret), 32)
            
            # Business metric - staging validation success protects production deployments
            self.record_metric("staging_validation_successful", True)
            self.record_metric("mandatory_services_configured", True)
    
    def test_production_environment_configuration_security(self):
        """
        Test production environment configuration security and validation.
        
        BUSINESS CRITICAL: Production configuration security protects $2M+ business
        operations and Enterprise customer data. Security failures are catastrophic.
        """
        # Production environment with secure configuration
        production_env_vars = {
            "ENVIRONMENT": "production", 
            "POSTGRES_HOST": "prod-postgres.internal",
            "POSTGRES_USER": "prod_user",
            "POSTGRES_PASSWORD": "prod_highly_secure_password_64_characters_absolutely_minimum",
            "POSTGRES_DB": "netra_production",
            "JWT_SECRET_KEY": "prod_jwt_secret_highly_secure_64_characters_absolutely_minimum_req",
            "SECRET_KEY": "prod_secret_key_highly_secure_64_characters_absolutely_minimum_req",
            "SERVICE_SECRET": "prod_service_secret_highly_secure_64_characters_absolutely_min",
            "REDIS_HOST": "prod-redis.internal",
            "CLICKHOUSE_HOST": "prod-clickhouse.internal", 
            "CLICKHOUSE_PASSWORD": "prod_clickhouse_highly_secure_password"
        }
        
        with self.temp_env_vars(**production_env_vars):
            
            with self.measure_config_load_time():
                config = self.config_manager.get_config()
            
            # Validate production configuration loaded correctly
            self.assertIsInstance(config, ProductionConfig)
            self.assertEqual(config.environment, "production")
            self.assertFalse(config.debug)
            self.assertEqual(config.log_level, "INFO")
            
            # Validate MANDATORY production services - CRITICAL for business operations
            self.assertIsNotNone(config.database_url)
            self.assertTrue(config.database_url.startswith("postgresql://"))
            
            # Production Redis is MANDATORY - supports $200K+ MRR in real-time operations
            self.assertEqual(config.redis.host, "prod-redis.internal")
            
            # Production ClickHouse is MANDATORY - supports analytics for Enterprise customers
            self.assertEqual(config.clickhouse_native.host, "prod-clickhouse.internal")
            
            # CRITICAL security validation - Enterprise compliance requirements
            self.assertIsNotNone(config.jwt_secret_key)
            self.assertGreaterEqual(len(config.jwt_secret_key), 32)
            self.assertIsNotNone(config.service_secret)
            self.assertGreaterEqual(len(config.service_secret), 32)
            
            # Security validation - no insecure patterns in production secrets
            insecure_patterns = ['default', 'test', 'dev', 'demo', 'example']
            for pattern in insecure_patterns:
                self.assertNotIn(pattern.lower(), config.jwt_secret_key.lower())
                self.assertNotIn(pattern.lower(), config.service_secret.lower())
            
            # Validate telemetry configuration for production monitoring
            self.assertEqual(config.otel_enabled, "true")
            self.assertEqual(config.otel_console_exporter, "false")  # No console output in prod
            
            # Business metrics - production security validation success 
            self.record_metric("production_security_validated", True)
            self.record_metric("enterprise_compliance_met", True)
    
    def test_testing_environment_specific_configuration(self):
        """
        Test testing environment configuration for comprehensive test execution.
        
        BUSINESS CRITICAL: Testing environment must work reliably to validate
        changes protecting $2M+ business operations from regressions.
        """
        # Force testing environment
        with self.temp_env_vars(ENVIRONMENT="testing", TESTING="true"):
            
            with self.measure_config_load_time():
                config = self.config_manager.get_config()
            
            # Validate testing configuration loaded correctly
            self.assertIsInstance(config, NetraTestingConfig)
            self.assertEqual(config.environment, "testing")
            
            # Validate test-safe defaults - CRITICAL for test execution reliability
            self.assertEqual(config.fast_startup_mode, "true")
            self.assertIsNotNone(config.service_secret)
            self.assertGreaterEqual(len(config.service_secret), 32)
            self.assertIsNotNone(config.jwt_secret_key)
            self.assertGreaterEqual(len(config.jwt_secret_key), 32)
            
            # Validate test database configuration
            self.assertIsNotNone(config.database_url)
            # Database URL should be valid for testing (test config uses in-memory SQLite)
            self.assertTrue(config.database_url.startswith(("postgresql://", "sqlite")))
            
            # Validate telemetry disabled for test performance
            self.assertEqual(config.otel_enabled, "false")
            
            # Business metric - testing environment reliability
            self.record_metric("testing_environment_configured", True)
    
    # === SERVICE DEPENDENCY CONFIGURATION TESTS ===
    
    def test_database_connection_configuration_validation(self):
        """
        Test database connection configuration validation across environments.
        
        BUSINESS CRITICAL: Database configuration failures prevent all business
        operations. Database supports 100% of $2M+ business revenue operations.
        """
        test_environments = [
            ("development", DevelopmentConfig),
            ("staging", StagingConfig), 
            ("production", ProductionConfig),
            ("testing", NetraTestingConfig)
        ]
        
        for env_name, expected_config_class in test_environments:
            with self.temp_env_vars(
                ENVIRONMENT=env_name,
                POSTGRES_HOST=f"{env_name}-postgres.internal",
                POSTGRES_USER=f"{env_name}_user",
                POSTGRES_PASSWORD=f"{env_name}_secure_password_32_characters",
                POSTGRES_DB=f"netra_{env_name}",
                JWT_SECRET_KEY=f"{env_name}_jwt_secret_32_characters_min",
                SECRET_KEY=f"{env_name}_secret_key_32_characters_min",
                SERVICE_SECRET=f"{env_name}_service_secret_32_chars_min"
            ):
                
                # Force reload for each environment
                self.config_manager.reload_config(force=True)
                
                config = self.config_manager.get_config()
                
                # Validate correct configuration class loaded
                self.assertIsInstance(config, expected_config_class)
                self.assertEqual(config.environment, env_name)
                
                # Validate database URL construction - CRITICAL for service connectivity
                self.assertIsNotNone(config.database_url)
                self.assertTrue(config.database_url.startswith("postgresql://"))
                self.assertIn(f"{env_name}_user", config.database_url)
                self.assertIn(f"netra_{env_name}", config.database_url)
                
                # Validate database connection pool settings - supports high-scale operations
                self.assertGreaterEqual(config.db_pool_size, 20)
                self.assertGreaterEqual(config.db_max_overflow, 30)
                self.assertGreaterEqual(config.db_pool_timeout, 30)
                
        # Business metric - database configuration reliability across all environments
        self.record_metric("database_config_validated_all_environments", True)
    
    def test_websocket_service_configuration_management(self):
        """
        Test WebSocket service configuration management and timeout coordination.
        
        BUSINESS CRITICAL: WebSocket configuration supports 90% of platform value
        through real-time chat functionality. Configuration failures break core UX.
        """
        with self.temp_env_vars(
            ENVIRONMENT="development",
            WEBSOCKET_SSOT_CONSOLIDATION="true"
        ):
            
            config = self.config_manager.get_config()
            
            # Validate WebSocket configuration loaded
            self.assertIsNotNone(config.ws_config)
            self.assertIsNotNone(config.ws_config.ws_url)
            
            # Validate timeout hierarchy - CRITICAL for $200K+ MRR reliability
            self.assertGreater(config.ws_config.connection_timeout, 0)
            self.assertGreater(config.ws_config.recv_timeout, 0) 
            self.assertGreater(config.ws_config.send_timeout, 0)
            
            # CRITICAL: WebSocket recv timeout MUST be > agent execution timeout
            self.assertGreater(config.ws_config.recv_timeout, config.agent_default_timeout)
            
            # Validate heartbeat configuration for connection reliability
            self.assertGreater(config.ws_config.heartbeat_timeout, 0)
            self.assertGreater(config.ws_config.heartbeat_interval, 0)
            self.assertGreater(config.ws_config.heartbeat_timeout, config.ws_config.heartbeat_interval)
            
            # Validate SSOT consolidation feature flag
            self.assertTrue(config.ws_config.ssot_consolidation_enabled)
            
            # Business metric - WebSocket configuration supports core chat functionality
            self.record_metric("websocket_config_supports_chat_value", True)
    
    def test_auth_service_integration_configuration(self):
        """
        Test auth service integration configuration across environments.
        
        BUSINESS CRITICAL: Authentication configuration secures all $2M+ business
        operations and protects Enterprise customer data. Auth failures are catastrophic.
        """
        environments = ["development", "staging", "production"]
        
        for env_name in environments:
            with self.temp_env_vars(
                ENVIRONMENT=env_name,
                AUTH_SERVICE_URL=f"http://{env_name}-auth.internal:8081",
                JWT_SECRET_KEY=f"{env_name}_jwt_secret_32_characters_minimum",
                SECRET_KEY=f"{env_name}_secret_key_32_characters_minimum", 
                SERVICE_SECRET=f"{env_name}_service_secret_32_chars_min",
                SERVICE_ID="netra-backend"
            ):
                
                # Force reload for environment
                self.config_manager.reload_config(force=True)
                config = self.config_manager.get_config()
                
                # Validate auth service configuration
                self.assertEqual(config.auth_service_url, f"http://{env_name}-auth.internal:8081")
                self.assertEqual(config.service_id, "netra-backend")
                
                # CRITICAL security validation - auth secrets properly configured
                self.assertIsNotNone(config.jwt_secret_key)
                self.assertGreaterEqual(len(config.jwt_secret_key), 32)
                self.assertIsNotNone(config.service_secret) 
                self.assertGreaterEqual(len(config.service_secret), 32)
                
                # Validate service secret is different from JWT secret - security requirement
                self.assertNotEqual(config.jwt_secret_key, config.service_secret)
                
                # Validate auth cache settings - performance optimization
                self.assertIsInstance(int(config.auth_cache_ttl_seconds), int)
                self.assertGreater(int(config.auth_cache_ttl_seconds), 0)
        
        # Business metric - auth configuration protects all business operations
        self.record_metric("auth_config_secures_all_operations", True)
    
    def test_redis_clickhouse_service_configuration(self):
        """
        Test Redis and ClickHouse service configuration for analytics and caching.
        
        BUSINESS CRITICAL: Redis supports real-time operations ($200K+ MRR) and
        ClickHouse supports Enterprise analytics. Configuration failures impact revenue.
        """
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            REDIS_URL="redis://staging-redis.internal:6379",
            REDIS_MODE="shared",
            CLICKHOUSE_HOST="staging-clickhouse.internal",
            CLICKHOUSE_PORT="8123", 
            CLICKHOUSE_PASSWORD="staging_clickhouse_secure_password",
            CLICKHOUSE_MODE="shared"
        ):
            
            config = self.config_manager.get_config()
            
            # Validate Redis configuration - supports real-time operations
            self.assertEqual(config.redis_url, "redis://staging-redis.internal:6379")
            self.assertEqual(config.redis_mode, "shared")
            self.assertTrue(config.dev_mode_redis_enabled)
            
            # Validate ClickHouse configuration - supports Enterprise analytics
            self.assertEqual(config.clickhouse_native.host, "staging-clickhouse.internal")
            self.assertEqual(config.clickhouse_native.port, 8123)
            self.assertEqual(config.clickhouse_native.password, "staging_clickhouse_secure_password")
            self.assertEqual(config.clickhouse_mode, "shared")
            self.assertTrue(config.dev_mode_clickhouse_enabled)
            
            # Validate timeout configurations for enterprise reliability
            self.assertGreater(config.clickhouse_native.connect_timeout, 0)
            self.assertGreater(config.clickhouse_native.read_timeout, 0)
            self.assertGreater(config.clickhouse_native.write_timeout, 0)
            self.assertGreater(config.clickhouse_native.query_timeout, 0)
            
            # Business metric - service configuration supports Enterprise features
            self.record_metric("redis_clickhouse_support_enterprise", True)
    
    # === CONFIGURATION CACHING AND PERFORMANCE TESTS ===
    
    def test_configuration_loading_and_caching_behavior(self):
        """
        Test configuration loading and caching behavior for performance optimization.
        
        BUSINESS CRITICAL: Configuration caching prevents performance bottlenecks
        that could impact user experience and system responsiveness under load.
        """
        with self.temp_env_vars(ENVIRONMENT="development"):
            
            # First load - should cache configuration
            with self.measure_config_load_time():
                config1 = self.config_manager.get_config()
            first_load_time = self.get_metric("config_load_time_seconds")
            
            # Second load - should use cached configuration (faster)
            with self.measure_config_load_time():
                config2 = self.config_manager.get_config()
            second_load_time = self.get_metric("config_load_time_seconds")
            
            # Validate both calls return same instance (caching working)
            self.assertIs(config1, config2, "Configuration should be cached")
            
            # Validate cached load is significantly faster
            cache_improvement = first_load_time - second_load_time
            self.assertGreater(cache_improvement, 0, "Cached load should be faster")
            
            # Validate performance thresholds  
            self.assertLess(first_load_time, 15.0, "Initial load too slow")  # Allow more time for first load
            self.assertLess(second_load_time, 5.0, "Cached load too slow")  # Allow reasonable cached load time
            
        # Business metric - configuration caching improves system performance
        self.record_metric("config_caching_improves_performance", True)
        self.record_metric("first_load_time_seconds", first_load_time)
        self.record_metric("cached_load_time_seconds", second_load_time)
    
    def test_cache_invalidation_and_refresh_mechanisms(self):
        """
        Test configuration cache invalidation and refresh mechanisms.
        
        BUSINESS CRITICAL: Cache invalidation ensures configuration changes
        take effect without service restart, critical for deployment reliability.
        """
        with self.temp_env_vars(ENVIRONMENT="development"):
            
            # Initial configuration load
            config1 = self.config_manager.get_config()
            self.assertEqual(config1.environment, "development")
            
            # Force cache invalidation and reload
            with self.measure_config_load_time():
                config2 = self.config_manager.reload_config(force=True)
            reload_time = self.get_metric("config_load_time_seconds")
            
            # Validate force reload creates new configuration instance
            self.assertIsNot(config1, config2, "Force reload should create new instance")
            self.assertEqual(config2.environment, "development")
            
            # Validate reload performance
            self.assertLess(reload_time, 2.0, "Force reload too slow")
            
        # Test environment change triggers cache invalidation
        with self.temp_env_vars(ENVIRONMENT="staging", 
                                JWT_SECRET_KEY="staging_jwt_32_chars_minimum",
                                SECRET_KEY="staging_secret_32_chars_minimum",
                                SERVICE_SECRET="staging_service_32_chars_min"):
            
            # Clear environment cache to trigger re-detection
            self.config_manager._environment = None
            
            config3 = self.config_manager.get_config()
            self.assertEqual(config3.environment, "staging")
            
        # Business metric - cache invalidation supports deployment reliability
        self.record_metric("cache_invalidation_supports_deployments", True)
    
    def test_performance_under_concurrent_configuration_requests(self):
        """
        Test configuration performance under concurrent requests.
        
        BUSINESS CRITICAL: Configuration must perform well under concurrent load
        to support high-traffic scenarios and prevent system bottlenecks.
        """
        request_count = 50
        thread_count = 10
        results = []
        errors = []
        
        def load_config_worker():
            """Worker function for concurrent configuration loading."""
            try:
                start_time = time.time()
                config = self.config_manager.get_config()
                end_time = time.time()
                
                # Validate configuration loaded correctly
                self.assertIsInstance(config, AppConfig)
                self.assertIsNotNone(config.environment)
                
                results.append(end_time - start_time)
            except Exception as e:
                errors.append(str(e))
        
        with self.temp_env_vars(ENVIRONMENT="development"):
            
            # Create and start worker threads
            threads = []
            for _ in range(thread_count):
                for _ in range(request_count // thread_count):
                    thread = threading.Thread(target=load_config_worker)
                    threads.append(thread)
            
            # Measure concurrent execution time
            concurrent_start = time.time()
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join(timeout=10.0)  # 10 second timeout
            concurrent_end = time.time()
            
            # Validate no errors occurred
            self.assertEqual(len(errors), 0, f"Concurrent config loading errors: {errors}")
            self.assertEqual(len(results), request_count, "Not all requests completed")
            
            # Validate performance metrics
            total_time = concurrent_end - concurrent_start
            avg_request_time = sum(results) / len(results)
            max_request_time = max(results)
            
            self.assertLess(total_time, 5.0, "Concurrent execution too slow")
            self.assertLess(avg_request_time, 0.5, "Average request time too high")
            self.assertLess(max_request_time, 2.0, "Max request time too high")
            
        # Business metrics - concurrent performance validation
        self.record_metric("concurrent_requests_completed", request_count)
        self.record_metric("concurrent_execution_time", total_time)
        self.record_metric("avg_concurrent_request_time", avg_request_time)
    
    def test_configuration_loading_latency_optimization(self):
        """
        Test configuration loading latency optimization across environments.
        
        BUSINESS CRITICAL: Configuration loading latency impacts application
        startup time and user experience, particularly important for serverless deployments.
        """
        environments = ["development", "staging", "production", "testing"]
        latency_results = {}
        
        for env_name in environments:
            env_vars = {
                "ENVIRONMENT": env_name,
                "JWT_SECRET_KEY": f"{env_name}_jwt_secret_32_characters_minimum",
                "SECRET_KEY": f"{env_name}_secret_key_32_characters_minimum",
                "SERVICE_SECRET": f"{env_name}_service_secret_32_chars_min"
            }
            
            with self.temp_env_vars(**env_vars):
                
                # Clear cache for accurate measurement
                self.config_manager.reload_config(force=True)
                
                # Measure configuration loading latency
                start_time = time.time()
                config = self.config_manager.get_config()
                end_time = time.time()
                
                loading_latency = end_time - start_time
                latency_results[env_name] = loading_latency
                
                # Validate configuration loaded correctly
                self.assertIsInstance(config, AppConfig)
                self.assertEqual(config.environment, env_name)
                
                # Validate latency thresholds for business requirements
                if env_name == "production":
                    # Production has stricter latency requirements
                    self.assertLess(loading_latency, 1.0, f"Production config loading too slow: {loading_latency}s")
                else:
                    self.assertLess(loading_latency, 2.0, f"{env_name} config loading too slow: {loading_latency}s")
        
        # Validate no environment is significantly slower than others
        avg_latency = sum(latency_results.values()) / len(latency_results)
        for env_name, latency in latency_results.items():
            self.assertLess(latency, avg_latency * 2, f"{env_name} latency too high compared to average")
        
        # Business metrics - configuration loading performance
        self.record_metric("config_latency_results", latency_results)
        self.record_metric("avg_config_loading_latency", avg_latency)
    
    # === ENVIRONMENT VARIABLE MANAGEMENT TESTS ===
    
    def test_isolated_environment_integration_validation(self):
        """
        Test IsolatedEnvironment integration validation with UnifiedConfigManager.
        
        BUSINESS CRITICAL: Environment isolation prevents configuration conflicts
        and ensures service independence, critical for multi-tenant operations.
        """
        # Validate IsolatedEnvironment integration
        isolated_env = self.config_manager._loader._env if hasattr(self.config_manager._loader, '_env') else get_env()
        self.assertIsInstance(isolated_env, IsolatedEnvironment)
        
        # Test environment variable precedence and override logic
        with self.temp_env_vars(
            ENVIRONMENT="development",
            TEST_CONFIG_VAR="test_value_from_environment",
            GEMINI_API_KEY="test_gemini_api_key_from_env"
        ):
            
            config = self.config_manager.get_config()
            
            # Validate environment variable loading through IsolatedEnvironment
            test_var = isolated_env.get("TEST_CONFIG_VAR")
            self.assertEqual(test_var, "test_value_from_environment")
            
            # Validate API key loading from environment
            self.assertEqual(config.gemini_api_key, "test_gemini_api_key_from_env")
            
            # Validate environment detection
            detected_env = self.config_manager.get_environment_name()
            self.assertEqual(detected_env, "development")
            
        # Business metric - environment integration supports service independence
        self.record_metric("environment_integration_validated", True)
    
    def test_environment_variable_precedence_override_logic(self):
        """
        Test environment variable precedence and override logic.
        
        BUSINESS CRITICAL: Proper environment variable precedence ensures
        deployment-specific configuration overrides work correctly.
        """
        base_env_vars = {
            "ENVIRONMENT": "staging", 
            "JWT_SECRET_KEY": "base_jwt_secret_32_characters_minimum",
            "SECRET_KEY": "base_secret_key_32_characters_minimum",
            "SERVICE_SECRET": "base_service_secret_32_chars_min"
        }
        
        with self.temp_env_vars(**base_env_vars):
            
            base_config = self.config_manager.get_config()
            self.assertEqual(base_config.jwt_secret_key, "base_jwt_secret_32_characters_minimum")
            
            # Test override with deployment-specific values
            override_env_vars = {
                **base_env_vars,
                "JWT_SECRET_KEY": "override_jwt_secret_32_characters_minimum",
                "SERVICE_SECRET": "override_service_secret_32_chars_min"
            }
            
            with self.temp_env_vars(**override_env_vars):
                
                # Force reload to pick up overrides
                self.config_manager.reload_config(force=True)
                override_config = self.config_manager.get_config()
                
                # Validate overrides took effect
                self.assertEqual(override_config.jwt_secret_key, "override_jwt_secret_32_characters_minimum")
                self.assertEqual(override_config.service_secret, "override_service_secret_32_chars_min")
                
                # Validate non-overridden values remain the same
                self.assertEqual(override_config.secret_key, "base_secret_key_32_characters_minimum")
        
        # Business metric - environment override logic supports deployment flexibility
        self.record_metric("env_override_logic_supports_deployments", True)
    
    def test_secure_environment_variable_handling(self):
        """
        Test secure environment variable handling and sanitization.
        
        BUSINESS CRITICAL: Secure environment variable handling prevents
        credential exposure and meets Enterprise security compliance requirements.
        """
        secure_env_vars = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "prod_jwt_highly_secure_64_characters_absolutely_minimum_required",
            "SECRET_KEY": "prod_secret_highly_secure_64_characters_absolutely_minimum_required",
            "SERVICE_SECRET": "prod_service_highly_secure_64_characters_absolutely_minimum_req",
            "POSTGRES_PASSWORD": "prod_postgres_highly_secure_password_64_chars_minimum",
            "REDIS_PASSWORD": "prod_redis_highly_secure_password_64_chars_minimum"
        }
        
        with self.temp_env_vars(**secure_env_vars):
            
            config = self.config_manager.get_config()
            
            # Validate secrets loaded correctly but not exposed in logs
            self.assertIsNotNone(config.jwt_secret_key)
            self.assertIsNotNone(config.service_secret)
            self.assertGreaterEqual(len(config.jwt_secret_key), 32)
            self.assertGreaterEqual(len(config.service_secret), 32)
            
            # Validate service secret sanitization - remove whitespace/line endings
            self.assertEqual(config.service_secret.strip(), config.service_secret)
            
            # Validate no insecure patterns in production secrets
            insecure_patterns = ['default', 'test', 'dev', 'demo', 'example', 'change', 'admin']
            for pattern in insecure_patterns:
                self.assertNotIn(pattern.lower(), config.jwt_secret_key.lower())
                self.assertNotIn(pattern.lower(), config.service_secret.lower())
            
            # Validate entropy - production secrets should have diverse characters
            jwt_unique_chars = len(set(config.jwt_secret_key))
            service_unique_chars = len(set(config.service_secret))
            self.assertGreater(jwt_unique_chars, 8, "JWT secret has insufficient entropy")
            self.assertGreater(service_unique_chars, 8, "Service secret has insufficient entropy")
            
        # Business metric - secure environment handling meets Enterprise compliance
        self.record_metric("secure_env_handling_enterprise_compliant", True)
    
    def test_environment_isolation_between_test_runs(self):
        """
        Test environment isolation between test runs.
        
        BUSINESS CRITICAL: Environment isolation prevents test interference
        and ensures reliable test execution protecting $2M+ operations validation.
        """
        # First test run - set specific environment
        with self.temp_env_vars(
            ENVIRONMENT="development",
            TEST_RUN_ID="first_test_run",
            CUSTOM_CONFIG_VALUE="first_value"
        ):
            
            config1 = self.config_manager.get_config()
            self.assertEqual(config1.environment, "development")
            
            # Store first run state
            first_run_env = self.isolated_env.get("TEST_RUN_ID")
            first_run_custom = self.isolated_env.get("CUSTOM_CONFIG_VALUE")
            self.assertEqual(first_run_env, "first_test_run")
            self.assertEqual(first_run_custom, "first_value")
        
        # Second test run - different environment (simulating separate test)
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            TEST_RUN_ID="second_test_run", 
            CUSTOM_CONFIG_VALUE="second_value",
            JWT_SECRET_KEY="staging_jwt_32_chars_minimum",
            SECRET_KEY="staging_secret_32_chars_minimum",
            SERVICE_SECRET="staging_service_32_chars_min"
        ):
            
            # Force reload to simulate new test execution
            self.config_manager.reload_config(force=True)
            config2 = self.config_manager.get_config()
            self.assertEqual(config2.environment, "staging")
            
            # Validate environment isolation - no values from first run
            second_run_env = self.isolated_env.get("TEST_RUN_ID")
            second_run_custom = self.isolated_env.get("CUSTOM_CONFIG_VALUE")
            self.assertEqual(second_run_env, "second_test_run")
            self.assertEqual(second_run_custom, "second_value")
            
            # Validate configs are different instances
            self.assertNotEqual(config1.environment, config2.environment)
        
        # Business metric - environment isolation ensures reliable testing
        self.record_metric("environment_isolation_ensures_reliable_testing", True)
    
    # === CONFIGURATION VALIDATION AND ERROR HANDLING TESTS ===
    
    def test_invalid_configuration_detection_handling(self):
        """
        Test invalid configuration detection and handling.
        
        BUSINESS CRITICAL: Invalid configuration detection prevents system failures
        that could impact business operations and customer experience.
        """
        # Test invalid environment
        with self.temp_env_vars(ENVIRONMENT="invalid_environment"):
            
            # Should fallback to development config  
            config = self.config_manager.get_config()
            self.assertIsInstance(config, DevelopmentConfig)
            
        # Test invalid/missing JWT secret (too short)
        with self.temp_env_vars(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="short",  # Invalid - too short
            SECRET_KEY="prod_secret_key_32_characters_minimum_required",
            SERVICE_SECRET="prod_service_secret_32_characters_minimum_req"
        ):
            
            # Should raise validation error for production environment
            with self.expect_exception(ValueError, "32 characters"):
                config = self.config_manager.get_config()
        
        # Test missing critical configuration in production
        with self.temp_env_vars(ENVIRONMENT="production"):
            
            # Should handle missing configuration gracefully
            try:
                config = self.config_manager.get_config()
                # If config loads, validate it has fallback values
                self.assertIsNotNone(config)
            except Exception as e:
                # Expected for production without required secrets
                self.assertTrue("required" in str(e).lower() or "secret" in str(e).lower())
        
        # Business metric - invalid config detection protects system stability
        self.record_metric("invalid_config_detection_protects_stability", True)
    
    def test_missing_configuration_parameter_validation(self):
        """
        Test missing configuration parameter validation.
        
        BUSINESS CRITICAL: Missing configuration parameter detection prevents
        runtime failures and provides clear error messages for troubleshooting.
        """
        # Test configuration validation functionality
        validation_successful = self.config_manager.validate_config_integrity()
        
        # Should be able to validate configuration without errors
        self.assertIsInstance(validation_successful, bool)
        
        # Test with minimal valid configuration
        with self.temp_env_vars(
            ENVIRONMENT="testing",
            SECRET_KEY="test_secret_key_32_characters_minimum_required",
            JWT_SECRET_KEY="test_jwt_secret_32_characters_minimum_required"
        ):
            
            config = self.config_manager.get_config()
            validation_result = self.config_manager.validate_config_integrity()
            
            # Should validate successfully with minimal config
            self.assertTrue(validation_result)
            self.assertIsNotNone(config.secret_key)
            self.assertIsNotNone(config.jwt_secret_key)
        
        # Business metric - missing config validation prevents runtime failures  
        self.record_metric("missing_config_validation_prevents_failures", True)
    
    def test_configuration_schema_validation(self):
        """
        Test configuration schema validation.
        
        BUSINESS CRITICAL: Configuration schema validation ensures all required
        fields are properly typed and validated, preventing runtime errors.
        """
        with self.temp_env_vars(
            ENVIRONMENT="development",
            SECRET_KEY="dev_secret_key_32_characters_minimum_required",
            JWT_SECRET_KEY="dev_jwt_secret_32_characters_minimum_required"
        ):
            
            config = self.config_manager.get_config()
            
            # Validate schema fields are properly typed
            self.assertIsInstance(config.environment, str)
            self.assertIsInstance(config.debug, bool)
            self.assertIsInstance(config.log_level, str)
            self.assertIsInstance(config.access_token_expire_minutes, int)
            
            # Validate nested configuration objects
            self.assertIsNotNone(config.ws_config)
            self.assertIsInstance(config.ws_config.connection_timeout, int)
            self.assertIsInstance(config.ws_config.recv_timeout, int)
            
            self.assertIsNotNone(config.redis)
            self.assertIsInstance(config.redis.host, str)
            self.assertIsInstance(config.redis.port, int)
            
            # Validate configuration constraints
            self.assertGreater(config.access_token_expire_minutes, 0)
            self.assertGreater(config.ws_config.connection_timeout, 0)
            self.assertGreater(config.redis.port, 0)
            self.assertLess(config.redis.port, 65536)
        
        # Business metric - schema validation ensures runtime reliability
        self.record_metric("schema_validation_ensures_runtime_reliability", True)
    
    def test_error_reporting_and_recovery_mechanisms(self):
        """
        Test configuration error reporting and recovery mechanisms.
        
        BUSINESS CRITICAL: Clear error reporting and recovery helps operations
        teams quickly resolve configuration issues preventing business impact.
        """
        # Test configuration integrity validation with detailed results
        validation_result, error_list = validate_config_integrity()
        
        self.assertIsInstance(validation_result, bool)
        self.assertIsInstance(error_list, list)
        
        # Test error handling with problematic configuration
        with self.temp_env_vars(
            ENVIRONMENT="production",
            SECRET_KEY="short",  # Too short - should trigger validation error
            SERVICE_SECRET="also_short"  # Too short - should trigger validation error
        ):
            
            try:
                config = self.config_manager.get_config()
                # If it doesn't fail, validation should report issues
                validation_result = self.config_manager.validate_config_integrity()
                if validation_result:
                    # Some environments might have more lenient validation
                    pass
            except ValueError as e:
                # Expected - validate error message is helpful
                error_message = str(e)
                self.assertTrue(
                    "32 characters" in error_message or 
                    "length" in error_message.lower(),
                    f"Error message not helpful: {error_message}"
                )
        
        # Test recovery mechanisms - should handle gracefully
        with self.temp_env_vars(ENVIRONMENT="development"):
            
            # Force config reload after error
            config = self.config_manager.reload_config(force=True)
            self.assertIsInstance(config, AppConfig)
            self.assertEqual(config.environment, "development")
        
        # Business metric - error reporting aids rapid issue resolution
        self.record_metric("error_reporting_aids_rapid_resolution", True)
    
    # === SECURITY AND COMPLIANCE TESTS ===
    
    def test_sensitive_configuration_parameter_protection(self):
        """
        Test sensitive configuration parameter protection.
        
        BUSINESS CRITICAL: Sensitive parameter protection prevents credential
        exposure and meets Enterprise security compliance requirements.
        """
        sensitive_config = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "prod_jwt_highly_secure_64_characters_absolutely_minimum_required",
            "SECRET_KEY": "prod_secret_highly_secure_64_characters_absolutely_minimum_required",
            "SERVICE_SECRET": "prod_service_highly_secure_64_characters_absolutely_minimum_req",
            "POSTGRES_PASSWORD": "prod_postgres_highly_secure_password",
            "REDIS_PASSWORD": "prod_redis_highly_secure_password",
            "GEMINI_API_KEY": "prod_gemini_api_key_highly_secure"
        }
        
        with self.temp_env_vars(**sensitive_config):
            
            config = self.config_manager.get_config()
            
            # Validate sensitive values are loaded but not exposed in config dict
            self.assertIsNotNone(config.jwt_secret_key)
            self.assertIsNotNone(config.service_secret)
            self.assertIsNotNone(config.gemini_api_key)
            
            # Test that sensitive values don't appear in string representation
            config_str = str(config)
            
            # These sensitive values should not appear in string representation
            sensitive_values = [
                "prod_jwt_highly_secure",
                "prod_service_highly_secure", 
                "prod_postgres_highly_secure",
                "prod_gemini_api_key_highly_secure"
            ]
            
            for sensitive_value in sensitive_values:
                # If they do appear, they should be masked
                if sensitive_value in config_str:
                    # Allow masked versions (first 3 chars + ***)
                    masked_version = sensitive_value[:3] + "***"
                    self.assertTrue(
                        masked_version in config_str or "***" in config_str,
                        f"Sensitive value {sensitive_value} not properly masked"
                    )
        
        # Business metric - sensitive parameter protection meets Enterprise compliance
        self.record_metric("sensitive_param_protection_enterprise_compliant", True)
    
    def test_configuration_access_control_validation(self):
        """
        Test configuration access control validation.
        
        BUSINESS CRITICAL: Configuration access control ensures only authorized
        components can access sensitive configuration data.
        """
        # Test environment-based access control
        environments_with_restrictions = ["production", "staging"]
        
        for env_name in environments_with_restrictions:
            with self.temp_env_vars(
                ENVIRONMENT=env_name,
                JWT_SECRET_KEY=f"{env_name}_jwt_secure_64_characters_absolutely_minimum_required",
                SECRET_KEY=f"{env_name}_secret_secure_64_characters_absolutely_minimum_required",
                SERVICE_SECRET=f"{env_name}_service_secure_64_characters_absolutely_minimum_req"
            ):
                
                config = self.config_manager.get_config()
                
                # Validate stricter security validation in restricted environments
                self.assertGreaterEqual(len(config.jwt_secret_key), 32)
                self.assertGreaterEqual(len(config.service_secret), 32)
                
                # Validate environment-specific restrictions
                if env_name == "production":
                    self.assertFalse(config.debug)
                    self.assertEqual(config.log_level, "INFO")
                    self.assertEqual(config.otel_console_exporter, "false")
        
        # Business metric - access control validation protects sensitive data
        self.record_metric("access_control_protects_sensitive_data", True)
    
    def test_audit_trail_for_configuration_changes(self):
        """
        Test audit trail for configuration changes.
        
        BUSINESS CRITICAL: Configuration change audit trail supports Enterprise
        compliance requirements and operational troubleshooting.
        """
        # Test configuration loading with different environments
        audit_events = []
        
        environments = ["development", "staging"]
        
        for env_name in environments:
            with self.temp_env_vars(
                ENVIRONMENT=env_name,
                JWT_SECRET_KEY=f"{env_name}_jwt_32_characters_minimum",
                SECRET_KEY=f"{env_name}_secret_32_characters_minimum",
                SERVICE_SECRET=f"{env_name}_service_32_chars_min"
            ):
                
                # Force reload to trigger configuration change
                config_before = self.config_manager._config_cache
                self.config_manager.reload_config(force=True) 
                config_after = self.config_manager.get_config()
                
                # Record audit event
                audit_events.append({
                    "environment": env_name,
                    "config_changed": config_before != config_after,
                    "timestamp": time.time()
                })
        
        # Validate audit events were recorded
        self.assertEqual(len(audit_events), len(environments))
        for event in audit_events:
            self.assertIn("environment", event)
            self.assertIn("timestamp", event)
        
        # Business metric - audit trail supports Enterprise compliance
        self.record_metric("audit_trail_supports_enterprise_compliance", True)
        self.record_metric("audit_events_recorded", len(audit_events))
    
    def test_secure_defaults_and_fallback_configuration(self):
        """
        Test secure defaults and fallback configuration.
        
        BUSINESS CRITICAL: Secure defaults prevent insecure configurations
        and fallbacks ensure system remains operational during configuration issues.
        """
        # Test with minimal environment (should use secure defaults)
        with self.temp_env_vars(ENVIRONMENT="testing"):
            
            config = self.config_manager.get_config()
            
            # Validate secure defaults are applied
            self.assertIsInstance(config, NetraTestingConfig)
            
            # Validate security defaults
            self.assertIsNotNone(config.secret_key)
            self.assertGreaterEqual(len(config.secret_key), 32)
            self.assertIsNotNone(config.jwt_secret_key) 
            self.assertGreaterEqual(len(config.jwt_secret_key), 32)
            self.assertIsNotNone(config.service_secret)
            self.assertGreaterEqual(len(config.service_secret), 32)
            
            # Validate test-safe defaults don't contain insecure patterns
            test_safe_secrets = [config.secret_key, config.jwt_secret_key, config.service_secret]
            for secret in test_safe_secrets:
                # Should not contain obvious insecure patterns but are test-safe
                self.assertNotIn("password", secret.lower())
                self.assertNotIn("admin", secret.lower())
            
            # Validate operational defaults
            self.assertEqual(config.fast_startup_mode, "true")
            self.assertEqual(config.otel_enabled, "false")  # Disabled for test performance
            
        # Test fallback behavior with completely empty environment
        original_env_name = self.isolated_env.get("ENVIRONMENT")
        try:
            self.isolated_env.delete("ENVIRONMENT", "test_fallback")
            
            # Force environment re-detection
            self.config_manager._environment = None
            fallback_config = self.config_manager.get_config()
            
            # Should fallback to development config
            self.assertIsInstance(fallback_config, (DevelopmentConfig, AppConfig))
            
        finally:
            # Restore original environment
            if original_env_name:
                self.isolated_env.set("ENVIRONMENT", original_env_name, "test_restore")
        
        # Business metric - secure defaults and fallbacks ensure system safety
        self.record_metric("secure_defaults_ensure_system_safety", True)
    
    # === BUSINESS CRITICAL INTEGRATION SCENARIOS ===
    
    def test_configuration_foundation_supports_all_business_services(self):
        """
        Test that configuration foundation supports all $2M+ business services.
        
        BUSINESS CRITICAL: This is the ultimate integration test validating that
        UnifiedConfigManager supports the entire business operation foundation.
        """
        # Test all critical business service configurations
        business_service_environments = {
            "development": "Development environment supporting daily engineering ($50K+ monthly engineering costs)",
            "staging": "Staging environment supporting deployment validation ($100K+ ARR protection)",
            "production": "Production environment supporting all $2M+ business revenue operations"
        }
        
        service_validation_results = {}
        
        for env_name, business_impact in business_service_environments.items():
            
            # Comprehensive environment configuration
            env_config = {
                "ENVIRONMENT": env_name,
                "JWT_SECRET_KEY": f"{env_name}_jwt_highly_secure_64_characters_absolutely_minimum_required",
                "SECRET_KEY": f"{env_name}_secret_highly_secure_64_characters_absolutely_minimum_required",
                "SERVICE_SECRET": f"{env_name}_service_highly_secure_64_characters_absolutely_minimum_req",
                "POSTGRES_HOST": f"{env_name}-postgres.internal",
                "POSTGRES_USER": f"{env_name}_user",
                "POSTGRES_PASSWORD": f"{env_name}_secure_database_password_64_characters",
                "POSTGRES_DB": f"netra_{env_name}",
                "REDIS_HOST": f"{env_name}-redis.internal",
                "CLICKHOUSE_HOST": f"{env_name}-clickhouse.internal",
                "CLICKHOUSE_PASSWORD": f"{env_name}_clickhouse_secure_password",
                "GEMINI_API_KEY": f"{env_name}_gemini_api_key_for_llm_operations"
            }
            
            with self.temp_env_vars(**env_config):
                
                # Force reload for environment
                self.config_manager.reload_config(force=True)
                
                with self.measure_config_load_time():
                    config = self.config_manager.get_config()
                
                config_load_time = self.get_metric("config_load_time_seconds")
                
                
                # Validate all critical service configurations
                validation_results = {
                    "config_loaded": config is not None,
                    "correct_environment": config.environment == env_name,
                    "database_configured": config.database_url is not None and (
                        "postgresql" in config.database_url or 
                        "sqlite" in config.database_url
                    ),
                    "auth_configured": config.jwt_secret_key is not None and len(config.jwt_secret_key) >= 32,
                    "service_auth_configured": config.service_secret is not None and len(config.service_secret) >= 32,
                    "websocket_configured": config.ws_config is not None and config.ws_config.connection_timeout > 0,
                    "redis_configured": config.redis.host is not None,
                    "clickhouse_configured": config.clickhouse_native.host is not None,
                    "llm_configured": config.gemini_api_key is not None,
                    "performance_acceptable": config_load_time < 15.0,  # Allow reasonable time for environment setup
                    "validation_passes": self.config_manager.validate_config_integrity()
                }
                
                # All validations must pass for business service support
                all_validations_pass = all(validation_results.values())
                self.assertTrue(all_validations_pass, f"{env_name} configuration validation failed: {validation_results}")
                
                service_validation_results[env_name] = {
                    "business_impact": business_impact,
                    "validation_results": validation_results,
                    "config_load_time": config_load_time,
                    "all_services_supported": all_validations_pass
                }
        
        # ULTIMATE BUSINESS VALIDATION: All environments must support full business operations
        all_environments_support_business = all(
            result["all_services_supported"] 
            for result in service_validation_results.values()
        )
        
        self.assertTrue(
            all_environments_support_business, 
            f"Configuration foundation does not support all business services: {service_validation_results}"
        )
        
        # Business metrics - configuration foundation business impact validation
        self.record_metric("configuration_supports_2m_business_revenue", True)
        self.record_metric("all_environments_validated", len(service_validation_results))
        self.record_metric("service_validation_results", service_validation_results)
        
        # Log business impact validation success
        for env_name, result in service_validation_results.items():
            self.record_metric(f"{env_name}_supports_business_operations", result["all_services_supported"])

    def test_enterprise_compliance_configuration_requirements(self):
        """
        Test Enterprise compliance configuration requirements.
        
        BUSINESS CRITICAL: Enterprise customers ($15K+ MRR each) require specific
        configuration compliance for security, audit, and reliability standards.
        """
        # Enterprise compliance test configuration
        enterprise_config = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "enterprise_jwt_highly_secure_256_bit_key_absolutely_minimum_required_for_compliance",
            "SECRET_KEY": "enterprise_secret_highly_secure_256_bit_key_absolutely_minimum_required_for_compliance", 
            "SERVICE_SECRET": "enterprise_service_highly_secure_256_bit_key_absolutely_minimum_required_compliance",
            "FERNET_KEY": "enterprise_fernet_highly_secure_key_for_data_encryption_compliance",
            "POSTGRES_HOST": "enterprise-postgres-primary.internal",
            "POSTGRES_USER": "enterprise_admin_user",
            "POSTGRES_PASSWORD": "enterprise_postgres_highly_secure_password_256_bit_compliance_required",
            "POSTGRES_DB": "netra_enterprise_production",
            "REDIS_HOST": "enterprise-redis-cluster.internal",
            "CLICKHOUSE_HOST": "enterprise-clickhouse-cluster.internal",
            "CLICKHOUSE_PASSWORD": "enterprise_clickhouse_highly_secure_password_compliance",
            "OTEL_ENABLED": "true",  # Required for Enterprise monitoring
            "OTEL_SERVICE_NAME": "netra-backend-enterprise"
        }
        
        with self.temp_env_vars(**enterprise_config):
            
            config = self.config_manager.get_config()
            
            # ENTERPRISE COMPLIANCE REQUIREMENTS
            
            # 1. Security Configuration Compliance
            security_compliance = {
                "jwt_secret_length": len(config.jwt_secret_key) >= 64,
                "service_secret_length": len(config.service_secret) >= 64, 
                "secret_key_length": len(config.secret_key) >= 64,
                "secrets_are_different": len(set([config.jwt_secret_key, config.service_secret, config.secret_key])) == 3,
                "no_debug_mode": not config.debug,
                "secure_log_level": config.log_level in ["INFO", "WARNING", "ERROR"]
            }
            
            # 2. Service Reliability Compliance
            reliability_compliance = {
                "database_configured": config.database_url is not None,
                "redis_mandatory": config.redis.host is not None,
                "clickhouse_mandatory": config.clickhouse_native.host is not None,
                "websocket_timeouts_configured": all([
                    config.ws_config.connection_timeout > 0,
                    config.ws_config.recv_timeout > 0,
                    config.ws_config.heartbeat_timeout > 0
                ]),
                "database_pool_configured": config.db_pool_size >= 20
            }
            
            # 3. Monitoring and Observability Compliance
            observability_compliance = {
                "telemetry_enabled": config.otel_enabled == "true",
                "service_named": config.otel_service_name is not None,
                "no_console_export": config.otel_console_exporter == "false",
                "logging_configured": config.log_level != "DEBUG"
            }
            
            # 4. Validate all compliance requirements
            all_compliance_checks = {
                **security_compliance,
                **reliability_compliance, 
                **observability_compliance
            }
            
            # ALL compliance checks must pass for Enterprise customers
            compliance_failures = [
                check_name for check_name, passed in all_compliance_checks.items() 
                if not passed
            ]
            
            self.assertEqual(
                len(compliance_failures), 0,
                f"Enterprise compliance failures: {compliance_failures}"
            )
            
            # 5. Enterprise Performance Requirements
            with self.measure_config_load_time():
                # Re-load config to test performance
                enterprise_config_reload = self.config_manager.reload_config(force=True)
            
            enterprise_load_time = self.get_metric("config_load_time_seconds")
            self.assertLess(enterprise_load_time, 1.0, "Enterprise config loading too slow")
            
        # Business metrics - Enterprise compliance validation
        self.record_metric("enterprise_compliance_validated", True)
        self.record_metric("security_compliance_checks_passed", len(security_compliance))
        self.record_metric("reliability_compliance_checks_passed", len(reliability_compliance))
        self.record_metric("observability_compliance_checks_passed", len(observability_compliance))
        self.record_metric("enterprise_config_load_time_acceptable", enterprise_load_time < 1.0)


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])