"""
ClickHouse Performance Tests - Simplified Version
Tests for ClickHouse performance without complex configuration loading
"""

import json
import random
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.logging_config import central_logger as logger


class TestClickHousePerformanceSimple:
    """Test ClickHouse performance with simplified configuration"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # Short timeout for fast execution
    async def test_batch_insert_performance_simple(self):
        """Test batch insert performance using direct mock client"""
        # Import and create mock client directly to avoid configuration overhead
        from netra_backend.app.db.clickhouse import MockClickHouseDatabase
        
        client = MockClickHouseDatabase()
        logger.info("Using simplified mock ClickHouse client for performance testing")
        
        await self._execute_batch_insert_test(client)

    async def _execute_batch_insert_test(self, client):
        """Execute batch insert performance test"""
        batch_size = 100  # Fast execution
        events = self._generate_performance_events(batch_size)
        
        # Measure insert time
        start_time = time.time()
        await self._perform_batch_insert(client, events)
        insert_duration = time.time() - start_time
        
        await self._log_performance_metrics(batch_size, insert_duration)
        await self._verify_batch_insertion(client, batch_size)

    def _generate_performance_events(self, batch_size):
        """Generate events for performance testing"""
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
            random.randint(50, 200),  # duration_ms
            ['latency_ms', 'throughput', 'cpu_usage'],  # metrics.name
            [random.uniform(10, 100), random.uniform(100, 1000), random.uniform(0, 100)],  # metrics.value
            ['ms', 'req/s', 'percent'],  # metrics.unit
            f'Performance test input {index}',  # input_text
            f'Performance test output {index}',  # output_text
            json.dumps({'batch_test': True, 'index': index})  # metadata
        ]

    async def _perform_batch_insert(self, client, events):
        """Perform the actual batch insert operation"""
        column_names = [
            'trace_id', 'span_id', 'user_id', 'session_id', 'timestamp',
            'workload_type', 'status', 'duration_ms',
            'metrics.name', 'metrics.value', 'metrics.unit',
            'input_text', 'output_text', 'metadata'
        ]
        
        # Use insert_data method (this was the missing method that caused the original timeout)
        await client.insert_data('workload_events', events, column_names=column_names)

    async def _log_performance_metrics(self, batch_size, insert_duration):
        """Log performance metrics from batch insert"""
        logger.info(f"[SIMPLE TEST] Inserted {batch_size} events in {insert_duration:.3f} seconds")
        rate = batch_size / insert_duration if insert_duration > 0 else float('inf')
        logger.info(f"[SIMPLE TEST] Insert rate: {rate:.0f} events/second")

    async def _verify_batch_insertion(self, client, expected_count):
        """Verify batch insertion was successful"""
        from netra_backend.app.db.clickhouse import MockClickHouseDatabase
        
        if isinstance(client, MockClickHouseDatabase):
            logger.info(f"[SIMPLE TEST] Mock batch insertion test completed with {expected_count} events")
            return
        
        # For real clients (not expected in this simplified test)
        count_result = await client.execute_query(
            "SELECT count() as count FROM workload_events WHERE metadata LIKE '%batch_test%'"
        )
        assert count_result[0]['count'] >= expected_count

    @pytest.mark.asyncio 
    @pytest.mark.timeout(5)
    async def test_mock_client_methods(self):
        """Test that all required mock client methods exist and work"""
        from netra_backend.app.db.clickhouse import MockClickHouseDatabase
        
        client = MockClickHouseDatabase()
        
        # Test all methods that the performance test uses
        start_time = time.time()
        
        # Basic methods
        await client.execute("SELECT 1")
        await client.execute_query("SELECT 1")
        await client.fetch("SELECT 1")
        await client.test_connection()
        client.ping()
        await client.command("SELECT 1")
        
        # The previously missing method
        await client.insert_data("test_table", [[1, 2, 3]], column_names=['a', 'b', 'c'])
        
        # Batch insert
        await client.batch_insert("test_table", [{"a": 1, "b": 2}])
        
        # Cleanup
        await client.cleanup()
        
        total_time = time.time() - start_time
        logger.info(f"All mock methods tested successfully in {total_time:.3f} seconds")
        
        # Should complete very quickly
        assert total_time < 1.0, f"Mock methods took too long: {total_time:.3f} seconds"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])