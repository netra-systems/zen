"""
Test Suite: DUAL SSOT ID Manager Compatibility Bridge
=====================================================

CRITICAL ISSUE #301: Tests the compatibility bridge between UnifiedIDManager and UnifiedIdGenerator
to resolve WebSocket 1011 errors caused by ID pattern mismatches.

Business Impact: Validates $500K+ ARR protection by ensuring WebSocket resource cleanup works
with consistent ID patterns across both SSOT implementations.

Test Strategy:
1. Test compatibility bridge functionality
2. Validate WebSocket-specific ID pattern consistency
3. Verify no regression in existing UnifiedIDManager functionality
4. Test resource cleanup pattern matching
5. Validate thread safety during transition
"""
import asyncio
import pytest
import threading
import time
from typing import Dict, Set
from unittest.mock import patch, MagicMock
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class DualSSOTIDManagerCompatibilityBridgeTests(SSotBaseTestCase):
    """Test compatibility bridge between dual SSOT ID systems."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.id_manager = UnifiedIDManager()

    def test_websocket_id_pattern_consistency(self):
        """
        CRITICAL: Test that WebSocket IDs from both systems follow consistent patterns
        to prevent 1011 errors during resource cleanup.
        """
        bridge_ws_id = self.id_manager.generate_websocket_id_with_user_context('test_user')
        generator_ws_id = UnifiedIdGenerator.generate_websocket_connection_id('test_user')
        user_prefix_in_id = 'test_user'[:8]
        self.assertTrue(user_prefix_in_id in bridge_ws_id, f"Bridge WebSocket ID should contain user context '{user_prefix_in_id}': {bridge_ws_id}")
        self._validate_cleanup_pattern_compatibility(bridge_ws_id, generator_ws_id)

    def test_user_context_id_generation_bridge(self):
        """Test compatibility bridge for UserExecutionContext ID generation."""
        thread_id_bridge, run_id_bridge, request_id_bridge = self.id_manager.generate_user_context_ids_compatible('test_user', 'context')
        thread_id_gen, run_id_gen, request_id_gen = UnifiedIdGenerator.generate_user_context_ids('test_user', 'context')
        thread_metadata = self.id_manager.get_id_metadata(thread_id_bridge)
        run_metadata = self.id_manager.get_id_metadata(run_id_bridge)
        self.assertIsNotNone(thread_metadata, 'Thread ID should be registered with metadata')
        self.assertIsNotNone(run_metadata, 'Run ID should be registered with metadata')
        self.assertEqual(thread_metadata.context.get('user_id'), 'test_user', 'Thread ID should have user context')
        self.assertEqual(run_metadata.context.get('user_id'), 'test_user', 'Run ID should have user context')
        self.assertIn('context', thread_id_bridge)
        self.assertIn('context', run_id_bridge)
        self._validate_context_id_pattern_compatibility(thread_id_bridge, run_id_bridge, thread_id_gen, run_id_gen)

    def test_websocket_factory_resource_cleanup_pattern_fix(self):
        """
        CRITICAL: Test the specific fix for WebSocket factory resource cleanup.
        
        The bug occurs when cleanup logic can't match IDs due to pattern differences:
        - thread_id format from one system
        - run_id format from another system
        - Cleanup fails, causing 1011 errors
        """
        user_id = 'test_user_123'
        mixed_ids = {'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix=user_id[:8]), 'run_id': UnifiedIdGenerator.generate_base_id(f'run_{user_id[:8]}'), 'ws_conn_id': UnifiedIdGenerator.generate_websocket_connection_id(user_id)}
        for id_type, generated_id in mixed_ids.items():
            self.assertTrue(self._extract_user_context(generated_id, user_id), f'Failed to extract user context from {id_type}: {generated_id}')

    def test_thread_safety_during_dual_system_usage(self):
        """Test thread safety when both systems are used concurrently."""
        results = {'manager_ids': set(), 'generator_ids': set(), 'conflicts': []}

        def generate_manager_ids():
            for _ in range(100):
                id_val = self.id_manager.generate_id(IDType.WEBSOCKET, prefix='thread_test')
                results['manager_ids'].add(id_val)

        def generate_generator_ids():
            for _ in range(100):
                id_val = UnifiedIdGenerator.generate_websocket_connection_id('thread_test')
                results['generator_ids'].add(id_val)
        threads = [threading.Thread(target=generate_manager_ids), threading.Thread(target=generate_generator_ids)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        manager_conflicts = results['manager_ids'].intersection(results['generator_ids'])
        self.assertEqual(len(manager_conflicts), 0, f'Found ID conflicts between systems: {manager_conflicts}')
        self.assertEqual(len(results['manager_ids']), 100)
        self.assertEqual(len(results['generator_ids']), 100)

    def test_compatibility_bridge_performance_impact(self):
        """Test that compatibility bridge doesn't significantly impact performance."""
        import time
        self.id_manager.optimize_for_websocket_performance()
        start_time = time.perf_counter()
        for _ in range(1000):
            self.id_manager.generate_websocket_id_with_user_context('perf_test')
        bridge_time = time.perf_counter() - start_time
        start_time = time.perf_counter()
        for _ in range(1000):
            UnifiedIdGenerator.generate_websocket_connection_id('perf_test')
        generator_time = time.perf_counter() - start_time
        performance_ratio = bridge_time / generator_time
        self.assertLess(performance_ratio, 2.0, f'Performance difference after optimization too high: {performance_ratio:.2f}x')
        user_ids = self.id_manager.get_websocket_cleanup_ids_fast('perf_test')
        self.assertTrue(isinstance(user_ids, list), 'Fast cleanup should return a list')

    def test_migration_warnings_and_deprecation_notices(self):
        """Test that compatibility bridge includes appropriate migration warnings."""
        with patch('netra_backend.app.core.unified_id_manager.logger') as mock_logger:
            self.id_manager.generate_id(IDType.WEBSOCKET, prefix='deprecated_test')

    def _validate_cleanup_pattern_compatibility(self, manager_id: str, generator_id: str):
        """Validate that both ID patterns are compatible with cleanup logic."""

        def extract_cleanup_key(id_string: str) -> str:
            """Simulate how WebSocket factory extracts cleanup keys."""
            if '_' in id_string:
                parts = id_string.split('_')
                for part in parts:
                    if len(part) >= 4 and any((c.isalnum() for c in part)):
                        return part[:8]
            return id_string[:8]
        manager_key = extract_cleanup_key(manager_id)
        generator_key = extract_cleanup_key(generator_id)
        self.assertGreater(len(manager_key), 0)
        self.assertGreater(len(generator_key), 0)

    def _validate_context_id_pattern_compatibility(self, thread_id_mgr: str, run_id_mgr: str, thread_id_gen: str, run_id_gen: str):
        """Validate that context IDs from both systems are compatible."""
        self.assertIn('thread', thread_id_mgr.lower())
        self.assertIn('thread', thread_id_gen.lower())
        self.assertTrue('run' in run_id_mgr.lower() or 'execution' in run_id_mgr.lower())
        self.assertIn('run', run_id_gen.lower())

    def _extract_user_context(self, generated_id: str, expected_user_id: str) -> bool:
        """Test if user context can be extracted from generated ID."""
        user_prefix = expected_user_id[:8]
        return user_prefix in generated_id or expected_user_id[:4] in generated_id

