"""
IsolatedEnvironment Integration Tests with Real Services

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Independence
- Business Goal: Ensure configuration system works correctly with real services
- Value Impact: Prevents configuration failures that cause service outages
- Strategic Impact: Core platform reliability - validates real-world usage scenarios

This test suite validates IsolatedEnvironment integration with real services:
1. Database connection configuration 
2. Auth service URL configuration
3. Redis connection configuration
4. Environment-specific service discovery
5. Configuration validation in real service contexts

CRITICAL: These tests use real services via real_services_fixture to validate
actual service integration scenarios.
"""

import pytest
from typing import Dict, Any

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestIsolatedEnvironmentWithRealServices(BaseIntegrationTest):
    """
    Integration tests for IsolatedEnvironment with real services.
    
    Business Value: Validates configuration system works with actual services,
    preventing configuration-related service failures in production.
    """

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_services_configuration_integration(self, real_services_fixture):
        """
        Test IsolatedEnvironment integration with real service configurations.
        
        Business Value: Ensures configuration system provides correct values for real services.
        """
        env = get_env()
        
        # Get real services configuration
        expected_config = {
            "DATABASE_URL": real_services_fixture.get("database_url", "postgresql://postgres:postgres@localhost:5434/test_db"),
            "AUTH_SERVICE_URL": real_services_fixture.get("auth_url", "http://localhost:8081"),
            "REDIS_URL": real_services_fixture.get("redis_url", "redis://localhost:6381"),
        }
        
        # Store original values for restoration
        original_values = {}
        for key in expected_config.keys():
            original_values[key] = env.get(key)
        
        try:
            # Set real services configuration
            for key, value in expected_config.items():
                env.set(key, value, source="real_services_integration_test")
            
            # Verify configuration is set correctly
            for key, expected_value in expected_config.items():
                actual_value = env.get(key)
                assert actual_value == expected_value, (
                    f"Real services config mismatch: {key} expected '{expected_value}', got '{actual_value}'"
                )
            
            # Test configuration validation with real services
            # Add minimum required variables for validation
            if not env.get("JWT_SECRET_KEY"):
                env.set("JWT_SECRET_KEY", "test_jwt_secret_for_real_services", source="real_services_test")
            if not env.get("SECRET_KEY"):
                env.set("SECRET_KEY", "test_secret_key_for_real_services", source="real_services_test")
            
            validation_result = env.validate_all()
            assert validation_result.is_valid == True, (
                f"Configuration validation failed with real services: {validation_result.errors}"
            )
            
            # Test subprocess environment includes real services config
            subprocess_env = env.get_subprocess_env()
            for key, expected_value in expected_config.items():
                assert key in subprocess_env, f"Real services var {key} missing from subprocess env"
                assert subprocess_env[key] == expected_value, (
                    f"Real services var {key} wrong in subprocess: expected '{expected_value}', "
                    f"got '{subprocess_env[key]}'"
                )
            
            # Record success metrics
            self.record_metric("real_services_vars_configured", len(expected_config))
            self.record_metric("real_services_validation_passed", True)
            
        finally:
            # Restore original configuration
            for key, original_value in original_values.items():
                if original_value is not None:
                    env.set(key, original_value, source="real_services_restore")
                else:
                    if env.exists(key):
                        env.delete(key, source="real_services_cleanup")
            
            # Clean up test-specific variables
            test_vars = ["JWT_SECRET_KEY", "SECRET_KEY"]
            for var in test_vars:
                if original_values.get(var) is None and env.get(var) and "real_services" in str(env.get_variable_source(var)):
                    env.delete(var, source="real_services_cleanup")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_environment_specific_real_services_config(self, real_services_fixture):
        """
        Test environment-specific configuration with real services.
        
        Business Value: Ensures correct service URLs for different environments.
        """
        env = get_env()
        
        # Test environment-specific service configurations
        env_configs = [
            {
                "environment": "testing",
                "database_url": "postgresql://test_user:test_pass@localhost:5434/test_db",
                "auth_url": "http://localhost:8081",
                "redis_url": "redis://localhost:6381"
            },
            {
                "environment": "development", 
                "database_url": "postgresql://dev_user:dev_pass@localhost:5432/dev_db",
                "auth_url": "http://localhost:8081",
                "redis_url": "redis://localhost:6379"
            },
            {
                "environment": "staging",
                "database_url": "postgresql://staging_user:staging_pass@staging-db:5432/staging_db",
                "auth_url": "https://auth.staging.netrasystems.ai",
                "redis_url": "redis://staging-redis:6379"
            }
        ]
        
        original_environment = env.get("ENVIRONMENT")
        
        try:
            for config in env_configs:
                # Set environment
                env.set("ENVIRONMENT", config["environment"], source="env_specific_test")
                
                # Set environment-specific service URLs
                env.set("DATABASE_URL", config["database_url"], source="env_specific_test")
                env.set("AUTH_SERVICE_URL", config["auth_url"], source="env_specific_test") 
                env.set("REDIS_URL", config["redis_url"], source="env_specific_test")
                
                # Verify environment detection
                detected_env = env.get_environment_name()
                expected_env = "test" if config["environment"] == "testing" else config["environment"]
                assert detected_env == expected_env, (
                    f"Environment detection failed: expected '{expected_env}', got '{detected_env}'"
                )
                
                # Verify service URLs are environment-appropriate
                db_url = env.get("DATABASE_URL")
                auth_url = env.get("AUTH_SERVICE_URL")
                redis_url = env.get("REDIS_URL")
                
                assert db_url == config["database_url"], (
                    f"Database URL wrong for {config['environment']}: expected '{config['database_url']}', got '{db_url}'"
                )
                assert auth_url == config["auth_url"], (
                    f"Auth URL wrong for {config['environment']}: expected '{config['auth_url']}', got '{auth_url}'"
                )
                assert redis_url == config["redis_url"], (
                    f"Redis URL wrong for {config['environment']}: expected '{config['redis_url']}', got '{redis_url}'"
                )
                
                # Clean up for next iteration
                env.delete("DATABASE_URL", source="env_specific_cleanup")
                env.delete("AUTH_SERVICE_URL", source="env_specific_cleanup")
                env.delete("REDIS_URL", source="env_specific_cleanup")
            
            # Record metrics
            self.record_metric("environment_configs_tested", len(env_configs))
            self.record_metric("env_specific_config_passed", True)
            
        finally:
            # Restore original environment
            if original_environment:
                env.set("ENVIRONMENT", original_environment, source="env_specific_restore")
            else:
                if env.exists("ENVIRONMENT"):
                    env.delete("ENVIRONMENT", source="env_specific_cleanup")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_service_configuration_access(self, real_services_fixture):
        """
        Test concurrent access to service configurations.
        
        Business Value: Ensures thread-safe service configuration for multi-user scenarios.
        """
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        env = get_env()
        
        # Set up base service configuration
        base_config = {
            "DATABASE_URL": real_services_fixture.get("database_url", "postgresql://postgres:postgres@localhost:5434/test_db"),
            "AUTH_SERVICE_URL": real_services_fixture.get("auth_url", "http://localhost:8081"),
            "REDIS_URL": real_services_fixture.get("redis_url", "redis://localhost:6381"),
        }
        
        original_values = {}
        for key in base_config.keys():
            original_values[key] = env.get(key)
        
        # Set base configuration
        for key, value in base_config.items():
            env.set(key, value, source="concurrent_test_base")
        
        def concurrent_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that accesses service configuration concurrently."""
            worker_results = {
                "worker_id": worker_id,
                "config_reads": 0,
                "config_matches": 0,
                "errors": []
            }
            
            try:
                worker_env = get_env()  # Should get same singleton
                
                # Read configuration multiple times
                for i in range(10):
                    try:
                        db_url = worker_env.get("DATABASE_URL")
                        auth_url = worker_env.get("AUTH_SERVICE_URL")
                        redis_url = worker_env.get("REDIS_URL")
                        
                        worker_results["config_reads"] += 1
                        
                        # Verify configuration matches expected
                        if (db_url == base_config["DATABASE_URL"] and 
                            auth_url == base_config["AUTH_SERVICE_URL"] and
                            redis_url == base_config["REDIS_URL"]):
                            worker_results["config_matches"] += 1
                        else:
                            worker_results["errors"].append(
                                f"Config mismatch in iteration {i}: "
                                f"db='{db_url}', auth='{auth_url}', redis='{redis_url}'"
                            )
                        
                        # Small delay to increase concurrency
                        time.sleep(0.001)
                        
                    except Exception as e:
                        worker_results["errors"].append(f"Exception in iteration {i}: {e}")
                        
            except Exception as e:
                worker_results["errors"].append(f"Worker setup error: {e}")
            
            return worker_results
        
        try:
            # Run concurrent workers
            num_workers = 5
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(concurrent_worker, i) for i in range(num_workers)]
                results = [future.result(timeout=10) for future in futures]
            
            # Analyze results
            total_reads = sum(r["config_reads"] for r in results)
            total_matches = sum(r["config_matches"] for r in results)
            all_errors = []
            for r in results:
                all_errors.extend(r["errors"])
            
            # Assertions
            assert len(results) == num_workers, f"Expected {num_workers} results, got {len(results)}"
            assert total_reads > 0, "No configuration reads completed"
            assert total_matches == total_reads, (
                f"Configuration inconsistency detected: {total_matches}/{total_reads} matches. Errors: {all_errors}"
            )
            assert len(all_errors) == 0, f"Concurrent access errors: {all_errors}"
            
            # Record metrics
            self.record_metric("concurrent_workers", num_workers)
            self.record_metric("total_config_reads", total_reads)
            self.record_metric("concurrent_access_passed", True)
            
        finally:
            # Restore original configuration
            for key, original_value in original_values.items():
                if original_value is not None:
                    env.set(key, original_value, source="concurrent_test_restore")
                else:
                    if env.exists(key):
                        env.delete(key, source="concurrent_test_cleanup")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_configuration_validation_with_real_services(self, real_services_fixture):
        """
        Test configuration validation with real service URLs.
        
        Business Value: Ensures configuration validation works with actual service endpoints.
        """
        env = get_env()
        
        # Use real service URLs for validation testing
        real_config = {
            "DATABASE_URL": real_services_fixture.get("database_url"),
            "AUTH_SERVICE_URL": real_services_fixture.get("auth_url"),
            "REDIS_URL": real_services_fixture.get("redis_url"),
            "JWT_SECRET_KEY": "real_services_jwt_secret_for_validation",
            "SECRET_KEY": "real_services_secret_key_for_validation"
        }
        
        original_values = {}
        for key in real_config.keys():
            original_values[key] = env.get(key)
        
        try:
            # Set real service configuration
            for key, value in real_config.items():
                if value is not None:  # Only set if fixture provides the value
                    env.set(key, value, source="validation_with_real_services")
            
            # Run validation
            validation_result = env.validate_all()
            
            # Should pass validation with real service URLs
            assert validation_result.is_valid == True, (
                f"Validation failed with real services: {validation_result.errors}"
            )
            
            # Test specific service URL formats
            if real_config["DATABASE_URL"]:
                db_url = env.get("DATABASE_URL")
                assert db_url.startswith(("postgresql://", "postgres://")), (
                    f"Invalid database URL format: {db_url}"
                )
            
            if real_config["AUTH_SERVICE_URL"]:
                auth_url = env.get("AUTH_SERVICE_URL")
                assert auth_url.startswith(("http://", "https://")), (
                    f"Invalid auth service URL format: {auth_url}"
                )
            
            if real_config["REDIS_URL"]:
                redis_url = env.get("REDIS_URL")
                assert redis_url.startswith("redis://"), (
                    f"Invalid Redis URL format: {redis_url}"
                )
            
            # Record metrics
            self.record_metric("real_service_validation_passed", True)
            self.record_metric("validated_service_urls", len([v for v in real_config.values() if v]))
            
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is not None:
                    env.set(key, original_value, source="validation_restore")
                else:
                    if env.exists(key):
                        env.delete(key, source="validation_cleanup")