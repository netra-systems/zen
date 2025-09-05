"""Query Builder Compatibility Module

Simple compatibility wrapper for legacy QueryBuilder imports.
Provides backward compatibility for test cases requiring query building.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class QueryBuilder:
    """Legacy QueryBuilder for backward compatibility.
    
    Provides query building methods for test cases.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def build_performance_metrics_query(
        timeframe: str = "24h", 
        metrics: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Build a performance metrics query."""
        base_metrics = metrics or ['latency_ms', 'throughput', 'success_rate']
        
        select_clause = ", ".join([f"avg({metric}) as {metric}" for metric in base_metrics])
        
        # Simple time filter based on timeframe
        if timeframe == "24h":
            time_filter = "timestamp >= now() - interval 24 hour"
        elif timeframe == "7d":
            time_filter = "timestamp >= now() - interval 7 day"
        else:
            time_filter = "timestamp >= now() - interval 1 hour"
        
        query = f"""
        SELECT 
            {select_clause},
            count(*) as total_requests
        FROM metrics 
        WHERE {time_filter}
        """
        
        if user_id:
            query += f" AND user_id = '{user_id}'"
        
        query += " GROUP BY toHour(timestamp) ORDER BY timestamp"
        
        return query.strip()
    
    @staticmethod
    def build_usage_patterns_query(
        timeframe: str = "24h",
        user_id: Optional[str] = None
    ) -> str:
        """Build a usage patterns query."""
        
        if timeframe == "24h":
            time_filter = "timestamp >= now() - interval 24 hour"
            group_by = "toHour(timestamp)"
        elif timeframe == "7d":
            time_filter = "timestamp >= now() - interval 7 day"
            group_by = "toDate(timestamp)"
        else:
            time_filter = "timestamp >= now() - interval 1 hour"
            group_by = "toMinute(timestamp)"
        
        query = f"""
        SELECT 
            {group_by} as time_period,
            count(*) as request_count,
            uniq(user_id) as unique_users,
            avg(latency_ms) as avg_latency
        FROM usage_events 
        WHERE {time_filter}
        """
        
        if user_id:
            query += f" AND user_id = '{user_id}'"
        
        query += f" GROUP BY {group_by} ORDER BY time_period"
        
        return query.strip()
    
    @staticmethod
    def build_anomaly_detection_query(
        metric: str = "latency_ms",
        timeframe: str = "24h",
        threshold_factor: float = 2.0
    ) -> str:
        """Build an anomaly detection query."""
        
        if timeframe == "24h":
            time_filter = "timestamp >= now() - interval 24 hour"
        elif timeframe == "7d":
            time_filter = "timestamp >= now() - interval 7 day"
        else:
            time_filter = "timestamp >= now() - interval 1 hour"
        
        query = f"""
        WITH stats AS (
            SELECT 
                avg({metric}) as mean_value,
                stddev({metric}) as std_value
            FROM metrics 
            WHERE {time_filter}
        )
        SELECT 
            timestamp,
            {metric},
            abs({metric} - stats.mean_value) > ({threshold_factor} * stats.std_value) as is_anomaly
        FROM metrics, stats
        WHERE {time_filter}
        ORDER BY timestamp
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