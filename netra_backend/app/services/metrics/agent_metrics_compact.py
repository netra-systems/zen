"""
Compact agent metrics collector using modular components.
Main interface for agent metrics collection and reporting.
"""

from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Metrics import TimeSeriesPoint
from netra_backend.app.agent_metrics_models import (
    AgentOperationRecord, AgentMetrics, FailureType, AgentMetricType
)
from netra_backend.app.agent_metrics_collector_core import AgentMetricsCollectorCore

logger = central_logger.get_logger(__name__)


class AgentMetricsCollector(AgentMetricsCollectorCore):
    """Compact agent metrics collector with time series support."""
    
    def __init__(self, max_buffer_size: int = 5000):
        super().__init__(max_buffer_size)
        # Health cache for performance
        self._health_cache: Dict[str, float] = {}
        self._health_cache_ttl = 30  # 30 seconds
        self._health_cache_timestamps: Dict[str, float] = {}

    def get_time_series_data(
        self,
        agent_name: str,
        metric_type: AgentMetricType,
        hours: int = 1
    ) -> List[TimeSeriesPoint]:
        """Get time series data for agent metrics."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        points = []
        
        for record in self._operation_records:
            if (record.agent_name == agent_name and 
                record.start_time >= cutoff_time and 
                record.end_time):
                
                value = self._extract_metric_value(record, metric_type)
                if value is not None:
                    points.append(TimeSeriesPoint(
                        timestamp=record.end_time,
                        value=value,
                        tags={"agent": agent_name, "operation": record.operation_type}
                    ))
        
        return sorted(points, key=lambda x: x.timestamp)

    def _extract_metric_value(
        self, 
        record: AgentOperationRecord, 
        metric_type: AgentMetricType
    ) -> Optional[float]:
        """Extract specific metric value from operation record."""
        mapping = {
            AgentMetricType.EXECUTION_TIME: record.execution_time_ms,
            AgentMetricType.SUCCESS_RATE: 1.0 if record.success else 0.0,
            AgentMetricType.ERROR_RATE: 0.0 if record.success else 1.0,
            AgentMetricType.TIMEOUT_RATE: 1.0 if record.failure_type == FailureType.TIMEOUT else 0.0,
            AgentMetricType.VALIDATION_ERROR_RATE: 1.0 if record.failure_type == FailureType.VALIDATION_ERROR else 0.0,
            AgentMetricType.MEMORY_USAGE: record.memory_usage_mb,
            AgentMetricType.CPU_USAGE: record.cpu_usage_percent
        }
        return mapping.get(metric_type)

    def get_health_score(self, agent_name: str) -> float:
        """Calculate health score for an agent with caching."""
        import time
        
        # Check cache first
        cache_key = agent_name
        current_time = time.time()
        
        if (cache_key in self._health_cache and 
            current_time - self._health_cache_timestamps.get(cache_key, 0) < self._health_cache_ttl):
            return self._health_cache[cache_key]
        
        # Calculate health score
        score = super().get_health_score(agent_name)
        
        # Cache the result
        self._health_cache[cache_key] = score
        self._health_cache_timestamps[cache_key] = current_time
        
        return score

    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status."""
        return {
            "active_operations": len(self._active_operations),
            "buffered_metrics": len(self._operation_records),
            "tracked_agents": len(self._agent_metrics),
            "buffer_utilization": len(self._operation_records) / self.max_buffer_size
        }

    async def cleanup_old_data(self, hours: int = 24) -> None:
        """Clean up old data including health cache."""
        await super().cleanup_old_data(hours)
        
        # Clear health cache
        self._health_cache.clear()
        self._health_cache_timestamps.clear()


# Global agent metrics collector instance
agent_metrics_collector = AgentMetricsCollector()