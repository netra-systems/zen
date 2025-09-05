"""Anomaly detection operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger as logger


class AnomalyDetectionOperations:
    """Handles anomaly detection analysis with proper type safety."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager

    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data."""
        return await self._execute_anomaly_detection(user_id, metric_name, time_range, z_score_threshold)

    async def _execute_anomaly_detection(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Execute anomaly detection workflow."""
        data = await self._fetch_anomaly_data(user_id, metric_name, time_range, z_score_threshold)
        return self._handle_anomaly_result(data, metric_name, z_score_threshold)

    async def _fetch_anomaly_data(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch anomaly data from database."""
        start_time, end_time = time_range
        query = self._build_anomaly_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = self._create_anomaly_cache_key(user_id, metric_name, start_time, z_score_threshold)
        return await self._fetch_cached_data(query, cache_key)

    def _handle_anomaly_result(
        self,
        data: Optional[List[Dict[str, Any]]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Handle anomaly detection result."""
        if not data:
            return self._create_no_anomalies_response(metric_name, z_score_threshold)
        return self._process_anomaly_data(data, metric_name, z_score_threshold)

    def _build_anomaly_query(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Build anomaly detection query."""
        return self._delegate_anomaly_query_build(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )

    def _delegate_anomaly_query_build(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Delegate anomaly query building to query builder."""
        return self.query_builder.build_anomaly_detection_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
    
    def _create_anomaly_cache_key(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Create cache key for anomaly detection."""
        return self._build_anomaly_cache_string(user_id, metric_name, start_time, z_score_threshold)

    def _build_anomaly_cache_string(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Build anomaly cache key string."""
        return f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"

    async def _fetch_cached_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_anomalies_response(self, metric_name: str, threshold: float) -> Dict[str, Any]:
        """Create no anomalies response."""
        return self._build_no_anomalies_dict(metric_name, threshold)

    def _build_no_anomalies_dict(self, metric_name: str, threshold: float) -> Dict[str, Any]:
        """Build no anomalies response dictionary."""
        return {
            "status": "no_anomalies",
            "message": f"No anomalies detected for {metric_name}",
            "threshold": threshold
        }
    
    def _process_anomaly_data(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Process anomaly detection data."""
        return self._build_anomaly_response(data, metric_name, z_score_threshold)

    def _build_anomaly_response(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Build complete anomaly response."""
        base_info = self._build_anomaly_base_info(metric_name, z_score_threshold, len(data))
        anomalies = self._format_anomaly_entries(data)
        return self._merge_anomaly_info(base_info, anomalies)

    def _merge_anomaly_info(self, base_info: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge base info with anomalies list."""
        return {**base_info, "anomalies": anomalies}
    
    def _build_anomaly_base_info(self, metric_name: str, threshold: float, count: int) -> Dict[str, Any]:
        """Build base anomaly information."""
        return self._create_anomaly_base_dict(metric_name, threshold, count)

    def _create_anomaly_base_dict(self, metric_name: str, threshold: float, count: int) -> Dict[str, Any]:
        """Create anomaly base information dictionary."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": threshold,
            "anomaly_count": count
        }
    
    def _format_anomaly_entries(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format anomaly entries for response."""
        limited_data = data[:50]  # Limit to top 50 anomalies
        return [self._format_single_anomaly(row) for row in limited_data]
    
    def _format_single_anomaly(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format single anomaly entry."""
        return self._build_anomaly_entry(row)

    def _build_anomaly_entry(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Build formatted anomaly entry."""
        z_score = row['z_score']
        return self._create_anomaly_entry_dict(row, z_score)

    def _create_anomaly_entry_dict(self, row: Dict[str, Any], z_score: float) -> Dict[str, Any]:
        """Create anomaly entry dictionary."""
        return {
            "timestamp": row['timestamp'],
            "value": row['metric_value'],
            "z_score": z_score,
            "severity": self._determine_anomaly_severity(z_score)
        }

    def _determine_anomaly_severity(self, z_score: float) -> str:
        """Determine anomaly severity based on z-score."""
        return "high" if abs(z_score) > 3 else "medium"