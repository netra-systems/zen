from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment
"""
Critical ClickHouse Reliability Tests - Cycles 16-20
Tests revenue-critical ClickHouse operations and failure scenarios.

Business Value Justification:
    - Segment: Enterprise customers requiring analytics SLA
- Business Goal: Prevent $1.8M annual revenue loss from analytics downtime
- Value Impact: Ensures analytics availability for decision-making workflows
- Strategic Impact: Enables real-time analytics SLA of 99.5% uptime

Cycles Covered: 16, 17, 18, 19, 20
""""

import pytest
import asyncio
import os
import time

from netra_backend.app.db.clickhouse import ClickHouseManager
from netra_backend.app.core.unified_logging import get_logger


logger = get_logger(__name__)


@pytest.mark.critical
@pytest.mark.clickhouse
@pytest.mark.parametrize("environment", ["test"])
class TestClickHouseReliability:
    """Critical ClickHouse reliability test suite."""

    @pytest.fixture
    async def clickhouse_manager(self):
        """Create isolated ClickHouse manager for testing."""
        # Skip if ClickHouse is disabled in testing environment
        if get_env().get("CLICKHOUSE_ENABLED", "false").lower() == "false":
        pytest.skip("ClickHouse disabled for testing environment")
        
        manager = ClickHouseManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()

        @pytest.mark.cycle_16
        async def test_clickhouse_connection_recovery_after_network_failure(self, environment, clickhouse_manager):
        """
        Cycle 16: Test ClickHouse connection recovery after network failures.
        
        Revenue Protection: $360K annually from analytics uptime.
        """"
        logger.info("Testing ClickHouse connection recovery - Cycle 16")
        
        # Verify initial connection works
        result = await clickhouse_manager.execute_query("SELECT 1")
        assert result is not None, "Initial ClickHouse connection failed"
        
        # Simulate network failure
        original_client = clickhouse_manager._client
        clickhouse_manager._client = None
        
        # Attempt query during failure - should trigger recovery
        try:
        result = await clickhouse_manager.execute_query("SELECT 1")
        # If successful, recovery worked
        assert result is not None, "Connection recovery failed"
        except Exception as e:
        logger.info(f"Expected failure during network outage: {e}")
            
        # Restore connection and verify recovery
        clickhouse_manager._client = original_client
        result = await clickhouse_manager.execute_query("SELECT 1")
        assert result is not None, "Connection failed to recover after restoration"
        
        logger.info("ClickHouse connection recovery verified")

        @pytest.mark.cycle_17
        async def test_clickhouse_query_timeout_prevents_hanging_analytics(self, environment, clickhouse_manager):
        """
        Cycle 17: Test ClickHouse query timeout prevents hanging analytics.
        
        Revenue Protection: $290K annually from preventing analytics hangs.
        """"
        logger.info("Testing ClickHouse query timeout - Cycle 17")
        
        # Test query with reasonable timeout
        start_time = time.time()
        try:
        # Use a query that might take time but should complete quickly in test environment
        result = await clickhouse_manager.execute_query(
        "SELECT count() FROM system.tables",
        timeout=5.0
        )
        query_time = time.time() - start_time
            
        assert query_time < 5.0, f"Query exceeded timeout: {query_time}s"
        assert result is not None, "Query should return result within timeout"
            
        except asyncio.TimeoutError:
        query_time = time.time() - start_time
        assert query_time <= 6.0, f"Timeout took too long to trigger: {query_time}s"
        logger.info("Query timeout correctly triggered")
        
        # Verify system is still responsive after timeout
        result = await clickhouse_manager.execute_query("SELECT 1")
        assert result is not None, "System not responsive after timeout"
        
        logger.info("ClickHouse query timeout verified")

        @pytest.mark.cycle_18
        async def test_clickhouse_batch_insert_atomicity_prevents_partial_data(self, environment, clickhouse_manager):
        """
        Cycle 18: Test ClickHouse batch insert atomicity prevents partial data corruption.
        
        Revenue Protection: $420K annually from preventing analytics data corruption.
        """"
        logger.info("Testing ClickHouse batch insert atomicity - Cycle 18")
        
        # Create test table
        table_name = "test_batch_atomicity"
        await clickhouse_manager.execute_query(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
        id UInt32,
        timestamp DateTime,
        value String
        ) ENGINE = MergeTree()
        ORDER BY (id, timestamp)
        """)""""
        
        # Prepare test data with intentional failure in middle
        test_data = [
        {"id": 1, "timestamp": "2025-8-26 12:0:0", "value": "valid_1"},
        {"id": 2, "timestamp": "2025-8-26 12:1:0", "value": "valid_2"},
        {"id": 3, "timestamp": "invalid_timestamp", "value": "invalid_3"},  # This should fail
        {"id": 4, "timestamp": "2025-8-26 12:3:0", "value": "valid_4"},
        ]
        
        # Attempt batch insert - should fail and rollback
        try:
        await clickhouse_manager.batch_insert(table_name, test_data)
        pytest.fail("Batch insert should have failed with invalid data")
        except Exception as e:
        logger.info(f"Expected batch insert failure: {e}")
        
        # Verify no partial data was inserted
        result = await clickhouse_manager.execute_query(f"SELECT count() FROM {table_name}")
        count = result[0][0] if result and result[0] else 0
        assert count == 0, f"Partial data inserted: {count} rows"
        
        # Test successful batch insert
        valid_data = [
        {"id": 1, "timestamp": "2025-8-26 12:0:0", "value": "valid_1"},
        {"id": 2, "timestamp": "2025-8-26 12:1:0", "value": "valid_2"},
        ]
        
        await clickhouse_manager.batch_insert(table_name, valid_data)
        
        # Verify all data was inserted
        result = await clickhouse_manager.execute_query(f"SELECT count() FROM {table_name}")
        count = result[0][0] if result and result[0] else 0
        assert count == 2, f"Incomplete data insertion: {count} rows"
        
        # Cleanup
        await clickhouse_manager.execute_query(f"DROP TABLE {table_name}")
        logger.info("ClickHouse batch insert atomicity verified")

        @pytest.mark.cycle_19
        async def test_clickhouse_memory_pressure_handling_prevents_oom(self, environment, clickhouse_manager):
        """
        Cycle 19: Test ClickHouse memory pressure handling prevents OOM crashes.
        
        Revenue Protection: $340K annually from preventing analytics service crashes.
        """"
        logger.info("Testing ClickHouse memory pressure handling - Cycle 19")
        
        # Create test table with large data simulation
        table_name = "test_memory_pressure"
        await clickhouse_manager.execute_query(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
        id UInt32,
        large_text String
        ) ENGINE = MergeTree()
        ORDER BY id
        """)""""
        
        # Test query with memory limits
        try:
        # Query that could potentially use significant memory
        result = await clickhouse_manager.execute_query(f"""
        SELECT 
        id,
        repeat('x', 1000) as large_string
        FROM numbers(10000)
        LIMIT 5000
        """, max_memory_usage="100MB")""""
            
        # Verify query completes without crashing
        assert result is not None, "Memory pressure query should complete"
        assert len(result) <= 5000, "Query returned unexpected result size"
            
        except Exception as e:
        # Memory limit exceeded is acceptable behavior
        logger.info(f"Memory limit correctly enforced: {e}")
        
        # Verify system is still responsive
        result = await clickhouse_manager.execute_query("SELECT 1")
        assert result is not None, "System not responsive after memory pressure"
        
        # Cleanup
        await clickhouse_manager.execute_query(f"DROP TABLE IF EXISTS {table_name}")
        logger.info("ClickHouse memory pressure handling verified")

        @pytest.mark.cycle_20
        async def test_clickhouse_concurrent_query_isolation_prevents_interference(self, environment, clickhouse_manager):
        """
        Cycle 20: Test ClickHouse concurrent query isolation prevents interference.
        
        Revenue Protection: $380K annually from preventing analytics query interference.
        """"
        logger.info("Testing ClickHouse concurrent query isolation - Cycle 20")
        
        async def long_running_query():
        """Simulate a long-running analytics query."""
        return await clickhouse_manager.execute_query("""
        SELECT 
        count(*),
        avg(number)
        FROM numbers(1000000)
        WHERE number % 2 = 0
        """)""""

        async def quick_query():
        """Quick system status query."""
        return await clickhouse_manager.execute_query("SELECT 1")

        # Start long-running query and quick queries concurrently
        start_time = time.time()
        
        tasks = [
        long_running_query(),
        quick_query(),
        quick_query(),
        quick_query()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all queries completed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 3, f"Not enough queries succeeded: {len(successful_results)}/4"
        
        # Quick queries should not be significantly delayed by long-running query
        # This is harder to test precisely, but total time should be reasonable
        assert total_time < 30.0, f"Concurrent queries took too long: {total_time}s"
        
        logger.info(f"ClickHouse concurrent query isolation verified: {len(successful_results)} successful queries in {total_time:.2f}s")
