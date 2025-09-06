"""
Time Series Analysis Tests
Test time-series analysis capabilities
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query

class TestTimeSeriesAnalysis:
    """Test time-series analysis capabilities"""

    def test_moving_average_calculation(self):
        """Test moving average calculation for metrics"""
        query = """
        WITH time_series AS (
        SELECT 
        toStartOfMinute(timestamp) as minute,
        avg(arrayElement(metrics.value, 
        arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency
        FROM workload_events
        WHERE timestamp >= now() - INTERVAL 24 HOUR
        AND arrayExists(x -> x = 'latency_ms', metrics.name)
        GROUP BY minute
        )
        SELECT 
        minute,
        avg_latency,
        avg(avg_latency) OVER (
        ORDER BY minute 
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as moving_avg_6min,
        avg(avg_latency) OVER (
        ORDER BY minute 
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW  
        ) as moving_avg_1hour
        FROM time_series
        ORDER BY minute DESC
        """""

        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Moving average query failed: {error}"

        def test_anomaly_detection_with_zscore(self):
            """Test anomaly detection using z-score"""
            query = """
            WITH baseline AS (
            SELECT 
            avg(arrayElement(metrics.value, 
            arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as mean_latency,
            stddevPop(arrayElement(metrics.value,
            arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as stddev_latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 7 DAY
            AND timestamp < now() - INTERVAL 1 HOUR
            AND arrayExists(x -> x = 'latency_ms', metrics.name)
            ),
            recent_data AS (
            SELECT 
            timestamp,
            workload_id,
            arrayElement(metrics.value,
            arrayFirstIndex(x -> x = 'latency_ms', metrics.name)) as latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            AND arrayExists(x -> x = 'latency_ms', metrics.name)
            )
            SELECT 
            rd.timestamp,
            rd.workload_id,
            rd.latency,
            b.mean_latency,
            b.stddev_latency,
            (rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0) as z_score,
            CASE 
            WHEN abs((rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0)) > 3 THEN 'critical'
            WHEN abs((rd.latency - b.mean_latency) / nullIf(b.stddev_latency, 0)) > 2 THEN 'warning'
            ELSE 'normal'
            END as anomaly_level
            FROM recent_data rd
            CROSS JOIN baseline b
            ORDER BY z_score DESC
            """""

            is_valid, error = validate_clickhouse_query(query)
            assert is_valid, f"Anomaly detection query failed: {error}"

            def test_seasonal_pattern_detection(self):
                """Test detection of seasonal patterns in metrics"""
                seasonal_query = """
                WITH hourly_metrics AS (
                SELECT 
                toHour(timestamp) as hour_of_day,
                toDayOfWeek(timestamp) as day_of_week,
                avg(arrayElement(metrics.value,
                arrayFirstIndex(x -> x = 'throughput', metrics.name))) as avg_throughput,
                count() as sample_count
                FROM workload_events
                WHERE timestamp >= now() - INTERVAL 30 DAY
                AND arrayExists(x -> x = 'throughput', metrics.name)
                GROUP BY hour_of_day, day_of_week
                HAVING sample_count > 10
                ),
                hourly_patterns AS (
                SELECT 
                hour_of_day,
                avg(avg_throughput) as typical_throughput,
                stddevPop(avg_throughput) as throughput_variance,
                count() as pattern_sample_size
                FROM hourly_metrics
                GROUP BY hour_of_day
                ),
                daily_patterns AS (
                SELECT 
                day_of_week,
                avg(avg_throughput) as typical_daily_throughput,
                stddevPop(avg_throughput) as daily_variance
                FROM hourly_metrics
                GROUP BY day_of_week
                )
                SELECT 
                h.hour_of_day,
                h.typical_throughput,
                h.throughput_variance,
                d.day_of_week,
                d.typical_daily_throughput,
                h.typical_throughput / nullIf(d.typical_daily_throughput, 0) as hourly_to_daily_ratio
                FROM hourly_patterns h
                CROSS JOIN daily_patterns d
                ORDER BY h.hour_of_day, d.day_of_week
                """""

                is_valid, error = validate_clickhouse_query(seasonal_query)
                assert is_valid, f"Seasonal pattern query failed: {error}"

                def test_trend_analysis_with_regression(self):
                    """Test trend analysis using linear regression"""
                    trend_query = """
                    WITH time_indexed_data AS (
                    SELECT 
                    toStartOfHour(timestamp) as hour,
                    avg(arrayElement(metrics.value,
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency,
                    row_number() OVER (ORDER BY toStartOfHour(timestamp)) as time_index
                    FROM workload_events
                    WHERE timestamp >= now() - INTERVAL 7 DAY
                    AND arrayExists(x -> x = 'latency_ms', metrics.name)
                    GROUP BY hour
                    HAVING count() > 5
                    ),
                    regression_stats AS (
                    SELECT 
                    count() as n,
                    sum(time_index) as sum_x,
                    sum(avg_latency) as sum_y,
                    sum(time_index * avg_latency) as sum_xy,
                    sum(time_index * time_index) as sum_x2
                    FROM time_indexed_data
                    )
                    SELECT 
                    -- Linear regression: y = mx + b
                    (n * sum_xy - sum_x * sum_y) / nullIf(n * sum_x2 - sum_x * sum_x, 0) as slope,
                    (sum_y - slope * sum_x) / nullIf(n, 0) as intercept,
                    CASE 
                    WHEN slope > 0 THEN 'increasing'
                    WHEN slope < 0 THEN 'decreasing'
                    ELSE 'stable'
                    END as trend_direction,
                    abs(slope) as trend_magnitude
                    FROM regression_stats
                    CROSS JOIN (SELECT slope FROM regression_stats LIMIT 1) s
                    """""

                    is_valid, error = validate_clickhouse_query(trend_query)
                    assert is_valid, f"Trend analysis query failed: {error}"

                    def test_forecast_calculation(self):
                        """Test simple forecasting based on historical data"""
                        forecast_query = """
                        WITH recent_data AS (
                        SELECT 
                        toStartOfHour(timestamp) as hour,
                        avg(arrayElement(metrics.value,
                        arrayFirstIndex(x -> x = 'cpu_usage', metrics.name))) as avg_cpu_usage
                        FROM workload_events
                        WHERE timestamp >= now() - INTERVAL 48 HOUR
                        AND arrayExists(x -> x = 'cpu_usage', metrics.name)
                        GROUP BY hour
                        ORDER BY hour
                        ),
                        moving_averages AS (
                        SELECT 
                        hour,
                        avg_cpu_usage,
                        avg(avg_cpu_usage) OVER (
                        ORDER BY hour 
                        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
                        ) as ma_12h,
                        avg(avg_cpu_usage) OVER (
                        ORDER BY hour 
                        ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
                        ) as ma_24h
                        FROM recent_data
                        ),
                        forecast_base AS (
                        SELECT 
                        max(hour) as last_hour,
                        argMax(ma_12h, hour) as latest_12h_avg,
                        argMax(ma_24h, hour) as latest_24h_avg,
                        stddevPop(avg_cpu_usage) as usage_volatility
                        FROM moving_averages
                        )
                        SELECT 
                        last_hour,
                        latest_12h_avg as short_term_forecast,
                        latest_24h_avg as long_term_forecast,
                        latest_12h_avg + usage_volatility as upper_bound_forecast,
                        latest_12h_avg - usage_volatility as lower_bound_forecast,
                        usage_volatility as forecast_uncertainty
                        FROM forecast_base
                        """""

                        is_valid, error = validate_clickhouse_query(forecast_query)
                        assert is_valid, f"Forecast calculation query failed: {error}"

                        def test_change_point_detection(self):
                            """Test detection of significant changes in metrics"""
                            change_point_query = """
                            WITH windowed_metrics AS (
                            SELECT 
                            toStartOfHour(timestamp) as hour,
                            avg(arrayElement(metrics.value,
                            arrayFirstIndex(x -> x = 'error_rate', metrics.name))) as avg_error_rate,
                            lag(avg(arrayElement(metrics.value,
                            arrayFirstIndex(x -> x = 'error_rate', metrics.name))), 1) OVER (ORDER BY toStartOfHour(timestamp)) as prev_error_rate,
                            lag(avg(arrayElement(metrics.value,
                            arrayFirstIndex(x -> x = 'error_rate', metrics.name))), 6) OVER (ORDER BY toStartOfHour(timestamp)) as error_rate_6h_ago
                            FROM workload_events
                            WHERE timestamp >= now() - INTERVAL 24 HOUR
                            AND arrayExists(x -> x = 'error_rate', metrics.name)
                            GROUP BY hour
                            )
                            SELECT 
                            hour,
                            avg_error_rate,
                            prev_error_rate,
                            error_rate_6h_ago,
                            avg_error_rate - prev_error_rate as hour_change,
                            avg_error_rate - error_rate_6h_ago as six_hour_change,
                            CASE 
                            WHEN abs(avg_error_rate - prev_error_rate) > 0.05 THEN 'significant_hourly_change'
                            WHEN abs(avg_error_rate - error_rate_6h_ago) > 0.1 THEN 'significant_trend_change'
                            ELSE 'normal'
                            END as change_classification
                            FROM windowed_metrics
                            WHERE prev_error_rate IS NOT NULL
                            ORDER BY hour DESC
                            """""

                            is_valid, error = validate_clickhouse_query(change_point_query)
                            assert is_valid, f"Change point detection query failed: {error}"