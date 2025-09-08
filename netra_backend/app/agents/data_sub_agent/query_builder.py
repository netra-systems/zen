"""Query Builder Compatibility Module

Simple compatibility wrapper for legacy QueryBuilder imports.
Provides backward compatibility for test cases requiring query building.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class QueryBuilder:
    """Legacy QueryBuilder for backward compatibility.
    
    Provides query building methods for test cases.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def build_performance_metrics_query(
        user_id: Optional[int] = None,
        workload_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation_level: str = "hour",
        # Backward compatibility parameters
        timeframe: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ) -> str:
        """Build a performance metrics query with proper nested array handling.
        
        Args:
            user_id: User ID to filter by
            workload_id: Optional workload ID filter
            start_time: Start time filter
            end_time: End time filter 
            aggregation_level: Time aggregation level (second, minute, hour, day)
            timeframe: Backward compatibility - time window (24h, 7d, etc.)
            metrics: Backward compatibility - list of metrics to include
        
        Returns:
            ClickHouse SQL query string with nested array handling
        """
        # Handle backward compatibility
        if timeframe is not None:
            # Convert timeframe to time filters
            if timeframe == "24h":
                start_time = datetime.now() - timedelta(hours=24)
                end_time = datetime.now()
            elif timeframe == "7d":
                start_time = datetime.now() - timedelta(days=7)
                end_time = datetime.now()
            elif timeframe == "365d":
                start_time = datetime.now() - timedelta(days=365)
                end_time = datetime.now()
            else:
                start_time = datetime.now() - timedelta(hours=1)
                end_time = datetime.now()
        
        # Ensure we have a user_id for the query
        if user_id is None:
            user_id = 1  # Default for backward compatibility
        
        # Map aggregation levels to ClickHouse functions
        aggregation_funcs = {
            "second": "toStartOfSecond",
            "minute": "toStartOfMinute", 
            "hour": "toStartOfHour",
            "day": "toStartOfDay"
        }
        
        time_func = aggregation_funcs.get(aggregation_level, "toStartOfHour")
        
        # Build time filters if provided
        time_filters = []
        if start_time:
            time_filters.append(f"timestamp >= '{start_time.isoformat()}'")
        if end_time:
            time_filters.append(f"timestamp <= '{end_time.isoformat()}'")
        
        time_filter = " AND ".join(time_filters) if time_filters else "1=1"
        
        # Optional workload filter
        workload_filter = f" AND workload_id = '{workload_id}'" if workload_id else ""
        
        query = f"""
        SELECT 
            {time_func}(timestamp) as time_bucket,
            arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as latency_idx,
            if(idx > 0, arrayElement(metrics.value, idx), 0) as latency_value,
            has(metrics.name, 'latency_ms') as has_latency,
            has(metrics.name, 'throughput') as has_throughput,
            avg(metric_value) as avg_latency,
            quantileIf(0.5, metric_value, has_latency) as latency_p50,
            quantileIf(0.95, metric_value, has_latency) as latency_p95,
            quantileIf(0.99, metric_value, has_latency) as latency_p99,
            avgIf(throughput_value, has_throughput) as avg_throughput,
            count(*) as total_requests
        FROM (
            SELECT 
                timestamp,
                metrics,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as idx,
                if(arrayFirstIndex(x -> x = 'latency_ms', metrics.name) > 0, 
                   arrayElement(metrics.value, arrayFirstIndex(x -> x = 'latency_ms', metrics.name)), 
                   0) as metric_value,
                if(arrayFirstIndex(x -> x = 'throughput', metrics.name) > 0, 
                   arrayElement(metrics.value, arrayFirstIndex(x -> x = 'throughput', metrics.name)), 
                   0) as throughput_value
            FROM workload_events 
            WHERE user_id = {user_id}
            AND {time_filter}
            {workload_filter}
        )
        WHERE idx > 0
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT 10000
        """
        
        return query.strip()
    
    @staticmethod
    def build_usage_patterns_query(
        user_id: int,
        days_back: int = 90
    ) -> str:
        """Build a usage patterns query with time-based filtering.
        
        Args:
            user_id: User ID to filter by
            days_back: Number of days to look back
        
        Returns:
            ClickHouse SQL query with proper time grouping
        """
        query = f"""
        SELECT 
            toHour(timestamp) as hour_of_day,
            toDayOfWeek(timestamp) as day_of_week,
            count() as event_count,
            uniqExact(workload_id) as unique_workloads,
            uniqExact(model_name) as unique_models,
            avg(if(arrayFirstIndex(x -> x = 'latency_ms', metrics.name) > 0,
                   arrayElement(metrics.value, arrayFirstIndex(x -> x = 'latency_ms', metrics.name)),
                   0)) as avg_latency
        FROM workload_events 
        WHERE user_id = {user_id}
        AND timestamp >= now() - INTERVAL {days_back} DAY
        GROUP BY day_of_week, hour_of_day
        ORDER BY day_of_week, hour_of_day
        """
        
        return query.strip()
    
    @staticmethod
    def build_anomaly_detection_query(
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float = 2.0
    ) -> str:
        """Build anomaly detection query with proper baseline calculation and null handling.
        
        Args:
            user_id: User ID to filter by
            metric_name: Name of metric to analyze
            start_time: Analysis start time
            end_time: Analysis end time
            z_score_threshold: Z-score threshold for anomaly detection
        
        Returns:
            ClickHouse SQL query with CTEs and nullIf handling
        """
        # Calculate baseline window (7 days back from start_time)
        baseline_start = start_time - timedelta(days=7)
        baseline_start_iso = baseline_start.isoformat()
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        
        query = f"""
        WITH baseline AS (
            SELECT 
                avg(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as mean_val,
                stddevPop(if(idx > 0, arrayElement(metrics.value, idx), 0.0)) as std_val
            FROM (
                SELECT 
                    arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as idx,
                    metrics
                FROM workload_events 
                WHERE user_id = {user_id}
                AND timestamp >= '{baseline_start_iso}'
                AND timestamp < '{start_time_iso}'
            )
            WHERE idx > 0
        ),
        baseline_stats AS (
            SELECT 
                mean_val,
                nullIf(std_val, 0) as std_value
            FROM baseline
        )
        SELECT 
            timestamp,
            arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as metric_idx,
            if(metric_idx > 0, arrayElement(metrics.value, metric_idx), 0) as metric_value,
            baseline_stats.mean_val,
            baseline_stats.std_value,
            nullIf(baseline_stats.std_value, 0) as safe_std_val,
            (metric_value - baseline_stats.mean_val) / baseline.std_val as z_score,
            abs(z_score) > {z_score_threshold} as is_anomaly
        FROM workload_events, baseline_stats, baseline
        WHERE user_id = {user_id}
        AND timestamp >= '{start_time_iso}'
        AND timestamp <= '{end_time_iso}'
        AND arrayFirstIndex(x -> x = '{metric_name}', metrics.name) > 0
        ORDER BY timestamp
        """
        
        return query.strip()
    
    @staticmethod
    def build_correlation_analysis_query(
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build correlation analysis query between two metrics.
        
        Args:
            user_id: User ID to filter by
            metric1: First metric name
            metric2: Second metric name
            start_time: Analysis start time
            end_time: Analysis end time
        
        Returns:
            ClickHouse SQL query for correlation analysis
        """
        query = f"""
        SELECT 
            arrayFirstIndex(x -> x = '{metric1}', metrics.name) as m1_idx,
            arrayFirstIndex(x -> x = '{metric2}', metrics.name) as m2_idx,
            if(m1_idx > 0, arrayElement(metrics.value, m1_idx), 0) as m1_value,
            if(m2_idx > 0, arrayElement(metrics.value, m2_idx), 0) as m2_value,
            corr(m1_value, m2_value) as correlation_coefficient,
            count(*) as sample_size
        FROM workload_events
        WHERE user_id = {user_id}
        AND timestamp >= '{start_time.isoformat()}'
        AND timestamp <= '{end_time.isoformat()}'
        AND arrayFirstIndex(x -> x = '{metric1}', metrics.name) > 0
        AND arrayFirstIndex(x -> x = '{metric2}', metrics.name) > 0
        """
        
        return query.strip()
    
    @staticmethod  
    def build_cost_analysis_query(
        timeframe: str = "24h",
        user_id: Optional[str] = None
    ) -> str:
        """Build a cost analysis query."""
        
        if timeframe == "24h":
            time_filter = "timestamp >= now() - interval 24 hour"
        elif timeframe == "7d":  
            time_filter = "timestamp >= now() - interval 7 day"
        else:
            time_filter = "timestamp >= now() - interval 1 hour"
        
        query = f"""
        SELECT 
            sum(cost_cents) / 100.0 as total_cost_dollars,
            sum(tokens_input + tokens_output) as total_tokens,
            avg(cost_cents) / 100.0 as avg_cost_per_request,
            count(*) as total_requests
        FROM cost_metrics 
        WHERE {time_filter}
        """
        
        if user_id:
            query += f" AND user_id = '{user_id}'"
        
        return query.strip()