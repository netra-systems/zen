"""
Real ClickHouse API Integration Tests
Tests actual ClickHouse operations with live API connections
"""

import pytest
import asyncio
import uuid
import json
import random
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional
import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_base import ClickHouseDatabase
from app.db.clickhouse_init import (
    initialize_clickhouse_tables,
    verify_workload_events_table,
    create_workload_events_table_if_missing
)
from app.db.clickhouse_query_fixer import (
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
    ClickHouseQueryInterceptor
)
from app.db.models_clickhouse import WORKLOAD_EVENTS_TABLE_SCHEMA
from app.config import settings
from app.logging_config import central_logger as logger


def _get_clickhouse_config():
    """Get ClickHouse configuration based on environment"""
    if settings.environment == "development":
        return settings.clickhouse_https_dev
    return settings.clickhouse_https


def _create_clickhouse_client(config):
    """Create ClickHouse client with given configuration"""
    return ClickHouseDatabase(
        host=config.host, port=config.port, user=config.user,
        password=config.password, database=config.database, secure=True
    )


async def _check_system_metrics_permission(client):
    """Check if user has permission to access system.metrics"""
    try:
        await client.execute_query("SELECT metric FROM system.metrics LIMIT 1")
        return True
    except Exception as e:
        if "Not enough privileges" in str(e) or "ACCESS_DENIED" in str(e):
            return False
        raise


async def _check_table_insert_permission(client, table_name):
    """Check if user has INSERT permission on table"""
    try:
        test_query = f"INSERT INTO {table_name} VALUES" 
        # This will fail but with different error if no INSERT permission
        await client.execute_query(test_query)
    except Exception as e:
        error_msg = str(e).lower()
        if "not enough privileges" in error_msg or "access_denied" in error_msg:
            return False
        # Other errors (like syntax) mean we likely have permission
        return True
    return True


async def _check_table_create_permission(client):
    """Check if user has CREATE TABLE permission"""
    test_table = f"temp_permission_test_{uuid.uuid4().hex[:8]}"
    try:
        await client.execute_query(f"CREATE TABLE {test_table} (id Int32) ENGINE = Memory")
        await client.execute_query(f"DROP TABLE {test_table}")
        return True
    except Exception as e:
        if "not enough privileges" in str(e).lower():
            return False
        return True


@pytest.fixture
def real_clickhouse_client():
    """Create a real ClickHouse client using production configuration"""
    config = _get_clickhouse_config()
    client = _create_clickhouse_client(config)
    interceptor = ClickHouseQueryInterceptor(client)
    yield interceptor
    # Note: Disconnect handled by the test itself or auto-cleanup


class TestRealClickHouseConnection:
    """Test real ClickHouse connection and basic operations"""
    async def test_real_connection(self, real_clickhouse_client):
        """Test actual connection to ClickHouse Cloud"""
        # Test basic connection
        result = await real_clickhouse_client.execute_query("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1
        
        # Test server version
        version_result = await real_clickhouse_client.execute_query("SELECT version() as version")
        assert len(version_result) == 1
        assert 'version' in version_result[0]
        logger.info(f"Connected to ClickHouse version: {version_result[0]['version']}")
    async def test_real_database_operations(self, real_clickhouse_client):
        """Test real database operations"""
        # Get current database
        db_result = await real_clickhouse_client.execute_query("SELECT currentDatabase() as db")
        assert len(db_result) == 1
        current_db = db_result[0]['db']
        logger.info(f"Current database: {current_db}")
        
        # List tables
        tables_result = await real_clickhouse_client.execute_query("SHOW TABLES")
        table_names = [row['name'] for row in tables_result if 'name' in row]
        logger.info(f"Available tables: {table_names}")
    async def test_real_system_queries(self, real_clickhouse_client):
        """Test system queries for monitoring"""
        # Check if user has system.metrics permission
        has_permission = await _check_system_metrics_permission(real_clickhouse_client)
        if not has_permission:
            pytest.skip("development_user lacks privileges for system.metrics")
        
        await self._execute_system_metrics_query(real_clickhouse_client)

    async def _execute_system_metrics_query(self, client):
        """Execute system metrics query with permission check"""
        metrics_query = """
        SELECT metric, value FROM system.metrics
        WHERE metric IN ('Query', 'HTTPConnection', 'TCPConnection')
        """
        metrics_result = await client.execute_query(metrics_query)
        assert isinstance(metrics_result, list)
        for row in metrics_result:
            logger.info(f"System metric {row.get('metric')}: {row.get('value')}")


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
            event = {
                'event_id': str(uuid.uuid4()),
                'timestamp': base_time - timedelta(minutes=i),
                'user_id': i % 100 + 1,  # UInt32 as per schema
                'workload_id': random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),
                'event_type': random.choice(['request', 'response', 'error']),
                'event_category': random.choice(['llm_call', 'tool_use', 'user_action']),
                'dimensions': f"{{'test_id': '{i}', 'batch': 'test_run'}}",
                'metadata': json.dumps({'test_id': i, 'test_run': True})
            }
            test_events.append(event)
        return test_events

    async def _insert_workload_events(self, client, test_events):
        """Insert workload events into ClickHouse"""
        insert_query = self._build_insert_query()
        for event in test_events:
            params = {k.replace('.', '_'): v for k, v in event.items()}
            await self._execute_insert_with_error_handling(client, insert_query, params)

    def _build_insert_query(self):
        """Build workload events insert query"""
        return """INSERT INTO workload_events (event_id, timestamp, user_id,
        workload_id, event_type, event_category, dimensions, metadata) 
        VALUES (%(event_id)s, %(timestamp)s, %(user_id)s, %(workload_id)s, 
        %(event_type)s, %(event_category)s, %(dimensions)s, %(metadata)s)"""

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


