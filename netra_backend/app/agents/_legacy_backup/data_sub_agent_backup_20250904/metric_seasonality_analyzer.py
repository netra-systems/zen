"""Metric seasonality analysis module for seasonal pattern detection."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger as logger


class MetricSeasonalityAnalyzer:
    """Specialized analyzer for metric seasonality pattern detection."""
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any) -> None:
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
    
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
    
    def _create_insufficient_seasonality_data_result(self, metric_name: str) -> Dict[str, Any]:
        """Create insufficient seasonality data result."""
        return {
            "metric": metric_name,
            "status": "insufficient_data",
            "message": f"Insufficient data for seasonality analysis of {metric_name} (need at least 24 points)"
        }
    
    def _analyze_seasonality_patterns(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze seasonality patterns in metric data."""
        timestamps = self._extract_timestamps(data)
        values = self._extract_values(data)
        
        seasonality_result = self._detect_seasonality(values, timestamps)
        hourly_patterns = self._analyze_hourly_patterns(data)
        daily_patterns = self._analyze_daily_patterns(data)
        
        return self._build_seasonality_result(metric_name, time_range, seasonality_result, hourly_patterns, daily_patterns, data)
    
    def _extract_timestamps(self, data: List[Dict[str, Any]]) -> List[datetime]:
        """Extract timestamps from data."""
        return [datetime.fromisoformat(row['timestamp']) for row in data]
    
    def _extract_values(self, data: List[Dict[str, Any]]) -> List[float]:
        """Extract values from data."""
        return [row['value'] for row in data]
    
    def _detect_seasonality(self, values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect seasonality using analysis engine."""
        return self.analysis_engine.detect_seasonality(values, timestamps)
    
    def _analyze_hourly_patterns(self, data: List[Dict[str, Any]]) -> Dict[int, float]:
        """Analyze hourly usage patterns."""
        hourly_values = self._group_by_hour(data)
        return self._calculate_hourly_averages(hourly_values)
    
    def _group_by_hour(self, data: List[Dict[str, Any]]) -> Dict[int, List[float]]:
        """Group data by hour of day."""
        hourly_values = {}
        for row in data:
            hour = datetime.fromisoformat(row['timestamp']).hour
            if hour not in hourly_values:
                hourly_values[hour] = []
            hourly_values[hour].append(row['value'])
        return hourly_values
    
    def _calculate_hourly_averages(self, hourly_values: Dict[int, List[float]]) -> Dict[int, float]:
        """Calculate average values for each hour."""
        return {hour: sum(values) / len(values) for hour, values in hourly_values.items()}
    
    def _analyze_daily_patterns(self, data: List[Dict[str, Any]]) -> Dict[int, float]:
        """Analyze daily usage patterns."""
        daily_values = self._group_by_day(data)
        return self._calculate_daily_averages(daily_values)
    
    def _group_by_day(self, data: List[Dict[str, Any]]) -> Dict[int, List[float]]:
        """Group data by day of week."""
        daily_values = {}
        for row in data:
            day_of_week = datetime.fromisoformat(row['timestamp']).weekday()
            if day_of_week not in daily_values:
                daily_values[day_of_week] = []
            daily_values[day_of_week].append(row['value'])
        return daily_values
    
    def _calculate_daily_averages(self, daily_values: Dict[int, List[float]]) -> Dict[int, float]:
        """Calculate average values for each day."""
        return {day: sum(values) / len(values) for day, values in daily_values.items()}
    
    def _build_seasonality_result(
        self, metric_name: str, time_range: Tuple[datetime, datetime],
        seasonality_result: Dict[str, Any], hourly_patterns: Dict[int, float],
        daily_patterns: Dict[int, float], data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete seasonality analysis result."""
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "seasonality": seasonality_result,
            "hourly_patterns": hourly_patterns,
            "daily_patterns": daily_patterns,
            "data_points": len(data)
        }
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }