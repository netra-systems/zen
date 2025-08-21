"""Metric percentile analysis module for specialized percentile calculations."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger as logger


class MetricPercentileAnalyzer:
    """Specialized analyzer for metric percentile calculations."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
    
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
    
    async def _fetch_metric_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch metric data with caching."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, None)
    
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
    
    def _format_percentiles_result(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        percentiles: List[float],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Format percentiles calculation result."""
        percentile_values = self._extract_percentile_values(data)
        sample_size = self._get_sample_size(data)
        
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "percentiles": percentile_values,
            "requested": percentiles,
            "sample_size": sample_size
        }
    
    def _extract_percentile_values(self, data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract percentile values from data."""
        percentile_values = {}
        for row in data:
            pct = row.get('percentile')
            value = row.get('value')
            if pct is not None and value is not None:
                percentile_values[f"p{pct}"] = value
        return percentile_values
    
    def _get_sample_size(self, data: List[Dict[str, Any]]) -> int:
        """Get sample size from data."""
        return data[0].get('sample_size', 0) if data else 0
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }