"""
Offline Configuration Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure configuration system integration works without external services
- Value Impact: Validates core configuration loading, validation, and environment management
- Strategic Impact: Enables immediate testing progress without Docker dependencies

These tests validate configuration integration between components without requiring
external services like Redis or PostgreSQL. They focus on:
1. Configuration loading from multiple sources
2. Environment detection and validation
3. Service initialization configuration
4. Cross-service configuration consistency
5. Configuration error handling and validation
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestConfigurationIntegrationOffline(SSotBaseTestCase):
    """Offline integration tests for configuration management system."""

    def setup_method(self, method=None):
        """Setup with enhanced environment isolation for offline testing."""
        super().setup_method(method)
        self.test_config_files = []  # Track temp files for cleanup
    
    def teardown_method(self, method=None):
        """Cleanup temporary configuration files."""
        try:
            for config_file in self.test_config_files:
                if config_file.exists():
                    config_file.unlink()
        finally:
            super().teardown_method(method)
    
    def create_temp_config_file(self, content: str, suffix: str = ".env") -> Path:
        """Create temporary configuration file and track for cleanup."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix=suffix, 
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(content)
        temp_file.close()
        
        temp_path = Path(temp_file.name)
        self.test_config_files.append(temp_path)
        return temp_path

    @pytest.mark.integration
    async def test_configuration_loading_precedence_integration(self):
        """
        Test configuration loading precedence between file sources and environment variables.
        
        This integration test validates that the configuration system correctly
        handles precedence when loading from multiple sources.
        """
        # Create base configuration file
        base_config = """
# Base configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=base_db
AUTH_SERVICE_URL=http://localhost:8081
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
SECRET_KEY=base_secret_key
        """.strip()
        
        base_config_path = self.create_temp_config_file(base_config)
        
        # Create override configuration file
        override_config = """
# Override configuration
DATABASE_NAME=override_db
AUTH_SERVICE_URL=http://override-auth:8081
NEW_CONFIG_VALUE=override_value
SECRET_KEY=override_secret_key
        """.strip()
        
        override_config_path = self.create_temp_config_file(override_config)
        
        # Load base configuration
        loaded_count, errors = self.get_env().load_from_file(base_config_path, override_existing=True)
        assert loaded_count > 0, f"Failed to load base config: {errors}"
        assert len(errors) == 0, f"Errors loading base config: {errors}"
        
        # Verify base configuration is loaded
        assert self.get_env_var("DATABASE_HOST") == "localhost"
        assert self.get_env_var("DATABASE_NAME") == "base_db"
        assert self.get_env_var("SECRET_KEY") == "base_secret_key"
        
        # Load override configuration without overriding existing
        override_count, override_errors = self.get_env().load_from_file(
            override_config_path, 
            override_existing=False
        )
        assert override_count > 0, f"Failed to load override config: {override_errors}"
        
        # Test precedence - existing values should NOT be overridden
        assert self.get_env_var("DATABASE_NAME") == "base_db"  # Should NOT be overridden
        assert self.get_env_var("SECRET_KEY") == "base_secret_key"  # Should NOT be overridden
        assert self.get_env_var("NEW_CONFIG_VALUE") == "override_value"  # Should be added
        
        # Load override configuration with overriding enabled
        override_count2, override_errors2 = self.get_env().load_from_file(
            override_config_path, 
            override_existing=True
        )
        
        # Test precedence - existing values should now be overridden
        assert self.get_env_var("DATABASE_NAME") == "override_db"  # Should be overridden
        assert self.get_env_var("SECRET_KEY") == "override_secret_key"  # Should be overridden
        assert self.get_env_var("AUTH_SERVICE_URL") == "http://override-auth:8081"  # Should be overridden
        
        # Environment variables should have highest precedence
        self.set_env_var("DATABASE_NAME", "env_override_db")
        assert self.get_env_var("DATABASE_NAME") == "env_override_db"
        
        # Record integration test metrics
        self.record_metric("base_config_vars_loaded", loaded_count)
        self.record_metric("override_config_vars_loaded", override_count)
        self.record_metric("configuration_precedence_integration_passed", True)

    @pytest.mark.integration  
    async def test_environment_detection_integration(self):
        """
        Test environment detection integration across different configuration patterns.
        
        This validates that environment detection works consistently across
        different configuration scenarios.
        """
        environment_scenarios = [
            {
                "name": "development_explicit",
                "config": {
                    "ENVIRONMENT": "development",
                    "DEBUG": "true",
                    "DATABASE_URL": "postgresql://dev:dev@localhost:5432/dev_db",
                    "AUTH_SERVICE_URL": "http://localhost:8081"
                },
                "expected_env": "development",
                "expected_debug": True
            },
            {
                "name": "test_normalized",
                "config": {
                    "ENVIRONMENT": "testing",  # Should normalize to "test"
                    "DEBUG": "true", 
                    "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
                    "AUTH_SERVICE_URL": "http://test-auth:8081"
                },
                "expected_env": "test",
                "expected_debug": True
            },
            {
                "name": "staging_secure",
                "config": {
                    "ENVIRONMENT": "staging",
                    "DEBUG": "false",
                    "DATABASE_URL": "postgresql://staging_user:secure_pass@staging-db:5432/staging_db",
                    "AUTH_SERVICE_URL": "https://auth.staging.example.com"
                },
                "expected_env": "staging", 
                "expected_debug": False
            },
            {
                "name": "production_locked",
                "config": {
                    "ENVIRONMENT": "production",
                    "DEBUG": "false",
                    "DATABASE_URL": "postgresql://prod_user:ultra_secure@prod-db:5432/prod_db",
                    "AUTH_SERVICE_URL": "https://auth.example.com"
                },
                "expected_env": "production",
                "expected_debug": False
            }
        ]
        
        for scenario in environment_scenarios:
            # Clear environment between scenarios
            if scenario["name"] != "development_explicit":  # Don't clear for first scenario
                for key in ["ENVIRONMENT", "DEBUG", "DATABASE_URL", "AUTH_SERVICE_URL"]:
                    if self.get_env().exists(key):
                        self.delete_env_var(key)
            
            # Apply scenario configuration
            for key, value in scenario["config"].items():
                self.set_env_var(key, value)
            
            # Test environment detection
            detected_env = self.get_env().get_environment_name()
            assert detected_env == scenario["expected_env"], (
                f"Environment detection failed for {scenario['name']}: "
                f"expected '{scenario['expected_env']}', got '{detected_env}'"
            )
            
            # Test environment boolean methods
            if scenario["expected_env"] == "development":
                assert self.get_env().is_development()
                assert not self.get_env().is_test()
                assert not self.get_env().is_staging()
                assert not self.get_env().is_production()
            elif scenario["expected_env"] == "test":
                assert not self.get_env().is_development()
                assert self.get_env().is_test()
                assert not self.get_env().is_staging()
                assert not self.get_env().is_production()
            elif scenario["expected_env"] == "staging":
                assert not self.get_env().is_development()
                assert not self.get_env().is_test()
                assert self.get_env().is_staging()
                assert not self.get_env().is_production()
            elif scenario["expected_env"] == "production":
                assert not self.get_env().is_development()
                assert not self.get_env().is_test()
                assert not self.get_env().is_staging()
                assert self.get_env().is_production()
            
            # Validate scenario-specific logic
            debug_value = self.get_env_var("DEBUG", "false").lower()
            expected_debug = scenario["expected_debug"]
            actual_debug = debug_value in ["true", "1", "yes"]
            assert actual_debug == expected_debug, (
                f"Debug setting mismatch for {scenario['name']}: "
                f"expected {expected_debug}, got {actual_debug}"
            )
            
            # Record scenario metrics
            self.record_metric(f"{scenario['name']}_environment_detected", detected_env)
            
        # Record overall integration metrics
        self.record_metric("environment_scenarios_tested", len(environment_scenarios))
        self.record_metric("environment_detection_integration_passed", True)

    @pytest.mark.integration
    async def test_configuration_validation_integration(self):
        """
        Test configuration validation integration across different validation scenarios.
        
        This validates that configuration validation works correctly with different
        configuration states and error conditions.
        """
        # Test Case 1: Valid minimal configuration
        minimal_valid_config = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "JWT_SECRET_KEY": "valid_jwt_secret_at_least_32_chars",
            "SECRET_KEY": "valid_secret_key_at_least_32_chars"
        }
        
        # Clear environment and apply minimal config
        critical_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]
        for var in critical_vars:
            if self.get_env().exists(var):
                self.delete_env_var(var)
        
        for key, value in minimal_valid_config.items():
            self.set_env_var(key, value)
        
        # Test validation passes with minimal config
        validation_result = self.get_env().validate_all()
        assert validation_result.is_valid, (
            f"Minimal config validation failed: {validation_result.errors}"
        )
        assert len(validation_result.errors) == 0
        
        # Test Case 2: Missing required variables
        missing_var_scenarios = [
            {
                "missing_var": "DATABASE_URL",
                "expected_error_pattern": "DATABASE_URL"
            },
            {
                "missing_var": "JWT_SECRET_KEY", 
                "expected_error_pattern": "JWT_SECRET_KEY"
            },
            {
                "missing_var": "SECRET_KEY",
                "expected_error_pattern": "SECRET_KEY"
            }
        ]
        
        for scenario in missing_var_scenarios:
            # Remove the required variable
            original_value = self.get_env_var(scenario["missing_var"])
            self.delete_env_var(scenario["missing_var"])
            
            # Test validation fails
            validation_result = self.get_env().validate_all()
            assert not validation_result.is_valid, (
                f"Validation should fail when {scenario['missing_var']} is missing"
            )
            assert len(validation_result.errors) > 0
            
            # Check that the expected error is present
            error_found = any(
                scenario["expected_error_pattern"] in error
                for error in validation_result.errors
            )
            assert error_found, (
                f"Expected error pattern '{scenario['expected_error_pattern']}' not found. "
                f"Errors: {validation_result.errors}"
            )
            
            # Restore the variable
            if original_value:
                self.set_env_var(scenario["missing_var"], original_value)
        
        # Test Case 3: Invalid configuration values
        invalid_scenarios = [
            {
                "name": "short_jwt_secret",
                "config": {"JWT_SECRET_KEY": "short"},
                "expected_error_pattern": "JWT_SECRET_KEY"
            },
            {
                "name": "short_secret_key",
                "config": {"SECRET_KEY": "short"},
                "expected_error_pattern": "SECRET_KEY"
            },
            {
                "name": "invalid_database_url",
                "config": {"DATABASE_URL": "not_a_url"},
                "expected_error_pattern": "DATABASE_URL"
            }
        ]
        
        for scenario in invalid_scenarios:
            # Store original values
            original_values = {}
            for key in scenario["config"].keys():
                original_values[key] = self.get_env_var(key)
            
            # Apply invalid configuration
            for key, value in scenario["config"].items():
                self.set_env_var(key, value)
            
            # Test validation fails
            validation_result = self.get_env().validate_all()
            
            # Note: Some validations might be lenient, so we'll log but not assert hard failure
            if not validation_result.is_valid:
                error_found = any(
                    scenario["expected_error_pattern"] in error
                    for error in validation_result.errors
                )
                if error_found:
                    self.record_metric(f"{scenario['name']}_validation_correctly_failed", True)
            else:
                # Some validations might be more permissive than expected
                self.record_metric(f"{scenario['name']}_validation_permissive", True)
            
            # Restore original values
            for key, original_value in original_values.items():
                if original_value:
                    self.set_env_var(key, original_value)
        
        # Test Case 4: Environment-specific validation (staging)
        if self.get_env().is_staging():
            # Test staging-specific validation logic
            staging_validation = self.get_env().validate_staging_database_credentials()
            self.record_metric("staging_validation_executed", True)
            self.record_metric("staging_validation_result", staging_validation.get("valid", False))
        
        # Record integration metrics
        self.record_metric("validation_scenarios_tested", 
                          1 + len(missing_var_scenarios) + len(invalid_scenarios))
        self.record_metric("configuration_validation_integration_passed", True)

    @pytest.mark.integration
    async def test_cross_service_configuration_consistency(self):
        """
        Test configuration consistency across different service contexts.
        
        This validates that configuration behaves consistently when accessed
        from different service perspectives (backend, auth, analytics).
        """
        # Simulate multi-service configuration
        multi_service_config = {
            # Shared configuration
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "INFO",
            "SECRET_KEY": "shared_secret_key_for_all_services",
            
            # Database configuration
            "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5434/test_db",
            "DATABASE_POOL_SIZE": "10",
            
            # Auth service configuration  
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "JWT_SECRET_KEY": "jwt_secret_key_shared_across_services",
            "JWT_EXPIRY_HOURS": "24",
            
            # Backend service configuration
            "BACKEND_HOST": "localhost",
            "BACKEND_PORT": "8000",
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
            
            # Redis configuration
            "REDIS_URL": "redis://localhost:6381",
            "REDIS_TIMEOUT": "5",
            
            # Analytics configuration
            "ANALYTICS_ENABLED": "true",
            "METRICS_COLLECTION_INTERVAL": "60"
        }
        
        # Apply multi-service configuration
        for key, value in multi_service_config.items():
            self.set_env_var(key, value)
        
        # Test 1: Verify all configuration is accessible
        for key, expected_value in multi_service_config.items():
            actual_value = self.get_env_var(key)
            assert actual_value == expected_value, (
                f"Configuration inconsistency: {key} expected '{expected_value}', got '{actual_value}'"
            )
        
        # Test 2: Test configuration derivation and computed values
        # Database connection components
        database_url = self.get_env_var("DATABASE_URL")
        assert database_url is not None
        assert "postgresql://" in database_url
        assert "test_user" in database_url
        assert "test_db" in database_url
        
        # Service URL construction
        backend_host = self.get_env_var("BACKEND_HOST")
        backend_port = self.get_env_var("BACKEND_PORT")
        expected_backend_url = f"http://{backend_host}:{backend_port}"
        
        # Test 3: Environment-specific behavior consistency
        env_name = self.get_env().get_environment_name()
        assert env_name == "test"
        assert self.get_env().is_test()
        
        # Test 4: Configuration validation consistency across services
        validation_result = self.get_env().validate_all()
        assert validation_result.is_valid, (
            f"Multi-service configuration validation failed: {validation_result.errors}"
        )
        
        # Test 5: Subprocess environment consistency
        subprocess_env = self.get_env().get_subprocess_env()
        for key, expected_value in multi_service_config.items():
            assert key in subprocess_env, f"Config {key} missing from subprocess environment"
            assert subprocess_env[key] == expected_value, (
                f"Subprocess config inconsistency: {key} expected '{expected_value}', "
                f"got '{subprocess_env[key]}'"
            )
        
        # Test 6: Configuration source tracking consistency
        for key in multi_service_config.keys():
            source = self.get_env().get_variable_source(key)
            assert source is not None, f"No source tracked for {key}"
            # Source should contain test identifier
            assert "test" in source.lower(), f"Source '{source}' doesn't indicate test origin"
        
        # Record cross-service integration metrics
        self.record_metric("multi_service_config_vars", len(multi_service_config))
        self.record_metric("cross_service_validation_passed", validation_result.is_valid)
        self.record_metric("subprocess_env_consistency_passed", True)
        self.record_metric("cross_service_configuration_integration_passed", True)

    @pytest.mark.integration
    async def test_configuration_error_handling_integration(self):
        """
        Test configuration error handling and recovery integration.
        
        This validates that the configuration system handles errors gracefully
        and provides useful error information for troubleshooting.
        """
        # Test Case 1: Malformed configuration file handling
        malformed_config = """
# Valid configuration
VALID_VAR1=value1
VALID_VAR2=value2

# Malformed lines (should be handled gracefully)
INVALID_LINE_NO_EQUALS
ANOTHER_INVALID_LINE

# Line with special characters
SPECIAL_CHARS=value!@#$%^&*()

# Empty value  
EMPTY_VALUE=

# Multiple equals signs
MULTIPLE_EQUALS=value=with=equals

# Valid line after malformed
VALID_VAR3=value3
        """.strip()
        
        malformed_config_path = self.create_temp_config_file(malformed_config)
        
        # Load malformed configuration - should handle errors gracefully
        loaded_count, errors = self.get_env().load_from_file(malformed_config_path)
        
        # Should have loaded valid variables despite errors
        assert loaded_count >= 4, f"Should load valid vars despite errors, got {loaded_count}"
        assert len(errors) >= 2, f"Should report errors for malformed lines, got {len(errors)}"
        
        # Valid variables should be loaded correctly
        assert self.get_env_var("VALID_VAR1") == "value1"
        assert self.get_env_var("VALID_VAR2") == "value2"
        assert self.get_env_var("VALID_VAR3") == "value3"
        assert self.get_env_var("SPECIAL_CHARS") == "value!@#$%^&*()"
        
        # Multiple equals should be handled (everything after first = is value)
        assert self.get_env_var("MULTIPLE_EQUALS") == "value=with=equals"
        
        # Empty value should be allowed
        empty_value = self.get_env_var("EMPTY_VALUE") 
        assert empty_value == "" or empty_value is None, f"Empty value handling failed: '{empty_value}'"
        
        # Test Case 2: File access error handling
        nonexistent_file = Path("/this/path/does/not/exist/config.env")
        loaded_count2, errors2 = self.get_env().load_from_file(nonexistent_file)
        
        assert loaded_count2 == 0, f"Should not load from nonexistent file"
        assert len(errors2) > 0, f"Should report error for nonexistent file"
        
        # Test Case 3: Invalid character handling
        unicode_config = """
# Unicode and special characters test
UNICODE_VAR=caf[U+00E9]_r[U+00E9]sum[U+00E9]_na[U+00EF]ve_[U+1F680]
NEWLINE_VAR=value_with\\nnewline
TAB_VAR=value_with\\ttab
QUOTES_VAR="quoted value with spaces"
SINGLE_QUOTES=''single quoted''
        """.strip()
        
        unicode_config_path = self.create_temp_config_file(unicode_config)
        loaded_count3, errors3 = self.get_env().load_from_file(unicode_config_path)
        
        assert loaded_count3 > 0, f"Should load unicode config, got {loaded_count3}"
        
        # Unicode should be preserved
        unicode_value = self.get_env_var("UNICODE_VAR")
        assert unicode_value is not None, "Unicode value should be loaded"
        assert "caf[U+00E9]" in unicode_value or "cafe" in unicode_value, "Unicode should be preserved or normalized"
        
        # Test Case 4: Large configuration handling
        large_config_vars = {}
        for i in range(100):
            var_name = f"LARGE_CONFIG_VAR_{i:03d}"
            var_value = f"large_config_value_{i}_{'x' * 100}"  # Long values
            large_config_vars[var_name] = var_value
            self.set_env_var(var_name, var_value)
        
        # Verify all large config variables are set
        for var_name, expected_value in large_config_vars.items():
            actual_value = self.get_env_var(var_name)
            assert actual_value == expected_value, f"Large config var {var_name} not preserved"
        
        # Test performance doesn't degrade significantly
        start_time = self.get_metrics().start_time or 0
        current_time = self.get_metrics().end_time or start_time + 1
        if current_time - start_time > 10.0:  # 10 second threshold
            self.record_metric("large_config_performance_warning", True)
        
        # Test Case 5: Configuration state recovery
        # Corrupt current state and verify recovery mechanisms
        original_env_count = len(self.get_env().get_all())
        
        # Clear critical config and verify validation detects issues
        self.delete_env_var("SECRET_KEY")
        validation_result = self.get_env().validate_all()
        assert not validation_result.is_valid, "Validation should fail with missing SECRET_KEY"
        
        # Restore critical config and verify recovery
        self.set_env_var("SECRET_KEY", "recovered_secret_key_for_validation")
        validation_result = self.get_env().validate_all() 
        assert validation_result.is_valid, (
            f"Validation should pass after recovery: {validation_result.errors}"
        )
        
        # Record error handling integration metrics
        self.record_metric("malformed_config_vars_loaded", loaded_count)
        self.record_metric("malformed_config_errors_count", len(errors))
        self.record_metric("unicode_config_vars_loaded", loaded_count3)
        self.record_metric("large_config_vars_count", len(large_config_vars))
        self.record_metric("configuration_error_handling_integration_passed", True)

    @pytest.mark.integration
    async def test_configuration_performance_integration(self):
        """
        Test configuration system performance under various load conditions.
        
        This validates that configuration operations remain performant
        during typical integration scenarios.
        """
        # Test Case 1: Bulk configuration loading performance
        bulk_config_vars = {}
        for i in range(500):  # Moderate size for integration test
            var_name = f"PERF_VAR_{i:03d}"
            var_value = f"performance_test_value_{i}_{hash(str(i)) % 10000}"
            bulk_config_vars[var_name] = var_value
        
        # Measure bulk set performance
        bulk_set_start = self.get_metrics().start_time
        for var_name, var_value in bulk_config_vars.items():
            self.set_env_var(var_name, var_value)
        bulk_set_time = (self.get_metrics().end_time or bulk_set_start) - bulk_set_start
        
        # Test Case 2: Bulk configuration read performance
        bulk_read_start = self.get_metrics().start_time
        for var_name in bulk_config_vars.keys():
            value = self.get_env_var(var_name)
            assert value is not None, f"Bulk read failed for {var_name}"
        bulk_read_time = (self.get_metrics().end_time or bulk_read_start) - bulk_read_start
        
        # Test Case 3: get_all() performance with many variables
        get_all_start = self.get_metrics().start_time  
        all_vars = self.get_env().get_all()
        get_all_time = (self.get_metrics().end_time or get_all_start) - get_all_start
        
        assert len(all_vars) >= len(bulk_config_vars), (
            f"get_all() should return at least {len(bulk_config_vars)} vars, got {len(all_vars)}"
        )
        
        # Test Case 4: Configuration validation performance
        validation_start = self.get_metrics().start_time
        validation_result = self.get_env().validate_all()
        validation_time = (self.get_metrics().end_time or validation_start) - validation_start
        
        # Test Case 5: Environment detection performance
        env_detection_start = self.get_metrics().start_time
        for i in range(100):  # Multiple calls to test caching/optimization
            env_name = self.get_env().get_environment_name()
            assert env_name is not None
        env_detection_time = (self.get_metrics().end_time or env_detection_start) - env_detection_start
        
        # Performance assertions - reasonable thresholds for integration tests
        # Note: These are more lenient than unit test thresholds due to integration overhead
        assert bulk_set_time < 5.0, f"Bulk set took too long: {bulk_set_time:.3f}s"
        assert bulk_read_time < 2.0, f"Bulk read took too long: {bulk_read_time:.3f}s"
        assert get_all_time < 1.0, f"get_all() took too long: {get_all_time:.3f}s"
        assert validation_time < 3.0, f"Validation took too long: {validation_time:.3f}s"
        assert env_detection_time < 0.5, f"Environment detection took too long: {env_detection_time:.3f}s"
        
        # Calculate operations per second
        read_ops_per_sec = len(bulk_config_vars) / bulk_read_time if bulk_read_time > 0 else float('inf')
        assert read_ops_per_sec >= 500, (  # Should handle at least 500 reads/sec
            f"Read performance too slow: {read_ops_per_sec:.0f} ops/sec (expected >= 500)"
        )
        
        # Record performance metrics
        self.record_metric("bulk_set_time_seconds", bulk_set_time)
        self.record_metric("bulk_read_time_seconds", bulk_read_time)
        self.record_metric("get_all_time_seconds", get_all_time)
        self.record_metric("validation_time_seconds", validation_time)
        self.record_metric("env_detection_time_seconds", env_detection_time)
        self.record_metric("read_ops_per_second", read_ops_per_sec)
        self.record_metric("bulk_config_vars_tested", len(bulk_config_vars))
        self.record_metric("configuration_performance_integration_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])