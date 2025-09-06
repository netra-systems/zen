"""
Performance Metrics Extraction Tests
Test performance metrics extraction from ClickHouse
"""

from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.db.clickhouse_query_fixer import (

    fix_clickhouse_array_syntax,

    validate_clickhouse_query,

)
from netra_backend.tests.fixtures.realistic_test_fixtures import validate_array_query_syntax

class TestPerformanceMetricsWithClickHouse:

    """Test performance metrics extraction from ClickHouse"""
    
    def test_metrics_extraction_with_arrays(self):

        """Test extracting metrics from nested arrays"""

        query = """

        WITH parsed_metrics AS (

            SELECT 

                timestamp,

                user_id,

                workload_id,

                arrayFirstIndex(x -> x = 'gpu_utilization', metrics.name) as gpu_idx,

                arrayFirstIndex(x -> x = 'memory_usage', metrics.name) as mem_idx,

                arrayFirstIndex(x -> x = 'throughput', metrics.name) as tput_idx,

                IF(gpu_idx > 0, arrayElement(metrics.value, gpu_idx), 0) as gpu_util,

                IF(mem_idx > 0, arrayElement(metrics.value, mem_idx), 0) as memory_mb,

                IF(tput_idx > 0, arrayElement(metrics.value, tput_idx), 0) as throughput

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 1 HOUR

        )

        SELECT 

            toStartOfMinute(timestamp) as minute,

            avg(gpu_util) as avg_gpu,

            max(memory_mb) as max_memory,

            sum(throughput) as total_throughput

        FROM parsed_metrics

        GROUP BY minute

        ORDER BY minute DESC

        """
        
        # Fix any array syntax issues

        fixed_query = fix_clickhouse_array_syntax(query)
        
        # Validate the fixed query

        is_valid, error = validate_clickhouse_query(fixed_query)

        assert is_valid, f"Metrics extraction query failed: {error}"
        
        # Ensure proper array functions are used

        assert "arrayFirstIndex" in fixed_query

        assert "arrayElement" in fixed_query

        assert "metrics.value[" not in fixed_query

    def test_system_resource_metrics(self):

        """Test system resource metrics extraction"""

        resource_query = """

        WITH resource_metrics AS (

            SELECT 

                timestamp,

                workload_id,

                arrayElement(metrics.value, 

                    arrayFirstIndex(x -> x = 'cpu_usage', metrics.name)) as cpu_percent,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'memory_usage', metrics.name)) as memory_mb,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'disk_io', metrics.name)) as disk_io_ops,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'network_bytes', metrics.name)) as network_bytes

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 1 HOUR

                AND arrayExists(x -> x IN ['cpu_usage', 'memory_usage', 'disk_io', 'network_bytes'], metrics.name)

        )

        SELECT 

            workload_id,

            avg(cpu_percent) as avg_cpu,

            max(memory_mb) as peak_memory,

            sum(disk_io_ops) as total_disk_ops,

            sum(network_bytes) as total_network_bytes,

            count() as sample_count

        FROM resource_metrics

        WHERE cpu_percent > 0 OR memory_mb > 0

        GROUP BY workload_id

        ORDER BY avg_cpu DESC

        """
        
        is_valid, error = validate_clickhouse_query(resource_query)

        assert is_valid, f"Resource metrics query failed: {error}"

    def test_performance_threshold_monitoring(self):

        """Test performance threshold monitoring queries"""

        threshold_query = """

        WITH performance_data AS (

            SELECT 

                timestamp,

                workload_id,

                user_id,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name)) as latency,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'throughput', metrics.name)) as throughput,

                arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'error_rate', metrics.name)) as error_rate

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 1 HOUR

                AND arrayExists(x -> x IN ['latency_ms', 'throughput', 'error_rate'], metrics.name)

        ),

        threshold_violations AS (

            SELECT 

                timestamp,

                workload_id,

                user_id,

                latency,

                throughput,

                error_rate,

                CASE 

                    WHEN latency > 5000 THEN 'high_latency'

                    WHEN throughput < 10 THEN 'low_throughput'

                    WHEN error_rate > 0.05 THEN 'high_error_rate'

                    ELSE 'normal'

                END as violation_type

            FROM performance_data

            WHERE latency > 5000 OR throughput < 10 OR error_rate > 0.05

        )

        SELECT 

            violation_type,

            count() as violation_count,

            uniq(workload_id) as affected_workloads,

            uniq(user_id) as affected_users,

            avg(latency) as avg_latency_during_violation,

            min(timestamp) as first_occurrence,

            max(timestamp) as last_occurrence

        FROM threshold_violations

        GROUP BY violation_type

        ORDER BY violation_count DESC

        """
        
        is_valid, error = validate_clickhouse_query(threshold_query)

        assert is_valid, f"Threshold monitoring query failed: {error}"

    def test_performance_correlation_analysis(self):

        """Test performance correlation between different metrics"""

        correlation_query = """

        WITH metric_pairs AS (

            SELECT 

                toStartOfMinute(timestamp) as minute,

                avg(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency,

                avg(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'cpu_usage', metrics.name))) as avg_cpu,

                avg(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'memory_usage', metrics.name))) as avg_memory,

                avg(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'throughput', metrics.name))) as avg_throughput

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 6 HOUR

                AND arrayExists(x -> x IN ['latency_ms', 'cpu_usage', 'memory_usage', 'throughput'], metrics.name)

            GROUP BY minute

            HAVING count() > 10

        )

        SELECT 

            corr(avg_latency, avg_cpu) as latency_cpu_correlation,

            corr(avg_latency, avg_memory) as latency_memory_correlation,

            corr(avg_throughput, avg_cpu) as throughput_cpu_correlation,

            corr(avg_throughput, avg_memory) as throughput_memory_correlation,

            count() as sample_points

        FROM metric_pairs

        WHERE avg_latency > 0 AND avg_cpu > 0 AND avg_memory > 0 AND avg_throughput > 0

        """
        
        is_valid, error = validate_clickhouse_query(correlation_query)

        assert is_valid, f"Correlation analysis query failed: {error}"

    def test_performance_baseline_calculation(self):

        """Test performance baseline calculation for comparison"""

        baseline_query = """

        WITH historical_performance AS (

            SELECT 

                workload_id,

                toHour(timestamp) as hour,

                avg(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency,

                quantile(0.95)(arrayElement(metrics.value,

                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as p95_latency,

                count() as request_count

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 7 DAY

                AND timestamp < now() - INTERVAL 1 DAY

                AND arrayExists(x -> x = 'latency_ms', metrics.name)

            GROUP BY workload_id, hour

            HAVING request_count > 5

        ),

        baselines AS (

            SELECT 

                workload_id,

                avg(avg_latency) as baseline_avg_latency,

                avg(p95_latency) as baseline_p95_latency,

                stddevPop(avg_latency) as latency_stddev

            FROM historical_performance

            GROUP BY workload_id

        )

        SELECT 

            workload_id,

            baseline_avg_latency,

            baseline_p95_latency,

            latency_stddev,

            baseline_avg_latency + 2 * latency_stddev as alert_threshold,

            baseline_p95_latency * 1.5 as p95_alert_threshold

        FROM baselines

        ORDER BY workload_id

        """
        
        is_valid, error = validate_clickhouse_query(baseline_query)

        assert is_valid, f"Baseline calculation query failed: {error}"