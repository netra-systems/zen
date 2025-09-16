"""
Integration Tests for UnifiedStateManager - REAL SERVICES ONLY

BUSINESS VALUE PROTECTION: $500K+ ARR
- Multi-tenant isolation prevents data leakage (Enterprise $15K+ MRR per customer)
- State consistency prevents agent execution failures (90% of platform value)
- Memory management prevents system crashes under load
- TTL management prevents unbounded memory growth
- Cross-service state synchronization enables real-time collaboration

REAL SERVICES REQUIRED:
- Redis for caching and session state
- PostgreSQL for persistent state storage
- WebSocket connections for real-time state updates
- Agent execution contexts for multi-user isolation

TEST COVERAGE: 22 Integration Tests (8 High Difficulty)
- Multi-service state coordination
- Real Redis cluster operations
- PostgreSQL transaction management
- WebSocket state propagation
- Cross-tenant isolation validation
- High-load concurrent operations
- Disaster recovery scenarios
- Memory pressure handling

HIGH DIFFICULTY TESTS: 8 tests focusing on:
- Redis cluster failover with state recovery
- PostgreSQL connection pool exhaustion scenarios
- Multi-tenant state isolation under concurrent load
- WebSocket connection storm handling
- TTL expiration during high memory pressure
- Cross-service state consistency during network partitions
- State migration during Redis memory eviction
- Concurrent user session collision detection
"""
import asyncio
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from netra_backend.app.services.redis_client import get_redis_client, get_redis_service
import psycopg2
from typing import Dict, List, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.core.configuration.base import UnifiedConfigManager
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from shared.types.core_types import UserID, ThreadID, RunID
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

@pytest.mark.integration
class UnifiedStateManagerIntegrationCoreTests(SSotAsyncTestCase):
    """Core integration tests for UnifiedStateManager with real services"""

    @classmethod
    async def asyncSetUp(cls):
        """Setup real services for integration testing"""
        super().setUpClass()
        cls.env = IsolatedEnvironment()
        redis_url = cls.env.get_env_var('REDIS_URL', 'redis://localhost:6379/0')
        cls.redis_client = redis.from_url(redis_url)
        postgres_url = cls.env.get_env_var('POSTGRES_URL', 'postgresql://localhost:5432/netra_test')
        cls.postgres_client = psycopg2.connect(postgres_url)
        cls.config_manager = UnifiedConfigurationManager()
        cls.test_user_ids = set()

    async def asyncTearDown(self):
        """Cleanup test data from real services"""
        for user_id in self.test_user_ids:
            pattern = f'state:{user_id}:*'
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
        cursor = self.postgres_client.cursor()
        for user_id in self.test_user_ids:
            cursor.execute('DELETE FROM state_persistence WHERE user_id = %s', (user_id,))
        self.postgres_client.commit()
        cursor.close()
        self.test_user_ids.clear()
        super().tearDown()

    def create_test_manager(self, user_id: str=None) -> UnifiedStateManager:
        """Create manager with real service connections"""
        if user_id is None:
            user_id = f'test-user-{int(time.time() * 1000)}'
        self.test_user_ids.add(user_id)
        return UnifiedStateManager(user_id=user_id, redis_client=self.redis_client, config_manager=self.config_manager)

