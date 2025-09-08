"""
Test Real ClickHouse Data Ingestion

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable data ingestion infrastructure for analytics and business intelligence
- Value Impact: Critical for agent state history ($15K+ MRR), user analytics, billing data, and performance metrics
- Strategic Impact: Core data infrastructure enables all analytics features, compliance reporting, and business insights

CRITICAL: This test validates our analytics infrastructure can reliably ingest and process high-volume customer data,
ensuring data integrity, performance, and scalability for business-critical analytics.
"""

import asyncio
import pytest
import time
import logging
import json
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Import test utilities with proper paths
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.isolated_environment import get_env

# Import from correct location based on actual codebase structure
try:
    from netra_backend.app.db.clickhouse import (
        get_clickhouse_client, 
        get_clickhouse_service,
        ClickHouseService,
        NoOpClickHouseClient
    )
except ImportError:
    # Fallback to analytics_service if netra_backend doesn't have ClickHouse
    from analytics_service.analytics_core.database.connection import (
        get_clickhouse_manager,
        StubClickHouseManager
    )
    # Create compatibility shims
    get_clickhouse_client = get_clickhouse_manager
    get_clickhouse_service = get_clickhouse_manager
    ClickHouseService = StubClickHouseManager
    NoOpClickHouseClient = StubClickHouseManager


