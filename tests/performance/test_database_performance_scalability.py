"""
Performance and Scalability Tests for Database Operations

Business Value Justification (BVJ):
- Segment: All (Performance impacts all customer tiers - Free, Early, Mid, Enterprise)
- Business Goal: Ensure system performance meets customer expectations under load
- Value Impact: Fast database operations directly impact user experience and customer satisfaction
- Strategic Impact: Scalable database performance enables platform growth and enterprise adoption

This test suite validates:
1. Database query performance under various load conditions
2. Connection pooling efficiency and scalability
3. Concurrent user handling and data isolation
4. Memory usage and resource optimization
5. Throughput and latency characteristics
6. Performance degradation thresholds
7. Recovery and performance after failures
"""

import pytest
import asyncio
import time
import psutil
import gc
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median
from dataclasses import dataclass

from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.configuration_validator import is_service_enabled
from shared.isolated_environment import get_env


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    operation_name: str
    total_operations: int
    total_time: float
    average_time: float
    median_time: float
    min_time: float
    max_time: float
    operations_per_second: float
    success_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float


class PerformanceProfiler:
    """Performance profiler for database operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.success_count = 0
        self.total_operations = 0
        self.start_memory = None
        self.start_cpu = None
    
    def start_profiling(self):
        """Start performance profiling."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = psutil.cpu_percent(interval=None)
        gc.collect()  # Clean garbage before test
    
    def record_operation(self, operation_time: float, success: bool = True):
        """Record an individual operation."""
        self.operation_times.append(operation_time)
        self.total_operations += 1
        if success:
            self.success_count += 1
    
    def end_profiling(self, operation_name: str) -> PerformanceMetrics:
        """End profiling and return metrics."""
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        current_cpu = psutil.cpu_percent(interval=None)
        
        if self.operation_times:
            avg_time = mean(self.operation_times)
            median_time = median(self.operation_times)
            min_time = min(self.operation_times)
            max_time = max(self.operation_times)
        else:
            avg_time = median_time = min_time = max_time = 0.0
        
        return PerformanceMetrics(
            operation_name=operation_name,
            total_operations=self.total_operations,
            total_time=total_time,
            average_time=avg_time,
            median_time=median_time,
            min_time=min_time,
            max_time=max_time,
            operations_per_second=self.total_operations / total_time if total_time > 0 else 0,
            success_rate=self.success_count / self.total_operations if self.total_operations > 0 else 0,
            memory_usage_mb=current_memory - self.start_memory,
            cpu_usage_percent=current_cpu
        )


