"""
Multi-Source Aggregation Tests
Test aggregation across multiple data sources
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

class TestMultiSourceCorrelation:
    """Test correlation analysis across multiple data sources"""

    def test_cross_table_correlation(self):
        """Test correlation analysis across multiple tables"""
        query = """
        WITH llm_metrics AS (
        SELECT 
        toStartOfMinute(timestamp) as minute,
        avg(latency_ms) as avg_llm_latency,
        sum(cost_cents) as total_cost,
        count() as llm_requests
        FROM llm_events
        WHERE timestamp >= now() - INTERVAL 1 HOUR
        GROUP BY minute
        ),
        workload_metrics AS (
        SELECT 
        toStartOfMinute(timestamp) as minute,
        avg(IF(arrayExists(x -> x = 'latency_ms', metrics.name),
        arrayElement(metrics.value, 
        arrayFirstIndex(x -> x = 'latency_ms', metrics.name)),
        0)) as avg_workload_latency,
        count() as workload_events
        FROM workload_events
        WHERE timestamp >= now() - INTERVAL 1 HOUR
        GROUP BY minute
        ),
        log_metrics AS (
        SELECT 
        toStartOfMinute(timestamp) as minute,
        countIf(level = 'ERROR') as error_count,
        countIf(level = 'WARNING') as warning_count
        FROM netra_app_internal_logs
        WHERE timestamp >= now() - INTERVAL 1 HOUR
        GROUP BY minute
        )
        SELECT 
        l.minute,
        l.avg_llm_latency,
        w.avg_workload_latency,
        l.total_cost,
        l.llm_requests,
        w.workload_events,
        lg.error_count,
        lg.warning_count,
        -- Calculate correlation coefficient manually
        corr(l.avg_llm_latency, w.avg_workload_latency) OVER () as latency_correlation
        FROM llm_metrics l
        FULL OUTER JOIN workload_metrics w ON l.minute = w.minute
        FULL OUTER JOIN log_metrics lg ON l.minute = lg.minute
        ORDER BY l.minute DESC
        """""

        # Fix array syntax if needed
        fixed_query = fix_clickhouse_array_syntax(query)
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Multi-source aggregation failed: {error}"

        def test_system_health_dashboard_query(self):
            """Test comprehensive system health dashboard query"""
            health_query = """
            SELECT 
            toStartOfMinute(timestamp) as minute,
            count() as workload_events_count,
            avg(duration_ms) as avg_workload_duration,
            CASE 
            WHEN avg(duration_ms) > 5000 THEN 'warning'
            ELSE 'healthy'
            END as health_status
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY minute
            ORDER BY minute DESC
            """""

            is_valid, error = validate_clickhouse_query(health_query)
            assert is_valid, f"System health dashboard query failed: {error}"

            def test_resource_utilization_across_sources(self):
                """Test resource utilization analysis across multiple sources"""
                utilization_query = """
                WITH resource_metrics AS (
                SELECT 
                toStartOfHour(timestamp) as hour,
                avg(IF(arrayExists(x -> x = 'cpu_usage', metrics.name),
                arrayElement(metrics.value, 
                arrayFirstIndex(x -> x = 'cpu_usage', metrics.name)), 0)) as avg_cpu,
                avg(IF(arrayExists(x -> x = 'memory_usage', metrics.name),
                arrayElement(metrics.value, 
                arrayFirstIndex(x -> x = 'memory_usage', metrics.name)), 0)) as avg_memory,
                count() as metric_samples
                FROM workload_events
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                AND (arrayExists(x -> x = 'cpu_usage', metrics.name) 
                OR arrayExists(x -> x = 'memory_usage', metrics.name))
                GROUP BY hour
                ),
                activity_metrics AS (
                SELECT 
                toStartOfHour(timestamp) as hour,
                count() as total_events,
                uniq(user_id) as unique_users,
                uniq(workload_type) as unique_workload_types
                FROM workload_events
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                GROUP BY hour
                ),
                error_metrics AS (
                SELECT 
                toStartOfHour(timestamp) as hour,
                countIf(level = 'ERROR') as error_count,
                countIf(level = 'WARNING') as warning_count,
                count() as total_logs
                FROM netra_app_internal_logs
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                GROUP BY hour
                )
                SELECT 
                r.hour,
                r.avg_cpu,
                r.avg_memory,
                a.total_events,
                a.unique_users,
                a.unique_workload_types,
                e.error_count,
                e.warning_count,
                -- Calculate efficiency metrics
                a.total_events / nullIf(r.avg_cpu, 0) as events_per_cpu_unit,
                a.unique_users / nullIf(r.avg_memory, 0) as users_per_memory_unit,
                e.error_count / nullIf(a.total_events, 0) as error_rate
                FROM resource_metrics r
                FULL OUTER JOIN activity_metrics a ON r.hour = a.hour
                FULL OUTER JOIN error_metrics e ON r.hour = e.hour
                ORDER BY r.hour DESC
                """""

                fixed_query = fix_clickhouse_array_syntax(utilization_query)
                is_valid, error = validate_clickhouse_query(fixed_query)
                assert is_valid, f"Resource utilization query failed: {error}"

                class TestBusinessMetricsAggregation:
                    """Test business metrics aggregation across sources"""

                    def test_business_metrics_aggregation(self):
                        """Test business metrics aggregation across technical sources"""
                        business_query = """
                        WITH user_activity AS (
                        SELECT 
                        toDate(timestamp) as date,
                        user_id,
                        count() as daily_requests,
                        uniq(workload_type) as workload_types_used,
                        avg(duration_ms) as avg_request_duration,
                        sum(duration_ms) as total_duration_ms
                        FROM workload_events
                        WHERE timestamp >= now() - INTERVAL 7 DAY
                        GROUP BY date, user_id
                        ),
                        user_costs AS (
                        SELECT 
                        toDate(timestamp) as date,
                        user_id,
                        sum(cost_cents) as daily_cost,
                        count() as llm_requests,
                        sum(input_tokens + output_tokens) as daily_tokens
                        FROM llm_events
                        WHERE timestamp >= now() - INTERVAL 7 DAY
                        GROUP BY date, user_id
                        ),
                        user_issues AS (
                        SELECT 
                        toDate(timestamp) as date,
                        JSONExtractInt(metadata, 'user_id') as user_id,
                        countIf(level = 'ERROR') as daily_errors,
                        countIf(level = 'WARNING') as daily_warnings
                        FROM netra_app_internal_logs
                        WHERE timestamp >= now() - INTERVAL 7 DAY
                        AND JSONExtractInt(metadata, 'user_id') > 0
                        GROUP BY date, user_id
                        )
                        SELECT 
                        ua.date,
                        ua.user_id,
                        ua.daily_requests,
                        ua.workload_types_used,
                        ua.avg_request_duration,
                        uc.daily_cost,
                        uc.llm_requests,
                        uc.daily_tokens,
                        ui.daily_errors,
                        ui.daily_warnings,
                        -- Business KPIs
                        uc.daily_cost / nullIf(ua.daily_requests, 0) as cost_per_request,
                        uc.daily_tokens / nullIf(uc.llm_requests, 0) as avg_tokens_per_llm_request,
                        ui.daily_errors / nullIf(ua.daily_requests, 0) as error_rate,
                        -- User engagement score
                        (ua.workload_types_used * 10 + ua.daily_requests - ui.daily_errors * 5) as engagement_score
                        FROM user_activity ua
                        LEFT JOIN user_costs uc ON ua.date = uc.date AND ua.user_id = uc.user_id
                        LEFT JOIN user_issues ui ON ua.date = ui.date AND ua.user_id = ui.user_id
                        ORDER BY ua.date DESC, engagement_score DESC
                        """""

                        is_valid, error = validate_clickhouse_query(business_query)
                        assert is_valid, f"Business metrics aggregation failed: {error}"

                        def test_performance_impact_correlation(self):
                            """Test correlation between performance metrics and business outcomes"""
                            impact_query = """
                            WITH performance_periods AS (
                            SELECT 
                            toStartOfHour(timestamp) as hour,
                            avg(duration_ms) as avg_duration,
                            quantile(0.95)(duration_ms) as p95_duration,
                            count() as request_volume,
                            uniq(user_id) as active_users
                            FROM workload_events
                            WHERE timestamp >= now() - INTERVAL 48 HOUR
                            GROUP BY hour
                            ),
                            error_periods AS (
                            SELECT 
                            toStartOfHour(timestamp) as hour,
                            countIf(level = 'ERROR') as error_count,
                            count() as total_logs,
                            uniq(component) as affected_components
                            FROM netra_app_internal_logs
                            WHERE timestamp >= now() - INTERVAL 48 HOUR
                            GROUP BY hour
                            ),
                            cost_periods AS (
                            SELECT 
                            toStartOfHour(timestamp) as hour,
                            sum(cost_cents) as total_cost,
                            avg(latency_ms) as avg_llm_latency,
                            count() as llm_volume
                            FROM llm_events
                            WHERE timestamp >= now() - INTERVAL 48 HOUR
                            GROUP BY hour
                            )
                            SELECT 
                            p.hour,
                            p.avg_duration,
                            p.p95_duration,
                            p.request_volume,
                            p.active_users,
                            e.error_count,
                            e.affected_components,
                            c.total_cost,
                            c.avg_llm_latency,
                            c.llm_volume,
                            -- Impact correlations
                            CASE 
                            WHEN p.avg_duration > 3000 AND e.error_count > 5 THEN 'high_impact_period'
                            WHEN p.avg_duration > 1500 OR e.error_count > 2 THEN 'medium_impact_period'
                            ELSE 'normal_period'
                            END as impact_classification,
                            -- Performance cost ratio
                            c.total_cost / nullIf(p.request_volume, 0) as cost_per_request,
                            e.error_count / nullIf(p.request_volume, 0) as error_rate_ratio
                            FROM performance_periods p
                            LEFT JOIN error_periods e ON p.hour = e.hour
                            LEFT JOIN cost_periods c ON p.hour = c.hour
                            ORDER BY p.hour DESC
                            """""

                            is_valid, error = validate_clickhouse_query(impact_query)
                            assert is_valid, f"Performance impact correlation failed: {error}"