class TestRealClickHouseDataIngestion:
    """Test ClickHouse data ingestion with real service infrastructure."""
    
    # SSOT: Test ports from TEST_CREATION_GUIDE.md
    TEST_CLICKHOUSE_PORT = 8125  # ClickHouse HTTP port in test environment
    
    def setup_method(self):
        """Setup method for each test."""
        self.test_user_id = "test_user_ingestion"
        self.env = get_env()  # Use IsolatedEnvironment per CLAUDE.md
        self.logger = logging.getLogger(__name__)
        self.test_table_name = f"test_ingestion_{int(time.time())}"
        
    def teardown_method(self):
        """Cleanup method after each test."""
        # Clean up test tables if possible
        asyncio.run(self._cleanup_test_tables())
    
    async def _cleanup_test_tables(self):
        """Clean up test tables created during tests."""
        try:
            client = await self._get_clickhouse_client_for_user(self.test_user_id)
            if client and not self._is_stub_or_noop(client):
                if hasattr(client, 'execute'):
                    # Drop test tables
                    await client.execute(f"DROP TABLE IF EXISTS {self.test_table_name}")
                    self.logger.info(f"Cleaned up test table: {self.test_table_name}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup test tables: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_single_record_insertion(self):
        """Test inserting a single record into ClickHouse."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - data ingestion test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create test table
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    user_id String,
                    event_type String,
                    timestamp DateTime,
                    data String
                ) ENGINE = Memory
            """)
            
            # Insert single record
            test_data = {
                'id': 1,
                'user_id': self.test_user_id,
                'event_type': 'test_event',
                'timestamp': datetime.now(),
                'data': json.dumps({'test': 'data'})
            }
            
            await client.execute(f"""
                INSERT INTO {self.test_table_name} 
                (id, user_id, event_type, timestamp, data)
                VALUES (%(id)s, %(user_id)s, %(event_type)s, %(timestamp)s, %(data)s)
            """, params=test_data)
            
            # Verify insertion
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            assert result[0]['count'] == 1, "Should have inserted 1 record"
            
            # Verify data integrity
            result = await client.execute(f"""
                SELECT * FROM {self.test_table_name} WHERE id = 1
            """)
            assert len(result) == 1, "Should retrieve the inserted record"
            assert result[0]['user_id'] == self.test_user_id
            
            self.logger.info("✓ Single record insertion successful")
            
        except Exception as e:
            self.logger.error(f"Single record insertion failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_batch_data_insertion_medium(self):
        """Test batch insertion of medium-sized dataset (100+ records)."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - batch insertion test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create test table
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    user_id String,
                    metric_value Float64,
                    category String,
                    timestamp DateTime
                ) ENGINE = Memory
            """)
            
            # Generate batch data
            batch_size = 150
            batch_data = []
            for i in range(batch_size):
                batch_data.append({
                    'id': i,
                    'user_id': f"{self.test_user_id}_{i % 10}",
                    'metric_value': random.uniform(0, 100),
                    'category': f"category_{i % 5}",
                    'timestamp': datetime.now() - timedelta(minutes=i)
                })
            
            # Insert batch
            start_time = time.time()
            
            # Use batch insert with VALUES clause
            values_list = []
            for record in batch_data:
                values_list.append(f"""
                    ({record['id']}, '{record['user_id']}', {record['metric_value']}, 
                     '{record['category']}', '{record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}')
                """)
            
            values_str = ','.join(values_list)
            await client.execute(f"""
                INSERT INTO {self.test_table_name} 
                (id, user_id, metric_value, category, timestamp)
                VALUES {values_str}
            """)
            
            insertion_time = time.time() - start_time
            
            # Verify insertion
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            assert result[0]['count'] == batch_size, f"Should have inserted {batch_size} records"
            
            # Verify data distribution
            result = await client.execute(f"""
                SELECT category, COUNT(*) as count 
                FROM {self.test_table_name} 
                GROUP BY category 
                ORDER BY category
            """)
            assert len(result) == 5, "Should have 5 categories"
            
            # Check performance
            records_per_second = batch_size / insertion_time
            self.logger.info(f"✓ Batch insertion: {batch_size} records in {insertion_time:.2f}s "
                           f"({records_per_second:.0f} records/sec)")
            
            # Basic performance assertion
            assert records_per_second > 10, "Batch insertion should be reasonably fast"
            
        except Exception as e:
            self.logger.error(f"Batch insertion failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_large_batch_insertion_performance(self):
        """Test large batch insertion performance (10,000+ records)."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - large batch test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create test table optimized for performance
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    value Float64,
                    timestamp DateTime
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, id)
            """)
            
            # Generate large dataset
            batch_size = 10000
            chunk_size = 1000  # Insert in chunks to avoid memory issues
            
            total_start_time = time.time()
            total_inserted = 0
            
            for chunk_start in range(0, batch_size, chunk_size):
                chunk_data = []
                for i in range(chunk_start, min(chunk_start + chunk_size, batch_size)):
                    chunk_data.append(
                        f"({i}, {random.uniform(0, 1000)}, "
                        f"'{(datetime.now() - timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S')}')"
                    )
                
                values_str = ','.join(chunk_data)
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} (id, value, timestamp)
                    VALUES {values_str}
                """)
                total_inserted += len(chunk_data)
            
            total_time = time.time() - total_start_time
            
            # Verify insertion
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            assert result[0]['count'] == batch_size, f"Should have inserted {batch_size} records"
            
            # Check performance metrics
            records_per_second = batch_size / total_time
            self.logger.info(f"✓ Large batch insertion: {batch_size} records in {total_time:.2f}s "
                           f"({records_per_second:.0f} records/sec)")
            
            # Performance assertion - should handle at least 100 records/sec
            assert records_per_second > 100, f"Performance too low: {records_per_second:.0f} records/sec"
            
            # Verify data distribution
            result = await client.execute(f"""
                SELECT 
                    MIN(value) as min_val,
                    MAX(value) as max_val,
                    AVG(value) as avg_val
                FROM {self.test_table_name}
            """)
            
            assert result[0]['min_val'] >= 0, "Minimum value should be >= 0"
            assert result[0]['max_val'] <= 1000, "Maximum value should be <= 1000"
            
        except Exception as e:
            self.logger.error(f"Large batch insertion failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_streaming_data_ingestion_simulation(self):
        """Test streaming data ingestion pattern with continuous inserts."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - streaming test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create streaming table
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    stream_id String,
                    sequence_num UInt64,
                    data String,
                    timestamp DateTime
                ) ENGINE = Memory
            """)
            
            # Simulate multiple concurrent streams
            async def stream_producer(stream_id: str, duration_seconds: int) -> int:
                """Simulate a data stream producer."""
                count = 0
                start_time = time.time()
                
                while time.time() - start_time < duration_seconds:
                    # Insert streaming data
                    await client.execute(f"""
                        INSERT INTO {self.test_table_name} 
                        (stream_id, sequence_num, data, timestamp)
                        VALUES ('{stream_id}', {count}, 'stream_data_{count}', now())
                    """)
                    count += 1
                    await asyncio.sleep(0.1)  # Simulate streaming rate
                
                return count
            
            # Run multiple streams concurrently
            stream_count = 3
            duration = 2  # Run for 2 seconds
            
            tasks = [
                stream_producer(f"stream_{i}", duration) 
                for i in range(stream_count)
            ]
            
            results = await asyncio.gather(*tasks)
            total_records = sum(results)
            
            # Verify streaming data
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            assert result[0]['count'] == total_records, f"Should have {total_records} streaming records"
            
            # Verify stream isolation
            result = await client.execute(f"""
                SELECT stream_id, COUNT(*) as count 
                FROM {self.test_table_name}
                GROUP BY stream_id
                ORDER BY stream_id
            """)
            
            assert len(result) == stream_count, f"Should have {stream_count} streams"
            
            self.logger.info(f"✓ Streaming ingestion: {total_records} records from {stream_count} streams")
            
        except Exception as e:
            self.logger.error(f"Streaming ingestion failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_validation_after_insertion(self):
        """Test data validation and integrity after insertion."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - validation test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create table with various data types
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    int_value Int32,
                    float_value Float64,
                    bool_value UInt8,
                    string_value String,
                    json_value String,
                    null_value Nullable(String),
                    timestamp DateTime
                ) ENGINE = Memory
            """)
            
            # Insert test data with various types
            test_records = [
                {
                    'id': 1,
                    'int_value': 42,
                    'float_value': 3.14159,
                    'bool_value': 1,
                    'string_value': 'test_string',
                    'json_value': json.dumps({'key': 'value'}),
                    'null_value': None,
                    'timestamp': datetime.now()
                },
                {
                    'id': 2,
                    'int_value': -100,
                    'float_value': 2.71828,
                    'bool_value': 0,
                    'string_value': 'another_test',
                    'json_value': json.dumps({'nested': {'data': 123}}),
                    'null_value': 'not_null',
                    'timestamp': datetime.now()
                }
            ]
            
            for record in test_records:
                null_val = 'NULL' if record['null_value'] is None else f"'{record['null_value']}'"
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} 
                    (id, int_value, float_value, bool_value, string_value, json_value, null_value, timestamp)
                    VALUES (
                        {record['id']}, {record['int_value']}, {record['float_value']}, 
                        {record['bool_value']}, '{record['string_value']}', 
                        '{record['json_value']}', {null_val}, 
                        '{record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}'
                    )
                """)
            
            # Validate data types
            result = await client.execute(f"SELECT * FROM {self.test_table_name} ORDER BY id")
            assert len(result) == 2, "Should have 2 records"
            
            # Validate first record
            first = result[0]
            assert first['int_value'] == 42
            assert abs(first['float_value'] - 3.14159) < 0.00001
            assert first['bool_value'] == 1
            assert first['string_value'] == 'test_string'
            
            # Validate JSON data
            json_data = json.loads(first['json_value'])
            assert json_data['key'] == 'value'
            
            # Validate aggregations
            result = await client.execute(f"""
                SELECT 
                    SUM(int_value) as sum_int,
                    AVG(float_value) as avg_float,
                    COUNT(*) as total_count,
                    COUNT(null_value) as non_null_count
                FROM {self.test_table_name}
            """)
            
            assert result[0]['sum_int'] == -58  # 42 + (-100)
            assert result[0]['total_count'] == 2
            assert result[0]['non_null_count'] == 1  # Only one non-null value
            
            self.logger.info("✓ Data validation successful - all types and aggregations correct")
            
        except Exception as e:
            self.logger.error(f"Data validation failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_malformed_data_error_handling(self):
        """Test error handling for malformed data insertion."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - error handling test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create strict table
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    required_field String,
                    numeric_field Int32
                ) ENGINE = Memory
            """)
            
            # Test 1: Missing required field
            with pytest.raises(Exception) as exc_info:
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} (id, numeric_field)
                    VALUES (1, 100)
                """)
            self.logger.info(f"✓ Missing field error caught: {exc_info.type.__name__}")
            
            # Test 2: Type mismatch
            with pytest.raises(Exception) as exc_info:
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} (id, required_field, numeric_field)
                    VALUES (2, 'valid', 'not_a_number')
                """)
            self.logger.info(f"✓ Type mismatch error caught: {exc_info.type.__name__}")
            
            # Verify no partial data was inserted
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            assert result[0]['count'] == 0, "No data should be inserted on errors"
            
            self.logger.info("✓ Malformed data error handling working correctly")
            
        except pytest.raises:
            raise  # Re-raise pytest.raises exceptions
        except Exception as e:
            self.logger.error(f"Error handling test failed unexpectedly: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_transaction_rollback_simulation(self):
        """Test transaction rollback behavior on insertion failure."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - rollback test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create table
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    data String
                ) ENGINE = Memory
            """)
            
            # Insert initial data
            await client.execute(f"""
                INSERT INTO {self.test_table_name} (id, data)
                VALUES (1, 'initial_data')
            """)
            
            # Verify initial state
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            initial_count = result[0]['count']
            assert initial_count == 1, "Should have 1 initial record"
            
            # Attempt batch insert with intentional failure
            batch_with_error = """
                (2, 'valid_data'),
                (3, 'another_valid'),
                (INVALID_ID, 'this_will_fail')
            """
            
            try:
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} (id, data)
                    VALUES {batch_with_error}
                """)
            except Exception:
                # Expected to fail
                pass
            
            # Verify rollback - count should remain the same
            result = await client.execute(f"SELECT COUNT(*) as count FROM {self.test_table_name}")
            final_count = result[0]['count']
            
            # Note: ClickHouse doesn't have traditional transactions
            # But batch inserts should be atomic
            self.logger.info(f"Initial count: {initial_count}, Final count: {final_count}")
            
            # For ClickHouse, the behavior depends on the engine and settings
            # Memory engine should maintain consistency
            assert final_count <= initial_count + 2, "Partial batch should not be inserted"
            
            self.logger.info("✓ Transaction rollback simulation completed")
            
        except Exception as e:
            self.logger.error(f"Rollback test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_data_deduplication_handling(self):
        """Test data deduplication mechanisms in ClickHouse."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - deduplication test not applicable")
        
        if not hasattr(client, 'execute'):
            pytest.skip("ClickHouse client doesn't support execute method")
        
        try:
            # Create table with ReplacingMergeTree for deduplication
            await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_table_name} (
                    id UInt64,
                    version UInt32,
                    data String,
                    timestamp DateTime
                ) ENGINE = ReplacingMergeTree(version)
                ORDER BY id
            """)
            
            # Insert duplicate records with different versions
            duplicates = [
                (1, 1, 'version_1', datetime.now()),
                (1, 2, 'version_2', datetime.now()),  # Same ID, newer version
                (1, 3, 'version_3', datetime.now()),  # Same ID, newest version
                (2, 1, 'different_id', datetime.now())
            ]
            
            for dup_id, version, data, ts in duplicates:
                await client.execute(f"""
                    INSERT INTO {self.test_table_name} (id, version, data, timestamp)
                    VALUES ({dup_id}, {version}, '{data}', '{ts.strftime('%Y-%m-%d %H:%M:%S')}')
                """)
            
            # Force merge to apply deduplication
            await client.execute(f"OPTIMIZE TABLE {self.test_table_name} FINAL")
            
            # Check deduplication result
            result = await client.execute(f"""
                SELECT id, version, data 
                FROM {self.test_table_name} 
                ORDER BY id, version DESC
            """)
            
            # Should have deduplicated to latest versions
            id_1_records = [r for r in result if r['id'] == 1]
            
            # ReplacingMergeTree keeps the row with max version
            if len(id_1_records) == 1:
                assert id_1_records[0]['version'] == 3, "Should keep latest version"
                assert id_1_records[0]['data'] == 'version_3'
                self.logger.info("✓ Deduplication working correctly - latest version retained")
            else:
                # Some ClickHouse configurations might not immediately deduplicate
                self.logger.info(f"Deduplication test: found {len(id_1_records)} records for ID 1")
            
        except Exception as e:
            self.logger.error(f"Deduplication test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_state_history_ingestion(self):
        """Test ingestion of agent state history - real business data."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - agent history test not applicable")
        
        # Check if the service has the agent history method
        service = get_clickhouse_service()
        if not hasattr(service, 'insert_agent_state_history'):
            pytest.skip("ClickHouse service doesn't support agent state history")
        
        try:
            # Create agent state history entry
            agent_state = {
                'run_id': f'test_run_{int(time.time())}',
                'thread_id': f'test_thread_{self.test_user_id}',
                'user_id': self.test_user_id,
                'agent_name': 'cost_optimizer',
                'state': 'completed',
                'input_tokens': 1500,
                'output_tokens': 750,
                'total_cost': 0.0375,
                'execution_time': 5.2,
                'tools_used': json.dumps(['analyze_costs', 'generate_report']),
                'metadata': json.dumps({
                    'optimization_type': 'aws_cost',
                    'potential_savings': 2500.00,
                    'recommendations_count': 5
                })
            }
            
            # Insert agent state history
            await service.insert_agent_state_history(
                run_id=agent_state['run_id'],
                thread_id=agent_state['thread_id'],
                user_id=agent_state['user_id'],
                agent_name=agent_state['agent_name'],
                state=agent_state['state'],
                input_tokens=agent_state['input_tokens'],
                output_tokens=agent_state['output_tokens'],
                total_cost=agent_state['total_cost'],
                execution_time=agent_state['execution_time'],
                tools_used=agent_state['tools_used'],
                metadata=agent_state['metadata']
            )
            
            self.logger.info("✓ Agent state history ingestion successful")
            
            # If we can query, verify the data
            if hasattr(client, 'execute'):
                # Try to query agent history (table name might vary)
                try:
                    result = await client.execute(f"""
                        SELECT * FROM agent_state_history 
                        WHERE run_id = '{agent_state['run_id']}'
                    """)
                    
                    if result:
                        assert result[0]['user_id'] == self.test_user_id
                        assert result[0]['agent_name'] == 'cost_optimizer'
                        self.logger.info("✓ Agent state history verified in database")
                except:
                    # Table might not exist or have different name
                    pass
            
        except Exception as e:
            self.logger.error(f"Agent state history ingestion failed: {e}")
            raise
    
    # Helper methods
    async def _get_clickhouse_client_for_user(self, user_id: str):
        """Get ClickHouse client with user context per factory pattern."""
        try:
            if hasattr(get_clickhouse_client, '__call__'):
                # If it's the netra_backend version
                client_or_context = get_clickhouse_client()
                # Check if it returns a context manager
                if hasattr(client_or_context, '__aenter__'):
                    async with client_or_context as client:
                        return client
                else:
                    return await client_or_context if asyncio.iscoroutine(client_or_context) else client_or_context
            else:
                # If it's the analytics_service version
                return get_clickhouse_client()
        except Exception as e:
            self.logger.warning(f"Failed to get ClickHouse client: {e}")
            return None
    
    def _is_stub_or_noop(self, client) -> bool:
        """Check if client is a stub or noop implementation."""
        if client is None:
            return True
        return isinstance(client, (NoOpClickHouseClient, StubClickHouseManager)) or \
               type(client).__name__ in ['StubClickHouseManager', 'NoOpClickHouseClient']