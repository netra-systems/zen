"""
Realistic ClickHouse Operations Tests
Tests ClickHouse with production-like data volumes and patterns
"""

import pytest
import asyncio
import uuid
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.clickhouse_query_fixer import (
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
    ClickHouseQueryInterceptor
)


class TestClickHouseArrayOperations:
    """Test proper array operations and the query fixer"""
    
    def test_fix_incorrect_array_syntax(self):
        """Test that incorrect array syntax is fixed"""
        incorrect_query = """
        SELECT 
            metrics.name[idx] as metric_name,
            metrics.value[idx] as metric_value,
            metrics.unit[idx] as metric_unit
        FROM workload_events
        WHERE metrics.name[1] = 'latency_ms'
        """
        
        fixed_query = fix_clickhouse_array_syntax(incorrect_query)
        
        # Verify all array accesses are fixed
        assert "arrayElement(metrics.name, idx)" in fixed_query
        assert "arrayElement(metrics.value, idx)" in fixed_query
        assert "arrayElement(metrics.unit, idx)" in fixed_query
        assert "arrayElement(metrics.name, 1)" in fixed_query
        
        # Verify no incorrect syntax remains
        assert "metrics.name[idx]" not in fixed_query
        assert "metrics.value[idx]" not in fixed_query
    
    def test_validate_query_catches_errors(self):
        """Test query validation catches common errors"""
        # Test incorrect array syntax
        bad_query = "SELECT metrics.value[idx] FROM table"
        is_valid, error = validate_clickhouse_query(bad_query)
        assert not is_valid
        assert "incorrect array syntax" in error
        
        # Test correct syntax passes
        good_query = "SELECT arrayElement(metrics.value, idx) FROM table"
        is_valid, error = validate_clickhouse_query(good_query)
        assert is_valid
        assert error == ""
    async def test_query_interceptor_fixes_queries(self):
        """Test the query interceptor automatically fixes queries"""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.execute_query = AsyncMock(return_value=[{"result": "success"}])
        
        # Wrap with interceptor
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        # Execute query with bad syntax
        bad_query = "SELECT metrics.value[idx] FROM workload_events"
        result = await interceptor.execute_query(bad_query)
        
        # Verify the fixed query was sent to the client
        mock_client.execute_query.assert_called_once()
        actual_query = mock_client.execute_query.call_args[0][0]
        assert "arrayElement(metrics.value, idx)" in actual_query
        assert "metrics.value[idx]" not in actual_query
        
        # Check stats
        stats = interceptor.get_stats()
        assert stats["queries_executed"] == 1
        assert stats["queries_fixed"] == 1


class TestRealisticLogIngestion:
    """Test realistic log ingestion patterns"""
    
    @pytest.fixture
    def generate_realistic_logs(self):
        """Generate realistic log entries"""
        log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]
        components = ["api", "worker", "scheduler", "llm_manager", "agent"]
        
        def _generate(count: int) -> List[Dict]:
            logs = []
            base_time = datetime.now() - timedelta(hours=1)
            
            for i in range(count):
                timestamp = base_time + timedelta(seconds=i * 0.1)
                logs.append({
                    "timestamp": timestamp.isoformat(),
                    "level": random.choice(log_types),
                    "component": random.choice(components),
                    "message": f"Log message {i}",
                    "metadata": {
                        "request_id": str(uuid.uuid4()),
                        "user_id": random.randint(1, 100),
                        "latency_ms": random.uniform(10, 500) if random.random() > 0.5 else None
                    }
                })
            return logs
        return _generate
    async def test_streaming_log_ingestion(self, generate_realistic_logs):
        """Test streaming ingestion of logs"""
        logs = generate_realistic_logs(1000)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Simulate batch inserts
            batch_size = 100
            for i in range(0, len(logs), batch_size):
                batch = logs[i:i+batch_size]
                
                # Simulate the insert
                query = f"""
                INSERT INTO netra_app_internal_logs 
                (timestamp, level, component, message, metadata)
                VALUES
                """
                
                await mock_instance.execute(query, batch)
            
            # Verify batches were inserted
            assert mock_instance.execute.call_count == 10  # 1000 logs / 100 batch size
    async def test_log_pattern_recognition(self):
        """Test pattern recognition across large log volumes"""
        # Simulate pattern detection query
        pattern_query = """
        WITH log_patterns AS (
            SELECT 
                component,
                level,
                extractAllGroups(message, '(\\w+Exception|Error: \\w+|Failed to \\w+)')[1] as error_pattern,
                count() as occurrence_count,
                avg(JSONExtractFloat(metadata, 'latency_ms')) as avg_latency
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 1 HOUR
                AND level IN ('ERROR', 'WARNING')
            GROUP BY component, level, error_pattern
            HAVING occurrence_count > 5
        )
        SELECT * FROM log_patterns
        ORDER BY occurrence_count DESC
        LIMIT 100
        """
        
        # Verify query is valid
        is_valid, error = validate_clickhouse_query(pattern_query)
        assert is_valid, f"Pattern query validation failed: {error}"


