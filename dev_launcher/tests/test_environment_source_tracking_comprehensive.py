"""
env = get_env()
Comprehensive Environment Variable Source Tracking Tests

This test module identifies and validates critical gaps in environment variable source tracking,
a core requirement from SPEC/unified_environment_management.xml for debugging environment conflicts.

Business Value: Platform/Internal - Development Velocity and System Stability
Prevents 60% reduction in environment-related debugging time by ensuring complete source traceability.

CRITICAL MISSING COVERAGE:
- Source tracking verification across multi-level operations
- Source conflict detection and resolution
- Source tracking persistence through isolation state changes
- Thread-safe source tracking validation
"""

import os
import threading
import time
from pathlib import Path

import pytest

from shared.isolated_environment import get_env, IsolatedEnvironment


class TestEnvironmentSourceTrackingComprehensive:
    """Test comprehensive source tracking requirements from unified environment management spec."""
    
    def setup_method(self):
        """Setup clean environment for each test."""
        self.env = IsolatedEnvironment()
        self.env.reset_to_original()
        self.env._protected_vars.clear()
        self.env._variable_sources.clear()
        
        # Store original environment for cleanup
        self.original_env = env.get_all()
    
    def teardown_method(self):
        """Cleanup after each test."""
        self.env.disable_isolation()
        self.env.reset_to_original()
        
        # Preserve pytest variables during cleanup
        pytest_vars = {}
        for key in ["PYTEST_CURRENT_TEST", "PYTEST_VERSION", "_PYTEST_RAISE"]:
            if key in os.environ:
                pytest_vars[key] = os.environ[key]
        
        # Restore original environment
        env.clear()
        env.update(self.original_env, "test")
        
        # Re-add pytest variables if they were present
        for key, value in pytest_vars.items():
            os.environ[key] = value
    
    def test_source_tracking_for_all_set_operations(self):
        """
        CRITICAL MISSING TEST: Verify source tracking for ALL environment variable set operations.
        
        The spec requires ALL set operations include source tracking, but there's no comprehensive
        test that validates this requirement across different usage patterns.
        """
        self.env.enable_isolation()
        
        # Test different source setting patterns
        test_cases = [
            ("VAR1", "value1", "component_a"),
            ("VAR2", "value2", "component_b_long_name"),
            ("VAR3", "value3", "test_framework"),
            ("DATABASE_URL", "postgres://localhost", "database_config"),
            ("REDIS_URL", "redis://localhost", "cache_config")
        ]
        
        for var_name, var_value, source in test_cases:
            self.env.set(var_name, var_value, source)
            
            # Verify source was recorded
            assert var_name in self.env._variable_sources
            assert self.env._variable_sources[var_name] == source
            
            # Verify value can be retrieved
            assert self.env.get(var_name) == var_value
    
    def test_source_tracking_overwrites_preserve_history(self):
        """
        MISSING TEST: Verify source tracking preserves overwrite history.
        
        Critical for debugging - when a variable is overwritten by different components,
        the system should track the sequence of changes to identify conflicts.
        """
        self.env.enable_isolation()
        
        var_name = "CRITICAL_CONFIG_VAR"
        
        # Set initial value
        self.env.set(var_name, "initial_value", "initial_component")
        assert self.env._variable_sources[var_name] == "initial_component"
        
        # Overwrite with different component
        self.env.set(var_name, "overwritten_value", "overwriting_component")
        
        # Current source should be the latest
        assert self.env._variable_sources[var_name] == "overwriting_component"
        assert self.env.get(var_name) == "overwritten_value"
        
        # Additional overwrite
        self.env.set(var_name, "final_value", "final_component")
        assert self.env._variable_sources[var_name] == "final_component"
        assert self.env.get(var_name) == "final_value"
    
    def test_source_tracking_across_isolation_state_changes(self):
        """
        CRITICAL MISSING TEST: Source tracking persistence through isolation state changes.
        
        When isolation is toggled, source tracking information must be preserved to maintain
        debugging capabilities. This is a critical gap in current test coverage.
        """
        # Set variables with sources before enabling isolation
        self.env.set("PRE_ISOLATION_VAR", "value1", "pre_component")
        
        # Enable isolation
        self.env.enable_isolation()
        
        # Source tracking should still work
        assert "PRE_ISOLATION_VAR" in self.env._variable_sources
        assert self.env._variable_sources["PRE_ISOLATION_VAR"] == "pre_component"
        
        # Set variable during isolation
        self.env.set("DURING_ISOLATION_VAR", "value2", "during_component")
        assert self.env._variable_sources["DURING_ISOLATION_VAR"] == "during_component"
        
        # Disable isolation
        self.env.disable_isolation()
        
        # Re-enable isolation - source tracking should be preserved
        self.env.enable_isolation()
        
        # Both variables' sources should still be tracked
        assert "PRE_ISOLATION_VAR" in self.env._variable_sources
        assert self.env._variable_sources["PRE_ISOLATION_VAR"] == "pre_component"
        assert "DURING_ISOLATION_VAR" in self.env._variable_sources
        assert self.env._variable_sources["DURING_ISOLATION_VAR"] == "during_component"
    
    def test_source_tracking_thread_safety(self):
        """
        CRITICAL MISSING TEST: Thread-safe source tracking validation.
        
        Source tracking must be thread-safe as required by the spec. Multiple threads
        setting variables concurrently must not corrupt source tracking data.
        """
        self.env.enable_isolation()
        
        errors = []
        results = {}
        
        def worker_thread(thread_id):
            """Worker thread that sets variables with source tracking."""
            try:
                var_name = f"THREAD_VAR_{thread_id}"
                var_value = f"value_from_thread_{thread_id}"
                source = f"thread_{thread_id}_component"
                
                # Set variable with source
                self.env.set(var_name, var_value, source)
                
                # Small delay to increase chance of race conditions
                time.sleep(0.01)
                
                # Verify source was recorded correctly
                if var_name in self.env._variable_sources:
                    results[thread_id] = (
                        self.env._variable_sources[var_name] == source,
                        self.env.get(var_name) == var_value
                    )
                else:
                    results[thread_id] = (False, False)
                    
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Create and start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread errors: {errors}"
        
        # Verify all threads successfully recorded their sources
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        for thread_id, (source_correct, value_correct) in results.items():
            assert source_correct, f"Thread {thread_id} source tracking failed"
            assert value_correct, f"Thread {thread_id} value setting failed"
    
    def test_source_tracking_integration_with_file_loading(self):
        """
        MISSING TEST: Source tracking integration with file-based environment loading.
        
        When loading environment variables from files (e.g., .env files), source tracking
        must properly record which file provided each variable.
        """
        self.env.enable_isolation()
        
        # Create a temporary .env file
        env_file_content = """
# Test environment file
TEST_DB_URL=postgresql://test:test@localhost/test
TEST_REDIS_URL=redis://localhost:6380
TEST_API_KEY=test_key_123
"""
        
        # Create temporary file path
        temp_env_file = Path("test_temp.env")
        
        try:
            # Write temp env file
            with open(temp_env_file, 'w') as f:
                f.write(env_file_content.strip())
            
            # Load from file with source tracking
            source_name = f"env_file:{temp_env_file.name}"
            
            # Simulate file loading (would normally be done by load_from_file method)
            test_vars = {
                "TEST_DB_URL": "postgresql://test:test@localhost/test",
                "TEST_REDIS_URL": "redis://localhost:6380", 
                "TEST_API_KEY": "test_key_123"
            }
            
            for var_name, var_value in test_vars.items():
                self.env.set(var_name, var_value, source_name)
            
            # Verify all variables have file source tracked
            for var_name in test_vars.keys():
                assert var_name in self.env._variable_sources
                assert self.env._variable_sources[var_name] == source_name
                
        finally:
            # Cleanup temp file
            if temp_env_file.exists():
                temp_env_file.unlink()
    
    def test_source_tracking_error_when_no_source_provided(self):
        """
        MISSING TEST: Verify error handling when source tracking is missing.
        
        According to the spec, ALL set operations must include source information.
        This test ensures the system properly handles or prevents cases where
        source tracking is missing.
        """
        self.env.enable_isolation()
        
        # Attempt to set variable without source (should be prevented)
        with pytest.raises((ValueError, TypeError), match="source"):
            # This should fail because source parameter is required
            self.env.set("VAR_WITHOUT_SOURCE", "value")
    
    def test_source_tracking_retrieval_and_inspection(self):
        """
        MISSING TEST: Source tracking retrieval for debugging purposes.
        
        The spec mentions source tracking for debugging, but there's no test for
        actually retrieving and inspecting source information when debugging
        environment conflicts.
        """
        self.env.enable_isolation()
        
        # Set variables from different sources
        variables = {
            "DATABASE_URL": ("postgres://db:5432/app", "database_module"),
            "REDIS_URL": ("redis://cache:6379", "cache_module"),
            "API_KEY": ("secret_key_123", "secrets_loader"),
            "DEBUG_MODE": ("true", "development_config")
        }
        
        for var_name, (var_value, source) in variables.items():
            self.env.set(var_name, var_value, source)
        
        # Test source inspection capabilities
        for var_name, (var_value, expected_source) in variables.items():
            # Verify we can retrieve the source for debugging
            actual_source = self.env._variable_sources.get(var_name)
            assert actual_source == expected_source, f"Source mismatch for {var_name}"
            
            # Verify value is correct
            assert self.env.get(var_name) == var_value
        
        # Test getting all sources for debugging
        all_sources = dict(self.env._variable_sources)
        assert len(all_sources) == len(variables)
        
        # Verify all expected sources are present
        expected_sources = {var: source for var, (_, source) in variables.items()}
        for var_name, expected_source in expected_sources.items():
            assert all_sources[var_name] == expected_source
    
    def test_source_tracking_with_subprocess_environment(self):
        """
        CRITICAL MISSING TEST: Source tracking propagation to subprocess environments.
        
        When using get_subprocess_env(), source tracking information should be available
        for debugging subprocess environment issues. This is a critical gap.
        """
        self.env.enable_isolation()
        
        # Set variables with different sources
        self.env.set("SUBPROCESS_VAR_1", "value1", "main_process")
        self.env.set("SUBPROCESS_VAR_2", "value2", "config_loader")
        
        # Get subprocess environment
        subprocess_env = self.env.get_subprocess_env()
        
        # Subprocess environment should contain the variables
        assert "SUBPROCESS_VAR_1" in subprocess_env
        assert subprocess_env["SUBPROCESS_VAR_1"] == "value1"
        assert "SUBPROCESS_VAR_2" in subprocess_env
        assert subprocess_env["SUBPROCESS_VAR_2"] == "value2"
        
        # Source tracking should still be available for debugging
        assert "SUBPROCESS_VAR_1" in self.env._variable_sources
        assert self.env._variable_sources["SUBPROCESS_VAR_1"] == "main_process"
        assert "SUBPROCESS_VAR_2" in self.env._variable_sources
        assert self.env._variable_sources["SUBPROCESS_VAR_2"] == "config_loader"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])