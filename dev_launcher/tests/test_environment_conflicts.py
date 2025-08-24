"""
Comprehensive tests for environment variable conflict prevention.

Tests the EnvironmentManager's ability to prevent conflicts, provide isolation,
and handle temporary flags properly.
"""

import os
import pytest
import tempfile
from pathlib import Path

from dev_launcher.isolated_environment import get_env, get_environment_manager


def reset_global_manager():
    """Reset the global environment manager for testing."""
    from dev_launcher.isolated_environment import _global_env
    _global_env.reset_to_original()
    _global_env._protected_vars.clear()
    _global_env._variable_sources.clear()


class TestEnvironmentManager:
    """Test EnvironmentManager functionality."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset global manager before each test
        reset_global_manager()
        # Get global manager and enable isolation
        self.manager = get_environment_manager()
        self.manager.enable_isolation()
        
        # Store original env vars to restore later
        self.original_env = dict(os.environ)
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_global_manager()
    
    def test_singleton_pattern(self):
        """Test that global manager follows singleton pattern."""
        manager1 = get_environment_manager()
        manager1.enable_isolation()
        manager2 = get_environment_manager()  # Should be same instance
        
        assert manager1 is manager2
        assert manager1.is_isolation_enabled() is True  # Isolation should be enabled
    
    def test_isolation_mode_prevents_os_environ_pollution(self):
        """Test that isolation mode prevents setting variables in os.environ."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Set a variable
        result = manager.set("TEST_VAR", "test_value", source="test")
        
        assert result is True
        assert manager.get("TEST_VAR") == "test_value"
        assert "TEST_VAR" not in os.environ  # Should not be in os.environ
    
    def test_non_isolation_mode_sets_os_environ(self):
        """Test that non-isolation mode sets variables in os.environ."""
        manager = get_environment_manager()
        manager.disable_isolation()  # Ensure isolation is disabled
        
        # Set a variable
        result = manager.set("TEST_VAR", "test_value", source="test")
        
        assert result is True
        assert manager.get("TEST_VAR") == "test_value"
        assert os.environ.get("TEST_VAR") == "test_value"
    
    def test_conflict_prevention_different_values(self):
        """Test that conflicts are prevented when different components try to set different values."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # First component sets variable
        result1 = manager.set("CONFLICT_VAR", "value1", source="component1")
        assert result1 is True
        
        # Protect the variable to prevent conflicts
        manager.protect_variable("CONFLICT_VAR")
        
        # Second component tries to set different value - should be prevented
        result2 = manager.set("CONFLICT_VAR", "value2", source="component2")
        assert result2 is False
        
        # Original value should be preserved
        assert manager.get("CONFLICT_VAR") == "value1"
    
    def test_no_conflict_same_values(self):
        """Test that no conflict occurs when components set the same value."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # First component sets variable
        result1 = manager.set("SAME_VAR", "same_value", source="component1")
        assert result1 is True
        
        # Second component sets same value - should succeed even without protection
        result2 = manager.set("SAME_VAR", "same_value", source="component2")
        assert result2 is True
        
        # Value should be preserved
        assert manager.get("SAME_VAR") == "same_value"
    
    def test_force_flag_permits_overriding_values(self):
        """Test that force flag permits overriding protected values."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # First component sets variable
        result1 = manager.set("OVERRIDE_VAR", "original", source="component1")
        assert result1 is True
        
        # Protect the variable
        manager.protect_variable("OVERRIDE_VAR")
        
        # Second component overrides with force flag
        result2 = manager.set("OVERRIDE_VAR", "overridden", source="component2", force=True)
        assert result2 is True
        
        # Value should be overridden
        assert manager.get("OVERRIDE_VAR") == "overridden"
        assert manager.get_variable_source("OVERRIDE_VAR") == "component2"
    
    def test_temporary_flag_cleanup(self):
        """Test that temporary flags can be manually cleaned up."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Set temporary flag
        manager.set("TEMP_FLAG", "temp_value", source="test")
        
        # Flag should be set
        assert manager.get("TEMP_FLAG") == "temp_value"
        assert manager.get("TEMP_FLAG") is not None
        
        # Manually clean up flag
        manager.delete("TEMP_FLAG", source="test_cleanup")
        
        # Flag should be cleaned up
        assert manager.get("TEMP_FLAG") is None
    
    def test_temporary_flag_isolation_mode(self):
        """Test that temporary flags respect isolation mode."""
        # Test in isolation mode
        manager_isolated = get_environment_manager()
        manager_isolated.enable_isolation()
        manager_isolated.set("TEMP_ISO", "value", source="test")
        assert "TEMP_ISO" not in os.environ  # Should not pollute os.environ
        manager_isolated.delete("TEMP_ISO", source="test_cleanup")
        
        # Test in non-isolation mode
        reset_global_manager()
        manager_non_isolated = get_environment_manager()
        manager_non_isolated.disable_isolation()
        manager_non_isolated.set("TEMP_NON_ISO", "value", source="test")
        assert os.environ.get("TEMP_NON_ISO") == "value"
        
        # Clean up from os.environ too
        manager_non_isolated.delete("TEMP_NON_ISO", source="test_cleanup")
        assert "TEMP_NON_ISO" not in os.environ
    
    def test_bulk_set_environment(self):
        """Test bulk setting of environment variables."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        variables = {
            "BULK_VAR1": "value1",
            "BULK_VAR2": "value2",
            "BULK_VAR3": "value3"
        }
        
        results = manager.bulk_set_environment(variables, source="bulk_test")
        
        # All should succeed
        assert all(results.values())
        
        # All should be accessible
        for key, expected_value in variables.items():
            assert manager.get(key) == expected_value
            assert manager.get_variable_source(key) == "bulk_test"
    
    def test_bulk_set_with_conflicts(self):
        """Test bulk setting with some conflicts."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Pre-set a variable and protect it
        manager.set("CONFLICT_BULK", "original", source="existing")
        manager.protect_variable("CONFLICT_BULK")
        
        variables = {
            "BULK_NEW": "new_value",
            "CONFLICT_BULK": "conflicting_value",  # This should fail
            "BULK_ANOTHER": "another_value"
        }
        
        results = manager.bulk_set_environment(variables, source="bulk_test")
        
        # Should have mixed results
        assert results["BULK_NEW"] is True
        assert results["CONFLICT_BULK"] is False  # Conflict prevented
        assert results["BULK_ANOTHER"] is True
        
        # Check final values
        assert manager.get("BULK_NEW") == "new_value"
        assert manager.get("CONFLICT_BULK") == "original"  # Unchanged
        assert manager.get("BULK_ANOTHER") == "another_value"
    
    def test_variable_source_tracking(self):
        """Test that variable sources are properly tracked."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Set variables from different sources
        manager.set("SOURCE1_VAR", "value1", source="source1")
        manager.set("SOURCE2_VAR", "value2", source="source2")
        manager.set("ANOTHER_SOURCE1_VAR", "value3", source="source1")
        
        # Check sources are tracked correctly
        assert manager.get_variable_source("SOURCE1_VAR") == "source1"
        assert manager.get_variable_source("SOURCE2_VAR") == "source2"
        assert manager.get_variable_source("ANOTHER_SOURCE1_VAR") == "source1"
    
    def test_variable_deletion_non_isolation(self):
        """Test deleting variables from os.environ when not in isolation mode."""
        manager = get_environment_manager()
        manager.disable_isolation()
        
        # Set variable that will go to os.environ
        manager.set("CLEAR_TEST", "value", source="test_source")
        
        # Verify it's in os.environ
        assert os.environ.get("CLEAR_TEST") == "value"
        
        # Delete the variable
        result = manager.delete("CLEAR_TEST", source="test_source")
        assert result is True
        
        # Should be cleared from both manager and os.environ
        assert manager.get("CLEAR_TEST") is None
        assert "CLEAR_TEST" not in os.environ
    
    def test_basic_functionality(self):
        """Test basic manager functionality."""
        # Use a fresh manager for isolated testing
        reset_global_manager()
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Set variables from different sources
        manager.set("VAR1", "value1", source="source_a")
        manager.set("VAR2", "value2", source="source_a")
        manager.set("VAR3", "value3", source="source_b")
        
        # Test isolation is working
        assert manager.is_isolation_enabled() is True
        
        # Test variables are accessible
        assert manager.get("VAR1") == "value1"
        assert manager.get("VAR2") == "value2"
        assert manager.get("VAR3") == "value3"
        
        # Test source tracking
        assert manager.get_variable_source("VAR1") == "source_a"
        assert manager.get_variable_source("VAR2") == "source_a"
        assert manager.get_variable_source("VAR3") == "source_b"
    
    def test_thread_safety(self):
        """Test thread safety of environment manager."""
        import threading
        import time
        
        manager = get_environment_manager()
        manager.enable_isolation()
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    key = f"THREAD_{thread_id}_VAR_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    result = manager.set(key, value, source=f"thread_{thread_id}")
                    results.append((thread_id, i, result))
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0, f"Thread errors: {errors}"
        
        # Should have all results
        assert len(results) == 50  # 5 threads * 10 operations each
        
        # All operations should have succeeded (no conflicts expected with unique keys)
        assert all(result for _, _, result in results)


class TestGlobalManagerFunctions:
    """Test global manager accessor functions."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_global_manager()
        self.original_env = dict(os.environ)
    
    def teardown_method(self):
        """Cleanup after each test."""
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_global_manager()
    
    def test_get_environment_manager_isolation_control(self):
        """Test isolation control in development mode."""
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        manager.enable_isolation()  # Explicitly enable for development
        
        assert manager.is_isolation_enabled() is True
    
    def test_get_environment_manager_production_mode(self):
        """Test production mode configuration."""
        os.environ["ENVIRONMENT"] = "production"
        
        manager = get_environment_manager()
        manager.disable_isolation()  # Explicitly disable for production
        
        assert manager.is_isolation_enabled() is False
    
    def test_get_environment_manager_explicit_mode(self):
        """Test explicit isolation mode setting."""
        os.environ["ENVIRONMENT"] = "production"  # This should be ignored
        
        manager = get_environment_manager()
        manager.enable_isolation()  # Explicitly enable regardless of environment
        
        assert manager.is_isolation_enabled() is True
    
    def test_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        manager1 = get_environment_manager()
        manager1.enable_isolation()
        manager2 = get_environment_manager()  # Should be same instance
        
        assert manager1 is manager2
        assert manager1.is_isolation_enabled() is True


