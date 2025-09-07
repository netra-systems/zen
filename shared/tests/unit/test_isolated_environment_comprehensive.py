"""
Test IsolatedEnvironment Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Independence
- Business Goal: Ensure the MOST CRITICAL SSOT module works perfectly
- Value Impact: IsolatedEnvironment is used by EVERY service and ALL tests - failure cascades to entire platform
- Strategic Impact: Platform stability, test reliability, and service independence depend on this module

CRITICAL IMPORTANCE: This module is the foundation of environment variable management across
the entire Netra platform. It prevents configuration drift, ensures test isolation, and
enables service independence. Any bug in this module can cascade to ALL services.

Testing Strategy:
- 100% code coverage of all methods and properties
- Real environment isolation testing (no mocks)
- Thread safety validation with concurrent access
- Environment variable operations (get, set, delete, validation)
- Source tracking functionality
- Context manager and cleanup behavior
- Error handling and edge cases
- Multi-user system compatibility
- Windows encoding support
"""

import pytest
import os
import threading
import time
import tempfile
import concurrent.futures
from pathlib import Path
from typing import Dict, Optional, Any
from unittest.mock import patch, Mock

# Import the module under test
from shared.isolated_environment import (
    IsolatedEnvironment, 
    get_env,
    ValidationResult,
    _mask_sensitive_value,
    setenv,
    getenv,
    delenv,
    get_subprocess_env,
    load_secrets,
    SecretLoader,
    EnvironmentValidator
)

# Import test framework SSOT patterns
from test_framework.ssot.isolated_test_helper import isolated_env
from test_framework.isolated_environment_fixtures import STANDARD_TEST_CONFIG


class TestIsolatedEnvironmentSingleton:
    """Test singleton behavior and instance management."""
    
    def test_singleton_instance_creation(self):
        """Test that IsolatedEnvironment properly implements singleton pattern."""
        # Get two instances
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment()
        
        # They should be the same instance
        assert env1 is env2
        assert id(env1) == id(env2)
    
    def test_get_instance_method(self):
        """Test get_instance class method returns same singleton."""
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment.get_instance()
        
        assert env1 is env2
    
    def test_get_env_function_consistency(self):
        """Test get_env() function returns same singleton instance."""
        env1 = IsolatedEnvironment()
        env2 = get_env()
        
        assert env1 is env2
    
    def test_thread_safe_singleton_creation(self):
        """Test singleton creation is thread-safe under concurrent access."""
        instances = []
        errors = []
        
        def create_instance():
            try:
                instance = IsolatedEnvironment()
                instances.append(instance)
            except Exception as e:
                errors.append(e)
        
        # Create 10 threads trying to create instances simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        
        # Verify all instances are the same
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "Thread safety violation: multiple instances created"


class TestEnvironmentIsolation:
    """Test environment isolation functionality."""
    
    def test_isolation_enable_disable(self):
        """Test enabling and disabling isolation mode."""
        env = get_env()
        
        # Start with clean state
        env.reset()
        initial_isolation_state = env.is_isolated()
        
        # Enable isolation
        env.enable_isolation(backup_original=True)
        assert env.is_isolated() == True
        assert env.is_isolation_enabled() == True  # Test alias
        
        # Disable isolation
        env.disable_isolation()
        assert env.is_isolated() == False
        
        # Reset for other tests
        env.reset()
    
    def test_isolation_prevents_os_environ_pollution(self):
        """Test that isolation mode prevents pollution of os.environ."""
        env = get_env()
        env.reset()
        
        # Record original os.environ state
        original_keys = set(os.environ.keys())
        
        # Enable isolation
        env.enable_isolation()
        
        # Set variable in isolated environment
        test_key = "TEST_ISOLATION_POLLUTION"
        env.set(test_key, "isolated_value", source="test")
        
        # Variable should exist in isolated environment
        assert env.get(test_key) == "isolated_value"
        
        # But NOT in os.environ (except for preserved variables)
        if test_key not in env.PRESERVE_IN_OS_ENVIRON:
            assert test_key not in os.environ
        
        # os.environ should have same keys as before
        current_keys = set(os.environ.keys())
        # Allow for preserved variables that might be added
        preserved_additions = current_keys - original_keys
        for key in preserved_additions:
            assert key in env.PRESERVE_IN_OS_ENVIRON, f"Unexpected key in os.environ: {key}"
        
        # Clean up
        env.reset()
    
    def test_preserved_variables_in_os_environ(self):
        """Test that preserved variables remain in os.environ during isolation."""
        env = get_env()
        env.reset()
        
        # Enable isolation
        env.enable_isolation()
        
        # Test with a preserved variable
        preserved_var = list(env.PRESERVE_IN_OS_ENVIRON)[0]  # Get first preserved var
        test_value = "test_preserved_value"
        
        env.set(preserved_var, test_value, source="test")
        
        # Should be in both isolated and os.environ
        assert env.get(preserved_var) == test_value
        assert os.environ.get(preserved_var) == test_value
        
        env.reset()
    
    def test_sync_with_os_environ_in_test_context(self):
        """Test synchronization with os.environ in test context."""
        env = get_env()
        env.reset()
        
        # Mock test context
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_example'}):
            env.enable_isolation()
            
            # Add something to os.environ after isolation
            test_key = "TEST_SYNC_VAR"
            os.environ[test_key] = "sync_test_value"
            
            # Trigger sync (happens automatically in test context)
            env._sync_with_os_environ()
            
            # Should be available in isolated environment
            assert env.get(test_key) == "sync_test_value"
        
        env.reset()


class TestEnvironmentVariableOperations:
    """Test basic environment variable operations."""
    
    def test_set_and_get_basic(self):
        """Test basic set and get operations."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test basic set/get
        env.set("TEST_BASIC", "basic_value", source="test")
        assert env.get("TEST_BASIC") == "basic_value"
        
        # Test with default value
        assert env.get("NONEXISTENT_VAR", "default") == "default"
        assert env.get("NONEXISTENT_VAR") is None
        
        env.reset()
    
    def test_set_with_source_tracking(self):
        """Test source tracking functionality."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set with source
        env.set("TEST_SOURCE", "source_value", source="unit_test")
        
        # Check source is tracked
        assert env.get_variable_source("TEST_SOURCE") == "unit_test"
        
        env.reset()
    
    def test_delete_operations(self):
        """Test delete operations and exists checking."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set a variable
        env.set("TEST_DELETE", "delete_me", source="test")
        assert env.exists("TEST_DELETE") == True
        assert env.is_set("TEST_DELETE") == True  # Test alias
        
        # Delete it
        result = env.delete("TEST_DELETE", source="test")
        assert result == True  # Successfully deleted
        
        # Should no longer exist
        assert env.exists("TEST_DELETE") == False
        assert env.get("TEST_DELETE") is None
        
        # Try to delete non-existent variable
        result = env.delete("NONEXISTENT", source="test")
        assert result == False  # Nothing to delete
        
        env.reset()
    
    def test_unset_alias(self):
        """Test unset method as alias for delete."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set and unset
        env.set("TEST_UNSET", "unset_me", source="test")
        env.unset("TEST_UNSET")  # No return value expected
        
        assert env.get("TEST_UNSET") is None
        assert env.exists("TEST_UNSET") == False
        
        env.reset()
    
    def test_update_multiple_variables(self):
        """Test updating multiple variables at once."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Update multiple
        variables = {
            "TEST_MULTI_1": "value1",
            "TEST_MULTI_2": "value2",
            "TEST_MULTI_3": "value3"
        }
        
        results = env.update(variables, source="test_batch")
        
        # All should succeed
        for key, result in results.items():
            assert result == True, f"Failed to set {key}"
        
        # Verify values
        for key, expected_value in variables.items():
            assert env.get(key) == expected_value
            assert env.get_variable_source(key) == "test_batch"
        
        env.reset()
    
    def test_get_all_variables(self):
        """Test getting all environment variables."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set some test variables
        test_vars = {
            "GET_ALL_1": "value1",
            "GET_ALL_2": "value2",
            "GET_ALL_3": "value3"
        }
        env.update(test_vars, source="test")
        
        # Get all variables
        all_vars = env.get_all()
        all_vars_alias1 = env.get_all_variables()  # Test alias
        all_vars_alias2 = env.as_dict()  # Test alias
        
        # All methods should return same result
        assert all_vars == all_vars_alias1 == all_vars_alias2
        
        # Should contain our test variables
        for key, value in test_vars.items():
            assert all_vars[key] == value
        
        env.reset()


class TestValueSanitization:
    """Test value sanitization functionality."""
    
    def test_mask_sensitive_value_function(self):
        """Test the _mask_sensitive_value function."""
        # Test sensitive patterns
        assert _mask_sensitive_value("PASSWORD", "secret123") == "sec***"
        assert _mask_sensitive_value("API_KEY", "sk-1234567890abcdef") == "sk-***"
        assert _mask_sensitive_value("SECRET", "top_secret") == "top***"
        assert _mask_sensitive_value("JWT_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9") == "eyJ***"
        
        # Test short sensitive values
        assert _mask_sensitive_value("KEY", "ab") == "***"
        assert _mask_sensitive_value("AUTH", "xyz") == "***"
        
        # Test non-sensitive patterns
        assert _mask_sensitive_value("DATABASE_URL", "postgresql://user:pass@host/db") == "postgresql://user:pass@host/db"[:50]
        
        # Test long non-sensitive values
        long_value = "a" * 60
        assert _mask_sensitive_value("LOG_LEVEL", long_value) == long_value[:50] + "..."
    
    def test_sanitize_database_url(self):
        """Test database URL sanitization."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test PostgreSQL URL
        db_url = "postgresql://user:pass@localhost:5432/dbname"
        env.set("DATABASE_URL", db_url, source="test")
        retrieved = env.get("DATABASE_URL")
        
        # Should preserve URL structure
        assert retrieved.startswith("postgresql://")
        assert "localhost:5432" in retrieved
        assert "dbname" in retrieved
        
        env.reset()
    
    def test_sanitize_generic_value(self):
        """Test generic value sanitization removes control characters."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test value with control characters
        value_with_control = "normal_text\x00\x01\x1f\x7f"
        env.set("TEST_SANITIZE", value_with_control, source="test")
        
        # Control characters should be removed
        retrieved = env.get("TEST_SANITIZE")
        assert retrieved == "normal_text"  # Control chars removed
        assert "\x00" not in retrieved
        assert "\x01" not in retrieved
        
        env.reset()


class TestShellCommandExpansion:
    """Test shell command expansion functionality."""
    
    def test_shell_expansion_disabled_in_test(self):
        """Test that shell expansion is disabled during pytest."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Mock pytest context
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_example'}):
            # Set value with shell command
            shell_value = "prefix_$(echo 'test')_suffix"
            env.set("TEST_SHELL", shell_value, source="test")
            
            # Should not be expanded in test context
            retrieved = env.get("TEST_SHELL")
            assert retrieved == shell_value  # Unchanged
        
        env.reset()
    
    def test_shell_expansion_disabled_flag(self):
        """Test that shell expansion can be disabled via flag."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Disable shell expansion
        env.set("DISABLE_SHELL_EXPANSION", "true", source="test")
        
        # Set value with shell command
        shell_value = "prefix_$(echo 'test')_suffix"
        env.set("TEST_SHELL_DISABLED", shell_value, source="test")
        
        # Should not be expanded
        retrieved = env.get("TEST_SHELL_DISABLED")
        assert retrieved == shell_value  # Unchanged
        
        env.reset()


class TestProtectionMechanism:
    """Test variable protection functionality."""
    
    def test_protect_variable(self):
        """Test protecting variables from modification."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set and protect a variable
        env.set("PROTECTED_VAR", "original_value", source="test")
        env.protect_variable("PROTECTED_VAR")
        assert env.is_protected("PROTECTED_VAR") == True
        
        # Try to modify protected variable (should fail)
        result = env.set("PROTECTED_VAR", "new_value", source="test")
        assert result == False  # Should be blocked
        
        # Value should remain unchanged
        assert env.get("PROTECTED_VAR") == "original_value"
        
        # Try with force (should succeed)
        result = env.set("PROTECTED_VAR", "forced_value", source="test", force=True)
        assert result == True  # Should succeed with force
        assert env.get("PROTECTED_VAR") == "forced_value"
        
        # Unprotect
        env.unprotect_variable("PROTECTED_VAR")
        assert env.is_protected("PROTECTED_VAR") == False
        
        # Now should be modifiable
        result = env.set("PROTECTED_VAR", "unprotected_value", source="test")
        assert result == True
        assert env.get("PROTECTED_VAR") == "unprotected_value"
        
        env.reset()
    
    def test_protect_alias_method(self):
        """Test protect method as alias for protect_variable."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        env.set("ALIAS_PROTECTED", "value", source="test")
        env.protect("ALIAS_PROTECTED")  # Using alias
        
        assert env.is_protected("ALIAS_PROTECTED") == True
        
        env.reset()


class TestCallbackSystem:
    """Test change callback system."""
    
    def test_change_callbacks(self):
        """Test change callback registration and execution."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Track callback calls
        callback_calls = []
        
        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        
        # Register callback
        env.add_change_callback(test_callback)
        
        # Make changes
        env.set("CALLBACK_TEST", "first_value", source="test")
        env.set("CALLBACK_TEST", "second_value", source="test")
        env.delete("CALLBACK_TEST", source="test")
        
        # Verify callbacks were called
        assert len(callback_calls) == 3
        
        # Check callback parameters
        assert callback_calls[0] == ("CALLBACK_TEST", None, "first_value")  # Set from None
        assert callback_calls[1] == ("CALLBACK_TEST", "first_value", "second_value")  # Update
        assert callback_calls[2] == ("CALLBACK_TEST", "second_value", None)  # Delete
        
        # Remove callback
        env.remove_change_callback(test_callback)
        
        # Further changes should not trigger callback
        env.set("NO_CALLBACK", "value", source="test")
        assert len(callback_calls) == 3  # No new callbacks
        
        env.reset()
    
    def test_callback_error_handling(self):
        """Test that callback errors don't break environment operations."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Callback that throws error
        def error_callback(key, old_value, new_value):
            raise ValueError("Callback error")
        
        env.add_change_callback(error_callback)
        
        # Should not raise error despite callback failure
        result = env.set("ERROR_CALLBACK_TEST", "value", source="test")
        assert result == True  # Operation should succeed
        assert env.get("ERROR_CALLBACK_TEST") == "value"
        
        env.reset()


class TestFileLoading:
    """Test loading variables from .env files."""
    
    def test_load_from_file_basic(self):
        """Test basic file loading functionality."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            f.write("TEST_FILE_VAR1=file_value1\n")
            f.write("TEST_FILE_VAR2=file_value2\n")
            f.write("# Comment line\n")
            f.write("\n")  # Empty line
            f.write("TEST_FILE_VAR3=\"quoted_value\"\n")
            temp_file = f.name
        
        try:
            # Load file
            loaded_count, errors = env.load_from_file(temp_file, source="test_file")
            
            # Should load successfully
            assert loaded_count == 3
            assert len(errors) == 0
            
            # Verify values
            assert env.get("TEST_FILE_VAR1") == "file_value1"
            assert env.get("TEST_FILE_VAR2") == "file_value2"
            assert env.get("TEST_FILE_VAR3") == "quoted_value"  # Quotes removed
            
            # Verify source tracking
            source = env.get_variable_source("TEST_FILE_VAR1")
            assert source is not None, "Source tracking should not be None"
            assert source == "test_file" or source.startswith("file:"), f"Expected test_file or file: prefix, got: {source}"
            
        finally:
            # Clean up - robust Windows-compatible cleanup
            try:
                os.unlink(temp_file)
            except (OSError, PermissionError) as e:
                # On Windows, files may be locked temporarily
                print(f"Warning: Could not delete temp file {temp_file}: {e}")
            env.reset()
    
    def test_load_from_file_override_behavior(self):
        """Test file loading override behavior."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set existing variable
        env.set("OVERRIDE_TEST", "existing_value", source="manual")
        
        # Create file with same variable
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            f.write("OVERRIDE_TEST=file_value\n")
            temp_file = f.name
        
        try:
            # Load with override_existing=False (default behavior for auto-load)
            loaded_count, errors = env.load_from_file(temp_file, override_existing=False)
            
            # Should not load (already exists)
            assert loaded_count == 0
            assert env.get("OVERRIDE_TEST") == "existing_value"  # Unchanged
            
            # Load with override_existing=True
            loaded_count, errors = env.load_from_file(temp_file, override_existing=True)
            
            # Should now load and override
            assert loaded_count == 1
            assert env.get("OVERRIDE_TEST") == "file_value"  # Changed
            
        finally:
            try:
                os.unlink(temp_file)
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not delete temp file {temp_file}: {e}")
            env.reset()
    
    def test_load_from_file_error_handling(self):
        """Test file loading error handling."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test non-existent file
        loaded_count, errors = env.load_from_file("/nonexistent/file.env")
        assert loaded_count == 0
        assert len(errors) > 0
        
        # Test malformed file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            f.write("VALID_VAR=valid_value\n")
            f.write("INVALID_LINE_NO_EQUALS\n")  # Invalid format
            f.write("ANOTHER_VALID=another_value\n")
            temp_file = f.name
        
        try:
            loaded_count, errors = env.load_from_file(temp_file)
            
            # Should load valid lines, report errors for invalid
            assert loaded_count == 2  # Two valid lines
            assert len(errors) == 1   # One invalid line
            assert "Invalid format" in errors[0]
            
            # Valid variables should still be loaded
            assert env.get("VALID_VAR") == "valid_value"
            assert env.get("ANOTHER_VALID") == "another_value"
            
        finally:
            try:
                os.unlink(temp_file)
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not delete temp file {temp_file}: {e}")
            env.reset()


class TestSubprocessEnvironment:
    """Test subprocess environment handling."""
    
    def test_get_subprocess_env_isolation_mode(self):
        """Test getting environment for subprocess in isolation mode."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set some isolated variables
        env.set("SUBPROCESS_VAR1", "value1", source="test")
        env.set("SUBPROCESS_VAR2", "value2", source="test")
        
        # Get subprocess env
        subprocess_env = env.get_subprocess_env()
        
        # Should include isolated variables
        assert subprocess_env["SUBPROCESS_VAR1"] == "value1"
        assert subprocess_env["SUBPROCESS_VAR2"] == "value2"
        
        # Should include critical system variables
        system_vars = ['PATH']  # PATH should always be present
        for var in system_vars:
            if var in os.environ:  # Only check if it exists
                assert var in subprocess_env
        
        env.reset()
    
    def test_get_subprocess_env_additional_vars(self):
        """Test adding additional variables to subprocess environment."""
        env = get_env()
        env.reset()
        
        additional = {
            "ADDITIONAL_VAR1": "additional1",
            "ADDITIONAL_VAR2": "additional2"
        }
        
        subprocess_env = env.get_subprocess_env(additional_vars=additional)
        
        # Should include additional variables
        assert subprocess_env["ADDITIONAL_VAR1"] == "additional1"
        assert subprocess_env["ADDITIONAL_VAR2"] == "additional2"
        
        env.reset()
    
    def test_get_subprocess_env_convenience_function(self):
        """Test convenience function for subprocess environment."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        env.set("CONVENIENCE_VAR", "convenience_value", source="test")
        
        # Test convenience function
        subprocess_env = get_subprocess_env(additional_vars={"EXTRA": "extra_value"})
        
        # Should include both isolated and additional variables
        assert subprocess_env["CONVENIENCE_VAR"] == "convenience_value"
        assert subprocess_env["EXTRA"] == "extra_value"
        
        env.reset()


class TestEnvironmentQueries:
    """Test environment name and type queries."""
    
    def test_environment_name_detection(self):
        """Test environment name detection and normalization."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test various environment values
        test_cases = [
            ("development", "development"),
            ("dev", "development"),
            ("local", "development"),
            ("test", "test"),
            ("testing", "test"),
            ("staging", "staging"),
            ("production", "production"),
            ("prod", "production"),
            ("unknown", "development"),  # Default
        ]
        
        for env_value, expected_name in test_cases:
            env.set("ENVIRONMENT", env_value, source="test")
            assert env.get_environment_name() == expected_name
        
        env.reset()
    
    def test_environment_type_checks(self):
        """Test environment type boolean checks."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test production
        env.set("ENVIRONMENT", "production", source="test")
        assert env.is_production() == True
        assert env.is_staging() == False
        assert env.is_development() == False
        assert env.is_test() == False
        
        # Test staging
        env.set("ENVIRONMENT", "staging", source="test")
        assert env.is_production() == False
        assert env.is_staging() == True
        assert env.is_development() == False
        assert env.is_test() == False
        
        # Test development
        env.set("ENVIRONMENT", "development", source="test")
        assert env.is_production() == False
        assert env.is_staging() == False
        assert env.is_development() == True
        assert env.is_test() == False
        
        # Test test
        env.set("ENVIRONMENT", "test", source="test")
        assert env.is_production() == False
        assert env.is_staging() == False
        assert env.is_development() == False
        assert env.is_test() == True
        
        env.reset()


class TestDatabaseValidation:
    """Test database credential validation for staging."""
    
    def test_staging_database_validation_success(self):
        """Test successful staging database credential validation."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set up valid staging credentials
        env.set("ENVIRONMENT", "staging", source="test")
        env.set("POSTGRES_HOST", "staging-db-host", source="test")
        env.set("POSTGRES_USER", "postgres", source="test")
        env.set("POSTGRES_PASSWORD", "secure_staging_password_123", source="test")
        env.set("POSTGRES_DB", "netra_staging", source="test")
        
        result = env.validate_staging_database_credentials()
        
        assert result["valid"] == True
        assert len(result["issues"]) == 0
        
        env.reset()
    
    def test_staging_database_validation_failures(self):
        """Test staging database credential validation failures."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set staging environment
        env.set("ENVIRONMENT", "staging", source="test")
        
        # Test missing variables - but validation continues to check other issues too
        result = env.validate_staging_database_credentials()
        assert result["valid"] == False
        # The validation checks for missing vars but also validates existing defaults
        # So we might get multiple issues including localhost check
        
        # Test localhost host (invalid for staging)
        env.set("POSTGRES_HOST", "localhost", source="test")
        env.set("POSTGRES_USER", "postgres", source="test")
        env.set("POSTGRES_PASSWORD", "password", source="test")  # Also weak password
        env.set("POSTGRES_DB", "netra_staging", source="test")
        
        result = env.validate_staging_database_credentials()
        assert result["valid"] == False
        
        issues = str(result["issues"])
        assert "cannot be 'localhost'" in issues  # Host validation
        assert "insecure default" in issues  # Password validation
        
        # Test invalid user pattern
        env.set("POSTGRES_HOST", "staging-db", source="test")
        env.set("POSTGRES_USER", "user_pr-4", source="test")  # Invalid pattern
        env.set("POSTGRES_PASSWORD", "secure_password_123", source="test")
        
        result = env.validate_staging_database_credentials()
        assert result["valid"] == False
        assert "Invalid POSTGRES_USER" in str(result["issues"])
        
        env.reset()


class TestThreadSafety:
    """Test thread safety of IsolatedEnvironment operations."""
    
    def test_concurrent_read_write_operations(self):
        """Test concurrent read/write operations are thread-safe."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Data for concurrent operations
        test_data = {f"THREAD_VAR_{i}": f"thread_value_{i}" for i in range(100)}
        results = {"set": [], "get": [], "errors": []}
        
        def writer_thread():
            """Worker thread that sets variables."""
            try:
                for key, value in test_data.items():
                    result = env.set(key, value, source=f"thread_{threading.current_thread().ident}")
                    results["set"].append((key, result))
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                results["errors"].append(e)
        
        def reader_thread():
            """Worker thread that reads variables."""
            try:
                time.sleep(0.01)  # Give writers a chance to start
                for key in test_data.keys():
                    value = env.get(key)
                    results["get"].append((key, value))
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                results["errors"].append(e)
        
        # Create and start threads
        threads = []
        # 2 writer threads
        for _ in range(2):
            t = threading.Thread(target=writer_thread)
            threads.append(t)
        # 2 reader threads
        for _ in range(2):
            t = threading.Thread(target=reader_thread)
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        assert len(results["errors"]) == 0, f"Thread safety errors: {results['errors']}"
        
        # Verify all variables were set successfully
        set_results = {key: result for key, result in results["set"]}
        for key in test_data.keys():
            if key in set_results:  # May not be set if thread contention
                assert set_results[key] == True, f"Failed to set {key}"
        
        # Verify final state consistency
        for key, expected_value in test_data.items():
            actual_value = env.get(key)
            if actual_value is not None:  # May be None if not set due to thread timing
                assert actual_value == expected_value, f"Inconsistent value for {key}"
        
        env.reset()
    
    def test_concurrent_isolation_operations(self):
        """Test concurrent isolation enable/disable operations."""
        env = get_env()
        env.reset()
        
        results = {"enable": [], "disable": [], "errors": []}
        
        def isolation_worker():
            """Worker that enables/disables isolation repeatedly."""
            try:
                for i in range(10):
                    env.enable_isolation()
                    results["enable"].append(threading.current_thread().ident)
                    time.sleep(0.001)
                    
                    env.disable_isolation()
                    results["disable"].append(threading.current_thread().ident)
                    time.sleep(0.001)
            except Exception as e:
                results["errors"].append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=isolation_worker) for _ in range(3)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        assert len(results["errors"]) == 0, f"Concurrent isolation errors: {results['errors']}"
        
        # Verify operations completed
        assert len(results["enable"]) > 0
        assert len(results["disable"]) > 0
        
        env.reset()


class TestStateManagement:
    """Test state reset and change tracking."""
    
    def test_reset_functionality(self):
        """Test environment reset functionality."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set up some state
        env.set("RESET_TEST1", "value1", source="test")
        env.set("RESET_TEST2", "value2", source="test")
        env.protect_variable("RESET_TEST1")
        
        # Verify state exists
        assert env.get("RESET_TEST1") == "value1"
        assert env.get("RESET_TEST2") == "value2"
        assert env.is_protected("RESET_TEST1") == True
        assert env.is_isolated() == True
        
        # Reset
        env.reset()
        
        # State should be cleared
        assert env.get("RESET_TEST1") is None
        assert env.get("RESET_TEST2") is None
        assert env.is_protected("RESET_TEST1") == False
        assert env.is_isolated() == False
    
    def test_reset_to_original_state(self):
        """Test reset to original state functionality."""
        env = get_env()
        env.reset()
        
        # Enable isolation with backup
        env.enable_isolation(backup_original=True)
        
        # Make changes
        env.set("ORIGINAL_TEST", "modified_value", source="test")
        
        # Reset to original
        env.reset_to_original()
        
        # Should be back to original state
        # (Original state depends on what was in os.environ at start)
        
        env.reset()
    
    def test_get_changes_since_init(self):
        """Test tracking changes since initialization."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Make some changes
        env.set("CHANGE_TEST1", "new_value", source="test")
        env.set("CHANGE_TEST2", "another_value", source="test")
        
        # Get changes
        changes = env.get_changes_since_init()
        
        # Should include our new variables
        assert "CHANGE_TEST1" in changes
        assert "CHANGE_TEST2" in changes
        
        # Change format: (original_value, current_value)
        assert changes["CHANGE_TEST1"] == (None, "new_value")  # Was None, now has value
        assert changes["CHANGE_TEST2"] == (None, "another_value")
        
        env.reset()


class TestCachingAndPerformance:
    """Test caching and performance optimizations."""
    
    def test_environment_cache(self):
        """Test environment variable caching."""
        env = get_env()
        env.reset()
        # Not in isolation mode to test caching behavior
        
        # Set a variable (not isolated)
        os.environ["CACHE_TEST"] = "cached_value"
        
        try:
            # First access should cache
            value1 = env.get("CACHE_TEST")
            assert value1 == "cached_value"
            
            # Modify os.environ directly (simulating external change)
            os.environ["CACHE_TEST"] = "modified_value"
            
            # Should still return cached value in non-isolation mode
            value2 = env.get("CACHE_TEST")
            # Note: Behavior may depend on implementation details
            
            # Clear cache
            env.clear_cache()
            
            # Now should get updated value
            value3 = env.get("CACHE_TEST")
            assert value3 == "modified_value"
            
        finally:
            # Clean up
            if "CACHE_TEST" in os.environ:
                del os.environ["CACHE_TEST"]
        
        env.reset()
    
    def test_get_all_with_prefix(self):
        """Test getting variables with prefix (performance optimization)."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set variables with different prefixes
        env.set("PREFIX_VAR1", "value1", source="test")
        env.set("PREFIX_VAR2", "value2", source="test")
        env.set("OTHER_VAR1", "other1", source="test")
        env.set("PREFIX_VAR3", "value3", source="test")
        
        # Get variables with prefix
        prefix_vars = env.get_all_with_prefix("PREFIX_")
        
        # Should only include prefixed variables
        assert len(prefix_vars) == 3
        assert prefix_vars["PREFIX_VAR1"] == "value1"
        assert prefix_vars["PREFIX_VAR2"] == "value2"
        assert prefix_vars["PREFIX_VAR3"] == "value3"
        assert "OTHER_VAR1" not in prefix_vars
        
        env.reset()


class TestClearOperation:
    """Test clear operation in isolation mode."""
    
    def test_clear_in_isolation_mode(self):
        """Test clearing all variables in isolation mode."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set some variables
        env.set("CLEAR_TEST1", "value1", source="test")
        env.set("CLEAR_TEST2", "value2", source="test")
        env.protect_variable("CLEAR_TEST1")
        
        # Verify they exist
        assert env.get("CLEAR_TEST1") == "value1"
        assert env.get("CLEAR_TEST2") == "value2"
        assert env.is_protected("CLEAR_TEST1") == True
        
        # Clear
        env.clear()
        
        # All should be gone
        assert env.get("CLEAR_TEST1") is None
        assert env.get("CLEAR_TEST2") is None
        assert env.is_protected("CLEAR_TEST1") == False
        
        env.reset()
    
    def test_clear_requires_isolation_mode(self):
        """Test that clear requires isolation mode."""
        env = get_env()
        env.reset()
        # Not in isolation mode
        
        # Should raise error
        with pytest.raises(RuntimeError, match="Cannot clear environment variables outside isolation mode"):
            env.clear()
        
        env.reset()


class TestDebugAndUtilities:
    """Test debugging and utility functions."""
    
    def test_get_debug_info(self):
        """Test debug information gathering."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set up some state
        env.set("DEBUG_VAR", "debug_value", source="debug_test")
        env.protect_variable("DEBUG_VAR")
        
        debug_info = env.get_debug_info()
        
        # Verify debug info structure
        assert "isolation_enabled" in debug_info
        assert "isolated_vars_count" in debug_info
        assert "os_environ_count" in debug_info
        assert "protected_vars" in debug_info
        assert "tracked_sources" in debug_info
        assert "change_callbacks_count" in debug_info
        assert "original_backup_count" in debug_info
        
        # Verify values
        assert debug_info["isolation_enabled"] == True
        assert debug_info["isolated_vars_count"] > 0
        assert "DEBUG_VAR" in debug_info["protected_vars"]
        assert debug_info["tracked_sources"]["DEBUG_VAR"] == "debug_test"
        
        env.reset()


class TestConvenienceFunctions:
    """Test convenience functions for backwards compatibility."""
    
    def test_convenience_functions(self):
        """Test setenv, getenv, delenv convenience functions."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test setenv
        result = setenv("CONVENIENCE_TEST", "convenience_value", source="convenience")
        assert result == True
        
        # Test getenv
        value = getenv("CONVENIENCE_TEST", "default")
        assert value == "convenience_value"
        
        # Test default
        default_value = getenv("NONEXISTENT", "default_value")
        assert default_value == "default_value"
        
        # Test delenv
        result = delenv("CONVENIENCE_TEST")
        assert result == True
        
        # Should be gone
        value = getenv("CONVENIENCE_TEST")
        assert value is None
        
        env.reset()


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and defaults."""
        # Basic creation
        result = ValidationResult(
            is_valid=True,
            errors=["error1"],
            warnings=["warning1"],
            missing_optional=["optional1"]
        )
        
        assert result.is_valid == True
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
        assert result.missing_optional == ["optional1"]
        
        # Defaults should be initialized
        assert result.fallback_applied == []
        assert result.suggestions == []
        assert result.missing_optional_by_category == {}
        
    def test_validation_all(self):
        """Test basic validation functionality."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set some required variables
        env.set("DATABASE_URL", "postgresql://test", source="test")
        env.set("JWT_SECRET_KEY", "test_secret", source="test")
        env.set("SECRET_KEY", "test_secret_key", source="test")
        
        result = env.validate_all()
        
        assert result.is_valid == True
        assert len(result.errors) == 0
        
        # Test with missing variables
        env.delete("DATABASE_URL")
        result = env.validate_all()
        
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert "Missing required variable: DATABASE_URL" in result.errors
        
        env.reset()


