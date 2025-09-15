"""WebSocket Factory Import Validation Test - Phase 1 SSOT Validation

CRITICAL MISSION: Validate SSOT imports work after WebSocket Manager Factory removal.

PURPOSE: Ensure SSOT import paths are functional and no circular dependencies exist
after factory removal. This test MUST FAIL initially to detect current deprecated
state, then PASS after complete factory removal.

TESTING CONSTRAINTS:
- NO Docker required - Unit test only
- Uses SSOT testing infrastructure
- Validates import paths and circular dependency prevention
- Tests Golden Path WebSocket functionality ($500K+ ARR protection)

BUSINESS VALUE:
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Goal: Eliminate SSOT violations threatening $500K+ ARR
- Impact: Ensures reliable WebSocket operations after factory removal
- Revenue Impact: Prevents WebSocket initialization failures affecting chat
"""
import pytest
import sys
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestWebSocketFactoryImportValidation(SSotAsyncTestCase):
    """
    Validate WebSocket Factory Import patterns for safe SSOT transition.
    
    These tests ensure that:
    1. SSOT import paths work correctly
    2. No circular dependencies exist after factory removal
    3. WebSocket manager initialization works through canonical paths
    4. Deprecated factory imports are properly removed
    """

    def setUp(self):
        """Setup test environment for WebSocket factory validation."""
        super().setUp()
        self.test_user_id = 'test_user_websocket_factory_validation'

    async def test_deprecated_factory_import_detection_MUST_FAIL_INITIALLY(self):
        """
        TEST 1: Detect deprecated WebSocket factory imports - MUST FAIL INITIALLY
        
        This test MUST FAIL initially because the deprecated factory still exists.
        After factory removal, this test should PASS (proving factory is gone).
        
        SUCCESS CRITERIA:
        - INITIAL STATE: Test FAILS (deprecated factory still importable)  
        - POST-REMOVAL: Test PASSES (deprecated factory import fails)
        """
        logger.info('Testing deprecated WebSocket factory import detection...')
        with self.assertRaises(ImportError, msg='CRITICAL: Deprecated factory still exists - removal incomplete'):
            from netra_backend.app.websocket_core.websocket_manager_factory import create_defensive_user_execution_context
            self.fail('SSOT VIOLATION: Deprecated WebSocket factory still importable. Factory removal incomplete. Expected ImportError for deprecated module.')

    async def test_canonical_ssot_imports_work_correctly(self):
        """
        TEST 1B: Validate canonical SSOT import paths work correctly
        
        This test should PASS both before and after factory removal,
        proving the canonical SSOT paths are stable and functional.
        """
        logger.info('Testing canonical SSOT import paths...')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            self.assertTrue(hasattr(WebSocketManager, '__init__'), 'WebSocketManager class missing __init__ method')
            self.assertTrue(callable(get_websocket_manager), 'get_websocket_manager is not callable')
            logger.info('✅ Canonical SSOT imports functional')
        except ImportError as e:
            self.fail(f'SSOT FAILURE: Canonical WebSocket imports broken: {e}')

    async def test_user_execution_context_creation_ssot_path(self):
        """
        TEST 1C: Validate UserExecutionContext creation works via SSOT paths
        
        Tests that user context creation works through canonical paths
        without requiring the deprecated factory.
        """
        logger.info('Testing UserExecutionContext creation via SSOT paths...')
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            user_context = UserExecutionContext(user_id=self.test_user_id, websocket_client_id='test_client_factory_validation')
            self.assertIsNotNone(user_context)
            self.assertEqual(user_context.user_id, self.test_user_id)
            logger.info('✅ UserExecutionContext creation via SSOT paths successful')
        except Exception as e:
            self.fail(f'SSOT FAILURE: UserExecutionContext creation failed: {e}')

    async def test_circular_dependency_prevention(self):
        """
        TEST 1D: Ensure no circular dependencies after factory removal
        
        Validates that removing the factory doesn't create import cycles
        that could break the WebSocket system.
        """
        logger.info('Testing circular dependency prevention...')
        import_paths_to_test = ['netra_backend.app.websocket_core.websocket_manager', 'netra_backend.app.services.user_execution_context', 'netra_backend.app.services.unified_authentication_service', 'netra_backend.app.core.unified_id_manager']
        successfully_imported = {}
        for import_path in import_paths_to_test:
            try:
                if import_path in sys.modules:
                    del sys.modules[import_path]
                module = __import__(import_path, fromlist=[''])
                successfully_imported[import_path] = module
                logger.debug(f'✅ Successfully imported: {import_path}')
            except ImportError as e:
                self.fail(f'CIRCULAR DEPENDENCY: Import failed for {import_path}: {e}')
            except Exception as e:
                self.fail(f'UNEXPECTED ERROR: Import error for {import_path}: {e}')
        self.assertEqual(len(successfully_imported), len(import_paths_to_test), 'Not all critical modules imported successfully')
        logger.info('✅ No circular dependencies detected in SSOT import paths')

    async def test_websocket_manager_initialization_without_factory(self):
        """
        TEST 1E: Validate WebSocket manager works without deprecated factory
        
        Tests that WebSocket manager can be initialized and used correctly
        through canonical SSOT patterns without factory dependencies.
        """
        logger.info('Testing WebSocket manager initialization without factory...')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            user_context = UserExecutionContext(user_id=self.test_user_id, websocket_client_id='test_websocket_init_validation')
            websocket_manager = WebSocketManager(user_context=user_context)
            self.assertIsNotNone(websocket_manager)
            self.assertEqual(websocket_manager.user_context.user_id, self.test_user_id)
            logger.info('✅ WebSocket manager initialization successful without factory')
        except Exception as e:
            self.fail(f'WEBSOCKET INIT FAILURE: Manager initialization failed: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')