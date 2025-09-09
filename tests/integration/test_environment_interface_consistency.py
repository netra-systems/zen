from shared.isolated_environment import get_env

env = get_env()

"""
Test for environment interface consistency across services.

This test ensures that IsolatedEnvironment implementations across different services
maintain consistent interfaces and behavior, as required by the unified environment
management specification.

Business Value: Platform/Internal - Interface Consistency
Ensures unified environment management patterns work consistently across all services.
"""

import os
import pytest
from typing import Dict, Any, Optional
from pathlib import Path

# Import both IsolatedEnvironment implementations to test consistency
from shared.isolated_environment import IsolatedEnvironment as DevLauncherIsolatedEnvironment
from shared.isolated_environment import IsolatedEnvironment as BackendIsolatedEnvironment


class TestEnvironmentInterfaceConsistency:
    """Test consistency between different IsolatedEnvironment implementations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with isolation."""
        # Store original environment
        self.original_env = env.get_all()
        
        # Clear test-specific variables
        test_vars = ['CONSISTENCY_TEST_VAR', 'INTERFACE_TEST_VAR', 'CROSS_SERVICE_VAR']
        for var in test_vars:
            os.environ.pop(var, None)
            
        # Get fresh instances for testing
        self.dev_env = DevLauncherIsolatedEnvironment()
        self.backend_env = BackendIsolatedEnvironment()
        
        # Enable isolation on both
        self.dev_env.enable_isolation(backup_original=True)
        self.backend_env.enable_isolation(backup_original=True)
            
        yield
        
        # Restore original environment
        self.dev_env.disable_isolation()
        self.backend_env.disable_isolation()
        # Don't call clear() outside isolation - just restore original values
        for key in list(os.environ.keys()):
            if key not in self.original_env:
                os.environ.pop(key, None)
        os.environ.update(self.original_env)

    def test_basic_interface_compatibility(self):
        """Test that both implementations support the same basic interface."""
        
        # Test that both have the core methods
        core_methods = ['get', 'set', 'delete', 'exists', 'get_all', 'update']
        
        for method_name in core_methods:
            assert hasattr(self.dev_env, method_name), f"DevLauncher missing method: {method_name}"
            assert hasattr(self.backend_env, method_name), f"Backend missing method: {method_name}"
            
            # Ensure they're callable
            assert callable(getattr(self.dev_env, method_name)), f"DevLauncher {method_name} not callable"
            assert callable(getattr(self.backend_env, method_name)), f"Backend {method_name} not callable"

    def test_isolation_interface_consistency(self):
        """Test that isolation-related methods work consistently."""
        
        isolation_methods = ['enable_isolation', 'disable_isolation']
        
        for method_name in isolation_methods:
            assert hasattr(self.dev_env, method_name), f"DevLauncher missing isolation method: {method_name}"
            assert hasattr(self.backend_env, method_name), f"Backend missing isolation method: {method_name}"

        # Test isolation state checking
        isolation_state_methods = ['is_isolation_enabled', 'is_isolated']
        
        # At least one of these should be available on each implementation
        dev_has_state_check = any(hasattr(self.dev_env, method) for method in isolation_state_methods)
        backend_has_state_check = any(hasattr(self.backend_env, method) for method in isolation_state_methods)
        
        assert dev_has_state_check, "DevLauncher should have isolation state checking"
        assert backend_has_state_check, "Backend should have isolation state checking"

    def test_cross_service_variable_isolation(self):
        """Test that variables set in one service don't pollute the other when isolated."""
        
        # Set a variable in dev_launcher environment
        self.dev_env.set("CROSS_SERVICE_VAR", "dev_value", "test_dev")
        
        # Set a different variable in backend environment  
        self.backend_env.set("CROSS_SERVICE_VAR", "backend_value", "test_backend")
        
        # Each should have their own isolated value
        assert self.dev_env.get("CROSS_SERVICE_VAR") == "dev_value"
        assert self.backend_env.get("CROSS_SERVICE_VAR") == "backend_value"
        
        # os.environ should not have been polluted
        assert "CROSS_SERVICE_VAR" not in os.environ

    def test_subprocess_environment_interface(self):
        """Test that subprocess environment generation works consistently."""
        
        # Both should support subprocess environment generation
        assert hasattr(self.dev_env, 'get_subprocess_env'), "DevLauncher missing get_subprocess_env"
        assert hasattr(self.backend_env, 'get_subprocess_env'), "Backend missing get_subprocess_env"
        
        # Set test variables in both
        self.dev_env.set("SUBPROCESS_TEST_DEV", "dev_subprocess_value", "test_dev")
        self.backend_env.set("SUBPROCESS_TEST_BACKEND", "backend_subprocess_value", "test_backend")
        
        # Get subprocess environments
        dev_subprocess_env = self.dev_env.get_subprocess_env()
        backend_subprocess_env = self.backend_env.get_subprocess_env()
        
        # Both should return dictionaries
        assert isinstance(dev_subprocess_env, dict), "DevLauncher subprocess env should be dict"
        assert isinstance(backend_subprocess_env, dict), "Backend subprocess env should be dict"
        
        # Each should contain their respective variables
        assert dev_subprocess_env.get("SUBPROCESS_TEST_DEV") == "dev_subprocess_value"
        assert backend_subprocess_env.get("SUBPROCESS_TEST_BACKEND") == "backend_subprocess_value"
        
        # Both should preserve critical system variables
        critical_vars = ['PATH']  # At minimum, PATH should be preserved
        for var in critical_vars:
            if var in os.environ:
                assert var in dev_subprocess_env, f"DevLauncher should preserve {var}"
                assert var in backend_subprocess_env, f"Backend should preserve {var}"

    def test_file_loading_interface_compatibility(self):
        """Test that file loading interfaces are compatible where available."""
        
        # Check if both implementations support file loading
        dev_has_load_from_file = hasattr(self.dev_env, 'load_from_file')
        backend_has_load_from_file = hasattr(self.backend_env, 'load_from_file')
        
        if dev_has_load_from_file and backend_has_load_from_file:
            
            # Create a temporary .env file
            test_env_content = """
# Test environment file
INTERFACE_TEST_VAR=file_loaded_value
CONSISTENCY_TEST_VAR=file_test
"""
            
            temp_env_file = Path("test_interface_consistency.env")
            try:
                temp_env_file.write_text(test_env_content.strip(), encoding='utf-8')
                
                # Load from file in both environments
                dev_loaded = self.dev_env.load_from_file(temp_env_file, override_existing=True)
                backend_loaded = self.backend_env.load_from_file(temp_env_file, override_existing=True)
                
                # Handle different return types
                # dev_launcher returns (count, errors), backend returns just count
                dev_count = dev_loaded[0] if isinstance(dev_loaded, tuple) else dev_loaded
                backend_count = backend_loaded[0] if isinstance(backend_loaded, tuple) else backend_loaded
                
                # Both should successfully load variables
                assert dev_count > 0, "DevLauncher should load variables from file"
                assert backend_count > 0, "Backend should load variables from file"
                
                # Both should have the loaded values
                assert self.dev_env.get("INTERFACE_TEST_VAR") == "file_loaded_value"
                assert self.backend_env.get("INTERFACE_TEST_VAR") == "file_loaded_value"
                
            finally:
                # Clean up test file
                if temp_env_file.exists():
                    temp_env_file.unlink()

    def test_singleton_behavior_per_service(self):
        """Test that each service maintains its own singleton pattern."""
        
        # Get multiple instances of each service's environment
        dev_env_1 = DevLauncherIsolatedEnvironment()
        dev_env_2 = DevLauncherIsolatedEnvironment()
        
        backend_env_1 = BackendIsolatedEnvironment()  
        backend_env_2 = BackendIsolatedEnvironment()
        
        # Each service should maintain singleton behavior
        assert dev_env_1 is dev_env_2, "DevLauncher should be singleton"
        assert backend_env_1 is backend_env_2, "Backend should be singleton"
        
        # But services should have different instances (service isolation)
        assert dev_env_1 is not backend_env_1, "Services should have separate environment instances"

    def test_thread_safety_consistency(self):
        """Test that both implementations are thread-safe."""
        
        import threading
        import time
        
        results = []
        errors = []
        
        def worker_thread(env, service_name: str, thread_id: int):
            try:
                # Each thread sets and retrieves variables
                for i in range(5):
                    key = f"THREAD_SAFETY_{service_name}_{thread_id}_{i}"
                    value = f"value_{service_name}_{thread_id}_{i}"
                    
                    env.set(key, value, f"thread_{thread_id}")
                    retrieved = env.get(key)
                    
                    results.append((service_name, thread_id, key, value, retrieved))
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                    
            except Exception as e:
                errors.append((service_name, thread_id, str(e)))
        
        # Test both environments with multiple threads
        threads = []
        
        # Dev launcher threads
        for i in range(3):
            t = threading.Thread(target=worker_thread, args=(self.dev_env, "dev", i))
            threads.append(t)
            
        # Backend threads  
        for i in range(3):
            t = threading.Thread(target=worker_thread, args=(self.backend_env, "backend", i))
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
            
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all operations succeeded
        expected_results = 6 * 5  # 6 threads * 5 operations each
        assert len(results) == expected_results, f"Expected {expected_results} results, got {len(results)}"
        
        # Verify all set/get operations were consistent
        for service_name, thread_id, key, set_value, retrieved_value in results:
            assert set_value == retrieved_value, f"Thread safety failure: {key} set to {set_value} but retrieved {retrieved_value}"

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across implementations."""
        
        # Test handling of None values
        dev_none_result = self.dev_env.get("NONEXISTENT_KEY")
        backend_none_result = self.backend_env.get("NONEXISTENT_KEY")
        
        assert dev_none_result is None, "DevLauncher should return None for nonexistent keys"
        assert backend_none_result is None, "Backend should return None for nonexistent keys"
        
        # Test default value handling
        dev_default = self.dev_env.get("NONEXISTENT_KEY", "default_value")
        backend_default = self.backend_env.get("NONEXISTENT_KEY", "default_value")
        
        assert dev_default == "default_value", "DevLauncher should return default value"
        assert backend_default == "default_value", "Backend should return default value"
        
        # Test delete on nonexistent keys (should not raise exceptions)
        try:
            self.dev_env.delete("NONEXISTENT_DELETE_KEY")
            dev_delete_ok = True
        except Exception:
            dev_delete_ok = False
            
        try:
            self.backend_env.delete("NONEXISTENT_DELETE_KEY")
            backend_delete_ok = True
        except Exception:
            backend_delete_ok = False
        
        assert dev_delete_ok, "DevLauncher should handle deleting nonexistent keys gracefully"
        assert backend_delete_ok, "Backend should handle deleting nonexistent keys gracefully"

    def test_environment_detection_consistency(self):
        """Test that environment detection works consistently when available."""
        
        # Set a test environment value
        test_env_value = "consistency_test"
        
        self.dev_env.set("ENVIRONMENT", test_env_value, "consistency_test")
        self.backend_env.set("ENVIRONMENT", test_env_value, "consistency_test") 
        
        # Both should be able to retrieve the value consistently
        dev_env_val = self.dev_env.get("ENVIRONMENT")
        backend_env_val = self.backend_env.get("ENVIRONMENT")
        
        assert dev_env_val == test_env_value, "DevLauncher should retrieve ENVIRONMENT consistently"
        assert backend_env_val == test_env_value, "Backend should retrieve ENVIRONMENT consistently"
        
        # Test with different environment values per service (isolation)
        self.dev_env.set("ENVIRONMENT", "dev_environment", "dev_test")
        self.backend_env.set("ENVIRONMENT", "backend_environment", "backend_test")
        
        # Each should maintain its isolated value
        assert self.dev_env.get("ENVIRONMENT") == "dev_environment"
        assert self.backend_env.get("ENVIRONMENT") == "backend_environment"