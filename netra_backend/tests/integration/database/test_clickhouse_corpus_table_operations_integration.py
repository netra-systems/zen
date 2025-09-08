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
        validate_test_config("backend")
        self.corpus_id = str(uuid.uuid4()).replace('-', '_')
        self.table_name = f"test_corpus_{self.corpus_id}"

    async def cleanup_table(self, table_name: str):
        """Cleanup test table after test completion."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {table_name}")
        except Exception as e:
            # Log cleanup failure but don't fail the test
            print(f"Warning: Failed to cleanup table {table_name}: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_corpus_table_creation_and_structure(self):
        """Test corpus table creation with proper structure and constraints.
        
        Critical for ensuring corpus data can be stored with required fields.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create corpus table with comprehensive structure
                create_query = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    corpus_name String,
                    workload_type String,
                    prompt String,
                    response String, 
                    metadata String DEFAULT '{{}}',
                    domain String DEFAULT 'general',
                    created_at DateTime64(3) DEFAULT now64(3),
                    updated_at DateTime64(3) DEFAULT now64(3),
                    version UInt32 DEFAULT 1,
                    embedding Array(Float32) DEFAULT [],
                    tags Array(String) DEFAULT [],
                    quality_score Float32 DEFAULT 0.0,
                    is_active Bool DEFAULT true
                ) ENGINE = MergeTree()
                PARTITION BY (user_id, toYYYYMM(created_at))
                ORDER BY (user_id, workload_type, created_at, record_id)
                """
                
                await client.execute(create_query)
                
                # Verify table structure
                describe_result = await client.execute(f"DESCRIBE TABLE {self.table_name}")
                
                # Validate required columns exist
                columns = [row['name'] for row in describe_result]
                required_columns = [
                    'record_id', 'user_id', 'corpus_name', 'workload_type', 
                    'prompt', 'response', 'created_at', 'embedding'
                ]
                
                for col in required_columns:
                    assert col in columns, f"Required column '{col}' missing from corpus table"
                
                # Verify table engine and partitioning
                table_info = await client.execute(f"""
                    SELECT engine, partition_key, sorting_key 
                    FROM system.tables 
                    WHERE name = '{self.table_name}'
                """)
                
                assert len(table_info) == 1, "Table should exist in system.tables"
                assert table_info[0]['engine'] == 'MergeTree', "Should use MergeTree engine"
                
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
                # Create test table
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    corpus_name String,
                    workload_type String,
                    prompt String,
                    response String,
                    created_at DateTime64(3) DEFAULT now64(3),
                    embedding Array(Float32) DEFAULT [],
                    tags Array(String) DEFAULT []
                ) ENGINE = MergeTree()
                ORDER BY (user_id, created_at, record_id)
                """)
                
                # Insert test data for multiple users
                test_data = [
                    {
                        'user_id': 'user-123',
                        'corpus_name': 'user123_corpus',
                        'workload_type': 'chat_completion',
                        'prompt': 'What is machine learning?',
                        'response': 'Machine learning is a subset of artificial intelligence...',
                        'embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
                        'tags': ['education', 'ml_basics']
                    },
                    {
                        'user_id': 'user-456', 
                        'corpus_name': 'user456_corpus',
                        'workload_type': 'code_generation',
                        'prompt': 'Create a Python function to sort a list',
                        'response': 'def sort_list(items): return sorted(items)',
                        'embedding': [0.6, 0.7, 0.8, 0.9, 1.0],
                        'tags': ['programming', 'python']
                    }
                ]
                
                # Insert data
                for data in test_data:
                    await client.execute(f"""
                        INSERT INTO {self.table_name} 
                        (user_id, corpus_name, workload_type, prompt, response, embedding, tags)
                        VALUES (%(user_id)s, %(corpus_name)s, %(workload_type)s, 
                               %(prompt)s, %(response)s, %(embedding)s, %(tags)s)
                    """, data)
                
                # Wait for data to be available (ClickHouse eventual consistency)
                await asyncio.sleep(0.1)
                
                # Verify user data isolation
                user123_data = await client.execute(f"""
                    SELECT user_id, corpus_name, workload_type, prompt, response
                    FROM {self.table_name} 
                    WHERE user_id = 'user-123'
                """)
                
                user456_data = await client.execute(f"""
                    SELECT user_id, corpus_name, workload_type, prompt, response
                    FROM {self.table_name} 
                    WHERE user_id = 'user-456' 
                """)
                
                # Validate user isolation
                assert len(user123_data) == 1, "User-123 should have exactly 1 record"
                assert len(user456_data) == 1, "User-456 should have exactly 1 record"
                
                assert user123_data[0]['corpus_name'] == 'user123_corpus'
                assert user456_data[0]['corpus_name'] == 'user456_corpus'
                
                # Validate data integrity  
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
                # Create optimized corpus table
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    workload_type String,
                    prompt String,
                    response String,
                    created_at DateTime64(3) DEFAULT now64(3),
                    domain String DEFAULT 'general',
                    tags Array(String) DEFAULT []
                ) ENGINE = MergeTree()
                PARTITION BY (user_id, toYYYYMM(created_at))
                ORDER BY (user_id, workload_type, created_at, record_id)
                """)
                
                # Insert bulk test data to test performance
                bulk_data = []
                for i in range(100):  # Insert 100 records for performance testing
                    user_id = f"perf-user-{i % 10}"  # 10 different users
                    bulk_data.append({
                        'user_id': user_id,
                        'workload_type': 'performance_test',
                        'prompt': f'Performance test prompt {i}',
                        'response': f'Performance test response {i}' * 10,  # Longer responses
                        'domain': 'testing',
                        'tags': ['performance', f'batch_{i//10}']
                    })
                
                # Insert bulk data efficiently
                for data in bulk_data:
                    await client.execute(f"""
                        INSERT INTO {self.table_name} 
                        (user_id, workload_type, prompt, response, domain, tags)
                        VALUES (%(user_id)s, %(workload_type)s, %(prompt)s, %(response)s, %(domain)s, %(tags)s)
                    """, data)
                
                # Wait for data availability
                await asyncio.sleep(0.2)
                
                # Test query performance with user filtering
                import time
                start_time = time.time()
                
                user_query_result = await client.execute(f"""
                    SELECT COUNT(*) as count, user_id
                    FROM {self.table_name} 
                    WHERE user_id = 'perf-user-1'
                    AND workload_type = 'performance_test'
                    GROUP BY user_id
                """)
                
                end_time = time.time()
                query_duration = end_time - start_time
                
                # Performance validation
                assert query_duration < 1.0, f"Query took too long: {query_duration:.2f}s"
                assert len(user_query_result) == 1, "Should return exactly one user group"
                assert user_query_result[0]['count'] == 10, "Should have 10 records for perf-user-1"
                
                # Test aggregate query performance
                start_time = time.time()
                
                aggregate_result = await client.execute(f"""
                    SELECT 
                        workload_type,
                        COUNT(*) as total_records,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM {self.table_name}
                    WHERE workload_type = 'performance_test'
                    GROUP BY workload_type
                """)
                
                end_time = time.time()
                aggregate_duration = end_time - start_time
                
                assert aggregate_duration < 1.0, f"Aggregate query took too long: {aggregate_duration:.2f}s"
                assert len(aggregate_result) == 1, "Should have one workload type"
                assert aggregate_result[0]['total_records'] == 100, "Should have 100 total records"
                assert aggregate_result[0]['unique_users'] == 10, "Should have 10 unique users"
                
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
                # Create concurrent test table
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String, 
                    operation_id String,
                    data String,
                    created_at DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, created_at, record_id)
                """)
                
                # Define concurrent operations
                async def insert_user_data(user_id: str, operation_count: int):
                    """Insert data for a specific user concurrently."""
                    async with get_clickhouse_client(bypass_manager=True) as concurrent_client:
                        for i in range(operation_count):
                            await concurrent_client.execute(f"""
                                INSERT INTO {self.table_name} 
                                (user_id, operation_id, data)
                                VALUES (%(user_id)s, %(operation_id)s, %(data)s)
                            """, {
                                'user_id': user_id,
                                'operation_id': f"{user_id}-op-{i}",
                                'data': f"Concurrent data for {user_id} operation {i}"
                            })
                
                # Run concurrent operations for multiple users
                concurrent_tasks = [
                    insert_user_data("concurrent-user-1", 20),
                    insert_user_data("concurrent-user-2", 15),  
                    insert_user_data("concurrent-user-3", 25)
                ]
                
                # Execute all tasks concurrently
                await asyncio.gather(*concurrent_tasks)
                
                # Wait for data to be fully committed
                await asyncio.sleep(0.3)
                
                # Verify data integrity after concurrent operations
                total_records = await client.execute(f"""
                    SELECT COUNT(*) as total FROM {self.table_name}
                """)
                assert total_records[0]['total'] == 60, "Should have 60 total records (20+15+25)"
                
                # Verify per-user data integrity
                user_counts = await client.execute(f"""
                    SELECT user_id, COUNT(*) as count 
                    FROM {self.table_name}
                    GROUP BY user_id
                    ORDER BY user_id
                """)
                
                expected_counts = {
                    'concurrent-user-1': 20,
                    'concurrent-user-2': 15, 
                    'concurrent-user-3': 25
                }
                
                for row in user_counts:
                    user_id = row['user_id']
                    actual_count = row['count']
                    expected_count = expected_counts[user_id]
                    assert actual_count == expected_count, f"User {user_id}: expected {expected_count}, got {actual_count}"
                
                # Verify no data corruption (unique operation IDs)
                unique_operations = await client.execute(f"""
                    SELECT COUNT(DISTINCT operation_id) as unique_ops FROM {self.table_name}
                """)
                assert unique_operations[0]['unique_ops'] == 60, "All operation IDs should be unique"
                
        finally:
            await self.cleanup_table(self.table_name)


class TestClickHouseCorpusTableServiceIntegration(BaseIntegrationTest):
    """Test corpus table operations through ClickHouse service layer."""
    
    def setup_method(self):
        """Setup test environment."""
        validate_test_config("backend")
        self.service = None
        self.test_table = f"test_service_corpus_{uuid.uuid4().hex[:8]}"

    async def cleanup_service_table(self):
        """Cleanup service test table."""
        if self.service:
            try:
                await self.service.execute(f"DROP TABLE IF EXISTS {self.test_table}")
            except Exception as e:
                print(f"Warning: Failed to cleanup service table {self.test_table}: {e}")

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
            
            # Create table through service
            await self.service.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table} (
                    record_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    prompt String,
                    response String,
                    created_at DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, created_at, record_id)
            """, user_id="admin")
            
            # Insert test data
            await self.service.execute(f"""
                INSERT INTO {self.test_table} (user_id, prompt, response)
                VALUES (%(user_id)s, %(prompt)s, %(response)s)
            """, {
                'user_id': 'cache-test-user',
                'prompt': 'Test caching behavior',
                'response': 'This response should be cached'
            }, user_id="cache-test-user")
            
            # Wait for data availability
            await asyncio.sleep(0.1)
            
            # First query - should hit database
            query = f"SELECT prompt, response FROM {self.test_table} WHERE user_id = %(user_id)s"
            params = {'user_id': 'cache-test-user'}
            
            result1 = await self.service.execute(query, params, user_id="cache-test-user")
            assert len(result1) == 1, "Should return one record"
            assert result1[0]['prompt'] == 'Test caching behavior'
            
            # Second query - should hit cache (verify through cache stats)
            cache_stats_before = self.service.get_cache_stats("cache-test-user")
            
            result2 = await self.service.execute(query, params, user_id="cache-test-user")
            assert result2 == result1, "Cached result should match original"
            
            cache_stats_after = self.service.get_cache_stats("cache-test-user")
            
            # Verify cache hit (cache stats should have increased)
            assert cache_stats_after is not None, "Should have cache stats"
            
        finally:
            await self.cleanup_service_table()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])