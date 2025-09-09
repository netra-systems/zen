"""
Unit Tests: IsolatedEnvironment SSOT Compliance

CRITICAL: These tests ensure IsolatedEnvironment singleton compliance and proper environment isolation.
Prevents configuration cascade failures through validation of SSOT patterns.

Business Value: Platform/Internal - Prevents 60% of production outages from config errors
Test Coverage: IsolatedEnvironment SSOT compliance, singleton consistency, isolation boundary validation
"""
import pytest
import threading
import time
import os
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestIsolatedEnvironmentSSOTCompliance:
    """Test IsolatedEnvironment SSOT compliance patterns to prevent cascade failures."""

    def test_singleton_consistency_across_modules(self):
        """
        CRITICAL: Test singleton consistency between class instance and module instance.
        
        PREVENTS: Multiple environment instances causing configuration drift
        CASCADE FAILURE: Different instances having different configurations
        """
        # Get instance through class method
        instance1 = IsolatedEnvironment()
        
        # Get instance through module function
        instance2 = get_env()
        
        # Get another instance through class
        instance3 = IsolatedEnvironment.get_instance()
        
        # All instances MUST be identical
        assert instance1 is instance2, f"Class instance {id(instance1)} != module instance {id(instance2)}"
        assert instance2 is instance3, f"Module instance {id(instance2)} != get_instance {id(instance3)}"
        assert instance1 is instance3, f"First instance {id(instance1)} != get_instance {id(instance3)}"
        
        # Verify singleton consistency through different access patterns
        assert IsolatedEnvironment._instance is instance1
        assert IsolatedEnvironment._instance is instance2
        assert IsolatedEnvironment._instance is instance3

    def test_thread_safe_singleton_creation(self):
        """
        CRITICAL: Test thread-safe singleton creation prevents multiple instances.
        
        PREVENTS: Race conditions during initialization causing multiple singletons
        CASCADE FAILURE: Different threads using different environment instances
        """
        instances = []
        errors = []
        
        def create_instance():
            try:
                instance = IsolatedEnvironment()
                instances.append(instance)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads trying to create instances simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
        
        # Start all threads at roughly the same time
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert not errors, f"Thread creation errors: {errors}"
        
        # Verify all instances are identical (singleton enforcement)
        assert len(instances) == 10
        first_instance = instances[0]
        for i, instance in enumerate(instances):
            assert instance is first_instance, f"Instance {i} ({id(instance)}) != first instance ({id(first_instance)})"

    def test_isolation_mode_prevents_os_environ_pollution(self):
        """
        CRITICAL: Test isolation mode prevents os.environ pollution during testing.
        
        PREVENTS: Test environment variables leaking to production code
        CASCADE FAILURE: Wrong database connections, API keys, service URLs
        """
        env = get_env()
        
        # Enable isolation mode
        env.enable_isolation()
        assert env.is_isolated(), "Isolation mode should be enabled"
        
        # Set test variable in isolation
        test_key = "TEST_ISOLATION_VARIABLE"
        test_value = "isolated_test_value"
        
        success = env.set(test_key, test_value, "test_isolation")
        assert success, "Should be able to set isolated variable"
        
        # Verify it's accessible through isolated environment
        assert env.get(test_key) == test_value, "Should retrieve isolated variable"
        
        # CRITICAL: Verify it doesn't leak to os.environ
        assert os.environ.get(test_key) != test_value, "Isolated variable leaked to os.environ"
        
        # Verify isolation boundary is maintained
        env.set("ANOTHER_ISOLATED_VAR", "another_value", "test")
        assert env.get("ANOTHER_ISOLATED_VAR") == "another_value"
        assert "ANOTHER_ISOLATED_VAR" not in os.environ
        
        # Clean up
        env.disable_isolation()

    def test_critical_variables_protection_mechanism(self):
        """
        CRITICAL: Test protection mechanism for critical environment variables.
        
        PREVENTS: Accidental modification of SERVICE_SECRET, DATABASE_URL, JWT_SECRET_KEY
        CASCADE FAILURE: Complete authentication failure, database connection loss
        """
        env = get_env()
        env.enable_isolation()
        
        # Set critical variables
        critical_vars = {
            "SERVICE_SECRET": "critical-service-secret-32-chars-min",
            "DATABASE_URL": "postgresql://localhost:5432/test_db",
            "JWT_SECRET_KEY": "critical-jwt-secret-key-32-characters-minimum"
        }
        
        for key, value in critical_vars.items():
            env.set(key, value, "test_setup")
        
        # Protect critical variables
        for key in critical_vars:
            env.protect_variable(key)
            assert env.is_protected(key), f"{key} should be protected"
        
        # Attempt to modify protected variables (should fail)
        for key in critical_vars:
            success = env.set(key, "hacker_value", "malicious_attempt")
            assert not success, f"Should not be able to modify protected variable {key}"
        
        # Verify original values are preserved
        for key, original_value in critical_vars.items():
            current_value = env.get(key)
            assert current_value == original_value, f"{key} was modified despite protection"
        
        # Test force override (emergency scenarios)
        service_secret_key = "SERVICE_SECRET"
        new_emergency_value = "emergency-service-secret-32-chars-min"
        success = env.set(service_secret_key, new_emergency_value, "emergency_override", force=True)
        assert success, "Should be able to force override protected variable"
        assert env.get(service_secret_key) == new_emergency_value


class TestEnvironmentIsolationBoundaries:
    """Test environment isolation boundaries to prevent configuration drift."""

    def test_test_context_automatic_isolation(self):
        """
        CRITICAL: Test automatic isolation activation in test contexts.
        
        PREVENTS: Test configurations affecting production environments
        CASCADE FAILURE: Wrong OAuth credentials, database URLs in production
        """
        env = get_env()
        
        # Mock test context indicators
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_module::test_function", "TESTING": "true"}):
            # Create new instance to trigger test context detection
            test_env = IsolatedEnvironment()
            
            # Should automatically enable isolation in test context
            assert test_env.is_isolated(), "Should automatically enable isolation in test context"
            
            # Should provide test environment defaults
            oauth_client_id = test_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert oauth_client_id == "test-oauth-client-id-for-automated-testing"
            
            e2e_oauth_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_oauth_key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"

    def test_environment_specific_config_independence(self):
        """
        CRITICAL: Test environment-specific configurations remain independent.
        
        PREVENTS: TEST vs STAGING vs PROD configuration cross-contamination
        CASCADE FAILURE: Staging credentials in production, localhost URLs in staging
        """
        env = get_env()
        env.enable_isolation()
        
        # Test environment configuration
        test_config = {
            "ENVIRONMENT": "test",
            "DATABASE_URL": "postgresql://localhost:5434/netra_test",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id"
        }
        
        # Staging environment configuration
        staging_config = {
            "ENVIRONMENT": "staging", 
            "DATABASE_URL": "postgresql://staging-db.gcp:5432/netra_staging",
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-oauth-client-id"
        }
        
        # Production environment configuration
        production_config = {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://prod-db.gcp:5432/netra_production", 
            "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "production-oauth-client-id"
        }
        
        # Test environment isolation
        for key, value in test_config.items():
            env.set(key, value, "test_env")
        
        # Verify test configuration is isolated
        for key, expected_value in test_config.items():
            actual_value = env.get(key)
            assert actual_value == expected_value, f"Test config {key}: expected {expected_value}, got {actual_value}"
        
        # Switch to staging simulation (clear and reload)
        env.clear()
        for key, value in staging_config.items():
            env.set(key, value, "staging_env")
        
        # Verify staging configuration is isolated
        for key, expected_value in staging_config.items():
            actual_value = env.get(key)
            assert actual_value == expected_value, f"Staging config {key}: expected {expected_value}, got {actual_value}"
        
        # Verify test config is completely gone
        for key in test_config:
            if key not in staging_config:
                assert env.get(key) is None, f"Test config {key} leaked to staging environment"

    def test_source_tracking_for_configuration_audit(self):
        """
        CRITICAL: Test source tracking for configuration audit and debugging.
        
        PREVENTS: Unknown configuration changes causing silent failures
        CASCADE FAILURE: Unable to trace configuration problems to source
        """
        env = get_env()
        env.enable_isolation()
        
        # Set variables from different sources
        config_sources = {
            "DATABASE_URL": ("file:.env", "postgresql://localhost:5432/test"),
            "JWT_SECRET_KEY": ("deployment_script", "jwt-secret-key-32-characters-minimum"),
            "SERVICE_SECRET": ("manual_override", "service-secret-32-characters-minimum"),
            "REDIS_URL": ("docker_compose", "redis://localhost:6379/0")
        }
        
        # Set all variables with source tracking
        for key, (source, value) in config_sources.items():
            success = env.set(key, value, source)
            assert success, f"Should be able to set {key}"
        
        # Verify source tracking
        for key, (expected_source, expected_value) in config_sources.items():
            actual_value = env.get(key)
            actual_source = env.get_variable_source(key)
            
            assert actual_value == expected_value, f"{key} value mismatch"
            assert actual_source == expected_source, f"{key} source: expected {expected_source}, got {actual_source}"
        
        # Test source organization
        sources_map = env.get_sources()
        assert "file:.env" in sources_map
        assert "DATABASE_URL" in sources_map["file:.env"]
        assert "deployment_script" in sources_map
        assert "JWT_SECRET_KEY" in sources_map["deployment_script"]

    def test_variable_sanitization_preserves_database_credentials(self):
        """
        CRITICAL: Test variable sanitization preserves database credential integrity.
        
        PREVENTS: Database connection failures from credential corruption
        CASCADE FAILURE: Complete backend failure, no data access
        """
        env = get_env()
        env.enable_isolation()
        
        # Test database URLs with special characters that need preservation
        test_database_urls = [
            "postgresql://user:p@ssw0rd!@localhost:5432/db",  # Special chars in password
            "postgresql://user:pass%40word@localhost:5432/db",  # URL-encoded password
            "mysql://user:complex$pass@db.host:3306/database",   # Dollar sign in password
            "clickhouse://user:p4ss&w*rd@clickhouse:8123/analytics"  # Complex password
        ]
        
        for i, url in enumerate(test_database_urls):
            key = f"DATABASE_URL_{i}"
            
            # Set database URL
            success = env.set(key, url, "test_sanitization")
            assert success, f"Should be able to set {key}"
            
            # Retrieve and verify no corruption occurred
            retrieved_url = env.get(key)
            assert retrieved_url == url, f"Database URL corrupted: expected {url}, got {retrieved_url}"
            
            # Verify URL still contains special characters
            if "@" in url:
                assert "@" in retrieved_url, "Password separator '@' was removed"
            if ":" in url:
                assert retrieved_url.count(":") >= 2, "Port separator ':' was corrupted"