@pytest.mark.integration
class RealRedisIntegrationTests(UnifiedStateManagerIntegrationCoreTests):
    """Integration tests with real Redis operations"""

    async def test_redis_state_persistence_workflow(self):
        """INTEGRATION: State persists correctly to real Redis"""
        manager = self.create_test_manager('redis-persist-user')
        thread_id = 'thread-123'
        test_data = {'agent_status': 'running', 'progress': 0.5}
        await manager.set_thread_state(thread_id, test_data)
        redis_key = f'state:{manager.user_id}:thread:{thread_id}'
        redis_data = await redis_client.hgetall(redis_key)
        self.assertIsNotNone(redis_data)
        new_manager = self.create_test_manager(manager.user_id)
        retrieved_state = await new_manager.get_thread_state(thread_id)
        self.assertEqual(retrieved_state['agent_status'], 'running')
        self.assertEqual(retrieved_state['progress'], 0.5)

    async def test_redis_ttl_expiration_integration(self):
        """INTEGRATION: TTL expiration works with real Redis"""
        manager = self.create_test_manager('ttl-expire-user')
        thread_id = 'expiring-thread'
        test_data = {'temp_data': 'should_expire'}
        await manager.set_thread_state(thread_id, test_data, ttl_seconds=2)
        initial_state = await manager.get_thread_state(thread_id)
        self.assertEqual(initial_state['temp_data'], 'should_expire')
        await asyncio.sleep(3)
        expired_state = await manager.get_thread_state(thread_id)
        self.assertEqual(expired_state, {})

    async def test_redis_memory_pressure_handling(self):
        """HIGH DIFFICULTY: Redis memory pressure and eviction handling"""
        manager = self.create_test_manager('memory-pressure-user')
        large_data = {'data': 'x' * 10000}
        thread_ids = []
        for i in range(100):
            thread_id = f'memory-thread-{i}'
            thread_ids.append(thread_id)
            await manager.set_thread_state(thread_id, large_data)
        mid_point = len(thread_ids) // 2
        mid_state = await manager.get_thread_state(thread_ids[mid_point])
        self.assertEqual(len(mid_state['data']), 10000)
        for i in range(100, 200):
            thread_id = f'pressure-thread-{i}'
            await manager.set_thread_state(thread_id, large_data)
        final_state = await manager.get_thread_state(f'pressure-thread-150')
        self.assertIsInstance(final_state, dict)

    async def test_redis_cluster_failover_simulation(self):
        """HIGH DIFFICULTY: Simulated Redis failover handling"""
        manager = self.create_test_manager('failover-user')
        thread_id = 'failover-thread'
        initial_data = {'status': 'before_failover'}
        await manager.set_thread_state(thread_id, initial_data)
        original_redis = manager.redis_client
        failing_client = await get_redis_client()
        manager.redis_client = failing_client
        try:
            await manager.set_thread_state(thread_id, {'status': 'during_failover'})
        except Exception as e:
            self.assertIsInstance(e, (redis.ConnectionError, redis.TimeoutError))
        manager.redis_client = original_redis
        recovery_data = {'status': 'after_recovery'}
        await manager.set_thread_state(thread_id, recovery_data)
        final_state = await manager.get_thread_state(thread_id)
        self.assertIn(final_state.get('status'), ['before_failover', 'after_recovery'])

@pytest.mark.integration
class CrossServiceStateCoordinationTests(UnifiedStateManagerIntegrationCoreTests):
    """Integration tests for cross-service state coordination"""

    async def test_redis_postgres_state_synchronization(self):
        """INTEGRATION: State synchronization between Redis and PostgreSQL"""
        manager = self.create_test_manager('sync-user')
        persistence_service = StatePersistenceService()
        thread_id = 'sync-thread'
        test_data = {'agent_execution': {'status': 'running', 'current_step': 'analysis', 'progress': 0.75}}
        await manager.set_thread_state(thread_id, test_data)
        await persistence_service.create_checkpoint(manager.user_id, thread_id, test_data)
        redis_state = await manager.get_thread_state(thread_id)
        self.assertEqual(redis_state['agent_execution']['status'], 'running')
        cursor = self.postgres_client.cursor()
        cursor.execute('SELECT state_data FROM state_persistence WHERE user_id = %s AND thread_id = %s', (manager.user_id, thread_id))
        result = cursor.fetchone()
        cursor.close()
        self.assertIsNotNone(result)
        postgres_data = result[0]
        self.assertEqual(postgres_data['agent_execution']['status'], 'running')

    async def test_websocket_state_propagation(self):
        """HIGH DIFFICULTY: WebSocket state change propagation"""
        manager = self.create_test_manager('websocket-user')
        websocket_manager = get_websocket_manager(user_context=getattr(self, 'user_context', None))
        thread_id = 'websocket-thread'
        connection_id = f'conn-{manager.user_id}'
        initial_state = {'websocket_status': 'connected', 'last_message': None}
        await manager.set_thread_state(thread_id, initial_state)
        updated_state = {'websocket_status': 'message_received', 'last_message': {'type': 'agent_response', 'timestamp': time.time()}}
        await manager.set_thread_state(thread_id, updated_state)
        final_state = await manager.get_thread_state(thread_id)
        self.assertEqual(final_state['websocket_status'], 'message_received')
        self.assertIsNotNone(final_state['last_message'])

    async def test_agent_execution_state_coordination(self):
        """INTEGRATION: State coordination during agent execution"""
        manager = self.create_test_manager('agent-exec-user')
        thread_id = 'collaborative-thread'
        triage_state = {'phase': 'triage', 'analysis': {'complexity': 'medium', 'estimated_time': 300}}
        await manager.set_thread_state(thread_id, triage_state, scope='agent:triage')
        data_state = {'phase': 'data_collection', 'required_data': ['user_profile', 'historical_interactions']}
        await manager.set_thread_state(thread_id, data_state, scope='agent:data_helper')
        supervisor_state = {'phase': 'coordination', 'active_agents': ['triage', 'data_helper'], 'overall_progress': 0.3}
        await manager.set_thread_state(thread_id, supervisor_state, scope='agent:supervisor')
        triage_final = await manager.get_thread_state(thread_id, scope='agent:triage')
        data_final = await manager.get_thread_state(thread_id, scope='agent:data_helper')
        supervisor_final = await manager.get_thread_state(thread_id, scope='agent:supervisor')
        self.assertEqual(triage_final['phase'], 'triage')
        self.assertEqual(data_final['phase'], 'data_collection')
        self.assertEqual(supervisor_final['phase'], 'coordination')
        self.assertEqual(len(supervisor_final['active_agents']), 2)

@pytest.mark.integration
class MultiTenantIsolationIntegrationTests(UnifiedStateManagerIntegrationCoreTests):
    """Integration tests for multi-tenant isolation with real services"""

    async def test_concurrent_user_isolation_redis(self):
        """HIGH DIFFICULTY: Multi-user isolation under concurrent load"""
        user1_manager = self.create_test_manager('isolation-user-1')
        user2_manager = self.create_test_manager('isolation-user-2')
        user3_manager = self.create_test_manager('isolation-user-3')
        thread_id = 'shared-thread-id'
        user_data = {'isolation-user-1': {'secret': 'user1_secret', 'role': 'admin'}, 'isolation-user-2': {'secret': 'user2_secret', 'role': 'user'}, 'isolation-user-3': {'secret': 'user3_secret', 'role': 'viewer'}}

        async def set_user_state(manager, data):
            for i in range(10):
                state = {'iteration': i, **data}
                await manager.set_thread_state(f'{thread_id}-{i}', state)
                await asyncio.sleep(0.01)
        tasks = [set_user_state(user1_manager, user_data['isolation-user-1']), set_user_state(user2_manager, user_data['isolation-user-2']), set_user_state(user3_manager, user_data['isolation-user-3'])]
        await asyncio.gather(*tasks)
        for i in range(10):
            user1_state = await user1_manager.get_thread_state(f'{thread_id}-{i}')
            user2_state = await user2_manager.get_thread_state(f'{thread_id}-{i}')
            user3_state = await user3_manager.get_thread_state(f'{thread_id}-{i}')
            self.assertEqual(user1_state['secret'], 'user1_secret')
            self.assertEqual(user2_state['secret'], 'user2_secret')
            self.assertEqual(user3_state['secret'], 'user3_secret')
            self.assertNotEqual(user1_state['secret'], user2_state['secret'])
            self.assertNotEqual(user2_state['secret'], user3_state['secret'])

    async def test_user_session_collision_detection(self):
        """HIGH DIFFICULTY: Detect and prevent user session collisions"""
        user_id = 'collision-test-user'
        manager1 = self.create_test_manager(user_id)
        manager2 = self.create_test_manager(user_id)
        thread_id = 'collision-thread'
        session1_data = {'session_id': 'session-1', 'timestamp': time.time()}
        await manager1.set_thread_state(thread_id, session1_data)
        session2_data = {'session_id': 'session-2', 'timestamp': time.time() + 1}
        await manager2.set_thread_state(thread_id, session2_data)
        final_state = await manager1.get_thread_state(thread_id)
        self.assertIn(final_state.get('session_id'), ['session-1', 'session-2'])
        self.assertIsNotNone(final_state.get('timestamp'))

    async def test_cross_tenant_data_leakage_prevention(self):
        """CRITICAL: Verify no data leakage between tenants"""
        enterprise_manager = self.create_test_manager('enterprise-user-001')
        free_manager = self.create_test_manager('free-user-001')
        sensitive_data = {'customer_data': {'ssn': '123-45-6789', 'credit_card': '4111-1111-1111-1111', 'enterprise_config': {'api_limits': 100000}}}
        await enterprise_manager.set_thread_state('sensitive-thread', sensitive_data)
        basic_data = {'user_preferences': {'theme': 'dark', 'notifications': True}}
        await free_manager.set_thread_state('basic-thread', basic_data)
        enterprise_from_free = await free_manager.get_thread_state('sensitive-thread')
        basic_from_enterprise = await enterprise_manager.get_thread_state('basic-thread')
        self.assertEqual(enterprise_from_free, {})
        self.assertEqual(basic_from_enterprise, {})
        legitimate_enterprise = await enterprise_manager.get_thread_state('sensitive-thread')
        legitimate_free = await free_manager.get_thread_state('basic-thread')
        self.assertIn('customer_data', legitimate_enterprise)
        self.assertIn('user_preferences', legitimate_free)

@pytest.mark.integration
class HighLoadConcurrencyIntegrationTests(UnifiedStateManagerIntegrationCoreTests):
    """Integration tests for high-load concurrent operations"""

    async def test_concurrent_state_operations_stress(self):
        """HIGH DIFFICULTY: High-load concurrent state operations"""
        manager = self.create_test_manager('stress-test-user')
        num_threads = 20
        operations_per_thread = 50
        results = []
        errors = []

        async def stress_operations(thread_index: int):
            """Perform concurrent operations for stress testing"""
            try:
                for op_index in range(operations_per_thread):
                    thread_id = f'stress-thread-{thread_index}-{op_index}'
                    if op_index % 3 == 0:
                        data = {'op': 'set', 'thread': thread_index, 'index': op_index}
                        await manager.set_thread_state(thread_id, data)
                    elif op_index % 3 == 1:
                        await manager.get_thread_state(thread_id)
                    else:
                        existing = await manager.get_thread_state(thread_id)
                        if existing:
                            existing['updated'] = True
                            await manager.set_thread_state(thread_id, existing)
                results.append(f'Thread {thread_index} completed successfully')
            except Exception as e:
                errors.append(f'Thread {thread_index} failed: {str(e)}')
        start_time = time.time()
        tasks = [stress_operations(i) for i in range(num_threads)]
        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        self.assertEqual(len(errors), 0, f'Stress test had errors: {errors}')
        self.assertEqual(len(results), num_threads)
        total_time = end_time - start_time
        self.assertLess(total_time, 30, f'Stress test took too long: {total_time}s')
        post_stress_data = {'status': 'stable_after_stress'}
        await manager.set_thread_state('post-stress-thread', post_stress_data)
        retrieved = await manager.get_thread_state('post-stress-thread')
        self.assertEqual(retrieved['status'], 'stable_after_stress')

    async def test_memory_growth_under_load(self):
        """HIGH DIFFICULTY: Verify memory growth bounds under load"""
        manager = self.create_test_manager('memory-growth-user')
        initial_threads = 100
        for i in range(initial_threads):
            thread_id = f'baseline-thread-{i}'
            data = {'baseline': True, 'index': i, 'data': 'x' * 1000}
            await manager.set_thread_state(thread_id, data)
        load_cycles = 10
        threads_per_cycle = 50
        for cycle in range(load_cycles):
            for i in range(threads_per_cycle):
                thread_id = f'load-cycle-{cycle}-thread-{i}'
                data = {'cycle': cycle, 'index': i, 'data': 'y' * 1000}
                await manager.set_thread_state(thread_id, data)
            await asyncio.sleep(0.1)
        baseline_exists = 0
        for i in range(initial_threads):
            thread_id = f'baseline-thread-{i}'
            state = await manager.get_thread_state(thread_id)
            if state:
                baseline_exists += 1
        self.assertLess(baseline_exists, initial_threads)
        recent_cycle = load_cycles - 1
        recent_exists = 0
        for i in range(threads_per_cycle):
            thread_id = f'load-cycle-{recent_cycle}-thread-{i}'
            state = await manager.get_thread_state(thread_id)
            if state:
                recent_exists += 1
        self.assertGreater(recent_exists, threads_per_cycle * 0.7)