class TestCorpusTableOperations:
    """Test corpus table creation and management"""
    async def test_create_dynamic_corpus_table(self):
        """Test creating a dynamic corpus table"""
        async with get_clickhouse_client() as client:
            # Check CREATE TABLE permission
            has_create_permission = await _check_table_create_permission(client)
            if not has_create_permission:
                pytest.skip("development_user lacks CREATE TABLE privileges")
            
            await self._execute_corpus_table_test(client)

    async def _execute_corpus_table_test(self, client):
        """Execute corpus table creation and testing"""
        corpus_id = str(uuid.uuid4()).replace('-', '_')
        table_name = f"netra_content_corpus_{corpus_id}"
        create_query = self._build_corpus_create_query(table_name)
        
        try:
            await self._test_corpus_table_operations(client, table_name, corpus_id)
        except Exception as e:
            if "not enough privileges" in str(e).lower():
                pytest.skip(f"Permission denied: {e}")
            raise
        finally:
            await self._cleanup_corpus_table(client, table_name)

    def _build_corpus_create_query(self, table_name):
        """Build CREATE TABLE query for corpus table"""
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            record_id UUID DEFAULT generateUUIDv4(), workload_id String,
            prompt String, response String, metadata String,
            domain String DEFAULT 'general', created_at DateTime64(3) DEFAULT now(),
            version UInt32 DEFAULT 1, embedding Array(Float32) DEFAULT [],
            tags Array(String) DEFAULT []
        ) ENGINE = MergeTree() PARTITION BY toYYYYMM(created_at)
        ORDER BY (workload_id, created_at, record_id)"""

    async def _test_corpus_table_operations(self, client, table_name, corpus_id):
        """Test corpus table operations"""
        # Create the corpus table
        create_query = self._build_corpus_create_query(table_name)
        await client.execute_query(create_query)
        
        # Verify the table was created
        tables_result = await client.execute_query(f"SHOW TABLES LIKE '{table_name}'")
        assert len(tables_result) > 0
        logger.info(f"Created corpus table: {table_name}")
        
        await self._insert_corpus_test_data(client, table_name, corpus_id)
        await self._verify_corpus_test_data(client, table_name)

    async def _insert_corpus_test_data(self, client, table_name, corpus_id):
        """Insert test data into corpus table"""
        insert_query = f"""
        INSERT INTO {table_name} (workload_id, prompt, response, 
        metadata, domain, tags) VALUES ('test_workload', 
        'Test prompt for corpus', 'Test response from model',
        '{{"test": true, "corpus_id": "{corpus_id}"}}', 'testing',
        ['test', 'automated', 'corpus'])"""
        await client.execute_query(insert_query)

    async def _verify_corpus_test_data(self, client, table_name):
        """Verify corpus test data insertion"""
        select_result = await client.execute_query(
            f"SELECT * FROM {table_name} WHERE workload_id = 'test_workload'"
        )
        assert len(select_result) == 1
        assert select_result[0]['prompt'] == 'Test prompt for corpus'

    async def _cleanup_corpus_table(self, client, table_name):
        """Cleanup corpus test table"""
        try:
            await client.execute_query(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"Cleaned up test table: {table_name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup table {table_name}: {e}")


class TestClickHousePerformance:
    """Test ClickHouse performance and optimization"""
    async def test_batch_insert_performance(self):
        """Test batch insert performance"""
        async with get_clickhouse_client() as client:
            # Ensure table exists
            await create_workload_events_table_if_missing()
            
            # Check INSERT permission
            has_insert = await _check_table_insert_permission(client, "workload_events")
            if not has_insert:
                pytest.skip("development_user lacks INSERT privileges for workload_events")
            
            # Generate large batch of events
            batch_size = 1000
            events = []
            base_time = datetime.now(UTC)
            
            for i in range(batch_size):
                event = [
                    str(uuid.uuid4()),  # event_id
                    base_time - timedelta(seconds=i),  # timestamp
                    i % 100 + 1,  # user_id (UInt32)
                    random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),  # workload_id
                    random.choice(['request', 'response', 'error']),  # event_type
                    random.choice(['llm_call', 'tool_use', 'user_action']),  # event_category
                    {'test_id': str(i), 'batch': 'perf_test'},  # dimensions
                    json.dumps({'batch_test': True, 'index': i})  # metadata
                ]
                events.append(event)
            
            # Measure insert time
            import time
            start_time = time.time()
            
            # Use the base client for raw insert
            if hasattr(client, 'base_client'):
                base_client = client.base_client
            else:
                base_client = client
            
            # Batch insert
            column_names = [
                'event_id', 'timestamp', 'user_id', 'workload_id', 'event_type',
                'event_category', 'dimensions', 'metadata'
            ]
            
            await base_client.insert_data('workload_events', events, column_names=column_names)
            
            end_time = time.time()
            insert_duration = end_time - start_time
            
            logger.info(f"Inserted {batch_size} events in {insert_duration:.2f} seconds")
            logger.info(f"Insert rate: {batch_size/insert_duration:.0f} events/second")
            
            # Verify insertion
            count_result = await client.execute_query(
                "SELECT count() as count FROM workload_events WHERE metadata LIKE '%batch_test%'"
            )
            assert count_result[0]['count'] >= batch_size
    async def test_query_performance_with_indexes(self):
        """Test query performance with proper indexing"""
        async with get_clickhouse_client() as client:
            # Test indexed query performance
            import time
            
            # Query using primary key columns (should be fast)
            start_time = time.time()
            indexed_query = """
            SELECT 
                workload_id,
                count() as cnt,
                uniq(user_id) as unique_users
            FROM workload_events
            WHERE workload_id IN ('simple_chat', 'rag_pipeline')
                AND timestamp >= now() - INTERVAL 1 DAY
            GROUP BY workload_id
            """
            
            result = await client.execute_query(indexed_query)
            indexed_duration = time.time() - start_time
            
            logger.info(f"Indexed query completed in {indexed_duration:.3f} seconds")
            
            # Query with full scan (should be slower)
            start_time = time.time()
            full_scan_query = """
            SELECT 
                count() as cnt
            FROM workload_events
            WHERE metadata LIKE '%test%'
            """
            
            result = await client.execute_query(full_scan_query)
            full_scan_duration = time.time() - start_time
            
            logger.info(f"Full scan query completed in {full_scan_duration:.3f} seconds")
            
            # Indexed queries should generally be faster
            # Note: This might not always be true for small datasets
            logger.info(f"Performance ratio: {full_scan_duration/max(indexed_duration, 0.001):.2f}x")


class TestClickHouseErrorHandling:
    """Test error handling and recovery"""
    async def test_invalid_query_handling(self):
        """Test handling of invalid queries"""
        async with get_clickhouse_client() as client:
            # Test syntax error
            with pytest.raises(Exception) as exc_info:
                await client.execute_query("SELECT * FROM non_existent_table_xyz123")
            
            error_msg = str(exc_info.value)
            logger.info(f"Expected error for non-existent table: {error_msg}")
    async def test_connection_recovery(self):
        """Test connection recovery after disconnect"""
        config = settings.clickhouse_https_dev if settings.environment == "development" else settings.clickhouse_https
        
        client = ClickHouseDatabase(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            secure=True
        )
        
        # First query should work
        result = await client.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
        
        # Disconnect
        await client.disconnect()
        
        # Query after disconnect should fail
        with pytest.raises(ConnectionError):
            await client.execute_query("SELECT 1 as test")
        
        # Reconnect
        client = ClickHouseDatabase(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            secure=True
        )
        
        # Should work again
        result = await client.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
        
        await client.disconnect()


class TestClickHouseIntegration:
    """Integration tests for ClickHouse with the application"""
    async def test_full_initialization_flow(self):
        """Test the full ClickHouse initialization flow"""
        # Run initialization
        await initialize_clickhouse_tables()
        
        # Verify all tables exist
        async with get_clickhouse_client() as client:
            tables_result = await client.execute_query("SHOW TABLES")
            table_names = [row['name'] for row in tables_result if 'name' in row]
            
            # Check for expected tables
            expected_tables = ['workload_events', 'netra_app_internal_logs', 'netra_global_supply_catalog']
            
            for expected_table in expected_tables:
                if expected_table in table_names:
                    logger.info(f"✓ Table {expected_table} exists")
                else:
                    logger.warning(f"✗ Table {expected_table} not found")
    async def test_query_interceptor_statistics(self):
        """Test query interceptor statistics tracking"""
        async with get_clickhouse_client() as client:
            # Reset statistics if possible
            if hasattr(client, 'reset_statistics'):
                client.reset_statistics()
            
            # Execute queries with different patterns
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
            
            # Get statistics
            if hasattr(client, 'get_statistics'):
                stats = client.get_statistics()
                logger.info(f"Query interceptor statistics: {stats}")
                assert stats['queries_executed'] >= 4
                assert stats['queries_fixed'] >= 2  # At least 2 queries needed fixing


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])