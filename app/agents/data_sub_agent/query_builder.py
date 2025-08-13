"""Query builder for ClickHouse queries."""

from datetime import datetime, timedelta
from typing import Optional


class QueryBuilder:
    """Build optimized ClickHouse queries"""
    
    @staticmethod
    def build_performance_metrics_query(
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation_level: str = "minute"
    ) -> str:
        """Build query for performance metrics"""
        
        time_function = {
            "second": "toStartOfSecond",
            "minute": "toStartOfMinute",
            "hour": "toStartOfHour",
            "day": "toStartOfDay"
        }.get(aggregation_level, "toStartOfMinute")
        
        workload_filter = f"AND workload_id = '{workload_id}'" if workload_id else ""
        
        return f"""
        SELECT
            {time_function}(timestamp) as time_bucket,
            count() as event_count,
            quantileIf(0.5, metric_value, has_latency) as latency_p50,
            quantileIf(0.95, metric_value, has_latency) as latency_p95,
            quantileIf(0.99, metric_value, has_latency) as latency_p99,
            avgIf(throughput_value, has_throughput) as avg_throughput,
            maxIf(throughput_value, has_throughput) as peak_throughput,
            countIf(event_type = 'error') / count() * 100 as error_rate,
            sumIf(cost_value, has_cost) / 100.0 as total_cost,
            uniqExact(workload_id) as unique_workloads
        FROM (
            SELECT
                *,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as idx,
                arrayFirstIndex(x -> x = 'throughput', metrics.name) as idx2,
                arrayFirstIndex(x -> x = 'cost_cents', metrics.name) as idx3,
                if(idx > 0, arrayElement(metrics.value, idx), 0.0) as metric_value,
                if(idx2 > 0, arrayElement(metrics.value, idx2), 0.0) as throughput_value,
                if(idx3 > 0, arrayElement(metrics.value, idx3), 0.0) as cost_value,
                idx > 0 as has_latency,
                idx2 > 0 as has_throughput,
                idx3 > 0 as has_cost
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= '{start_time.isoformat()}'
                AND timestamp <= '{end_time.isoformat()}'
                {workload_filter}
        )
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT 10000
        """
    
    @staticmethod
    def build_anomaly_detection_query(
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float = 2.0
    ) -> str:
        """Build query for anomaly detection"""
        
        return f"""
        WITH baseline AS (
            SELECT
                arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as idx,
                avg(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as mean_val,
                stddevPop(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as std_val
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= '{(start_time - timedelta(days=7)).isoformat()}'
                AND timestamp < '{start_time.isoformat()}'
        )
        SELECT
            timestamp,
            arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as idx,
            if(idx > 0, arrayElement(metrics.value, idx), 0.0) as metric_value,
            (metric_value - baseline.mean_val) / baseline.std_val as z_score,
            abs(z_score) > {z_score_threshold} as is_anomaly
        FROM workload_events, baseline
        WHERE user_id = {user_id}
            AND timestamp >= '{start_time.isoformat()}'
            AND timestamp <= '{end_time.isoformat()}'
            AND is_anomaly = 1
        ORDER BY abs(z_score) DESC
        LIMIT 100
        """
    
    @staticmethod
    def build_correlation_analysis_query(
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build query for correlation analysis between two metrics"""
        
        return f"""
        SELECT
            corr(m1_value, m2_value) as correlation_coefficient,
            count() as sample_size,
            avg(m1_value) as metric1_avg,
            avg(m2_value) as metric2_avg,
            stddevPop(m1_value) as metric1_std,
            stddevPop(m2_value) as metric2_std
        FROM (
            SELECT
                arrayFirstIndex(x -> x = '{metric1}', metrics.name) as idx1,
                arrayFirstIndex(x -> x = '{metric2}', metrics.name) as idx2,
                if(idx1 > 0, arrayElement(metrics.value, idx1), 0.0) as m1_value,
                if(idx2 > 0, arrayElement(metrics.value, idx2), 0.0) as m2_value
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= '{start_time.isoformat()}'
                AND timestamp <= '{end_time.isoformat()}'
                AND idx1 > 0 AND idx2 > 0
        )
        """
    
    @staticmethod
    def build_usage_patterns_query(
        user_id: int,
        days_back: int = 30
    ) -> str:
        """Build query for usage pattern analysis"""
        
        return f"""
        SELECT
            toDayOfWeek(timestamp) as day_of_week,
            toHour(timestamp) as hour_of_day,
            count() as event_count,
            uniqExact(workload_id) as unique_workloads,
            uniqExact(model_name) as unique_models,
            sumIf(cost_value, has_cost) / 100.0 as total_cost
        FROM (
            SELECT
                *,
                arrayFirstIndex(x -> x = 'cost_cents', metrics.name) as idx,
                if(idx > 0, arrayElement(metrics.value, idx), 0.0) as cost_value,
                idx > 0 as has_cost
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= now() - INTERVAL {days_back} DAY
        )
        GROUP BY day_of_week, hour_of_day
        ORDER BY day_of_week, hour_of_day
        """