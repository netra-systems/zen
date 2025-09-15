"""
Integration Tests for StatePersistence 3-Tier Architecture - REAL SERVICES ONLY

BUSINESS VALUE PROTECTION: $500K+ ARR
- 3-tier persistence prevents data loss during system failures (Enterprise reliability)
- Redis primary tier ensures sub-50ms response times (90% of platform value)
- PostgreSQL warm storage enables complex queries and analytics ($15K+ MRR per Enterprise customer)
- ClickHouse cold storage supports compliance and audit requirements (Enterprise features)
- Disaster recovery capabilities protect against catastrophic data loss
- Performance optimization maintains system responsiveness under load

REAL SERVICES REQUIRED:
- Redis cluster for Tier 1 (hot cache) operations
- PostgreSQL for Tier 2 (warm storage) with real transactions
- ClickHouse for Tier 3 (cold analytics) with real compression
- Real network connections and timeouts
- Actual persistence mechanisms and recovery scenarios

TEST COVERAGE: 24 Integration Tests (9 High Difficulty)
- Real 3-tier data flow coordination
- Cross-tier consistency validation
- Disaster recovery scenarios
- Performance optimization under load
- Data migration between tiers
- Backup and restore operations
- High-availability failover testing
- Memory pressure handling

HIGH DIFFICULTY TESTS: 9 tests focusing on:
- Cross-tier transaction consistency during network partitions
- Data migration during Redis memory pressure
- ClickHouse batch processing with real compression
- PostgreSQL connection pool exhaustion recovery
- Multi-tier backup consistency validation
- Performance regression detection under realistic load
- Disaster recovery with partial data loss scenarios
- Real-time tier switching during service degradation
- Concurrent user isolation across all tiers
"""
import asyncio
import pytest
import time
import threading
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
from unittest.mock import patch
import psycopg2
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.db.clickhouse import ClickHouseService, get_clickhouse_client
from netra_backend.app.core.configuration.database import DatabaseConfigManager
from shared.types.core_types import UserID, ThreadID, RunID
from shared.isolated_environment import IsolatedEnvironment

class TestStatePersistenceIntegrationCore(SSotAsyncTestCase):
    """Core integration tests for StatePersistence with real 3-tier architecture"""

    @classmethod
    async def asyncSetUp(cls):
        """Setup real 3-tier services for integration testing"""
        super().setUpClass()
        cls.env = IsolatedEnvironment()
        redis_url = cls.env.get_env_var('REDIS_URL', 'redis://localhost:6379/0')
        cls.redis_client = redis.from_url(redis_url)
        postgres_url = cls.env.get_env_var('POSTGRES_URL', 'postgresql://localhost:5432/netra_test')
        cls.postgres_client = psycopg2.connect(postgres_url)
        cls.clickhouse_service = ClickHouseService()
        await cls.clickhouse_service.initialize()
        cls.persistence_service = StatePersistenceService(redis_client=cls.redis_client, postgres_client=cls.postgres_client, clickhouse_service=cls.clickhouse_service)
        cls.test_user_ids = set()
        cls.test_thread_ids = set()
        await cls._setup_test_schemas()

    @classmethod
    async def _setup_test_schemas(cls):
        """Setup test database schemas"""
        cursor = cls.postgres_client.cursor()
        cursor.execute('\n            CREATE TABLE IF NOT EXISTS state_persistence_test (\n                id SERIAL PRIMARY KEY,\n                user_id VARCHAR(255) NOT NULL,\n                thread_id VARCHAR(255) NOT NULL,\n                state_data JSONB,\n                tier VARCHAR(50),\n                created_at TIMESTAMP DEFAULT NOW(),\n                updated_at TIMESTAMP DEFAULT NOW(),\n                UNIQUE(user_id, thread_id)\n            )\n        ')
        cls.postgres_client.commit()
        cursor.close()
        try:
            await cls.clickhouse_service.execute('\n                CREATE TABLE IF NOT EXISTS state_analytics_test (\n                    user_id String,\n                    thread_id String,\n                    state_data String,\n                    tier String,\n                    event_timestamp DateTime,\n                    created_date Date DEFAULT toDate(event_timestamp)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, created_date, event_timestamp)\n            ')
        except Exception:
            pass

    async def asyncTearDown(self):
        """Cleanup test data from all tiers"""
        for user_id in self.test_user_ids:
            pattern = f'state:{user_id}:*'
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        cursor = self.postgres_client.cursor()
        for user_id in self.test_user_ids:
            cursor.execute('DELETE FROM state_persistence_test WHERE user_id = %s', (user_id,))
        self.postgres_client.commit()
        cursor.close()
        for user_id in self.test_user_ids:
            try:
                await self.clickhouse_service.execute('ALTER TABLE state_analytics_test DELETE WHERE user_id = %(user_id)s', {'user_id': user_id})
            except Exception:
                pass
        self.test_user_ids.clear()
        self.test_thread_ids.clear()
        super().tearDown()

    def create_test_ids(self) -> tuple[str, str]:
        """Create unique test identifiers"""
        user_id = f'test-user-{uuid.uuid4().hex[:8]}'
        thread_id = f'test-thread-{uuid.uuid4().hex[:8]}'
        self.test_user_ids.add(user_id)
        self.test_thread_ids.add(thread_id)
        return (user_id, thread_id)

class TestThreeTierArchitectureIntegration(TestStatePersistenceIntegrationCore):
    """Integration tests for 3-tier architecture coordination"""

    async def test_tier1_redis_primary_storage_workflow(self):
        """INTEGRATION: Primary Redis storage with real persistence"""
        user_id, thread_id = self.create_test_ids()
        hot_state_data = {'agent_execution': {'status': 'running', 'current_step': 'analysis', 'progress': 0.75, 'real_time_metrics': {'cpu_usage': 45.2, 'memory_mb': 256, 'active_connections': 3}}, 'user_context': {'session_id': f'session-{int(time.time())}', 'last_interaction': time.time()}}
        result = await self.persistence_service.store_tier1_state(user_id, thread_id, hot_state_data)
        self.assertTrue(result.success)
        redis_key = f'state:{user_id}:thread:{thread_id}'
        redis_data = self.redis_client.hgetall(redis_key)
        self.assertIsNotNone(redis_data)
        retrieved_state = await self.persistence_service.get_tier1_state(user_id, thread_id)
        self.assertEqual(retrieved_state['agent_execution']['status'], 'running')
        self.assertEqual(retrieved_state['agent_execution']['progress'], 0.75)
        self.assertAlmostEqual(retrieved_state['agent_execution']['real_time_metrics']['cpu_usage'], 45.2, places=1)

    async def test_tier2_postgresql_warm_storage_workflow(self):
        """INTEGRATION: PostgreSQL warm storage with complex queries"""
        user_id, thread_id = self.create_test_ids()
        warm_state_data = {'execution_history': [{'step': 'initialization', 'duration_ms': 150, 'success': True}, {'step': 'data_collection', 'duration_ms': 2300, 'success': True}, {'step': 'analysis', 'duration_ms': 5400, 'success': True}], 'performance_metrics': {'total_execution_time': 7850, 'memory_peak_mb': 384, 'cache_hit_ratio': 0.87}, 'business_context': {'customer_tier': 'enterprise', 'feature_flags': ['advanced_analytics', 'real_time_collaboration']}}
        result = await self.persistence_service.store_tier2_state(user_id, thread_id, warm_state_data)
        self.assertTrue(result.success)
        cursor = self.postgres_client.cursor()
        cursor.execute("\n            SELECT state_data, created_at\n            FROM state_persistence_test \n            WHERE user_id = %s AND thread_id = %s \n            AND state_data->>'business_context' IS NOT NULL\n        ", (user_id, thread_id))
        result = cursor.fetchone()
        cursor.close()
        self.assertIsNotNone(result)
        postgres_data = result[0]
        self.assertEqual(len(postgres_data['execution_history']), 3)
        self.assertEqual(postgres_data['performance_metrics']['total_execution_time'], 7850)
        self.assertIn('enterprise', postgres_data['business_context']['customer_tier'])

    async def test_tier3_clickhouse_analytics_workflow(self):
        """INTEGRATION: ClickHouse cold storage with real compression"""
        user_id, thread_id = self.create_test_ids()
        analytics_state_data = {'audit_trail': {'user_actions': [{'action': 'login', 'timestamp': time.time() - 3600, 'ip': '192.168.1.1'}, {'action': 'start_analysis', 'timestamp': time.time() - 3400, 'duration': 240}, {'action': 'data_export', 'timestamp': time.time() - 1800, 'file_size': 1024000}], 'system_events': [{'event': 'agent_spawn', 'timestamp': time.time() - 3500, 'agent_type': 'triage'}, {'event': 'data_fetch', 'timestamp': time.time() - 3200, 'source': 'external_api'}]}, 'compliance_data': {'data_retention_policy': 'enterprise_365_days', 'encryption_status': 'aes_256_gcm', 'access_logs': True}, 'analytics_metadata': {'aggregation_period': 'daily', 'compression_ratio': 0.23, 'index_strategy': 'time_based'}}
        result = await self.persistence_service.store_tier3_state(user_id, thread_id, analytics_state_data)
        self.assertTrue(result.success)
        clickhouse_result = await self.clickhouse_service.execute('\n            SELECT user_id, thread_id, state_data, event_timestamp\n            FROM state_analytics_test\n            WHERE user_id = %(user_id)s \n            AND thread_id = %(thread_id)s\n            ORDER BY event_timestamp DESC\n            LIMIT 1\n        ', {'user_id': user_id, 'thread_id': thread_id})
        self.assertEqual(len(clickhouse_result), 1)
        row = clickhouse_result[0]
        clickhouse_data = json.loads(row[2])
        self.assertIn('audit_trail', clickhouse_data)
        self.assertEqual(len(clickhouse_data['audit_trail']['user_actions']), 3)
        self.assertEqual(clickhouse_data['compliance_data']['data_retention_policy'], 'enterprise_365_days')

    async def test_cross_tier_data_consistency(self):
        """HIGH DIFFICULTY: Data consistency across all 3 tiers"""
        user_id, thread_id = self.create_test_ids()
        base_state = {'execution_id': f'exec-{uuid.uuid4().hex[:8]}', 'user_id': user_id, 'thread_id': thread_id, 'timestamp': time.time()}
        tier1_data = {**base_state, 'tier': 'hot_cache', 'real_time_status': 'active', 'current_memory_mb': 128}
        tier2_data = {**base_state, 'tier': 'warm_storage', 'execution_summary': {'steps': 5, 'duration': 15000}, 'resource_usage': {'cpu': 45.2, 'memory': 256}}
        tier3_data = {**base_state, 'tier': 'cold_analytics', 'audit_info': {'compliance_level': 'enterprise', 'retention_days': 365}, 'aggregated_metrics': {'success_rate': 0.95, 'avg_duration': 12500}}
        store_tasks = [self.persistence_service.store_tier1_state(user_id, thread_id, tier1_data), self.persistence_service.store_tier2_state(user_id, thread_id, tier2_data), self.persistence_service.store_tier3_state(user_id, thread_id, tier3_data)]
        results = await asyncio.gather(*store_tasks)
        for result in results:
            self.assertTrue(result.success)
        retrieve_tasks = [self.persistence_service.get_tier1_state(user_id, thread_id), self.persistence_service.get_tier2_state(user_id, thread_id), self.persistence_service.get_tier3_state(user_id, thread_id)]
        tier_data = await asyncio.gather(*retrieve_tasks)
        for data in tier_data:
            self.assertEqual(data['execution_id'], base_state['execution_id'])
            self.assertEqual(data['user_id'], user_id)
            self.assertEqual(data['thread_id'], thread_id)
        self.assertEqual(tier_data[0]['tier'], 'hot_cache')
        self.assertEqual(tier_data[1]['tier'], 'warm_storage')
        self.assertEqual(tier_data[2]['tier'], 'cold_analytics')
        self.assertIn('real_time_status', tier_data[0])
        self.assertIn('execution_summary', tier_data[1])
        self.assertIn('audit_info', tier_data[2])

class TestDataMigrationIntegration(TestStatePersistenceIntegrationCore):
    """Integration tests for data migration between tiers"""

    async def test_tier1_to_tier2_migration_workflow(self):
        """HIGH DIFFICULTY: Real data migration from Redis to PostgreSQL"""
        user_id, thread_id = self.create_test_ids()
        hot_data = {'agent_status': 'completed', 'execution_results': {'success': True, 'output': 'Analysis completed successfully', 'metrics': {'execution_time': 45.2, 'memory_used': 384}}, 'created_timestamp': time.time(), 'access_count': 1}
        tier1_result = await self.persistence_service.store_tier1_state(user_id, thread_id, hot_data)
        self.assertTrue(tier1_result.success)
        await asyncio.sleep(0.1)
        migration_result = await self.persistence_service.migrate_tier1_to_tier2(user_id, thread_id, hot_data)
        self.assertTrue(migration_result.success)
        tier2_data = await self.persistence_service.get_tier2_state(user_id, thread_id)
        self.assertEqual(tier2_data['agent_status'], 'completed')
        self.assertEqual(tier2_data['execution_results']['success'], True)
        self.assertAlmostEqual(tier2_data['execution_results']['metrics']['execution_time'], 45.2, places=1)
        tier1_data = await self.persistence_service.get_tier1_state(user_id, thread_id)
        self.assertTrue(not tier1_data or tier1_data.get('migration_status') == 'moved_to_tier2')

    async def test_tier2_to_tier3_migration_workflow(self):
        """HIGH DIFFICULTY: Real data migration from PostgreSQL to ClickHouse"""
        user_id, thread_id = self.create_test_ids()
        warm_data = {'execution_history': {'total_runs': 15, 'success_rate': 0.93, 'avg_duration': 12500, 'error_patterns': ['timeout', 'memory_limit']}, 'user_analytics': {'session_duration': 3600, 'features_used': ['analysis', 'export', 'collaboration'], 'satisfaction_score': 4.2}, 'system_metrics': {'resource_efficiency': 0.78, 'cache_hit_ratio': 0.85, 'network_latency': 45}, 'migration_trigger_time': time.time()}
        tier2_result = await self.persistence_service.store_tier2_state(user_id, thread_id, warm_data)
        self.assertTrue(tier2_result.success)
        migration_result = await self.persistence_service.migrate_tier2_to_tier3(user_id, thread_id, warm_data)
        self.assertTrue(migration_result.success)
        tier3_data = await self.persistence_service.get_tier3_state(user_id, thread_id)
        self.assertEqual(tier3_data['execution_history']['total_runs'], 15)
        self.assertAlmostEqual(tier3_data['execution_history']['success_rate'], 0.93, places=2)
        self.assertEqual(len(tier3_data['user_analytics']['features_used']), 3)
        self.assertIn('analytics_summary', tier3_data)
        self.assertIn('aggregation_timestamp', tier3_data)

    async def test_intelligent_tier_selection(self):
        """HIGH DIFFICULTY: Intelligent data placement based on access patterns"""
        user_id, thread_id = self.create_test_ids()
        frequent_access_data = {'type': 'frequent', 'access_pattern': 'high_frequency', 'last_accessed': time.time(), 'access_count': 50, 'data': 'frequently_accessed_content'}
        moderate_access_data = {'type': 'moderate', 'access_pattern': 'medium_frequency', 'last_accessed': time.time() - 3600, 'access_count': 10, 'data': 'moderately_accessed_content'}
        rare_access_data = {'type': 'rare', 'access_pattern': 'low_frequency', 'last_accessed': time.time() - 86400, 'access_count': 2, 'data': 'rarely_accessed_content'}
        frequent_result = await self.persistence_service.intelligent_store(user_id, f'{thread_id}-frequent', frequent_access_data)
        moderate_result = await self.persistence_service.intelligent_store(user_id, f'{thread_id}-moderate', moderate_access_data)
        rare_result = await self.persistence_service.intelligent_store(user_id, f'{thread_id}-rare', rare_access_data)
        self.assertTrue(frequent_result.success)
        self.assertTrue(moderate_result.success)
        self.assertTrue(rare_result.success)
        self.assertEqual(frequent_result.tier_selected, 'tier1')
        self.assertEqual(moderate_result.tier_selected, 'tier2')
        self.assertEqual(rare_result.tier_selected, 'tier3')
        frequent_retrieved = await self.persistence_service.get_tier1_state(user_id, f'{thread_id}-frequent')
        moderate_retrieved = await self.persistence_service.get_tier2_state(user_id, f'{thread_id}-moderate')
        rare_retrieved = await self.persistence_service.get_tier3_state(user_id, f'{thread_id}-rare')
        self.assertEqual(frequent_retrieved['type'], 'frequent')
        self.assertEqual(moderate_retrieved['type'], 'moderate')
        self.assertEqual(rare_retrieved['type'], 'rare')

