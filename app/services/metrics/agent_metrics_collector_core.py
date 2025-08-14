"""
Core agent metrics collection functionality.
Handles operation tracking and metrics aggregation.
"""

import asyncio
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict

from app.logging_config import central_logger
from app.schemas.Metrics import TimeSeriesPoint
from .agent_metrics_models import (
    AgentOperationRecord, AgentMetrics, FailureType, AgentMetricType,
    create_operation_record, calculate_operation_metrics,
    update_agent_metrics, calculate_health_score
)

logger = central_logger.get_logger(__name__)


class AgentMetricsCollectorCore:
    """Core functionality for agent metrics collection."""
    
    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self._operation_records = deque(maxlen=max_buffer_size)
        self._active_operations: Dict[str, AgentOperationRecord] = {}
        self._agent_metrics: Dict[str, AgentMetrics] = defaultdict(AgentMetrics)
        
        # Performance tracking
        self._performance_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Alert thresholds
        self.error_rate_threshold = 0.2  # 20% error rate
        self.timeout_threshold = 30.0    # 30 seconds
        self.memory_threshold_mb = 1024  # 1GB
        self.cpu_threshold_percent = 80  # 80% CPU

    async def start_operation(
        self, 
        agent_name: str, 
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking an agent operation."""
        record = create_operation_record(agent_name, operation_type, metadata)
        self._active_operations[record.operation_id] = record
        
        logger.debug(f"Started tracking {agent_name} operation {record.operation_id}")
        return record.operation_id

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
        if operation_id not in self._active_operations:
            logger.warning(f"Operation {operation_id} not found")
            return None
        
        record = self._active_operations.pop(operation_id)
        record.end_time = datetime.now(UTC)
        record.success = success
        record.failure_type = failure_type
        record.error_message = error_message
        record.memory_usage_mb = memory_usage_mb
        record.cpu_usage_percent = cpu_usage_percent
        
        if record.end_time and record.start_time:
            duration = record.end_time - record.start_time
            record.execution_time_ms = duration.total_seconds() * 1000
        
        if metadata:
            record.metadata.update(metadata)
        
        # Store completed record
        self._operation_records.append(record)
        
        # Update aggregated metrics
        await self._update_agent_metrics(record)
        
        # Track performance trends
        await self._track_performance(record)
        
        # Check for alerts
        await self._check_alert_conditions(record)
        
        return record

    async def record_timeout(
        self, 
        operation_id: str, 
        timeout_duration_ms: float
    ) -> None:
        """Record a timeout for an operation."""
        await self.end_operation(
            operation_id=operation_id,
            success=False,
            failure_type=FailureType.TIMEOUT,
            error_message=f"Operation timed out after {timeout_duration_ms}ms"
        )

    async def record_validation_error(
        self, 
        operation_id: str, 
        validation_error: str
    ) -> None:
        """Record a validation error for an operation."""
        await self.end_operation(
            operation_id=operation_id,
            success=False,
            failure_type=FailureType.VALIDATION_ERROR,
            error_message=validation_error
        )

    async def _update_agent_metrics(self, record: AgentOperationRecord) -> None:
        """Update aggregated metrics for an agent."""
        agent_name = record.agent_name
        metrics = self._agent_metrics[agent_name]
        
        if not metrics.agent_name:
            metrics.agent_name = agent_name
        
        update_agent_metrics(metrics, record)
        
        # Update execution time average
        await self._update_execution_time_avg(agent_name, record.execution_time_ms)

    async def _update_execution_time_avg(
        self, 
        agent_name: str, 
        execution_time_ms: float
    ) -> None:
        """Update rolling average execution time."""
        window_key = f"{agent_name}:execution_time"
        self._performance_windows[window_key].append(execution_time_ms)
        
        # Calculate new average
        times = list(self._performance_windows[window_key])
        if times:
            self._agent_metrics[agent_name].avg_execution_time_ms = sum(times) / len(times)

    async def _track_performance(self, record: AgentOperationRecord) -> None:
        """Track performance metrics in time windows."""
        agent_name = record.agent_name
        
        # Track execution times
        exec_key = f"{agent_name}:execution_time"
        self._performance_windows[exec_key].append(record.execution_time_ms)
        
        # Track memory usage
        if record.memory_usage_mb > 0:
            mem_key = f"{agent_name}:memory"
            self._performance_windows[mem_key].append(record.memory_usage_mb)
        
        # Track CPU usage
        if record.cpu_usage_percent > 0:
            cpu_key = f"{agent_name}:cpu"
            self._performance_windows[cpu_key].append(record.cpu_usage_percent)

    async def _check_alert_conditions(self, record: AgentOperationRecord) -> None:
        """Check if alert conditions are met."""
        agent_name = record.agent_name
        metrics = self._agent_metrics[agent_name]
        
        # Check error rate threshold
        if metrics.error_rate > self.error_rate_threshold:
            await self._trigger_error_rate_alert(agent_name, metrics.error_rate)
        
        # Check timeout threshold
        if record.execution_time_ms > (self.timeout_threshold * 1000):
            await self._trigger_timeout_alert(agent_name, record.execution_time_ms)
        
        # Check resource thresholds
        if record.memory_usage_mb > self.memory_threshold_mb:
            await self._trigger_memory_alert(agent_name, record.memory_usage_mb)
        
        if record.cpu_usage_percent > self.cpu_threshold_percent:
            await self._trigger_cpu_alert(agent_name, record.cpu_usage_percent)

    async def _trigger_error_rate_alert(self, agent_name: str, error_rate: float) -> None:
        """Trigger alert for high error rate."""
        logger.warning(
            f"HIGH ERROR RATE ALERT: Agent {agent_name} has error rate of {error_rate:.2%}"
        )

    async def _trigger_timeout_alert(self, agent_name: str, execution_time_ms: float) -> None:
        """Trigger alert for operation timeout."""
        logger.warning(
            f"TIMEOUT ALERT: Agent {agent_name} operation took {execution_time_ms:.0f}ms"
        )

    async def _trigger_memory_alert(self, agent_name: str, memory_mb: float) -> None:
        """Trigger alert for high memory usage."""
        logger.warning(
            f"MEMORY ALERT: Agent {agent_name} using {memory_mb:.0f}MB memory"
        )

    async def _trigger_cpu_alert(self, agent_name: str, cpu_percent: float) -> None:
        """Trigger alert for high CPU usage."""
        logger.warning(
            f"CPU ALERT: Agent {agent_name} using {cpu_percent:.1f}% CPU"
        )

    def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get current metrics for an agent."""
        return self._agent_metrics.get(agent_name)

    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        return dict(self._agent_metrics)

    def get_active_operations(self) -> Dict[str, AgentOperationRecord]:
        """Get currently active operations."""
        return self._active_operations.copy()

    def get_recent_operations(
        self, 
        agent_name: Optional[str] = None,
        hours: int = 1
    ) -> List[AgentOperationRecord]:
        """Get recent operations within time window."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        recent_ops = []
        for record in self._operation_records:
            if record.start_time >= cutoff_time:
                if agent_name is None or record.agent_name == agent_name:
                    recent_ops.append(record)
        
        return sorted(recent_ops, key=lambda x: x.start_time, reverse=True)

    def get_health_score(self, agent_name: str) -> float:
        """Calculate health score for an agent (0.0 to 1.0)."""
        metrics = self._agent_metrics.get(agent_name)
        if not metrics:
            return 1.0
        return calculate_health_score(metrics)

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide agent metrics overview."""
        total_operations = sum(m.total_operations for m in self._agent_metrics.values())
        total_failures = sum(m.failed_operations for m in self._agent_metrics.values())
        
        active_agents = len([m for m in self._agent_metrics.values() if m.total_operations > 0])
        unhealthy_agents = len([
            name for name in self._agent_metrics.keys() 
            if self.get_health_score(name) < 0.7
        ])
        
        return {
            "total_operations": total_operations,
            "total_failures": total_failures,
            "system_error_rate": total_failures / total_operations if total_operations > 0 else 0.0,
            "active_agents": active_agents,
            "unhealthy_agents": unhealthy_agents,
            "active_operations": len(self._active_operations),
            "buffer_utilization": len(self._operation_records) / self.max_buffer_size
        }

    async def cleanup_old_data(self, hours: int = 24) -> None:
        """Clean up old operation records."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        # Filter operation records
        filtered_records = deque(maxlen=self.max_buffer_size)
        for record in self._operation_records:
            if record.start_time >= cutoff_time:
                filtered_records.append(record)
        
        self._operation_records = filtered_records
        logger.info(f"Cleaned up agent metrics data older than {hours} hours")