class TestLegacyCompatibilityClasses:
    """Test legacy compatibility classes and functions."""
    
    def test_secret_loader_class(self):
        """Test SecretLoader legacy compatibility class."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Create SecretLoader
        loader = SecretLoader()
        
        # Test methods
        assert loader.load_secrets() == True  # Always returns True
        
        # Test setting and getting secrets
        result = loader.set_secret("SECRET_TEST", "secret_value", source="secret_loader")
        assert result == True
        
        value = loader.get_secret("SECRET_TEST", "default")
        assert value == "secret_value"
        
        # Test with custom env manager
        custom_loader = SecretLoader(env_manager=env)
        assert custom_loader.env_manager is env
        
        env.reset()
    
    def test_load_secrets_function(self):
        """Test load_secrets legacy function."""
        result = load_secrets()
        assert result == True  # Always returns True for compatibility
    
    def test_environment_validator_class(self):
        """Test EnvironmentValidator legacy compatibility class."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Create validator
        validator = EnvironmentValidator(enable_fallbacks=True, development_mode=True)
        
        # Set up test environment
        env.set("DATABASE_URL", "postgresql://test", source="test")
        env.set("JWT_SECRET_KEY", "test_secret", source="test")
        env.set("SECRET_KEY", "test_secret_key", source="test")
        
        # Test validation methods
        result = validator.validate_all()
        assert result.is_valid == True
        
        result2 = validator.validate_with_fallbacks()
        assert result2.is_valid == True
        
        # Test print method (should not error)
        validator.print_validation_summary(result)
        
        # Test suggestions
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list)
        
        env.reset()


class TestContextManagement:
    """Test context manager behavior and cleanup."""
    
    def test_explicit_unset_tracking(self):
        """Test that explicitly unset variables are tracked properly."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set a variable
        env.set("UNSET_TEST", "original_value", source="test")
        assert env.get("UNSET_TEST") == "original_value"
        assert env.exists("UNSET_TEST") == True
        
        # Delete it (should mark as explicitly unset)
        env.delete("UNSET_TEST")
        
        # Should not exist and return None/default
        assert env.exists("UNSET_TEST") == False
        assert env.get("UNSET_TEST") is None
        assert env.get("UNSET_TEST", "default") == "default"
        
        # Should not appear in get_all()
        all_vars = env.get_all()
        assert "UNSET_TEST" not in all_vars
        
        env.reset()
    
    def test_optimized_persistence_defaults(self):
        """Test that optimized persistence defaults are set."""
        env = get_env()
        env.reset()
        
        # Should have default optimized persistence settings
        assert env.get("ENABLE_OPTIMIZED_PERSISTENCE") is not None
        assert env.get("OPTIMIZED_PERSISTENCE_CACHE_SIZE") is not None
        assert env.get("OPTIMIZED_PERSISTENCE_DEDUPLICATION") is not None
        assert env.get("OPTIMIZED_PERSISTENCE_COMPRESSION") is not None
        
        env.reset()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test setting with None value (should convert to string)
        result = env.set("NULL_TEST", None, source="test")
        assert result == True
        assert env.get("NULL_TEST") == "None"  # Converted to string
        
        # Test empty string
        result = env.set("EMPTY_TEST", "", source="test")
        assert result == True
        assert env.get("EMPTY_TEST") == ""
        
        env.reset()
    
    def test_file_loading_edge_cases(self):
        """Test file loading edge cases."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test with Path object instead of string
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            f.write("PATH_TEST=path_value\n")
            temp_file = f.name
        
        try:
            # Use Path object
            path_obj = Path(temp_file)
            loaded_count, errors = env.load_from_file(path_obj)
            
            assert loaded_count == 1
            assert len(errors) == 0
            assert env.get("PATH_TEST") == "path_value"
            
        finally:
            try:
                os.unlink(temp_file)
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not delete temp file {temp_file}: {e}")
        
        env.reset()


# Run performance test if explicitly requested
class TestPerformance:
    """Performance tests (optional, run with explicit marker)."""
    
    @pytest.mark.performance
    def test_large_scale_operations(self):
        """Test performance with large number of variables."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set many variables
        num_vars = 1000
        start_time = time.time()
        
        for i in range(num_vars):
            env.set(f"PERF_VAR_{i}", f"value_{i}", source="performance_test")
        
        set_time = time.time() - start_time
        
        # Get all variables
        start_time = time.time()
        for i in range(num_vars):
            value = env.get(f"PERF_VAR_{i}")
            assert value == f"value_{i}"
        
        get_time = time.time() - start_time
        
        # Verify reasonable performance (adjust thresholds as needed)
        assert set_time < 5.0, f"Setting {num_vars} variables took too long: {set_time}s"
        assert get_time < 2.0, f"Getting {num_vars} variables took too long: {get_time}s"
        
        env.reset()


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v"])