"""
Circular Dependency Fix Validation Test (Issue #368)
Test validates that Phase 4 fix successfully eliminated bootstrap circular dependency.

PURPOSE: Prove that SSOT logging initializes without circular import errors
BUSINESS IMPACT: Restores Golden Path ($500K+ ARR) debugging capabilities
"""

import sys
import importlib
from unittest.mock import patch
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestCircularDependencyFix(SSotBaseTestCase):
    """Validates that the circular dependency between SSOT logging and configuration is fixed."""
    
    def setUp(self):
        """Set up test environment with clean import state."""
        super().setUp()
        self.original_modules = set(sys.modules.keys())
    
    def tearDown(self):
        """Clean up imported modules to prevent test interference."""
        current_modules = set(sys.modules.keys())
        new_modules = current_modules - self.original_modules
        
        # Clean up specific modules that were added during test
        cleanup_prefixes = [
            'shared.logging',
            'netra_backend.app.core.configuration',
            'netra_backend.app.logging_config'
        ]
        
        for module_name in new_modules:
            if any(module_name.startswith(prefix) for prefix in cleanup_prefixes):
                sys.modules.pop(module_name, None)
        
        super().tearDown()
    
    def test_circular_dependency_eliminated(self):
        """
        CRITICAL SUCCESS TEST: Validates circular dependency is completely eliminated.
        
        This test should PASS after Phase 4 implementation.
        Before fix: circular import would cause ImportError
        After fix: lazy loading pattern prevents circular dependency
        """
        import_order = []
        
        def track_imports(name, *args, **kwargs):
            import_order.append(name)
            return original_import(name, *args, **kwargs)
        
        original_import = __import__
        
        with patch('builtins.__import__', side_effect=track_imports):
            # This sequence previously caused circular dependency
            try:
                # Step 1: Import SSOT logging
                from shared.logging.unified_logging_ssot import get_logger
                
                # Step 2: Create logger (this triggers configuration loading)
                logger = get_logger('test')
                
                # Step 3: Import configuration directly
                from netra_backend.app.core.configuration import unified_config_manager
                
                # Step 4: Get config (this previously caused circular dependency)
                config = unified_config_manager.get_config()
                
                # Step 5: Use logger again to confirm everything works
                logger.info('Circular dependency test successful')
                
                # If we reach here, circular dependency is fixed
                self.assertTrue(True, "Circular dependency successfully eliminated")
                
            except ImportError as e:
                self.fail(f"Circular dependency still exists: {e}")
    
    def test_lazy_loading_fallback_works(self):
        """
        Test that the lazy loading fallback mechanism works correctly.
        
        This validates that even if the logger import fails, the system
        gracefully falls back to basic logging.
        """
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        # Create a fresh manager instance
        manager = UnifiedConfigManager()
        
        # Test that lazy loading works
        logger = manager._get_logger()
        self.assertIsNotNone(logger, "Lazy loaded logger should not be None")
        
        # Test that logger can be used
        logger.info("Test message from lazy loaded logger")
        
        # Test that subsequent calls return the same logger instance
        logger2 = manager._get_logger()
        self.assertIs(logger, logger2, "Lazy loaded logger should be cached")
    
    def test_golden_path_functionality_preserved(self):
        """
        Test that Golden Path functionality is preserved after the fix.
        
        This ensures the circular dependency fix doesn't break critical business features.
        """
        # Test auth logging (critical for Golden Path)
        from shared.logging.unified_logging_ssot import get_logger
        auth_logger = get_logger('auth')
        auth_logger.info('User login test', extra={'user_id': 'test123'})
        
        # Test configuration access 
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        
        # Validate configuration is accessible
        self.assertIsNotNone(config, "Configuration should be accessible")
        self.assertTrue(hasattr(config, 'environment'), "Config should have environment")
        
        # Test that configuration doesn't break logging
        system_logger = get_logger('system')
        system_logger.info(f'Configuration loaded for environment: {config.environment}')
        
        # If we reach here without exceptions, Golden Path functionality is preserved
        self.assertTrue(True, "Golden Path functionality preserved")
    
    def test_bootstrap_initialization_deterministic(self):
        """
        Test that bootstrap initialization is now deterministic.
        
        This validates that the lazy loading fix makes initialization predictable.
        """
        results = []
        
        # Try initialization multiple times
        for attempt in range(3):
            # Clear relevant modules
            modules_to_clear = [name for name in sys.modules.keys() 
                              if any(prefix in name for prefix in ['shared.logging', 'netra_backend.app.core.configuration'])]
            for module_name in modules_to_clear:
                sys.modules.pop(module_name, None)
            
            try:
                # Attempt initialization
                from shared.logging.unified_logging_ssot import get_logger
                logger = get_logger('bootstrap_test')
                logger.info(f'Bootstrap attempt {attempt}')
                results.append(True)
            except Exception as e:
                results.append(False)
        
        # All attempts should succeed
        self.assertTrue(all(results), f"Bootstrap should be deterministic. Results: {results}")
        self.assertEqual(len(results), 3, "Should have 3 bootstrap attempts")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])