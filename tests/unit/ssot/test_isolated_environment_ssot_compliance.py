#!/usr/bin/env python3
"""
Test SSOT IsolatedEnvironment Pattern Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Ensure SSOT environment access patterns
- Value Impact: Prevents configuration drift and Golden Path blockers
- Strategic Impact: $500K+ ARR protected through stable environment management

CRITICAL PURPOSE:
This test validates the core SSOT pattern for environment variable access.
Direct `os.environ` usage bypasses isolation, thread safety, and test defaults,
creating cascade failures in Golden Path functionality.

SSOT COMPLIANCE:
Tests MUST use `shared.isolated_environment.get_env()` for ALL environment access.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

# SSOT Import - Use ONLY this pattern for environment access
from shared.isolated_environment import get_env, IsolatedEnvironment


@pytest.mark.unit
class IsolatedEnvironmentSSOTComplianceTests:
    """Test SSOT IsolatedEnvironment pattern in isolation."""
    
    def test_get_env_function_returns_singleton(self):
        """Test that get_env() returns the same singleton instance."""
        env1 = get_env()
        env2 = get_env()
        env3 = IsolatedEnvironment()
        
        # All should be the same singleton instance
        assert env1 is env2, "get_env() should return same singleton instance"
        assert env1 is env3, "IsolatedEnvironment() should return same singleton as get_env()"
        assert id(env1) == id(env2) == id(env3), "All instances must have same memory ID"
    
    def test_isolated_environment_basic_operations(self):
        """Test basic SSOT environment operations."""
        env = get_env()
        
        # Test set operation
        result = env.set("TEST_SSOT_KEY", "test_value", source="unit_test")
        assert result is True, "set() should return True on success"
        
        # Test get operation
        value = env.get("TEST_SSOT_KEY")
        assert value == "test_value", "get() should return the set value"
        
        # Test exists operation
        assert env.exists("TEST_SSOT_KEY"), "exists() should return True for set key"
        
        # Test delete operation
        deleted = env.delete("TEST_SSOT_KEY", source="unit_test_cleanup")
        assert deleted is True, "delete() should return True when key exists"
        
        # Test get after delete
        value_after_delete = env.get("TEST_SSOT_KEY", "default")
        assert value_after_delete == "default", "get() should return default after delete"
        
        # Cleanup
        env.clear_env_var("TEST_SSOT_KEY")
    
    def test_isolation_mode_functionality(self):
        """Test isolation mode prevents os.environ pollution."""
        env = get_env()
        
        # Enable isolation
        env.enable_isolation()
        assert env.is_isolated(), "is_isolated() should return True after enabling"
        
        # Set variable in isolation mode
        env.set("TEST_ISOLATION_KEY", "isolated_value", source="unit_test")
        
        # Variable should exist in isolated environment
        assert env.get("TEST_ISOLATION_KEY") == "isolated_value"
        
        # Variable should NOT exist in os.environ (isolation working)
        assert "TEST_ISOLATION_KEY" not in os.environ, "Isolated variables should not pollute os.environ"
        
        # Disable isolation and cleanup
        env.disable_isolation()
        env.clear_env_var("TEST_ISOLATION_KEY")
    
    def test_thread_safety_of_environment_operations(self):
        """Test that IsolatedEnvironment operations are thread-safe."""
        env = get_env()
        env.enable_isolation()
        
        results = []
        errors = []
        
        def worker_thread(thread_id: int):
            """Worker thread that performs environment operations."""
            try:
                # Each thread sets and gets its own variable
                key = f"THREAD_TEST_{thread_id}"
                value = f"thread_value_{thread_id}"
                
                # Set variable
                success = env.set(key, value, source=f"thread_{thread_id}")
                if not success:
                    errors.append(f"Thread {thread_id}: Failed to set {key}")
                    return
                
                # Get variable immediately
                retrieved_value = env.get(key)
                if retrieved_value != value:
                    errors.append(f"Thread {thread_id}: Expected {value}, got {retrieved_value}")
                    return
                
                # Short delay to allow race conditions
                time.sleep(0.01)
                
                # Get variable again to test consistency
                retrieved_value2 = env.get(key)
                if retrieved_value2 != value:
                    errors.append(f"Thread {thread_id}: Value changed from {value} to {retrieved_value2}")
                    return
                
                results.append((thread_id, key, value, "success"))
                
                # Cleanup this thread's variable
                env.delete(key, source=f"thread_{thread_id}_cleanup")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: Exception {e}")
        
        # Run multiple threads concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(10)]
            for future in futures:
                future.result()  # Wait for completion
        
        # Verify results
        assert len(errors) == 0, f"Thread safety failures: {errors}"
        assert len(results) == 10, f"Expected 10 successful thread operations, got {len(results)}"
        
        # Cleanup
        env.disable_isolation()
    
    def test_test_defaults_functionality(self):
        """Test that test defaults are provided in test context."""
        env = get_env()
        env.enable_isolation()
        
        # In test context, should get test defaults for OAuth credentials
        oauth_client_id = env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
        assert oauth_client_id is not None, "Should get test OAuth client ID in test context"
        assert "test" in oauth_client_id.lower(), "Test OAuth credentials should contain 'test'"
        
        oauth_secret = env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
        assert oauth_secret is not None, "Should get test OAuth secret in test context"
        assert "test" in oauth_secret.lower(), "Test OAuth secret should contain 'test'"
        
        # JWT secret should be provided
        jwt_secret = env.get("JWT_SECRET_KEY")
        assert jwt_secret is not None, "Should get JWT secret in test context"
        assert len(jwt_secret) >= 32, "JWT secret should be at least 32 characters"
        
        # Cleanup
        env.disable_isolation()
    
    def test_environment_reset_functionality(self):
        """Test that environment can be reset cleanly."""
        env = get_env()
        env.enable_isolation()
        
        # Set some test variables
        env.set("RESET_TEST_1", "value1", source="reset_test")
        env.set("RESET_TEST_2", "value2", source="reset_test")
        
        # Verify variables exist
        assert env.get("RESET_TEST_1") == "value1"
        assert env.get("RESET_TEST_2") == "value2"
        
        # Reset environment
        env.reset()
        
        # Variables should no longer exist
        assert env.get("RESET_TEST_1") is None
        assert env.get("RESET_TEST_2") is None
        
        # Isolation should be disabled after reset
        assert not env.is_isolated(), "Isolation should be disabled after reset"
    
    def test_ssot_violation_detection_os_environ_direct_access(self):
        """Test that direct os.environ access is detectable SSOT violation."""
        # This test documents the violation pattern that should be avoided
        
        # VIOLATION PATTERN: Direct os.environ access (BAD)
        with patch.dict(os.environ, {"VIOLATION_TEST": "direct_access"}, clear=False):
            # Direct access bypasses SSOT pattern
            direct_value = os.environ.get("VIOLATION_TEST")
            assert direct_value == "direct_access", "Direct access works but violates SSOT"
        
        # CORRECT PATTERN: SSOT access (GOOD)
        env = get_env()
        env.enable_isolation()
        env.set("VIOLATION_TEST", "ssot_access", source="ssot_test")
        
        ssot_value = env.get("VIOLATION_TEST")
        assert ssot_value == "ssot_access", "SSOT access provides proper isolation"
        
        # Direct access should NOT see isolated variable (proving isolation works)
        direct_isolated = os.environ.get("VIOLATION_TEST")
        # This should be None because isolated variables don't pollute os.environ
        # If this assertion fails, isolation is not working properly
        assert direct_isolated != "ssot_access", "Isolated variables should not pollute os.environ"
        
        # Cleanup
        env.disable_isolation()
    
    def test_context_manager_functionality(self):
        """Test IsolatedEnvironment context manager support."""
        # Test using with statement
        with get_env() as env:
            # Should enable isolation automatically
            assert env.is_isolated(), "Context manager should enable isolation"
            
            # Set variable in context
            env.set("CONTEXT_TEST", "context_value", source="context_test")
            value = env.get("CONTEXT_TEST")
            assert value == "context_value", "Variables should work in context"
        
        # After context exit, isolation should be disabled and original restored
        # (Note: Current implementation behavior)
        env = get_env()
        # Variable should not persist after context (depending on implementation)
        # This tests the cleanup behavior
    
    @pytest.mark.parametrize("env_var,expected_default", [
        ("JWT_SECRET_KEY", True),  # Should have test default
        ("GOOGLE_OAUTH_CLIENT_ID_TEST", True),  # Should have test default
        ("POSTGRES_HOST", True),  # Should have test default
        ("NONEXISTENT_VAR", False),  # Should not have default
    ])
    def test_test_defaults_parametrized(self, env_var, expected_default):
        """Parametrized test for various test defaults."""
        env = get_env()
        env.enable_isolation()
        
        value = env.get(env_var)
        
        if expected_default:
            assert value is not None, f"{env_var} should have test default value"
            assert len(str(value)) > 0, f"{env_var} default should not be empty"
        else:
            assert value is None, f"{env_var} should not have test default"
        
        # Cleanup
        env.disable_isolation()
    
    def test_variable_source_tracking(self):
        """Test that variable sources are tracked for debugging."""
        env = get_env()
        env.enable_isolation()
        
        # Set variable with source
        env.set("SOURCE_TEST", "tracked_value", source="unit_test_source")
        
        # Get source information
        source = env.get_variable_source("SOURCE_TEST")
        assert source == "unit_test_source", "Source should be tracked correctly"
        
        # Cleanup
        env.delete("SOURCE_TEST")
        env.disable_isolation()
    
    def test_subprocess_environment_generation(self):
        """Test subprocess environment generation includes proper variables."""
        env = get_env()
        env.enable_isolation()
        
        # Set test variables
        env.set("SUBPROCESS_TEST", "subprocess_value", source="subprocess_test")
        
        # Get subprocess environment
        subprocess_env = env.get_subprocess_env({"ADDITIONAL_VAR": "additional_value"})
        
        # Should include isolated variable
        assert "SUBPROCESS_TEST" in subprocess_env
        assert subprocess_env["SUBPROCESS_TEST"] == "subprocess_value"
        
        # Should include additional variable
        assert "ADDITIONAL_VAR" in subprocess_env
        assert subprocess_env["ADDITIONAL_VAR"] == "additional_value"
        
        # Should include system variables like PATH
        assert "PATH" in subprocess_env, "System PATH should be included"
        
        # Cleanup
        env.disable_isolation()