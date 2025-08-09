"""Test ClickHouse service for time-series data and analytics."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.services.clickhouse_service import (
    ClickHouseService,
    ClickHouseQueryBuilder,
    TimeSeriesData,
    AggregationFunction
)


@pytest.fixture
async def clickhouse_service():
    """Create a test ClickHouse service instance."""
    service = ClickHouseService(
        host="localhost",
        port=9000,
        database="test_analytics"
    )
    await service.initialize()
    yield service
    await service.close()


@pytest.mark.asyncio
class TestClickHouseConnection:
    """Test ClickHouse connection management."""

    async def test_service_initialization(self, clickhouse_service):
        """Test ClickHouse service initialization."""
        assert clickhouse_service.client is not None
        assert clickhouse_service.database == "test_analytics"
        assert await clickhouse_service.is_healthy()

    async def test_connection_health_check(self, clickhouse_service):
        """Test connection health checking."""
        # Healthy connection
        assert await clickhouse_service.is_healthy()
        
        # Simulate unhealthy connection
        with patch.object(clickhouse_service.client, 'execute', side_effect=Exception("Connection failed")):
            assert not await clickhouse_service.is_healthy()

    async def test_connection_retry_logic(self, clickhouse_service):
        """Test connection retry on failure."""
        attempt_count = 0
        
        async def mock_execute(*args):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Connection failed")
            return [(1,)]
        
        with patch.object(clickhouse_service.client, 'execute', side_effect=mock_execute):
            result = await clickhouse_service.execute_with_retry("SELECT 1")
            assert result == [(1,)]
            assert attempt_count == 3

    async def test_query_timeout(self, clickhouse_service):
        """Test query timeout handling."""
        with patch.object(clickhouse_service.client, 'execute', 
                         side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await clickhouse_service.execute_query(
                    "SELECT sleep(10)",
                    timeout=1
                )


@pytest.mark.asyncio
class TestTimeSeriesOperations:
    """Test time-series data operations."""

    async def test_insert_time_series_data(self, clickhouse_service):
        """Test inserting time-series data."""
        events = [
            {
                "timestamp": datetime.now(),
                "event_type": "api_call",
                "user_id": "user1",
                "duration_ms": 150,
                "status": "success"
            },
            {
                "timestamp": datetime.now(),
                "event_type": "api_call",
                "user_id": "user2",
                "duration_ms": 300,
                "status": "error"
            }
        ]
        
        result = await clickhouse_service.insert_events("workload_events", events)
        assert result["inserted_count"] == 2
        assert result["success"] is True

    async def test_batch_insert_performance(self, clickhouse_service):
        """Test batch insert performance and optimization."""
        # Generate large batch of events
        events = []
        base_time = datetime.now()
        
        for i in range(10000):
            events.append({
                "timestamp": base_time + timedelta(seconds=i),
                "event_type": f"event_{i % 10}",
                "value": i,
                "metadata": {"batch": i // 100}
            })
        
        # Insert in batches
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            result = await clickhouse_service.insert_batch(
                "performance_events",
                batch,
                batch_size=batch_size
            )
            total_inserted += result["inserted_count"]
        
        assert total_inserted == 10000

    async def test_time_range_queries(self, clickhouse_service):
        """Test querying data within time ranges."""
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        query = """
        SELECT 
            toStartOfHour(timestamp) as hour,
            count() as event_count,
            avg(duration_ms) as avg_duration
        FROM workload_events
        WHERE timestamp >= %(start)s AND timestamp <= %(end)s
        GROUP BY hour
        ORDER BY hour
        """
        
        result = await clickhouse_service.execute_query(
            query,
            params={"start": start_time, "end": end_time}
        )
        
        assert isinstance(result, list)
        if result:
            assert "hour" in result[0]
            assert "event_count" in result[0]
            assert "avg_duration" in result[0]

    async def test_aggregation_functions(self, clickhouse_service):
        """Test various aggregation functions."""
        aggregations = {
            "total_events": "count()",
            "avg_duration": "avg(duration_ms)",
            "max_duration": "max(duration_ms)",
            "p95_duration": "quantile(0.95)(duration_ms)",
            "unique_users": "uniqExact(user_id)"
        }
        
        query = clickhouse_service.build_aggregation_query(
            table="workload_events",
            aggregations=aggregations,
            group_by=["event_type"],
            where="timestamp >= now() - INTERVAL 1 DAY"
        )
        
        result = await clickhouse_service.execute_query(query)
        
        if result:
            for row in result:
                assert "event_type" in row
                assert all(agg in row for agg in aggregations.keys())

    async def test_window_functions(self, clickhouse_service):
        """Test window functions for analytics."""
        query = """
        SELECT 
            timestamp,
            value,
            avg(value) OVER (
                ORDER BY timestamp 
                ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
            ) as moving_avg,
            row_number() OVER (
                PARTITION BY event_type 
                ORDER BY value DESC
            ) as rank
        FROM performance_events
        WHERE timestamp >= now() - INTERVAL 1 HOUR
        """
        
        result = await clickhouse_service.execute_query(query)
        
        if result:
            assert "moving_avg" in result[0]
            assert "rank" in result[0]


@pytest.mark.asyncio
class TestClickHouseQueryBuilder:
    """Test ClickHouse query builder functionality."""

    async def test_select_query_builder(self, clickhouse_service):
        """Test building SELECT queries."""
        builder = ClickHouseQueryBuilder()
        
        query = (builder
                .select(["user_id", "count() as event_count"])
                .from_table("workload_events")
                .where("timestamp >= now() - INTERVAL 1 DAY")
                .where("status = 'success'")
                .group_by(["user_id"])
                .having("event_count > 100")
                .order_by(["event_count DESC"])
                .limit(10)
                .build())
        
        expected = """
        SELECT user_id, count() as event_count
        FROM workload_events
        WHERE timestamp >= now() - INTERVAL 1 DAY AND status = 'success'
        GROUP BY user_id
        HAVING event_count > 100
        ORDER BY event_count DESC
        LIMIT 10
        """
        
        assert query.strip() == expected.strip()

    async def test_join_query_builder(self, clickhouse_service):
        """Test building JOIN queries."""
        builder = ClickHouseQueryBuilder()
        
        query = (builder
                .select(["e.*, u.name"])
                .from_table("events e")
                .join("users u", "e.user_id = u.id", join_type="LEFT")
                .where("e.timestamp >= today()")
                .build())
        
        assert "LEFT JOIN users u ON e.user_id = u.id" in query

    async def test_subquery_builder(self, clickhouse_service):
        """Test building queries with subqueries."""
        subquery = (ClickHouseQueryBuilder()
                   .select(["user_id", "max(timestamp) as last_seen"])
                   .from_table("events")
                   .group_by(["user_id"])
                   .build())
        
        main_query = (ClickHouseQueryBuilder()
                     .select(["*"])
                     .from_table(f"({subquery}) as active_users")
                     .where("last_seen >= now() - INTERVAL 1 HOUR")
                     .build())
        
        assert "active_users" in main_query
        assert "last_seen >= now() - INTERVAL 1 HOUR" in main_query


@pytest.mark.asyncio
class TestDataRetentionAndCompression:
    """Test data retention and compression strategies."""

    async def test_partition_management(self, clickhouse_service):
        """Test partition management for data retention."""
        # Create table with partitioning
        create_query = """
        CREATE TABLE IF NOT EXISTS test_partitioned (
            timestamp DateTime,
            data String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY timestamp
        TTL timestamp + INTERVAL 90 DAY
        """
        
        await clickhouse_service.execute_query(create_query)
        
        # Get partition info
        partitions = await clickhouse_service.get_table_partitions("test_partitioned")
        
        assert isinstance(partitions, list)
        for partition in partitions:
            assert "partition" in partition
            assert "rows" in partition
            assert "bytes_on_disk" in partition

    async def test_data_compression(self, clickhouse_service):
        """Test data compression effectiveness."""
        # Insert compressible data
        data = []
        for i in range(1000):
            data.append({
                "timestamp": datetime.now(),
                "repeated_text": "This is a repeated text pattern" * 10,
                "unique_id": i
            })
        
        table_name = "compression_test"
        await clickhouse_service.insert_batch(table_name, data)
        
        # Check compression ratio
        stats = await clickhouse_service.get_table_stats(table_name)
        
        assert stats["compression_ratio"] > 1.0
        assert stats["bytes_on_disk"] < stats["uncompressed_bytes"]

    async def test_data_archival(self, clickhouse_service):
        """Test data archival to cold storage."""
        # Move old partitions to cold storage
        result = await clickhouse_service.archive_old_partitions(
            table="workload_events",
            older_than_days=30,
            target_storage="cold"
        )
        
        assert "archived_partitions" in result
        assert "total_bytes_moved" in result


@pytest.mark.asyncio
class TestPerformanceOptimization:
    """Test query performance optimization."""

    async def test_query_profiling(self, clickhouse_service):
        """Test query profiling and performance metrics."""
        query = """
        SELECT 
            event_type,
            count() as cnt,
            avg(duration_ms) as avg_dur
        FROM workload_events
        GROUP BY event_type
        """
        
        profile = await clickhouse_service.profile_query(query)
        
        assert "execution_time_ms" in profile
        assert "rows_read" in profile
        assert "bytes_read" in profile
        assert "memory_usage" in profile

    async def test_index_optimization(self, clickhouse_service):
        """Test index usage and optimization."""
        # Create table with secondary indexes
        create_query = """
        CREATE TABLE IF NOT EXISTS indexed_events (
            timestamp DateTime,
            user_id String,
            event_type String,
            INDEX idx_user (user_id) TYPE bloom_filter GRANULARITY 3,
            INDEX idx_type (event_type) TYPE set(100) GRANULARITY 2
        ) ENGINE = MergeTree()
        ORDER BY timestamp
        """
        
        await clickhouse_service.execute_query(create_query)
        
        # Test query using indexes
        query = "SELECT * FROM indexed_events WHERE user_id = 'user123'"
        
        explain = await clickhouse_service.explain_query(query)
        assert "idx_user" in explain["indexes_used"]

    async def test_materialized_views(self, clickhouse_service):
        """Test materialized views for pre-aggregation."""
        # Create materialized view
        create_mv = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_stats
        ENGINE = SummingMergeTree()
        ORDER BY (hour, event_type)
        AS SELECT
            toStartOfHour(timestamp) as hour,
            event_type,
            count() as event_count,
            sum(duration_ms) as total_duration
        FROM workload_events
        GROUP BY hour, event_type
        """
        
        await clickhouse_service.execute_query(create_mv)
        
        # Query from materialized view (should be faster)
        query = "SELECT * FROM hourly_stats WHERE hour >= today()"
        
        result = await clickhouse_service.execute_query(query)
        profile = await clickhouse_service.profile_query(query)
        
        # Materialized view queries should be faster
        assert profile["execution_time_ms"] < 100

    async def test_query_cache(self, clickhouse_service):
        """Test query result caching."""
        query = "SELECT count(*) FROM workload_events"
        
        # First execution
        result1, time1 = await clickhouse_service.execute_with_timing(query)
        
        # Second execution (should use cache)
        result2, time2 = await clickhouse_service.execute_with_timing(query)
        
        assert result1 == result2
        assert time2 < time1  # Cached query should be faster

    async def test_distributed_query_execution(self, clickhouse_service):
        """Test distributed query execution across shards."""
        # Create distributed table
        create_dist = """
        CREATE TABLE IF NOT EXISTS events_distributed AS events
        ENGINE = Distributed(cluster_name, database, events, rand())
        """
        
        await clickhouse_service.execute_query(create_dist)
        
        # Execute distributed query
        query = """
        SELECT 
            event_type,
            count() as cnt
        FROM events_distributed
        GROUP BY event_type
        """
        
        result = await clickhouse_service.execute_distributed_query(query)
        
        assert isinstance(result, list)
        assert all("event_type" in row for row in result)