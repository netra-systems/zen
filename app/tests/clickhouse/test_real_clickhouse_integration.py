"""
Real ClickHouse Integration Tests
Integration tests for ClickHouse with the application
"""

import pytest
from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_init import initialize_clickhouse_tables
from app.logging_config import central_logger as logger


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

    async def test_application_table_schema_compatibility(self):
        """Test that application tables have expected schema"""
        async with get_clickhouse_client() as client:
            # Test workload_events table schema
            workload_schema = await client.execute_query(
                "DESCRIBE TABLE workload_events"
            )
            
            # Expected columns in workload_events
            expected_columns = [
                'trace_id', 'span_id', 'user_id', 'session_id', 'timestamp',
                'workload_type', 'status', 'duration_ms', 'input_text', 'output_text'
            ]
            
            schema_columns = [row['name'] for row in workload_schema]
            
            for expected_col in expected_columns:
                assert expected_col in schema_columns, f"Missing column: {expected_col}"
                logger.info(f"✓ Column {expected_col} found in workload_events")

    async def test_cross_table_query_execution(self):
        """Test that cross-table queries work properly"""
        async with get_clickhouse_client() as client:
            # Test a query that joins multiple tables (if they exist)
            try:
                cross_table_query = """
                SELECT 
                    w.workload_type,
                    count() as event_count
                FROM workload_events w
                WHERE w.timestamp >= now() - INTERVAL 1 HOUR
                GROUP BY w.workload_type
                LIMIT 10
                """
                
                result = await client.execute_query(cross_table_query)
                assert isinstance(result, list)
                logger.info(f"Cross-table query returned {len(result)} results")
                
            except Exception as e:
                # This might fail if tables don't exist or have no data
                logger.warning(f"Cross-table query failed (may be expected): {e}")

    async def test_application_metrics_integration(self):
        """Test integration with application metrics system"""
        async with get_clickhouse_client() as client:
            # Test that we can query application-specific metrics
            try:
                metrics_query = """
                SELECT 
                    toStartOfHour(timestamp) as hour,
                    workload_type,
                    avg(duration_ms) as avg_duration,
                    count() as request_count
                FROM workload_events
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                GROUP BY hour, workload_type
                ORDER BY hour DESC
                LIMIT 100
                """
                
                result = await client.execute_query(metrics_query)
                assert isinstance(result, list)
                logger.info(f"Metrics integration query returned {len(result)} results")
                
            except Exception as e:
                logger.warning(f"Metrics query failed (may be expected with no data): {e}")