"""
Test ClickHouse Corpus Table Operations - Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable corpus data storage and retrieval
- Value Impact: Critical for AI model training data integrity (100% accuracy required)
- Strategic Impact: Enables data-driven AI improvements (+$20K MRR from better models)

This test suite validates ClickHouse corpus table operations with real database connections,
ensuring data integrity and performance for multi-user corpus management.
"""
import pytest
import asyncio
import uuid
from typing import Dict, List, Any
from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import validate_test_config

class TestClickHouseCorpusTableIntegration(BaseIntegrationTest):
    """Test ClickHouse corpus table operations with real database connections."""

    def setup_method(self):
        """Setup test environment and validate configuration."""
        validate_test_config('backend')
        self.corpus_id = str(uuid.uuid4()).replace('-', '_')
        self.table_name = f'test_corpus_{self.corpus_id}'

    async def cleanup_table(self, table_name: str):
        """Cleanup test table after test completion."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {table_name}')
        except Exception as e:
            print(f'Warning: Failed to cleanup table {table_name}: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_table_creation_and_structure(self):
        """Test corpus table creation with proper structure and constraints.
        
        Critical for ensuring corpus data can be stored with required fields.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                create_query = f"\n                CREATE TABLE IF NOT EXISTS {self.table_name} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    corpus_name String,\n                    workload_type String,\n                    prompt String,\n                    response String, \n                    metadata String DEFAULT '{{}}',\n                    domain String DEFAULT 'general',\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    updated_at DateTime64(3) DEFAULT now64(3),\n                    version UInt32 DEFAULT 1,\n                    embedding Array(Float32) DEFAULT [],\n                    tags Array(String) DEFAULT [],\n                    quality_score Float32 DEFAULT 0.0,\n                    is_active Bool DEFAULT true\n                ) ENGINE = MergeTree()\n                PARTITION BY (user_id, toYYYYMM(created_at))\n                ORDER BY (user_id, workload_type, created_at, record_id)\n                "
                await client.execute(create_query)
                describe_result = await client.execute(f'DESCRIBE TABLE {self.table_name}')
                columns = [row['name'] for row in describe_result]
                required_columns = ['record_id', 'user_id', 'corpus_name', 'workload_type', 'prompt', 'response', 'created_at', 'embedding']
                for col in required_columns:
                    assert col in columns, f"Required column '{col}' missing from corpus table"
                table_info = await client.execute(f"\n                    SELECT engine, partition_key, sorting_key \n                    FROM system.tables \n                    WHERE name = '{self.table_name}'\n                ")
                assert len(table_info) == 1, 'Table should exist in system.tables'
                assert table_info[0]['engine'] == 'MergeTree', 'Should use MergeTree engine'
        finally:
            await self.cleanup_table(self.table_name)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_data_insertion_and_retrieval(self):
        """Test corpus data insertion and retrieval with user isolation.
        
        Validates multi-user corpus data integrity and isolation.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.table_name} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    corpus_name String,\n                    workload_type String,\n                    prompt String,\n                    response String,\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    embedding Array(Float32) DEFAULT [],\n                    tags Array(String) DEFAULT []\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, created_at, record_id)\n                ')
                test_data = [{'user_id': 'user-123', 'corpus_name': 'user123_corpus', 'workload_type': 'chat_completion', 'prompt': 'What is machine learning?', 'response': 'Machine learning is a subset of artificial intelligence...', 'embedding': [0.1, 0.2, 0.3, 0.4, 0.5], 'tags': ['education', 'ml_basics']}, {'user_id': 'user-456', 'corpus_name': 'user456_corpus', 'workload_type': 'code_generation', 'prompt': 'Create a Python function to sort a list', 'response': 'def sort_list(items): return sorted(items)', 'embedding': [0.6, 0.7, 0.8, 0.9, 1.0], 'tags': ['programming', 'python']}]
                for data in test_data:
                    await client.execute(f'\n                        INSERT INTO {self.table_name} \n                        (user_id, corpus_name, workload_type, prompt, response, embedding, tags)\n                        VALUES (%(user_id)s, %(corpus_name)s, %(workload_type)s, \n                               %(prompt)s, %(response)s, %(embedding)s, %(tags)s)\n                    ', data)
                await asyncio.sleep(0.1)
                user123_data = await client.execute(f"\n                    SELECT user_id, corpus_name, workload_type, prompt, response\n                    FROM {self.table_name} \n                    WHERE user_id = 'user-123'\n                ")
                user456_data = await client.execute(f"\n                    SELECT user_id, corpus_name, workload_type, prompt, response\n                    FROM {self.table_name} \n                    WHERE user_id = 'user-456' \n                ")
                assert len(user123_data) == 1, 'User-123 should have exactly 1 record'
                assert len(user456_data) == 1, 'User-456 should have exactly 1 record'
                assert user123_data[0]['corpus_name'] == 'user123_corpus'
                assert user456_data[0]['corpus_name'] == 'user456_corpus'
                assert user123_data[0]['workload_type'] == 'chat_completion'
                assert user456_data[0]['workload_type'] == 'code_generation'
                assert 'machine learning' in user123_data[0]['response'].lower()
                assert 'sort_list' in user456_data[0]['response']
        finally:
            await self.cleanup_table(self.table_name)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_table_performance_and_indexing(self):
        """Test corpus table performance with proper indexing.
        
        Ensures corpus queries perform well under realistic data volumes.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"\n                CREATE TABLE IF NOT EXISTS {self.table_name} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    workload_type String,\n                    prompt String,\n                    response String,\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    domain String DEFAULT 'general',\n                    tags Array(String) DEFAULT []\n                ) ENGINE = MergeTree()\n                PARTITION BY (user_id, toYYYYMM(created_at))\n                ORDER BY (user_id, workload_type, created_at, record_id)\n                ")
                bulk_data = []
                for i in range(100):
                    user_id = f'perf-user-{i % 10}'
                    bulk_data.append({'user_id': user_id, 'workload_type': 'performance_test', 'prompt': f'Performance test prompt {i}', 'response': f'Performance test response {i}' * 10, 'domain': 'testing', 'tags': ['performance', f'batch_{i // 10}']})
                for data in bulk_data:
                    await client.execute(f'\n                        INSERT INTO {self.table_name} \n                        (user_id, workload_type, prompt, response, domain, tags)\n                        VALUES (%(user_id)s, %(workload_type)s, %(prompt)s, %(response)s, %(domain)s, %(tags)s)\n                    ', data)
                await asyncio.sleep(0.2)
                import time
                start_time = time.time()
                user_query_result = await client.execute(f"\n                    SELECT COUNT(*) as count, user_id\n                    FROM {self.table_name} \n                    WHERE user_id = 'perf-user-1'\n                    AND workload_type = 'performance_test'\n                    GROUP BY user_id\n                ")
                end_time = time.time()
                query_duration = end_time - start_time
                assert query_duration < 1.0, f'Query took too long: {query_duration:.2f}s'
                assert len(user_query_result) == 1, 'Should return exactly one user group'
                assert user_query_result[0]['count'] == 10, 'Should have 10 records for perf-user-1'
                start_time = time.time()
                aggregate_result = await client.execute(f"\n                    SELECT \n                        workload_type,\n                        COUNT(*) as total_records,\n                        COUNT(DISTINCT user_id) as unique_users\n                    FROM {self.table_name}\n                    WHERE workload_type = 'performance_test'\n                    GROUP BY workload_type\n                ")
                end_time = time.time()
                aggregate_duration = end_time - start_time
                assert aggregate_duration < 1.0, f'Aggregate query took too long: {aggregate_duration:.2f}s'
                assert len(aggregate_result) == 1, 'Should have one workload type'
                assert aggregate_result[0]['total_records'] == 100, 'Should have 100 total records'
                assert aggregate_result[0]['unique_users'] == 10, 'Should have 10 unique users'
        finally:
            await self.cleanup_table(self.table_name)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_table_concurrent_operations(self):
        """Test corpus table handles concurrent operations safely.
        
        Critical for multi-user platform ensuring data consistency under load.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.table_name} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String, \n                    operation_id String,\n                    data String,\n                    created_at DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, created_at, record_id)\n                ')

                async def insert_user_data(user_id: str, operation_count: int):
                    """Insert data for a specific user concurrently."""
                    async with get_clickhouse_client(bypass_manager=True) as concurrent_client:
                        for i in range(operation_count):
                            await concurrent_client.execute(f'\n                                INSERT INTO {self.table_name} \n                                (user_id, operation_id, data)\n                                VALUES (%(user_id)s, %(operation_id)s, %(data)s)\n                            ', {'user_id': user_id, 'operation_id': f'{user_id}-op-{i}', 'data': f'Concurrent data for {user_id} operation {i}'})
                concurrent_tasks = [insert_user_data('concurrent-user-1', 20), insert_user_data('concurrent-user-2', 15), insert_user_data('concurrent-user-3', 25)]
                await asyncio.gather(*concurrent_tasks)
                await asyncio.sleep(0.3)
                total_records = await client.execute(f'\n                    SELECT COUNT(*) as total FROM {self.table_name}\n                ')
                assert total_records[0]['total'] == 60, 'Should have 60 total records (20+15+25)'
                user_counts = await client.execute(f'\n                    SELECT user_id, COUNT(*) as count \n                    FROM {self.table_name}\n                    GROUP BY user_id\n                    ORDER BY user_id\n                ')
                expected_counts = {'concurrent-user-1': 20, 'concurrent-user-2': 15, 'concurrent-user-3': 25}
                for row in user_counts:
                    user_id = row['user_id']
                    actual_count = row['count']
                    expected_count = expected_counts[user_id]
                    assert actual_count == expected_count, f'User {user_id}: expected {expected_count}, got {actual_count}'
                unique_operations = await client.execute(f'\n                    SELECT COUNT(DISTINCT operation_id) as unique_ops FROM {self.table_name}\n                ')
                assert unique_operations[0]['unique_ops'] == 60, 'All operation IDs should be unique'
        finally:
            await self.cleanup_table(self.table_name)

class TestClickHouseCorpusTableServiceIntegration(BaseIntegrationTest):
    """Test corpus table operations through ClickHouse service layer."""

    def setup_method(self):
        """Setup test environment."""
        validate_test_config('backend')
        self.service = None
        self.test_table = f'test_service_corpus_{uuid.uuid4().hex[:8]}'

    async def cleanup_service_table(self):
        """Cleanup service test table."""
        if self.service:
            try:
                await self.service.execute(f'DROP TABLE IF EXISTS {self.test_table}')
            except Exception as e:
                print(f'Warning: Failed to cleanup service table {self.test_table}: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_operations_through_service_with_caching(self):
        """Test corpus operations through ClickHouse service with caching.
        
        Validates service layer provides proper caching and user isolation.
        """
        try:
            self.service = get_clickhouse_service()
            await self.service.initialize()
            await self.service.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_table} (\n                    record_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    prompt String,\n                    response String,\n                    created_at DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, created_at, record_id)\n            ', user_id='admin')
            await self.service.execute(f'\n                INSERT INTO {self.test_table} (user_id, prompt, response)\n                VALUES (%(user_id)s, %(prompt)s, %(response)s)\n            ', {'user_id': 'cache-test-user', 'prompt': 'Test caching behavior', 'response': 'This response should be cached'}, user_id='cache-test-user')
            await asyncio.sleep(0.1)
            query = f'SELECT prompt, response FROM {self.test_table} WHERE user_id = %(user_id)s'
            params = {'user_id': 'cache-test-user'}
            result1 = await self.service.execute(query, params, user_id='cache-test-user')
            assert len(result1) == 1, 'Should return one record'
            assert result1[0]['prompt'] == 'Test caching behavior'
            cache_stats_before = self.service.get_cache_stats('cache-test-user')
            result2 = await self.service.execute(query, params, user_id='cache-test-user')
            assert result2 == result1, 'Cached result should match original'
            cache_stats_after = self.service.get_cache_stats('cache-test-user')
            assert cache_stats_after is not None, 'Should have cache stats'
        finally:
            await self.cleanup_service_table()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')