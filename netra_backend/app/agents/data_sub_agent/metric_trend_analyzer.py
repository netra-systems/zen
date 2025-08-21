"""Metric trend analysis module for specialized trend detection operations."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger as logger


class MetricTrendAnalyzer:
    """Specialized analyzer for metric trend detection and analysis."""
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any) -> None:
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
    
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
    
    async def _fetch_metric_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch metric data with caching."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, None)
    
    def _create_insufficient_trend_data_result(self, metric_name: str) -> Dict[str, Any]:
        """Create insufficient trend data result."""
        return {
            "metric": metric_name,
            "status": "insufficient_data",
            "message": f"Insufficient data for trend analysis of {metric_name} (need at least 3 points)"
        }
    
    def _analyze_trend_patterns(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze trend patterns in metric data."""
        timestamps = self._extract_timestamps(data)
        values = self._extract_values(data)
        
        trend_result = self._detect_trend(values, timestamps)
        change_points = self._detect_change_points(values)
        
        return self._build_trend_result(metric_name, time_range, trend_result, change_points, data)
    
    def _extract_timestamps(self, data: List[Dict[str, Any]]) -> List[datetime]:
        """Extract timestamps from data."""
        return [datetime.fromisoformat(row['timestamp']) for row in data]
    
    def _extract_values(self, data: List[Dict[str, Any]]) -> List[float]:
        """Extract values from data."""
        return [row['value'] for row in data]
    
    def _detect_trend(self, values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect trend in values over time."""
        return self.analysis_engine.detect_trend(values, timestamps)
    
    def _detect_change_points(self, values: List[float]) -> List[int]:
        """Detect change points in values."""
        return self.analysis_engine.detect_change_points(values)
    
    def _build_trend_result(
        self, metric_name: str, time_range: Tuple[datetime, datetime],
        trend_result: Dict[str, Any], change_points: List[int], data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete trend analysis result."""
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "trend": trend_result,
            "change_points": change_points,
            "data_points": len(data)
        }
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }