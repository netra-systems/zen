from shared.isolated_environment import get_env
"""
env = get_env()
Tests for IsolatedEnvironment class.

Comprehensive tests to verify:
1. Isolation mode prevents os.environ pollution
2. Environment variable management works correctly  
3. Backwards compatibility is maintained
4. Thread safety
5. Source tracking and debugging features
"""

import os
import pytest
import threading
import tempfile
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment, get_env, setenv, getenv, delenv


class TestIsolatedEnvironmentBasics:
    """Test basic IsolatedEnvironment functionality."""
    
    def test_singleton_pattern(self):
        """Test that IsolatedEnvironment follows singleton pattern."""
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment()
        env3 = get_env()
        
        assert env1 is env2
        assert env2 is env3
    
    def test_isolation_disabled_by_default(self):
        """Test that isolation is disabled by default."""
        env = IsolatedEnvironment()
        assert not env.is_isolation_enabled()
    
    def test_enable_disable_isolation(self):
        """Test enabling and disabling isolation mode."""
        env = IsolatedEnvironment()
        original_state = env.is_isolation_enabled()
        
        # Enable isolation
        env.enable_isolation()
        assert env.is_isolation_enabled()
        
        # Disable isolation
        env.disable_isolation()
        assert not env.is_isolation_enabled()
        
        # Restore original state for other tests
        if original_state:
            env.enable_isolation()
    
    def test_basic_get_set_operations(self):
        """Test basic get/set operations."""
        env = IsolatedEnvironment()
        
        # Test setting and getting
        success = env.set("TEST_VAR_BASIC", "test_value", "test_source")
        assert success
        assert env.get("TEST_VAR_BASIC") == "test_value"
        
        # Test default value
        assert env.get("NONEXISTENT_VAR", "default") == "default"
        assert env.get("NONEXISTENT_VAR") is None
    
    def test_delete_operation(self):
        """Test delete operation."""
        env = IsolatedEnvironment()
        
        # Set a variable
        env.set("TEST_VAR_DELETE", "delete_me", "test_source")
        assert env.get("TEST_VAR_DELETE") == "delete_me"
        
        # Delete it
        success = env.delete("TEST_VAR_DELETE", "test_delete")
        assert success
        assert env.get("TEST_VAR_DELETE") is None
        
        # Try to delete non-existent
        success = env.delete("NONEXISTENT_VAR", "test_delete")
        assert not success
    
    def test_bulk_update(self):
        """Test bulk update functionality."""
        env = IsolatedEnvironment()
        
        variables = {
            "BULK_VAR_1": "value1",
            "BULK_VAR_2": "value2", 
            "BULK_VAR_3": "value3"
        }
        
        results = env.update(variables, "bulk_test")
        
        # All should succeed
        assert all(results.values())
        
        # Verify values
        for key, expected_value in variables.items():
            assert env.get(key) == expected_value


class TestIsolatedEnvironmentIsolation:
    """Test isolation mode functionality."""
    
    def test_isolation_mode_prevents_os_environ_pollution(self):
        """Test that isolation mode prevents pollution of os.environ."""
        env = IsolatedEnvironment()
        
        # Store original state
        original_os_vars = env.get_all()
        
        # Enable isolation
        env.enable_isolation(backup_original=True)
        
        try:
            # Set variables in isolation mode
            env.set("ISOLATED_TEST_VAR", "isolated_value", "isolation_test")
            env.set("ANOTHER_ISOLATED_VAR", "another_value", "isolation_test")
            
            # Variables should be accessible through isolated environment
            assert env.get("ISOLATED_TEST_VAR") == "isolated_value" 
            assert env.get("ANOTHER_ISOLATED_VAR") == "another_value"
            
            # But os.environ should not be polluted (these should not exist in os.environ)
            assert "ISOLATED_TEST_VAR" not in os.environ
            assert "ANOTHER_ISOLATED_VAR" not in os.environ
            
        finally:
            # Restore original environment
            env.disable_isolation(restore_original=True)
            
            # Verify os.environ is clean
            current_os_vars = env.get_all()
            
            # Should have same variables as before
            assert "ISOLATED_TEST_VAR" not in current_os_vars
            assert "ANOTHER_ISOLATED_VAR" not in current_os_vars
    
    def test_isolation_mode_with_existing_variables(self):
        """Test isolation mode behavior with existing os.environ variables."""
        # Set some variables in os.environ first
        env.set("EXISTING_VAR", "original_value", "test")
        
        try:
            env = IsolatedEnvironment()
            
            # Enable isolation - should copy existing vars
            env.enable_isolation(backup_original=True)
            
            # Should be able to access existing variables
            assert env.get("EXISTING_VAR") == "original_value"
            
            # Should be able to modify them in isolation
            env.set("EXISTING_VAR", "modified_value", "isolation_test")
            assert env.get("EXISTING_VAR") == "modified_value"
            
            # But os.environ should still have original value
            assert env.get("EXISTING_VAR") == "original_value"
            
            # Disable isolation without restore - should sync to os.environ
            env.disable_isolation(restore_original=False)
            
            # Now os.environ should have the modified value
            assert env.get("EXISTING_VAR") == "modified_value"
            
        finally:
            # Clean up
            env.delete("EXISTING_VAR", "test")
    
    def test_subprocess_environment(self):
        """Test subprocess environment functionality."""
        env = IsolatedEnvironment()
        
        # Enable isolation
        env.enable_isolation()
        
        try:
            # Set some isolated variables
            env.set("SUBPROCESS_VAR_1", "value1", "subprocess_test")
            env.set("SUBPROCESS_VAR_2", "value2", "subprocess_test")
            
            # Get subprocess environment
            subprocess_env = env.get_subprocess_env()
            
            # Should contain isolated variables
            assert subprocess_env["SUBPROCESS_VAR_1"] == "value1"
            assert subprocess_env["SUBPROCESS_VAR_2"] == "value2"
            
            # Test with additional variables
            additional = {"EXTRA_VAR": "extra_value"}
            subprocess_env = env.get_subprocess_env(additional)
            assert subprocess_env["EXTRA_VAR"] == "extra_value"
            assert subprocess_env["SUBPROCESS_VAR_1"] == "value1"
            
        finally:
            env.disable_isolation()


class TestIsolatedEnvironmentProtection:
    """Test variable protection functionality."""
    
    def test_protected_variables(self):
        """Test variable protection mechanism."""
        env = IsolatedEnvironment()
        
        # Set a variable
        env.set("PROTECTED_VAR", "original_value", "protection_test")
        
        # Protect it
        env.protect_variable("PROTECTED_VAR")
        assert env.is_protected("PROTECTED_VAR")
        
        # Try to modify (should fail)
        success = env.set("PROTECTED_VAR", "new_value", "attacker", force=False)
        assert not success
        assert env.get("PROTECTED_VAR") == "original_value"
        
        # Force modification (should succeed)
        success = env.set("PROTECTED_VAR", "forced_value", "admin", force=True)
        assert success
        assert env.get("PROTECTED_VAR") == "forced_value"
        
        # Unprotect
        env.unprotect_variable("PROTECTED_VAR")
        assert not env.is_protected("PROTECTED_VAR")
        
        # Now normal modification should work
        success = env.set("PROTECTED_VAR", "unprotected_value", "normal_user")
        assert success
        assert env.get("PROTECTED_VAR") == "unprotected_value"


