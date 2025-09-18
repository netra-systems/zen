"""
ClickHouse Multi-Source Aggregation and Large Volume Tests
Tests cross-table correlation and realistic data volumes
"""

import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
)

class TestMultiSourceAggregation:
    """Test aggregation across multiple data sources"""
    
    def _get_llm_metrics_cte(self):
        """Get LLM metrics CTE query part"""
        return """llm_metrics AS (
            SELECT 
                toStartOfMinute(timestamp) as minute,
                avg(latency_ms) as avg_llm_latency,
                sum(cost_cents) as total_cost,
                count() as llm_requests
            FROM llm_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY minute
        )"""

    def _get_workload_metrics_cte(self):
        """Get workload metrics CTE query part"""
        return """workload_metrics AS (
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
        )"""

    def _get_log_metrics_cte(self):
        """Get log metrics CTE query part"""
        return """log_metrics AS (
            SELECT 
                toStartOfMinute(timestamp) as minute,
                countIf(level = 'ERROR') as error_count,
                countIf(level = 'WARNING') as warning_count
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY minute
        )"""

    def _get_correlation_select(self):
        """Get correlation SELECT query part"""
        return """SELECT 
            l.minute,
            l.avg_llm_latency,
            w.avg_workload_latency,
            l.total_cost,
            l.llm_requests,
            w.workload_events,
            lg.error_count,
            lg.warning_count,
            corr(l.avg_llm_latency, w.avg_workload_latency) OVER () as latency_correlation
        FROM llm_metrics l
        FULL OUTER JOIN workload_metrics w ON l.minute = w.minute
        FULL OUTER JOIN log_metrics lg ON l.minute = lg.minute
        ORDER BY l.minute DESC"""

    def _create_cross_table_correlation_query(self):
        """Create the cross-table correlation query"""
        llm_cte = self._get_llm_metrics_cte()
        workload_cte = self._get_workload_metrics_cte()
        log_cte = self._get_log_metrics_cte()
        select_part = self._get_correlation_select()
        return f"WITH {llm_cte},\n{workload_cte},\n{log_cte}\n{select_part}"

    def _fix_query_syntax(self, query):
        """Fix array syntax in query if needed"""
        return fix_clickhouse_array_syntax(query)

    def _validate_cross_table_query(self, fixed_query):
        """Validate the cross-table correlation query"""
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Multi-source aggregation failed: {error}"

    def test_cross_table_correlation(self):
        """Test correlation analysis across multiple tables"""
        query = self._create_cross_table_correlation_query()
        fixed_query = self._fix_query_syntax(query)
        self._validate_cross_table_query(fixed_query)

class TestRealisticDataVolumes:
    """Test with realistic data volumes"""
    
    def _get_large_scale_query(self):
        """Get large scale aggregation query"""
        return """
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
        """

    def _validate_large_scale_query(self, query):
        """Validate large scale aggregation query"""
        fixed_query = fix_clickhouse_array_syntax(query)
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Large scale aggregation failed: {error}"

    async def test_large_scale_aggregation(self):
        """Test aggregation over large data volumes"""
        query = self._get_large_scale_query()
        self._validate_large_scale_query(query)
    
    def _get_materialized_view_query(self):
        """Get materialized view creation query"""
        return """
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
        """

    def _validate_materialized_view_syntax(self, view_query):
        """Validate materialized view syntax"""
        assert "CREATE MATERIALIZED VIEW" in view_query
        assert "ENGINE = AggregatingMergeTree()" in view_query

    async def test_materialized_view_creation(self):
        """Test creation of materialized views for performance"""
        view_query = self._get_materialized_view_query()
        self._validate_materialized_view_syntax(view_query)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])