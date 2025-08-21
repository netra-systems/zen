"""
ClickHouse Workload Events Tests
Tests for workload_events table operations and complex queries
"""

import pytest
import asyncio
import uuid
import json
import random
from datetime import datetime, timedelta, UTC
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import (
    initialize_clickhouse_tables,
    verify_workload_events_table,
    create_workload_events_table_if_missing
)
from logging_config import central_logger as logger
from netra_backend.tests.test_clickhouse_permissions import _check_table_insert_permission


async def _ensure_workload_table():
    """Create workload table if missing and verify access"""
    success = await create_workload_events_table_if_missing()
    if not success:
        pytest.skip("Cannot create workload_events table")
    exists = await verify_workload_events_table()
    if not exists:
        pytest.skip("workload_events table not accessible")


class TestWorkloadEventsTable:
    """Test workload_events table operations with real data"""
    
    @pytest.fixture
    def setup_workload_table(self, event_loop):
        """Ensure workload_events table exists"""
        async def _setup_table():
            # Initialize ClickHouse tables including workload_events
            await initialize_clickhouse_tables()
            
            # Verify the table exists
            exists = await verify_workload_events_table()
            if not exists:
                pytest.skip("workload_events table could not be created or verified")
        
        event_loop.run_until_complete(_setup_table())
        yield
        # Cleanup test data (optional) - kept for analysis

    async def test_insert_workload_events(self, setup_workload_table):
        """Test inserting real workload events"""
        async with get_clickhouse_client() as client:
            await self._debug_database_state(client)
            await self._check_workload_events_permissions(client)
            test_events = self._generate_test_workload_events()
            await self._insert_workload_events(client, test_events)
            await self._verify_workload_events_insertion(client)

    async def _check_workload_events_permissions(self, client):
        """Check workload_events table permissions"""
        has_insert = await _check_table_insert_permission(client, "workload_events")
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

    def _generate_test_workload_events(self):
        """Generate test workload events for insertion"""
        test_events = []
        base_time = datetime.now(UTC)
        for i in range(10):
            event = self._create_single_test_event(i, base_time)
            test_events.append(event)
        return test_events

    def _create_single_test_event(self, index, base_time):
        """Create a single test workload event matching actual schema"""
        return {
            'user_id': index % 1000,  # UInt32 as per schema
            'workload_id': f'workload_{uuid.uuid4()}',
            'event_type': random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),
            'event_category': random.choice(['completed', 'in_progress', 'failed']),
            'metrics.name': ['latency_ms', 'tokens_used', 'cost_cents'],
            'metrics.value': [random.uniform(50, 500), random.randint(100, 1000), random.uniform(0.01, 1.0)],
            'metrics.unit': ['ms', 'tokens', 'cents'],
            'dimensions': {'test_id': str(index), 'test_run': 'true'},
            'metadata': json.dumps({'test_id': index, 'test_run': True})
        }

    async def _insert_workload_events(self, client, test_events):
        """Insert workload events into ClickHouse"""
        insert_query = self._build_insert_query()
        for event in test_events:
            # Convert keys to match parameter names in query
            params = {}
            for k, v in event.items():
                # Convert dots to underscores for parameter names
                param_key = k.replace('.', '_')
                params[param_key] = v
            await self._execute_insert_with_error_handling(client, insert_query, params)

    def _build_insert_query(self):
        """Build workload events insert query matching actual schema"""
        return """INSERT INTO workload_events (user_id, workload_id, 
        event_type, event_category, metrics.name, metrics.value, 
        metrics.unit, dimensions, metadata) VALUES (%(user_id)s, 
        %(workload_id)s, %(event_type)s, %(event_category)s, 
        %(metrics_name)s, %(metrics_value)s, %(metrics_unit)s, 
        %(dimensions)s, %(metadata)s)"""

    async def _execute_insert_with_error_handling(self, client, query, params):
        """Execute insert with permission error handling"""
        try:
            await client.execute_query(query, params)
        except Exception as e:
            if "Not enough privileges" in str(e):
                pytest.skip(f"INSERT permission denied: {e}")
            raise

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
            # This query has incorrect syntax that should be fixed
            incorrect_query = self._build_array_syntax_query()
            
            # The interceptor should fix this automatically
            result = await client.execute_query(incorrect_query)
            await self._process_array_query_results(result)

    def _build_array_syntax_query(self):
        """Build array syntax query for testing"""
        return """
        SELECT 
            event_id,
            metrics.name[1] as first_metric_name,
            metrics.value[1] as first_metric_value,
            metrics.unit[1] as first_metric_unit
        FROM workload_events
        WHERE arrayLength(metrics.name) > 0
        ORDER BY timestamp DESC
        LIMIT 5
        """

    async def _process_array_query_results(self, result):
        """Process and log array query results"""
        # Should get results without errors
        assert isinstance(result, list)
        for row in result:
            if row.get('first_metric_name'):
                logger.info(f"Metric: {row['first_metric_name']} = {row['first_metric_value']} {row['first_metric_unit']}")

    async def test_complex_aggregation_queries(self, setup_workload_table):
        """Test complex aggregation queries with nested arrays"""
        async with get_clickhouse_client() as client:
            # Query with proper array functions
            aggregation_query = self._build_aggregation_query()
            result = await client.execute_query(aggregation_query)
            await self._process_aggregation_results(result)

    def _build_aggregation_query(self):
        """Build complex aggregation query"""
        return """
        WITH metric_analysis AS (
            SELECT 
                event_type,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as latency_idx,
                arrayFirstIndex(x -> x = 'tokens_used', metrics.name) as tokens_idx,
                arrayFirstIndex(x -> x = 'cost_cents', metrics.name) as cost_idx,
                if(latency_idx > 0, arrayElement(metrics.value, latency_idx), 0) as latency,
                if(tokens_idx > 0, arrayElement(metrics.value, tokens_idx), 0) as tokens,
                if(cost_idx > 0, arrayElement(metrics.value, cost_idx), 0) as cost
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
        )
        SELECT 
            event_type,
            count() as request_count,
            avg(latency) as avg_latency_ms,
            sum(tokens) as total_tokens,
            sum(cost) as total_cost_cents
        FROM metric_analysis
        GROUP BY event_type
        ORDER BY request_count DESC
        """

    async def _process_aggregation_results(self, result):
        """Process and log aggregation query results"""
        assert isinstance(result, list)
        
        for row in result:
            logger.info(f"Event type {row['event_type']}: "
                      f"{row['request_count']} requests, "
                      f"avg latency {row['avg_latency_ms']:.2f}ms, "
                      f"total cost ${row['total_cost_cents']/100:.2f}")

    async def test_time_series_analysis(self, setup_workload_table):
        """Test time-series analysis queries"""
        async with get_clickhouse_client() as client:
            time_series_query = self._build_time_series_query()
            result = await client.execute_query(time_series_query)
            await self._process_time_series_results(result)

    def _build_time_series_query(self):
        """Build time series analysis query"""
        return """
        WITH latency_metrics AS (
            SELECT 
                timestamp,
                user_id,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as latency_idx,
                if(latency_idx > 0, arrayElement(metrics.value, latency_idx), 0) as duration_ms
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
        )
        SELECT 
            toStartOfMinute(timestamp) as time_bucket,
            count() as events_per_minute,
            avg(duration_ms) as avg_duration,
            quantile(0.95)(duration_ms) as p95_duration,
            uniq(user_id) as unique_users
        FROM latency_metrics
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT 60
        """

    async def _process_time_series_results(self, result):
        """Process and log time series results"""
        assert isinstance(result, list)
        
        if result:
            logger.info(f"Time series data: {len(result)} time buckets")
            latest = result[0]
            logger.info(f"Latest minute: {latest['events_per_minute']} events, "
                      f"avg duration {latest['avg_duration']:.2f}ms, "
                      f"P95 {latest['p95_duration']:.2f}ms")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])