class TestIsolatedEnvironmentFileOperations:
    """Test file loading functionality."""
    
    def test_load_from_file(self):
        """Test loading environment variables from .env file."""
        env = IsolatedEnvironment()
        
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# Test .env file\n")
            f.write("FILE_VAR_1=value1\n")
            f.write("FILE_VAR_2=value2\n")
            f.write("FILE_VAR_3='quoted value'\n")
            f.write('FILE_VAR_4="double quoted"\n')
            f.write("# Comment line\n")
            f.write("\n")  # Empty line
            f.write("INVALID_LINE_NO_EQUALS\n")  # Invalid line
            env_file_path = Path(f.name)
        
        try:
            # Load from file
            loaded_count, errors = env.load_from_file(env_file_path, "test_file")
            
            # Should load 4 valid variables
            assert loaded_count == 4
            assert len(errors) == 1  # One invalid line
            
            # Check values
            assert env.get("FILE_VAR_1") == "value1"
            assert env.get("FILE_VAR_2") == "value2"
            assert env.get("FILE_VAR_3") == "quoted value"
            assert env.get("FILE_VAR_4") == "double quoted"
            
            # Check source tracking
            assert env.get_variable_source("FILE_VAR_1") == "test_file"
            
        finally:
            # Clean up
            env_file_path.unlink()
    
    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file."""
        env = IsolatedEnvironment()
        
        non_existent = Path("/nonexistent/path/file.env")
        loaded_count, errors = env.load_from_file(non_existent, "missing_file")
        
        assert loaded_count == 0
        assert len(errors) == 1
        assert "not found" in errors[0].lower()


class TestIsolatedEnvironmentThreadSafety:
    """Test thread safety of IsolatedEnvironment."""
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        env = IsolatedEnvironment()
        results = []
        errors = []
        
        def worker_thread(thread_id: int):
            try:
                # Each thread sets its own variables
                for i in range(10):
                    key = f"THREAD_{thread_id}_VAR_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    success = env.set(key, value, f"thread_{thread_id}")
                    results.append((thread_id, key, success))
                    
                    # Verify we can read it back immediately
                    read_value = env.get(key)
                    assert read_value == value, f"Thread {thread_id}: Expected {value}, got {read_value}"
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all to complete
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 50  # 5 threads * 10 variables each
        
        # Verify all variables are accessible
        for thread_id in range(5):
            for i in range(10):
                key = f"THREAD_{thread_id}_VAR_{i}"
                expected_value = f"thread_{thread_id}_value_{i}"
                assert env.get(key) == expected_value


class TestIsolatedEnvironmentCallbacks:
    """Test change callback functionality."""
    
    def test_change_callbacks(self):
        """Test change notification callbacks."""
        env = IsolatedEnvironment()
        callback_events = []
        
        def change_callback(key: str, old_value: str, new_value: str):
            callback_events.append((key, old_value, new_value))
        
        # Add callback
        env.add_change_callback(change_callback)
        
        # Set a variable
        env.set("CALLBACK_VAR", "value1", "callback_test")
        assert len(callback_events) == 1
        assert callback_events[0] == ("CALLBACK_VAR", None, "value1")
        
        # Modify the variable
        env.set("CALLBACK_VAR", "value2", "callback_test", force=True)
        assert len(callback_events) == 2
        assert callback_events[1] == ("CALLBACK_VAR", "value1", "value2")
        
        # Delete the variable
        env.delete("CALLBACK_VAR", "callback_test")
        assert len(callback_events) == 3
        assert callback_events[2] == ("CALLBACK_VAR", "value2", None)
        
        # Remove callback
        env.remove_change_callback(change_callback)
        
        # Further changes should not trigger callback
        env.set("CALLBACK_VAR", "value3", "callback_test")
        assert len(callback_events) == 3  # No new events


class TestIsolatedEnvironmentUtilityFunctions:
    """Test utility and debug functions."""
    
    def test_get_all_variables(self):
        """Test getting all environment variables."""
        env = IsolatedEnvironment()
        
        # Set some test variables
        test_vars = {
            "GET_ALL_VAR_1": "value1",
            "GET_ALL_VAR_2": "value2",
            "GET_ALL_VAR_3": "value3"
        }
        
        for key, value in test_vars.items():
            env.set(key, value, "get_all_test")
        
        # Get all variables
        all_vars = env.get_all()
        
        # Should contain our test variables
        for key, value in test_vars.items():
            assert key in all_vars
            assert all_vars[key] == value
    
    def test_changes_since_init(self):
        """Test tracking changes since initialization."""
        env = IsolatedEnvironment()
        
        # Set a new variable
        env.set("NEW_CHANGE_VAR", "new_value", "changes_test")
        
        # Modify an existing variable (if any exist)
        original_path = env.get("PATH", "")
        if original_path:
            env.set("PATH", original_path + ";test_addition", "changes_test")
        
        # Get changes
        changes = env.get_changes_since_init()
        
        # Should include our new variable
        assert "NEW_CHANGE_VAR" in changes
        assert changes["NEW_CHANGE_VAR"] == (None, "new_value")
        
        if original_path:
            assert "PATH" in changes
            assert changes["PATH"][0] == original_path
    
    def test_debug_info(self):
        """Test debug information functionality."""
        env = IsolatedEnvironment()
        
        # Set some variables and enable features
        env.set("DEBUG_VAR", "debug_value", "debug_test")
        env.protect_variable("DEBUG_VAR")
        
        debug_info = env.get_debug_info()
        
        # Check debug info structure
        assert "isolation_enabled" in debug_info
        assert "protected_vars" in debug_info
        assert "tracked_sources" in debug_info
        
        # Check content
        assert "DEBUG_VAR" in debug_info["protected_vars"]
        assert "DEBUG_VAR" in debug_info["tracked_sources"]
        assert debug_info["tracked_sources"]["DEBUG_VAR"] == "debug_test"
    
    def test_reset_to_original(self):
        """Test reset to original state."""
        env = IsolatedEnvironment()
        
        # Make some changes
        env.set("RESET_TEST_VAR", "will_be_reset", "reset_test")
        
        # Verify change exists
        assert env.get("RESET_TEST_VAR") == "will_be_reset"
        
        # Reset to original
        env.reset_to_original()
        
        # Variable should be gone
        assert env.get("RESET_TEST_VAR") is None


class TestBackwardsCompatibilityFunctions:
    """Test backwards compatibility functions."""
    
    def test_global_functions(self):
        """Test global convenience functions."""
        # Test setenv
        success = setenv("COMPAT_VAR", "compat_value", "compat_test")
        assert success
        
        # Test getenv
        value = getenv("COMPAT_VAR", "default")
        assert value == "compat_value"
        
        # Test default
        default_value = getenv("NONEXISTENT_COMPAT", "default")
        assert default_value == "default"
        
        # Test delenv
        success = delenv("COMPAT_VAR")
        assert success
        
        # Should be gone
        value = getenv("COMPAT_VAR")
        assert value is None


class TestIsolatedEnvironmentEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_values(self):
        """Test handling of empty values."""
        env = IsolatedEnvironment()
        
        # Set empty string
        env.set("EMPTY_VAR", "", "empty_test")
        assert env.get("EMPTY_VAR") == ""
        
        # Empty string should not be None
        assert env.get("EMPTY_VAR") is not None
    
    def test_large_values(self):
        """Test handling of large values."""
        env = IsolatedEnvironment()
        
        # Create a large value
        large_value = "x" * 10000
        env.set("LARGE_VAR", large_value, "large_test")
        
        # Should be able to retrieve it
        assert env.get("LARGE_VAR") == large_value
        assert len(env.get("LARGE_VAR")) == 10000
    
    def test_special_characters_in_values(self):
        """Test handling of special characters in values."""
        env = IsolatedEnvironment()
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        unicode_chars = " FIRE: [U+2728] LIGHTNING: [U+FE0F][U+1F680]"
        mixed_value = f"Special: {special_chars} Unicode: {unicode_chars}"
        
        env.set("SPECIAL_VAR", mixed_value, "special_test")
        assert env.get("SPECIAL_VAR") == mixed_value
    
    def test_callback_exceptions(self):
        """Test handling of exceptions in callbacks."""
        env = IsolatedEnvironment()
        
        def faulty_callback(key: str, old_value: str, new_value: str):
            raise ValueError("Callback error")
        
        # Add faulty callback
        env.add_change_callback(faulty_callback)
        
        # Setting variable should not fail even if callback does
        success = env.set("CALLBACK_ERROR_VAR", "value", "error_test")
        assert success
        assert env.get("CALLBACK_ERROR_VAR") == "value"


# Integration tests
class TestIsolatedEnvironmentIntegration:
    """Integration tests with existing system."""
    
    def test_integration_with_os_environ(self):
        """Test integration with existing os.environ usage."""
        env = IsolatedEnvironment()
        
        # Existing variable in os.environ
        original_path = env.get("PATH", "")
        
        # Should be accessible through isolated environment
        assert env.get("PATH") == original_path
        
        # Modify through isolated environment
        new_path = original_path + ";test_integration"
        env.set("PATH", new_path, "integration_test")
        
        # Should be reflected in os.environ (when not in isolation mode)
        if not env.is_isolation_enabled():
            assert env.get("PATH") == new_path
        
        # Restore original
        if original_path:
            env.set("PATH", original_path, "integration_restore")
        else:
            env.delete("PATH", "integration_restore")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])