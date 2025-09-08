"""
Test ClickHouse Performance - Integration Tests

Business Value Justification (BVJ):
- Segment: Mid and Enterprise
- Business Goal: Ensure sub-second analytics response times
- Value Impact: Fast analytics drives user engagement (+15% retention)  
- Strategic Impact: Enables real-time dashboards for premium users (+$8K MRR)

This test suite validates ClickHouse performance characteristics under realistic
workloads, ensuring analytics queries meet performance SLAs.
"""

import pytest
import asyncio
import time
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta

from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.configuration_validator import validate_test_config


class TestClickHousePerformanceIntegration(BaseIntegrationTest):
    """Test ClickHouse performance characteristics and optimizations."""
    
    def setup_method(self):
        """Setup test environment and performance test data."""
        validate_test_config("backend")
        self.perf_table = f"perf_test_{uuid.uuid4().hex[:8]}"
        self.performance_thresholds = {
            'simple_select': 0.1,      # 100ms for simple selects
            'aggregate_query': 0.5,    # 500ms for aggregations
            'complex_join': 1.0,       # 1s for complex operations
            'bulk_insert': 2.0         # 2s for bulk inserts
        }

    async def cleanup_perf_table(self):
        """Cleanup performance test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.perf_table}")
                await client.execute(f"DROP TABLE IF EXISTS {self.perf_table}_events")
                await client.execute(f"DROP TABLE IF EXISTS {self.perf_table}_users")
        except Exception as e:
            print(f"Warning: Failed to cleanup performance tables: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_simple_query_performance(self):
        """Test simple query performance meets SLA requirements.
        
        Critical for ensuring responsive user analytics dashboard.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create optimized table for simple queries
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.perf_table} (
                    id UInt64,
                    user_id String,
                    metric_value Float64,
                    category String,
                    timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, timestamp, id)
                """)
                
                # Insert test data for performance testing
                test_data_size = 1000  # 1K records for performance baseline
                for i in range(test_data_size):
                    await client.execute(f"""
                        INSERT INTO {self.perf_table} (id, user_id, metric_value, category)
                        VALUES (%(id)s, %(user_id)s, %(metric_value)s, %(category)s)
                    """, {
                        'id': i,
                        'user_id': f'perf_user_{i % 50}',  # 50 different users
                        'metric_value': (i % 100) * 1.5,
                        'category': f'category_{i % 10}'    # 10 categories
                    })
                
                # Wait for data availability
                await asyncio.sleep(0.2)
                
                # Test 1: Simple SELECT by user_id performance
                start_time = time.time()
                
                simple_result = await client.execute(f"""
                    SELECT id, user_id, metric_value, category
                    FROM {self.perf_table}
                    WHERE user_id = 'perf_user_1'
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                
                simple_query_time = time.time() - start_time
                
                # Validate performance
                assert simple_query_time < self.performance_thresholds['simple_select'], \
                    f"Simple query took {simple_query_time:.3f}s, exceeds {self.performance_thresholds['simple_select']}s threshold"
                
                assert len(simple_result) > 0, "Should return results for existing user"
                
                # Test 2: COUNT query performance  
                start_time = time.time()
                
                count_result = await client.execute(f"""
                    SELECT COUNT(*) as total_records
                    FROM {self.perf_table}
                """)
                
                count_query_time = time.time() - start_time
                
                assert count_query_time < self.performance_thresholds['simple_select'], \
                    f"Count query took {count_query_time:.3f}s, exceeds threshold"
                
                assert count_result[0]['total_records'] == test_data_size, \
                    f"Should count all {test_data_size} records"
                
                # Test 3: Range query performance
                start_time = time.time()
                
                range_result = await client.execute(f"""
                    SELECT user_id, COUNT(*) as record_count
                    FROM {self.perf_table}
                    WHERE metric_value BETWEEN 50.0 AND 150.0
                    GROUP BY user_id
                    ORDER BY record_count DESC
                    LIMIT 5
                """)
                
                range_query_time = time.time() - start_time
                
                assert range_query_time < self.performance_thresholds['simple_select'], \
                    f"Range query took {range_query_time:.3f}s, exceeds threshold"
                
                assert len(range_result) > 0, "Should return results for range query"
                
        finally:
            await self.cleanup_perf_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_aggregate_query_performance(self):
        """Test aggregate query performance for analytics dashboards.
        
        Critical for real-time analytics and dashboard responsiveness.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table optimized for aggregations
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.perf_table} (
                    user_id String,
                    event_type String,
                    value Float64,
                    date Date,
                    timestamp DateTime64(3)
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(date)
                ORDER BY (event_type, date, user_id)
                """)
                
                # Insert larger dataset for aggregation testing
                base_date = datetime(2024, 1, 1)
                records_per_day = 100
                days_of_data = 30  # 30 days of data
                
                for day in range(days_of_data):
                    current_date = base_date + timedelta(days=day)
                    for record in range(records_per_day):
                        await client.execute(f"""
                            INSERT INTO {self.perf_table} (user_id, event_type, value, date, timestamp)
                            VALUES (%(user_id)s, %(event_type)s, %(value)s, %(date)s, %(timestamp)s)
                        """, {
                            'user_id': f'agg_user_{record % 20}',  # 20 users
                            'event_type': f'event_{record % 5}',    # 5 event types
                            'value': record * 2.5 + day * 10,
                            'date': current_date.strftime('%Y-%m-%d'),
                            'timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S')
                        })
                
                # Wait for data to be available
                await asyncio.sleep(0.5)
                
                # Test 1: Daily aggregation performance
                start_time = time.time()
                
                daily_agg_result = await client.execute(f"""
                    SELECT 
                        date,
                        event_type,
                        COUNT(*) as event_count,
                        AVG(value) as avg_value,
                        SUM(value) as total_value
                    FROM {self.perf_table}
                    WHERE date >= '2024-01-01' AND date <= '2024-01-31'
                    GROUP BY date, event_type
                    ORDER BY date DESC, event_type
                    LIMIT 50
                """)
                
                daily_agg_time = time.time() - start_time
                
                assert daily_agg_time < self.performance_thresholds['aggregate_query'], \
                    f"Daily aggregation took {daily_agg_time:.3f}s, exceeds {self.performance_thresholds['aggregate_query']}s threshold"
                
                assert len(daily_agg_result) > 0, "Should return daily aggregation results"
                
                # Test 2: User-based aggregation performance
                start_time = time.time()
                
                user_agg_result = await client.execute(f"""
                    SELECT 
                        user_id,
                        COUNT(DISTINCT event_type) as unique_events,
                        COUNT(*) as total_events,
                        MAX(value) as max_value,
                        MIN(value) as min_value,
                        quantile(0.95)(value) as p95_value
                    FROM {self.perf_table}
                    GROUP BY user_id
                    HAVING total_events > 50
                    ORDER BY total_events DESC
                """)
                
                user_agg_time = time.time() - start_time
                
                assert user_agg_time < self.performance_thresholds['aggregate_query'], \
                    f"User aggregation took {user_agg_time:.3f}s, exceeds threshold"
                
                assert len(user_agg_result) > 0, "Should return user aggregation results"
                
                # Test 3: Time-series aggregation with window functions
                start_time = time.time()
                
                timeseries_result = await client.execute(f"""
                    SELECT 
                        date,
                        SUM(value) as daily_total,
                        AVG(value) as daily_avg,
                        AVG(SUM(value)) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7day_avg
                    FROM {self.perf_table}
                    WHERE date >= '2024-01-01'
                    GROUP BY date
                    ORDER BY date
                """)
                
                timeseries_time = time.time() - start_time
                
                assert timeseries_time < self.performance_thresholds['aggregate_query'], \
                    f"Time-series aggregation took {timeseries_time:.3f}s, exceeds threshold"
                
                assert len(timeseries_result) > 0, "Should return time-series results"
                
                # Validate rolling average calculation
                for i, row in enumerate(timeseries_result):
                    assert row['daily_total'] > 0, "Daily totals should be positive"
                    assert row['daily_avg'] > 0, "Daily averages should be positive"
                    if i >= 6:  # Rolling average should be available after 7 days
                        assert row['rolling_7day_avg'] > 0, "Rolling average should be positive"
                
        finally:
            await self.cleanup_perf_table()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self):
        """Test performance under concurrent query load.
        
        Ensures system can handle multiple simultaneous analytics requests.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table for concurrent testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.perf_table} (
                    query_id UInt64,
                    user_id String,
                    metric Float64,
                    timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, timestamp, query_id)
                """)
                
                # Insert data for concurrent testing
                concurrent_data_size = 500
                for i in range(concurrent_data_size):
                    await client.execute(f"""
                        INSERT INTO {self.perf_table} (query_id, user_id, metric)
                        VALUES (%(query_id)s, %(user_id)s, %(metric)s)
                    """, {
                        'query_id': i,
                        'user_id': f'concurrent_user_{i % 10}',
                        'metric': i * 1.1
                    })
                
                await asyncio.sleep(0.2)
                
                # Define concurrent query operations
                async def run_concurrent_query(query_type: str, iterations: int):
                    """Run multiple queries concurrently."""
                    query_times = []
                    async with get_clickhouse_client(bypass_manager=True) as concurrent_client:
                        for i in range(iterations):
                            start = time.time()
                            
                            if query_type == "simple":
                                await concurrent_client.execute(f"""
                                    SELECT COUNT(*) as count FROM {self.perf_table}
                                    WHERE user_id = 'concurrent_user_{i % 10}'
                                """)
                            elif query_type == "aggregate":
                                await concurrent_client.execute(f"""
                                    SELECT user_id, AVG(metric) as avg_metric
                                    FROM {self.perf_table}
                                    GROUP BY user_id
                                    ORDER BY avg_metric DESC
                                    LIMIT 5
                                """)
                            
                            query_times.append(time.time() - start)
                    
                    return query_times
                
                # Run concurrent operations
                start_time = time.time()
                
                concurrent_tasks = [
                    run_concurrent_query("simple", 10),     # 10 simple queries
                    run_concurrent_query("aggregate", 8),   # 8 aggregate queries
                    run_concurrent_query("simple", 12),     # 12 more simple queries
                    run_concurrent_query("aggregate", 6)    # 6 more aggregate queries
                ]
                
                results = await asyncio.gather(*concurrent_tasks)
                
                total_concurrent_time = time.time() - start_time
                
                # Analyze concurrent performance
                all_query_times = []
                for task_times in results:
                    all_query_times.extend(task_times)
                
                avg_query_time = sum(all_query_times) / len(all_query_times)
                max_query_time = max(all_query_times)
                total_queries = len(all_query_times)
                
                # Performance assertions for concurrent load
                assert avg_query_time < 0.3, f"Average concurrent query time {avg_query_time:.3f}s exceeds 0.3s"
                assert max_query_time < 1.0, f"Maximum concurrent query time {max_query_time:.3f}s exceeds 1.0s"
                assert total_concurrent_time < 5.0, f"Total concurrent execution {total_concurrent_time:.3f}s exceeds 5.0s"
                
                # Calculate throughput (queries per second)
                throughput = total_queries / total_concurrent_time
                assert throughput > 10, f"Concurrent throughput {throughput:.1f} QPS is below minimum 10 QPS"
                
        finally:
            await self.cleanup_perf_table()


class TestClickHouseCachePerformanceIntegration(BaseIntegrationTest):
    """Test ClickHouse caching performance and efficiency."""
    
    def setup_method(self):
        """Setup cache performance testing."""
        validate_test_config("backend")
        self.cache_table = f"cache_test_{uuid.uuid4().hex[:8]}"

    async def cleanup_cache_table(self):
        """Cleanup cache test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.cache_table}")
        except Exception as e:
            print(f"Warning: Failed to cleanup cache table: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_query_caching_performance_improvement(self):
        """Test query caching provides significant performance improvement.
        
        Critical for reducing database load and improving response times.
        """
        try:
            service = get_clickhouse_service()
            await service.initialize()
            
            # Clear cache to ensure clean test
            service.clear_cache()
            
            async with get_clickhouse_client(bypass_manager=True) as client:
                # Create table for cache testing
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.cache_table} (
                    id UInt64,
                    user_id String,
                    data String,
                    timestamp DateTime64(3) DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (user_id, timestamp, id)
                """)
                
                # Insert test data
                for i in range(200):
                    await client.execute(f"""
                        INSERT INTO {self.cache_table} (id, user_id, data)
                        VALUES (%(id)s, %(user_id)s, %(data)s)
                    """, {
                        'id': i,
                        'user_id': f'cache_user_{i % 5}',
                        'data': f'Cache test data {i}' * 10  # Larger data for meaningful cache benefit
                    })
                
                await asyncio.sleep(0.2)
                
                # Test query without cache (first execution)
                test_query = f"""
                    SELECT user_id, COUNT(*) as count, AVG(LENGTH(data)) as avg_length
                    FROM {self.cache_table}
                    WHERE user_id = %(user_id)s
                    GROUP BY user_id
                """
                test_params = {'user_id': 'cache_user_1'}
                user_id = "cache_test_user"
                
                # First execution (uncached)
                start_time = time.time()
                result1 = await service.execute(test_query, test_params, user_id=user_id)
                uncached_time = time.time() - start_time
                
                # Second execution (should be cached)
                start_time = time.time()
                result2 = await service.execute(test_query, test_params, user_id=user_id)
                cached_time = time.time() - start_time
                
                # Validate cache effectiveness
                assert result1 == result2, "Cached result should match original"
                assert len(result1) > 0, "Should return query results"
                
                # Cache should provide significant performance improvement
                cache_improvement_ratio = uncached_time / cached_time if cached_time > 0 else float('inf')
                assert cache_improvement_ratio > 2, f"Cache should improve performance by >2x, got {cache_improvement_ratio:.1f}x"
                assert cached_time < 0.05, f"Cached query should be <50ms, took {cached_time:.3f}s"
                
                # Verify cache stats
                cache_stats = service.get_cache_stats(user_id)
                assert cache_stats is not None, "Should have cache statistics"
                
        finally:
            await self.cleanup_cache_table()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])