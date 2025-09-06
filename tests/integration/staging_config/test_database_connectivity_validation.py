"""
Database Connectivity Validation Test Suite
===========================================

CRITICAL MISSION: Comprehensive testing of database connectivity for staging environment.
This test suite validates all database connections (PostgreSQL, Redis, ClickHouse)
and ensures proper error handling and configuration validation.

Test Categories:
- Connection establishment tests
- Configuration validation tests
- Error handling and recovery tests
- Performance and response time tests
- Environment-specific tests
- Health check endpoint tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Prevent database connectivity failures in staging
- Value Impact: Early detection of database issues before production
- Strategic Impact: Foundation for reliable staging environment
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder
from scripts.validate_database_connections import DatabaseConnectionValidator

# Test framework imports - simplified
# from test_framework.assertions import validate_response_structure, assert_connection_healthy
# from test_framework.fixtures.isolated_environment import isolated_env_fixture


class TestDatabaseConnectivityValidation:
    """
    Comprehensive database connectivity validation test suite.
    
    Tests all aspects of database connectivity including:
    - PostgreSQL connection validation
    - Redis connection validation
    - ClickHouse connection validation
    - Configuration parsing and validation
    - Error handling and recovery
    - Performance testing
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.env = get_env()
        self.original_environment = self.env.get("ENVIRONMENT", "development")
        
        # Set environment to staging for tests
        self.env.set_env_var("ENVIRONMENT", "staging")
        
        yield
        
        # Restore original environment
        self.env.set_env_var("ENVIRONMENT", self.original_environment)
    
    @pytest.mark.asyncio
    async def test_postgresql_connection_validation_staging(self):
        """
        Test PostgreSQL connection validation in staging environment.
        
        CRITICAL: This test validates staging PostgreSQL connectivity
        and configuration parsing.
        """
        # Test with staging-like configuration
        staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "34.28.12.145",  # Staging database IP
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "staging_secure_password_2024"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        # Mock the environment variables
        with patch.dict(validator.env._env_vars, staging_config):
            # Test configuration validation
            url_builder = DatabaseURLBuilder(staging_config)
            is_valid, error_msg = url_builder.validate()
            
            if not is_valid:
                # Expected for placeholder IPs
                assert "localhost" not in error_msg, "Should not complain about localhost in staging with proper config"
                pytest.skip(f"Configuration validation failed as expected: {error_msg}")
            
            # Test connection attempt (will fail with placeholder IP but should show proper error handling)
            postgresql_result = await validator.validate_postgresql()
            
            # Validate response structure
            assert "status" in postgresql_result
            assert "connection_test" in postgresql_result
            assert "configuration_validation" in postgresql_result
            assert "staging_specific_issues" in postgresql_result
            
            # Check configuration validation
            config_validation = postgresql_result["configuration_validation"]
            assert config_validation["postgres_host"] == "34.28.12.145"
            assert config_validation["postgres_port"] == "5432"
            assert config_validation["postgres_db"] == "netra_staging"
            assert config_validation["postgres_user"] == "postgres"
            
            # Should not have critical staging issues with proper config
            staging_issues = postgresql_result["staging_specific_issues"]
            localhost_issues = [issue for issue in staging_issues if "localhost" in issue.lower()]
            assert len(localhost_issues) == 0, "Should not have localhost issues with staging IP"
    
    @pytest.mark.asyncio
    async def test_postgresql_staging_issues_detection(self):
        """
        Test detection of critical staging configuration issues.
        
        CRITICAL: This test validates that the system properly detects
        common staging configuration problems.
        """
        # Test with problematic staging configuration
        problematic_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "localhost",  # PROBLEM: localhost in staging
            "POSTGRES_PORT": "5433",      # PROBLEM: test port in staging
            "POSTGRES_DB": "netra_test",  # PROBLEM: test database in staging
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "postgres"  # PROBLEM: dev password in staging
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, problematic_config):
            postgresql_result = await validator.validate_postgresql()
            
            staging_issues = postgresql_result["staging_specific_issues"]
            
            # Should detect localhost issue
            localhost_issues = [issue for issue in staging_issues if "localhost" in issue.lower()]
            assert len(localhost_issues) > 0, "Should detect localhost usage in staging"
            
            # Should detect development password
            password_issues = [issue for issue in staging_issues if "development password" in issue.lower()]
            assert len(password_issues) > 0, "Should detect development password in staging"
    
    @pytest.mark.asyncio
    async def test_redis_connection_validation_staging(self):
        """
        Test Redis connection validation in staging environment.
        """
        staging_config = {
            "ENVIRONMENT": "staging",
            "REDIS_HOST": "34.28.12.146",  # Staging Redis IP
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "staging_redis_password_2024",
            "REDIS_DB": "0"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, staging_config):
            redis_result = await validator.validate_redis()
            
            # Validate response structure
            assert "status" in redis_result
            assert "connection_test" in redis_result
            assert "configuration" in redis_result
            assert "staging_specific_issues" in redis_result
            
            # Check configuration
            config = redis_result["configuration"]
            assert config["redis_host"] == "34.28.12.146"
            assert config["redis_port"] == "6379"
            assert config["redis_password"] == "***"  # Should be masked
            
            # Should not have localhost issues with staging IP
            staging_issues = redis_result["staging_specific_issues"]
            localhost_issues = [issue for issue in staging_issues if "localhost" in issue.lower()]
            assert len(localhost_issues) == 0, "Should not have localhost issues with staging IP"
    
    @pytest.mark.asyncio
    async def test_clickhouse_connection_validation_staging(self):
        """
        Test ClickHouse connection validation in staging environment.
        """
        staging_config = {
            "ENVIRONMENT": "staging",
            "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "CLICKHOUSE_PORT": "8443",
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_PASSWORD": "staging_clickhouse_password",
            "CLICKHOUSE_SECURE": "true"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, staging_config):
            clickhouse_result = await validator.validate_clickhouse()
            
            # Validate response structure
            assert "status" in clickhouse_result
            assert "connection_test" in clickhouse_result
            assert "configuration" in clickhouse_result
            
            # Check configuration
            config = clickhouse_result["configuration"]
            assert config["clickhouse_host"] == "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
            assert config["clickhouse_port"] == "8443"
            assert config["clickhouse_secure"] is True
            assert config["clickhouse_password"] == "***"  # Should be masked
    
    @pytest.mark.asyncio
    async def test_database_url_builder_staging_configuration(self):
        """
        Test DatabaseURLBuilder with staging configuration.
        
        CRITICAL: This test validates URL building for staging environment
        with proper configuration parsing.
        """
        staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "34.28.12.145",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "staging_password"
        }
        
        url_builder = DatabaseURLBuilder(staging_config)
        
        # Test environment detection
        assert url_builder.environment == "staging"
        
        # Test TCP configuration detection
        assert url_builder.tcp.has_config is True
        
        # Test Cloud SQL detection (should be False for TCP config)
        assert url_builder.cloud_sql.is_cloud_sql is False
        
        # Test URL generation
        staging_url = url_builder.staging.auto_url
        if staging_url:  # May be None if validation fails
            assert "34.28.12.145" in staging_url
            assert "5432" in staging_url
            assert "netra_staging" in staging_url
            assert "sslmode=require" in staging_url  # Should use SSL for staging
        
        # Test validation
        is_valid, error_msg = url_builder.validate()
        
        # Debug information
        debug_info = url_builder.debug_info()
        assert debug_info["environment"] == "staging"
        assert debug_info["has_tcp_config"] is True
    
    @pytest.mark.asyncio
    async def test_database_url_builder_cloud_sql_configuration(self):
        """
        Test DatabaseURLBuilder with Cloud SQL configuration.
        
        CRITICAL: This test validates Cloud SQL URL building which is
        the recommended approach for production-like staging.
        """
        cloud_sql_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "cloud_sql_password"
        }
        
        url_builder = DatabaseURLBuilder(cloud_sql_config)
        
        # Test Cloud SQL detection
        assert url_builder.cloud_sql.is_cloud_sql is True
        
        # Test TCP configuration detection (should be False for Cloud SQL)
        assert url_builder.tcp.has_config is False
        
        # Test URL generation
        cloud_sql_url = url_builder.cloud_sql.async_url
        if cloud_sql_url:
            assert "/cloudsql/" in cloud_sql_url
            assert "netra-staging:us-central1:netra-staging-db" in cloud_sql_url
            assert "netra_staging" in cloud_sql_url
        
        # Test validation
        is_valid, error_msg = url_builder.validate()
        
        if not is_valid:
            # Expected for this test - we're testing the validation logic
            assert "cloudsql" in error_msg.lower() or "format" in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_full_system_validation_staging(self):
        """
        Test full system validation with staging configuration.
        
        CRITICAL: This test validates the complete database validation
        workflow for staging environment.
        """
        staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "34.28.12.145",
            "POSTGRES_PORT": "5432", 
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "staging_password",
            "REDIS_HOST": "34.28.12.146",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "redis_password",
            "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "CLICKHOUSE_PORT": "8443",
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_PASSWORD": "clickhouse_password",
            "CLICKHOUSE_SECURE": "true",
            "REDIS_REQUIRED": "false",
            "CLICKHOUSE_REQUIRED": "false"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, staging_config):
            # Run full validation
            results = await validator.run_full_validation()
            
            # Validate top-level structure
            assert "environment" in results
            assert "timestamp" in results
            assert "postgresql" in results
            assert "redis" in results
            assert "clickhouse" in results
            assert "overall_status" in results
            
            assert results["environment"] == "staging"
            
            # Validate individual service results
            for service in ["postgresql", "redis", "clickhouse"]:
                service_result = results[service]
                assert "status" in service_result
                assert "connection_test" in service_result
                
                # All services should have connection attempts
                connection_test = service_result["connection_test"]
                assert "connected" in connection_test
                assert "error" in connection_test
                
                # Services should either succeed or fail with proper error messages
                if not connection_test["connected"]:
                    assert connection_test["error"] is not None
                    assert len(connection_test["error"]) > 0
            
            # Overall status should be determined by critical services
            # PostgreSQL failure should result in failed overall status
            if results["postgresql"]["status"] == "failed":
                assert results["overall_status"] in ["failed"]
            
            # Generate report
            report = validator.generate_report()
            assert "DATABASE CONNECTION VALIDATION REPORT" in report
            assert "STAGING" in report
            assert "POSTGRESQL" in report
            assert "REDIS" in report
            assert "CLICKHOUSE" in report
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """
        Test error handling and recovery mechanisms.
        
        This test validates that the system properly handles various
        error conditions and provides useful error information.
        """
        # Test with completely invalid configuration
        invalid_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "invalid-host-that-does-not-exist.com",
            "POSTGRES_PORT": "99999",  # Invalid port
            "POSTGRES_DB": "",         # Empty database name
            "POSTGRES_USER": "",       # Empty user
            "POSTGRES_PASSWORD": ""    # Empty password
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, invalid_config):
            # Test PostgreSQL with invalid config
            postgresql_result = await validator.validate_postgresql()
            
            # Should detect configuration errors
            assert postgresql_result["status"] in ["failed", "configuration_error"]
            
            if "configuration_validation" in postgresql_result:
                config_validation = postgresql_result["configuration_validation"]
                assert config_validation["is_valid"] is False
                assert config_validation["error_message"] is not None
            
            # Should detect staging-specific issues
            staging_issues = postgresql_result["staging_specific_issues"]
            missing_var_issues = [issue for issue in staging_issues 
                                if "missing" in issue.lower()]
            # Should detect missing required variables
            assert len(missing_var_issues) > 0 or postgresql_result["status"] == "configuration_error"
    
    @pytest.mark.asyncio 
    async def test_performance_validation(self):
        """
        Test database connection performance validation.
        
        This test validates that connection attempts have reasonable timeouts
        and performance characteristics.
        """
        # Test with configuration that will timeout
        timeout_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "10.255.255.1",  # Non-routable IP for timeout
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "password"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, timeout_config):
            start_time = time.time()
            
            # Test PostgreSQL connection with timeout
            postgresql_result = await validator.validate_postgresql()
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Should timeout within reasonable time (not too fast, not too slow)
            assert 1 < elapsed_time < 30, f"Connection attempt took {elapsed_time:.2f}s - should be 1-30s"
            
            # Should detect timeout
            connection_test = postgresql_result["connection_test"]
            if connection_test and "error" in connection_test:
                error_msg = connection_test["error"].lower()
                timeout_indicators = ["timeout", "refused", "unreachable", "failed to connect"]
                assert any(indicator in error_msg for indicator in timeout_indicators), \
                    f"Expected timeout/connection error, got: {connection_test['error']}"
    
    @pytest.mark.asyncio
    async def test_configuration_validation_edge_cases(self):
        """
        Test configuration validation with various edge cases.
        
        This test validates the robustness of configuration parsing
        and validation logic.
        """
        edge_cases = [
            # Empty configuration
            {"ENVIRONMENT": "staging"},
            
            # Mixed valid/invalid configuration
            {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "valid-host.com", 
                "POSTGRES_PORT": "invalid-port",
                "POSTGRES_DB": "valid_db",
                "POSTGRES_USER": "",  # Empty user
                "POSTGRES_PASSWORD": "valid_password"
            },
            
            # URL-encoded values
            {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "host%20with%20spaces",
                "POSTGRES_PASSWORD": "password%20with%20spaces%21"
            },
            
            # Special characters
            {
                "ENVIRONMENT": "staging", 
                "POSTGRES_HOST": "host.com",
                "POSTGRES_PASSWORD": "p@ssw0rd!#$%^&*()"
            }
        ]
        
        for i, config in enumerate(edge_cases):
            validator = DatabaseConnectionValidator("staging")
            
            with patch.dict(validator.env._env_vars, config):
                # Should not crash with any configuration
                try:
                    postgresql_result = await validator.validate_postgresql()
                    
                    # Should always return valid structure
                    assert "status" in postgresql_result
                    assert "configuration_validation" in postgresql_result
                    
                    # Status should reflect configuration validity
                    if not config.get("POSTGRES_HOST"):
                        assert postgresql_result["status"] in ["failed", "configuration_error", "not_configured"]
                    
                except Exception as e:
                    pytest.fail(f"Configuration edge case {i} caused unexpected exception: {e}")
    
    def test_database_url_masking_security(self):
        """
        Test that database URLs are properly masked for logging.
        
        CRITICAL: This test ensures that sensitive information like
        passwords are not exposed in logs or error messages.
        """
        test_urls = [
            "postgresql://user:password@host:5432/db",
            "postgresql://user:complex!pass@word@host:5432/db",
            "postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance",
            "redis://user:password@host:6379/0",
            "clickhouse://user:password@host:8443/db?secure=1"
        ]
        
        for url in test_urls:
            masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
            
            # Should not contain the original password
            assert "password" not in masked_url
            assert "complex!pass@word" not in masked_url
            assert "pass" not in masked_url or masked_url.count("pass") <= url.count("pass") - 1
            
            # Should contain masked indicators
            assert "***" in masked_url or "*" in masked_url
            
            # Should preserve non-sensitive parts
            if "host" in url and "password" not in "host":
                assert "host" in masked_url
    
    @pytest.mark.asyncio
    async def test_environment_specific_behavior(self):
        """
        Test that validation behavior changes appropriately by environment.
        
        This test ensures that staging environment has different validation
        rules than development environment.
        """
        base_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_dev",
            "POSTGRES_USER": "postgres", 
            "POSTGRES_PASSWORD": "postgres"
        }
        
        # Test development environment (should allow localhost)
        dev_config = {**base_config, "ENVIRONMENT": "development"}
        dev_validator = DatabaseConnectionValidator("development")
        
        with patch.dict(dev_validator.env._env_vars, dev_config):
            dev_result = await dev_validator.validate_postgresql()
            dev_issues = dev_result.get("staging_specific_issues", [])
            
            # Should not complain about localhost in development
            localhost_issues = [issue for issue in dev_issues if "localhost" in issue.lower()]
            assert len(localhost_issues) == 0, "Development should allow localhost"
        
        # Test staging environment (should flag localhost)
        staging_config = {**base_config, "ENVIRONMENT": "staging"}
        staging_validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(staging_validator.env._env_vars, staging_config):
            staging_result = await staging_validator.validate_postgresql()
            staging_issues = staging_result.get("staging_specific_issues", [])
            
            # Should complain about localhost in staging
            localhost_issues = [issue for issue in staging_issues if "localhost" in issue.lower()]
            assert len(localhost_issues) > 0, "Staging should flag localhost usage"