@pytest.mark.performance
@pytest.mark.real_services
class TestDatabasePerformanceScalability:
    """Performance and scalability tests for database operations."""
    
    @pytest.fixture
    async def performance_clickhouse_db(self):
        """Create ClickHouse connection for performance testing."""
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled - performance tests require real database")
        
        env = get_env()
        
        try:
            db = ClickHouseDatabase(
                host=env.get("CLICKHOUSE_HOST", "localhost"),
                port=int(env.get("CLICKHOUSE_PORT", "8123")),
                database=env.get("CLICKHOUSE_DATABASE", "test_db"),
                user=env.get("CLICKHOUSE_USER", "default"),
                password=env.get("CLICKHOUSE_PASSWORD", ""),
                secure=env.get("CLICKHOUSE_SECURE", "false").lower() == "true"
            )
            
            if not await db.test_connection():
                pytest.skip("ClickHouse not available for performance testing")
            
            yield db
            
        except Exception as e:
            pytest.skip(f"ClickHouse unavailable for performance testing: {e}")
        
        finally:
            try:
                await db.disconnect()
            except:
                pass
    
    @pytest.fixture
    async def performance_test_table(self, performance_clickhouse_db):
        """Create performance test table."""
        table_name = f"perf_test_{int(time.time())}"
        
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            id UInt64,
            user_id String,
            timestamp DateTime64(3),
            event_type String,
            data String,
            value Float64,
            category LowCardinality(String),
            tags Array(String)
        ) ENGINE = MergeTree()
        ORDER BY (user_id, timestamp)
        PARTITION BY toYYYYMM(timestamp)
        """
        
        try:
            await performance_clickhouse_db.command(create_table_sql)
            yield table_name
        finally:
            try:
                await performance_clickhouse_db.command(f"DROP TABLE IF EXISTS {table_name}")
            except:
                pass
    
    async def test_single_operation_performance_baseline(self, performance_clickhouse_db):
        """Test baseline performance for single database operations."""
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        # Test simple query performance
        for i in range(100):
            start_time = time.time()
            
            try:
                result = await performance_clickhouse_db.execute_query("SELECT 1 as test_value")
                assert len(result) == 1
                success = True
            except Exception:
                success = False
            
            operation_time = time.time() - start_time
            profiler.record_operation(operation_time, success)
        
        metrics = profiler.end_profiling("simple_query")
        
        # Performance assertions
        assert metrics.success_rate >= 0.95  # 95% success rate minimum
        assert metrics.average_time < 0.1     # Average query should be < 100ms
        assert metrics.operations_per_second >= 10  # At least 10 ops/sec
        assert metrics.memory_usage_mb < 50   # Memory usage should be reasonable
        
        print(f"Single Operation Baseline: {metrics.operations_per_second:.2f} ops/sec, "
              f"avg: {metrics.average_time*1000:.2f}ms")
    
    async def test_batch_insertion_performance(self, performance_clickhouse_db, performance_test_table):
        """Test batch insertion performance with varying batch sizes."""
        table_name = performance_test_table
        batch_sizes = [100, 500, 1000, 2000]
        
        performance_results = {}
        
        for batch_size in batch_sizes:
            profiler = PerformanceProfiler()
            profiler.start_profiling()
            
            # Generate test data
            batch_data = []
            for i in range(batch_size):
                batch_data.append([
                    i,
                    f"user_{i % 100}",
                    "2025-01-01 12:00:00",
                    f"event_type_{i % 10}",
                    f'{{"data": "test_data_{i}", "value": {i}}}',
                    float(i * 1.5),
                    f"category_{i % 5}",
                    [f"tag_{i % 3}", f"tag_{(i+1) % 3}"]
                ])
            
            column_names = ["id", "user_id", "timestamp", "event_type", "data", "value", "category", "tags"]
            
            # Perform batch insertion
            start_time = time.time()
            
            try:
                await performance_clickhouse_db.insert_data(table_name, batch_data, column_names)
                success = True
            except Exception as e:
                success = False
                print(f"Batch insertion failed for size {batch_size}: {e}")
            
            operation_time = time.time() - start_time
            profiler.record_operation(operation_time, success)
            
            metrics = profiler.end_profiling(f"batch_insert_{batch_size}")
            performance_results[batch_size] = metrics
            
            # Performance assertions based on batch size
            assert metrics.success_rate >= 0.95
            
            if batch_size <= 1000:
                assert metrics.average_time < 2.0  # Small batches should be fast
            else:
                assert metrics.average_time < 5.0  # Larger batches have more leeway
            
            # Verify data was inserted
            count_query = f"SELECT COUNT(*) as total FROM {table_name}"
            count_result = await performance_clickhouse_db.execute_query(count_query)
            expected_total = sum(batch_sizes[:batch_sizes.index(batch_size) + 1])
            assert count_result[0]["total"] == expected_total
        
        # Analyze performance scaling
        for batch_size, metrics in performance_results.items():
            print(f"Batch Size {batch_size}: {metrics.operations_per_second:.2f} ops/sec, "
                  f"time: {metrics.average_time:.3f}s, "
                  f"memory: {metrics.memory_usage_mb:.2f}MB")
    
    async def test_concurrent_query_performance(self, performance_clickhouse_db, performance_test_table):
        """Test concurrent query performance and connection handling."""
        table_name = performance_test_table
        
        # Insert test data first
        test_data = []
        for i in range(1000):
            test_data.append([
                i,
                f"user_{i % 50}",
                "2025-01-01 12:00:00",
                f"event_{i % 10}",
                f'{{"concurrent_test": {i}}}',
                float(i),
                f"cat_{i % 5}",
                [f"tag_{i % 3}"]
            ])
        
        column_names = ["id", "user_id", "timestamp", "event_type", "data", "value", "category", "tags"]
        await performance_clickhouse_db.insert_data(table_name, test_data, column_names)
        
        concurrent_levels = [1, 5, 10, 20]
        
        for concurrency in concurrent_levels:
            profiler = PerformanceProfiler()
            profiler.start_profiling()
            
            async def concurrent_query_worker(worker_id: int):
                """Worker function for concurrent queries."""
                worker_times = []
                
                for i in range(10):  # 10 queries per worker
                    query_start = time.time()
                    
                    try:
                        query = f"""
                        SELECT 
                            user_id,
                            COUNT(*) as event_count,
                            AVG(value) as avg_value
                        FROM {table_name}
                        WHERE id >= {worker_id * 50} AND id < {(worker_id + 1) * 50}
                        GROUP BY user_id
                        ORDER BY event_count DESC
                        LIMIT 5
                        """
                        
                        result = await performance_clickhouse_db.execute_query(query)
                        assert isinstance(result, list)
                        success = True
                        
                    except Exception as e:
                        print(f"Worker {worker_id} query {i} failed: {e}")
                        success = False
                    
                    query_time = time.time() - query_start
                    worker_times.append((query_time, success))
                
                return worker_times
            
            # Run concurrent workers
            tasks = [concurrent_query_worker(i) for i in range(concurrency)]
            start_concurrent = time.time()
            
            worker_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_time = time.time() - start_concurrent
            
            # Process results
            total_queries = 0
            successful_queries = 0
            all_query_times = []
            
            for worker_result in worker_results:
                if isinstance(worker_result, list):
                    for query_time, success in worker_result:
                        total_queries += 1
                        if success:
                            successful_queries += 1
                        all_query_times.append(query_time)
                        profiler.record_operation(query_time, success)
            
            metrics = profiler.end_profiling(f"concurrent_queries_{concurrency}")
            
            # Performance assertions
            assert metrics.success_rate >= 0.90  # 90% success rate under concurrency
            assert metrics.average_time < 1.0     # Individual queries should still be fast
            
            # Throughput should improve with concurrency (to a point)
            if concurrency <= 10:
                assert metrics.operations_per_second >= concurrency * 5  # At least 5 ops/sec per worker
            
            print(f"Concurrency {concurrency}: {metrics.operations_per_second:.2f} ops/sec, "
                  f"success rate: {metrics.success_rate:.2%}, "
                  f"avg time: {metrics.average_time*1000:.2f}ms")
    
    async def test_large_dataset_query_performance(self, performance_clickhouse_db, performance_test_table):
        """Test query performance on large datasets."""
        table_name = performance_test_table
        
        # Insert large dataset in chunks
        chunk_size = 5000
        total_records = 50000
        
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        print(f"Inserting {total_records} records in chunks of {chunk_size}...")
        
        for chunk_start in range(0, total_records, chunk_size):
            chunk_data = []
            chunk_end = min(chunk_start + chunk_size, total_records)
            
            for i in range(chunk_start, chunk_end):
                chunk_data.append([
                    i,
                    f"user_{i % 1000}",  # 1000 unique users
                    "2025-01-01 12:00:00",
                    f"event_type_{i % 20}",  # 20 event types
                    f'{{"large_dataset": {i}, "category": "{i % 100}"}}',
                    float(i * 2.5),
                    f"category_{i % 10}",  # 10 categories
                    [f"tag_{i % 5}", f"tag_{(i+1) % 5}", f"tag_{(i+2) % 5}"]
                ])
            
            column_names = ["id", "user_id", "timestamp", "event_type", "data", "value", "category", "tags"]
            
            insert_start = time.time()
            await performance_clickhouse_db.insert_data(table_name, chunk_data, column_names)
            insert_time = time.time() - insert_start
            
            profiler.record_operation(insert_time, True)
        
        insert_metrics = profiler.end_profiling("large_dataset_insertion")
        
        print(f"Large dataset insertion: {insert_metrics.operations_per_second:.2f} chunks/sec")
        
        # Test complex queries on large dataset
        complex_queries = [
            # Simple aggregation
            f"SELECT COUNT(*) as total FROM {table_name}",
            
            # Group by aggregation
            f"""
            SELECT 
                category,
                COUNT(*) as event_count,
                AVG(value) as avg_value,
                MAX(value) as max_value
            FROM {table_name}
            GROUP BY category
            ORDER BY event_count DESC
            """,
            
            # User-based aggregation
            f"""
            SELECT 
                user_id,
                COUNT(*) as user_events,
                SUM(value) as total_value
            FROM {table_name}
            GROUP BY user_id
            HAVING user_events > 40
            ORDER BY total_value DESC
            LIMIT 100
            """,
            
            # Complex filtering and aggregation
            f"""
            SELECT 
                event_type,
                category,
                COUNT(*) as combo_count,
                percentile(value, 0.5) as median_value,
                percentile(value, 0.95) as p95_value
            FROM {table_name}
            WHERE value > 1000 AND arrayExists(x -> x LIKE 'tag_1%', tags)
            GROUP BY event_type, category
            ORDER BY combo_count DESC
            LIMIT 50
            """
        ]
        
        query_profiler = PerformanceProfiler()
        query_profiler.start_profiling()
        
        for i, query in enumerate(complex_queries):
            query_start = time.time()
            
            try:
                result = await performance_clickhouse_db.execute_query(query)
                assert isinstance(result, list)
                assert len(result) > 0
                success = True
                
            except Exception as e:
                print(f"Complex query {i} failed: {e}")
                success = False
            
            query_time = time.time() - query_start
            query_profiler.record_operation(query_time, success)
            
            print(f"Query {i+1}: {query_time:.3f}s, {len(result) if success else 0} results")
        
        query_metrics = query_profiler.end_profiling("complex_queries_large_dataset")
        
        # Performance assertions for large dataset queries
        assert query_metrics.success_rate >= 0.90
        assert query_metrics.average_time < 10.0  # Complex queries should complete within 10s
        
        # Verify data integrity
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        count_result = await performance_clickhouse_db.execute_query(count_query)
        assert count_result[0]["total"] == total_records
    
    async def test_memory_usage_and_resource_optimization(self, performance_clickhouse_db, performance_test_table):
        """Test memory usage and resource optimization under load."""
        table_name = performance_test_table
        
        # Monitor memory usage during intensive operations
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        memory_measurements = []
        
        # Perform memory-intensive operations
        for batch_num in range(10):
            # Generate large batch
            large_batch = []
            batch_size = 10000
            
            for i in range(batch_size):
                record_id = batch_num * batch_size + i
                large_batch.append([
                    record_id,
                    f"memory_test_user_{record_id % 500}",
                    "2025-01-01 12:00:00",
                    f"memory_event_{record_id % 15}",
                    f'{{"large_payload": "{"x" * 100}", "id": {record_id}, "batch": {batch_num}}}',  # Larger payload
                    float(record_id * 3.14),
                    f"mem_category_{record_id % 8}",
                    [f"mem_tag_{record_id % 7}", f"mem_tag_{(record_id+1) % 7}"]
                ])
            
            column_names = ["id", "user_id", "timestamp", "event_type", "data", "value", "category", "tags"]
            
            # Insert batch and measure memory
            await performance_clickhouse_db.insert_data(table_name, large_batch, column_names)
            
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_usage = current_memory - initial_memory
            memory_measurements.append(memory_usage)
            
            # Force garbage collection
            gc.collect()
            
            print(f"Batch {batch_num + 1}: Memory usage {memory_usage:.2f}MB")
        
        # Memory usage assertions
        max_memory_usage = max(memory_measurements)
        avg_memory_usage = mean(memory_measurements)
        
        # Memory usage should be reasonable (< 500MB for test operations)
        assert max_memory_usage < 500, f"Memory usage too high: {max_memory_usage:.2f}MB"
        
        # Memory should not continuously grow (basic leak detection)
        final_memory = memory_measurements[-1]
        initial_test_memory = memory_measurements[0]
        memory_growth = final_memory - initial_test_memory
        
        # Growth should be bounded
        assert memory_growth < 200, f"Excessive memory growth: {memory_growth:.2f}MB"
        
        print(f"Memory test: Max {max_memory_usage:.2f}MB, Avg {avg_memory_usage:.2f}MB, Growth {memory_growth:.2f}MB")
    
    async def test_connection_pooling_performance(self, performance_clickhouse_db):
        """Test connection pooling efficiency and performance."""
        # This test would be more relevant for connection managers
        # but we can test basic connection reuse efficiency
        
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        # Test rapid consecutive queries (connection reuse)
        for i in range(100):
            query_start = time.time()
            
            try:
                # Simple query that should reuse connection
                result = await performance_clickhouse_db.execute_query(f"SELECT {i} as iteration")
                assert result[0]["iteration"] == i
                success = True
                
            except Exception:
                success = False
            
            query_time = time.time() - query_start
            profiler.record_operation(query_time, success)
        
        metrics = profiler.end_profiling("connection_reuse")
        
        # Connection reuse should be very fast
        assert metrics.success_rate >= 0.98
        assert metrics.average_time < 0.05  # Should be very fast with connection reuse
        assert metrics.operations_per_second >= 20  # High throughput with reuse
        
        print(f"Connection reuse: {metrics.operations_per_second:.2f} ops/sec, "
              f"avg: {metrics.average_time*1000:.2f}ms")
    
    async def test_performance_degradation_thresholds(self, performance_clickhouse_db, performance_test_table):
        """Test performance degradation thresholds and limits."""
        table_name = performance_test_table
        
        # Test performance under increasing load
        load_levels = [10, 50, 100, 200, 500]
        performance_degradation = {}
        
        for load_level in load_levels:
            profiler = PerformanceProfiler()
            profiler.start_profiling()
            
            # Generate load-appropriate dataset
            load_data = []
            for i in range(load_level):
                load_data.append([
                    i,
                    f"load_user_{i % max(1, load_level // 10)}",
                    "2025-01-01 12:00:00",
                    f"load_event_{i % 5}",
                    f'{{"load_test": {i}, "level": {load_level}}}',
                    float(i * 1.1),
                    f"load_cat_{i % 3}",
                    [f"load_tag_{i % 2}"]
                ])
            
            column_names = ["id", "user_id", "timestamp", "event_type", "data", "value", "category", "tags"]
            
            # Insert data
            insert_start = time.time()
            await performance_clickhouse_db.insert_data(table_name, load_data, column_names)
            insert_time = time.time() - insert_start
            profiler.record_operation(insert_time, True)
            
            # Query the data
            query_start = time.time()
            query = f"""
            SELECT 
                user_id,
                COUNT(*) as events,
                AVG(value) as avg_value
            FROM {table_name}
            WHERE id >= 0
            GROUP BY user_id
            ORDER BY events DESC
            """
            
            try:
                result = await performance_clickhouse_db.execute_query(query)
                query_time = time.time() - query_start
                profiler.record_operation(query_time, True)
                success = True
                
            except Exception as e:
                query_time = time.time() - query_start
                profiler.record_operation(query_time, False)
                success = False
                print(f"Query failed at load level {load_level}: {e}")
            
            metrics = profiler.end_profiling(f"load_level_{load_level}")
            performance_degradation[load_level] = metrics
            
            print(f"Load {load_level}: {metrics.operations_per_second:.2f} ops/sec, "
                  f"avg: {metrics.average_time:.3f}s, success: {metrics.success_rate:.2%}")
        
        # Analyze performance degradation
        baseline_ops_per_sec = performance_degradation[load_levels[0]].operations_per_second
        
        for load_level, metrics in performance_degradation.items():
            degradation_ratio = metrics.operations_per_second / baseline_ops_per_sec
            
            # Performance should not degrade more than 50% even at high load
            if load_level <= 200:
                assert degradation_ratio >= 0.5, (
                    f"Excessive performance degradation at load {load_level}: "
                    f"{degradation_ratio:.2%} of baseline performance"
                )
            
            # System should remain functional even under stress
            assert metrics.success_rate >= 0.80, (
                f"Unacceptable failure rate at load {load_level}: {metrics.success_rate:.2%}"
            )
    
    async def test_recovery_performance_after_failure(self, performance_clickhouse_db):
        """Test performance recovery after connection failures."""
        # Test baseline performance
        baseline_profiler = PerformanceProfiler()
        baseline_profiler.start_profiling()
        
        for i in range(20):
            start_time = time.time()
            try:
                result = await performance_clickhouse_db.execute_query("SELECT 1 as baseline")
                success = True
            except Exception:
                success = False
            
            operation_time = time.time() - start_time
            baseline_profiler.record_operation(operation_time, success)
        
        baseline_metrics = baseline_profiler.end_profiling("baseline_before_failure")
        
        # Simulate connection failure and recovery
        await performance_clickhouse_db.disconnect()
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Reconnect (create new connection)
        env = get_env()
        recovered_db = ClickHouseDatabase(
            host=env.get("CLICKHOUSE_HOST", "localhost"),
            port=int(env.get("CLICKHOUSE_PORT", "8123")),
            database=env.get("CLICKHOUSE_DATABASE", "test_db"),
            user=env.get("CLICKHOUSE_USER", "default"),
            password=env.get("CLICKHOUSE_PASSWORD", ""),
        )
        
        # Test performance after recovery
        recovery_profiler = PerformanceProfiler()
        recovery_profiler.start_profiling()
        
        for i in range(20):
            start_time = time.time()
            try:
                result = await recovered_db.execute_query("SELECT 1 as recovery")
                success = True
            except Exception:
                success = False
            
            operation_time = time.time() - start_time
            recovery_profiler.record_operation(operation_time, success)
        
        recovery_metrics = recovery_profiler.end_profiling("performance_after_recovery")
        
        # Performance should recover to near baseline levels
        performance_ratio = recovery_metrics.operations_per_second / baseline_metrics.operations_per_second
        
        assert recovery_metrics.success_rate >= 0.90  # Should recover successfully
        assert performance_ratio >= 0.75  # Performance should recover to at least 75% of baseline
        
        print(f"Recovery performance: {performance_ratio:.2%} of baseline, "
              f"success rate: {recovery_metrics.success_rate:.2%}")
        
        # Cleanup
        await recovered_db.disconnect()