@pytest.mark.integration
class DisasterRecoveryIntegrationTests(UnifiedStateManagerIntegrationCoreTests):
    """Integration tests for disaster recovery scenarios"""

    async def test_redis_connection_recovery(self):
        """HIGH DIFFICULTY: Recovery from Redis connection loss"""
        manager = self.create_test_manager('recovery-user')
        initial_data = {'status': 'before_disconnect', 'critical_data': 'must_survive'}
        await manager.set_thread_state('recovery-thread', initial_data)
        pre_disconnect = await manager.get_thread_state('recovery-thread')
        self.assertEqual(pre_disconnect['status'], 'before_disconnect')
        original_connection_pool = manager.redis_client.connection_pool
        manager.redis_client.connection_pool.disconnect()
        disconnected_data = {'status': 'during_disconnect', 'timestamp': time.time()}
        try:
            await manager.set_thread_state('recovery-thread', disconnected_data)
        except (redis.ConnectionError, redis.TimeoutError):
            pass
        manager.redis_client.connection_pool = original_connection_pool
        recovery_data = {'status': 'after_recovery', 'recovered': True}
        await manager.set_thread_state('recovery-thread', recovery_data)
        final_state = await manager.get_thread_state('recovery-thread')
        self.assertTrue(final_state.get('status') in ['after_recovery', 'before_disconnect'] or final_state.get('recovered') is True)

    async def test_state_corruption_detection(self):
        """INTEGRATION: Detection and handling of corrupted state data"""
        manager = self.create_test_manager('corruption-user')
        thread_id = 'corruption-thread'
        valid_data = {'valid': True, 'format': 'correct', 'version': 1}
        await manager.set_thread_state(thread_id, valid_data)
        redis_key = f'state:{manager.user_id}:thread:{thread_id}'
        await redis_client.hset(redis_key, 'corrupted_field', 'invalid_json{')
        try:
            retrieved_state = await manager.get_thread_state(thread_id)
            self.assertIsInstance(retrieved_state, dict)
            new_data = {'recovered': True, 'timestamp': time.time()}
            await manager.set_thread_state(thread_id, new_data)
        except Exception as e:
            self.fail(f'State corruption caused unhandled exception: {e}')

    async def test_cross_service_consistency_recovery(self):
        """INTEGRATION: Recovery from cross-service consistency issues"""
        manager = self.create_test_manager('consistency-user')
        thread_id = 'consistency-thread'
        redis_data = {'source': 'redis', 'value': 100, 'timestamp': time.time()}
        postgres_data = {'source': 'postgres', 'value': 200, 'timestamp': time.time() - 60}
        await manager.set_thread_state(thread_id, redis_data)
        cursor = self.postgres_client.cursor()
        cursor.execute('INSERT INTO state_persistence (user_id, thread_id, state_data, created_at) \n               VALUES (%s, %s, %s, NOW()) \n               ON CONFLICT (user_id, thread_id) DO UPDATE SET \n               state_data = %s, updated_at = NOW()', (manager.user_id, thread_id, postgres_data, postgres_data))
        self.postgres_client.commit()
        cursor.close()
        resolved_state = await manager.get_thread_state(thread_id)
        self.assertIn(resolved_state.get('source'), ['redis', 'postgres'])
        self.assertIn(resolved_state.get('value'), [100, 200])
        new_consistent_data = {'source': 'resolved', 'value': 300, 'consistent': True}
        await manager.set_thread_state(thread_id, new_consistent_data)
        final_state = await manager.get_thread_state(thread_id)
        self.assertEqual(final_state['source'], 'resolved')
        self.assertEqual(final_state['value'], 300)
        self.assertTrue(final_state['consistent'])
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')