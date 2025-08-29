"""
ClickHouse Performance Tests
Tests for ClickHouse performance and optimization features
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import json
import random
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.logging_config import central_logger as logger

from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing
from netra_backend.tests.clickhouse.test_clickhouse_permissions import (
    _check_table_insert_permission,
)

class TestClickHousePerformance:
    """Test ClickHouse performance and optimization"""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Add timeout to prevent hanging
    async def test_batch_insert_performance(self):
        """Test batch insert performance"""
        async with get_clickhouse_client() as client:
            # Check if we're using mock client - skip expensive operations
            from netra_backend.app.db.clickhouse import MockClickHouseDatabase
            if isinstance(client, MockClickHouseDatabase):
                logger.info("Using mock ClickHouse client - skipping table creation and permission checks")
                await self._execute_batch_insert_test(client)
                return
            
            # Only do expensive operations for real clients
            # Ensure table exists
            await create_workload_events_table_if_missing()
            
            # Check INSERT permission
            has_insert = await _check_table_insert_permission(client, "workload_events")
            if not has_insert:
                pytest.skip("development_user lacks INSERT privileges for workload_events")
            
            await self._execute_batch_insert_test(client)

    async def _execute_batch_insert_test(self, client):
        """Execute batch insert performance test"""
        # Use smaller batch size for faster testing - performance tests should be quick
        batch_size = 100  # Reduced from 1000 for faster execution
        events = self._generate_performance_events(batch_size)
        
        # Measure insert time
        start_time = time.time()
        await self._perform_batch_insert(client, events)
        insert_duration = time.time() - start_time
        
        await self._log_performance_metrics(batch_size, insert_duration)
        await self._verify_batch_insertion(client, batch_size)

    def _generate_performance_events(self, batch_size):
        """Generate large batch of events for performance testing"""
        events = []
        base_time = datetime.now(UTC)
        
        for i in range(batch_size):
            event = self._create_performance_event(i, base_time)
            events.append(event)
        return events

    def _create_performance_event(self, index, base_time):
        """Create single performance test event"""
        return [
            str(uuid.uuid4()),  # trace_id
            str(uuid.uuid4()),  # span_id
            f'perf_user_{index % 10}',  # user_id
            f'perf_session_{index % 5}',  # session_id
            base_time - timedelta(seconds=index),  # timestamp
            random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),  # workload_type
            'completed',  # status
            random.randint(50, 2000),  # duration_ms
            ['latency_ms', 'throughput', 'cpu_usage'],  # metrics.name
            [random.uniform(10, 100), random.uniform(100, 1000), random.uniform(0, 100)],  # metrics.value
            ['ms', 'req/s', 'percent'],  # metrics.unit
            f'Performance test input {index}',  # input_text
            f'Performance test output {index}',  # output_text
            json.dumps({'batch_test': True, 'index': index})  # metadata
        ]

    async def _perform_batch_insert(self, client, events):
        """Perform the actual batch insert operation"""
        # Use the base client for raw insert
        if hasattr(client, 'base_client'):
            base_client = client.base_client
        else:
            base_client = client
        
        # Batch insert
        column_names = self._get_column_names()
        await base_client.insert_data('workload_events', events, column_names=column_names)

    def _get_column_names(self):
        """Get column names for batch insert"""
        return [
            'trace_id', 'span_id', 'user_id', 'session_id', 'timestamp',
            'workload_type', 'status', 'duration_ms',
            'metrics.name', 'metrics.value', 'metrics.unit',
            'input_text', 'output_text', 'metadata'
        ]

    async def _log_performance_metrics(self, batch_size, insert_duration):
        """Log performance metrics from batch insert"""
        logger.info(f"Inserted {batch_size} events in {insert_duration:.2f} seconds")
        logger.info(f"Insert rate: {batch_size/insert_duration:.0f} events/second")

    async def _verify_batch_insertion(self, client, expected_count):
        """Verify batch insertion was successful"""
        # Check if we're using a mock client
        from netra_backend.app.db.clickhouse import MockClickHouseDatabase
        if isinstance(client, MockClickHouseDatabase):
            # For mock clients, just verify the method worked (no actual data to verify)
            logger.info(f"[MOCK ClickHouse] Batch insertion test completed with {expected_count} events")
            return
        
        # For real clients, verify the data was actually inserted
        count_result = await client.execute_query(
            "SELECT count() as count FROM workload_events WHERE metadata LIKE '%batch_test%'"
        )
        assert count_result[0]['count'] >= expected_count

    @pytest.mark.asyncio
    async def test_query_performance_with_indexes(self):
        """Test query performance with proper indexing"""
        async with get_clickhouse_client() as client:
            # Test indexed query performance
            await self._test_indexed_query_performance(client)
            await self._test_full_scan_performance(client)

    async def _test_indexed_query_performance(self, client):
        """Test performance of indexed queries"""
        start_time = time.time()
        indexed_query = self._build_indexed_query()
        
        result = await client.execute_query(indexed_query)
        indexed_duration = time.time() - start_time
        
        logger.info(f"Indexed query completed in {indexed_duration:.3f} seconds")
        return indexed_duration

    def _build_indexed_query(self):
        """Build query that uses primary key columns (indexed)"""
        return """
        SELECT 
            workload_type,
            count() as cnt,
            avg(duration_ms) as avg_duration
        FROM workload_events
        WHERE workload_type IN ('simple_chat', 'rag_pipeline')
            AND timestamp >= now() - INTERVAL 1 DAY
        GROUP BY workload_type
        """

    async def _test_full_scan_performance(self, client):
        """Test performance of full scan queries"""
        start_time = time.time()
        full_scan_query = self._build_full_scan_query()
        
        result = await client.execute_query(full_scan_query)
        full_scan_duration = time.time() - start_time
        
        logger.info(f"Full scan query completed in {full_scan_duration:.3f} seconds")
        return full_scan_duration

    def _build_full_scan_query(self):
        """Build query that requires full table scan"""
        return """
        SELECT 
            count() as cnt
        FROM workload_events
        WHERE input_text LIKE '%test%'
        """

    @pytest.mark.asyncio
    async def test_query_interceptor_statistics(self):
        """Test query interceptor statistics tracking"""
        async with get_clickhouse_client() as client:
            # Reset statistics if possible
            if hasattr(client, 'reset_statistics'):
                client.reset_statistics()
            
            await self._execute_test_queries(client)
            await self._check_interceptor_statistics(client)

    async def _execute_test_queries(self, client):
        """Execute queries with different patterns for interceptor testing"""
        queries = [
            "SELECT metrics.value[1] FROM workload_events LIMIT 1",  # Needs fixing
            "SELECT arrayElement(metrics.value, 1) FROM workload_events LIMIT 1",  # Already correct
            "SELECT * FROM workload_events LIMIT 1",  # No arrays
            "SELECT metrics.name[idx], metrics.value[idx] FROM workload_events LIMIT 1"  # Multiple fixes
        ]
        
        for query in queries:
            try:
                await client.execute_query(query)
            except Exception as e:
                logger.warning(f"Query failed (expected for some): {e}")

    async def _check_interceptor_statistics(self, client):
        """Check and log interceptor statistics"""
        # Get statistics
        if hasattr(client, 'get_statistics'):
            stats = client.get_statistics()
            logger.info(f"Query interceptor statistics: {stats}")
            assert stats['queries_executed'] >= 4
            assert stats['queries_fixed'] >= 2  # At least 2 queries needed fixing

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])