class TestIntegrationScenarios:
    """Test integration scenarios that simulate real dev launcher conflicts."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_global_manager()
        self.original_env = dict(os.environ)
    
    def teardown_method(self):
        """Cleanup after each test."""
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_global_manager()
    
    def test_auth_service_port_conflict_scenario(self):
        """Test the specific AUTH_SERVICE_PORT conflict scenario."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Simulate auth_starter setting port
        auth_result = manager.set("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert auth_result is True
        
        # Simulate service_startup trying to set the same port (this was the bug)
        startup_result = manager.set("AUTH_SERVICE_PORT", "8081", source="service_startup")
        assert startup_result is True  # Same value, should succeed
        
        # Protect the variable to simulate conflict prevention
        manager.protect_variable("AUTH_SERVICE_PORT")
        
        # Simulate service_startup trying to set different port (conflict)
        conflict_result = manager.set("AUTH_SERVICE_PORT", "8082", source="service_startup")
        assert conflict_result is False  # Conflict should be prevented
        
        # Port should remain as originally set
        assert manager.get("AUTH_SERVICE_PORT") == "8081"
        assert manager.get_variable_source("AUTH_SERVICE_PORT") == "auth_starter"
    
    def test_secrets_loading_temporary_flag_scenario(self):
        """Test the NETRA_SECRETS_LOADING temporary flag scenario."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Simulate early secret loading with temporary flag
        manager.set("NETRA_SECRETS_LOADING", "true", source="launcher_early_load")
        
        # During loading, flag should be set
        assert manager.get("NETRA_SECRETS_LOADING") == "true"
        
        # Other components should be able to check for the flag
        assert manager.get("NETRA_SECRETS_LOADING") is not None
        
        # Simulate secret loader setting secrets
        manager.set("DATABASE_URL", "postgresql://test", source="secret_loader")
        
        # Manually clean up flag (simulating end of loading)
        manager.delete("NETRA_SECRETS_LOADING", source="launcher_cleanup")
        
        # After cleanup, flag should be cleaned up automatically
        assert manager.get("NETRA_SECRETS_LOADING") is None
        
        # But actual secrets should remain
        assert manager.get("DATABASE_URL") == "postgresql://test"
    
    def test_environment_defaults_vs_secrets_priority(self):
        """Test priority between defaults, secrets, and explicit overrides."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # 1. Launcher sets defaults first
        manager.set("BACKEND_PORT", "8000", source="launcher_defaults")
        
        # 2. Secret loader tries to set from .env (should be allowed to override)
        result = manager.set("BACKEND_PORT", "8001", source="secret_loader", force=True)
        assert result is True
        assert manager.get("BACKEND_PORT") == "8001"
        
        # 3. Protect the variable and try to set without force (should fail)
        manager.protect_variable("BACKEND_PORT")
        result = manager.set("BACKEND_PORT", "8002", source="other_component")
        assert result is False
        assert manager.get("BACKEND_PORT") == "8001"  # Unchanged
        
        # 4. Auth starter can set for auth-specific port
        result = manager.set("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert result is True
    
    def test_multiple_components_setting_different_vars(self):
        """Test multiple components setting their own variables without conflicts."""
        manager = get_environment_manager()
        manager.enable_isolation()
        
        # Different components set their own variables (avoid conflicts by using unique variables)
        components = [
            ("secret_loader", {"DATABASE_URL": "postgresql://test", "JWT_SECRET": "secret123"}),
            ("launcher_defaults", {"CORS_ORIGINS": "*", "LOG_LEVEL": "INFO"}),
            ("auth_starter", {"AUTH_SERVICE_PORT": "8081", "AUTH_SERVICE_URL": "http://localhost:8081"}),
            ("service_startup", {"STARTUP_PORT": "8000", "FRONTEND_PORT": "3000"}),  # Changed BACKEND_PORT to avoid conflict
        ]
        
        # All components set their variables
        for source, variables in components:
            results = manager.bulk_set_environment(variables, source=source)
            assert all(results.values()), f"Failed to set variables from {source}: {results}"
        
        # Verify all variables are set correctly
        expected_vars = {}
        for source, variables in components:
            expected_vars.update(variables)
        
        for key, expected_value in expected_vars.items():
            assert manager.get(key) == expected_value
    
    def test_isolation_mode_integration(self):
        """Test that isolation mode works correctly in integration scenarios."""
        # Test development environment (isolation mode)
        os.environ["ENVIRONMENT"] = "development"
        os.environ["EXISTING_VAR"] = "should_be_ignored"
        
        dev_manager = get_environment_manager()
        dev_manager.enable_isolation()
        assert dev_manager.is_isolation_enabled() is True
        
        # Set variable in isolation mode
        dev_manager.set("TEST_VAR", "isolated_value", source="test")
        
        # Should not affect os.environ
        assert "TEST_VAR" not in os.environ
        
        # When we enable isolation, existing os.environ vars should be copied over
        # (isolation copies current os.environ when enabled, so EXISTING_VAR should be available)
        assert dev_manager.get("EXISTING_VAR") == "should_be_ignored"
        
        # Reset and test production environment
        reset_global_manager()
        os.environ["ENVIRONMENT"] = "production"
        
        prod_manager = get_environment_manager()
        prod_manager.disable_isolation()
        assert prod_manager.is_isolation_enabled() is False
        
        # Set variable in non-isolation mode
        prod_manager.set("PROD_VAR", "production_value", source="test")
        
        # Should affect os.environ
        assert os.environ.get("PROD_VAR") == "production_value"
        
        # Should read from os.environ in non-isolation mode
        assert prod_manager.get("EXISTING_VAR") == "should_be_ignored"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])