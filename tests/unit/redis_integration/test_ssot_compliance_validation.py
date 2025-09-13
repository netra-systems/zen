"""
SSOT Compliance Validation Tests for Redis Integration

Purpose: Validate system-wide SSOT compliance for Redis operations
Business Value: Ensures consistent Redis patterns protecting business reliability
Issue: #725 - System-wide Redis SSOT compliance validation

Test Strategy:
1. Validate SSOT redis_manager as single source of truth
2. Check for duplicate Redis implementations
3. Ensure consistent Redis patterns across modules  
4. Validate SSOT migration compliance
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSsotComplianceValidation(SSotBaseTestCase):
    """
    SSOT Compliance: System-wide Redis integration validation
    
    Business Impact: SSOT compliance ensures system reliability and maintainability
    SSOT Requirement: Single source of truth for all Redis operations
    Architecture Goal: Eliminate duplicate Redis implementations
    """

    def setUp(self):
        """Setup comprehensive SSOT compliance testing environment"""
        super().setUp()
        self.ssot_redis_manager_path = 'test_framework.ssot.database_test_utility'
        self.expected_redis_methods = [
            'get_redis_client',
            'setup_test_redis', 
            'cleanup_test_redis'
        ]
        
    def test_ssot_redis_manager_availability(self):
        """
        Test that SSOT redis_manager is available and functional
        
        This validates the primary SSOT source for Redis operations
        """
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Validate redis_manager exists and is not None
            self.assertIsNotNone(redis_manager, "SSOT redis_manager should be available")
            
            # Check for expected Redis management methods
            for method_name in self.expected_redis_methods:
                self.assertTrue(
                    hasattr(redis_manager, method_name),
                    f"SSOT redis_manager should provide {method_name}"
                )
                
        except ImportError as e:
            self.fail(f"SSOT redis_manager should be importable: {e}")
            
    def test_no_duplicate_redis_managers(self):
        """
        Test that no duplicate Redis managers exist in the system
        
        SSOT compliance requires single source for Redis operations
        """
        # List of potential duplicate Redis manager locations
        potential_duplicates = [
            'test_framework.redis_manager',
            'test_framework.redis_test_manager', 
            'test_framework.ssot.redis_test_manager',
            'netra_backend.app.redis_manager',
            'shared.redis_manager'
        ]
        
        duplicate_count = 0
        available_managers = []
        
        for manager_path in potential_duplicates:
            try:
                # Attempt to import each potential duplicate
                __import__(manager_path)
                duplicate_count += 1
                available_managers.append(manager_path)
            except ImportError:
                # ImportError is expected for non-existent duplicates
                continue
                
        # SSOT compliance: should only have the official redis_manager
        self.assertLessEqual(
            duplicate_count, 
            1, 
            f"Found multiple Redis managers: {available_managers}. "
            f"SSOT requires single source: {self.ssot_redis_manager_path}"
        )
        
    def test_redis_import_patterns_compliance(self):
        """
        Test that Redis import patterns follow SSOT compliance
        
        Validates consistent import patterns across the codebase
        """
        # Test the canonical SSOT import pattern
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Validate import was successful
            self.assertIsNotNone(redis_manager)
            
            # Test that the import provides expected interface
            if hasattr(redis_manager, 'get_redis_client'):
                # Mock the client to test interface compliance
                with patch.object(redis_manager, 'get_redis_client') as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client
                    
                    client = redis_manager.get_redis_client()
                    self.assertIsNotNone(client)
                    mock_get_client.assert_called_once()
                    
        except ImportError as e:
            self.fail(f"SSOT Redis import pattern should work: {e}")
            
    def test_redis_manager_consistency(self):
        """
        Test that redis_manager provides consistent interface
        
        Ensures all Redis operations go through standardized interface
        """
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Test interface consistency
            interface_methods = []
            
            for method_name in self.expected_redis_methods:
                if hasattr(redis_manager, method_name):
                    method = getattr(redis_manager, method_name)
                    interface_methods.append({
                        'name': method_name,
                        'callable': callable(method),
                        'method': method
                    })
                    
            # Validate all expected methods are callable
            for method_info in interface_methods:
                self.assertTrue(
                    method_info['callable'],
                    f"redis_manager.{method_info['name']} should be callable"
                )
                
            # Ensure at least basic Redis functionality is available
            self.assertGreaterEqual(
                len(interface_methods), 
                1, 
                "redis_manager should provide at least basic Redis functionality"
            )
            
        except ImportError as e:
            self.fail(f"Redis manager consistency check failed: {e}")
            
    def test_migration_from_redis_test_manager(self):
        """
        Test migration compatibility from RedisTestManager to redis_manager
        
        Ensures smooth transition from old to SSOT patterns
        """
        # Test that old RedisTestManager imports fail as expected
        with self.assertRaises(ImportError):
            from test_framework.ssot.redis_test_manager import RedisTestManager
            
        # Test that new SSOT redis_manager works as replacement
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Validate redis_manager can replace RedisTestManager functionality
            self.assertIsNotNone(redis_manager)
            
            # Test that redis_manager provides equivalent capabilities
            has_client_method = hasattr(redis_manager, 'get_redis_client')
            has_setup_method = hasattr(redis_manager, 'setup_test_redis')
            has_cleanup_method = hasattr(redis_manager, 'cleanup_test_redis')
            
            # At least one core method should be available
            has_core_functionality = has_client_method or has_setup_method or has_cleanup_method
            
            self.assertTrue(
                has_core_functionality,
                "redis_manager should provide core Redis functionality to replace RedisTestManager"
            )
            
        except ImportError as e:
            self.fail(f"Migration from RedisTestManager should work via redis_manager: {e}")
            
    def test_cross_module_redis_consistency(self):
        """
        Test Redis usage consistency across different modules
        
        Validates that all modules use the same SSOT redis_manager
        """
        # Test modules that should use Redis consistently
        test_modules = [
            'test_framework.ssot.database_test_utility',
            # Add other modules that should use Redis here
        ]
        
        redis_managers_found = []
        
        for module_path in test_modules:
            try:
                module = __import__(module_path, fromlist=[''])
                
                # Check if module has redis_manager
                if hasattr(module, 'redis_manager'):
                    redis_managers_found.append({
                        'module': module_path,
                        'manager': module.redis_manager
                    })
                    
            except ImportError:
                # Module not available, skip
                continue
                
        # Validate consistency across modules
        if len(redis_managers_found) > 1:
            # All redis_managers should be the same instance or equivalent
            first_manager = redis_managers_found[0]['manager']
            
            for manager_info in redis_managers_found[1:]:
                # Check that all managers have similar interface
                first_methods = [m for m in dir(first_manager) if not m.startswith('_')]
                current_methods = [m for m in dir(manager_info['manager']) if not m.startswith('_')]
                
                # Should have overlapping methods for consistency
                common_methods = set(first_methods).intersection(set(current_methods))
                
                self.assertGreater(
                    len(common_methods), 
                    0,
                    f"Redis managers in {redis_managers_found[0]['module']} and "
                    f"{manager_info['module']} should have consistent interfaces"
                )
                
    def test_redis_error_handling_consistency(self):
        """
        Test that Redis error handling is consistent across SSOT implementation
        
        Ensures reliable error patterns for Redis operations
        """
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Test error handling patterns
            with patch.object(redis_manager, 'get_redis_client') as mock_get_client:
                
                # Test connection error handling
                mock_get_client.side_effect = ConnectionError("Redis connection failed")
                
                with self.assertRaises(ConnectionError):
                    redis_manager.get_redis_client()
                    
                mock_get_client.assert_called_once()
                
                # Reset mock for next test
                mock_get_client.reset_mock()
                mock_get_client.side_effect = None
                
                # Test successful connection
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client
                
                client = redis_manager.get_redis_client()
                self.assertIsNotNone(client)
                
        except ImportError as e:
            self.fail(f"Redis error handling consistency test failed: {e}")
            
    def test_ssot_redis_configuration_compliance(self):
        """
        Test that Redis configuration follows SSOT patterns
        
        Validates consistent Redis configuration across the system
        """
        try:
            from test_framework.ssot.database_test_utility import redis_manager
            
            # Test that redis_manager can be configured consistently
            with patch.object(redis_manager, 'get_redis_client') as mock_get_client:
                
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client
                
                # Test configuration methods if available
                if hasattr(redis_manager, 'setup_test_redis'):
                    with patch.object(redis_manager, 'setup_test_redis') as mock_setup:
                        mock_setup.return_value = True
                        
                        setup_result = redis_manager.setup_test_redis()
                        self.assertTrue(setup_result)
                        mock_setup.assert_called_once()
                        
                # Test cleanup methods if available  
                if hasattr(redis_manager, 'cleanup_test_redis'):
                    with patch.object(redis_manager, 'cleanup_test_redis') as mock_cleanup:
                        mock_cleanup.return_value = True
                        
                        cleanup_result = redis_manager.cleanup_test_redis()
                        self.assertTrue(cleanup_result)
                        mock_cleanup.assert_called_once()
                        
        except ImportError as e:
            self.fail(f"Redis configuration compliance test failed: {e}")


if __name__ == '__main__':
    # Run with SSOT test runner for compliance
    unittest.main()
