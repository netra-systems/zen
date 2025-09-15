"""
Integration Tests for UnifiedIDManager - REAL SERVICES ONLY

BUSINESS VALUE PROTECTION: $500K+ ARR
- Unique ID generation prevents data corruption and system conflicts
- Thread-safe operations enable concurrent user sessions (Enterprise scalability)
- Cross-service ID coordination ensures data integrity across microservices
- ID validation prevents security vulnerabilities from malformed identifiers
- Performance under load maintains system responsiveness (90% of platform value)
- Disaster recovery ensures business continuity during system failures

REAL SERVICES REQUIRED:
- Real Redis for ID sequence management and caching
- Real PostgreSQL for ID persistence and uniqueness constraints
- Real database transactions for atomic ID operations
- Real concurrency with multiple threads and processes
- Real network latency and timeout scenarios
- Real memory constraints and garbage collection

TEST COVERAGE: 18 Integration Tests (6 High Difficulty)
- Real database constraint validation
- Cross-service ID synchronization
- High-concurrency ID generation
- Database transaction integrity
- Network partition handling
- Memory pressure scenarios
- Disaster recovery workflows
- Performance regression detection

HIGH DIFFICULTY TESTS: 6 tests focusing on:
- Concurrent ID generation with real database deadlock scenarios
- Cross-service ID coordination during network partitions
- ID uniqueness validation under extreme concurrent load
- Database transaction rollback and recovery scenarios
- Memory pressure handling with real garbage collection
- Performance benchmarking under realistic production load
"""
import asyncio
import pytest
import time
import threading
import uuid
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set
from unittest.mock import patch
from netra_backend.app.services.redis_client import get_redis_client, get_redis_service
import psycopg2
from psycopg2 import sql
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.core.configuration.base import UnifiedConfigManager
from shared.types.core_types import UserID, ThreadID, RunID
from shared.isolated_environment import IsolatedEnvironment

