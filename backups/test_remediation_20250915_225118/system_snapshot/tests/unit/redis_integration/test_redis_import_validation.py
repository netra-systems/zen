"""
Redis Import Validation Tests

Purpose: Validate RedisTestManager import fix and SSOT compliance
Business Value: Protects $500K+ ARR by ensuring test infrastructure reliability
Issue: #725 - RedisTestManager import violations in action plan UVS

Test Strategy:
1. Reproduce original ImportError scenario
2. Validate fix through proper import paths
3. Ensure SSOT compliance with redis_manager
4. Test both failing and passing scenarios
"""

import pytest
import unittest
import sys
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class RedisImportValidationTests(SSotBaseTestCase):
    """
    SSOT Compliance: Redis import validation and error reproduction
    
    Business Impact: Test infrastructure must be reliable to protect business value
    SSOT Requirement: All Redis operations through unified redis_manager
    """

    def setUp(self):
        """Setup test environment with clean module state"""
        super().setUp()
        # Clean any cached imports to ensure fresh import testing
        self.original_modules = dict(sys.modules)
        
    def tearDown(self):
        """Clean up module state after each test"""
        super().tearDown()
        # Restore original module state
        sys.modules.clear()
        sys.modules.update(self.original_modules)

    def test_reproduce_redis_test_manager_import_error(self):
        """
        Reproduce the original ImportError from RedisTestManager
        
        This test validates that the old import path fails as expected,
        confirming the need for the SSOT compliance fix.
        """
        # Remove redis-related modules to simulate clean environment
        modules_to_remove = [
            'test_framework.ssot.redis_test_manager', 
            'test_framework.ssot.database_test_utility',
            'test_framework.redis_test_manager'
        ]
        
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]
        
        # Attempt to import RedisTestManager directly (should fail)
        with self.assertRaises(ImportError) as context:
            from test_framework.ssot.redis_test_manager import RedisTestManager
            
        # Validate the error message indicates the missing module
        error_message = str(context.exception)
        self.assertIn("redis_test_manager", error_message.lower())
        
    def test_validate_actual_redis_test_manager_import(self):
        """
        Validate that the actual Redis test manager import works correctly
        
        This confirms the current working Redis test infrastructure
        """
        try:
            # Import the actual working Redis test manager
            from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
            
            # Validate RedisTestManager can be instantiated
            redis_manager = RedisTestManager()
            self.assertIsNotNone(redis_manager)
            
            # Check that it has expected Redis management methods
            expected_methods = ['get', 'set', 'delete', 'exists', 'cleanup']
            
            for method_name in expected_methods:
                self.assertTrue(
                    hasattr(redis_manager, method_name),
                    f"RedisTestManager should provide {method_name} functionality"
                )
                
        except ImportError as e:
            self.fail(f"Actual RedisTestManager import should not fail: {e}")
            
    def test_action_plan_uvs_redis_integration_fix(self):
        """
        Test the specific Action Plan UVS Redis integration scenario
        
        This validates that Action Plan UVS can use the working Redis test manager
        """
        try:
            # Import the working Redis test manager
            from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
            
            # Simulate Action Plan UVS builder Redis operations
            redis_manager = RedisTestManager()
            
            # Test that UVS can use Redis operations
            import asyncio
            
            async def test_uvs_redis_operations():
                await redis_manager.initialize()
                
                # Simulate UVS storing action plan data
                await redis_manager.set('uvs:action_plan:123', 'test_data')
                stored_data = await redis_manager.get('uvs:action_plan:123')
                
                return stored_data
                
            # Run the async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(test_uvs_redis_operations())
                self.assertEqual(result, 'test_data')
            finally:
                loop.close()
                
        except ImportError as e:
            self.fail(f"Action Plan UVS Redis integration should work: {e}")
                
    def test_redis_test_framework_structure(self):
        """
        Validate Redis test framework structure and availability
        
        Documents the actual Redis testing infrastructure that exists
        """
        # Test that the working Redis test manager exists
        try:
            from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
            
            # Validate RedisTestManager is available
            redis_manager = RedisTestManager()
            self.assertIsNotNone(redis_manager)
            
            # Test that it provides expected functionality
            self.assertTrue(hasattr(redis_manager, 'get'))
            self.assertTrue(hasattr(redis_manager, 'set'))
            self.assertTrue(hasattr(redis_manager, 'cleanup'))
            
        except ImportError as e:
            self.fail(f"RedisTestManager should be available: {e}")
            
    def test_import_error_handling(self):
        """
        Test that import errors are handled gracefully
        
        This ensures robust behavior when Redis modules are not available
        """
        # Test behavior when trying to import non-existent Redis modules
        with self.assertRaises(ImportError):
            from test_framework.ssot.redis_test_manager import RedisTestManager
            
        # Test that working Redis manager is still available
        try:
            from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
            redis_manager = RedisTestManager()
            self.assertIsNotNone(redis_manager)
        except ImportError as e:
            self.fail(f"Working Redis test manager should be available: {e}")
                
    def test_redis_manager_integration_scenarios(self):
        """
        Test various Redis integration scenarios with the working test manager
        
        Validates RedisTestManager handles common use cases properly
        """
        try:
            from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
            
            redis_manager = RedisTestManager()
            
            # Test scenarios that RedisTestManager should handle
            test_scenarios = [
                'get',
                'set', 
                'delete',
                'cleanup',
                'initialize'
            ]
            
            for scenario in test_scenarios:
                # Check that RedisTestManager can handle each scenario
                self.assertTrue(
                    hasattr(redis_manager, scenario),
                    f"RedisTestManager should have {scenario} method"
                )
                method = getattr(redis_manager, scenario)
                self.assertTrue(
                    callable(method), 
                    f"RedisTestManager.{scenario} should be callable"
                )
                    
        except ImportError as e:
            self.fail(f"RedisTestManager integration testing failed: {e}")


if __name__ == '__main__':
    # Run with SSOT test runner for compliance
    unittest.main()
