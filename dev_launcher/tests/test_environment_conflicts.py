"""
Comprehensive tests for environment variable conflict prevention.

Tests the EnvironmentManager's ability to prevent conflicts, provide isolation,
and handle temporary flags properly.
"""

import os
import pytest
import tempfile
from pathlib import Path

from dev_launcher.isolated_environment import get_env


class TestEnvironmentManager:
    """Test EnvironmentManager functionality."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset global manager before each test
        reset_global_manager()
        # Create fresh manager
        self.manager = EnvironmentManager(isolation_mode=True)
        
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
        manager1 = get_environment_manager(isolation_mode=True)
        manager2 = get_environment_manager(isolation_mode=False)  # Should be ignored
        
        assert manager1 is manager2
        assert manager1.isolation_mode is True  # First initialization wins
    
    def test_isolation_mode_prevents_os_environ_pollution(self):
        """Test that isolation mode prevents setting variables in os.environ."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # Set a variable
        result = manager.set_environment("TEST_VAR", "test_value", source="test")
        
        assert result is True
        assert manager.get_environment("TEST_VAR") == "test_value"
        assert "TEST_VAR" not in os.environ  # Should not be in os.environ
    
    def test_non_isolation_mode_sets_os_environ(self):
        """Test that non-isolation mode sets variables in os.environ."""
        manager = EnvironmentManager(isolation_mode=False)
        
        # Set a variable
        result = manager.set_environment("TEST_VAR", "test_value", source="test")
        
        assert result is True
        assert manager.get_environment("TEST_VAR") == "test_value"
        assert os.environ.get("TEST_VAR") == "test_value"
    
    def test_conflict_prevention_different_values(self):
        """Test that conflicts are prevented when different components try to set different values."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # First component sets variable
        result1 = manager.set_environment("CONFLICT_VAR", "value1", source="component1")
        assert result1 is True
        
        # Second component tries to set different value - should be prevented
        result2 = manager.set_environment("CONFLICT_VAR", "value2", source="component2")
        assert result2 is False
        
        # Original value should be preserved
        assert manager.get_environment("CONFLICT_VAR") == "value1"
        
        # Conflict should be tracked
        conflicts = manager.get_conflicts_report()
        assert "CONFLICT_VAR" in conflicts["conflicts_prevented"]
        assert "component2" in conflicts["conflicts_prevented"]["CONFLICT_VAR"]
    
    def test_no_conflict_same_values(self):
        """Test that no conflict occurs when components set the same value."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # First component sets variable
        result1 = manager.set_environment("SAME_VAR", "same_value", source="component1")
        assert result1 is True
        
        # Second component sets same value - should succeed
        result2 = manager.set_environment("SAME_VAR", "same_value", source="component2")
        assert result2 is True
        
        # Value should be preserved
        assert manager.get_environment("SAME_VAR") == "same_value"
        
        # No conflicts should be tracked
        conflicts = manager.get_conflicts_report()
        assert "SAME_VAR" not in conflicts["conflicts_prevented"]
    
    def test_allow_override_flag(self):
        """Test that allow_override flag permits overriding values."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # First component sets variable
        result1 = manager.set_environment("OVERRIDE_VAR", "original", source="component1")
        assert result1 is True
        
        # Second component overrides with flag
        result2 = manager.set_environment("OVERRIDE_VAR", "overridden", source="component2", allow_override=True)
        assert result2 is True
        
        # Value should be overridden
        assert manager.get_environment("OVERRIDE_VAR") == "overridden"
        assert manager.get_variable_source("OVERRIDE_VAR") == "component2"
    
    def test_temporary_flag_cleanup(self):
        """Test that temporary flags are properly cleaned up."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # Use temporary flag
        with manager.set_temporary_flag("TEMP_FLAG", "temp_value", source="test"):
            # Flag should be set during context
            assert manager.get_environment("TEMP_FLAG") == "temp_value"
            assert manager.has_variable("TEMP_FLAG") is True
        
        # Flag should be cleaned up after context
        assert manager.get_environment("TEMP_FLAG") is None
        assert manager.has_variable("TEMP_FLAG") is False
    
    def test_temporary_flag_isolation_mode(self):
        """Test that temporary flags respect isolation mode."""
        # Test in isolation mode
        manager_isolated = EnvironmentManager(isolation_mode=True)
        with manager_isolated.set_temporary_flag("TEMP_ISO", "value", source="test"):
            assert "TEMP_ISO" not in os.environ  # Should not pollute os.environ
        
        # Test in non-isolation mode
        reset_global_manager()
        manager_non_isolated = EnvironmentManager(isolation_mode=False)
        with manager_non_isolated.set_temporary_flag("TEMP_NON_ISO", "value", source="test"):
            assert os.environ.get("TEMP_NON_ISO") == "value"
        
        # Should be cleaned up from os.environ too
        assert "TEMP_NON_ISO" not in os.environ
    
    def test_bulk_set_environment(self):
        """Test bulk setting of environment variables."""
        manager = EnvironmentManager(isolation_mode=True)
        
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
            assert manager.get_environment(key) == expected_value
            assert manager.get_variable_source(key) == "bulk_test"
    
    def test_bulk_set_with_conflicts(self):
        """Test bulk setting with some conflicts."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # Pre-set a variable
        manager.set_environment("CONFLICT_BULK", "original", source="existing")
        
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
        assert manager.get_environment("BULK_NEW") == "new_value"
        assert manager.get_environment("CONFLICT_BULK") == "original"  # Unchanged
        assert manager.get_environment("BULK_ANOTHER") == "another_value"
    
    def test_clear_variables_by_source(self):
        """Test clearing variables by source."""
        manager = EnvironmentManager(isolation_mode=True)
        
        # Set variables from different sources
        manager.set_environment("SOURCE1_VAR", "value1", source="source1")
        manager.set_environment("SOURCE2_VAR", "value2", source="source2")
        manager.set_environment("ANOTHER_SOURCE1_VAR", "value3", source="source1")
        
        # Clear source1 variables
        manager.clear_variables_by_source("source1")
        
        # Source1 variables should be gone
        assert manager.get_environment("SOURCE1_VAR") is None
        assert manager.get_environment("ANOTHER_SOURCE1_VAR") is None
        
        # Source2 variable should remain
        assert manager.get_environment("SOURCE2_VAR") == "value2"
    
    def test_clear_variables_by_source_non_isolation(self):
        """Test clearing variables from os.environ when not in isolation mode."""
        manager = EnvironmentManager(isolation_mode=False)
        
        # Set variable that will go to os.environ
        manager.set_environment("CLEAR_TEST", "value", source="test_source")
        
        # Verify it's in os.environ
        assert os.environ.get("CLEAR_TEST") == "value"
        
        # Clear by source
        manager.clear_variables_by_source("test_source")
        
        # Should be cleared from both manager and os.environ
        assert manager.get_environment("CLEAR_TEST") is None
        assert "CLEAR_TEST" not in os.environ
    
    def test_get_status_report(self):
        """Test status reporting functionality."""
        # Use a fresh manager for isolated testing
        reset_global_manager()
        manager = get_environment_manager(isolation_mode=True)
        
        # Set variables from different sources
        manager.set_environment("VAR1", "value1", source="source_a")
        manager.set_environment("VAR2", "value2", source="source_a")
        manager.set_environment("VAR3", "value3", source="source_b")
        
        # Cause a conflict
        manager.set_environment("VAR1", "conflict_value", source="source_c")
        
        status = manager.get_status()
        
        assert status["isolation_mode"] is True
        assert status["total_variables"] == 3
        assert status["sources"]["source_a"] == 2
        assert status["sources"]["source_b"] == 1
        assert status["conflicts_prevented"] == 1
        
        # Check variables by source
        assert "VAR1" in status["variables_by_source"]["source_a"]
        assert "VAR2" in status["variables_by_source"]["source_a"]
        assert "VAR3" in status["variables_by_source"]["source_b"]
    
    def test_thread_safety(self):
        """Test thread safety of environment manager."""
        import threading
        import time
        
        manager = EnvironmentManager(isolation_mode=True)
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    key = f"THREAD_{thread_id}_VAR_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    result = manager.set_environment(key, value, source=f"thread_{thread_id}")
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
    
    def test_get_environment_manager_auto_detect_development(self):
        """Test auto-detection of development mode."""
        os.environ["ENVIRONMENT"] = "development"
        
        manager = get_environment_manager()
        
        assert manager.isolation_mode is True
    
    def test_get_environment_manager_auto_detect_production(self):
        """Test auto-detection of production mode."""
        os.environ["ENVIRONMENT"] = "production"
        
        manager = get_environment_manager()
        
        assert manager.isolation_mode is False
    
    def test_get_environment_manager_explicit_mode(self):
        """Test explicit isolation mode setting."""
        os.environ["ENVIRONMENT"] = "production"  # This should be ignored
        
        manager = get_environment_manager(isolation_mode=True)
        
        assert manager.isolation_mode is True
    
    def test_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        manager1 = get_environment_manager(isolation_mode=True)
        manager2 = get_environment_manager(isolation_mode=False)  # Should be ignored
        
        assert manager1 is manager2
        assert manager1.isolation_mode is True


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
        manager = get_environment_manager(isolation_mode=True)
        
        # Simulate auth_starter setting port
        auth_result = manager.set_environment("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert auth_result is True
        
        # Simulate service_startup trying to set the same port (this was the bug)
        startup_result = manager.set_environment("AUTH_SERVICE_PORT", "8081", source="service_startup")
        assert startup_result is True  # Same value, should succeed
        
        # Simulate service_startup trying to set different port (conflict)
        conflict_result = manager.set_environment("AUTH_SERVICE_PORT", "8082", source="service_startup")
        assert conflict_result is False  # Conflict should be prevented
        
        # Port should remain as originally set
        assert manager.get_environment("AUTH_SERVICE_PORT") == "8081"
        assert manager.get_variable_source("AUTH_SERVICE_PORT") == "auth_starter"
    
    def test_secrets_loading_temporary_flag_scenario(self):
        """Test the NETRA_SECRETS_LOADING temporary flag scenario."""
        manager = get_environment_manager(isolation_mode=True)
        
        # Simulate early secret loading with temporary flag
        with manager.set_temporary_flag("NETRA_SECRETS_LOADING", "true", source="launcher_early_load"):
            # During loading, flag should be set
            assert manager.get_environment("NETRA_SECRETS_LOADING") == "true"
            
            # Other components should be able to check for the flag
            assert manager.has_variable("NETRA_SECRETS_LOADING") is True
            
            # Simulate secret loader setting secrets
            manager.set_environment("DATABASE_URL", "postgresql://test", source="secret_loader")
        
        # After context, flag should be cleaned up automatically
        assert manager.get_environment("NETRA_SECRETS_LOADING") is None
        assert manager.has_variable("NETRA_SECRETS_LOADING") is False
        
        # But actual secrets should remain
        assert manager.get_environment("DATABASE_URL") == "postgresql://test"
    
    def test_environment_defaults_vs_secrets_priority(self):
        """Test priority between defaults, secrets, and explicit overrides."""
        manager = get_environment_manager(isolation_mode=True)
        
        # 1. Launcher sets defaults first
        manager.set_environment("BACKEND_PORT", "8000", source="launcher_defaults")
        
        # 2. Secret loader tries to set from .env (should be allowed to override)
        result = manager.set_environment("BACKEND_PORT", "8001", source="secret_loader", allow_override=True)
        assert result is True
        assert manager.get_environment("BACKEND_PORT") == "8001"
        
        # 3. Another component tries to set without override (should fail)
        result = manager.set_environment("BACKEND_PORT", "8002", source="other_component")
        assert result is False
        assert manager.get_environment("BACKEND_PORT") == "8001"  # Unchanged
        
        # 4. Auth starter can override for auth-specific port
        result = manager.set_environment("AUTH_SERVICE_PORT", "8081", source="auth_starter")
        assert result is True
    
    def test_multiple_components_setting_different_vars(self):
        """Test multiple components setting their own variables without conflicts."""
        manager = get_environment_manager(isolation_mode=True)
        
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
            assert manager.get_environment(key) == expected_value
        
        # Get status to verify proper tracking
        status = manager.get_status()
        assert status["total_variables"] == len(expected_vars)
        assert status["conflicts_prevented"] == 0  # No conflicts expected
    
    def test_isolation_mode_integration(self):
        """Test that isolation mode works correctly in integration scenarios."""
        # Test development environment (isolation mode)
        os.environ["ENVIRONMENT"] = "development"
        os.environ["EXISTING_VAR"] = "should_be_ignored"
        
        dev_manager = get_environment_manager()
        assert dev_manager.isolation_mode is True
        
        # Set variable in isolation mode
        dev_manager.set_environment("TEST_VAR", "isolated_value", source="test")
        
        # Should not affect os.environ
        assert "TEST_VAR" not in os.environ
        
        # Should not read from os.environ in isolation mode
        assert dev_manager.get_environment("EXISTING_VAR") is None
        
        # Reset and test production environment
        reset_global_manager()
        os.environ["ENVIRONMENT"] = "production"
        
        prod_manager = get_environment_manager()
        assert prod_manager.isolation_mode is False
        
        # Set variable in non-isolation mode
        prod_manager.set_environment("PROD_VAR", "production_value", source="test")
        
        # Should affect os.environ
        assert os.environ.get("PROD_VAR") == "production_value"
        
        # Should read from os.environ in non-isolation mode
        assert prod_manager.get_environment("EXISTING_VAR") == "should_be_ignored"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])