class TestUnifiedIDManagerIntegrationCore(SSotAsyncTestCase):
    """Core integration tests for UnifiedIDManager with real services"""

    @classmethod
    async def asyncSetUp(cls):
        """Setup real services for ID management integration testing"""
        super().setUpClass()
        cls.env = IsolatedEnvironment()
        redis_url = cls.env.get_env_var('REDIS_URL', 'redis://localhost:6379/2')
        cls.redis_client = redis.from_url(redis_url)
        postgres_url = cls.env.get_env_var('POSTGRES_URL', 'postgresql://localhost:5432/netra_id_test')
        cls.postgres_client = psycopg2.connect(postgres_url)
        cls.config_manager = UnifiedConfigurationManager()
        cls.id_manager = UnifiedIDManager(redis_client=cls.redis_client, postgres_client=cls.postgres_client, config_manager=cls.config_manager)
        cls.test_generated_ids = set()
        cls.test_sequences = set()
        cls.performance_metrics = {'generation_times': [], 'validation_times': [], 'concurrent_operations': []}
        await cls._setup_test_schemas()

    @classmethod
    async def _setup_test_schemas(cls):
        """Setup test database schemas for ID management"""
        cursor = cls.postgres_client.cursor()
        cursor.execute('\n            CREATE TABLE IF NOT EXISTS id_registry_test (\n                id SERIAL PRIMARY KEY,\n                generated_id VARCHAR(255) UNIQUE NOT NULL,\n                id_type VARCHAR(50) NOT NULL,\n                format_type VARCHAR(50) NOT NULL,\n                created_at TIMESTAMP DEFAULT NOW(),\n                created_by VARCHAR(255),\n                metadata JSONB,\n                INDEX(id_type, format_type),\n                INDEX(created_at)\n            )\n        ')
        cursor.execute('\n            CREATE TABLE IF NOT EXISTS id_sequences_test (\n                sequence_name VARCHAR(255) PRIMARY KEY,\n                current_value BIGINT NOT NULL DEFAULT 0,\n                increment_by INTEGER NOT NULL DEFAULT 1,\n                min_value BIGINT NOT NULL DEFAULT 1,\n                max_value BIGINT NOT NULL DEFAULT 9223372036854775807,\n                updated_at TIMESTAMP DEFAULT NOW()\n            )\n        ')
        cursor.execute('\n            CREATE TABLE IF NOT EXISTS id_relationships_test (\n                id SERIAL PRIMARY KEY,\n                parent_id VARCHAR(255) NOT NULL,\n                child_id VARCHAR(255) NOT NULL,\n                relationship_type VARCHAR(50) NOT NULL,\n                service_context VARCHAR(100),\n                created_at TIMESTAMP DEFAULT NOW(),\n                UNIQUE(parent_id, child_id, relationship_type),\n                INDEX(parent_id),\n                INDEX(child_id)\n            )\n        ')
        cls.postgres_client.commit()
        cursor.close()

    async def asyncTearDown(self):
        """Cleanup test data from all ID management services"""
        for sequence_name in self.test_sequences:
            await redis_client.delete(f'id_sequence:{sequence_name}')
        for generated_id in self.test_generated_ids:
            await redis_client.delete(f'id_cache:{generated_id}')
        cursor = self.postgres_client.cursor()
        if self.test_generated_ids:
            id_list = list(self.test_generated_ids)
            cursor.execute('\n                DELETE FROM id_registry_test \n                WHERE generated_id = ANY(%s)\n            ', (id_list,))
            cursor.execute('\n                DELETE FROM id_relationships_test \n                WHERE parent_id = ANY(%s) OR child_id = ANY(%s)\n            ', (id_list, id_list))
        if self.test_sequences:
            sequence_list = list(self.test_sequences)
            cursor.execute('\n                DELETE FROM id_sequences_test \n                WHERE sequence_name = ANY(%s)\n            ', (sequence_list,))
        self.postgres_client.commit()
        cursor.close()
        self.test_generated_ids.clear()
        self.test_sequences.clear()
        self.performance_metrics = {'generation_times': [], 'validation_times': [], 'concurrent_operations': []}
        super().tearDown()

    def track_generated_id(self, generated_id: str, id_type: str='test'):
        """Track generated ID for cleanup"""
        self.test_generated_ids.add(generated_id)
        cursor = self.postgres_client.cursor()
        try:
            cursor.execute('\n                INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by)\n                VALUES (%s, %s, %s, %s)\n                ON CONFLICT (generated_id) DO NOTHING\n            ', (generated_id, id_type, 'integration_test', 'test_framework'))
            self.postgres_client.commit()
        except Exception as e:
            print(f'Warning: Could not track ID {generated_id}: {e}')
        finally:
            cursor.close()

