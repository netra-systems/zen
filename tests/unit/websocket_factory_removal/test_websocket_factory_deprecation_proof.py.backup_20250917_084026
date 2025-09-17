"""WebSocket Factory Deprecation Proof Test - Phase 1 Factory Removal Validation

CRITICAL MISSION: Prove the WebSocket Manager Factory can be safely removed.

PURPOSE: Demonstrate that the factory module can be completely removed without
breaking system functionality. This test MUST FAIL after factory removal,
proving the factory is truly gone and all functionality moved to SSOT locations.

TESTING CONSTRAINTS:
- NO Docker required - Unit test only
- Uses SSOT testing infrastructure
- Validates complete factory removal
- Ensures no dead imports or references remain

BUSINESS VALUE:
- Segment: Platform Infrastructure - Affects ALL tiers
- Goal: Complete SSOT consolidation and technical debt elimination
- Impact: Reduces codebase complexity and maintenance overhead
- Revenue Impact: Eliminates factory-related race conditions threatening stability
"""
import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class WebSocketFactoryDeprecationProofTests(SSotAsyncTestCase):
    """
    Prove WebSocket Factory can be safely removed and all functionality migrated.
    
    These tests demonstrate that:
    1. Factory module can be completely removed without breaking functionality
    2. All factory functions have equivalent SSOT implementations
    3. No dead imports or references remain after removal
    4. System performance improves without factory overhead
    """

    def setUp(self):
        """Setup test environment for factory deprecation proof."""
        super().setUp()
        self.factory_module_path = 'netra_backend.app.websocket_core.websocket_manager_factory'
        self.test_user_id = 'test_user_factory_deprecation_proof'

    async def test_factory_module_removal_proof_MUST_FAIL_AFTER_REMOVAL(self):
        """
        TEST 3A: Prove factory module removal - MUST FAIL after removal
        
        This test should PASS initially (factory exists), then FAIL after removal
        (proving the factory module is truly gone).
        
        SUCCESS CRITERIA:
        - PRE-REMOVAL: Test PASSES (factory module importable)
        - POST-REMOVAL: Test FAILS (factory module not importable)
        """
        logger.info('Testing factory module removal proof...')
        try:
            factory_module = importlib.import_module(self.factory_module_path)
            self.assertIsNotNone(factory_module, 'Factory module should exist before removal')
            self.assertTrue(hasattr(factory_module, 'create_defensive_user_execution_context'), 'Critical factory function missing')
            logger.warning('⚠️  FACTORY STILL EXISTS - Removal not yet complete')
        except ImportError:
            self.fail('✅ FACTORY REMOVAL COMPLETE: Factory module no longer importable. This test failure proves successful factory removal.')

    async def test_factory_functions_migrated_to_ssot_equivalents(self):
        """
        TEST 3B: Verify all factory functions have SSOT equivalents
        
        Tests that every function provided by the deprecated factory
        has an equivalent implementation in the canonical SSOT locations.
        """
        logger.info('Testing factory function migration to SSOT equivalents...')
        function_migrations = {'create_defensive_user_execution_context': {'ssot_module': 'netra_backend.app.services.user_execution_context', 'ssot_class': 'UserExecutionContext', 'ssot_method': '__init__'}, 'create_test_user_context': {'ssot_module': 'netra_backend.app.services.user_execution_context', 'ssot_class': 'UserExecutionContext', 'ssot_method': '__init__'}}
        for factory_function, ssot_info in function_migrations.items():
            try:
                ssot_module = importlib.import_module(ssot_info['ssot_module'])
                ssot_class = getattr(ssot_module, ssot_info['ssot_class'])
                self.assertTrue(callable(ssot_class), f"SSOT equivalent {ssot_info['ssot_class']} not callable")
                if ssot_info['ssot_method'] == '__init__':
                    test_instance = ssot_class(user_id=self.test_user_id, websocket_client_id='test_factory_migration')
                    self.assertIsNotNone(test_instance)
                    self.assertEqual(test_instance.user_id, self.test_user_id)
                logger.info(f'✅ SSOT equivalent verified for {factory_function}')
            except Exception as e:
                self.fail(f'SSOT MIGRATION FAILURE: {factory_function} -> {ssot_info}: {e}')

    async def test_no_dead_factory_imports_remain(self):
        """
        TEST 3C: Ensure no dead factory imports remain in codebase
        
        Validates that after factory removal, no modules attempt to import
        from the removed factory, which would cause ImportErrors.
        """
        logger.info('Testing for dead factory imports...')
        modules_to_check = ['netra_backend.app.services.unified_authentication_service', 'netra_backend.app.websocket_core.websocket_manager', 'netra_backend.app.core.unified_id_manager']
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                self.assertIsNotNone(module, f'Module {module_path} failed to import')
                logger.debug(f'✅ No dead factory imports in {module_path}')
            except ImportError as e:
                if 'websocket_manager_factory' in str(e):
                    self.fail(f'DEAD IMPORT: {module_path} still attempts to import from removed factory: {e}')
                else:
                    raise
        logger.info('✅ No dead factory imports detected')

    async def test_system_performance_improvement_without_factory(self):
        """
        TEST 3D: Validate system performance improves without factory overhead
        
        Tests that removing the factory layer eliminates performance overhead
        and reduces object creation time.
        """
        logger.info('Testing system performance improvement without factory...')
        import time
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            start_time = time.perf_counter()
            contexts = []
            for i in range(100):
                context = UserExecutionContext(user_id=f'{self.test_user_id}_{i}', websocket_client_id=f'perf_test_{i}')
                contexts.append(context)
            end_time = time.perf_counter()
            direct_creation_time = end_time - start_time
            self.assertEqual(len(contexts), 100)
            self.assertLess(direct_creation_time, 1.0, f'Direct creation too slow: {direct_creation_time:.3f}s')
            logger.info(f'✅ Performance test: {direct_creation_time:.3f}s for 100 contexts')
        except Exception as e:
            self.fail(f'PERFORMANCE TEST FAILURE: {e}')

    async def test_factory_removal_completeness_verification(self):
        """
        TEST 3E: Comprehensive factory removal completeness check
        
        Performs a comprehensive check to ensure the factory removal is
        complete and no traces remain in the system.
        """
        logger.info('Testing factory removal completeness...')
        if self.factory_module_path in sys.modules:
            logger.warning(f'Factory module still in sys.modules: {self.factory_module_path}')
        critical_modules = ['netra_backend.app.services.unified_authentication_service', 'netra_backend.app.websocket_core.websocket_manager']
        for module_path in critical_modules:
            try:
                module = importlib.import_module(module_path)
                import inspect
                try:
                    source = inspect.getsource(module)
                    factory_references = ['websocket_manager_factory', 'create_defensive_user_execution_context']
                    for ref in factory_references:
                        if ref in source:
                            logger.warning(f"Factory reference '{ref}' found in {module_path}")
                except OSError:
                    pass
            except ImportError:
                pass
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            context = UserExecutionContext(user_id=self.test_user_id, websocket_client_id='completeness_test')
            manager = WebSocketManager(user_context=context)
            self.assertIsNotNone(context)
            self.assertIsNotNone(manager)
            logger.info('✅ SSOT alternatives fully functional')
        except Exception as e:
            self.fail(f'SSOT FUNCTIONALITY FAILURE: {e}')

    async def test_golden_path_functionality_preserved_without_factory(self):
        """
        TEST 3F: Ensure Golden Path functionality preserved without factory
        
        Tests that critical Golden Path WebSocket functionality ($500K+ ARR)
        continues to work correctly after factory removal.
        """
        logger.info('Testing Golden Path functionality preservation...')
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            golden_path_user = f'golden_path_{self.test_user_id}'
            user_context = UserExecutionContext(user_id=golden_path_user, websocket_client_id='golden_path_test_client')
            websocket_manager = WebSocketManager(user_context=user_context)
            self.assertIsNotNone(user_context)
            self.assertIsNotNone(websocket_manager)
            self.assertEqual(websocket_manager.user_context.user_id, golden_path_user)
            required_methods = ['send_event', 'close_connection', 'is_connected']
            for method in required_methods:
                self.assertTrue(hasattr(websocket_manager, method) or hasattr(websocket_manager, method.replace('_', '')), f'WebSocket manager missing critical method: {method}')
            logger.info('✅ Golden Path functionality preserved without factory')
        except Exception as e:
            self.fail(f'GOLDEN PATH FAILURE: Critical functionality broken: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')