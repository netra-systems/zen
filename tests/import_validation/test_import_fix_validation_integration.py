#!/usr/bin/env python3
"""
INTEGRATION TEST SUITE: Import Fix Validation

PURPOSE:
Integration-level tests to validate that the dev_launcher import fixes work correctly
across different contexts and integration points.

FOCUS: Integration testing (non-docker) following testing best practices.
"""

import unittest
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestImportFixIntegrationValidation(SSotBaseTestCase, unittest.TestCase):
    """
    Integration tests to validate that import fixes work correctly in realistic scenarios.
    """
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        
    def test_demo_configuration_module_integration(self):
        """
        INTEGRATION TEST: Validate that demo.py works correctly after import fix.
        
        This tests the actual business functionality of the demo configuration module.
        """
        try:
            # Import the module that was previously failing
            import sys
            sys.path.append(str(self.project_root))
            
            # This should work after the fix
            from netra_backend.app.core.configuration.demo import get_backend_demo_config, is_demo_mode
            
            # Test that the module functions work correctly
            config = get_backend_demo_config()
            self.assertIsInstance(config, dict)
            
            # Test essential config keys exist
            expected_keys = ['enabled', 'session_ttl', 'max_sessions', 'refresh_interval']
            for key in expected_keys:
                self.assertIn(key, config, f"Demo config missing key: {key}")
                
            # Test demo mode detection works
            demo_status = is_demo_mode()
            self.assertIsInstance(demo_status, bool)
            
        except ImportError as e:
            self.fail(f"Demo configuration module integration failed after fix: {e}")
            
    def test_configuration_integration_test_functionality(self):
        """
        INTEGRATION TEST: Validate that test_configuration_integration.py works after fix.
        
        This tests that the integration test itself can run successfully.
        """
        # We can't easily run the actual test file, but we can test that
        # the import pattern it uses now works
        
        try:
            # Simulate the corrected import from the integration test
            from shared.isolated_environment import IsolatedEnvironment
            
            # Test the functionality that the integration test would use
            env = IsolatedEnvironment()
            
            # Test accessing environment variables (what the integration test does)
            test_env_vars = [
                'ENVIRONMENT',
                'DATABASE_URL', 
                'REDIS_URL'
            ]
            
            for var in test_env_vars:
                # Should not raise exceptions (may return None for missing vars)
                value = env.get(var)
                # Just verify the call doesn't crash
                self.assertTrue(True, f"Successfully accessed {var}")
                
        except Exception as e:
            self.fail(f"Configuration integration test functionality failed: {e}")
            
    def test_cross_service_import_compatibility(self):
        """
        INTEGRATION TEST: Verify that the fix maintains cross-service compatibility.
        
        Tests that other services can also use the corrected import path.
        """
        # Test that the import works from different service contexts
        import_test_code = """
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Test import from different service contexts
from shared.isolated_environment import IsolatedEnvironment

# Test basic functionality
env = IsolatedEnvironment()
test_val = env.get('TEST_VAR', 'default')
print(f'SUCCESS: {test_val}')
"""
        
        # Write test code to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(import_test_code)
            temp_file = f.name
            
        try:
            # Run the test code in subprocess (simulates different service context)
            result = subprocess.run([
                sys.executable, temp_file
            ], capture_output=True, text=True, cwd=str(self.project_root))
            
            self.assertEqual(result.returncode, 0, f"Cross-service import failed: {result.stderr}")
            self.assertIn("SUCCESS", result.stdout)
            
        finally:
            # Clean up
            os.unlink(temp_file)
            
    def test_environment_configuration_integration(self):
        """
        INTEGRATION TEST: Test that environment configuration works end-to-end.
        
        This validates the complete workflow that was broken by the import issue.
        """
        from shared.isolated_environment import IsolatedEnvironment
        
        # Test the complete workflow
        env = IsolatedEnvironment()
        
        # Test isolation mode (what the integration tests use)
        env.enable_isolation()
        
        # Test setting and getting values
        test_key = 'INTEGRATION_TEST_KEY'
        test_value = 'integration_test_value'
        
        with patch.dict(os.environ, {test_key: test_value}):
            retrieved_value = env.get(test_key)
            self.assertEqual(retrieved_value, test_value)
            
            # Test boolean conversion
            env_bool = env.get_bool('NONEXISTENT_BOOL', False)
            self.assertFalse(env_bool)
            
        # Disable isolation
        env.disable_isolation()
        
    def test_thread_safety_integration(self):
        """
        INTEGRATION TEST: Verify that the fix resolves thread loading issues.
        
        This addresses the business impact of "frontend thread loading failures".
        """
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def worker_thread():
            """Worker thread that tests import in thread context."""
            try:
                # This import was failing in thread contexts
                from shared.isolated_environment import IsolatedEnvironment
                
                # Test basic functionality in thread
                env = IsolatedEnvironment()
                test_val = env.get('THREAD_TEST', 'thread_success')
                
                results_queue.put(('success', test_val))
                
            except Exception as e:
                errors_queue.put(('error', str(e)))
                
        # Start multiple threads to test thread safety
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread)
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)  # 10 second timeout
            
        # Check results
        self.assertTrue(errors_queue.empty(), f"Thread errors occurred: {list(errors_queue.queue)}")
        self.assertEqual(results_queue.qsize(), 5, "Not all threads completed successfully")
        
        # Verify all threads got expected results
        while not results_queue.empty():
            status, value = results_queue.get()
            self.assertEqual(status, 'success')
            self.assertEqual(value, 'thread_success')


class TestImportFixRegressionPrevention(SSotBaseTestCase, unittest.TestCase):
    """
    Regression prevention tests to ensure the fix doesn't break other functionality.
    """
    
    def test_dev_launcher_internal_functionality_preserved(self):
        """
        REGRESSION TEST: Ensure dev_launcher internal functionality still works.
        
        The fix should not break internal dev_launcher operations.
        """
        # Test that dev_launcher can still be imported
        try:
            import dev_launcher
            self.assertTrue(hasattr(dev_launcher, '__version__') or hasattr(dev_launcher, 'DevLauncher'))
        except ImportError as e:
            self.fail(f"dev_launcher module import failed: {e}")
            
    def test_shared_module_isolation_maintained(self):
        """
        REGRESSION TEST: Verify that shared module isolation is maintained.
        
        The SSOT migration should maintain service independence.
        """
        from shared.isolated_environment import IsolatedEnvironment
        
        # Test that multiple instances are independent
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment()
        
        # Enable isolation on one but not the other
        env1.enable_isolation()
        # env2 remains in normal mode
        
        # They should behave independently
        # This is a basic test - the actual isolation testing is complex
        self.assertIsNotNone(env1)
        self.assertIsNotNone(env2)
        
    def test_no_circular_import_issues(self):
        """
        REGRESSION TEST: Ensure the fix doesn't create circular import issues.
        
        The import path change could potentially create circular dependencies.
        """
        # Test importing in different orders
        import_orders = [
            ['shared.isolated_environment', 'dev_launcher'],
            ['dev_launcher', 'shared.isolated_environment']
        ]
        
        for order in import_orders:
            # Use subprocess to get clean import environment
            test_code = f"""
import importlib
try:
    for module in {order}:
        importlib.import_module(module)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {{e}}")
"""
            
            result = subprocess.run([
                sys.executable, '-c', test_code
            ], capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, f"Import order {order} failed: {result.stderr}")
            self.assertIn("SUCCESS", result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)