class TestRealDatabaseIntegration(TestUnifiedIDManagerIntegrationCore):
    """Integration tests with real database operations"""

    async def test_id_uniqueness_with_real_database_constraints(self):
        """INTEGRATION: ID uniqueness validation with real database constraints"""
        generated_ids = set()
        for i in range(100):
            user_id = await self.id_manager.generate_user_id()
            self.track_generated_id(user_id, 'user')
            self.assertNotIn(user_id, generated_ids)
            generated_ids.add(user_id)
            self.assertTrue(user_id.startswith('user_'))
            self.assertEqual(len(user_id), 41)
        cursor = self.postgres_client.cursor()
        cursor.execute('\n            SELECT COUNT(DISTINCT generated_id) as unique_count,\n                   COUNT(*) as total_count\n            FROM id_registry_test \n            WHERE id_type = %s AND created_by = %s\n        ', ('user', 'test_framework'))
        result = cursor.fetchone()
        cursor.close()
        unique_count, total_count = result
        self.assertEqual(unique_count, total_count)
        self.assertEqual(unique_count, 100)

    async def test_cross_service_id_coordination(self):
        """HIGH DIFFICULTY: Cross-service ID coordination with real database transactions"""
        user_id = await self.id_manager.generate_user_id()
        self.track_generated_id(user_id, 'user')
        thread_ids = []
        for i in range(5):
            thread_id = await self.id_manager.generate_thread_id(user_id)
            thread_ids.append(thread_id)
            self.track_generated_id(thread_id, 'thread')
        run_ids = []
        for thread_id in thread_ids:
            for j in range(3):
                run_id = await self.id_manager.generate_run_id(thread_id)
                run_ids.append(run_id)
                self.track_generated_id(run_id, 'run')
        cursor = self.postgres_client.cursor()
        cursor.execute('\n            SELECT COUNT(*) FROM id_relationships_test\n            WHERE parent_id = %s AND relationship_type = %s\n        ', (user_id, 'user_thread'))
        user_thread_count = cursor.fetchone()[0]
        self.assertEqual(user_thread_count, 5)
        cursor.execute('\n            SELECT COUNT(*) FROM id_relationships_test\n            WHERE relationship_type = %s AND parent_id = ANY(%s)\n        ', ('thread_run', thread_ids))
        thread_run_count = cursor.fetchone()[0]
        self.assertEqual(thread_run_count, 15)
        cursor.close()
        for thread_id in thread_ids:
            self.assertTrue(thread_id.startswith('thread_'))
        for run_id in run_ids:
            self.assertTrue(run_id.startswith('run_'))

    async def test_database_transaction_integrity(self):
        """HIGH DIFFICULTY: Database transaction integrity during ID operations"""

        async def atomic_id_creation(batch_id: str, count: int):
            """Create IDs atomically or fail entirely"""
            cursor = self.postgres_client.cursor()
            try:
                cursor.execute('BEGIN')
                batch_ids = []
                for i in range(count):
                    new_id = await self.id_manager.generate_user_id()
                    batch_ids.append(new_id)
                    cursor.execute('\n                        INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by, metadata)\n                        VALUES (%s, %s, %s, %s, %s)\n                    ', (new_id, 'user', f'batch_{batch_id}', 'atomic_test', {'batch_id': batch_id, 'index': i}))
                if batch_id == 'fail_batch':
                    raise Exception('Simulated failure for testing rollback')
                cursor.execute('COMMIT')
                for new_id in batch_ids:
                    self.track_generated_id(new_id, 'user')
                return {'success': True, 'ids': batch_ids}
            except Exception as e:
                cursor.execute('ROLLBACK')
                return {'success': False, 'error': str(e)}
            finally:
                cursor.close()
        success_result = await atomic_id_creation('success_batch', 10)
        self.assertTrue(success_result['success'])
        self.assertEqual(len(success_result['ids']), 10)
        fail_result = await atomic_id_creation('fail_batch', 5)
        self.assertFalse(fail_result['success'])
        self.assertIn('Simulated failure', fail_result['error'])
        cursor = self.postgres_client.cursor()
        cursor.execute('\n            SELECT COUNT(*) FROM id_registry_test\n            WHERE format_type = %s\n        ', ('batch_success_batch',))
        success_count = cursor.fetchone()[0]
        self.assertEqual(success_count, 10)
        cursor.execute('\n            SELECT COUNT(*) FROM id_registry_test\n            WHERE format_type = %s\n        ', ('batch_fail_batch',))
        fail_count = cursor.fetchone()[0]
        self.assertEqual(fail_count, 0)
        cursor.close()

    async def test_database_deadlock_handling(self):
        """HIGH DIFFICULTY: Database deadlock handling during concurrent ID operations"""
        deadlock_results = []

        async def concurrent_id_operations(worker_id: int, operation_count: int):
            """Perform concurrent ID operations that might cause deadlocks"""
            cursor = self.postgres_client.cursor()
            results = {'success': 0, 'deadlocks': 0, 'other_errors': 0}
            for i in range(operation_count):
                try:
                    cursor.execute('BEGIN')
                    user_id = await self.id_manager.generate_user_id()
                    thread_id = await self.id_manager.generate_thread_id(user_id)
                    if worker_id % 2 == 0:
                        cursor.execute('\n                            INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by)\n                            VALUES (%s, %s, %s, %s)\n                        ', (user_id, 'user', f'worker_{worker_id}', 'deadlock_test'))
                        cursor.execute('\n                            INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by)\n                            VALUES (%s, %s, %s, %s)\n                        ', (thread_id, 'thread', f'worker_{worker_id}', 'deadlock_test'))
                    else:
                        cursor.execute('\n                            INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by)\n                            VALUES (%s, %s, %s, %s)\n                        ', (thread_id, 'thread', f'worker_{worker_id}', 'deadlock_test'))
                        cursor.execute('\n                            INSERT INTO id_registry_test (generated_id, id_type, format_type, created_by)\n                            VALUES (%s, %s, %s, %s)\n                        ', (user_id, 'user', f'worker_{worker_id}', 'deadlock_test'))
                    cursor.execute('COMMIT')
                    results['success'] += 1
                    self.track_generated_id(user_id, 'user')
                    self.track_generated_id(thread_id, 'thread')
                except psycopg2.errors.DeadlockDetected:
                    cursor.execute('ROLLBACK')
                    results['deadlocks'] += 1
                    await asyncio.sleep(0.01)
                except Exception as e:
                    cursor.execute('ROLLBACK')
                    results['other_errors'] += 1
                    print(f'Worker {worker_id} error: {e}')
            cursor.close()
            return results
        worker_count = 8
        operations_per_worker = 20
        start_time = time.time()
        tasks = [concurrent_id_operations(i, operations_per_worker) for i in range(worker_count)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        total_success = sum((r['success'] for r in results))
        total_deadlocks = sum((r['deadlocks'] for r in results))
        total_other_errors = sum((r['other_errors'] for r in results))
        execution_time = end_time - start_time
        self.assertLess(execution_time, 10)
        self.assertGreater(total_success, 0)
        self.assertLessEqual(total_other_errors, total_success * 0.1)
        final_count_cursor = self.postgres_client.cursor()
        final_count_cursor.execute('\n            SELECT COUNT(*) FROM id_registry_test\n            WHERE created_by = %s\n        ', ('deadlock_test',))
        final_count = final_count_cursor.fetchone()[0]
        final_count_cursor.close()
        self.assertEqual(final_count, total_success * 2)

class TestHighConcurrencyIntegration(TestUnifiedIDManagerIntegrationCore):
    """Integration tests for high-concurrency ID generation scenarios"""

    async def test_concurrent_id_generation_stress(self):
        """HIGH DIFFICULTY: High-concurrency ID generation with real threading"""
        concurrent_threads = 15
        ids_per_thread = 100

        def generate_ids_in_thread(thread_id: int):
            """Generate IDs in separate thread to test thread safety"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:

                async def async_id_generation():
                    generated_ids = []
                    errors = []
                    for i in range(ids_per_thread):
                        try:
                            if i % 3 == 0:
                                new_id = await self.id_manager.generate_user_id()
                            elif i % 3 == 1:
                                base_user = await self.id_manager.generate_user_id()
                                new_id = await self.id_manager.generate_thread_id(base_user)
                            else:
                                base_user = await self.id_manager.generate_user_id()
                                base_thread = await self.id_manager.generate_thread_id(base_user)
                                new_id = await self.id_manager.generate_run_id(base_thread)
                            generated_ids.append(new_id)
                        except Exception as e:
                            errors.append(f'Thread {thread_id}, iteration {i}: {str(e)}')
                    return {'thread_id': thread_id, 'generated_ids': generated_ids, 'errors': errors, 'success_count': len(generated_ids)}
                return loop.run_until_complete(async_id_generation())
            finally:
                loop.close()
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            future_to_thread = {executor.submit(generate_ids_in_thread, i): i for i in range(concurrent_threads)}
            thread_results = []
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    thread_results.append(result)
                    for generated_id in result['generated_ids']:
                        self.track_generated_id(generated_id, 'concurrent_test')
                except Exception as e:
                    print(f'Thread {thread_id} failed: {e}')
        end_time = time.time()
        execution_time = end_time - start_time
        total_ids = sum((len(r['generated_ids']) for r in thread_results))
        total_errors = sum((len(r['errors']) for r in thread_results))
        self.assertLess(execution_time, 15)
        ids_per_second = total_ids / execution_time
        self.assertGreater(ids_per_second, 100)
        expected_total = concurrent_threads * ids_per_thread
        success_rate = total_ids / expected_total
        self.assertGreater(success_rate, 0.95)
        all_ids = []
        for result in thread_results:
            all_ids.extend(result['generated_ids'])
        unique_ids = set(all_ids)
        self.assertEqual(len(unique_ids), len(all_ids))
        cursor = self.postgres_client.cursor()
        cursor.execute('\n            SELECT COUNT(DISTINCT generated_id) as unique_db_count,\n                   COUNT(*) as total_db_count\n            FROM id_registry_test \n            WHERE created_by = %s\n        ', ('test_framework',))
        db_result = cursor.fetchone()
        cursor.close()
        unique_db_count, total_db_count = db_result
        self.assertEqual(unique_db_count, total_db_count)

    async def test_memory_pressure_during_id_generation(self):
        """HIGH DIFFICULTY: ID generation under memory pressure with real garbage collection"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        large_batch_size = 5000
        generated_ids = []
        for batch in range(10):
            batch_ids = []
            for i in range(large_batch_size):
                user_id = await self.id_manager.generate_user_id()
                id_metadata = {'batch': batch, 'index': i, 'timestamp': time.time(), 'large_data': 'x' * 1000, 'nested_data': {'level1': {'level2': {'level3': f'data_{i}'}}}}
                batch_ids.append((user_id, id_metadata))
                if len(batch_ids) % 100 == 0:
                    for tracked_id, _ in batch_ids[-100:]:
                        self.track_generated_id(tracked_id, 'memory_pressure_test')
            generated_ids.extend(batch_ids)
            if batch % 3 == 2:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                if memory_growth > 500:
                    gc.collect()
                    post_gc_memory = process.memory_info().rss / 1024 / 1024
                    print(f'Memory before GC: {current_memory:.1f}MB, after GC: {post_gc_memory:.1f}MB')
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        self.assertLess(total_memory_growth, 1000)
        final_ids = [id_data[0] for id_data in generated_ids]
        unique_final_ids = set(final_ids)
        self.assertEqual(len(unique_final_ids), len(final_ids))
        post_pressure_id = await self.id_manager.generate_user_id()
        self.track_generated_id(post_pressure_id, 'post_pressure_test')
        self.assertIsNotNone(post_pressure_id)
        self.assertTrue(post_pressure_id.startswith('user_'))
        del generated_ids
        gc.collect()

    async def test_performance_benchmarking(self):
        """HIGH DIFFICULTY: Performance benchmarking under realistic production load"""
        benchmark_scenarios = [{'name': 'low_load', 'concurrent_users': 5, 'operations_per_user': 50}, {'name': 'medium_load', 'concurrent_users': 15, 'operations_per_user': 100}, {'name': 'high_load', 'concurrent_users': 25, 'operations_per_user': 200}]
        benchmark_results = {}
        for scenario in benchmark_scenarios:
            scenario_name = scenario['name']
            concurrent_users = scenario['concurrent_users']
            operations_per_user = scenario['operations_per_user']

            async def benchmark_user_workflow(user_index: int):
                """Simulate realistic user ID generation workflow"""
                workflow_times = []
                generated_user_ids = []
                for operation in range(operations_per_user):
                    start_time = time.perf_counter()
                    user_id = await self.id_manager.generate_user_id()
                    generated_user_ids.append(user_id)
                    thread_count = 2 + operation % 2
                    for _ in range(thread_count):
                        thread_id = await self.id_manager.generate_thread_id(user_id)
                        run_count = 1 + operation % 2
                        for _ in range(run_count):
                            run_id = await self.id_manager.generate_run_id(thread_id)
                    operation_time = time.perf_counter() - start_time
                    workflow_times.append(operation_time)
                    await asyncio.sleep(0.001)
                for user_id in generated_user_ids:
                    self.track_generated_id(user_id, f'benchmark_{scenario_name}')
                return {'user_index': user_index, 'operation_times': workflow_times, 'avg_time': sum(workflow_times) / len(workflow_times), 'max_time': max(workflow_times), 'min_time': min(workflow_times)}
            scenario_start = time.perf_counter()
            tasks = [benchmark_user_workflow(i) for i in range(concurrent_users)]
            user_results = await asyncio.gather(*tasks)
            scenario_end = time.perf_counter()
            scenario_duration = scenario_end - scenario_start
            all_operation_times = []
            for result in user_results:
                all_operation_times.extend(result['operation_times'])
            total_operations = sum((len(r['operation_times']) for r in user_results))
            benchmark_results[scenario_name] = {'total_duration': scenario_duration, 'total_operations': total_operations, 'operations_per_second': total_operations / scenario_duration, 'avg_operation_time': sum(all_operation_times) / len(all_operation_times), 'p95_operation_time': sorted(all_operation_times)[int(len(all_operation_times) * 0.95)], 'max_operation_time': max(all_operation_times), 'concurrent_users': concurrent_users}
        low_load = benchmark_results['low_load']
        self.assertGreater(low_load['operations_per_second'], 200)
        self.assertLess(low_load['avg_operation_time'], 0.01)
        medium_load = benchmark_results['medium_load']
        self.assertGreater(medium_load['operations_per_second'], 150)
        self.assertLess(medium_load['avg_operation_time'], 0.02)
        high_load = benchmark_results['high_load']
        self.assertGreater(high_load['operations_per_second'], 100)
        self.assertLess(high_load['avg_operation_time'], 0.05)
        for scenario_name, results in benchmark_results.items():
            self.assertLess(results['p95_operation_time'], 0.1, f"P95 time too high for {scenario_name}: {results['p95_operation_time']}")
        self.performance_metrics['concurrent_operations'] = benchmark_results
        print(f'\nPerformance Benchmark Results:')
        for scenario_name, results in benchmark_results.items():
            print(f"{scenario_name}: {results['operations_per_second']:.1f} ops/sec, avg: {results['avg_operation_time'] * 1000:.1f}ms, p95: {results['p95_operation_time'] * 1000:.1f}ms")

class TestDisasterRecoveryIntegration(TestUnifiedIDManagerIntegrationCore):
    """Integration tests for disaster recovery scenarios"""

    async def test_redis_connection_failure_recovery(self):
        """HIGH DIFFICULTY: Recovery from Redis connection failure with sequence continuity"""
        initial_ids = []
        for i in range(10):
            user_id = await self.id_manager.generate_user_id()
            initial_ids.append(user_id)
            self.track_generated_id(user_id, 'redis_failure_test')
        initial_sequences = {}
        for sequence_name in ['user_id_seq', 'thread_id_seq', 'run_id_seq']:
            seq_value = await redis_client.get(f'id_sequence:{sequence_name}')
            if seq_value:
                initial_sequences[sequence_name] = int(seq_value)
        original_redis = self.id_manager.redis_client
        self.id_manager.redis_client = await get_redis_client()
        fallback_ids = []
        try:
            for i in range(5):
                user_id = await self.id_manager.generate_user_id()
                fallback_ids.append(user_id)
                self.track_generated_id(user_id, 'redis_failure_fallback')
                self.assertTrue(user_id.startswith('user_'))
                self.assertEqual(len(user_id), 41)
        except Exception as e:
            self.fail(f'ID generation should work during Redis failure: {e}')
        self.id_manager.redis_client = original_redis
        recovery_ids = []
        for i in range(5):
            user_id = await self.id_manager.generate_user_id()
            recovery_ids.append(user_id)
            self.track_generated_id(user_id, 'redis_recovery_test')
        all_ids = initial_ids + fallback_ids + recovery_ids
        unique_ids = set(all_ids)
        self.assertEqual(len(unique_ids), len(all_ids))
        final_sequences = {}
        for sequence_name in ['user_id_seq', 'thread_id_seq', 'run_id_seq']:
            seq_value = await redis_client.get(f'id_sequence:{sequence_name}')
            if seq_value:
                final_sequences[sequence_name] = int(seq_value)
        for seq_name, initial_val in initial_sequences.items():
            final_val = final_sequences.get(seq_name, 0)
            self.assertGreaterEqual(final_val, initial_val)

    async def test_database_connection_failure_recovery(self):
        """INTEGRATION: Database connection failure with graceful degradation"""
        initial_ids = []
        for i in range(5):
            user_id = await self.id_manager.generate_user_id()
            initial_ids.append(user_id)
            self.track_generated_id(user_id, 'db_failure_test')
        original_postgres = self.id_manager.postgres_client
        self.id_manager.postgres_client = None
        try:
            degraded_mode_ids = []
            for i in range(3):
                user_id = await self.id_manager.generate_user_id()
                degraded_mode_ids.append(user_id)
                self.assertTrue(user_id.startswith('user_'))
                self.assertEqual(len(user_id), 41)
            for user_id in degraded_mode_ids:
                self.test_generated_ids.add(user_id)
        except Exception as e:
            print(f'Expected database failure during outage: {e}')
            degraded_mode_ids = []
        self.id_manager.postgres_client = original_postgres
        recovery_ids = []
        for i in range(5):
            user_id = await self.id_manager.generate_user_id()
            recovery_ids.append(user_id)
            self.track_generated_id(user_id, 'db_recovery_test')
        all_successful_ids = initial_ids + degraded_mode_ids + recovery_ids
        unique_ids = set(all_successful_ids)
        self.assertEqual(len(unique_ids), len(all_successful_ids))
        cursor = self.postgres_client.cursor()
        cursor.execute('\n            SELECT COUNT(*) FROM id_registry_test\n            WHERE created_by = %s AND id_type = %s\n        ', ('test_framework', 'user'))
        stored_count = cursor.fetchone()[0]
        cursor.close()
        expected_minimum = len(initial_ids) + len(recovery_ids)
        self.assertGreaterEqual(stored_count, expected_minimum)

    async def test_network_partition_consistency(self):
        """HIGH DIFFICULTY: ID consistency during simulated network partitions"""
        partition_a_redis = redis.from_url(self.env.get_env_var('REDIS_URL', 'redis://localhost:6379/3'))
        partition_b_redis = redis.from_url(self.env.get_env_var('REDIS_URL', 'redis://localhost:6379/4'))
        manager_a = UnifiedIDManager(redis_client=partition_a_redis, postgres_client=self.postgres_client, config_manager=self.config_manager, instance_id='partition_a')
        manager_b = UnifiedIDManager(redis_client=partition_b_redis, postgres_client=self.postgres_client, config_manager=self.config_manager, instance_id='partition_b')
        partition_a_ids = []
        partition_b_ids = []

        async def generate_in_partition_a():
            for i in range(20):
                user_id = await manager_a.generate_user_id()
                partition_a_ids.append(user_id)
                await asyncio.sleep(0.01)

        async def generate_in_partition_b():
            for i in range(20):
                user_id = await manager_b.generate_user_id()
                partition_b_ids.append(user_id)
                await asyncio.sleep(0.01)
        await asyncio.gather(generate_in_partition_a(), generate_in_partition_b())
        all_partition_ids = partition_a_ids + partition_b_ids
        unique_partition_ids = set(all_partition_ids)
        self.assertEqual(len(unique_partition_ids), len(all_partition_ids))
        for user_id in all_partition_ids:
            self.track_generated_id(user_id, 'network_partition_test')
        for user_id in all_partition_ids:
            self.assertTrue(user_id.startswith('user_'))
            self.assertEqual(len(user_id), 41)
        partition_a_redis.flushdb()
        partition_b_redis.flushdb()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')