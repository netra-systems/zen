"""Specialized metrics analysis module with proper type safety."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from app.logging_config import central_logger as logger


class MetricsAnalyzer:
    """Specialized analyzer for metrics with strong typing and ≤8 line functions."""
    
    def __init__(
        self,
        query_builder: Any,
        analysis_engine: Any,
        clickhouse_ops: Any
    ) -> None:
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
    
    async def analyze_metric_distribution(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze distribution characteristics of a specific metric."""
        query = self._build_distribution_query(user_id, metric_name, time_range)
        data = await self._fetch_metric_data(query, f"dist_{user_id}_{metric_name}")
        
        if not data:
            return self._create_empty_distribution_result(metric_name)
        
        return self._process_distribution_data(data, metric_name, time_range)
    
    async def detect_metric_trends(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Detect trends in metric values over time."""
        query = self._build_trend_query(user_id, metric_name, time_range)
        data = await self._fetch_metric_data(query, f"trend_{user_id}_{metric_name}")
        
        if not data or len(data) < 3:
            return self._create_insufficient_trend_data_result(metric_name)
        
        return self._analyze_trend_patterns(data, metric_name, time_range)
    
    async def calculate_metric_percentiles(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        percentiles: List[float] = [50.0, 75.0, 90.0, 95.0, 99.0]
    ) -> Dict[str, Any]:
        """Calculate percentiles for a specific metric."""
        query = self._build_percentiles_query(user_id, metric_name, time_range, percentiles)
        data = await self._fetch_metric_data(query, f"pct_{user_id}_{metric_name}")
        
        if not data:
            return self._create_empty_percentiles_result(metric_name, percentiles)
        
        return self._format_percentiles_result(data, metric_name, percentiles, time_range)
    
    async def compare_metrics_performance(
        self,
        user_id: int,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Compare performance across multiple metrics."""
        if len(metric_names) < 2:
            return {"error": "At least 2 metrics required for comparison"}
        
        metric_stats = {}
        for metric in metric_names:
            stats = await self._calculate_metric_summary_stats(user_id, metric, time_range)
            metric_stats[metric] = stats
        
        return self._create_comparison_result(metric_stats, time_range)
    
    async def detect_metric_seasonality(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Detect seasonal patterns in metric data."""
        query = self._build_seasonality_query(user_id, metric_name, time_range)
        data = await self._fetch_metric_data(query, f"season_{user_id}_{metric_name}")
        
        if not data or len(data) < 24:  # Need at least 24 data points
            return self._create_insufficient_seasonality_data_result(metric_name)
        
        return self._analyze_seasonality_patterns(data, metric_name, time_range)
    
    def _build_distribution_query(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> str:
        """Build query for metric distribution analysis."""
        return self.query_builder.build_metric_distribution_query(
            user_id, metric_name, time_range[0], time_range[1]
        )
    
    def _build_trend_query(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> str:
        """Build query for trend analysis."""
        return self.query_builder.build_metric_trend_query(
            user_id, metric_name, time_range[0], time_range[1]
        )
    
    def _build_percentiles_query(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        percentiles: List[float]
    ) -> str:
        """Build query for percentiles calculation."""
        return self.query_builder.build_percentiles_query(
            user_id, metric_name, time_range[0], time_range[1], percentiles
        )
    
    def _build_seasonality_query(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> str:
        """Build query for seasonality analysis."""
        return self.query_builder.build_seasonality_query(
            user_id, metric_name, time_range[0], time_range[1]
        )
    
    async def _fetch_metric_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch metric data with caching."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, None)
    
    def _create_empty_distribution_result(self, metric_name: str) -> Dict[str, Any]:
        """Create empty distribution result."""
        return {
            "metric": metric_name,
            "status": "no_data",
            "message": f"No data available for distribution analysis of {metric_name}"
        }
    
    def _create_insufficient_trend_data_result(self, metric_name: str) -> Dict[str, Any]:
        """Create insufficient trend data result."""
        return {
            "metric": metric_name,
            "status": "insufficient_data",
            "message": f"Insufficient data for trend analysis of {metric_name} (need at least 3 points)"
        }
    
    def _create_empty_percentiles_result(
        self,
        metric_name: str,
        percentiles: List[float]
    ) -> Dict[str, Any]:
        """Create empty percentiles result."""
        return {
            "metric": metric_name,
            "status": "no_data",
            "requested_percentiles": percentiles,
            "message": f"No data available for percentile calculation of {metric_name}"
        }
    
    def _create_insufficient_seasonality_data_result(self, metric_name: str) -> Dict[str, Any]:
        """Create insufficient seasonality data result."""
        return {
            "metric": metric_name,
            "status": "insufficient_data",
            "message": f"Insufficient data for seasonality analysis of {metric_name} (need at least 24 points)"
        }
    
    def _process_distribution_data(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Process distribution analysis data."""
        values = [row['value'] for row in data if 'value' in row]
        
        if not values:
            return self._create_empty_distribution_result(metric_name)
        
        distribution_stats = self.analysis_engine.calculate_distribution_statistics(values)
        outliers = self.analysis_engine.identify_outliers(values)
        
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "distribution": distribution_stats,
            "outliers": {"count": len(outliers), "indices": outliers[:10]},
            "sample_size": len(values)
        }
    
    def _analyze_trend_patterns(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze trend patterns in metric data."""
        timestamps = [datetime.fromisoformat(row['timestamp']) for row in data]
        values = [row['value'] for row in data]
        
        trend_result = self.analysis_engine.detect_trend(values, timestamps)
        change_points = self.analysis_engine.detect_change_points(values)
        
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "trend": trend_result,
            "change_points": change_points,
            "data_points": len(data)
        }
    
    def _format_percentiles_result(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        percentiles: List[float],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Format percentiles calculation result."""
        percentile_values = {}
        for row in data:
            pct = row.get('percentile')
            value = row.get('value')
            if pct is not None and value is not None:
                percentile_values[f"p{pct}"] = value
        
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "percentiles": percentile_values,
            "requested": percentiles,
            "sample_size": data[0].get('sample_size', 0) if data else 0
        }
    
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
        valid_metrics = {k: v for k, v in metric_stats.items() if v.get("status") != "no_data"}
        
        if not valid_metrics:
            return {"status": "no_data", "message": "No valid data for any metrics"}
        
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
    
    def _analyze_seasonality_patterns(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze seasonality patterns in metric data."""
        timestamps = [datetime.fromisoformat(row['timestamp']) for row in data]
        values = [row['value'] for row in data]
        
        seasonality_result = self.analysis_engine.detect_seasonality(values, timestamps)
        hourly_patterns = self._analyze_hourly_patterns(data)
        daily_patterns = self._analyze_daily_patterns(data)
        
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "seasonality": seasonality_result,
            "hourly_patterns": hourly_patterns,
            "daily_patterns": daily_patterns,
            "data_points": len(data)
        }
    
    def _analyze_hourly_patterns(self, data: List[Dict[str, Any]]) -> Dict[int, float]:
        """Analyze hourly usage patterns."""
        hourly_values = {}
        for row in data:
            hour = datetime.fromisoformat(row['timestamp']).hour
            if hour not in hourly_values:
                hourly_values[hour] = []
            hourly_values[hour].append(row['value'])
        
        return {hour: sum(values) / len(values) for hour, values in hourly_values.items()}
    
    def _analyze_daily_patterns(self, data: List[Dict[str, Any]]) -> Dict[int, float]:
        """Analyze daily usage patterns."""
        daily_values = {}
        for row in data:
            day_of_week = datetime.fromisoformat(row['timestamp']).weekday()
            if day_of_week not in daily_values:
                daily_values[day_of_week] = []
            daily_values[day_of_week].append(row['value'])
        
        return {day: sum(values) / len(values) for day, values in daily_values.items()}
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }