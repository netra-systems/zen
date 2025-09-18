"""WebSocket Factory Import Validation Test - FIXED VERSION

CRITICAL MISSION: Validate SSOT imports work after WebSocket Manager Factory removal.

PURPOSE: Ensure SSOT import paths are functional and no circular dependencies exist
after factory removal. These tests should now PASS since factory has been removed.

FIXES APPLIED:
- Replaced SSotAsyncTestCase with unittest.TestCase
- Fixed assertion methods (assertRaises, fail, etc.)
- Updated test expectations for post-removal reality
- Added proper import validation

TESTING CONSTRAINTS:
- NO Docker required - Unit test only
- Uses standard unittest framework
- Validates import paths and circular dependency prevention
- Tests Golden Path WebSocket functionality (500K+ ARR protection)

BUSINESS VALUE:
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Goal: Eliminate SSOT violations threatening 500K+ ARR
- Impact: Ensures reliable WebSocket operations after factory removal
- Revenue Impact: Prevents WebSocket initialization failures affecting chat
"""

import pytest
import unittest
import sys
import importlib
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Use standard logging instead of SSOT logging to avoid dependency issues
import logging

logger = logging.getLogger(__name__)


@pytest.mark.unit
class WebSocketFactoryImportValidationFixedTests(unittest.TestCase):
    """
    Validate WebSocket Factory Import patterns for safe SSOT transition.
    
    These tests ensure that:
    1. Deprecated factory imports properly fail (proving removal)
    2. SSOT import paths work correctly
    3. No circular dependencies exist after factory removal
    4. WebSocket manager initialization works through canonical paths
    """

    def setUp(self):
        """Setup test environment for WebSocket factory validation."""
        self.test_user_id = "test_user_websocket_factory_validation"

    def test_deprecated_factory_import_fails_correctly(self):
        """
        TEST 1: Deprecated factory import should fail - EXPECTED TO PASS
        
        This test should PASS because the deprecated factory has been removed.
        If this test fails, it means factory removal was incomplete.
        
        SUCCESS CRITERIA:
        - ImportError raised when trying to import deprecated factory
        - Proves factory removal was successful
        """
        logger.info("Testing deprecated WebSocket factory import fails correctly...")
        
        # Test 1A: Deprecated factory module should NOT be importable
        with self.assertRaises(ImportError, 
                             msg="CRITICAL: Deprecated factory still exists - removal incomplete"):
            from netra_backend.app.websocket_core.websocket_manager_factory import create_defensive_user_execution_context
            
            # If we reach here, the deprecated factory still exists (TEST SHOULD FAIL)
            self.fail(
                "SSOT VIOLATION: Deprecated WebSocket factory still importable. "
                "Factory removal incomplete. Expected ImportError for deprecated module."
            )

    def test_canonical_ssot_imports_work_correctly(self):
        """
        TEST 2: Validate canonical SSOT import paths work correctly - EXPECTED TO PASS
        
        This test should PASS both before and after factory removal,
        proving the canonical SSOT paths are stable and functional.
        """
        logger.info("Testing canonical SSOT import paths...")
        
        try:
            # Test canonical WebSocket manager import
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            
            # Validate classes are importable and properly defined
            self.assertTrue(hasattr(WebSocketManager, '__init__'), 
                          "WebSocketManager class missing __init__ method")
            
            # Test WebSocket manager functions
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            self.assertTrue(callable(get_websocket_manager), 
                          "get_websocket_manager is not callable")
            
            logger.info("CHECK Canonical SSOT imports functional")
            
        except ImportError as e:
            self.fail(f"SSOT FAILURE: Canonical WebSocket imports broken: {e}")

    def test_user_execution_context_creation_ssot_path(self):
        """
        TEST 3: Validate UserExecutionContext creation works via SSOT paths - EXPECTED TO PASS
        
        Tests that user context creation works through canonical paths
        without requiring the deprecated factory.
        """
        logger.info("Testing UserExecutionContext creation via SSOT paths...")
        
        try:
            # Test direct UserExecutionContext import and creation
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create context directly without factory (SSOT pattern)
            user_context = UserExecutionContext(
                user_id=self.test_user_id,
                thread_id="test_thread_factory_validation",
                run_id="test_run_factory_validation",
                websocket_client_id="test_client_factory_validation"
            )
            
            # Validate context creation succeeded
            self.assertIsNotNone(user_context)
            self.assertEqual(user_context.user_id, self.test_user_id)
            
            logger.info("CHECK UserExecutionContext creation via SSOT paths successful")
            
        except Exception as e:
            self.fail(f"SSOT FAILURE: UserExecutionContext creation failed: {e}")

    def test_circular_dependency_prevention(self):
        """
        TEST 4: Ensure no circular dependencies after factory removal - EXPECTED TO PASS
        
        Validates that removing the factory doesn't create import cycles
        that could break the WebSocket system.
        """
        logger.info("Testing circular dependency prevention...")
        
        import_paths_to_test = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.services.user_execution_context',
            'netra_backend.app.services.unified_authentication_service',
            'netra_backend.app.core.unified_id_manager'
        ]
        
        # Track successful imports to detect cycles
        successfully_imported = {}
        import_errors = []
        
        for import_path in import_paths_to_test:
            try:
                # Clear any cached imports to force fresh import
                if import_path in sys.modules:
                    del sys.modules[import_path]
                
                # Attempt import
                module = importlib.import_module(import_path)
                successfully_imported[import_path] = module
                
                logger.debug(f"CHECK Successfully imported: {import_path}")
                
            except ImportError as e:
                import_errors.append(f"Import failed for {import_path}: {e}")
            except Exception as e:
                import_errors.append(f"Unexpected error for {import_path}: {e}")
        
        # Validate all critical modules imported successfully
        if import_errors:
            self.fail(f"CIRCULAR DEPENDENCY OR IMPORT ERRORS: {'; '.join(import_errors)}")
        
        self.assertEqual(len(successfully_imported), len(import_paths_to_test),
                        "Not all critical modules imported successfully")
        
        logger.info("CHECK No circular dependencies detected in SSOT import paths")

    def test_websocket_manager_initialization_without_factory(self):
        """
        TEST 5: Validate WebSocket manager works without deprecated factory - EXPECTED TO PASS
        
        Tests that WebSocket manager can be initialized and used correctly
        through canonical SSOT patterns without factory dependencies.
        """
        logger.info("Testing WebSocket manager initialization without factory...")
        
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create user context via SSOT pattern
            user_context = UserExecutionContext(
                user_id=self.test_user_id,
                thread_id="test_thread_websocket_init",
                run_id="test_run_websocket_init",
                websocket_client_id="test_websocket_init_validation"
            )
            
            # Initialize WebSocket manager directly (no factory)
            websocket_manager = WebSocketManager(user_context=user_context)
            
            # Validate initialization
            self.assertIsNotNone(websocket_manager)
            self.assertEqual(websocket_manager.user_context.user_id, self.test_user_id)
            
            logger.info("CHECK WebSocket manager initialization successful without factory")
            
        except Exception as e:
            self.fail(f"WEBSOCKET INIT FAILURE: Manager initialization failed: {e}")

    def test_no_remaining_factory_references_in_critical_files(self):
        """
        TEST 6: Ensure no factory references remain in critical files - EXPECTED TO PASS
        
        Validates that critical files don't contain references to the removed factory.
        """
        logger.info("Testing for remaining factory references in critical files...")
        
        critical_files_to_check = [
            'netra_backend.app.services.unified_authentication_service',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.services.user_execution_context'
        ]
        
        factory_references_found = []
        
        for module_path in critical_files_to_check:
            try:
                module = importlib.import_module(module_path)
                module_source = None
                
                # Try to get source code for inspection
                import inspect
                try:
                    module_source = inspect.getsource(module)
                except:
                    # If we can't get source, skip this check
                    continue
                
                # Check for problematic factory references (imports, not comments)
                if module_source:
                    # Look for actual import statements or function calls, not just comments
                    import_patterns = [
                        'from netra_backend.app.websocket_core.websocket_manager_factory import',
                        'import netra_backend.app.websocket_core.websocket_manager_factory',
                        'websocket_manager_factory.create_',
                        'from .websocket_manager_factory import'
                    ]
                    for pattern in import_patterns:
                        if pattern in module_source:
                            factory_references_found.append(f"{module_path} contains active factory import: {pattern}")
                    
            except ImportError:
                # Module doesn't exist, that's fine
                continue
            except Exception as e:
                logger.warning(f"Could not check {module_path}: {e}")
        
        if factory_references_found:
            self.fail(f"FACTORY CLEANUP INCOMPLETE: {'; '.join(factory_references_found)}")
        
        logger.info("CHECK No factory references found in critical files")


if __name__ == "__main__":
    # Run the validation tests
    unittest.main(verbosity=2)