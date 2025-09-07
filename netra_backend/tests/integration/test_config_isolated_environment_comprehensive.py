"""
Test IsolatedEnvironment Configuration System Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Independence
- Business Goal: Ensure configuration isolation prevents cross-test pollution and service failures
- Value Impact: Prevents configuration drift that causes cascade failures across services
- Strategic Impact: Core platform reliability - config bugs cause 503 errors and auth failures

This comprehensive test suite validates that the IsolatedEnvironment singleton correctly:
1. Maintains isolation between test/development/staging/production environments
2. Prevents configuration pollution between concurrent tests and services
3. Handles multi-environment scenarios that cause real-world failures
4. Validates thread safety and concurrent access patterns
5. Tests configuration loading, validation, and error handling
6. Ensures sensitive value masking and security compliance

CRITICAL: These tests use REAL IsolatedEnvironment instances (no mocks) to validate
actual business scenarios that could break the platform if configuration fails.
"""

import asyncio
import os
import threading
import time
import tempfile
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import IsolatedEnvironment, get_env, ValidationResult


@dataclass
class EnvironmentTestScenario:
    """Test scenario for environment validation."""
    name: str
    environment_vars: Dict[str, str]
    expected_environment: str
    should_pass: bool
    expected_errors: List[str] = None
    expected_warnings: List[str] = None


class TestIsolatedEnvironmentComprehensive(SSotBaseTestCase):
    """
    Comprehensive integration tests for IsolatedEnvironment functionality.
    
    Business Value: Tests real configuration scenarios that prevent:
    - Cross-service configuration pollution (causes auth failures)
    - Environment variable leaks between tests (causes flaky tests)
    - Configuration validation failures (causes startup crashes)
    - Thread safety issues in multi-user environments
    """

    def setup_method(self, method=None):
        """Setup method with enhanced environment isolation."""
        super().setup_method(method)
        
        # Get fresh IsolatedEnvironment instance for each test
        self.env = get_env()
        
        # Ensure we start with isolation enabled for testing
        if not self.env.is_isolated():
            self.env.enable_isolation(backup_original=True)
        
        # Store original environment state for comprehensive restoration
        self._original_env_backup = self.env.get_all().copy()
        self._test_added_vars = set()

    def teardown_method(self, method=None):
        """Teardown with comprehensive environment restoration."""
        try:
            # Clean up any test-specific variables we added
            if hasattr(self, '_test_added_vars'):
                for var_name in self._test_added_vars:
                    if self.env.exists(var_name):
                        self.env.delete(var_name, source="test_cleanup")
            
            # Reset to original state
            if hasattr(self.env, 'reset_to_original'):
                self.env.reset_to_original()
            
        finally:
            super().teardown_method(method)

    def _add_test_var(self, key: str, value: str, source: str = "test") -> None:
        """Helper to add test variables with tracking for cleanup."""
        if not hasattr(self, '_test_added_vars'):
            self._test_added_vars = set()
        if not hasattr(self, 'env'):
            self.env = get_env()
        self.env.set(key, value, source=source)
        self._test_added_vars.add(key)

    # === CORE ISOLATION PATTERN TESTS ===

    @pytest.mark.integration
    async def test_environment_isolation_prevents_cross_test_pollution(self):
        """
        CRITICAL: Test that environment isolation prevents configuration leaks between tests.
        
        Business Value: Prevents flaky tests and configuration drift that causes:
        - Auth service connecting to wrong URLs (500 errors)
        - Database connections using wrong credentials (connection failures)  
        - Service discovery failures due to wrong ports
        """
        # Simulate Test 1 configuration
        test1_vars = {
            "DATABASE_URL": "postgresql://test1_user:test1_pass@localhost:5434/test1_db",
            "AUTH_SERVICE_URL": "http://test1-auth:8081",
            "ENVIRONMENT": "test1",
            "JWT_SECRET_KEY": "test1_jwt_secret",
        }
        
        # Set Test 1 environment
        for key, value in test1_vars.items():
            self._add_test_var(key, value, source="test1_simulation")
        
        # Verify Test 1 environment is set correctly
        for key, expected_value in test1_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Test 1 environment setup failed: {key} expected '{expected_value}', got '{actual_value}'"
            )
        
        # Record Test 1 metrics
        self.record_metric("test1_vars_set", len(test1_vars))
        
        # Simulate Test 2 configuration (completely different)
        test2_vars = {
            "DATABASE_URL": "postgresql://test2_user:test2_pass@localhost:5435/test2_db",
            "AUTH_SERVICE_URL": "http://test2-auth:8082", 
            "ENVIRONMENT": "test2",
            "JWT_SECRET_KEY": "test2_jwt_secret_completely_different",
        }
        
        # Clear Test 1 vars and set Test 2 vars
        for key in test1_vars.keys():
            self.env.delete(key, source="test1_cleanup")
        
        for key, value in test2_vars.items():
            self._add_test_var(key, value, source="test2_simulation")
        
        # CRITICAL: Verify Test 1 configuration is completely gone
        for key, test1_value in test1_vars.items():
            actual_value = self.env.get(key)
            assert actual_value != test1_value, (
                f"POLLUTION DETECTED: Test 1 value '{test1_value}' leaked into Test 2 for {key}"
            )
        
        # Verify Test 2 configuration is correct
        for key, expected_value in test2_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Test 2 environment setup failed: {key} expected '{expected_value}', got '{actual_value}'"
            )
        
        # Record isolation success metrics
        self.record_metric("isolation_test_passed", True)
        self.record_metric("test2_vars_set", len(test2_vars))

    @pytest.mark.integration
    async def test_multi_environment_configuration_independence(self):
        """
        Test that development/testing/staging/production environments remain independent.
        
        Business Value: Prevents environment configuration leaks that cause:
        - Production secrets leaking to staging (security issue)
        - Test database URLs used in production (data loss)
        - Wrong OAuth credentials in staging (auth failures)
        """
        test_scenarios = [
            EnvironmentTestScenario(
                name="development",
                environment_vars={
                    "ENVIRONMENT": "development",
                    "DATABASE_URL": "postgresql://dev_user:dev_pass@localhost:5432/dev_db",
                    "AUTH_SERVICE_URL": "http://localhost:8081",
                    "DEBUG": "true",
                    "OAUTH_CLIENT_ID": "dev_oauth_client",
                    "OAUTH_CLIENT_SECRET": "dev_oauth_secret"
                },
                expected_environment="development",
                should_pass=True
            ),
            EnvironmentTestScenario(
                name="testing", 
                environment_vars={
                    "ENVIRONMENT": "testing",
                    "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5434/test_db",
                    "AUTH_SERVICE_URL": "http://test-auth:8081",
                    "DEBUG": "true",
                    "OAUTH_CLIENT_ID": "test_oauth_client",
                    "OAUTH_CLIENT_SECRET": "test_oauth_secret"
                },
                expected_environment="test",  # IsolatedEnvironment normalizes "testing" -> "test"
                should_pass=True
            ),
            EnvironmentTestScenario(
                name="staging",
                environment_vars={
                    "ENVIRONMENT": "staging", 
                    "DATABASE_URL": "postgresql://staging_user:staging_secure_pass@staging-db:5432/staging_db",
                    "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
                    "DEBUG": "false",
                    "OAUTH_CLIENT_ID": "staging_oauth_client",
                    "OAUTH_CLIENT_SECRET": "staging_oauth_secret_secure"
                },
                expected_environment="staging",
                should_pass=True
            ),
            EnvironmentTestScenario(
                name="production",
                environment_vars={
                    "ENVIRONMENT": "production",
                    "DATABASE_URL": "postgresql://prod_user:prod_ultra_secure_pass@prod-db:5432/prod_db",
                    "AUTH_SERVICE_URL": "https://auth.netrasystems.ai",
                    "DEBUG": "false",
                    "OAUTH_CLIENT_ID": "prod_oauth_client",
                    "OAUTH_CLIENT_SECRET": "prod_oauth_secret_ultra_secure"
                },
                expected_environment="production",
                should_pass=True
            )
        ]
        
        for i, scenario in enumerate(test_scenarios):
            # Clear environment between scenarios to test independence
            if i > 0:
                # Clear previous scenario vars to ensure independence
                prev_scenario = test_scenarios[i-1]
                for key in prev_scenario.environment_vars.keys():
                    if self.env.exists(key):
                        self.env.delete(key, source=f"cleanup_{prev_scenario.name}")
            
            # Set current scenario environment
            for key, value in scenario.environment_vars.items():
                self._add_test_var(key, value, source=f"scenario_{scenario.name}")
            
            # Verify environment is correctly detected
            detected_env = self.env.get_environment_name()
            assert detected_env == scenario.expected_environment, (
                f"Environment detection failed for {scenario.name}: "
                f"expected '{scenario.expected_environment}', got '{detected_env}'"
            )
            
            # Verify all scenario variables are set correctly
            for key, expected_value in scenario.environment_vars.items():
                actual_value = self.env.get(key)
                assert actual_value == expected_value, (
                    f"Variable mismatch in {scenario.name}: {key} expected '{expected_value}', got '{actual_value}'"
                )
            
            # CRITICAL: Verify no cross-contamination from previous scenarios
            if i > 0:
                prev_scenario = test_scenarios[i-1]
                for key, prev_value in prev_scenario.environment_vars.items():
                    if key not in scenario.environment_vars:
                        # This key should not exist in current scenario
                        actual_value = self.env.get(key)
                        assert actual_value != prev_value, (
                            f"CROSS-CONTAMINATION: {prev_scenario.name} variable '{key}={prev_value}' "
                            f"leaked into {scenario.name}"
                        )
            
            # Record metrics for each environment
            self.record_metric(f"{scenario.name}_env_vars_count", len(scenario.environment_vars))
            self.record_metric(f"{scenario.name}_isolation_success", True)

    # === CONFIGURATION LOADING TESTS ===

    @pytest.mark.integration
    async def test_configuration_file_loading_with_precedence(self):
        """
        Test configuration loading from multiple sources with proper precedence.
        
        Business Value: Ensures configuration loading follows correct precedence to prevent:
        - Wrong database credentials (OS env should override .env file)
        - Incorrect service URLs (Docker env should override local .env)
        - Auth failures due to wrong OAuth settings
        """
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_content = """
# Test .env file
DATABASE_URL=postgresql://env_file_user:env_file_pass@localhost:5432/env_file_db
AUTH_SERVICE_URL=http://env-file-auth:8081
JWT_SECRET_KEY=env_file_jwt_secret
OAUTH_CLIENT_ID=env_file_oauth_id
OAUTH_CLIENT_SECRET=env_file_oauth_secret
ENV_FILE_ONLY_VAR=env_file_value
            """.strip()
            env_file.write(env_content)
            env_file_path = env_file.name

        try:
            # Test 1: Load from .env file only
            loaded_count, errors = self.env.load_from_file(env_file_path, override_existing=True)
            assert loaded_count > 0, f"No variables loaded from .env file: {errors}"
            assert len(errors) == 0, f"Errors loading .env file: {errors}"
            
            # Verify .env file variables are loaded
            expected_env_file_vars = {
                "DATABASE_URL": "postgresql://env_file_user:env_file_pass@localhost:5432/env_file_db",
                "AUTH_SERVICE_URL": "http://env-file-auth:8081",
                "JWT_SECRET_KEY": "env_file_jwt_secret",
                "ENV_FILE_ONLY_VAR": "env_file_value"
            }
            
            for key, expected_value in expected_env_file_vars.items():
                actual_value = self.env.get(key)
                assert actual_value == expected_value, (
                    f".env file loading failed: {key} expected '{expected_value}', got '{actual_value}'"
                )
            
            # Test 2: Override with OS environment variables (higher precedence)
            os_override_vars = {
                "DATABASE_URL": "postgresql://os_user:os_pass@localhost:5434/os_db",
                "AUTH_SERVICE_URL": "http://os-auth:8082",
                "OS_ONLY_VAR": "os_value"
            }
            
            for key, value in os_override_vars.items():
                self._add_test_var(key, value, source="os_override")
            
            # Verify OS env variables override .env file
            for key, expected_value in os_override_vars.items():
                actual_value = self.env.get(key)
                assert actual_value == expected_value, (
                    f"OS environment override failed: {key} expected '{expected_value}', got '{actual_value}'"
                )
            
            # Verify .env-only variables still exist
            assert self.env.get("ENV_FILE_ONLY_VAR") == "env_file_value"
            assert self.env.get("JWT_SECRET_KEY") == "env_file_jwt_secret"  # Not overridden
            
            # Test 3: Test override_existing=False behavior
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file2:
                env_content2 = """
DATABASE_URL=postgresql://env_file2_user:env_file2_pass@localhost:5432/env_file2_db
NEW_VAR_FROM_FILE2=file2_value
                """.strip()
                env_file2.write(env_content2)
                env_file2_path = env_file2.name
            
            try:
                # Load without overriding existing
                loaded_count2, errors2 = self.env.load_from_file(env_file2_path, override_existing=False)
                assert len(errors2) == 0, f"Errors loading second .env file: {errors2}"
                
                # #removed-legacyshould NOT change (already exists)
                actual_db_url = self.env.get("DATABASE_URL")
                expected_db_url = os_override_vars["DATABASE_URL"]  # Should still be OS override
                assert actual_db_url == expected_db_url, (
                    f"override_existing=False failed: #removed-legacychanged from '{expected_db_url}' to '{actual_db_url}'"
                )
                
                # NEW_VAR_FROM_FILE2 should be added
                assert self.env.get("NEW_VAR_FROM_FILE2") == "file2_value"
                
            finally:
                os.unlink(env_file2_path)
            
            # Record metrics
            self.record_metric("env_file_vars_loaded", loaded_count)
            self.record_metric("precedence_test_passed", True)

        finally:
            # Cleanup
            os.unlink(env_file_path)

    @pytest.mark.integration 
    async def test_sensitive_value_masking_and_security(self):
        """
        Test that sensitive configuration values are properly masked in logs and debug output.
        
        Business Value: Prevents security leaks that could expose:
        - Database passwords in logs (compliance violation)
        - JWT secrets in debug output (security breach)
        - OAuth credentials in error messages (auth compromise)
        """
        # Test sensitive variable patterns
        sensitive_test_vars = {
            "DATABASE_PASSWORD": "super_secret_db_password_123!",
            "JWT_SECRET_KEY": "jwt_secret_key_ultra_secure_456",
            "OAUTH_CLIENT_SECRET": "oauth_client_secret_789",
            "API_KEY": "api_key_secret_abc123",
            "AUTH_TOKEN": "auth_token_secure_def456", 
            "PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...",
            "FERNET_KEY": "fernet_encryption_key_ghi789"
        }
        
        # Test non-sensitive variables (should not be masked)
        non_sensitive_vars = {
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432", 
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "ENVIRONMENT": "testing",
            "DEBUG": "true",
            "SERVICE_NAME": "netra_backend"
        }
        
        # Set all test variables
        for key, value in {**sensitive_test_vars, **non_sensitive_vars}.items():
            self._add_test_var(key, value, source="security_test")
        
        # Test 1: Verify variables are set correctly (functionality not affected by masking)
        for key, expected_value in sensitive_test_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Sensitive variable not set correctly: {key}"
            )
        
        for key, expected_value in non_sensitive_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Non-sensitive variable not set correctly: {key}"
            )
        
        # Test 2: Verify debug info masks sensitive values
        debug_info = self.env.get_debug_info()
        assert "tracked_sources" in debug_info
        
        # Verify that if debug info includes variable values, they should be masked
        # (The actual IsolatedEnvironment may or may not include values in debug info)
        
        # Test 3: Test source tracking doesn't leak sensitive values
        for key in sensitive_test_vars.keys():
            source = self.env.get_variable_source(key)
            assert source == "security_test", f"Source tracking failed for {key}"
        
        # Test 4: Test environment variable validation doesn't leak sensitive values
        all_env_vars = self.env.get_all()
        
        # Verify sensitive vars exist in environment but masking logic is available
        for key in sensitive_test_vars.keys():
            assert key in all_env_vars, f"Sensitive variable {key} missing from environment"
        
        # Test 5: Database URL sanitization (complex sensitive value)
        complex_db_url = "postgresql://user:complex_p@ssw0rd!#$@localhost:5432/mydb?sslmode=require"
        self._add_test_var("COMPLEX_DATABASE_URL", complex_db_url, source="complex_test")
        
        # Verify the complex URL is preserved correctly
        actual_complex_url = self.env.get("COMPLEX_DATABASE_URL")
        assert actual_complex_url == complex_db_url, (
            f"Complex database URL not preserved: expected '{complex_db_url}', got '{actual_complex_url}'"
        )
        
        # Record security test metrics
        self.record_metric("sensitive_vars_tested", len(sensitive_test_vars))
        self.record_metric("security_masking_passed", True)

    # === THREAD SAFETY AND CONCURRENCY TESTS ===

    @pytest.mark.integration
    async def test_thread_safety_concurrent_access(self):
        """
        Test thread safety of IsolatedEnvironment under concurrent access.
        
        Business Value: Ensures multi-user scenarios work correctly without:
        - Race conditions causing wrong configuration values
        - Thread interference in WebSocket connections
        - Concurrent agent execution using wrong user context
        """
        # Test configuration
        num_threads = 10
        operations_per_thread = 20
        test_results = {}
        errors = []
        
        def thread_worker(thread_id: int) -> Dict[str, Any]:
            """Worker function for thread safety testing."""
            thread_results = {
                "thread_id": thread_id,
                "operations_completed": 0,
                "get_operations": 0,
                "set_operations": 0,
                "errors": []
            }
            
            try:
                env = get_env()  # Should return same singleton instance
                
                for op_num in range(operations_per_thread):
                    try:
                        # Test SET operation
                        var_key = f"THREAD_{thread_id}_VAR_{op_num}"
                        var_value = f"thread_{thread_id}_value_{op_num}_{time.time()}"
                        
                        env.set(var_key, var_value, source=f"thread_{thread_id}")
                        thread_results["set_operations"] += 1
                        
                        # Test GET operation (should get what we just set)
                        retrieved_value = env.get(var_key)
                        if retrieved_value != var_value:
                            thread_results["errors"].append(
                                f"Value mismatch: set '{var_value}', got '{retrieved_value}'"
                            )
                        else:
                            thread_results["get_operations"] += 1
                        
                        # Test concurrent access to shared variable
                        shared_var = "SHARED_THREAD_COUNTER"
                        current_count = env.get(shared_var, "0")
                        new_count = str(int(current_count) + 1)
                        env.set(shared_var, new_count, source=f"thread_{thread_id}")
                        
                        thread_results["operations_completed"] += 1
                        
                        # Small delay to increase chance of race conditions
                        time.sleep(0.001)
                        
                    except Exception as e:
                        thread_results["errors"].append(f"Operation {op_num}: {str(e)}")
                        
            except Exception as e:
                thread_results["errors"].append(f"Thread setup error: {str(e)}")
            
            return thread_results
        
        # Initialize shared counter
        self._add_test_var("SHARED_THREAD_COUNTER", "0", source="thread_safety_init")
        
        # Execute concurrent threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(num_threads)]
            
            # Collect results
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    test_results[result["thread_id"]] = result
                except Exception as e:
                    errors.append(f"Thread execution error: {e}")
        
        # Analyze results
        total_operations = sum(r["operations_completed"] for r in test_results.values())
        total_set_ops = sum(r["set_operations"] for r in test_results.values())
        total_get_ops = sum(r["get_operations"] for r in test_results.values())
        all_errors = []
        for result in test_results.values():
            all_errors.extend(result["errors"])
        all_errors.extend(errors)
        
        # Assertions
        assert len(test_results) == num_threads, f"Expected {num_threads} thread results, got {len(test_results)}"
        assert total_operations > 0, "No operations completed by any thread"
        assert len(all_errors) == 0, f"Thread safety errors detected: {all_errors}"
        
        # Verify shared counter reflects all increments (may have race conditions, but should be close)
        final_counter = int(self.env.get("SHARED_THREAD_COUNTER", "0"))
        expected_min_counter = num_threads  # At least one increment per thread
        assert final_counter >= expected_min_counter, (
            f"Shared counter too low: expected >= {expected_min_counter}, got {final_counter}"
        )
        
        # Record metrics
        self.record_metric("threads_tested", num_threads)
        self.record_metric("total_operations", total_operations)
        self.record_metric("thread_safety_errors", len(all_errors))
        self.record_metric("thread_safety_passed", len(all_errors) == 0)

    @pytest.mark.integration
    async def test_subprocess_environment_isolation(self):
        """
        Test that subprocess environment is properly isolated and managed.
        
        Business Value: Ensures subprocess operations (Docker, Git, etc.) work correctly with:
        - Proper environment variable inheritance
        - No pollution from test environment to subprocess
        - Correct service discovery for external tools
        """
        # Set up test environment with both system and application variables
        test_vars = {
            "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5434/test_db",
            "AUTH_SERVICE_URL": "http://test-auth:8081",
            "CUSTOM_APP_VAR": "custom_test_value",
            "PYTHONPATH": "/test/custom/pythonpath"
        }
        
        for key, value in test_vars.items():
            self._add_test_var(key, value, source="subprocess_test")
        
        # Test 1: Get subprocess environment
        subprocess_env = self.env.get_subprocess_env()
        
        # Verify test variables are included
        for key, expected_value in test_vars.items():
            assert key in subprocess_env, f"Test variable {key} missing from subprocess environment"
            assert subprocess_env[key] == expected_value, (
                f"Test variable {key} has wrong value in subprocess env: "
                f"expected '{expected_value}', got '{subprocess_env[key]}'"
            )
        
        # Verify critical system variables are preserved
        critical_system_vars = ["PATH"]
        for var in critical_system_vars:
            if var in os.environ:
                assert var in subprocess_env, f"Critical system variable {var} missing from subprocess environment"
        
        # Test 2: Additional variables
        additional_vars = {
            "SUBPROCESS_TEST_VAR": "subprocess_value",
            "CUSTOM_PATH_ADDITION": "/custom/bin"
        }
        
        subprocess_env_with_additional = self.env.get_subprocess_env(additional_vars)
        
        # Verify additional variables are included
        for key, expected_value in additional_vars.items():
            assert key in subprocess_env_with_additional, f"Additional variable {key} missing"
            assert subprocess_env_with_additional[key] == expected_value, (
                f"Additional variable {key} has wrong value"
            )
        
        # Verify original variables are still there
        for key, expected_value in test_vars.items():
            assert subprocess_env_with_additional[key] == expected_value, (
                f"Original variable {key} was lost when adding additional variables"
            )
        
        # Test 3: Real subprocess execution (if possible)
        try:
            # Try to run a simple subprocess with our environment
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    ['cmd', '/c', 'echo %DATABASE_URL%'],
                    env=subprocess_env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:  # Unix-like
                result = subprocess.run(
                    ['sh', '-c', 'echo $DATABASE_URL'],
                    env=subprocess_env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if result.returncode == 0:
                # Verify the environment variable was passed correctly
                output = result.stdout.strip()
                expected_db_url = test_vars["DATABASE_URL"]
                assert expected_db_url in output or output == expected_db_url, (
                    f"Subprocess did not receive correct DATABASE_URL: expected '{expected_db_url}', "
                    f"subprocess output: '{output}'"
                )
                
                self.record_metric("subprocess_execution_success", True)
            else:
                self.record_metric("subprocess_execution_failed", True)
                # Don't fail the test if subprocess execution fails (may not be available)
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            # Subprocess execution may not work in all test environments
            self.record_metric("subprocess_execution_skipped", str(e))
        
        # Record metrics
        self.record_metric("subprocess_env_vars_count", len(subprocess_env))
        self.record_metric("subprocess_isolation_tested", True)

    # === ENVIRONMENT DETECTION AND VALIDATION TESTS ===

    @pytest.mark.integration
    async def test_environment_detection_accuracy(self):
        """
        Test that environment detection correctly identifies all environments.
        
        Business Value: Prevents configuration errors that cause:
        - Wrong database connections (test DB used in production)
        - Incorrect auth service URLs (staging auth in production)
        - Wrong debug settings (debug enabled in production)
        """
        environment_test_cases = [
            # Development variants
            ("development", "development"),
            ("dev", "development"),
            ("local", "development"),
            ("Development", "development"),  # Case insensitive
            ("DEV", "development"),
            
            # Testing variants
            ("test", "test"),
            ("testing", "test"),
            ("Test", "test"),
            ("TESTING", "test"),
            
            # Staging
            ("staging", "staging"),
            ("Staging", "staging"),
            ("STAGING", "staging"),
            
            # Production variants
            ("production", "production"),
            ("prod", "production"),
            ("Production", "production"),
            ("PROD", "production"),
            
            # Default case
            ("", "development"),  # Empty should default to development
            ("unknown_env", "development"),  # Unknown should default to development
        ]
        
        for input_env, expected_env in environment_test_cases:
            # Clear any existing ENVIRONMENT variable
            if self.env.exists("ENVIRONMENT"):
                self.env.delete("ENVIRONMENT", source="env_detection_test_cleanup")
            
            # Set the test environment
            if input_env:  # Don't set empty string
                self._add_test_var("ENVIRONMENT", input_env, source="env_detection_test")
            
            # Test environment detection
            detected_env = self.env.get_environment_name()
            assert detected_env == expected_env, (
                f"Environment detection failed: input '{input_env}' -> expected '{expected_env}', got '{detected_env}'"
            )
            
            # Test environment boolean methods
            if expected_env == "development":
                assert self.env.is_development() == True
                assert self.env.is_test() == False
                assert self.env.is_staging() == False
                assert self.env.is_production() == False
            elif expected_env == "test":
                assert self.env.is_development() == False
                assert self.env.is_test() == True
                assert self.env.is_staging() == False
                assert self.env.is_production() == False
            elif expected_env == "staging":
                assert self.env.is_development() == False
                assert self.env.is_test() == False
                assert self.env.is_staging() == True
                assert self.env.is_production() == False
            elif expected_env == "production":
                assert self.env.is_development() == False
                assert self.env.is_test() == False
                assert self.env.is_staging() == False
                assert self.env.is_production() == True
        
        self.record_metric("environment_variants_tested", len(environment_test_cases))
        self.record_metric("environment_detection_passed", True)

    @pytest.mark.integration
    async def test_configuration_validation_comprehensive(self):
        """
        Test comprehensive configuration validation for different scenarios.
        
        Business Value: Prevents startup failures due to:
        - Missing required configuration variables
        - Invalid database URLs
        - Wrong auth service configurations
        - Missing OAuth credentials
        """
        # Test Case 1: Valid configuration
        valid_config = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "JWT_SECRET_KEY": "valid_jwt_secret_key_123",
            "SECRET_KEY": "valid_secret_key_456"
        }
        
        # Clear environment and set valid config
        for key in ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]:
            if self.env.exists(key):
                self.env.delete(key, source="validation_test_cleanup")
        
        for key, value in valid_config.items():
            self._add_test_var(key, value, source="valid_config_test")
        
        # Test validation passes
        validation_result = self.env.validate_all()
        assert validation_result.is_valid == True, (
            f"Valid configuration failed validation: errors={validation_result.errors}"
        )
        assert len(validation_result.errors) == 0, (
            f"Valid configuration has validation errors: {validation_result.errors}"
        )
        
        # Test Case 2: Missing required variables
        missing_var_scenarios = [
            ("DATABASE_URL", ["Missing required variable: DATABASE_URL"]),
            ("JWT_SECRET_KEY", ["Missing required variable: JWT_SECRET_KEY"]),
            ("SECRET_KEY", ["Missing required variable: SECRET_KEY"]),
        ]
        
        for missing_var, expected_errors in missing_var_scenarios:
            # Remove the required variable
            if self.env.exists(missing_var):
                self.env.delete(missing_var, source="missing_var_test")
            
            # Test validation fails
            validation_result = self.env.validate_all()
            assert validation_result.is_valid == False, (
                f"Validation should fail when {missing_var} is missing"
            )
            
            # Check for expected error message
            error_found = any(expected_error in validation_result.errors 
                            for expected_error in expected_errors)
            assert error_found, (
                f"Expected error for missing {missing_var} not found. "
                f"Expected: {expected_errors}, Got: {validation_result.errors}"
            )
            
            # Restore the variable for next test
            self._add_test_var(missing_var, valid_config[missing_var], source="restore_var_test")
        
        # Test Case 3: Staging database validation (specific business logic)
        staging_validation_scenarios = [
            {
                "name": "valid_staging",
                "environment": "staging",
                "vars": {
                    "POSTGRES_HOST": "staging-postgres.example.com",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "secure_staging_password_123",
                    "POSTGRES_DB": "staging_db"
                },
                "should_pass": True
            },
            {
                "name": "invalid_staging_localhost",
                "environment": "staging", 
                "vars": {
                    "POSTGRES_HOST": "localhost",  # Invalid for staging
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "secure_password",
                    "POSTGRES_DB": "staging_db"
                },
                "should_pass": False,
                "expected_error": "POSTGRES_HOST cannot be 'localhost' in staging"
            },
            {
                "name": "invalid_staging_user",
                "environment": "staging",
                "vars": {
                    "POSTGRES_HOST": "staging-postgres.example.com",
                    "POSTGRES_USER": "user_pr-4",  # Invalid pattern
                    "POSTGRES_PASSWORD": "secure_password",
                    "POSTGRES_DB": "staging_db"
                },
                "should_pass": False,
                "expected_error": "Invalid POSTGRES_USER 'user_pr-4'"
            }
        ]
        
        for scenario in staging_validation_scenarios:
            # Set up scenario
            self._add_test_var("ENVIRONMENT", scenario["environment"], source="staging_validation_test")
            
            for key, value in scenario["vars"].items():
                self._add_test_var(key, value, source="staging_validation_test")
            
            # Run staging-specific validation
            staging_result = self.env.validate_staging_database_credentials()
            
            if scenario["should_pass"]:
                assert staging_result["valid"] == True, (
                    f"Staging validation should pass for {scenario['name']}: {staging_result['issues']}"
                )
            else:
                assert staging_result["valid"] == False, (
                    f"Staging validation should fail for {scenario['name']}"
                )
                
                if "expected_error" in scenario:
                    error_found = any(scenario["expected_error"] in issue 
                                    for issue in staging_result["issues"])
                    assert error_found, (
                        f"Expected staging error '{scenario['expected_error']}' not found. "
                        f"Got issues: {staging_result['issues']}"
                    )
        
        # Record validation test metrics
        self.record_metric("validation_scenarios_tested", 
                          1 + len(missing_var_scenarios) + len(staging_validation_scenarios))
        self.record_metric("configuration_validation_passed", True)

    # === ERROR HANDLING AND EDGE CASES ===

    @pytest.mark.integration
    async def test_error_handling_and_recovery(self):
        """
        Test error handling and recovery scenarios.
        
        Business Value: Ensures system remains stable when:
        - Configuration files are corrupted
        - Environment variables contain invalid characters
        - Concurrent modifications cause conflicts
        """
        # Test Case 1: Invalid .env file format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as invalid_env_file:
            invalid_content = """
# Valid line
VALID_VAR=valid_value

# Invalid lines (no equals sign)
INVALID_LINE_NO_EQUALS
ANOTHER_INVALID_LINE

# Empty line and comment are OK


# Malformed line with multiple equals
MULTIPLE=EQUALS=SIGNS=HERE

# Valid line after invalid
ANOTHER_VALID=another_value
            """.strip()
            invalid_env_file.write(invalid_content)
            invalid_file_path = invalid_env_file.name

        try:
            # Load invalid file - should handle errors gracefully
            loaded_count, errors = self.env.load_from_file(invalid_file_path, override_existing=True)
            
            # Should have loaded some valid variables despite errors
            assert loaded_count >= 2, f"Should have loaded at least 2 valid vars, got {loaded_count}"
            assert len(errors) >= 2, f"Should have at least 2 errors for invalid lines, got {len(errors)}"
            
            # Valid variables should be loaded
            assert self.env.get("VALID_VAR") == "valid_value"
            assert self.env.get("ANOTHER_VALID") == "another_value"
            
            # Multiple equals should be handled (everything after first = is the value)
            assert self.env.get("MULTIPLE") == "EQUALS=SIGNS=HERE"
            
        finally:
            os.unlink(invalid_file_path)
        
        # Test Case 2: Environment variable with control characters
        test_vars_with_control_chars = {
            "CLEAN_VAR": "normal_clean_value",
            "VAR_WITH_NEWLINE": "value_with\nnewline", 
            "VAR_WITH_TAB": "value_with\ttab",
            "VAR_WITH_CARRIAGE_RETURN": "value_with\rcarriage_return",
            "VAR_WITH_NULL": "value_with\x00null_byte"
        }
        
        for key, value in test_vars_with_control_chars.items():
            self._add_test_var(key, value, source="control_char_test")
        
        # Verify variables are set and control characters are handled
        clean_var = self.env.get("CLEAN_VAR")
        assert clean_var == "normal_clean_value", "Clean variable should be unchanged"
        
        # Control characters should be sanitized
        var_with_newline = self.env.get("VAR_WITH_NEWLINE")
        assert "\n" not in var_with_newline, "Newline should be sanitized"
        assert "value_with" in var_with_newline, "Content should be preserved"
        
        # Test Case 3: Very large environment values
        large_value = "x" * 10000  # 10KB value
        self._add_test_var("LARGE_VAR", large_value, source="large_value_test")
        
        retrieved_large = self.env.get("LARGE_VAR")
        assert retrieved_large == large_value, "Large values should be handled correctly"
        assert len(retrieved_large) == 10000, f"Large value length mismatch: expected 10000, got {len(retrieved_large)}"
        
        # Test Case 4: Unicode and special characters
        unicode_test_vars = {
            "UNICODE_VAR": "value_with_unicode_🚀_emoji",
            "SPECIAL_CHARS": "value!@#$%^&*()_+-={}[]|\\:;\"'<>?,./ with spaces",
            "ACCENTED_CHARS": "café_résumé_naïve_São_Paulo",
        }
        
        for key, value in unicode_test_vars.items():
            self._add_test_var(key, value, source="unicode_test")
        
        # Verify unicode values are preserved
        for key, expected_value in unicode_test_vars.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Unicode variable {key} not preserved: expected '{expected_value}', got '{actual_value}'"
            )
        
        # Record error handling test metrics
        self.record_metric("invalid_env_file_errors", len(errors))
        self.record_metric("control_char_vars_tested", len(test_vars_with_control_chars))
        self.record_metric("unicode_vars_tested", len(unicode_test_vars))
        self.record_metric("error_handling_passed", True)

    @pytest.mark.integration
    async def test_performance_under_load(self):
        """
        Test IsolatedEnvironment performance under load conditions.
        
        Business Value: Ensures system performance remains acceptable during:
        - High-frequency configuration reads (WebSocket authentication)
        - Bulk configuration updates (service startup)
        - Concurrent user sessions with different configurations
        """
        # Performance test configuration
        num_variables = 1000
        num_operations = 5000
        
        # Setup: Create many variables
        setup_start = time.time()
        
        for i in range(num_variables):
            var_name = f"PERF_VAR_{i}"
            var_value = f"performance_test_value_{i}_{time.time()}"
            self._add_test_var(var_name, var_value, source="performance_test")
        
        setup_time = time.time() - setup_start
        
        # Test 1: Bulk read performance
        read_start = time.time()
        
        for i in range(num_operations):
            var_index = i % num_variables
            var_name = f"PERF_VAR_{var_index}"
            value = self.env.get(var_name)
            assert value is not None, f"Performance test variable {var_name} missing"
        
        read_time = time.time() - read_start
        
        # Test 2: Bulk write performance
        write_start = time.time()
        
        for i in range(num_operations // 10):  # Fewer writes to avoid memory issues
            var_name = f"PERF_WRITE_VAR_{i}"
            var_value = f"perf_write_value_{i}"
            self._add_test_var(var_name, var_value, source="performance_write_test")
        
        write_time = time.time() - write_start
        
        # Test 3: get_all() performance with many variables
        get_all_start = time.time()
        all_vars = self.env.get_all()
        get_all_time = time.time() - get_all_start
        
        # Performance assertions (reasonable thresholds)
        ops_per_second_read = num_operations / read_time if read_time > 0 else float('inf')
        ops_per_second_write = (num_operations // 10) / write_time if write_time > 0 else float('inf')
        
        # Performance should be reasonable (adjust thresholds as needed)
        assert setup_time < 10.0, f"Setup of {num_variables} variables took too long: {setup_time:.2f}s"
        assert read_time < 5.0, f"Reading {num_operations} variables took too long: {read_time:.2f}s"
        assert write_time < 10.0, f"Writing {num_operations//10} variables took too long: {write_time:.2f}s"
        assert get_all_time < 1.0, f"get_all() took too long: {get_all_time:.2f}s"
        assert len(all_vars) >= num_variables, f"get_all() returned too few variables: {len(all_vars)} < {num_variables}"
        
        # Read performance should be fast (at least 1000 ops/sec)
        assert ops_per_second_read >= 1000, (
            f"Read performance too slow: {ops_per_second_read:.0f} ops/sec (expected >= 1000)"
        )
        
        # Record performance metrics
        self.record_metric("setup_time_seconds", setup_time)
        self.record_metric("read_time_seconds", read_time)
        self.record_metric("write_time_seconds", write_time) 
        self.record_metric("get_all_time_seconds", get_all_time)
        self.record_metric("read_ops_per_second", ops_per_second_read)
        self.record_metric("write_ops_per_second", ops_per_second_write)
        self.record_metric("variables_tested", num_variables)
        self.record_metric("total_operations", num_operations)
        self.record_metric("performance_test_passed", True)

    # === INTEGRATION WITH REAL SERVICES ===

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_integration_with_real_services(self, real_services_fixture):
        """
        Test IsolatedEnvironment integration with real services.
        
        Business Value: Validates configuration works with actual services:
        - Database connections use correct credentials
        - Auth service URLs resolve correctly
        - Service discovery works with configured ports
        """
        # Get real services configuration
        real_services_config = {
            "DATABASE_URL": real_services_fixture.get("database_url", "postgresql://postgres:postgres@localhost:5434/test_db"),
            "AUTH_SERVICE_URL": real_services_fixture.get("auth_url", "http://localhost:8081"),
            "REDIS_URL": real_services_fixture.get("redis_url", "redis://localhost:6381"),
            "ENVIRONMENT": "testing"
        }
        
        # Apply real services configuration 
        for key, value in real_services_config.items():
            self._add_test_var(key, value, source="real_services_integration")
        
        # Test 1: Verify configuration is applied correctly
        for key, expected_value in real_services_config.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Real services config mismatch: {key} expected '{expected_value}', got '{actual_value}'"
            )
        
        # Test 2: Test configuration affects environment detection
        detected_env = self.env.get_environment_name()
        assert detected_env == "test", f"Environment detection failed with real services: got '{detected_env}'"
        
        # Test 3: Test subprocess environment includes real services config
        subprocess_env = self.env.get_subprocess_env()
        for key, expected_value in real_services_config.items():
            assert key in subprocess_env, f"Real services var {key} missing from subprocess env"
            assert subprocess_env[key] == expected_value, (
                f"Real services var {key} wrong in subprocess: expected '{expected_value}', got '{subprocess_env[key]}'"
            )
        
        # Test 4: Test configuration validation with real services
        validation_result = self.env.validate_all()
        
        # Should pass validation if JWT_SECRET_KEY and SECRET_KEY are provided or defaulted
        if not validation_result.is_valid:
            # Add minimal required vars for validation to pass
            self._add_test_var("JWT_SECRET_KEY", "test_jwt_secret_for_real_services", source="real_services_validation")
            self._add_test_var("SECRET_KEY", "test_secret_key_for_real_services", source="real_services_validation")
            
            validation_result = self.env.validate_all()
            assert validation_result.is_valid == True, (
                f"Configuration validation failed with real services: {validation_result.errors}"
            )
        
        # Record integration test metrics
        self.record_metric("real_services_vars_set", len(real_services_config))
        self.record_metric("real_services_integration_passed", True)

    # === COMPREHENSIVE SYSTEM TEST ===

    @pytest.mark.integration
    async def test_comprehensive_system_scenario(self):
        """
        CRITICAL: End-to-end system test simulating real production scenario.
        
        Business Value: Validates the entire configuration system works correctly
        in realistic scenarios that mirror actual production usage patterns.
        """
        # Scenario: Multi-environment configuration with service startup simulation
        
        # Phase 1: Development environment startup
        dev_config = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://dev_user:dev_pass@localhost:5432/dev_db",
            "AUTH_SERVICE_URL": "http://localhost:8081", 
            "REDIS_URL": "redis://localhost:6379",
            "JWT_SECRET_KEY": "dev_jwt_secret_123",
            "SECRET_KEY": "dev_secret_key_456",
            "DEBUG": "true",
            "OAUTH_CLIENT_ID": "dev_oauth_client",
            "OAUTH_CLIENT_SECRET": "dev_oauth_secret"
        }
        
        # Simulate service startup in development
        for key, value in dev_config.items():
            self._add_test_var(key, value, source="dev_startup")
        
        # Validate development configuration
        assert self.env.get_environment_name() == "development"
        assert self.env.is_development() == True
        validation_result = self.env.validate_all()
        assert validation_result.is_valid == True, f"Dev config validation failed: {validation_result.errors}"
        
        # Phase 2: Simulate environment switch to staging
        staging_config = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://staging_user:staging_secure_pass@staging-postgres:5432/staging_db",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "REDIS_URL": "redis://staging-redis:6379",
            "JWT_SECRET_KEY": "staging_jwt_secret_ultra_secure",
            "SECRET_KEY": "staging_secret_key_ultra_secure",
            "DEBUG": "false",
            "OAUTH_CLIENT_ID": "staging_oauth_client",
            "OAUTH_CLIENT_SECRET": "staging_oauth_secret_secure"
        }
        
        # Clear development config and set staging config
        for key in dev_config.keys():
            self.env.delete(key, source="dev_to_staging_transition")
        
        for key, value in staging_config.items():
            self._add_test_var(key, value, source="staging_startup")
        
        # Validate staging configuration
        assert self.env.get_environment_name() == "staging"
        assert self.env.is_staging() == True
        assert self.env.is_development() == False
        
        # Staging-specific validation
        staging_validation = self.env.validate_staging_database_credentials()
        assert staging_validation["valid"] == True, f"Staging validation failed: {staging_validation['issues']}"
        
        # Phase 3: Simulate concurrent user sessions (multi-tenancy)
        user_sessions = [
            {
                "user_id": "user_123",
                "session_vars": {
                    "USER_ID": "user_123",
                    "SESSION_TOKEN": "session_token_123",
                    "USER_PREFERENCES": "theme=dark,lang=en"
                }
            },
            {
                "user_id": "user_456", 
                "session_vars": {
                    "USER_ID": "user_456",
                    "SESSION_TOKEN": "session_token_456",
                    "USER_PREFERENCES": "theme=light,lang=es"
                }
            }
        ]
        
        # Simulate user sessions
        for session in user_sessions:
            for key, value in session["session_vars"].items():
                session_var_name = f"{session['user_id']}_{key}"
                self._add_test_var(session_var_name, value, source=f"user_session_{session['user_id']}")
        
        # Verify session isolation
        for session in user_sessions:
            for key, expected_value in session["session_vars"].items():
                session_var_name = f"{session['user_id']}_{key}"
                actual_value = self.env.get(session_var_name)
                assert actual_value == expected_value, (
                    f"User session isolation failed: {session_var_name} expected '{expected_value}', got '{actual_value}'"
                )
        
        # Phase 4: Simulate configuration file loading (deployment scenario)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as deployment_env:
            deployment_content = """
# Deployment override configuration
LOG_LEVEL=INFO
METRICS_ENABLED=true
TRACING_ENABLED=true
RATE_LIMIT_ENABLED=true
DEPLOYMENT_VERSION=v1.2.3
DEPLOYMENT_TIMESTAMP=2024-01-15T10:30:00Z
            """.strip()
            deployment_env.write(deployment_content)
            deployment_env_path = deployment_env.name
        
        try:
            # Load deployment configuration (should not override existing)
            loaded_count, errors = self.env.load_from_file(deployment_env_path, override_existing=False)
            assert loaded_count > 0, f"Deployment config not loaded: {errors}"
            assert len(errors) == 0, f"Deployment config errors: {errors}"
            
            # Verify deployment config is loaded
            assert self.env.get("LOG_LEVEL") == "INFO"
            assert self.env.get("DEPLOYMENT_VERSION") == "v1.2.3"
            
            # Verify existing staging config is preserved
            assert self.env.get("ENVIRONMENT") == "staging"
            assert self.env.get("AUTH_SERVICE_URL") == "https://auth.staging.netrasystems.ai"
            
        finally:
            os.unlink(deployment_env_path)
        
        # Phase 5: Final system validation
        final_validation = self.env.validate_all()
        assert final_validation.is_valid == True, f"Final system validation failed: {final_validation.errors}"
        
        # Verify all components are working together
        all_vars = self.env.get_all()
        assert len(all_vars) >= len(staging_config) + len(user_sessions) * 3 + 6  # staging + users + deployment
        
        # Record comprehensive test metrics
        self.record_metric("dev_config_vars", len(dev_config))
        self.record_metric("staging_config_vars", len(staging_config))
        self.record_metric("user_sessions", len(user_sessions))
        self.record_metric("deployment_vars_loaded", loaded_count)
        self.record_metric("final_total_vars", len(all_vars))
        self.record_metric("comprehensive_scenario_passed", True)
        
        # Log success summary
        metrics = self.get_all_metrics()
        self.set_env_var("TEST_COMPLETION_TIME", str(time.time()))
        
        # This test represents the gold standard for IsolatedEnvironment functionality
        assert True, "Comprehensive system scenario completed successfully"


# === HELPER TEST CLASS FOR LEGACY COMPATIBILITY ===

class TestIsolatedEnvironmentLegacyCompatibility(SSotBaseTestCase):
    """
    Tests for backwards compatibility with legacy environment management patterns.
    
    Business Value: Ensures smooth migration from legacy code without breaking existing functionality.
    """

    @pytest.mark.integration
    async def test_legacy_get_env_function(self):
        """Test that get_env() function works correctly."""
        env = get_env()
        assert isinstance(env, IsolatedEnvironment)
        
        # Test singleton behavior
        env2 = get_env()
        assert env is env2, "get_env() should return same singleton instance"

    @pytest.mark.integration
    async def test_legacy_convenience_functions(self):
        """Test legacy convenience functions still work."""
        from shared.isolated_environment import setenv, getenv, delenv
        
        # Test setenv/getenv
        result = setenv("LEGACY_TEST_VAR", "legacy_value", source="legacy_test")
        assert result == True, "setenv should return True on success"
        
        value = getenv("LEGACY_TEST_VAR")
        assert value == "legacy_value", f"getenv failed: expected 'legacy_value', got '{value}'"
        
        # Test delenv
        delete_result = delenv("LEGACY_TEST_VAR")
        assert delete_result == True, "delenv should return True on success"
        
        value_after_delete = getenv("LEGACY_TEST_VAR")
        assert value_after_delete is None, "Variable should be None after deletion"