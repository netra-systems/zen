"""Anomaly detection module for DataSubAgent."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class AnomalyDetector:
    """Focused anomaly detection operations."""
    
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
        data = await self._fetch_anomaly_data(user_id, metric_name, time_range, z_score_threshold)
        if not data:
            return self._create_no_anomalies_response(metric_name, z_score_threshold)
        return self._build_anomalies_response(data, metric_name, z_score_threshold)
    
    async def _fetch_anomaly_data(self, user_id: int, metric_name: str, time_range: Tuple[datetime, datetime], 
                                 z_score_threshold: float) -> Optional[List[Dict]]:
        """Fetch anomaly data from ClickHouse."""
        start_time, end_time = time_range
        query = self._build_anomaly_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = self._build_anomaly_cache_key(user_id, metric_name, start_time, z_score_threshold)
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _build_anomaly_query(self, user_id: int, metric_name: str, start_time: datetime, 
                           end_time: datetime, z_score_threshold: float) -> str:
        """Build anomaly detection query."""
        return self.query_builder.build_anomaly_detection_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
    
    def _build_anomaly_cache_key(self, user_id: int, metric_name: str, 
                               start_time: datetime, z_score_threshold: float) -> str:
        """Build cache key for anomaly detection."""
        return f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
    
    def _create_no_anomalies_response(self, metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Create response for no anomalies found."""
        return {
            "status": "no_anomalies",
            "message": f"No anomalies detected for {metric_name}",
            "threshold": z_score_threshold
        }
    
    def _build_anomalies_response(self, data: List[Dict], metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Build anomalies response."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": z_score_threshold,
            "anomaly_count": len(data),
            "anomalies": self._format_anomaly_list(data)
        }
    
    def _format_anomaly_list(self, data: List[Dict]) -> List[Dict]:
        """Format anomaly list for response."""
        return [
            self._format_single_anomaly(row)
            for row in data[:50]
        ]
    
    def _format_single_anomaly(self, row: Dict) -> Dict[str, Any]:
        """Format single anomaly entry."""
        return {
            "timestamp": row['timestamp'],
            "value": row['metric_value'],
            "z_score": row['z_score'],
            "severity": self._determine_severity(row['z_score'])
        }
    
    def _determine_severity(self, z_score: float) -> str:
        """Determine anomaly severity based on z-score."""
        return "high" if abs(z_score) > 3 else "medium"