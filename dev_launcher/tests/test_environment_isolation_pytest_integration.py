"""
Test environment isolation integration with pytest framework.

This test module focuses on critical edge cases where environment isolation
interacts with pytest's own environment variable management, exposing gaps
in the unified environment management system.

Business Value: Platform/Internal - Test Stability
Prevents test framework integration failures that could block CI/CD pipeline.
"""

import os
import threading
import pytest
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env, get_environment_manager


env = get_env()
class TestPytestEnvironmentIntegration:
    """Test environment isolation integration with pytest framework."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset global manager state
        from shared.isolated_environment import _global_env
        _global_env.reset_to_original()
        _global_env._protected_vars.clear()
        _global_env._variable_sources.clear()
        
        # Store original environment for cleanup
        self.original_env = env.get_all()
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Preserve pytest variables during cleanup
        pytest_vars = {}
        for key in ["PYTEST_CURRENT_TEST", "PYTEST_VERSION", "_PYTEST_RAISE"]:
            if env.exists(key):
                pytest_vars[key] = env.get(key)
        
        # Restore original environment
        env.clear()
        env.update(self.original_env, "test")
        
        # Re-add pytest variables if they were present
        for key, value in pytest_vars.items():
            env.set(key, value)
    
    def test_pytest_current_test_isolation_compatibility(self):
        """
        CRITICAL MISSING TEST: Test that PYTEST_CURRENT_TEST is preserved during isolation.
        
        This test exposes a critical gap where pytest's teardown process fails because
        environment isolation has interfered with pytest's own environment variables.
        """
        manager = get_environment_manager()
        
        # Simulate pytest setting PYTEST_CURRENT_TEST (as it does during test execution)
        pytest_test_var = "dev_launcher/tests/test_environment_isolation_pytest_integration.py::TestPytestEnvironmentIntegration::test_pytest_current_test_isolation_compatibility (call)"
        env.set("PYTEST_CURRENT_TEST", pytest_test_var, "test")
        
        # Enable isolation mode (this is where the bug occurs)
        manager.enable_isolation()
        
        # The critical assertion: PYTEST_CURRENT_TEST must be preserved in os.environ
        # even when isolation is enabled, because pytest teardown relies on it
        assert "PYTEST_CURRENT_TEST" in os.environ
        assert os.environ["PYTEST_CURRENT_TEST"] == pytest_test_var
        
        # Additional verification: isolated environment should also have access
        assert manager.get("PYTEST_CURRENT_TEST") == pytest_test_var
    
    def test_pytest_environment_variable_preservation_during_isolation(self):
        """
        MISSING TEST: Test that pytest-specific environment variables are preserved.
        
        Tests that critical pytest environment variables remain accessible to both
        the pytest framework and the isolated environment system.
        """
        manager = get_environment_manager()
        
        # Set up pytest-related environment variables
        pytest_vars = {
            "PYTEST_CURRENT_TEST": "test_module::test_function (call)",
            "PYTEST_VERSION": "8.4.1",
            "_PYTEST_RAISE": "1"
        }
        
        for key, value in pytest_vars.items():
            os.environ[key] = value
        
        # Enable isolation
        manager.enable_isolation()
        
        # CRITICAL: All pytest variables must remain in os.environ
        for key, expected_value in pytest_vars.items():
            assert key in os.environ, f"Pytest variable {key} was removed from os.environ during isolation"
            assert os.environ[key] == expected_value, f"Pytest variable {key} value changed during isolation"
            
            # Also verify access through isolated environment
            assert manager.get(key) == expected_value, f"Pytest variable {key} not accessible through isolated environment"
    
    def test_isolation_mode_with_pytest_teardown_simulation(self):
        """
        MISSING TEST: Test isolation compatibility with pytest teardown process.
        
        Simulates the exact sequence that causes pytest teardown failures:
        1. Test runs with PYTEST_CURRENT_TEST set
        2. Environment isolation is enabled
        3. Test completes and pytest tries to clean up PYTEST_CURRENT_TEST
        """
        manager = get_environment_manager()
        
        # Step 1: Simulate pytest setting current test variable
        test_name = "test_module::test_function (call)"
        env.set("PYTEST_CURRENT_TEST", test_name, "test")
        
        # Step 2: Enable isolation (this is where the preservation must happen)
        manager.enable_isolation()
        
        # Step 3: Simulate pytest teardown trying to remove the variable
        # This should NOT fail even with isolation enabled
        try:
            # This is what pytest does in its teardown process
            removed_value = env.delete("PYTEST_CURRENT_TEST", "test")
            assert removed_value == test_name
        except KeyError:
            pytest.fail("PYTEST_CURRENT_TEST was not preserved in os.environ during isolation - this breaks pytest teardown")
    
    def test_environment_isolation_pytest_fixture_compatibility(self):
        """
        MISSING TEST: Test isolation works correctly with pytest fixtures.
        
        Tests that environment variables set by pytest fixtures are properly
        handled by the isolation system.
        """
        manager = get_environment_manager()
        
        # Simulate pytest fixture setting environment variables
        fixture_vars = {
            "TEST_FIXTURE_VAR": "fixture_value",
            "PYTEST_CURRENT_TEST": "fixture_test (setup)",
            "TEST_DATABASE_URL": "sqlite:///:memory:"
        }
        
        # Set variables as if they were set by pytest fixtures
        for key, value in fixture_vars.items():
            os.environ[key] = value
            
        # Enable isolation after fixture setup
        manager.enable_isolation()
        
        # Verify fixture variables are accessible
        for key, expected_value in fixture_vars.items():
            assert manager.get(key) == expected_value
            # Critical for pytest: fixture vars must remain in os.environ too
            if key.startswith("PYTEST_"):
                assert key in os.environ
                assert os.environ[key] == expected_value
    
    def test_cross_thread_environment_isolation_with_pytest(self):
        """
        MISSING TEST: Test thread-safe isolation with pytest variables.
        
        Tests that pytest environment variables remain stable across threads
        when environment isolation is enabled.
        """
        manager = get_environment_manager()
        
        # Set pytest variable
        test_name = "test_module::test_function (call)"
        env.set("PYTEST_CURRENT_TEST", test_name, "test")
        
        manager.enable_isolation()
        
        results = []
        errors = []
        
        def worker_thread():
            """Worker that verifies pytest variables in another thread."""
            try:
                # Verify pytest variable is accessible in worker thread
                pytest_var = manager.get("PYTEST_CURRENT_TEST")
                results.append(pytest_var == test_name)
                
                # Critical: verify it's still in os.environ for pytest framework
                results.append("PYTEST_CURRENT_TEST" in os.environ)
                results.append(env.get("PYTEST_CURRENT_TEST") == test_name)
                
            except Exception as e:
                errors.append(str(e))
        
        # Run worker thread
        thread = threading.Thread(target=worker_thread)
        thread.start()
        thread.join()
        
        # Verify no errors and all checks passed
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert all(results), f"Some thread checks failed: {results}"
        
        # Main thread should still have access too
        assert manager.get("PYTEST_CURRENT_TEST") == test_name
        assert "PYTEST_CURRENT_TEST" in os.environ
    
    def test_environment_variable_protection_excludes_pytest_vars(self):
        """
        MISSING TEST: Test that pytest variables are never protected/blocked.
        
        Critical test ensuring that protection mechanisms don't interfere
        with pytest's own environment variable management.
        """
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Set a pytest variable
        env.set("PYTEST_CURRENT_TEST", "initial_test (call)", "test")
        
        # Try to protect pytest variables (this should be prevented)
        pytest_vars = ["PYTEST_CURRENT_TEST", "PYTEST_VERSION", "_PYTEST_RAISE"]
        
        for pytest_var in pytest_vars:
            # Set the variable if not already set
            if pytest_var not in os.environ:
                os.environ[pytest_var] = "test_value"
            
            # Protection should NOT be allowed for pytest variables
            # (or if protection is allowed, it should not affect os.environ access)
            manager.protect_variable(pytest_var)
            
            # Critical: pytest variables must always remain modifiable in os.environ
            # because pytest framework needs to manage them
            original_value = env.get(pytest_var)
            try:
                os.environ[pytest_var] = "modified_by_pytest"
                # This should succeed - pytest must be able to modify its own vars
                assert os.environ[pytest_var] == "modified_by_pytest"
            finally:
                # Restore original value
                if original_value:
                    os.environ[pytest_var] = original_value
                else:
                    os.environ.pop(pytest_var, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])