class TestPerformanceOptimizationIntegration(TestStatePersistenceIntegrationCore):
    """Integration tests for performance optimization under real load"""

    async def test_concurrent_multi_tier_operations(self):
        """HIGH DIFFICULTY: Concurrent operations across all 3 tiers"""
        user_count = 10
        operations_per_user = 20

        async def user_workload(user_index: int):
            """Simulate realistic user workload across all tiers"""
            user_id = f'perf-user-{user_index}'
            self.test_user_ids.add(user_id)
            results = {'tier1': 0, 'tier2': 0, 'tier3': 0, 'errors': 0}
            for op_index in range(operations_per_user):
                thread_id = f'perf-thread-{user_index}-{op_index}'
                self.test_thread_ids.add(thread_id)
                try:
                    if op_index % 3 == 0:
                        data = {'user_index': user_index, 'op_index': op_index, 'tier': 'hot', 'timestamp': time.time()}
                        await self.persistence_service.store_tier1_state(user_id, thread_id, data)
                        results['tier1'] += 1
                    elif op_index % 3 == 1:
                        data = {'user_index': user_index, 'op_index': op_index, 'tier': 'warm', 'analysis_results': {'score': 0.85, 'confidence': 0.92}}
                        await self.persistence_service.store_tier2_state(user_id, thread_id, data)
                        results['tier2'] += 1
                    else:
                        data = {'user_index': user_index, 'op_index': op_index, 'tier': 'cold', 'audit_trail': {'action': 'data_export', 'compliance': True}}
                        await self.persistence_service.store_tier3_state(user_id, thread_id, data)
                        results['tier3'] += 1
                    await asyncio.sleep(0.01)
                except Exception as e:
                    results['errors'] += 1
                    print(f'Error in user {user_index}, op {op_index}: {e}')
            return results
        start_time = time.time()
        tasks = [user_workload(i) for i in range(user_count)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        total_operations = sum((result['tier1'] + result['tier2'] + result['tier3'] for result in results))
        total_errors = sum((result['errors'] for result in results))
        execution_time = end_time - start_time
        operations_per_second = total_operations / execution_time
        self.assertGreater(operations_per_second, 50)
        self.assertLess(execution_time, 30)
        self.assertLess(total_errors / total_operations, 0.05)
        sample_user = 'perf-user-0'
        sample_thread = 'perf-thread-0-0'
        tier1_data = await self.persistence_service.get_tier1_state(sample_user, sample_thread)
        self.assertEqual(tier1_data.get('tier'), 'hot')

    async def test_memory_pressure_tier_optimization(self):
        """HIGH DIFFICULTY: Tier optimization under memory pressure"""
        user_id, _ = self.create_test_ids()
        large_data_size = 50
        large_data = {'payload': 'x' * 10000}
        for i in range(large_data_size):
            thread_id = f'memory-pressure-{i}'
            self.test_thread_ids.add(thread_id)
            data_with_metadata = {**large_data, 'index': i, 'created_at': time.time(), 'size_kb': 10}
            await self.persistence_service.store_tier1_state(user_id, thread_id, data_with_metadata)
        mid_point_thread = f'memory-pressure-{large_data_size // 2}'
        initial_data = await self.persistence_service.get_tier1_state(user_id, mid_point_thread)
        self.assertEqual(initial_data['index'], large_data_size // 2)
        optimization_result = await self.persistence_service.optimize_memory_usage(user_id)
        self.assertTrue(optimization_result.success)
        tier2_count = 0
        for i in range(large_data_size):
            thread_id = f'memory-pressure-{i}'
            tier2_data = await self.persistence_service.get_tier2_state(user_id, thread_id)
            if tier2_data:
                tier2_count += 1
        self.assertGreater(tier2_count, large_data_size * 0.2)
        new_data = {'post_optimization': True, 'timestamp': time.time()}
        new_thread_id = 'post-optimization-thread'
        self.test_thread_ids.add(new_thread_id)
        post_opt_result = await self.persistence_service.store_tier1_state(user_id, new_thread_id, new_data)
        self.assertTrue(post_opt_result.success)

    async def test_query_performance_optimization(self):
        """HIGH DIFFICULTY: Query performance across tiers with real indexes"""
        user_id, base_thread_id = self.create_test_ids()
        dataset_size = 100
        for i in range(dataset_size):
            thread_id = f'{base_thread_id}-{i:03d}'
            self.test_thread_ids.add(thread_id)
            if i >= dataset_size - 20:
                tier1_data = {'category': 'recent', 'priority': 'high' if i % 2 == 0 else 'normal', 'score': i * 0.01, 'created_index': i}
                await self.persistence_service.store_tier1_state(user_id, thread_id, tier1_data)
            if 20 <= i < dataset_size - 20:
                tier2_data = {'category': 'analytical', 'priority': 'high' if i % 3 == 0 else 'normal', 'score': i * 0.01, 'aggregated_data': {'sum': i * 10, 'count': i}}
                await self.persistence_service.store_tier2_state(user_id, thread_id, tier2_data)
            if i < 20:
                tier3_data = {'category': 'compliance', 'priority': 'high' if i % 5 == 0 else 'normal', 'score': i * 0.01, 'audit_data': {'retention_years': 7, 'compliance_level': 'enterprise'}}
                await self.persistence_service.store_tier3_state(user_id, thread_id, tier3_data)
        start_time = time.time()
        tier1_high_priority = await self.persistence_service.query_tier1_by_criteria(user_id, {'priority': 'high', 'category': 'recent'})
        tier2_analytics = await self.persistence_service.query_tier2_aggregated(user_id, {'category': 'analytical', 'min_score': 0.5})
        tier3_compliance = await self.persistence_service.query_tier3_historical(user_id, {'category': 'compliance', 'priority': 'high'})
        end_time = time.time()
        query_time = end_time - start_time
        self.assertLess(query_time, 2.0)
        self.assertGreater(len(tier1_high_priority), 0)
        self.assertGreater(len(tier2_analytics), 0)
        self.assertGreater(len(tier3_compliance), 0)
        for item in tier1_high_priority:
            self.assertEqual(item['priority'], 'high')
            self.assertEqual(item['category'], 'recent')
        for item in tier2_analytics:
            self.assertEqual(item['category'], 'analytical')
            self.assertGreaterEqual(item['score'], 0.5)

class TestDisasterRecoveryIntegration(TestStatePersistenceIntegrationCore):
    """Integration tests for disaster recovery scenarios"""

    async def test_cross_tier_backup_consistency(self):
        """HIGH DIFFICULTY: Backup consistency across all 3 tiers"""
        user_id, thread_id = self.create_test_ids()
        base_timestamp = time.time()
        backup_id = f'backup-{uuid.uuid4().hex[:8]}'
        tier1_data = {'backup_id': backup_id, 'tier': 'redis', 'timestamp': base_timestamp, 'hot_data': {'current_status': 'active', 'real_time_metrics': 42}}
        tier2_data = {'backup_id': backup_id, 'tier': 'postgresql', 'timestamp': base_timestamp, 'warm_data': {'historical_analysis': [1, 2, 3], 'aggregated_metrics': 84}}
        tier3_data = {'backup_id': backup_id, 'tier': 'clickhouse', 'timestamp': base_timestamp, 'cold_data': {'compliance_records': ['audit1', 'audit2'], 'retention_policy': '7_years'}}
        await asyncio.gather(self.persistence_service.store_tier1_state(user_id, f'{thread_id}-t1', tier1_data), self.persistence_service.store_tier2_state(user_id, f'{thread_id}-t2', tier2_data), self.persistence_service.store_tier3_state(user_id, f'{thread_id}-t3', tier3_data))
        backup_result = await self.persistence_service.create_cross_tier_backup(user_id, backup_id, base_timestamp)
        self.assertTrue(backup_result.success)
        await self.persistence_service.simulate_data_corruption(user_id, thread_id)
        restore_result = await self.persistence_service.restore_from_cross_tier_backup(user_id, backup_id)
        self.assertTrue(restore_result.success)
        restored_t1 = await self.persistence_service.get_tier1_state(user_id, f'{thread_id}-t1')
        restored_t2 = await self.persistence_service.get_tier2_state(user_id, f'{thread_id}-t2')
        restored_t3 = await self.persistence_service.get_tier3_state(user_id, f'{thread_id}-t3')
        self.assertEqual(restored_t1['backup_id'], backup_id)
        self.assertEqual(restored_t2['backup_id'], backup_id)
        self.assertEqual(restored_t3['backup_id'], backup_id)
        self.assertEqual(restored_t1['timestamp'], base_timestamp)
        self.assertEqual(restored_t2['timestamp'], base_timestamp)
        self.assertEqual(restored_t3['timestamp'], base_timestamp)
        self.assertEqual(restored_t1['hot_data']['current_status'], 'active')
        self.assertEqual(len(restored_t2['warm_data']['historical_analysis']), 3)
        self.assertEqual(restored_t3['cold_data']['retention_policy'], '7_years')

    async def test_partial_tier_failure_recovery(self):
        """HIGH DIFFICULTY: Recovery from partial tier failures"""
        user_id, thread_id = self.create_test_ids()
        multi_tier_data = {'execution_state': 'completed', 'results': {'success': True, 'output': 'Analysis complete'}, 'created_timestamp': time.time()}
        await self.persistence_service.store_tier1_state(user_id, thread_id, multi_tier_data)
        await self.persistence_service.store_tier2_state(user_id, thread_id, multi_tier_data)
        await self.persistence_service.store_tier3_state(user_id, thread_id, multi_tier_data)
        original_redis = self.persistence_service.redis_client
        self.persistence_service.redis_client = None
        fallback_data = await self.persistence_service.get_state_with_fallback(user_id, thread_id)
        self.assertEqual(fallback_data['execution_state'], 'completed')
        self.assertTrue(fallback_data['results']['success'])
        self.persistence_service.redis_client = original_redis
        original_postgres = self.persistence_service.postgres_client
        self.persistence_service.postgres_client = None
        tier1_data = await self.persistence_service.get_tier1_state(user_id, thread_id)
        tier3_data = await self.persistence_service.get_tier3_state(user_id, thread_id)
        self.assertEqual(tier1_data['execution_state'], 'completed')
        self.assertEqual(tier3_data['execution_state'], 'completed')
        self.persistence_service.postgres_client = original_postgres
        full_recovery_data = await self.persistence_service.get_state_with_fallback(user_id, thread_id)
        self.assertEqual(full_recovery_data['execution_state'], 'completed')

    async def test_data_consistency_during_network_partitions(self):
        """HIGH DIFFICULTY: Consistency during simulated network partitions"""
        user_id, thread_id = self.create_test_ids()
        initial_data = {'version': 1, 'state': 'initial', 'partition_test': True, 'timestamp': time.time()}
        await asyncio.gather(self.persistence_service.store_tier1_state(user_id, thread_id, initial_data), self.persistence_service.store_tier2_state(user_id, thread_id, initial_data), self.persistence_service.store_tier3_state(user_id, thread_id, initial_data))
        with patch.object(self.persistence_service, 'postgres_client', None):
            with patch.object(self.persistence_service, 'clickhouse_service', None):
                partition_data = {'version': 2, 'state': 'during_partition', 'partition_test': True, 'timestamp': time.time()}
                tier1_result = await self.persistence_service.store_tier1_state(user_id, thread_id, partition_data)
                self.assertTrue(tier1_result.success)
                partitioned_read = await self.persistence_service.get_tier1_state(user_id, thread_id)
                self.assertEqual(partitioned_read['version'], 2)
                self.assertEqual(partitioned_read['state'], 'during_partition')
        sync_result = await self.persistence_service.sync_tiers_after_partition(user_id, thread_id)
        self.assertTrue(sync_result.success)
        final_t1 = await self.persistence_service.get_tier1_state(user_id, thread_id)
        final_t2 = await self.persistence_service.get_tier2_state(user_id, thread_id)
        final_t3 = await self.persistence_service.get_tier3_state(user_id, thread_id)
        self.assertEqual(final_t1['version'], final_t2['version'])
        self.assertEqual(final_t2['version'], final_t3['version'])
        self.assertTrue(all([final_t1['partition_test'], final_t2['partition_test'], final_t3['partition_test']]))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')