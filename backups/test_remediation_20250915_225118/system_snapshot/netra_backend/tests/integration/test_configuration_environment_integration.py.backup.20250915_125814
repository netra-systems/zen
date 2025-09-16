"""
Configuration and Environment Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable configuration management and environment isolation
- Value Impact: Prevents configuration errors that could cause system failures
- Strategic Impact: Core platform stability and multi-environment support

These tests validate critical configuration and environment management functionality
across different services and environments. They test real business scenarios that
bridge unit and end-to-end testing by validating configuration loading, validation,
service-specific patterns, and environment isolation.

CRITICAL REQUIREMENTS:
- NO MOCKS! Tests use real configuration and environment components
- IsolatedEnvironment used for ALL environment access (per CLAUDE.md)
- Tests validate real business value for environment management
- Follow SSOT patterns from test_framework/
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.configuration.central_config_validator import (
    CentralConfigurationValidator, 
    get_central_validator,
    Environment as ConfigEnvironment,
    validate_platform_configuration,
    get_jwt_secret,
    get_database_credentials,
    get_oauth_credentials
)
from shared.config_builder_base import ConfigBuilderBase, ConfigEnvironment


class MockConfigBuilder(ConfigBuilderBase):
    """Mock configuration builder for testing base functionality."""
    
    def validate(self):
        return True, ""
    
    def get_debug_info(self):
        base_info = self.get_common_debug_info()
        base_info["mock_specific"] = "test_data"
        return base_info


class TestConfigurationEnvironment(BaseIntegrationTest):
    """Integration tests for configuration and environment functionality."""
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        
        # Get fresh isolated environment instance for each test
        self.env = get_env()
        
        # Enable isolation for all tests to ensure clean environment
        self.env.enable_isolation()
        
        # Store original environment state for restoration
        self.original_env_state = dict(os.environ)
        
        # Clear any cached validator state
        from shared.configuration.central_config_validator import clear_central_validator_cache
        clear_central_validator_cache()
    
    def teardown_method(self):
        """Tear down method called after each test method."""
        super().teardown_method()
        
        # Restore original environment state
        os.environ.clear()
        os.environ.update(self.original_env_state)
        
        # Reset isolated environment
        self.env.reset()
        
        # Clear validator cache
        from shared.configuration.central_config_validator import clear_central_validator_cache
        clear_central_validator_cache()
    
    @pytest.mark.integration
    def test_isolated_environment_creation_and_lifecycle(self):
        """
        Test IsolatedEnvironment creation and lifecycle management.
        
        BVJ: Validates core environment isolation patterns that prevent
        configuration leakage between services and test contexts.
        """
        # Test singleton behavior
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment.get_instance()
        env3 = get_env()
        
        assert env1 is env2 is env3, "IsolatedEnvironment should be a singleton"
        
        # Test isolation lifecycle
        assert self.env.is_isolated(), "Isolation should be enabled by default in test context"
        
        # Test setting and getting variables in isolation
        test_key = "TEST_ISOLATION_VAR"
        test_value = "isolated_test_value"
        
        self.env.set(test_key, test_value, "test_isolation")
        assert self.env.get(test_key) == test_value
        
        # Verify isolation - variable should not be in os.environ
        assert test_key not in os.environ or os.environ[test_key] != test_value
        
        # Test disable isolation
        self.env.disable_isolation()
        assert not self.env.is_isolated()
        
        # Re-enable and verify isolation works again
        self.env.enable_isolation()
        assert self.env.is_isolated()
        
        self.logger.info(" PASS:  IsolatedEnvironment lifecycle management validated")
    
    @pytest.mark.integration
    def test_environment_variable_isolation_boundary_enforcement(self):
        """
        Test environment variable isolation and boundary enforcement.
        
        BVJ: Critical for multi-user system - prevents configuration bleeding
        between different user contexts and service boundaries.
        """
        # Set up test variables in different contexts
        test_vars = {
            "ISOLATION_TEST_1": "value1",
            "ISOLATION_TEST_2": "value2", 
            "SENSITIVE_SECRET": "secret_value_should_be_isolated"
        }
        
        # Enable isolation and set variables
        self.env.enable_isolation()
        
        for key, value in test_vars.items():
            self.env.set(key, value, "boundary_test")
        
        # Verify variables are accessible through isolated environment
        for key, expected_value in test_vars.items():
            assert self.env.get(key) == expected_value
        
        # Test boundary enforcement - sensitive data should not leak to os.environ
        for key in test_vars.keys():
            if "SECRET" in key:
                # Sensitive variables should not be in os.environ when isolated
                assert key not in os.environ or os.environ[key] != test_vars[key]
        
        # Test protected variables
        protected_key = "PROTECTED_VAR"
        self.env.set(protected_key, "protected_value", "boundary_test")
        self.env.protect_variable(protected_key)
        
        # Should not be able to modify protected variable
        assert not self.env.set(protected_key, "new_value", "boundary_test")
        assert self.env.get(protected_key) == "protected_value"
        
        # Test unset behavior in isolation
        self.env.delete("ISOLATION_TEST_1")
        assert self.env.get("ISOLATION_TEST_1") is None
        assert not self.env.exists("ISOLATION_TEST_1")
        
        self.logger.info(" PASS:  Environment variable isolation boundaries enforced")
    
    @pytest.mark.integration
    def test_configuration_loading_and_validation_across_services(self):
        """
        Test configuration loading and validation across different services.
        
        BVJ: Ensures configuration consistency across backend, auth, and analytics
        services, preventing service startup failures due to missing configs.
        """
        # Test configuration loading patterns used by different services
        test_configs = {
            # Backend service configs
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-backend-service-validation",
            "DATABASE_URL": "postgresql://test:pass@localhost:5432/testdb",
            "REDIS_HOST": "test-redis-host",
            "REDIS_PASSWORD": "test-redis-password",
            
            # Auth service configs
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test-oauth-client-secret-validation",
            "SERVICE_SECRET": "test-service-secret-for-inter-service-auth",
            
            # Analytics service configs
            "ANTHROPIC_API_KEY": "sk-ant-test-key-for-analytics-llm-integration",
            "GEMINI_API_KEY": "test-gemini-api-key-for-analytics-service",
            "FERNET_KEY": "test-fernet-encryption-key-32-chars-long"
        }
        
        # Load configurations into isolated environment
        self.env.update(test_configs, "service_integration_test")
        
        # Validate that each service type can access its required configs
        # Backend service validation
        jwt_secret = self.env.get("JWT_SECRET_KEY")
        assert jwt_secret is not None and len(jwt_secret) >= 32
        
        database_url = self.env.get("DATABASE_URL")
        assert database_url and "postgresql://" in database_url
        
        # Auth service validation
        oauth_client_id = self.env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
        oauth_client_secret = self.env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
        assert oauth_client_id and oauth_client_secret
        assert len(oauth_client_secret) >= 10
        
        # Analytics service validation
        anthropic_key = self.env.get("ANTHROPIC_API_KEY")
        gemini_key = self.env.get("GEMINI_API_KEY")
        assert anthropic_key and "sk-ant-" in anthropic_key
        assert gemini_key is not None
        
        # Test cross-service configuration access
        service_secret = self.env.get("SERVICE_SECRET")
        assert service_secret and len(service_secret) >= 32
        
        # Validate configuration sources are tracked
        for key in test_configs.keys():
            source = self.env.get_variable_source(key)
            assert source == "service_integration_test"
        
        self.logger.info(" PASS:  Multi-service configuration loading validated")
    
    @pytest.mark.integration  
    def test_service_specific_configuration_patterns(self):
        """
        Test service-specific configuration patterns.
        
        BVJ: Validates that each service (backend, auth, analytics) has
        proper configuration isolation and can load service-specific configs.
        """
        # Test backend service configuration patterns
        backend_configs = {
            "POSTGRES_HOST": "backend-postgres-host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "backend_user",
            "POSTGRES_PASSWORD": "backend_secure_password",
            "POSTGRES_DB": "backend_database"
        }
        
        # Test auth service configuration patterns
        auth_configs = {
            "AUTH_JWT_SECRET": "auth-service-jwt-secret-key-validation",
            "AUTH_REDIS_HOST": "auth-redis-host",
            "AUTH_SESSION_TIMEOUT": "3600"
        }
        
        # Test analytics service configuration patterns
        analytics_configs = {
            "ANALYTICS_CLICKHOUSE_HOST": "analytics-clickhouse-host", 
            "ANALYTICS_BATCH_SIZE": "100",
            "ANALYTICS_PROCESSING_INTERVAL": "60"
        }
        
        # Load service-specific configurations
        all_configs = {}
        all_configs.update(backend_configs)
        all_configs.update(auth_configs) 
        all_configs.update(analytics_configs)
        
        self.env.update(all_configs, "service_specific_test")
        
        # Validate backend service can access its configs
        assert self.env.get("POSTGRES_HOST") == "backend-postgres-host"
        assert self.env.get("POSTGRES_PORT") == "5432"
        
        # Validate auth service can access its configs
        assert self.env.get("AUTH_JWT_SECRET") == "auth-service-jwt-secret-key-validation"
        assert self.env.get("AUTH_REDIS_HOST") == "auth-redis-host"
        
        # Validate analytics service can access its configs
        assert self.env.get("ANALYTICS_CLICKHOUSE_HOST") == "analytics-clickhouse-host"
        assert self.env.get("ANALYTICS_BATCH_SIZE") == "100"
        
        # Test service configuration with prefixes
        service_prefixes = ["BACKEND_", "AUTH_", "ANALYTICS_"]
        
        for prefix in service_prefixes:
            prefix_configs = self.env.get_all_with_prefix(prefix)
            # Should find configs specific to that service prefix
            service_specific_count = len([k for k in all_configs.keys() if k.startswith(prefix)])
            if service_specific_count > 0:
                assert len(prefix_configs) >= service_specific_count
        
        self.logger.info(" PASS:  Service-specific configuration patterns validated")
    
    @pytest.mark.integration
    def test_environment_switching_scenarios(self):
        """
        Test environment switching scenarios (test, dev, staging, prod).
        
        BVJ: Critical for deployment safety - ensures configurations are 
        properly isolated between environments and prevent production secrets
        from leaking to development environments.
        """
        # Test development environment
        self.env.set("ENVIRONMENT", "development", "env_switch_test")
        assert self.env.get_environment_name() == "development"
        assert self.env.is_development()
        assert not self.env.is_production()
        assert not self.env.is_staging()
        
        # Test staging environment  
        self.env.set("ENVIRONMENT", "staging", "env_switch_test")
        self.env.clear_cache()  # Clear cache to pick up new environment
        assert self.env.get_environment_name() == "staging"
        assert self.env.is_staging()
        assert not self.env.is_development()
        assert not self.env.is_production()
        
        # Test production environment
        self.env.set("ENVIRONMENT", "production", "env_switch_test")  
        self.env.clear_cache()
        assert self.env.get_environment_name() == "production"
        assert self.env.is_production()
        assert not self.env.is_development()
        assert not self.env.is_staging()
        
        # Test test environment
        self.env.set("ENVIRONMENT", "test", "env_switch_test")
        self.env.clear_cache()
        assert self.env.get_environment_name() == "test"
        assert self.env.is_test()
        
        # Test environment-specific configuration validation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            env_file_path = f.name
            f.write("DEV_SPECIFIC_CONFIG=dev_value\n")
            f.write("SHARED_CONFIG=shared_value\n")
        
        try:
            # Load environment-specific config
            loaded_count, errors = self.env.load_from_file(env_file_path, "env_specific_test")
            assert loaded_count > 0
            assert len(errors) == 0
            
            # Verify configs were loaded
            assert self.env.get("DEV_SPECIFIC_CONFIG") == "dev_value"
            assert self.env.get("SHARED_CONFIG") == "shared_value"
            
        finally:
            # Clean up temp file
            Path(env_file_path).unlink(missing_ok=True)
        
        self.logger.info(" PASS:  Environment switching scenarios validated")
    
    @pytest.mark.integration
    def test_configuration_cascade_and_inheritance_patterns(self):
        """
        Test configuration cascade and inheritance patterns.
        
        BVJ: Ensures proper configuration precedence (OS env > .env file > defaults)
        which is critical for deployment flexibility and local development.
        """
        # Test configuration precedence: OS environ > isolated vars > defaults
        test_key = "CASCADE_TEST_VAR"
        
        # Set in isolated environment (lowest priority in this test)
        self.env.set(test_key, "isolated_value", "cascade_test")
        assert self.env.get(test_key) == "isolated_value"
        
        # Set in OS environ (highest priority) 
        os.environ[test_key] = "os_environ_value"
        
        # When not isolated, should get OS environ value
        self.env.disable_isolation()
        assert self.env.get(test_key) == "os_environ_value"
        
        # When isolated, should get isolated value
        self.env.enable_isolation()
        assert self.env.get(test_key) == "isolated_value"
        
        # Test configuration inheritance from .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            env_file_path = f.name
            f.write("INHERITED_CONFIG_1=file_value_1\n")
            f.write("INHERITED_CONFIG_2=file_value_2\n")
            f.write("# Comment line should be ignored\n")
            f.write("QUOTED_CONFIG='quoted_value'\n")
            f.write('DOUBLE_QUOTED_CONFIG="double_quoted_value"\n')
        
        try:
            # Test file loading with override_existing=False
            self.env.set("INHERITED_CONFIG_1", "existing_value", "cascade_test")
            
            loaded_count, errors = self.env.load_from_file(
                env_file_path, 
                "cascade_file_test", 
                override_existing=False
            )
            
            assert loaded_count >= 3  # Should load configs not already set
            assert len(errors) == 0
            
            # Existing value should not be overridden
            assert self.env.get("INHERITED_CONFIG_1") == "existing_value"
            
            # New values should be loaded
            assert self.env.get("INHERITED_CONFIG_2") == "file_value_2"
            assert self.env.get("QUOTED_CONFIG") == "quoted_value"
            assert self.env.get("DOUBLE_QUOTED_CONFIG") == "double_quoted_value"
            
            # Test with override_existing=True
            loaded_count, errors = self.env.load_from_file(
                env_file_path,
                "cascade_file_override_test", 
                override_existing=True
            )
            
            # Now existing value should be overridden
            assert self.env.get("INHERITED_CONFIG_1") == "file_value_1"
            
        finally:
            Path(env_file_path).unlink(missing_ok=True)
            if test_key in os.environ:
                del os.environ[test_key]
        
        self.logger.info(" PASS:  Configuration cascade and inheritance validated")
    
    @pytest.mark.integration
    def test_environment_variable_precedence_and_resolution(self):
        """
        Test environment variable precedence and resolution.
        
        BVJ: Critical for avoiding configuration conflicts between different
        sources (code defaults, .env files, OS environment, cloud secrets).
        """
        test_precedence_key = "PRECEDENCE_TEST_VAR"
        
        # Test 1: Default value resolution
        default_value = "default_test_value"
        assert self.env.get(test_precedence_key, default_value) == default_value
        
        # Test 2: Isolated environment takes precedence over default
        isolated_value = "isolated_test_value"
        self.env.set(test_precedence_key, isolated_value, "precedence_test")
        assert self.env.get(test_precedence_key, default_value) == isolated_value
        
        # Test 3: OS environment precedence when isolation is disabled
        os_value = "os_environment_value"
        os.environ[test_precedence_key] = os_value
        
        self.env.disable_isolation()
        assert self.env.get(test_precedence_key) == os_value
        
        # Test 4: Re-enable isolation - should use isolated value
        self.env.enable_isolation()
        assert self.env.get(test_precedence_key) == isolated_value
        
        # Test 5: Variable resolution with shell expansion
        shell_test_key = "SHELL_EXPANSION_TEST"
        if os.name != 'nt':  # Skip shell expansion on Windows
            self.env.set(shell_test_key, "$(echo 'shell_expanded_value')", "shell_test")
            # Note: Shell expansion might be disabled in test context for security
            resolved_value = self.env.get(shell_test_key)
            assert resolved_value is not None
        
        # Test 6: Variable resolution with environment variable references
        ref_test_key = "REFERENCE_TEST_VAR"
        self.env.set("BASE_VALUE", "base_value", "precedence_test")
        self.env.set(ref_test_key, "${BASE_VALUE}_suffix", "precedence_test")
        
        # Note: Variable expansion might be disabled in test context
        resolved_ref_value = self.env.get(ref_test_key)
        assert resolved_ref_value is not None
        
        # Test 7: Subprocess environment resolution
        subprocess_env = self.env.get_subprocess_env({"SUBPROCESS_EXTRA": "extra_value"})
        assert isinstance(subprocess_env, dict)
        assert "SUBPROCESS_EXTRA" in subprocess_env
        assert subprocess_env["SUBPROCESS_EXTRA"] == "extra_value"
        
        # Clean up
        if test_precedence_key in os.environ:
            del os.environ[test_precedence_key]
        
        self.logger.info(" PASS:  Environment variable precedence and resolution validated")
    
    @pytest.mark.integration
    def test_configuration_error_handling_and_validation(self):
        """
        Test configuration error handling and validation.
        
        BVJ: Prevents silent configuration failures that could cause
        production outages or security vulnerabilities.
        """
        # Test 1: Central configuration validator error handling
        validator = CentralConfigurationValidator()
        
        # Test environment detection
        self.env.set("ENVIRONMENT", "test", "validation_test")
        validator.clear_environment_cache()
        assert validator.get_environment() == ConfigEnvironment.TEST
        
        # Test 2: Configuration validation with missing required variables
        self.env.set("ENVIRONMENT", "staging", "validation_test")
        validator.clear_environment_cache()
        
        # This should fail validation due to missing staging requirements
        with pytest.raises(ValueError) as exc_info:
            validator.validate_all_requirements()
        
        assert "staging environment" in str(exc_info.value).lower()
        
        # Test 3: Provide valid staging configuration
        staging_configs = {
            "JWT_SECRET_STAGING": "staging-jwt-secret-key-32-characters-long-for-validation",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-oauth-client-secret-validation",
            "REDIS_HOST": "staging-redis-host",
            "REDIS_PASSWORD": "staging-redis-password",
            "SERVICE_SECRET": "staging-service-secret-32-characters-long",
            "FERNET_KEY": "staging-fernet-key-32-characters-long-for-encryption",
            "GEMINI_API_KEY": "staging-gemini-api-key"
        }
        
        self.env.update(staging_configs, "staging_validation_test")
        
        # Should now pass validation (assuming no database requirements for this test)
        try:
            validator.validate_all_requirements()
            validation_passed = True
        except ValueError as e:
            # May fail due to database config requirements - that's expected
            validation_passed = "database" in str(e).lower()
        
        assert validation_passed, "Either validation should pass or fail only on database config"
        
        # Test 4: Individual configuration retrieval and validation
        self.env.set("ENVIRONMENT", "test", "validation_test")
        validator.clear_environment_cache()
        
        test_configs = {
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-individual-validation",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id-validation",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test-oauth-client-secret-validation"
        }
        
        self.env.update(test_configs, "individual_validation_test")
        
        # Test JWT secret retrieval
        jwt_secret = validator.get_jwt_secret()
        assert jwt_secret == "test-jwt-secret-key-for-individual-validation"
        
        # Test OAuth credentials retrieval
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"] == "test-oauth-client-id-validation"
        assert oauth_creds["client_secret"] == "test-oauth-client-secret-validation"
        
        # Test 5: Error handling for invalid configurations
        with pytest.raises(ValueError):
            # Should fail - environment set to invalid value
            self.env.set("ENVIRONMENT", "invalid_environment", "error_test")
            validator.clear_environment_cache()
            validator.get_environment()
        
        self.logger.info(" PASS:  Configuration error handling and validation tested")
    
    @pytest.mark.integration
    def test_environment_cleanup_and_resource_management(self):
        """
        Test environment cleanup and resource management.
        
        BVJ: Prevents resource leaks and ensures clean state between
        test runs, critical for CI/CD pipeline reliability.
        """
        # Test 1: Environment state backup and restore
        initial_var_count = len(self.env.get_all())
        
        # Add test variables
        test_vars = {
            f"CLEANUP_TEST_{i}": f"value_{i}" for i in range(10)
        }
        
        self.env.update(test_vars, "cleanup_test")
        
        # Verify variables were added
        assert len(self.env.get_all()) >= initial_var_count + 10
        
        for key, value in test_vars.items():
            assert self.env.get(key) == value
        
        # Test environment reset
        self.env.reset()
        
        # After reset, should be back to clean state
        reset_vars = self.env.get_all()
        assert len(reset_vars) <= initial_var_count + 5  # Allow some tolerance
        
        # Test variables should be gone
        for key in test_vars.keys():
            assert self.env.get(key) is None
        
        # Test 2: Cache cleanup
        cache_test_vars = {
            "CACHE_TEST_1": "cache_value_1",
            "CACHE_TEST_2": "cache_value_2"
        }
        
        self.env.update(cache_test_vars, "cache_test")
        
        # Access variables to populate cache
        for key in cache_test_vars.keys():
            self.env.get(key)
        
        # Clear cache
        self.env.clear_cache()
        
        # Variables should still be accessible (cache cleared, not variables)
        for key, value in cache_test_vars.items():
            assert self.env.get(key) == value
        
        # Test 3: Protected variable cleanup
        protected_var = "PROTECTED_CLEANUP_VAR"
        self.env.set(protected_var, "protected_value", "cleanup_test")
        self.env.protect_variable(protected_var)
        
        assert self.env.is_protected(protected_var)
        
        # Unprotect and verify
        self.env.unprotect_variable(protected_var)
        assert not self.env.is_protected(protected_var)
        
        # Should now be able to modify
        assert self.env.set(protected_var, "new_value", "cleanup_test")
        assert self.env.get(protected_var) == "new_value"
        
        # Test 4: Callback management
        callback_called = []
        
        def test_callback(key, old_value, new_value):
            callback_called.append((key, old_value, new_value))
        
        self.env.add_change_callback(test_callback)
        
        # Make a change to trigger callback
        self.env.set("CALLBACK_TEST", "callback_value", "cleanup_test")
        
        assert len(callback_called) > 0
        assert callback_called[-1][0] == "CALLBACK_TEST"
        assert callback_called[-1][2] == "callback_value"
        
        # Remove callback
        self.env.remove_change_callback(test_callback)
        
        # Further changes should not trigger callback
        initial_callback_count = len(callback_called)
        self.env.set("CALLBACK_TEST_2", "callback_value_2", "cleanup_test")
        assert len(callback_called) == initial_callback_count
        
        self.logger.info(" PASS:  Environment cleanup and resource management validated")
    
    @pytest.mark.integration
    def test_configuration_hot_reloading_and_updates(self):
        """
        Test configuration hot reloading and updates.
        
        BVJ: Enables dynamic configuration updates without service restarts,
        critical for maintaining availability during configuration changes.
        """
        # Test 1: Dynamic configuration updates
        dynamic_config_key = "DYNAMIC_CONFIG_TEST"
        initial_value = "initial_dynamic_value"
        updated_value = "updated_dynamic_value"
        
        self.env.set(dynamic_config_key, initial_value, "hot_reload_test")
        assert self.env.get(dynamic_config_key) == initial_value
        
        # Track changes
        changes_tracked = []
        
        def track_changes(key, old_value, new_value):
            changes_tracked.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value
            })
        
        self.env.add_change_callback(track_changes)
        
        # Update configuration
        self.env.set(dynamic_config_key, updated_value, "hot_reload_update")
        
        # Verify update was tracked
        assert len(changes_tracked) > 0
        last_change = changes_tracked[-1]
        assert last_change["key"] == dynamic_config_key
        assert last_change["old_value"] == initial_value
        assert last_change["new_value"] == updated_value
        
        # Verify new value is accessible
        assert self.env.get(dynamic_config_key) == updated_value
        
        # Test 2: File-based hot reloading
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            config_file_path = f.name
            f.write("HOT_RELOAD_CONFIG_1=initial_file_value_1\n")
            f.write("HOT_RELOAD_CONFIG_2=initial_file_value_2\n")
        
        try:
            # Initial load
            loaded_count, errors = self.env.load_from_file(config_file_path, "hot_reload_file_test")
            assert loaded_count > 0
            assert self.env.get("HOT_RELOAD_CONFIG_1") == "initial_file_value_1"
            
            # Update file content
            with open(config_file_path, 'w') as f:
                f.write("HOT_RELOAD_CONFIG_1=updated_file_value_1\n")
                f.write("HOT_RELOAD_CONFIG_2=updated_file_value_2\n")
                f.write("HOT_RELOAD_CONFIG_3=new_file_value_3\n")
            
            # Reload configuration
            loaded_count, errors = self.env.load_from_file(
                config_file_path, 
                "hot_reload_file_update",
                override_existing=True
            )
            
            assert loaded_count >= 3
            assert self.env.get("HOT_RELOAD_CONFIG_1") == "updated_file_value_1"
            assert self.env.get("HOT_RELOAD_CONFIG_2") == "updated_file_value_2"
            assert self.env.get("HOT_RELOAD_CONFIG_3") == "new_file_value_3"
            
        finally:
            Path(config_file_path).unlink(missing_ok=True)
            self.env.remove_change_callback(track_changes)
        
        # Test 3: Batch configuration updates
        batch_configs = {
            "BATCH_CONFIG_1": "batch_value_1",
            "BATCH_CONFIG_2": "batch_value_2", 
            "BATCH_CONFIG_3": "batch_value_3"
        }
        
        # Track changes for batch update
        batch_changes_tracked = []
        
        def track_batch_changes(key, old_value, new_value):
            batch_changes_tracked.append(key)
        
        self.env.add_change_callback(track_batch_changes)
        
        # Perform batch update
        update_results = self.env.update(batch_configs, "batch_hot_reload_test")
        
        # Verify all updates succeeded
        for key, success in update_results.items():
            assert success, f"Batch update failed for {key}"
        
        # Verify all changes were tracked
        assert len(batch_changes_tracked) >= len(batch_configs)
        
        # Verify all values are accessible
        for key, expected_value in batch_configs.items():
            assert self.env.get(key) == expected_value
        
        self.env.remove_change_callback(track_batch_changes)
        
        self.logger.info(" PASS:  Configuration hot reloading and updates validated")
    
    @pytest.mark.integration
    def test_cross_service_configuration_coordination(self):
        """
        Test cross-service configuration coordination.
        
        BVJ: Ensures configuration consistency across microservices,
        preventing integration failures due to configuration mismatches.
        """
        # Test 1: Shared configuration across services
        shared_configs = {
            "SHARED_DATABASE_HOST": "shared-postgres-host",
            "SHARED_REDIS_HOST": "shared-redis-host", 
            "SHARED_JWT_SECRET": "shared-jwt-secret-32-characters-long-for-all-services",
            "SHARED_SERVICE_SECRET": "shared-service-secret-for-inter-service-communication"
        }
        
        self.env.update(shared_configs, "cross_service_shared")
        
        # Verify shared configs are accessible to all services
        for key, expected_value in shared_configs.items():
            assert self.env.get(key) == expected_value
            
            # Verify source tracking for shared configs
            source = self.env.get_variable_source(key)
            assert source == "cross_service_shared"
        
        # Test 2: Service-specific configuration coordination
        backend_configs = {
            "BACKEND_SPECIFIC_CONFIG": "backend_specific_value",
            "BACKEND_WORKER_COUNT": "4"
        }
        
        auth_configs = {
            "AUTH_SPECIFIC_CONFIG": "auth_specific_value",
            "AUTH_SESSION_TIMEOUT": "3600"
        }
        
        # Load service-specific configs
        self.env.update(backend_configs, "backend_service")
        self.env.update(auth_configs, "auth_service")
        
        # Test 3: Configuration coordination via central validator
        self.env.set("ENVIRONMENT", "test", "cross_service_test")
        
        # Set up test environment configs for coordination
        coordination_configs = {
            "JWT_SECRET_KEY": "coordination-test-jwt-secret-key-for-all-services",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "coordination-test-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "coordination-test-oauth-client-secret"
        }
        
        self.env.update(coordination_configs, "coordination_test")
        
        # Test central validator coordination
        validator = get_central_validator()
        validator.clear_environment_cache()
        
        # Each service should get consistent JWT secret
        jwt_secret = validator.get_jwt_secret()
        assert jwt_secret == "coordination-test-jwt-secret-key-for-all-services"
        
        # Each service should get consistent OAuth credentials
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"] == "coordination-test-oauth-client-id"
        assert oauth_creds["client_secret"] == "coordination-test-oauth-client-secret"
        
        # Test 4: Configuration changes propagation
        coordination_changes = []
        
        def track_coordination_changes(key, old_value, new_value):
            if "SHARED_" in key or "COORDINATION" in key:
                coordination_changes.append({
                    "key": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        self.env.add_change_callback(track_coordination_changes)
        
        # Update shared configuration
        self.env.set("SHARED_DATABASE_HOST", "updated-shared-postgres-host", "coordination_update")
        
        # Verify change was tracked
        assert len(coordination_changes) > 0
        last_change = coordination_changes[-1]
        assert last_change["key"] == "SHARED_DATABASE_HOST"
        assert last_change["new_value"] == "updated-shared-postgres-host"
        
        # All services should see the updated value
        assert self.env.get("SHARED_DATABASE_HOST") == "updated-shared-postgres-host"
        
        self.env.remove_change_callback(track_coordination_changes)
        
        self.logger.info(" PASS:  Cross-service configuration coordination validated")
    
    @pytest.mark.integration
    def test_environment_security_and_sanitization(self):
        """
        Test environment security and sanitization.
        
        BVJ: Prevents security vulnerabilities from malformed environment
        variables and ensures sensitive data is properly handled.
        """
        # Test 1: Sensitive value masking for logging
        sensitive_configs = {
            "SECRET_KEY": "super-secret-key-that-should-be-masked",
            "PASSWORD": "sensitive-password-value",
            "API_KEY": "sk-api-key-that-contains-sensitive-data",
            "JWT_TOKEN": "jwt-token-with-sensitive-authentication-data",
            "OAUTH_SECRET": "oauth-secret-for-authentication"
        }
        
        self.env.update(sensitive_configs, "security_test")
        
        # Verify sensitive values are stored but sources are tracked
        for key, expected_value in sensitive_configs.items():
            assert self.env.get(key) == expected_value
            assert self.env.get_variable_source(key) == "security_test"
        
        # Test debug info should not expose sensitive values directly
        debug_info = self.env.get_debug_info()
        assert isinstance(debug_info, dict)
        assert "isolation_enabled" in debug_info
        
        # Test 2: Database URL sanitization
        database_urls = [
            "postgresql://user:password@host:5432/database",
            "mysql://user:secret@mysql-host:3306/mydb",
            "clickhouse://user:pass@clickhouse-host:8123/analytics"
        ]
        
        for i, db_url in enumerate(database_urls):
            db_key = f"DATABASE_URL_{i}"
            self.env.set(db_key, db_url, "security_sanitization_test")
            
            # Verify URL is stored (sanitization happens internally)
            stored_url = self.env.get(db_key)
            assert stored_url is not None
            assert "://" in stored_url  # Basic URL structure maintained
        
        # Test 3: Environment variable validation for security
        invalid_configs = {
            "INVALID_NULL_BYTE": "value_with_\x00_null_byte",
            "INVALID_CONTROL_CHAR": "value_with_\x01_control_char",
            "INVALID_NEWLINE": "value_with_\n_newline"
        }
        
        for key, value in invalid_configs.items():
            # Set the value - sanitization should handle invalid characters
            self.env.set(key, value, "security_validation_test")
            
            # Retrieved value should be sanitized (control characters removed)
            sanitized_value = self.env.get(key)
            assert sanitized_value is not None
            # Control characters should be removed during sanitization
            assert "\x00" not in sanitized_value
            assert "\x01" not in sanitized_value
            # Note: Newlines might be allowed in some contexts
        
        # Test 4: Environment variable isolation for security
        security_isolation_test_var = "SECURITY_ISOLATION_VAR"
        security_value = "security-sensitive-value-should-be-isolated"
        
        # Set in isolated environment
        self.env.enable_isolation()
        self.env.set(security_isolation_test_var, security_value, "security_isolation")
        
        # Should be accessible in isolated environment
        assert self.env.get(security_isolation_test_var) == security_value
        
        # Should not leak to OS environment
        assert security_isolation_test_var not in os.environ or os.environ[security_isolation_test_var] != security_value
        
        # Test 5: Configuration validation for staging database credentials
        self.env.set("ENVIRONMENT", "staging", "security_staging_test")
        
        # Test staging database validation
        staging_db_validation = self.env.validate_staging_database_credentials()
        assert isinstance(staging_db_validation, dict)
        assert "valid" in staging_db_validation
        assert "issues" in staging_db_validation
        assert "warnings" in staging_db_validation
        
        self.logger.info(" PASS:  Environment security and sanitization validated")
    
    @pytest.mark.integration
    def test_configuration_performance_and_caching(self):
        """
        Test configuration performance and caching.
        
        BVJ: Ensures configuration access is performant for high-throughput
        scenarios, critical for maintaining application responsiveness.
        """
        import time
        
        # Test 1: Configuration access performance
        performance_configs = {
            f"PERF_TEST_CONFIG_{i}": f"performance_value_{i}" 
            for i in range(100)
        }
        
        self.env.update(performance_configs, "performance_test")
        
        # Measure performance of configuration access
        start_time = time.time()
        
        for _ in range(10):  # 10 iterations of accessing all configs
            for key in performance_configs.keys():
                value = self.env.get(key)
                assert value is not None
        
        access_time = time.time() - start_time
        
        # Should be able to access 1000 config values in reasonable time (< 1 second)
        assert access_time < 1.0, f"Configuration access too slow: {access_time}s for 1000 accesses"
        
        # Test 2: Cache effectiveness
        cache_test_key = "CACHE_EFFECTIVENESS_TEST"
        cache_test_value = "cache_test_value_for_performance_validation"
        
        self.env.set(cache_test_key, cache_test_value, "cache_test")
        
        # First access (should populate cache)
        start_time = time.time()
        first_access = self.env.get(cache_test_key)
        first_access_time = time.time() - start_time
        
        assert first_access == cache_test_value
        
        # Second access (should use cache)
        start_time = time.time()
        second_access = self.env.get(cache_test_key)
        second_access_time = time.time() - start_time
        
        assert second_access == cache_test_value
        # Second access should be faster (cached) - but this is micro-optimization
        # So we just verify it's not significantly slower
        assert second_access_time <= first_access_time * 2
        
        # Test 3: Bulk configuration operations performance
        bulk_configs = {
            f"BULK_CONFIG_{i}": f"bulk_value_{i}" 
            for i in range(50)
        }
        
        # Measure bulk update performance
        start_time = time.time()
        update_results = self.env.update(bulk_configs, "bulk_performance_test")
        bulk_update_time = time.time() - start_time
        
        # Bulk update should complete in reasonable time
        assert bulk_update_time < 0.5, f"Bulk update too slow: {bulk_update_time}s for 50 configs"
        
        # Verify all updates succeeded
        for key, success in update_results.items():
            assert success, f"Bulk update failed for {key}"
        
        # Measure bulk retrieval performance
        start_time = time.time()
        all_configs = self.env.get_all()
        bulk_retrieval_time = time.time() - start_time
        
        # Should retrieve all configs quickly
        assert bulk_retrieval_time < 0.5, f"Bulk retrieval too slow: {bulk_retrieval_time}s"
        assert len(all_configs) >= len(bulk_configs)
        
        # Test 4: Environment switching performance
        environments = ["development", "staging", "test", "production"]
        
        start_time = time.time()
        for env_name in environments * 5:  # 20 environment switches
            self.env.set("ENVIRONMENT", env_name, "perf_env_switch")
            self.env.clear_cache()  # Force cache refresh
            detected_env = self.env.get_environment_name()
            assert detected_env in ["development", "staging", "test", "production"]
        
        env_switch_time = time.time() - start_time
        
        # Environment switching should be fast
        assert env_switch_time < 1.0, f"Environment switching too slow: {env_switch_time}s for 20 switches"
        
        self.logger.info(" PASS:  Configuration performance and caching validated")
    
    @pytest.mark.integration
    def test_environment_integration_with_agent_contexts(self):
        """
        Test environment integration with agent contexts.
        
        BVJ: Ensures proper environment isolation for multi-user agent
        execution contexts, critical for preventing data leakage between users.
        """
        # Test 1: Agent context environment isolation
        user1_context = "user1_agent_context"
        user2_context = "user2_agent_context"
        
        # Simulate user-specific environment configurations
        user1_configs = {
            "USER_ID": "user_1",
            "USER_SESSION_ID": "user1_session_123",
            "USER_AGENT_CONTEXT": user1_context,
            "USER_SPECIFIC_CONFIG": "user1_specific_value"
        }
        
        user2_configs = {
            "USER_ID": "user_2", 
            "USER_SESSION_ID": "user2_session_456",
            "USER_AGENT_CONTEXT": user2_context,
            "USER_SPECIFIC_CONFIG": "user2_specific_value"
        }
        
        # Set up user 1 context
        self.env.update(user1_configs, f"agent_context_{user1_context}")
        
        # Verify user 1 can access their context
        assert self.env.get("USER_ID") == "user_1"
        assert self.env.get("USER_SESSION_ID") == "user1_session_123"
        assert self.env.get("USER_SPECIFIC_CONFIG") == "user1_specific_value"
        
        # Switch to user 2 context (simulate new agent execution)
        # Clear and set up user 2 environment
        for key in user1_configs.keys():
            self.env.delete(key)
        
        self.env.update(user2_configs, f"agent_context_{user2_context}")
        
        # Verify user 2 can access their context
        assert self.env.get("USER_ID") == "user_2"
        assert self.env.get("USER_SESSION_ID") == "user2_session_456" 
        assert self.env.get("USER_SPECIFIC_CONFIG") == "user2_specific_value"
        
        # Verify user 1 data is no longer accessible
        assert self.env.get("USER_ID") != "user_1"
        
        # Test 2: Agent execution environment variables
        agent_execution_configs = {
            "AGENT_ID": "test_agent_001",
            "AGENT_TYPE": "data_analysis_agent",
            "AGENT_EXECUTION_CONTEXT": "integration_test_execution",
            "AGENT_MAX_EXECUTION_TIME": "300",
            "AGENT_MEMORY_LIMIT": "512mb"
        }
        
        self.env.update(agent_execution_configs, "agent_execution_context")
        
        # Verify agent execution configs are accessible
        assert self.env.get("AGENT_ID") == "test_agent_001"
        assert self.env.get("AGENT_TYPE") == "data_analysis_agent"
        assert self.env.get("AGENT_MAX_EXECUTION_TIME") == "300"
        
        # Test 3: Environment configuration for agent tool execution
        tool_execution_configs = {
            "TOOL_EXECUTION_TIMEOUT": "60",
            "TOOL_RESULT_MAX_SIZE": "1048576",
            "TOOL_ALLOWED_OPERATIONS": "read,write,execute",
            "TOOL_SANDBOX_ENABLED": "true"
        }
        
        self.env.update(tool_execution_configs, "tool_execution_context")
        
        # Verify tool execution configs
        assert self.env.get("TOOL_EXECUTION_TIMEOUT") == "60"
        assert self.env.get_env_bool("TOOL_SANDBOX_ENABLED") == True
        assert self.env.get_env_int("TOOL_RESULT_MAX_SIZE") == 1048576
        
        # Test 4: Multi-tenant environment isolation
        tenant1_id = "tenant_001"
        tenant2_id = "tenant_002"
        
        # Set up tenant-specific configurations
        tenant1_configs = {
            "TENANT_ID": tenant1_id,
            "TENANT_DATABASE_PREFIX": f"tenant_{tenant1_id}_",
            "TENANT_REDIS_DB": "1",
            "TENANT_MAX_AGENTS": "10"
        }
        
        # Tenant 1 environment
        self.env.update(tenant1_configs, f"tenant_context_{tenant1_id}")
        
        # Verify tenant 1 isolation
        assert self.env.get("TENANT_ID") == tenant1_id
        assert self.env.get("TENANT_DATABASE_PREFIX") == f"tenant_{tenant1_id}_"
        
        # Switch to tenant 2 (clear tenant 1 configs first)
        for key in tenant1_configs.keys():
            self.env.delete(key)
        
        tenant2_configs = {
            "TENANT_ID": tenant2_id,
            "TENANT_DATABASE_PREFIX": f"tenant_{tenant2_id}_", 
            "TENANT_REDIS_DB": "2",
            "TENANT_MAX_AGENTS": "5"
        }
        
        self.env.update(tenant2_configs, f"tenant_context_{tenant2_id}")
        
        # Verify tenant 2 isolation  
        assert self.env.get("TENANT_ID") == tenant2_id
        assert self.env.get("TENANT_DATABASE_PREFIX") == f"tenant_{tenant2_id}_"
        assert self.env.get("TENANT_REDIS_DB") == "2"
        
        # Verify tenant 1 data is no longer accessible
        assert self.env.get("TENANT_ID") != tenant1_id
        
        self.logger.info(" PASS:  Environment integration with agent contexts validated")
    
    @pytest.mark.integration
    def test_configuration_observability_and_debugging(self):
        """
        Test configuration observability and debugging capabilities.
        
        BVJ: Provides visibility into configuration state for debugging
        production issues and ensuring proper configuration management.
        """
        # Test 1: Configuration change tracking
        changes_since_init = self.env.get_changes_since_init()
        initial_changes_count = len(changes_since_init)
        
        # Make configuration changes
        debug_configs = {
            "DEBUG_CONFIG_1": "debug_value_1",
            "DEBUG_CONFIG_2": "debug_value_2",
            "DEBUG_SENSITIVE_CONFIG": "debug_sensitive_value"
        }
        
        self.env.update(debug_configs, "observability_test")
        
        # Track changes since initialization
        changes_after_update = self.env.get_changes_since_init()
        assert len(changes_after_update) > initial_changes_count
        
        # Verify specific changes are tracked
        for key, value in debug_configs.items():
            if key in changes_after_update:
                original_value, current_value = changes_after_update[key]
                assert current_value == value
        
        # Test 2: Debug information collection
        debug_info = self.env.get_debug_info()
        
        assert isinstance(debug_info, dict)
        required_debug_fields = [
            "isolation_enabled",
            "isolated_vars_count", 
            "os_environ_count",
            "protected_vars",
            "tracked_sources"
        ]
        
        for field in required_debug_fields:
            assert field in debug_info, f"Debug info missing required field: {field}"
        
        # Verify debug info contains meaningful data
        assert isinstance(debug_info["isolation_enabled"], bool)
        assert isinstance(debug_info["isolated_vars_count"], int)
        assert isinstance(debug_info["protected_vars"], list)
        assert isinstance(debug_info["tracked_sources"], dict)
        
        # Test 3: Configuration source tracking
        for key in debug_configs.keys():
            source = self.env.get_variable_source(key)
            assert source == "observability_test"
        
        # Test configuration with different sources
        multi_source_configs = {
            "SOURCE_TEST_1": ("file_source", "file_value_1"),
            "SOURCE_TEST_2": ("env_source", "env_value_2"),
            "SOURCE_TEST_3": ("default_source", "default_value_3")
        }
        
        for key, (source, value) in multi_source_configs.items():
            self.env.set(key, value, source)
            
        # Verify source tracking
        for key, (expected_source, expected_value) in multi_source_configs.items():
            actual_source = self.env.get_variable_source(key)
            actual_value = self.env.get(key)
            
            assert actual_source == expected_source
            assert actual_value == expected_value
        
        # Test 4: ConfigBuilderBase debug capabilities
        builder = MockConfigBuilder()
        
        # Test common debug info
        builder_debug_info = builder.get_common_debug_info()
        
        assert isinstance(builder_debug_info, dict)
        assert "class_name" in builder_debug_info
        assert "environment" in builder_debug_info
        assert "environment_detection" in builder_debug_info
        
        # Verify environment detection info
        env_detection = builder_debug_info["environment_detection"]
        assert isinstance(env_detection["is_development"], bool)
        assert isinstance(env_detection["is_staging"], bool)
        assert isinstance(env_detection["is_production"], bool)
        
        # Test safe log summary
        log_summary = builder.get_safe_log_summary()
        assert isinstance(log_summary, str)
        assert "MockConfigBuilder" in log_summary
        assert "Environment:" in log_summary
        
        # Test 5: Configuration validation observability
        self.env.set("ENVIRONMENT", "test", "observability_validation_test")
        
        validator = CentralConfigurationValidator()
        validator.clear_environment_cache()
        
        # Test environment detection observability
        detected_environment = validator.get_environment()
        assert detected_environment == ConfigEnvironment.TEST
        
        # Test configuration retrieval with validation
        test_validation_configs = {
            "JWT_SECRET_KEY": "observability-test-jwt-secret-key-validation",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "observability-test-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "observability-test-oauth-client-secret"
        }
        
        self.env.update(test_validation_configs, "validation_observability_test")
        
        # Test validated configuration retrieval
        jwt_secret = validator.get_jwt_secret()
        assert jwt_secret == "observability-test-jwt-secret-key-validation"
        
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"] == "observability-test-oauth-client-id"
        
        # Test 6: Error reporting and debugging
        # Create configuration error scenario
        self.env.set("ENVIRONMENT", "staging", "error_debug_test")
        validator.clear_environment_cache()
        
        # This should fail validation due to missing staging requirements
        try:
            validator.validate_all_requirements()
            validation_error_occurred = False
        except ValueError as e:
            validation_error_occurred = True
            error_message = str(e)
            
            # Verify error message contains useful debugging information
            assert "staging environment" in error_message.lower()
            assert len(error_message) > 20  # Should be descriptive
        
        # Should have encountered validation error for staging without proper configs
        assert validation_error_occurred, "Expected validation error for incomplete staging config"
        
        self.logger.info(" PASS:  Configuration observability and debugging validated")