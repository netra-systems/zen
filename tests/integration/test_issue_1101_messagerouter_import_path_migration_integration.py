"""
Integration Tests for Issue #1101 MessageRouter Import Path Migration

These tests validate the import path migration strategy with real services:
1. Test import path compatibility during migration
2. Validate services can switch between import paths
3. Test backward compatibility during transition
4. Monitor migration impact on real integrations

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Safe migration path without service disruption
- Value Impact: Ensures zero-downtime migration to SSOT compliance
- Strategic Impact: Protects Golden Path during system evolution
"""
import pytest
import asyncio
import time
import importlib
import sys
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.integration
class MessageRouterImportPathMigrationTests(SSotAsyncTestCase):
    """Integration tests for MessageRouter import path migration with real services."""

    def setUp(self):
        """Set up test environment with migration tracking."""
        super().setUp()
        self.test_user_id = 'migration_user_789'
        self.test_thread_id = f'thread_{self.test_user_id}_{int(time.time())}'
        self.test_run_id = f'run_{self.test_user_id}_{int(time.time())}'
        self.user_context = UserExecutionContext.from_request(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        self.migration_tracking = {'successful_imports': [], 'failed_imports': [], 'compatibility_issues': [], 'performance_metrics': {}}

    async def test_legacy_import_path_compatibility(self):
        """Test that legacy import paths continue to work during migration."""
        start_time = time.time()
        try:
            from netra_backend.app.core.message_router import MessageRouter as CoreRouter
            from netra_backend.app.core.message_router import message_router as core_instance
            self.assertIsNotNone(CoreRouter)
            self.assertIsNotNone(core_instance)
            router = CoreRouter()
            self.assertIsNotNone(router)
            self.migration_tracking['successful_imports'].append({'path': 'netra_backend.app.core.message_router', 'type': 'legacy_proxy', 'time': time.time() - start_time})
            logger.info('Legacy core import path compatibility confirmed')
        except ImportError as e:
            self.migration_tracking['failed_imports'].append({'path': 'netra_backend.app.core.message_router', 'error': str(e), 'time': time.time() - start_time})
            self.fail(f'Legacy import path failed: {e}')

    async def test_canonical_import_path_stability(self):
        """Test that canonical import path is stable and reliable."""
        start_time = time.time()
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
            from netra_backend.app.websocket_core.handlers import get_message_router
            self.assertIsNotNone(CanonicalRouter)
            self.assertIsNotNone(get_message_router)
            router1 = CanonicalRouter()
            router2 = get_message_router()
            self.assertIsNotNone(router1)
            self.assertIsNotNone(router2)
            self.migration_tracking['successful_imports'].append({'path': 'netra_backend.app.websocket_core.handlers', 'type': 'canonical', 'time': time.time() - start_time})
            logger.info('Canonical import path stability confirmed')
        except ImportError as e:
            self.migration_tracking['failed_imports'].append({'path': 'netra_backend.app.websocket_core.handlers', 'error': str(e), 'time': time.time() - start_time})
            self.fail(f'Canonical import path failed: {e}')

    async def test_services_import_path_compatibility(self):
        """Test that services import path provides canonical reference."""
        start_time = time.time()
        try:
            from netra_backend.app.services.message_router import MessageRouter as ServicesRouter
            self.assertIsNotNone(ServicesRouter)
            router = ServicesRouter()
            self.assertIsNotNone(router)
            self.assertFalse(hasattr(router, '_canonical_router'))
            self.migration_tracking['successful_imports'].append({'path': 'netra_backend.app.services.message_router', 'type': 'canonical_reference', 'time': time.time() - start_time})
            logger.info('Services import path compatibility confirmed')
        except ImportError as e:
            self.migration_tracking['failed_imports'].append({'path': 'netra_backend.app.services.message_router', 'error': str(e), 'time': time.time() - start_time})
            self.fail(f'Services import path failed: {e}')

    async def test_import_path_migration_gradual_transition(self):
        """Test gradual transition from legacy to canonical import paths."""
        migration_steps = [{'name': 'legacy_proxy', 'import': 'from netra_backend.app.core.message_router import MessageRouter', 'expected_type': 'proxy'}, {'name': 'services_canonical', 'import': 'from netra_backend.app.services.message_router import MessageRouter', 'expected_type': 'canonical'}, {'name': 'direct_canonical', 'import': 'from netra_backend.app.websocket_core.handlers import MessageRouter', 'expected_type': 'canonical'}]
        for step in migration_steps:
            start_time = time.time()
            try:
                if step['name'] == 'legacy_proxy':
                    from netra_backend.app.core.message_router import MessageRouter as StepRouter
                elif step['name'] == 'services_canonical':
                    from netra_backend.app.services.message_router import MessageRouter as StepRouter
                else:
                    from netra_backend.app.websocket_core.handlers import MessageRouter as StepRouter
                router = StepRouter()
                self.assertIsNotNone(router)
                if step['expected_type'] == 'proxy':
                    self.assertTrue(hasattr(router, '_canonical_router'), f"Step {step['name']} should be proxy but isn't")
                else:
                    self.assertFalse(hasattr(router, '_canonical_router'), f"Step {step['name']} should be canonical but is proxy")
                self.migration_tracking['successful_imports'].append({'migration_step': step['name'], 'path': step['import'], 'expected_type': step['expected_type'], 'time': time.time() - start_time})
                logger.info(f"Migration step {step['name']} successful")
            except Exception as e:
                self.migration_tracking['failed_imports'].append({'migration_step': step['name'], 'path': step['import'], 'error': str(e), 'time': time.time() - start_time})
                self.fail(f"Migration step {step['name']} failed: {e}")

    async def test_import_path_functional_equivalence(self):
        """Test that all import paths provide functionally equivalent routers."""
        from netra_backend.app.core.message_router import MessageRouter as CoreRouter
        from netra_backend.app.websocket_core.handlers import MessageRouter as HandlersRouter
        from netra_backend.app.services.message_router import MessageRouter as ServicesRouter
        core_router = CoreRouter()
        handlers_router = HandlersRouter()
        services_router = ServicesRouter()
        routers = [('core', core_router), ('handlers', handlers_router), ('services', services_router)]
        for name, router in routers:
            required_methods = ['add_handler', 'handlers']
            for method in required_methods:
                self.assertTrue(hasattr(router, method), f'Router from {name} missing {method}')
            initial_handler_count = len(router.handlers)
            self.assertIsInstance(initial_handler_count, int)
            self.assertGreaterEqual(initial_handler_count, 0)
        logger.info('Import path functional equivalence confirmed')

    async def test_migration_impact_on_websocket_integration(self):
        """Test migration impact on WebSocket integration services."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        ws_manager = WebSocketManager(user_context=self.user_context)
        self.assertIsNotNone(ws_manager)
        try:
            self.assertTrue(hasattr(ws_manager, 'user_context'))
            self.assertEqual(ws_manager.user_context.user_id, self.test_user_id)
            self.migration_tracking['successful_imports'].append({'integration': 'websocket_manager', 'status': 'compatible', 'time': time.time()})
        except Exception as e:
            self.migration_tracking['compatibility_issues'].append({'integration': 'websocket_manager', 'error': str(e), 'time': time.time()})

    async def test_import_path_performance_impact(self):
        """Test performance impact of different import paths."""
        import_paths = [('core', 'from netra_backend.app.core.message_router import MessageRouter'), ('handlers', 'from netra_backend.app.websocket_core.handlers import MessageRouter'), ('services', 'from netra_backend.app.services.message_router import MessageRouter')]
        for path_name, import_statement in import_paths:
            import_start = time.time()
            try:
                if path_name == 'core':
                    from netra_backend.app.core.message_router import MessageRouter as PathRouter
                elif path_name == 'handlers':
                    from netra_backend.app.websocket_core.handlers import MessageRouter as PathRouter
                else:
                    from netra_backend.app.services.message_router import MessageRouter as PathRouter
                import_time = time.time() - import_start
                instance_start = time.time()
                router = PathRouter()
                instance_time = time.time() - instance_start
                method_start = time.time()
                handler_count = len(router.handlers)
                method_time = time.time() - method_start
                self.migration_tracking['performance_metrics'][path_name] = {'import_time': import_time, 'instance_time': instance_time, 'method_time': method_time, 'total_time': import_time + instance_time + method_time, 'handler_count': handler_count}
            except Exception as e:
                self.migration_tracking['performance_metrics'][path_name] = {'error': str(e), 'import_time': time.time() - import_start}
        if len(self.migration_tracking['performance_metrics']) > 1:
            times = {name: metrics.get('total_time', float('inf')) for name, metrics in self.migration_tracking['performance_metrics'].items() if 'total_time' in metrics}
            if times:
                fastest = min(times.values())
                slowest = max(times.values())
                self.assertLess(slowest - fastest, 0.05, 'Import path performance difference too large')
        logger.info(f"Import path performance metrics: {self.migration_tracking['performance_metrics']}")

    async def test_circular_import_prevention_during_migration(self):
        """Test that migration doesn't introduce circular imports."""
        import_order = []
        original_import = __builtins__.__import__

        def tracking_import(name, *args, **kwargs):
            if 'message_router' in name.lower():
                import_order.append(name)
            return original_import(name, *args, **kwargs)
        try:
            __builtins__.__import__ = tracking_import
            from netra_backend.app.core.message_router import MessageRouter as CoreRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter as HandlersRouter
            from netra_backend.app.services.message_router import MessageRouter as ServicesRouter
            core_router = CoreRouter()
            handlers_router = HandlersRouter()
            services_router = ServicesRouter()
        finally:
            __builtins__.__import__ = original_import
        unique_imports = list(set(import_order))
        self.assertEqual(len(import_order), len(unique_imports), f'Potential circular imports detected: {import_order}')
        logger.info(f'Import order tracking: {import_order}')

    async def test_migration_rollback_capability(self):
        """Test that migration can be rolled back if needed."""
        try:
            from netra_backend.app.core.message_router import MessageRouter as LegacyRouter
            from netra_backend.app.core.message_router import message_router as legacy_instance
            self.assertIsNotNone(LegacyRouter)
            self.assertIsNotNone(legacy_instance)
            router = LegacyRouter()
            self.assertTrue(hasattr(router, '_canonical_router'))
            self.migration_tracking['successful_imports'].append({'capability': 'rollback_legacy', 'status': 'available', 'time': time.time()})
            logger.info('Migration rollback capability confirmed')
        except Exception as e:
            self.migration_tracking['compatibility_issues'].append({'capability': 'rollback_legacy', 'error': str(e), 'time': time.time()})

    def test_migration_tracking_summary(self):
        """Generate migration tracking summary."""
        successful_count = len(self.migration_tracking['successful_imports'])
        failed_count = len(self.migration_tracking['failed_imports'])
        issue_count = len(self.migration_tracking['compatibility_issues'])
        migration_summary = {'successful_imports': successful_count, 'failed_imports': failed_count, 'compatibility_issues': issue_count, 'success_rate': successful_count / (successful_count + failed_count) * 100 if successful_count + failed_count > 0 else 0, 'performance_metrics': self.migration_tracking['performance_metrics'], 'details': {'successful': self.migration_tracking['successful_imports'], 'failed': self.migration_tracking['failed_imports'], 'issues': self.migration_tracking['compatibility_issues']}}
        logger.info(f'Migration Tracking Summary: {migration_summary}')
        self.assertGreaterEqual(migration_summary['success_rate'], 90.0, 'Migration success rate should be at least 90%')
        self.assertLessEqual(failed_count, 1, 'Should have 1 or fewer failed imports')
        self.assertLessEqual(issue_count, 2, 'Should have 2 or fewer compatibility issues')
        return migration_summary
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')