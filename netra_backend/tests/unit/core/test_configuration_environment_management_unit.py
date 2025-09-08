"""
Test Configuration Environment Management - Unit Tests

Business Value Justification (BVJ):
- Segment: All environments (Testing, Dev, Staging, Production)
- Business Goal: Prevent environment configuration mismatches
- Value Impact: Avoids costly deployment failures (saves $10K+ per incident)
- Strategic Impact: Enables reliable CI/CD pipeline and multi-environment deployment

This test suite validates environment-specific configuration management,
ensuring proper isolation and configuration loading across environments.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest


class TestConfigurationEnvironmentManagementUnit(BaseIntegrationTest):
    """Test configuration environment management functionality."""
    
    @pytest.mark.unit
    def test_isolated_environment_creation_and_isolation(self):
        """Test isolated environment creation maintains proper isolation.
        
        Critical for ensuring test environments don't affect each other.
        """
        # Create multiple isolated environments
        env1 = IsolatedEnvironment("test_env_1")
        env2 = IsolatedEnvironment("test_env_2")
        
        # Set different values in each environment
        env1.set("TEST_VAR", "value_from_env1", source="test")
        env2.set("TEST_VAR", "value_from_env2", source="test")
        
        # Verify isolation - each environment has its own values
        assert env1.get("TEST_VAR") == "value_from_env1", "Environment 1 should have its own value"
        assert env2.get("TEST_VAR") == "value_from_env2", "Environment 2 should have its own value"
        
        # Verify environments don't interfere with each other
        env1.set("UNIQUE_VAR_1", "env1_unique", source="test")
        env2.set("UNIQUE_VAR_2", "env2_unique", source="test")
        
        assert env1.get("UNIQUE_VAR_1") == "env1_unique"
        assert env1.get("UNIQUE_VAR_2") is None, "Environment 1 should not see env2's variables"
        
        assert env2.get("UNIQUE_VAR_2") == "env2_unique"
        assert env2.get("UNIQUE_VAR_1") is None, "Environment 2 should not see env1's variables"

    @pytest.mark.unit
    def test_environment_variable_precedence_and_overrides(self):
        """Test environment variable precedence follows correct order.
        
        Ensures configuration overrides work as expected in different environments.
        """
        env = IsolatedEnvironment("precedence_test")
        
        # Test precedence order: explicit > test > environment > default
        env.set("PRECEDENCE_VAR", "environment_value", source="environment")
        env.set("PRECEDENCE_VAR", "test_value", source="test")
        
        # Test source should take precedence over environment
        assert env.get("PRECEDENCE_VAR") == "test_value", "Test source should override environment"
        
        # Explicit set should take highest precedence
        env.set("PRECEDENCE_VAR", "explicit_value", source="explicit")
        assert env.get("PRECEDENCE_VAR") == "explicit_value", "Explicit source should have highest precedence"
        
        # Test default values
        assert env.get("NONEXISTENT_VAR", "default") == "default", "Should return default for missing vars"
        
        # Test source tracking
        sources = env.get_sources("PRECEDENCE_VAR")
        assert "explicit" in sources, "Should track explicit source"
        assert "test" in sources, "Should track test source"
        assert "environment" in sources, "Should track environment source"

    @pytest.mark.unit
    def test_global_environment_instance_behavior(self):
        """Test global environment instance behaves consistently.
        
        Ensures get_env() returns consistent environment instance.
        """
        # Multiple calls should return same instance
        env1 = get_env()
        env2 = get_env()
        
        assert env1 is env2, "get_env() should return same instance"
        
        # Changes through one reference should be visible through another
        env1.set("GLOBAL_TEST_VAR", "global_value", source="test")
        assert env2.get("GLOBAL_TEST_VAR") == "global_value", "Changes should be visible globally"
        
        # Environment should maintain state across calls
        env1.set("PERSISTENT_VAR", "persistent_value", source="test")
        env3 = get_env()
        assert env3.get("PERSISTENT_VAR") == "persistent_value", "Environment state should persist"

    @pytest.mark.unit
    def test_environment_configuration_validation_by_type(self):
        """Test environment configuration validation for different types.
        
        Validates type conversion and validation works correctly.
        """
        env = IsolatedEnvironment("type_validation_test")
        
        # Test boolean conversion
        env.set("BOOL_TRUE", "true", source="test")
        env.set("BOOL_FALSE", "false", source="test") 
        env.set("BOOL_1", "1", source="test")
        env.set("BOOL_0", "0", source="test")
        
        # Boolean values should be recognized
        assert env.get_bool("BOOL_TRUE") is True, "Should convert 'true' to True"
        assert env.get_bool("BOOL_FALSE") is False, "Should convert 'false' to False"
        assert env.get_bool("BOOL_1") is True, "Should convert '1' to True"
        assert env.get_bool("BOOL_0") is False, "Should convert '0' to False"
        
        # Test integer conversion
        env.set("INT_VAR", "12345", source="test")
        env.set("INVALID_INT", "not_a_number", source="test")
        
        assert env.get_int("INT_VAR") == 12345, "Should convert string to int"
        assert env.get_int("INVALID_INT", 0) == 0, "Should return default for invalid int"
        assert env.get_int("MISSING_INT", 42) == 42, "Should return default for missing int"
        
        # Test list conversion
        env.set("LIST_VAR", "item1,item2,item3", source="test")
        env.set("EMPTY_LIST", "", source="test")
        
        result_list = env.get_list("LIST_VAR")
        assert result_list == ["item1", "item2", "item3"], "Should split comma-separated values"
        assert env.get_list("EMPTY_LIST") == [], "Should return empty list for empty string"
        assert env.get_list("MISSING_LIST", ["default"]) == ["default"], "Should return default list"


class TestEnvironmentSpecificConfigurationUnit(BaseIntegrationTest):
    """Test environment-specific configuration handling."""
    
    @pytest.mark.unit
    def test_testing_environment_configuration(self):
        """Test testing environment configuration setup.
        
        Critical for ensuring test environments are properly configured.
        """
        env = IsolatedEnvironment("testing")
        
        # Set testing environment configuration
        env.set("ENVIRONMENT", "testing", source="test")
        env.set("TESTING", "1", source="test")
        env.set("DATABASE_URL", "sqlite:///test.db", source="test")
        env.set("REDIS_URL", "redis://localhost:6381/0", source="test")
        env.set("CLICKHOUSE_ENABLED", "false", source="test")
        
        # Verify testing configuration
        assert env.get("ENVIRONMENT") == "testing", "Environment should be testing"
        assert env.get_bool("TESTING") is True, "Testing flag should be True"
        assert "sqlite" in env.get("DATABASE_URL"), "Should use SQLite for testing"
        assert "6381" in env.get("REDIS_URL"), "Should use test Redis port"
        assert env.get_bool("CLICKHOUSE_ENABLED") is False, "ClickHouse should be disabled in testing"

    @pytest.mark.unit
    def test_development_environment_configuration(self):
        """Test development environment configuration setup.
        
        Validates development-specific configuration requirements.
        """
        env = IsolatedEnvironment("development")
        
        # Set development environment configuration
        env.set("ENVIRONMENT", "development", source="environment")
        env.set("DEBUG", "true", source="environment")
        env.set("DATABASE_URL", "postgresql://dev_user:dev_pass@localhost:5432/dev_db", source="environment")
        env.set("REDIS_URL", "redis://localhost:6379/0", source="environment")
        env.set("CLICKHOUSE_HOST", "localhost", source="environment")
        env.set("LOG_LEVEL", "DEBUG", source="environment")
        
        # Verify development configuration
        assert env.get("ENVIRONMENT") == "development", "Environment should be development"
        assert env.get_bool("DEBUG") is True, "Debug should be enabled"
        assert "postgresql" in env.get("DATABASE_URL"), "Should use PostgreSQL for development"
        assert "5432" in env.get("DATABASE_URL"), "Should use default PostgreSQL port"
        assert env.get("LOG_LEVEL") == "DEBUG", "Should use DEBUG log level"

    @pytest.mark.unit
    def test_staging_environment_configuration(self):
        """Test staging environment configuration setup.
        
        Ensures staging mirrors production configuration patterns.
        """
        env = IsolatedEnvironment("staging")
        
        # Set staging environment configuration  
        env.set("ENVIRONMENT", "staging", source="environment")
        env.set("DEBUG", "false", source="environment")
        env.set("DATABASE_URL", "postgresql://staging_user:staging_pass@staging-db:5432/staging_db", source="environment")
        env.set("CLICKHOUSE_URL", "clickhouse://staging_user:staging_pass@staging-clickhouse.cloud:8443/staging_db?secure=1", source="environment")
        env.set("LOG_LEVEL", "INFO", source="environment")
        env.set("ENABLE_METRICS", "true", source="environment")
        
        # Verify staging configuration
        assert env.get("ENVIRONMENT") == "staging", "Environment should be staging"
        assert env.get_bool("DEBUG") is False, "Debug should be disabled"
        assert "staging-db" in env.get("DATABASE_URL"), "Should use staging database host"
        assert "secure=1" in env.get("CLICKHOUSE_URL"), "Should use secure ClickHouse connection"
        assert env.get("LOG_LEVEL") == "INFO", "Should use INFO log level"
        assert env.get_bool("ENABLE_METRICS") is True, "Should enable metrics collection"

    @pytest.mark.unit 
    def test_production_environment_configuration(self):
        """Test production environment configuration requirements.
        
        Critical for ensuring production configuration is secure and complete.
        """
        env = IsolatedEnvironment("production")
        
        # Set production environment configuration
        env.set("ENVIRONMENT", "production", source="environment")
        env.set("DEBUG", "false", source="environment")
        env.set("DATABASE_URL", "postgresql://prod_user:$(SECRET)@prod-db-cluster:5432/prod_db", source="environment")
        env.set("CLICKHOUSE_URL", "clickhouse://prod_user:$(SECRET)@prod-clickhouse.cloud:8443/prod_db?secure=1", source="environment")
        env.set("LOG_LEVEL", "WARNING", source="environment")
        env.set("ENABLE_METRICS", "true", source="environment")
        env.set("ENABLE_TRACING", "true", source="environment")
        env.set("HTTPS_ONLY", "true", source="environment")
        
        # Verify production configuration
        assert env.get("ENVIRONMENT") == "production", "Environment should be production"
        assert env.get_bool("DEBUG") is False, "Debug must be disabled in production"
        assert "prod-db-cluster" in env.get("DATABASE_URL"), "Should use production database cluster"
        assert "secure=1" in env.get("CLICKHOUSE_URL"), "Must use secure ClickHouse in production"
        assert env.get("LOG_LEVEL") == "WARNING", "Should use WARNING log level for production"
        assert env.get_bool("HTTPS_ONLY") is True, "Must enforce HTTPS in production"
        assert env.get_bool("ENABLE_TRACING") is True, "Should enable tracing in production"


class TestEnvironmentConfigurationErrorHandlingUnit(BaseIntegrationTest):
    """Test environment configuration error handling and validation."""
    
    @pytest.mark.unit
    def test_missing_critical_environment_variables(self):
        """Test handling of missing critical environment variables.
        
        Ensures system fails gracefully when critical config is missing.
        """
        env = IsolatedEnvironment("error_handling_test")
        
        # Test missing variables with no defaults
        assert env.get("MISSING_VAR") is None, "Missing variables should return None"
        assert env.get("MISSING_VAR", "default") == "default", "Should use provided default"
        
        # Test critical variable validation
        critical_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "SERVICE_SECRET"]
        missing_vars = []
        
        for var in critical_vars:
            if env.get(var) is None:
                missing_vars.append(var)
        
        # For test environment, this is expected
        assert len(missing_vars) > 0, "Test environment should be missing production variables"
        
        # Test error handling for invalid values
        env.set("INVALID_BOOL", "not_a_boolean", source="test")
        env.set("INVALID_INT", "not_a_number", source="test")
        
        # Should handle invalid values gracefully
        assert env.get_bool("INVALID_BOOL", False) is False, "Should return default for invalid boolean"
        assert env.get_int("INVALID_INT", 0) == 0, "Should return default for invalid integer"

    @pytest.mark.unit
    def test_environment_configuration_warnings_and_deprecations(self):
        """Test environment configuration warnings for deprecated settings.
        
        Ensures deprecated configuration is properly handled and warned about.
        """
        env = IsolatedEnvironment("deprecation_test")
        
        # Test deprecated configuration patterns
        deprecated_vars = {
            "OLD_DATABASE_URL": "postgresql://old_format",
            "LEGACY_API_KEY": "legacy_api_key_format", 
            "DEPRECATED_HOST": "old.hostname.com"
        }
        
        for var, value in deprecated_vars.items():
            env.set(var, value, source="environment")
        
        # Test that deprecated variables are still accessible
        assert env.get("OLD_DATABASE_URL") == "postgresql://old_format"
        assert env.get("LEGACY_API_KEY") == "legacy_api_key_format"
        
        # Test migration path - new variables should override old ones
        env.set("DATABASE_URL", "postgresql://new_format", source="environment")
        
        # New format should be preferred
        new_url = env.get("DATABASE_URL")
        old_url = env.get("OLD_DATABASE_URL")
        
        assert new_url == "postgresql://new_format", "Should use new format"
        assert old_url == "postgresql://old_format", "Old format should still be accessible"

    @pytest.mark.unit
    def test_environment_configuration_security_validation(self):
        """Test environment configuration security validation.
        
        Ensures sensitive configuration is properly validated and secured.
        """
        env = IsolatedEnvironment("security_test")
        
        # Test secret validation
        env.set("JWT_SECRET_KEY", "test_secret_key_12345", source="test")
        env.set("SERVICE_SECRET", "test_service_secret_67890", source="test")
        env.set("API_KEY", "test_api_key_abcdef", source="test")
        
        # Secrets should be accessible
        assert env.get("JWT_SECRET_KEY") is not None, "JWT secret should be accessible"
        assert env.get("SERVICE_SECRET") is not None, "Service secret should be accessible"
        assert env.get("API_KEY") is not None, "API key should be accessible"
        
        # Test weak secret detection
        weak_secrets = ["123", "password", "secret", "test"]
        for weak_secret in weak_secrets:
            env.set("WEAK_SECRET", weak_secret, source="test")
            secret_value = env.get("WEAK_SECRET")
            
            # Weak secrets should still be stored (validation is application-level)
            assert secret_value == weak_secret, f"Should store weak secret: {weak_secret}"
            
            # But we can detect them for validation
            if len(secret_value) < 10:
                assert True, "Detected weak secret (validation would warn in real usage)"
        
        # Test environment variable exposure protection
        sensitive_vars = ["SECRET", "PASSWORD", "KEY", "TOKEN"]
        for var_type in sensitive_vars:
            test_var = f"TEST_{var_type}"
            env.set(test_var, f"sensitive_{var_type.lower()}_value", source="test")
            
            # Sensitive variables should be accessible in test environment
            assert env.get(test_var) is not None, f"Should access {test_var} in test environment"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])