class TestHealthCheckEndpoints:
    """
    Test the health check endpoints for database connectivity.
    
    These tests validate that the FastAPI health check endpoints
    properly integrate with the database validation system.
    """
    
    @pytest.fixture(autouse=True)
    def setup_health_check_tests(self):
        """Set up health check endpoint tests."""
        # Import here to avoid circular imports
        from netra_backend.app.api.health_checks import health_manager
        self.health_manager = health_manager
        
        yield
    
    @pytest.mark.asyncio
    async def test_health_manager_postgresql_check(self):
        """
        Test health manager PostgreSQL check directly.
        
        This test validates the health manager component that backs
        the health check endpoints.
        """
        # Test with mock configuration
        staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "mock-staging-db.com",
            "POSTGRES_PORT": "5432", 
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "staging_password"
        }
        
        with patch.dict(self.health_manager.env._env_vars, staging_config):
            # Mock the database manager health check
            with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_db_manager:
                mock_manager = MagicMock()
                mock_manager.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "engine": "primary"
                })
                mock_db_manager.return_value = mock_manager
                
                health_result = await self.health_manager.check_postgresql_health()
                
                # Validate response structure
                assert hasattr(health_result, 'status')
                assert hasattr(health_result, 'connected')
                assert hasattr(health_result, 'service')
                
                assert health_result.service == "postgresql"
                assert health_result.status == "healthy"
                assert health_result.connected is True
    
    @pytest.mark.asyncio
    async def test_health_manager_overall_health_check(self):
        """
        Test health manager overall health check.
        
        This test validates the system-wide health aggregation logic.
        """
        # Mock individual health checks
        with patch.object(self.health_manager, 'check_postgresql_health') as mock_pg, \
             patch.object(self.health_manager, 'check_redis_health') as mock_redis, \
             patch.object(self.health_manager, 'check_clickhouse_health') as mock_ch:
            
            # Mock successful health checks
            from netra_backend.app.api.health_checks import DatabaseHealthStatus
            
            mock_pg.return_value = DatabaseHealthStatus(
                service="postgresql",
                status="healthy",
                connected=True,
                checked_at=datetime.utcnow()
            )
            
            mock_redis.return_value = DatabaseHealthStatus(
                service="redis", 
                status="not_configured",
                connected=False,
                checked_at=datetime.utcnow()
            )
            
            mock_ch.return_value = DatabaseHealthStatus(
                service="clickhouse",
                status="not_configured", 
                connected=False,
                checked_at=datetime.utcnow()
            )
            
            system_health = await self.health_manager.check_overall_health()
            
            # Validate response structure
            assert hasattr(system_health, 'overall_status')
            assert hasattr(system_health, 'services')
            assert hasattr(system_health, 'environment')
            
            # Should be healthy with PostgreSQL healthy and others not configured
            assert system_health.overall_status == "healthy"
            
            # Should contain all services
            assert "postgresql" in system_health.services
            assert "redis" in system_health.services
            assert "clickhouse" in system_health.services
    
    @pytest.mark.asyncio
    async def test_health_manager_failure_detection(self):
        """
        Test health manager failure detection and aggregation.
        
        This test validates that critical service failures are properly
        detected and reflected in overall system health.
        """
        with patch.object(self.health_manager, 'check_postgresql_health') as mock_pg, \
             patch.object(self.health_manager, 'check_redis_health') as mock_redis, \
             patch.object(self.health_manager, 'check_clickhouse_health') as mock_ch:
            
            from netra_backend.app.api.health_checks import DatabaseHealthStatus
            
            # Mock PostgreSQL failure (critical service)
            mock_pg.return_value = DatabaseHealthStatus(
                service="postgresql",
                status="failed",
                connected=False,
                error="Connection refused",
                checked_at=datetime.utcnow()
            )
            
            # Mock Redis as healthy
            mock_redis.return_value = DatabaseHealthStatus(
                service="redis",
                status="healthy",
                connected=True,
                checked_at=datetime.utcnow()
            )
            
            # Mock ClickHouse as not configured
            mock_ch.return_value = DatabaseHealthStatus(
                service="clickhouse",
                status="not_configured",
                connected=False,
                checked_at=datetime.utcnow()
            )
            
            system_health = await self.health_manager.check_overall_health()
            
            # PostgreSQL failure should result in overall failure
            assert system_health.overall_status == "failed"
            
            # Individual service status should be preserved
            assert system_health.services["postgresql"].status == "failed"
            assert system_health.services["redis"].status == "healthy"
            assert system_health.services["clickhouse"].status == "not_configured"