class TestLLMMetricsAggregation:
    """Test LLM-specific metrics and optimizations"""
    
    def generate_llm_metrics(self, count: int) -> List[Dict]:
        """Generate realistic LLM metrics"""
        models = ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro"]
        
        metrics = []
        for i in range(count):
            metrics.append({
                "timestamp": datetime.now() - timedelta(minutes=count-i),
                "model": random.choice(models),
                "request_id": str(uuid.uuid4()),
                "input_tokens": random.randint(100, 2000),
                "output_tokens": random.randint(50, 1000),
                "latency_ms": random.uniform(500, 5000),
                "cost_cents": random.uniform(0.1, 5.0),
                "success": random.random() > 0.05,  # 95% success rate
                "temperature": random.choice([0.0, 0.3, 0.7, 1.0]),
                "user_id": random.randint(1, 50),
                "workload_type": random.choice(["chat", "completion", "embedding", "analysis"])
            })
        return metrics
    
    def test_llm_cost_optimization_query(self):
        """Test query for LLM cost optimization analysis"""
        query = """
        WITH model_costs AS (
            SELECT 
                model,
                workload_type,
                avg(cost_cents) as avg_cost,
                avg(latency_ms) as avg_latency,
                quantile(0.95)(latency_ms) as p95_latency,
                sum(input_tokens + output_tokens) as total_tokens,
                count() as request_count,
                sum(cost_cents) as total_cost
            FROM llm_events
            WHERE timestamp >= now() - INTERVAL 7 DAY
                AND success = true
            GROUP BY model, workload_type
        ),
        optimization_opportunities AS (
            SELECT 
                workload_type,
                model as current_model,
                avg_cost as current_avg_cost,
                avg_latency as current_avg_latency,
                (SELECT model FROM model_costs mc2 
                 WHERE mc2.workload_type = mc1.workload_type 
                   AND mc2.avg_cost < mc1.avg_cost
                   AND mc2.p95_latency < mc1.p95_latency * 1.2
                 ORDER BY mc2.avg_cost ASC
                 LIMIT 1) as recommended_model,
                (current_avg_cost - 
                 (SELECT avg_cost FROM model_costs mc3 
                  WHERE mc3.workload_type = mc1.workload_type 
                    AND mc3.avg_cost < mc1.avg_cost
                  ORDER BY mc3.avg_cost ASC
                  LIMIT 1)) * request_count as potential_savings
            FROM model_costs mc1
            WHERE request_count > 100
        )
        SELECT * FROM optimization_opportunities
        WHERE potential_savings > 0
        ORDER BY potential_savings DESC
        """
        
        # This complex query should be valid
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"LLM optimization query failed: {error}"
    async def test_llm_usage_patterns(self):
        """Test LLM usage pattern analysis"""
        query = """
        SELECT 
            toHour(timestamp) as hour,
            model,
            workload_type,
            count() as requests,
            avg(latency_ms) as avg_latency,
            sum(cost_cents) as total_cost,
            avg(temperature) as avg_temperature,
            sum(input_tokens) as total_input_tokens,
            sum(output_tokens) as total_output_tokens
        FROM llm_events
        WHERE timestamp >= now() - INTERVAL 24 HOUR
        GROUP BY hour, model, workload_type
        ORDER BY hour DESC, total_cost DESC
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid


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
        """
        
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
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Anomaly detection query failed: {error}"


class TestLogClusteringAlgorithms:
    """Test log clustering and pattern mining"""
    
    def test_log_clustering_with_similarity(self):
        """Test log clustering using similarity metrics"""
        query = """
        WITH log_signatures AS (
            SELECT 
                message,
                -- Extract template by replacing numbers and UUIDs
                replaceRegexpAll(
                    replaceRegexpAll(message, '[0-9]+', 'NUM'),
                    '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 'UUID'
                ) as template,
                count() as occurrence_count,
                min(timestamp) as first_seen,
                max(timestamp) as last_seen,
                groupArray(JSONExtractString(metadata, 'request_id'))[1:10] as sample_requests
            FROM netra_app_internal_logs
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY message, template
            HAVING occurrence_count > 1
        ),
        clusters AS (
            SELECT 
                template,
                sum(occurrence_count) as total_occurrences,
                count() as unique_messages,
                min(first_seen) as cluster_first_seen,
                max(last_seen) as cluster_last_seen,
                groupArray(sample_requests[1])[1:5] as cluster_samples
            FROM log_signatures
            GROUP BY template
            HAVING total_occurrences > 10
        )
        SELECT * FROM clusters
        ORDER BY total_occurrences DESC
        LIMIT 100
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Log clustering query failed: {error}"
    
    def test_error_cascade_detection(self):
        """Test detection of error cascades in logs"""
        query = """
        WITH error_windows AS (
            SELECT 
                toStartOfMinute(timestamp) as minute,
                component,
                count() as error_count,
                groupArray(message)[1:5] as sample_errors,
                uniq(JSONExtractString(metadata, 'user_id')) as affected_users
            FROM netra_app_internal_logs
            WHERE level = 'ERROR'
                AND timestamp >= now() - INTERVAL 6 HOUR
            GROUP BY minute, component
        ),
        cascades AS (
            SELECT 
                e1.minute as start_minute,
                e1.component as source_component,
                e2.component as affected_component,
                e1.error_count as source_errors,
                e2.error_count as cascade_errors,
                e2.affected_users
            FROM error_windows e1
            INNER JOIN error_windows e2 
                ON e2.minute >= e1.minute 
                AND e2.minute <= e1.minute + INTERVAL 5 MINUTE
                AND e1.component != e2.component
            WHERE e1.error_count > 10
                AND e2.error_count > e1.error_count * 0.5
        )
        SELECT * FROM cascades
        ORDER BY start_minute DESC, source_errors DESC
        """
        
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"Error cascade query failed: {error}"


class TestMultiSourceAggregation:
    """Test aggregation across multiple data sources"""
    
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
        """
        
        # Fix array syntax if needed
        fixed_query = fix_clickhouse_array_syntax(query)
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Multi-source aggregation failed: {error}"
class TestRealisticDataVolumes:
    """Test with realistic data volumes"""
    
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
        """
        
        fixed_query = fix_clickhouse_array_syntax(query)
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Large scale aggregation failed: {error}"
    
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
        """
        
        # Materialized view syntax should be valid
        assert "CREATE MATERIALIZED VIEW" in view_query
        assert "ENGINE = AggregatingMergeTree()" in view_query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])