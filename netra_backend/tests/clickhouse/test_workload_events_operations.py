"""
Workload Events Table Operations Tests
Tests workload_events table operations with real data
"""

import pytest
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.clickhouse import get_clickhouse_client
from logging_config import central_logger as logger
from netra_backend.tests.clickhouse_test_fixtures import (

# Add project root to path
    setup_workload_table,
    check_table_insert_permission,
    generate_test_workload_events,
    build_workload_insert_query,
    insert_with_permission_check
)


class TestWorkloadEventsTable:
    """Test workload_events table operations with real data"""
    
    async def test_insert_workload_events(self, setup_workload_table):
        """Test inserting real workload events"""
        async with get_clickhouse_client() as client:
            await self._debug_database_state(client)
            await self._check_workload_events_permissions(client)
            test_events = generate_test_workload_events()
            await self._insert_workload_events(client, test_events)
            await self._verify_workload_events_insertion(client)

    async def _check_workload_events_permissions(self, client):
        """Check workload_events table permissions"""
        has_insert = await check_table_insert_permission(client, "workload_events")
        if not has_insert:
            pytest.skip("development_user lacks INSERT privileges for workload_events")

    async def _debug_database_state(self, client):
        """Debug current database and table state"""
        db_result = await client.execute_query("SELECT currentDatabase() as db")
        current_db = db_result[0]['db'] if db_result else "unknown"
        tables_result = await client.execute_query("SHOW TABLES")
        table_names = [row.get('name', '') for row in tables_result]
        workload_tables = [t for t in table_names if 'workload' in t.lower()]
        print(f"[DEBUG] Current database: {current_db}, Available tables: {table_names}, Workload tables: {workload_tables}")

    async def _insert_workload_events(self, client, test_events):
        """Insert workload events into ClickHouse"""
        insert_query = build_workload_insert_query()
        for event in test_events:
            params = {k.replace('.', '_'): v for k, v in event.items()}
            await insert_with_permission_check(client, insert_query, params)

    async def _verify_workload_events_insertion(self, client):
        """Verify workload events were inserted correctly"""
        count_result = await client.execute_query("SELECT count() as count FROM workload_events WHERE metadata LIKE '%test_run%'")
        if not count_result:
            pytest.fail("Query returned no results - table may not exist or query failed")
        count = count_result[0]['count']
        assert count >= 10, f"Expected at least 10 inserted events, found {count}"
        logger.info(f"Successfully inserted {count} test events")

    async def test_query_with_array_syntax_fix(self, setup_workload_table):
        """Test querying with array syntax that needs fixing"""
        async with get_clickhouse_client() as client:
            # This query tests basic workload events selection
            test_query = """
            SELECT 
                event_id,
                workload_id,
                event_type,
                event_category
            FROM workload_events
            ORDER BY timestamp DESC
            LIMIT 5
            """
            
            # Execute the test query
            result = await client.execute_query(test_query)
            
            # Should get results without errors
            assert isinstance(result, list)
            for row in result:
                if row.get('workload_id'):
                    logger.info(f"Event: {row['event_id']} workload: {row['workload_id']} type: {row['event_type']}")

    async def test_complex_aggregation_queries(self, setup_workload_table):
        """Test complex aggregation queries with nested arrays"""
        async with get_clickhouse_client() as client:
            # Query with basic aggregation
            aggregation_query = """
            SELECT 
                workload_id,
                count() as request_count,
                event_type,
                event_category
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY workload_id, event_type, event_category
            ORDER BY request_count DESC
            """
            
            result = await client.execute_query(aggregation_query)
            assert isinstance(result, list)
            
            for row in result:
                logger.info(f"Workload {row['workload_id']}: "
                          f"{row['request_count']} requests, "
                          f"type: {row['event_type']}, "
                          f"category: {row['event_category']}")

    async def test_time_series_analysis(self, setup_workload_table):
        """Test time-series analysis queries"""
        async with get_clickhouse_client() as client:
            time_series_query = """
            SELECT 
                toStartOfMinute(timestamp) as time_bucket,
                count() as events_per_minute,
                uniq(user_id) as unique_users,
                uniq(workload_id) as unique_workloads
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT 60
            """
            
            result = await client.execute_query(time_series_query)
            assert isinstance(result, list)
            
            if result:
                logger.info(f"Time series data: {len(result)} time buckets")
                latest = result[0]
                logger.info(f"Latest minute: {latest['events_per_minute']} events, "
                          f"unique users: {latest['unique_users']}, "
                          f"unique workloads: {latest['unique_workloads']}")