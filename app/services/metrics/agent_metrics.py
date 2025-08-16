"""
Agent metrics collection and monitoring system.
Main orchestrator for agent metrics functionality using modular components.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.logging_config import central_logger
from app.schemas.Metrics import TimeSeriesPoint
from .agent_metrics_models import (
    AgentOperationRecord, AgentMetrics, FailureType, AgentMetricType
)
from .agent_metrics_collector_core import AgentMetricsCollectorCore

logger = central_logger.get_logger(__name__)


class AgentMetricsCollector:
    """Orchestrator for agent metrics collection and monitoring."""
    
    def __init__(self, max_buffer_size: int = 5000):
        self._core = AgentMetricsCollectorCore(max_buffer_size)
        logger.debug(f"Initialized AgentMetricsCollector with buffer size {max_buffer_size}")

    async def start_operation(
        self, 
        agent_name: str, 
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking an agent operation."""
        return await self._core.start_operation(agent_name, operation_type, metadata)

    async def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        failure_type: Optional[FailureType] = None,
        error_message: Optional[str] = None,
        memory_usage_mb: float = 0.0,
        cpu_usage_percent: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentOperationRecord]:
        """End operation tracking and record metrics."""
        return await self._core.end_operation(
            operation_id, success, failure_type, error_message,
            memory_usage_mb, cpu_usage_percent, metadata
        )

    async def record_timeout(
        self, 
        operation_id: str, 
        timeout_duration_ms: float
    ) -> None:
        """Record a timeout for an operation."""
        await self._core.record_timeout(operation_id, timeout_duration_ms)

    async def record_validation_error(
        self, 
        operation_id: str, 
        validation_error: str
    ) -> None:
        """Record a validation error for an operation."""
        await self._core.record_validation_error(operation_id, validation_error)

    def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get current metrics for an agent."""
        return self._core.get_agent_metrics(agent_name)

    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        return self._core.get_all_agent_metrics()

    def get_active_operations(self) -> Dict[str, AgentOperationRecord]:
        """Get currently active operations."""
        return self._core.get_active_operations()

    def get_recent_operations(
        self, 
        agent_name: Optional[str] = None,
        hours: int = 1
    ) -> List[AgentOperationRecord]:
        """Get recent operations within time window."""
        return self._core.get_recent_operations(agent_name, hours)

    def get_time_series_data(
        self,
        agent_name: str,
        metric_type: AgentMetricType,
        hours: int = 1
    ) -> List[TimeSeriesPoint]:
        """Get time series data for agent metrics."""
        return self._create_time_series_points(agent_name, metric_type, hours)
    
    def _create_time_series_points(self, agent_name: str, metric_type: AgentMetricType, hours: int) -> List[TimeSeriesPoint]:
        """Create time series points for specified agent and metric."""
        recent_ops = self._core.get_recent_operations(agent_name, hours)
        points = self._extract_points_from_operations(recent_ops, agent_name, metric_type)
        return sorted(points, key=lambda x: x.timestamp)
    
    def _extract_points_from_operations(self, operations: List[AgentOperationRecord], agent_name: str, metric_type: AgentMetricType) -> List[TimeSeriesPoint]:
        """Extract time series points from operation records."""
        points = []
        for record in operations:
            point = self._create_point_from_record(record, agent_name, metric_type)
            if point:
                points.append(point)
        return points
    
    def _create_point_from_record(self, record: AgentOperationRecord, agent_name: str, metric_type: AgentMetricType) -> Optional[TimeSeriesPoint]:
        """Create time series point from operation record."""
        if not record.end_time:
            return None
        value = self._extract_metric_value(record, metric_type)
        return self._create_time_series_point(record, value, agent_name) if value is not None else None
    
    def _create_time_series_point(self, record: AgentOperationRecord, value: float, agent_name: str) -> TimeSeriesPoint:
        """Create a single time series point."""
        return TimeSeriesPoint(
            timestamp=record.end_time,
            value=value,
            tags={"agent": agent_name, "operation": record.operation_type}
        )

    def _extract_metric_value(self, record: AgentOperationRecord, metric_type: AgentMetricType) -> Optional[float]:
        """Extract specific metric value from operation record."""
        basic_metrics = self._get_basic_metric_values(record)
        advanced_metrics = self._get_advanced_metric_values(record)
        return {**basic_metrics, **advanced_metrics}.get(metric_type)
    
    def _get_basic_metric_values(self, record: AgentOperationRecord) -> Dict[AgentMetricType, float]:
        """Get basic metric values from record."""
        execution_metrics = self._get_execution_metrics(record)
        resource_metrics = self._get_resource_metrics(record)
        return {**execution_metrics, **resource_metrics}
    
    def _get_advanced_metric_values(self, record: AgentOperationRecord) -> Dict[AgentMetricType, float]:
        """Get advanced metric values from record."""
        return {
            AgentMetricType.TIMEOUT_RATE: 1.0 if record.failure_type == FailureType.TIMEOUT else 0.0,
            AgentMetricType.VALIDATION_ERROR_RATE: 1.0 if record.failure_type == FailureType.VALIDATION_ERROR else 0.0
        }

    def get_health_score(self, agent_name: str) -> float:
        """Calculate health score for an agent (0.0 to 1.0)."""
        return self._core.get_health_score(agent_name)

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide agent metrics overview."""
        return await self._core.get_system_overview()

    async def cleanup_old_data(self, hours: int = 24) -> None:
        """Clean up old operation records."""
        await self._core.cleanup_old_data(hours)
    
    def _create_point_from_record(self, record: AgentOperationRecord, agent_name: str, metric_type: AgentMetricType) -> Optional[TimeSeriesPoint]:
        """Create time series point from record if valid."""
        if record.end_time:
            value = self._extract_metric_value(record, metric_type)
            if value is not None:
                return self._create_time_series_point(record, value, agent_name)
        return None
    
    def _get_execution_metrics(self, record: AgentOperationRecord) -> Dict[AgentMetricType, float]:
        """Get execution-related metrics."""
        return {
            AgentMetricType.EXECUTION_TIME: record.execution_time_ms,
            AgentMetricType.SUCCESS_RATE: 1.0 if record.success else 0.0,
            AgentMetricType.ERROR_RATE: 0.0 if record.success else 1.0
        }
    
    def _get_resource_metrics(self, record: AgentOperationRecord) -> Dict[AgentMetricType, float]:
        """Get resource-related metrics."""
        return {
            AgentMetricType.MEMORY_USAGE: record.memory_usage_mb,
            AgentMetricType.CPU_USAGE: record.cpu_usage_percent
        }


# Global agent metrics collector instance
agent_metrics_collector = AgentMetricsCollector()