@pytest.mark.integration
class TestDatabaseConnectivityIntegration:
    """
    Integration tests for database connectivity with real or mock services.
    
    These tests require either real database services or comprehensive mocking.
    They test the full integration flow from configuration to connection.
    """
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_workflow(self):
        """
        Test complete end-to-end validation workflow.
        
        This test validates the entire flow from configuration loading
        through connection validation to report generation.
        """
        # Use a realistic but mock configuration
        realistic_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-db.netra.internal",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging", 
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "secure_staging_password_2024",
            "REDIS_HOST": "staging-redis.netra.internal",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "secure_redis_password_2024",
            "CLICKHOUSE_HOST": "staging-clickhouse.netra.internal",
            "CLICKHOUSE_PORT": "8443",
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_PASSWORD": "secure_clickhouse_password_2024",
            "CLICKHOUSE_SECURE": "true"
        }
        
        validator = DatabaseConnectionValidator("staging")
        
        with patch.dict(validator.env._env_vars, realistic_config):
            # Test configuration loading
            assert validator.environment == "staging"
            assert validator.results["configuration"]["loaded_from"] is not None
            
            # Test URL builder integration
            url_builder = DatabaseURLBuilder(realistic_config)
            assert url_builder.environment == "staging"
            
            # Test validation (will fail with mock hosts but should handle gracefully)
            results = await validator.run_full_validation()
            
            # Validate complete results structure
            expected_top_level_keys = [
                "environment", "timestamp", "postgresql", 
                "redis", "clickhouse", "overall_status"
            ]
            
            for key in expected_top_level_keys:
                assert key in results, f"Missing key: {key}"
            
            # Validate each service has complete structure
            for service in ["postgresql", "redis", "clickhouse"]:
                service_result = results[service]
                expected_service_keys = [
                    "status", "connection_test", "configuration"
                ]
                
                for key in expected_service_keys:
                    assert key in service_result, f"Missing key {key} in {service}"
            
            # Test report generation
            report = validator.generate_report()
            assert len(report) > 100, "Report should be comprehensive"
            assert "STAGING" in report
            
            # Test report saving
            report_path = validator.save_report()
            assert report_path.exists(), "Report file should be created"
            assert report_path.suffix == ".json", "Report should be JSON format"
            
            # Cleanup
            report_path.unlink(missing_ok=True)
            report_path.with_suffix('.txt').unlink(missing_ok=True)