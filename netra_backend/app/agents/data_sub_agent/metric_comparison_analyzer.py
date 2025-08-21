"""Metric comparison analysis module for cross-metric performance comparison."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger as logger


class MetricComparisonAnalyzer:
    """Specialized analyzer for cross-metric performance comparison."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
    
    async def compare_metrics_performance(
        self,
        user_id: int,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Compare performance across multiple metrics."""
        if len(metric_names) < 2:
            return {"error": "At least 2 metrics required for comparison"}
        
        metric_stats = await self._calculate_all_metric_stats(user_id, metric_names, time_range)
        return self._create_comparison_result(metric_stats, time_range)
    
    async def _calculate_all_metric_stats(
        self, user_id: int, metric_names: List[str], time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate summary statistics for all metrics."""
        metric_stats = {}
        for metric in metric_names:
            stats = await self._calculate_metric_summary_stats(user_id, metric, time_range)
            metric_stats[metric] = stats
        return metric_stats
    
    async def _calculate_metric_summary_stats(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Calculate summary statistics for a metric."""
        query = self._build_summary_stats_query(user_id, metric_name, time_range)
        data = await self._fetch_metric_data(query, f"summary_{user_id}_{metric_name}")
        
        if not data or not data[0]:
            return {"status": "no_data"}
        
        return self._format_summary_stats(data[0])
    
    def _build_summary_stats_query(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> str:
        """Build query for summary statistics."""
        return self.query_builder.build_summary_stats_query(
            user_id, metric_name, time_range[0], time_range[1]
        )
    
    async def _fetch_metric_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch metric data with caching."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, None)
    
    def _format_summary_stats(self, stats_row: Dict[str, Any]) -> Dict[str, Any]:
        """Format summary statistics result."""
        return {
            "mean": stats_row.get('avg_value', 0),
            "median": stats_row.get('median_value', 0),
            "std_dev": stats_row.get('stddev_value', 0),
            "min": stats_row.get('min_value', 0),
            "max": stats_row.get('max_value', 0),
            "count": stats_row.get('count_value', 0)
        }
    
    def _create_comparison_result(
        self,
        metric_stats: Dict[str, Dict[str, Any]],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Create metrics comparison result."""
        valid_metrics = self._filter_valid_metrics(metric_stats)
        
        if not valid_metrics:
            return {"status": "no_data", "message": "No valid data for any metrics"}
        
        return self._build_comparison_result(valid_metrics, time_range)
    
    def _filter_valid_metrics(self, metric_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter metrics with valid data."""
        return {k: v for k, v in metric_stats.items() if v.get("status") != "no_data"}
    
    def _build_comparison_result(
        self, valid_metrics: Dict[str, Dict[str, Any]], time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Build complete comparison result."""
        return {
            "time_range": self._format_time_range(time_range),
            "metrics_compared": list(valid_metrics.keys()),
            "statistics": valid_metrics,
            "best_performing": self._identify_best_performing_metric(valid_metrics),
            "worst_performing": self._identify_worst_performing_metric(valid_metrics)
        }
    
    def _identify_best_performing_metric(self, metrics: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Identify best performing metric (lowest mean)."""
        if not metrics:
            return None
        
        return min(metrics.items(), key=lambda x: x[1].get('mean', float('inf')))[0]
    
    def _identify_worst_performing_metric(self, metrics: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Identify worst performing metric (highest mean)."""
        if not metrics:
            return None
        
        return max(metrics.items(), key=lambda x: x[1].get('mean', 0))[0]
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }