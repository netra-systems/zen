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
        validate_test_config('backend')
        self.perf_table = f'perf_test_{uuid.uuid4().hex[:8]}'
        self.performance_thresholds = {'simple_select': 0.1, 'aggregate_query': 0.5, 'complex_join': 1.0, 'bulk_insert': 2.0}

    async def cleanup_perf_table(self):
        """Cleanup performance test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {self.perf_table}')
                await client.execute(f'DROP TABLE IF EXISTS {self.perf_table}_events')
                await client.execute(f'DROP TABLE IF EXISTS {self.perf_table}_users')
        except Exception as e:
            print(f'Warning: Failed to cleanup performance tables: {e}')

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_simple_query_performance(self):
        """Test simple query performance meets SLA requirements.
        
        Critical for ensuring responsive user analytics dashboard.
        """
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.perf_table} (\n                    id UInt64,\n                    user_id String,\n                    metric_value Float64,\n                    category String,\n                    timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, timestamp, id)\n                ')
                test_data_size = 1000
                for i in range(test_data_size):
                    await client.execute(f'\n                        INSERT INTO {self.perf_table} (id, user_id, metric_value, category)\n                        VALUES (%(id)s, %(user_id)s, %(metric_value)s, %(category)s)\n                    ', {'id': i, 'user_id': f'perf_user_{i % 50}', 'metric_value': i % 100 * 1.5, 'category': f'category_{i % 10}'})
                await asyncio.sleep(0.2)
                start_time = time.time()
                simple_result = await client.execute(f"\n                    SELECT id, user_id, metric_value, category\n                    FROM {self.perf_table}\n                    WHERE user_id = 'perf_user_1'\n                    ORDER BY timestamp DESC\n                    LIMIT 10\n                ")
                simple_query_time = time.time() - start_time
                assert simple_query_time < self.performance_thresholds['simple_select'], f"Simple query took {simple_query_time:.3f}s, exceeds {self.performance_thresholds['simple_select']}s threshold"
                assert len(simple_result) > 0, 'Should return results for existing user'
                start_time = time.time()
                count_result = await client.execute(f'\n                    SELECT COUNT(*) as total_records\n                    FROM {self.perf_table}\n                ')
                count_query_time = time.time() - start_time
                assert count_query_time < self.performance_thresholds['simple_select'], f'Count query took {count_query_time:.3f}s, exceeds threshold'
                assert count_result[0]['total_records'] == test_data_size, f'Should count all {test_data_size} records'
                start_time = time.time()
                range_result = await client.execute(f'\n                    SELECT user_id, COUNT(*) as record_count\n                    FROM {self.perf_table}\n                    WHERE metric_value BETWEEN 50.0 AND 150.0\n                    GROUP BY user_id\n                    ORDER BY record_count DESC\n                    LIMIT 5\n                ')
                range_query_time = time.time() - start_time
                assert range_query_time < self.performance_thresholds['simple_select'], f'Range query took {range_query_time:.3f}s, exceeds threshold'
                assert len(range_result) > 0, 'Should return results for range query'
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
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.perf_table} (\n                    user_id String,\n                    event_type String,\n                    value Float64,\n                    date Date,\n                    timestamp DateTime64(3)\n                ) ENGINE = MergeTree()\n                PARTITION BY toYYYYMM(date)\n                ORDER BY (event_type, date, user_id)\n                ')
                base_date = datetime(2024, 1, 1)
                records_per_day = 100
                days_of_data = 30
                for day in range(days_of_data):
                    current_date = base_date + timedelta(days=day)
                    for record in range(records_per_day):
                        await client.execute(f'\n                            INSERT INTO {self.perf_table} (user_id, event_type, value, date, timestamp)\n                            VALUES (%(user_id)s, %(event_type)s, %(value)s, %(date)s, %(timestamp)s)\n                        ', {'user_id': f'agg_user_{record % 20}', 'event_type': f'event_{record % 5}', 'value': record * 2.5 + day * 10, 'date': current_date.strftime('%Y-%m-%d'), 'timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S')})
                await asyncio.sleep(0.5)
                start_time = time.time()
                daily_agg_result = await client.execute(f"\n                    SELECT \n                        date,\n                        event_type,\n                        COUNT(*) as event_count,\n                        AVG(value) as avg_value,\n                        SUM(value) as total_value\n                    FROM {self.perf_table}\n                    WHERE date >= '2024-01-01' AND date <= '2024-01-31'\n                    GROUP BY date, event_type\n                    ORDER BY date DESC, event_type\n                    LIMIT 50\n                ")
                daily_agg_time = time.time() - start_time
                assert daily_agg_time < self.performance_thresholds['aggregate_query'], f"Daily aggregation took {daily_agg_time:.3f}s, exceeds {self.performance_thresholds['aggregate_query']}s threshold"
                assert len(daily_agg_result) > 0, 'Should return daily aggregation results'
                start_time = time.time()
                user_agg_result = await client.execute(f'\n                    SELECT \n                        user_id,\n                        COUNT(DISTINCT event_type) as unique_events,\n                        COUNT(*) as total_events,\n                        MAX(value) as max_value,\n                        MIN(value) as min_value,\n                        quantile(0.95)(value) as p95_value\n                    FROM {self.perf_table}\n                    GROUP BY user_id\n                    HAVING total_events > 50\n                    ORDER BY total_events DESC\n                ')
                user_agg_time = time.time() - start_time
                assert user_agg_time < self.performance_thresholds['aggregate_query'], f'User aggregation took {user_agg_time:.3f}s, exceeds threshold'
                assert len(user_agg_result) > 0, 'Should return user aggregation results'
                start_time = time.time()
                timeseries_result = await client.execute(f"\n                    SELECT \n                        date,\n                        SUM(value) as daily_total,\n                        AVG(value) as daily_avg,\n                        AVG(SUM(value)) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7day_avg\n                    FROM {self.perf_table}\n                    WHERE date >= '2024-01-01'\n                    GROUP BY date\n                    ORDER BY date\n                ")
                timeseries_time = time.time() - start_time
                assert timeseries_time < self.performance_thresholds['aggregate_query'], f'Time-series aggregation took {timeseries_time:.3f}s, exceeds threshold'
                assert len(timeseries_result) > 0, 'Should return time-series results'
                for i, row in enumerate(timeseries_result):
                    assert row['daily_total'] > 0, 'Daily totals should be positive'
                    assert row['daily_avg'] > 0, 'Daily averages should be positive'
                    if i >= 6:
                        assert row['rolling_7day_avg'] > 0, 'Rolling average should be positive'
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
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.perf_table} (\n                    query_id UInt64,\n                    user_id String,\n                    metric Float64,\n                    timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, timestamp, query_id)\n                ')
                concurrent_data_size = 500
                for i in range(concurrent_data_size):
                    await client.execute(f'\n                        INSERT INTO {self.perf_table} (query_id, user_id, metric)\n                        VALUES (%(query_id)s, %(user_id)s, %(metric)s)\n                    ', {'query_id': i, 'user_id': f'concurrent_user_{i % 10}', 'metric': i * 1.1})
                await asyncio.sleep(0.2)

                async def run_concurrent_query(query_type: str, iterations: int):
                    """Run multiple queries concurrently."""
                    query_times = []
                    async with get_clickhouse_client(bypass_manager=True) as concurrent_client:
                        for i in range(iterations):
                            start = time.time()
                            if query_type == 'simple':
                                await concurrent_client.execute(f"\n                                    SELECT COUNT(*) as count FROM {self.perf_table}\n                                    WHERE user_id = 'concurrent_user_{i % 10}'\n                                ")
                            elif query_type == 'aggregate':
                                await concurrent_client.execute(f'\n                                    SELECT user_id, AVG(metric) as avg_metric\n                                    FROM {self.perf_table}\n                                    GROUP BY user_id\n                                    ORDER BY avg_metric DESC\n                                    LIMIT 5\n                                ')
                            query_times.append(time.time() - start)
                    return query_times
                start_time = time.time()
                concurrent_tasks = [run_concurrent_query('simple', 10), run_concurrent_query('aggregate', 8), run_concurrent_query('simple', 12), run_concurrent_query('aggregate', 6)]
                results = await asyncio.gather(*concurrent_tasks)
                total_concurrent_time = time.time() - start_time
                all_query_times = []
                for task_times in results:
                    all_query_times.extend(task_times)
                avg_query_time = sum(all_query_times) / len(all_query_times)
                max_query_time = max(all_query_times)
                total_queries = len(all_query_times)
                assert avg_query_time < 0.3, f'Average concurrent query time {avg_query_time:.3f}s exceeds 0.3s'
                assert max_query_time < 1.0, f'Maximum concurrent query time {max_query_time:.3f}s exceeds 1.0s'
                assert total_concurrent_time < 5.0, f'Total concurrent execution {total_concurrent_time:.3f}s exceeds 5.0s'
                throughput = total_queries / total_concurrent_time
                assert throughput > 10, f'Concurrent throughput {throughput:.1f} QPS is below minimum 10 QPS'
        finally:
            await self.cleanup_perf_table()

class TestClickHouseCachePerformanceIntegration(BaseIntegrationTest):
    """Test ClickHouse caching performance and efficiency."""

    def setup_method(self):
        """Setup cache performance testing."""
        validate_test_config('backend')
        self.cache_table = f'cache_test_{uuid.uuid4().hex[:8]}'

    async def cleanup_cache_table(self):
        """Cleanup cache test table."""
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'DROP TABLE IF EXISTS {self.cache_table}')
        except Exception as e:
            print(f'Warning: Failed to cleanup cache table: {e}')

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
            service.clear_cache()
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.cache_table} (\n                    id UInt64,\n                    user_id String,\n                    data String,\n                    timestamp DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = MergeTree()\n                ORDER BY (user_id, timestamp, id)\n                ')
                for i in range(200):
                    await client.execute(f'\n                        INSERT INTO {self.cache_table} (id, user_id, data)\n                        VALUES (%(id)s, %(user_id)s, %(data)s)\n                    ', {'id': i, 'user_id': f'cache_user_{i % 5}', 'data': f'Cache test data {i}' * 10})
                await asyncio.sleep(0.2)
                test_query = f'\n                    SELECT user_id, COUNT(*) as count, AVG(LENGTH(data)) as avg_length\n                    FROM {self.cache_table}\n                    WHERE user_id = %(user_id)s\n                    GROUP BY user_id\n                '
                test_params = {'user_id': 'cache_user_1'}
                user_id = 'cache_test_user'
                start_time = time.time()
                result1 = await service.execute(test_query, test_params, user_id=user_id)
                uncached_time = time.time() - start_time
                start_time = time.time()
                result2 = await service.execute(test_query, test_params, user_id=user_id)
                cached_time = time.time() - start_time
                assert result1 == result2, 'Cached result should match original'
                assert len(result1) > 0, 'Should return query results'
                cache_improvement_ratio = uncached_time / cached_time if cached_time > 0 else float('inf')
                assert cache_improvement_ratio > 2, f'Cache should improve performance by >2x, got {cache_improvement_ratio:.1f}x'
                assert cached_time < 0.05, f'Cached query should be <50ms, took {cached_time:.3f}s'
                cache_stats = service.get_cache_stats(user_id)
                assert cache_stats is not None, 'Should have cache statistics'
        finally:
            await self.cleanup_cache_table()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')