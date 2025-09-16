import asyncio

"""
Realistic Data Volumes Tests
Test with realistic data volumes
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
fix_clickhouse_array_syntax,
validate_clickhouse_query,
)

class TestRealisticDataVolumes:
    """Test with realistic data volumes"""

    @pytest.mark.asyncio
    async def test_large_scale_aggregation(self):
        """Test aggregation over large data volumes"""
        # Simulate a query over 1TB of data
        query = """
        SELECT 
        toStartOfHour(timestamp) as hour,
        workload_type,
        count() as event_count,
        avg(arrayElement(metrics.value, 
        arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency,
        quantile(0.99)(arrayElement(metrics.value,
        arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as p99_latency,
        sum(arrayElement(metrics.value,
        arrayFirstIndex(x -> x = 'cost_cents', metrics.name))) as total_cost
        FROM workload_events
        WHERE timestamp >= now() - INTERVAL 30 DAY
        AND (arrayExists(x -> x = 'latency_ms', metrics.name) 
        OR arrayExists(x -> x = 'cost_cents', metrics.name))
        GROUP BY hour, workload_type
        HAVING event_count > 1000
        ORDER BY hour DESC
        LIMIT 10000
        """""

        fixed_query = fix_clickhouse_array_syntax(query)
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Large scale aggregation failed: {error}"

        @pytest.mark.asyncio
        async def test_materialized_view_creation(self):
            """Test creation of materialized views for performance"""
            view_query = """
            CREATE MATERIALIZED VIEW IF NOT EXISTS llm_hourly_stats
            ENGINE = AggregatingMergeTree()
            ORDER BY (hour, model, workload_type)
            AS
            SELECT 
            toStartOfHour(timestamp) as hour,
            model,
            workload_type,
            count() as request_count,
            avg(latency_ms) as avg_latency,
            sum(cost_cents) as total_cost,
            sum(input_tokens) as total_input_tokens,
            sum(output_tokens) as total_output_tokens
            FROM llm_events
            GROUP BY hour, model, workload_type
            """""

        # Materialized view syntax should be valid
            assert "CREATE MATERIALIZED VIEW" in view_query
            assert "ENGINE = AggregatingMergeTree()" in view_query

            def test_partition_pruning_query(self):
                """Test queries that benefit from partition pruning"""
                partition_query = """
                SELECT 
                toYYYYMM(timestamp) as month,
                workload_type,
                count() as monthly_events,
                avg(duration_ms) as avg_duration,
                sum(duration_ms) / 1000 / 3600 as total_hours_processing
                FROM workload_events
                WHERE timestamp >= '2024-01-01'
                AND timestamp < '2024-07-01'
                AND workload_type IN ('rag_pipeline', 'simple_chat')
                GROUP BY month, workload_type
                ORDER BY month DESC, workload_type
                """""

                is_valid, error = validate_clickhouse_query(partition_query)
                assert is_valid, f"Partition pruning query failed: {error}"

                def test_high_cardinality_aggregation(self):
                    """Test aggregation with high cardinality dimensions"""
                    high_cardinality_query = """
                    SELECT 
                    user_id,
                    workload_type,
                    toDate(timestamp) as date,
                    count() as daily_requests,
                    sum(duration_ms) as total_duration,
                    avg(duration_ms) as avg_duration,
                    quantile(0.95)(duration_ms) as p95_duration,
                    uniq(session_id) as unique_sessions,
                    -- Calculate user activity metrics
                    sum(duration_ms) / 1000 / 60 as total_minutes_used,
                    CASE 
                    WHEN count() > 1000 THEN 'heavy_user'
                    WHEN count() > 100 THEN 'moderate_user'
                    ELSE 'light_user'
                    END as user_tier
                    FROM workload_events
                    WHERE timestamp >= now() - INTERVAL 30 DAY
                    GROUP BY user_id, workload_type, date
                    HAVING daily_requests > 10
                    ORDER BY total_duration DESC
                    LIMIT 100000
                    """""

                    is_valid, error = validate_clickhouse_query(high_cardinality_query)
                    assert is_valid, f"High cardinality aggregation failed: {error}"

                    def test_time_series_downsampling(self):
                        """Test downsampling of high-frequency time series data"""
                        downsampling_query = """
                        WITH minute_metrics AS (
                        SELECT 
                        toStartOfMinute(timestamp) as minute,
                        avg(arrayElement(metrics.value,
                        arrayFirstIndex(x -> x = 'throughput', metrics.name))) as avg_throughput,
                        max(arrayElement(metrics.value,
                        arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as max_latency,
                        count() as sample_count
                        FROM workload_events
                        WHERE timestamp >= now() - INTERVAL 7 DAY
                        AND arrayExists(x -> x IN ['throughput', 'latency_ms'], metrics.name)
                        GROUP BY minute
                        HAVING sample_count > 0
                        ),
                        hour_metrics AS (
                        SELECT 
                        toStartOfHour(minute) as hour,
                        avg(avg_throughput) as hourly_avg_throughput,
                        max(max_latency) as hourly_max_latency,
                        sum(sample_count) as hourly_samples
                        FROM minute_metrics
                        GROUP BY hour
                        ),
                        day_metrics AS (
                        SELECT 
                        toDate(hour) as day,
                        avg(hourly_avg_throughput) as daily_avg_throughput,
                        max(hourly_max_latency) as daily_max_latency,
                        sum(hourly_samples) as daily_samples
                        FROM hour_metrics
                        GROUP BY day
                        )
                        SELECT 
                        day,
                        daily_avg_throughput,
                        daily_max_latency,
                        daily_samples,
                        -- Calculate data reduction ratio
                        daily_samples / (24 * 60) as avg_samples_per_minute
                        FROM day_metrics
                        ORDER BY day DESC
                        """""

                        fixed_query = fix_clickhouse_array_syntax(downsampling_query)
                        is_valid, error = validate_clickhouse_query(fixed_query)
                        assert is_valid, f"Time series downsampling failed: {error}"

                        def test_complex_join_performance(self):
                            """Test performance of complex joins across large tables"""
                            complex_join_query = """
                            WITH user_profiles AS (
                            SELECT 
                            user_id,
                            count() as total_requests,
                            avg(duration_ms) as avg_duration,
                            uniq(workload_type) as workload_diversity,
                            min(timestamp) as first_request,
                            max(timestamp) as last_request
                            FROM workload_events
                            WHERE timestamp >= now() - INTERVAL 30 DAY
                            GROUP BY user_id
                            HAVING total_requests > 100
                            ),
                            user_costs AS (
                            SELECT 
                            user_id,
                            sum(cost_cents) as total_cost,
                            avg(cost_cents) as avg_cost_per_request,
                            count() as llm_requests
                            FROM llm_events
                            WHERE timestamp >= now() - INTERVAL 30 DAY
                            GROUP BY user_id
                            ),
                            user_errors AS (
                            SELECT 
                            JSONExtractInt(metadata, 'user_id') as user_id,
                            countIf(level = 'ERROR') as error_count,
                            countIf(level = 'WARNING') as warning_count
                            FROM netra_app_internal_logs
                            WHERE timestamp >= now() - INTERVAL 30 DAY
                            AND JSONExtractInt(metadata, 'user_id') > 0
                            GROUP BY user_id
                            )
                            SELECT 
                            up.user_id,
                            up.total_requests,
                            up.avg_duration,
                            up.workload_diversity,
                            uc.total_cost,
                            uc.avg_cost_per_request,
                            uc.llm_requests,
                            ue.error_count,
                            ue.warning_count,
                            -- Calculate derived metrics
                            uc.total_cost / nullIf(up.total_requests, 0) as cost_per_workload_request,
                            ue.error_count / nullIf(up.total_requests, 0) as error_rate,
                            dateDiff('day', up.first_request, up.last_request) as days_active,
                            -- User value score
                            (up.total_requests * 0.1 + uc.llm_requests * 0.5 + up.workload_diversity * 10 - ue.error_count * 2) as value_score
                            FROM user_profiles up
                            LEFT JOIN user_costs uc ON up.user_id = uc.user_id
                            LEFT JOIN user_errors ue ON up.user_id = ue.user_id
                            ORDER BY value_score DESC
                            LIMIT 10000
                            """""

                            is_valid, error = validate_clickhouse_query(complex_join_query)
                            assert is_valid, f"Complex join performance query failed: {error}"

                            def test_streaming_aggregation_simulation(self):
                                """Test streaming aggregation patterns for real-time analytics"""
                                streaming_query = """
                                WITH real_time_metrics AS (
                                SELECT 
                                toStartOfInterval(timestamp, INTERVAL 30 SECOND) as time_window,
                                workload_type,
                                count() as requests_per_30s,
                                avg(duration_ms) as avg_duration_30s,
                                countIf(status = 'failed') as failures_per_30s,
                                uniq(user_id) as unique_users_30s
                                FROM workload_events
                                WHERE timestamp >= now() - INTERVAL 10 MINUTE
                                GROUP BY time_window, workload_type
                                ),
                                sliding_window_metrics AS (
                                SELECT 
                                time_window,
                                workload_type,
                                requests_per_30s,
                                avg_duration_30s,
                                failures_per_30s,
                                unique_users_30s,
                                -- 5-minute sliding window averages
                                avg(requests_per_30s) OVER (
                                PARTITION BY workload_type 
                                ORDER BY time_window 
                                ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                                ) as avg_requests_5min,
                                avg(avg_duration_30s) OVER (
                                PARTITION BY workload_type 
                                ORDER BY time_window 
                                ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                                ) as avg_duration_5min
                                FROM real_time_metrics
                                )
                                SELECT 
                                time_window,
                                workload_type,
                                requests_per_30s,
                                avg_duration_30s,
                                failures_per_30s,
                                unique_users_30s,
                                avg_requests_5min,
                                avg_duration_5min,
                                -- Anomaly detection
                                CASE 
                                WHEN requests_per_30s > avg_requests_5min * 2 THEN 'traffic_spike'
                                WHEN avg_duration_30s > avg_duration_5min * 1.5 THEN 'latency_spike'
                                WHEN failures_per_30s > 5 THEN 'error_spike'
                                ELSE 'normal'
                                END as anomaly_status
                                FROM sliding_window_metrics
                                ORDER BY time_window DESC, workload_type
                                """""

                                is_valid, error = validate_clickhouse_query(streaming_query)
                                assert is_valid, f"Streaming aggregation simulation failed: {error}"