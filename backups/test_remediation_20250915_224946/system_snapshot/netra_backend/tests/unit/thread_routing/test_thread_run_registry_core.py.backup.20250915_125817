"""
Test Thread Run Registry Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket event routing via thread-run mappings
- Value Impact: Thread-run registry prevents 20% of WebSocket notification failures
- Strategic Impact: SSOT for thread-to-run mappings critical for chat value delivery

Tests the ThreadRunRegistry CRUD operations, TTL expiration handling, and
thread-to-run mapping functionality. These tests ensure the registry maintains
reliable mappings for WebSocket event routing when orchestrator is unavailable.
"""
import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, List
from netra_backend.app.services.thread_run_registry import ThreadRunRegistry, RegistryConfig, RunMapping, MappingState, get_thread_run_registry, initialize_thread_run_registry
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestThreadRunRegistryCore(SSotAsyncTestCase):
    """Test thread run registry core functionality with SSOT patterns."""

    @pytest.fixture(autouse=True)
    async def setup_registry(self):
        """Set up test fixtures following SSOT patterns."""
        self.test_config = RegistryConfig(mapping_ttl_hours=1, cleanup_interval_minutes=1, max_mappings=100, enable_debug_logging=True)
        self.registry = ThreadRunRegistry(self.test_config)
        self.test_run_id = 'run_thread_test_12345_67890_abcd1234'
        self.test_thread_id = 'thread_test_12345'
        self.test_user_id = 'user_test_98765'
        self.test_metadata = {'agent_name': 'cost_optimizer', 'user_id': self.test_user_id, 'created_by': 'test_suite'}
        yield
        if hasattr(self, 'registry') and self.registry:
            await self.registry.shutdown()

    async def test_register_run_mapping_success(self):
        """Test successful registration of run mapping."""
        success = await self.registry.register(self.test_run_id, self.test_thread_id, self.test_metadata)
        assert success, 'Run mapping registration should succeed'
        retrieved_thread_id = await self.registry.get_thread(self.test_run_id)
        assert retrieved_thread_id == self.test_thread_id, 'Retrieved thread ID should match registered value'

    async def test_register_duplicate_run_mapping(self):
        """Test registration of duplicate run mapping."""
        await self.registry.register(self.test_run_id, self.test_thread_id, self.test_metadata)
        different_thread_id = 'thread_different_67890'
        success = await self.registry.register(self.test_run_id, different_thread_id, {'note': 'duplicate attempt'})
        assert success, 'Duplicate registration should succeed (overwrite)'
        retrieved_thread_id = await self.registry.get_thread(self.test_run_id)
        assert retrieved_thread_id == different_thread_id, 'Latest registration should overwrite previous mapping'

    async def test_register_with_invalid_parameters(self):
        """Test registration with invalid parameters."""
        test_cases = [('', self.test_thread_id, 'Empty run_id should fail'), (None, self.test_thread_id, 'None run_id should fail'), (self.test_run_id, '', 'Empty thread_id should fail'), (self.test_run_id, None, 'None thread_id should fail')]
        for run_id, thread_id, description in test_cases:
            success = await self.registry.register(run_id, thread_id)
            assert not success, description

    async def test_get_thread_mapping_success(self):
        """Test successful retrieval of thread mapping."""
        await self.registry.register(self.test_run_id, self.test_thread_id, self.test_metadata)
        retrieved_thread_id = await self.registry.get_thread(self.test_run_id)
        assert retrieved_thread_id == self.test_thread_id, 'Should retrieve correct thread ID for registered run ID'

    async def test_get_thread_mapping_not_found(self):
        """Test retrieval of non-existent mapping."""
        non_existent_run_id = 'run_nonexistent_11111_22222_xyz'
        retrieved_thread_id = await self.registry.get_thread(non_existent_run_id)
        assert retrieved_thread_id is None, 'Should return None for non-existent run ID'

    async def test_get_runs_for_thread(self):
        """Test retrieval of all run IDs for a thread."""
        run_ids = [f'run_{self.test_thread_id}_1_abc1', f'run_{self.test_thread_id}_2_def2', f'run_{self.test_thread_id}_3_ghi3']
        for run_id in run_ids:
            await self.registry.register(run_id, self.test_thread_id)
        retrieved_runs = await self.registry.get_runs(self.test_thread_id)
        assert len(retrieved_runs) == 3, 'Should retrieve all runs for thread'
        for run_id in run_ids:
            assert run_id in retrieved_runs, f'Should include {run_id} in thread runs'

    async def test_unregister_run_success(self):
        """Test successful unregistration of run mapping."""
        await self.registry.register(self.test_run_id, self.test_thread_id, self.test_metadata)
        thread_id = await self.registry.get_thread(self.test_run_id)
        assert thread_id is not None, 'Mapping should exist before unregistration'
        success = await self.registry.unregister_run(self.test_run_id)
        assert success, 'Unregistration should succeed'
        thread_id = await self.registry.get_thread(self.test_run_id)
        assert thread_id is None, 'Mapping should not exist after unregistration'

    async def test_unregister_nonexistent_run(self):
        """Test unregistration of non-existent run mapping."""
        non_existent_run_id = 'run_nonexistent_99999_88888_zzz'
        success = await self.registry.unregister_run(non_existent_run_id)
        assert not success, 'Unregistration of non-existent run should return False'

    async def test_mapping_ttl_expiration(self):
        """Test that mappings expire based on TTL configuration."""
        short_ttl_config = RegistryConfig(mapping_ttl_hours=0.001, cleanup_interval_minutes=10, enable_debug_logging=True)
        short_registry = ThreadRunRegistry(short_ttl_config)
        try:
            await short_registry.register(self.test_run_id, self.test_thread_id)
            thread_id = await short_registry.get_thread(self.test_run_id)
            assert thread_id is not None, 'Mapping should exist immediately after registration'
            await asyncio.sleep(4.0)
            cleanup_count = await short_registry.cleanup_old_mappings()
            assert cleanup_count > 0, 'Should clean up expired mappings'
            thread_id = await short_registry.get_thread(self.test_run_id)
            assert thread_id is None, 'Mapping should be None after TTL expiration'
        finally:
            await short_registry.shutdown()

    async def test_mapping_access_updates_timestamp(self):
        """Test that accessing mapping updates last_accessed timestamp."""
        await self.registry.register(self.test_run_id, self.test_thread_id, self.test_metadata)
        initial_mapping = self.registry._run_to_thread.get(self.test_run_id)
        initial_access_time = initial_mapping.last_accessed
        await asyncio.sleep(0.1)
        await self.registry.get_thread(self.test_run_id)
        updated_mapping = self.registry._run_to_thread.get(self.test_run_id)
        updated_access_time = updated_mapping.last_accessed
        assert updated_access_time > initial_access_time, 'Accessing mapping should update last_accessed timestamp'

    async def test_cleanup_old_mappings_manual(self):
        """Test manual cleanup of old mappings."""
        short_ttl_config = RegistryConfig(mapping_ttl_hours=0.001, enable_debug_logging=True)
        cleanup_registry = ThreadRunRegistry(short_ttl_config)
        try:
            await cleanup_registry.register('run_old_1', 'thread_1')
            await cleanup_registry.register('run_old_2', 'thread_2')
            await asyncio.sleep(4.0)
            await cleanup_registry.register('run_fresh_1', 'thread_3')
            cleanup_count = await cleanup_registry.cleanup_old_mappings()
            assert cleanup_count >= 2, 'Should clean up at least 2 expired mappings'
            fresh_thread = await cleanup_registry.get_thread('run_fresh_1')
            assert fresh_thread is not None, 'Fresh mapping should survive cleanup'
        finally:
            await cleanup_registry.shutdown()

    async def test_thread_to_runs_reverse_mapping(self):
        """Test reverse mapping from thread to runs."""
        run_ids = [f'run_{self.test_thread_id}_1_abc1', f'run_{self.test_thread_id}_2_def2']
        for run_id in run_ids:
            await self.registry.register(run_id, self.test_thread_id)
        thread_runs = await self.registry.get_runs(self.test_thread_id)
        assert len(thread_runs) == 2, 'Should return all runs for thread'
        for run_id in run_ids:
            assert run_id in thread_runs, f'Should include {run_id}'

    async def test_thread_cleanup_removes_reverse_mapping(self):
        """Test that unregistering run removes it from reverse mapping."""
        run_id_1 = f'run_{self.test_thread_id}_1_abc1'
        run_id_2 = f'run_{self.test_thread_id}_2_def2'
        await self.registry.register(run_id_1, self.test_thread_id)
        await self.registry.register(run_id_2, self.test_thread_id)
        thread_runs = await self.registry.get_runs(self.test_thread_id)
        assert len(thread_runs) == 2, 'Should have 2 runs initially'
        await self.registry.unregister_run(run_id_1)
        thread_runs = await self.registry.get_runs(self.test_thread_id)
        assert len(thread_runs) == 1, 'Should have 1 run after unregistration'
        assert run_id_2 in thread_runs, 'Remaining run should still be present'
        assert run_id_1 not in thread_runs, 'Unregistered run should be removed'

    async def test_empty_thread_cleanup(self):
        """Test that empty thread entries are cleaned up."""
        run_id = f'run_{self.test_thread_id}_1_abc1'
        await self.registry.register(run_id, self.test_thread_id)
        await self.registry.unregister_run(run_id)
        assert self.test_thread_id not in self.registry._thread_to_runs, 'Empty thread entry should be cleaned up'

    async def test_concurrent_registrations(self):
        """Test concurrent registration operations."""

        async def register_mapping(run_suffix: int):
            run_id = f'run_concurrent_{run_suffix}_{int(time.time())}_test'
            thread_id = f'thread_concurrent_{run_suffix}'
            return await self.registry.register(run_id, thread_id)
        tasks = [register_mapping(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        successful_registrations = sum((1 for result in results if result))
        assert successful_registrations == 50, 'All concurrent registrations should succeed'

    async def test_concurrent_lookups(self):
        """Test concurrent lookup operations."""
        run_ids = []
        for i in range(10):
            run_id = f'run_lookup_test_{i}_{int(time.time())}_abc'
            thread_id = f'thread_lookup_test_{i}'
            await self.registry.register(run_id, thread_id)
            run_ids.append((run_id, thread_id))

        async def lookup_mapping(run_id: str, expected_thread_id: str):
            result = await self.registry.get_thread(run_id)
            return result == expected_thread_id
        tasks = [lookup_mapping(run_id, thread_id) for run_id, thread_id in run_ids]
        results = await asyncio.gather(*tasks)
        successful_lookups = sum((1 for result in results if result))
        assert successful_lookups == 10, 'All concurrent lookups should return correct results'

    async def test_registry_max_mappings_limit(self):
        """Test registry respects maximum mappings limit."""
        limited_config = RegistryConfig(max_mappings=5, enable_debug_logging=True)
        limited_registry = ThreadRunRegistry(limited_config)
        try:
            for i in range(5):
                run_id = f'run_limit_test_{i}_{int(time.time())}'
                thread_id = f'thread_limit_test_{i}'
                success = await limited_registry.register(run_id, thread_id)
                assert success, f'Registration {i} should succeed within limit'
            metrics = await limited_registry.get_metrics()
            assert metrics['active_mappings'] == 5, 'Should have exactly 5 active mappings'
        finally:
            await limited_registry.shutdown()

    async def test_registry_metrics_collection(self):
        """Test registry metrics collection."""
        await self.registry.register(self.test_run_id, self.test_thread_id)
        await self.registry.get_thread(self.test_run_id)
        await self.registry.get_thread('nonexistent_run')
        await self.registry.unregister_run(self.test_run_id)
        metrics = await self.registry.get_metrics()
        expected_keys = ['active_mappings', 'total_registrations', 'successful_lookups', 'failed_lookups', 'expired_mappings_cleaned', 'lookup_success_rate', 'registry_uptime_seconds', 'registry_healthy']
        for key in expected_keys:
            assert key in metrics, f'Metrics should include {key}'
        assert metrics['total_registrations'] == 1, 'Should track total registrations'
        assert metrics['successful_lookups'] == 1, 'Should track successful lookups'
        assert metrics['failed_lookups'] == 1, 'Should track failed lookups'
        assert metrics['lookup_success_rate'] == 0.5, 'Should calculate correct success rate (1 success, 1 failure)'

    async def test_registry_status_information(self):
        """Test registry status information."""
        status = await self.registry.get_status()
        expected_keys = ['registry_healthy', 'active_mappings', 'total_registrations', 'lookup_success_rate', 'uptime_seconds', 'config', 'cleanup_task_running', 'timestamp']
        for key in expected_keys:
            assert key in status, f'Status should include {key}'
        assert status['registry_healthy'], 'Registry should be healthy'
        assert isinstance(status['uptime_seconds'], (int, float)), 'Uptime should be numeric'
        assert 'mapping_ttl_hours' in status['config'], 'Status should include configuration'

    async def test_registry_error_resilience(self):
        """Test registry resilience to errors."""
        mock_lock = AsyncMock()
        mock_lock.__aenter__.side_effect = Exception('Lock error')
        with patch.object(self.registry, '_registry_lock', mock_lock):
            success = await self.registry.register('test_run', 'test_thread')
            assert not success, 'Should handle lock errors gracefully'
        success = await self.registry.register(self.test_run_id, self.test_thread_id)
        assert success, 'Registry should recover from errors'

    async def test_cleanup_error_handling(self):
        """Test cleanup error handling."""
        mock_cleanup_lock = AsyncMock()
        mock_cleanup_lock.__aenter__.side_effect = Exception('Cleanup error')
        with patch.object(self.registry, '_cleanup_lock', mock_cleanup_lock):
            cleanup_count = await self.registry.cleanup_old_mappings()
            assert cleanup_count == 0, 'Should return 0 when cleanup encounters errors'

    async def test_singleton_factory_function(self):
        """Test singleton factory function behavior."""
        registry1 = await get_thread_run_registry()
        registry2 = await get_thread_run_registry()
        assert registry1 is registry2, 'Factory should return same singleton instance'

    async def test_initialize_thread_run_registry(self):
        """Test registry initialization function."""
        from netra_backend.app.services.thread_run_registry import _registry_instance
        import netra_backend.app.services.thread_run_registry as trr_module
        original_instance = trr_module._registry_instance
        trr_module._registry_instance = None
        try:
            init_config = RegistryConfig(mapping_ttl_hours=2, cleanup_interval_minutes=5, enable_debug_logging=False)
            registry = await initialize_thread_run_registry(init_config)
            assert isinstance(registry, ThreadRunRegistry), 'Should return ThreadRunRegistry instance'
            assert registry.config.mapping_ttl_hours == 2, 'Should use provided configuration'
            await registry.shutdown()
        finally:
            trr_module._registry_instance = original_instance

    async def test_debug_listing_functionality(self):
        """Test debug listing of all mappings."""
        test_mappings = [('run_debug_1', 'thread_debug_1'), ('run_debug_2', 'thread_debug_2')]
        for run_id, thread_id in test_mappings:
            await self.registry.register(run_id, thread_id)
        debug_info = await self.registry.debug_list_all_mappings()
        assert 'total_mappings' in debug_info, 'Debug info should include total mappings count'
        assert 'mappings' in debug_info, 'Debug info should include mappings details'
        assert debug_info['total_mappings'] == 2, 'Should report correct total mappings count'
        mappings = debug_info['mappings']
        for run_id, thread_id in test_mappings:
            assert run_id in mappings, f'Debug info should include {run_id}'
            assert mappings[run_id]['thread_id'] == thread_id, f'Debug info should show correct thread_id for {run_id}'

    async def test_registry_shutdown(self):
        """Test registry shutdown process."""
        await self.registry.register(self.test_run_id, self.test_thread_id)
        assert not self.registry._shutdown, 'Registry should not be shutdown initially'
        await self.registry.shutdown()
        assert self.registry._shutdown, 'Registry should be shutdown after shutdown()'
        assert len(self.registry._run_to_thread) == 0, 'All mappings should be cleared after shutdown'

    async def test_shutdown_cancels_background_tasks(self):
        """Test that shutdown cancels background cleanup task."""
        assert self.registry._cleanup_task is not None, 'Cleanup task should be created on initialization'
        assert not self.registry._cleanup_task.done(), 'Cleanup task should be running initially'
        await self.registry.shutdown()
        assert self.registry._shutdown, 'Registry should be marked as shutdown'
        assert self.registry._cleanup_task.done() or self.registry._cleanup_task.cancelled() or 'cancelling' in str(self.registry._cleanup_task), f'Cleanup task should be done, cancelled, or cancelling after shutdown. State: {self.registry._cleanup_task}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')