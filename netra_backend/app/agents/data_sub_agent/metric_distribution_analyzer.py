"""Metric distribution analysis module for specialized distribution operations."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger as logger


class MetricDistributionAnalyzer:
    """Specialized analyzer for metric distribution characteristics."""
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any) -> None:
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
    
    def _process_distribution_data(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Process distribution analysis data."""
        values = self._extract_values(data)
        
        if not values:
            return self._create_empty_distribution_result(metric_name)
        
        distribution_stats = self._calculate_distribution_stats(values)
        outliers = self._identify_outliers(values)
        
        return self._build_distribution_result(metric_name, time_range, distribution_stats, outliers, values)
    
    def _extract_values(self, data: List[Dict[str, Any]]) -> List[float]:
        """Extract values from data rows."""
        return [row['value'] for row in data if 'value' in row]
    
    def _calculate_distribution_stats(self, values: List[float]) -> Dict[str, Any]:
        """Calculate distribution statistics."""
        return self.analysis_engine.calculate_distribution_statistics(values)
    
    def _identify_outliers(self, values: List[float]) -> List[int]:
        """Identify outliers in values."""
        return self.analysis_engine.identify_outliers(values)
    
    def _build_distribution_result(
        self, metric_name: str, time_range: Tuple[datetime, datetime], 
        distribution_stats: Dict[str, Any], outliers: List[int], values: List[float]
    ) -> Dict[str, Any]:
        """Build complete distribution analysis result."""
        return {
            "metric": metric_name,
            "time_range": self._format_time_range(time_range),
            "distribution": distribution_stats,
            "outliers": self._format_outliers(outliers),
            "sample_size": len(values)
        }
    
    def _format_outliers(self, outliers: List[int]) -> Dict[str, Any]:
        """Format outliers information."""
        return {"count": len(outliers), "indices": outliers[:10]}
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for output."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
        }