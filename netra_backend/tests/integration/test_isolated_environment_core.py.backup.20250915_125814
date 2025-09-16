"""
Core IsolatedEnvironment Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Independence
- Business Goal: Ensure configuration isolation prevents cross-test pollution and service failures
- Value Impact: Prevents configuration drift that causes cascade failures across services
- Strategic Impact: Core platform reliability - config bugs cause 503 errors and auth failures

This test suite validates the most critical IsolatedEnvironment functionality:
1. Environment isolation between tests
2. Configuration loading and precedence
3. Multi-environment scenarios (dev/test/staging/prod)
4. Thread safety for multi-user scenarios
5. Sensitive value handling for security compliance

CRITICAL: These tests use REAL IsolatedEnvironment instances (no mocks) to validate
actual business scenarios that could break the platform if configuration fails.
"""

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

import pytest

from shared.isolated_environment import IsolatedEnvironment, get_env


class TestIsolatedEnvironmentCore:
    """
    Core integration tests for IsolatedEnvironment functionality.
    
    Business Value: Tests real configuration scenarios that prevent:
    - Cross-service configuration pollution (causes auth failures) 
    - Environment variable leaks between tests (causes flaky tests)
    - Configuration validation failures (causes startup crashes)
    """

    def setup_method(self, method=None):
        """Setup for each test method."""
        self.env = get_env()
        # Store original state for cleanup
        self._original_vars = set(self.env.get_all().keys())
        
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Clean up any variables we added during the test
        current_vars = set(self.env.get_all().keys())
        added_vars = current_vars - self._original_vars
        for var in added_vars:
            self.env.delete(var, source="test_cleanup")

    @pytest.mark.integration
    def test_environment_isolation_basic(self):
        """
        Test basic environment isolation functionality.
        
        Business Value: Prevents configuration leaks that cause service failures.
        """
        # Test 1: Set and retrieve variables
        test_vars = {
            "TEST_VAR_1": "test_value_1",
            "TEST_VAR_2": "test_value_2",
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test"
        }
        
        for key, value in test_vars.items():
            result = self.env.set(key, value, source="isolation_test")
            assert result == True, f"Failed to set {key}"
            
        # Verify all variables are set correctly
        for key, expected_value in test_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Variable {key}: expected '{expected_value}', got '{actual_value}'"
            )
        
        # Test 2: Delete variables
        self.env.delete("TEST_VAR_1", source="isolation_test")
        assert self.env.get("TEST_VAR_1") is None, "Variable should be deleted"
        assert self.env.get("TEST_VAR_2") == "test_value_2", "Other variables should remain"

    @pytest.mark.integration  
    def test_environment_detection(self):
        """
        Test environment detection for different configurations.
        
        Business Value: Ensures correct environment-specific behavior.
        """
        test_cases = [
            ("development", "development"),
            ("test", "test"),
            ("testing", "test"), 
            ("staging", "staging"),
            ("production", "production"),
            ("", "development"),  # Default
        ]
        
        original_env = self.env.get("ENVIRONMENT")
        
        try:
            for input_env, expected_env in test_cases:
                if input_env:
                    self.env.set("ENVIRONMENT", input_env, source="env_detection_test")
                else:
                    if self.env.exists("ENVIRONMENT"):
                        self.env.delete("ENVIRONMENT", source="env_detection_test")
                
                detected_env = self.env.get_environment_name()
                assert detected_env == expected_env, (
                    f"Environment detection failed: input '{input_env}' -> "
                    f"expected '{expected_env}', got '{detected_env}'"
                )
                
                # Test boolean methods
                assert self.env.is_development() == (expected_env == "development")
                assert self.env.is_test() == (expected_env == "test")
                assert self.env.is_staging() == (expected_env == "staging")
                assert self.env.is_production() == (expected_env == "production")
                
        finally:
            # Restore original environment
            if original_env:
                self.env.set("ENVIRONMENT", original_env, source="env_detection_restore")

    @pytest.mark.integration
    def test_file_loading_with_precedence(self):
        """
        Test configuration loading from files with proper precedence.
        
        Business Value: Ensures configuration precedence prevents wrong credentials.
        """
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_content = """
DATABASE_URL=postgresql://file_user:file_pass@localhost:5432/file_db
AUTH_SERVICE_URL=http://file-auth:8081
FILE_ONLY_VAR=file_value
            """.strip()
            env_file.write(env_content)
            env_file_path = env_file.name

        try:
            # Load from file
            loaded_count, errors = self.env.load_from_file(env_file_path, override_existing=True)
            assert loaded_count >= 3, f"Expected at least 3 vars loaded, got {loaded_count}"
            assert len(errors) == 0, f"Unexpected errors: {errors}"
            
            # Verify file variables are loaded
            assert self.env.get("DATABASE_URL") == "postgresql://file_user:file_pass@localhost:5432/file_db"
            assert self.env.get("AUTH_SERVICE_URL") == "http://file-auth:8081"
            assert self.env.get("FILE_ONLY_VAR") == "file_value"
            
            # Test environment variable override
            self.env.set("DATABASE_URL", "postgresql://override:pass@localhost:5434/override", 
                        source="env_override")
            
            # Environment variable should take precedence
            assert self.env.get("DATABASE_URL") == "postgresql://override:pass@localhost:5434/override"
            assert self.env.get("FILE_ONLY_VAR") == "file_value"  # File var should remain
            
        finally:
            os.unlink(env_file_path)

    @pytest.mark.integration
    def test_sensitive_value_handling(self):
        """
        Test handling of sensitive configuration values.
        
        Business Value: Prevents security leaks in logs and debug output.
        """
        sensitive_vars = {
            "DATABASE_PASSWORD": "super_secret_password_123",
            "JWT_SECRET_KEY": "jwt_secret_key_456",
            "OAUTH_CLIENT_SECRET": "oauth_secret_789",
            "API_KEY": "api_key_abc123"
        }
        
        non_sensitive_vars = {
            "DATABASE_HOST": "localhost",
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "ENVIRONMENT": "test"
        }
        
        # Set all variables
        for key, value in {**sensitive_vars, **non_sensitive_vars}.items():
            self.env.set(key, value, source="sensitive_test")
        
        # Verify all variables are set correctly (functionality not affected)
        for key, expected_value in sensitive_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, f"Sensitive var {key} not set correctly"
            
        for key, expected_value in non_sensitive_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, f"Non-sensitive var {key} not set correctly"
        
        # Test complex database URL handling (with valid characters)
        complex_db_url = "postgresql://user:secure_p@ssw0rd@localhost:5432/db?sslmode=require"
        self.env.set("COMPLEX_DB_URL", complex_db_url, source="complex_test")
        retrieved_url = self.env.get("COMPLEX_DB_URL")
        assert retrieved_url == complex_db_url, (
            f"Complex database URL not preserved: expected '{complex_db_url}', got '{retrieved_url}'"
        )

    @pytest.mark.integration
    def test_thread_safety_basic(self):
        """
        Test basic thread safety of IsolatedEnvironment.
        
        Business Value: Ensures multi-user scenarios work without race conditions.
        """
        num_threads = 5
        operations_per_thread = 10
        results = {}
        
        def thread_worker(thread_id: int):
            """Worker function for thread safety testing."""
            thread_results = {"operations": 0, "errors": []}
            env = get_env()  # Should get same singleton
            
            try:
                for i in range(operations_per_thread):
                    var_key = f"THREAD_{thread_id}_VAR_{i}"
                    var_value = f"thread_{thread_id}_value_{i}"
                    
                    # Set and immediately read back
                    env.set(var_key, var_value, source=f"thread_{thread_id}")
                    retrieved = env.get(var_key)
                    
                    if retrieved != var_value:
                        thread_results["errors"].append(
                            f"Mismatch: set '{var_value}', got '{retrieved}'"
                        )
                    else:
                        thread_results["operations"] += 1
                        
            except Exception as e:
                thread_results["errors"].append(f"Exception: {e}")
                
            results[thread_id] = thread_results
        
        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout per thread
        
        # Analyze results
        total_operations = sum(r["operations"] for r in results.values())
        all_errors = []
        for r in results.values():
            all_errors.extend(r["errors"])
        
        assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
        assert total_operations > 0, "No operations completed successfully"
        assert len(all_errors) == 0, f"Thread safety errors: {all_errors}"

    @pytest.mark.integration
    def test_subprocess_environment(self):
        """
        Test subprocess environment generation.
        
        Business Value: Ensures external tools receive correct configuration.
        """
        # Set test environment
        test_env = {
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test",
            "AUTH_SERVICE_URL": "http://test-auth:8081",
            "CUSTOM_VAR": "custom_value"
        }
        
        for key, value in test_env.items():
            self.env.set(key, value, source="subprocess_test")
        
        # Get subprocess environment
        subprocess_env = self.env.get_subprocess_env()
        
        # Verify test variables are included
        for key, expected_value in test_env.items():
            assert key in subprocess_env, f"Test var {key} missing from subprocess env"
            assert subprocess_env[key] == expected_value, (
                f"Test var {key} wrong in subprocess env: expected '{expected_value}', "
                f"got '{subprocess_env[key]}'"
            )
        
        # Test with additional variables
        additional_vars = {"EXTRA_VAR": "extra_value"}
        subprocess_env_with_extra = self.env.get_subprocess_env(additional_vars)
        
        # Verify additional variables are included
        assert "EXTRA_VAR" in subprocess_env_with_extra
        assert subprocess_env_with_extra["EXTRA_VAR"] == "extra_value"
        
        # Verify original variables are still there
        for key, expected_value in test_env.items():
            assert subprocess_env_with_extra[key] == expected_value

    @pytest.mark.integration
    def test_configuration_validation(self):
        """
        Test configuration validation functionality.
        
        Business Value: Prevents startup failures due to missing required config.
        """
        # Clear any existing required variables
        required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]
        original_values = {}
        for var in required_vars:
            original_values[var] = self.env.get(var)
            if self.env.exists(var):
                self.env.delete(var, source="validation_test_cleanup")
        
        try:
            # Test 1: Missing required variables should fail validation
            validation_result = self.env.validate_all()
            assert validation_result.is_valid == False, "Validation should fail with missing vars"
            assert len(validation_result.errors) > 0, "Should have validation errors"
            
            # Test 2: Set required variables and validate again
            valid_config = {
                "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
                "JWT_SECRET_KEY": "valid_jwt_secret_key_123",
                "SECRET_KEY": "valid_secret_key_456"
            }
            
            for key, value in valid_config.items():
                self.env.set(key, value, source="validation_test")
            
            validation_result = self.env.validate_all()
            assert validation_result.is_valid == True, (
                f"Validation should pass with all required vars: {validation_result.errors}"
            )
            assert len(validation_result.errors) == 0, (
                f"Should have no errors: {validation_result.errors}"
            )
            
        finally:
            # Restore original values
            for var, original_value in original_values.items():
                if original_value is not None:
                    self.env.set(var, original_value, source="validation_test_restore")

    @pytest.mark.integration
    def test_singleton_behavior(self):
        """
        Test that IsolatedEnvironment maintains singleton behavior.
        
        Business Value: Ensures consistent configuration across the application.
        """
        # Get multiple references
        env1 = get_env()
        env2 = get_env()
        env3 = IsolatedEnvironment()
        
        # All should be the same instance
        assert env1 is env2, "get_env() should return same instance"
        assert env1 is env3, "IsolatedEnvironment() should return same instance"
        assert env2 is env3, "All references should be identical"
        
        # Test that changes are visible across all references
        env1.set("SINGLETON_TEST", "singleton_value", source="singleton_test")
        
        assert env2.get("SINGLETON_TEST") == "singleton_value"
        assert env3.get("SINGLETON_TEST") == "singleton_value"
        
        # Cleanup
        env1.delete("SINGLETON_TEST", source="singleton_cleanup")

    @pytest.mark.integration
    def test_multi_environment_isolation(self):
        """
        Test isolation between different environment configurations.
        
        Business Value: Prevents environment configuration leaks.
        """
        # Test development environment
        dev_config = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://dev:dev@localhost:5432/dev",
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "DEBUG": "true"
        }
        
        for key, value in dev_config.items():
            self.env.set(key, value, source="dev_test")
            
        # Verify development environment
        assert self.env.get_environment_name() == "development"
        assert self.env.is_development() == True
        
        for key, expected in dev_config.items():
            assert self.env.get(key) == expected
        
        # Clear and switch to staging
        for key in dev_config.keys():
            self.env.delete(key, source="dev_to_staging")
        
        staging_config = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://staging:staging@staging-db:5432/staging",
            "AUTH_SERVICE_URL": "https://auth.staging.example.com",
            "DEBUG": "false"
        }
        
        for key, value in staging_config.items():
            self.env.set(key, value, source="staging_test")
        
        # Verify staging environment
        assert self.env.get_environment_name() == "staging"
        assert self.env.is_staging() == True
        assert self.env.is_development() == False
        
        # Verify no dev config leaked
        for key, dev_value in dev_config.items():
            actual_value = self.env.get(key)
            if key in staging_config:
                assert actual_value == staging_config[key], (
                    f"Staging value not set: {key}"
                )
            else:
                assert actual_value != dev_value, (
                    f"Dev value leaked to staging: {key}={dev_value}"
                )


# === LEGACY COMPATIBILITY TESTS ===

class TestIsolatedEnvironmentLegacyCompatibility:
    """Test backwards compatibility with legacy environment patterns."""

    def setup_method(self):
        self.env = get_env()
        self._test_vars = set()
    
    def teardown_method(self):
        # Clean up test variables
        for var in self._test_vars:
            if self.env.exists(var):
                self.env.delete(var, source="legacy_test_cleanup")

    @pytest.mark.integration
    def test_legacy_convenience_functions(self):
        """Test legacy convenience functions still work."""
        from shared.isolated_environment import setenv, getenv, delenv
        
        # Track for cleanup
        self._test_vars.add("LEGACY_TEST_VAR")
        
        # Test setenv/getenv
        result = setenv("LEGACY_TEST_VAR", "legacy_value", source="legacy_test")
        assert result == True, "setenv should return True"
        
        value = getenv("LEGACY_TEST_VAR")
        assert value == "legacy_value", f"getenv failed: expected 'legacy_value', got '{value}'"
        
        # Test delenv
        delete_result = delenv("LEGACY_TEST_VAR")
        assert delete_result == True, "delenv should return True"
        
        value_after_delete = getenv("LEGACY_TEST_VAR")
        assert value_after_delete is None, "Variable should be None after deletion"
        
        # Remove from tracking since it's deleted
        self._test_vars.remove("LEGACY_TEST_VAR")

    @pytest.mark.integration
    def test_legacy_classes(self):
        """Test legacy compatibility classes."""
        from shared.isolated_environment import SecretLoader, EnvironmentValidator
        
        # Test SecretLoader
        loader = SecretLoader()
        assert loader.env_manager is not None
        assert loader.load_secrets() == True
        
        # Test setting and getting secrets
        self._test_vars.add("TEST_SECRET")
        result = loader.set_secret("TEST_SECRET", "secret_value")
        assert result == True
        
        retrieved = loader.get_secret("TEST_SECRET")
        assert retrieved == "secret_value"
        
        # Test EnvironmentValidator
        validator = EnvironmentValidator()
        assert hasattr(validator, 'validate_all')
        assert hasattr(validator, 'env')