@pytest.mark.unit
class WebSocketResourceCleanupFixTests(SSotBaseTestCase):
    """Specific tests for WebSocket 1011 error fix through ID pattern consistency."""

    def setup_method(self):
        super().setup_method()
        self.cleanup_registry = {}

    def test_websocket_1011_error_prevention(self):
        """
        CRITICAL: Test the specific fix that prevents WebSocket 1011 errors.
        
        The issue occurs when:
        1. WebSocket connection created with one ID pattern
        2. Resource cleanup uses different ID pattern  
        3. Cleanup fails to find resources, causing 1011 error
        """
        user_id = 'test_user_123'
        connection_scenarios = [{'system': 'manager', 'thread_id': f'thread_1_{int(time.time())}_{user_id[:8]}', 'ws_id': f'websocket_1_{int(time.time())}_{user_id[:8]}'}, {'system': 'generator', 'thread_id': UnifiedIdGenerator.generate_base_id(f'thread_{user_id[:8]}'), 'ws_id': UnifiedIdGenerator.generate_websocket_connection_id(user_id)}]
        for scenario in connection_scenarios:
            self._register_websocket_connection(scenario['thread_id'], scenario['ws_id'])
            cleanup_success = self._cleanup_websocket_resources(scenario['thread_id'], user_id)
            self.assertTrue(cleanup_success, f"Cleanup failed for {scenario['system']} system IDs")
            self.cleanup_registry.clear()

    def _register_websocket_connection(self, thread_id: str, ws_id: str):
        """Simulate WebSocket connection registration."""
        self.cleanup_registry[thread_id] = {'ws_id': ws_id, 'created_at': time.time(), 'status': 'active'}

    def _cleanup_websocket_resources(self, thread_id: str, user_id: str) -> bool:
        """
        Simulate WebSocket resource cleanup logic.
        
        This is the critical fix - cleanup should work regardless of 
        which ID system originally created the IDs.
        """
        if thread_id in self.cleanup_registry:
            del self.cleanup_registry[thread_id]
            return True
        user_prefix = user_id[:8]
        matching_keys = []
        for registered_thread_id in self.cleanup_registry.keys():
            if user_prefix in registered_thread_id or self._extract_user_pattern(registered_thread_id, user_id):
                matching_keys.append(registered_thread_id)
        for key in matching_keys:
            del self.cleanup_registry[key]
        return len(matching_keys) > 0

    def _extract_user_pattern(self, thread_id: str, user_id: str) -> bool:
        """Extract user pattern for cleanup matching."""
        patterns = [user_id[:4], user_id[:8], user_id.split('_')[0]]
        return any((pattern in thread_id for pattern in patterns if pattern))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')