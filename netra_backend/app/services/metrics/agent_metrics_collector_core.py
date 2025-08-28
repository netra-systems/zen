"""
Core agent metrics collection functionality.
Handles operation tracking and metrics aggregation.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.metrics import TimeSeriesPoint
from netra_backend.app.services.metrics.agent_metrics_models import (
    AgentMetrics,
    AgentMetricType,
    AgentOperationRecord,
    FailureType,
    calculate_health_score,
    calculate_operation_metrics,
    create_operation_record,
    update_agent_metrics,
)
from netra_backend.app.services.metrics.metric_aggregator import MetricAggregator
from netra_backend.app.services.metrics.metric_formatter import MetricFormatter
from netra_backend.app.services.metrics.metric_publisher import MetricPublisher
from netra_backend.app.services.metrics.metric_reader import MetricReader

logger = central_logger.get_logger(__name__)


class AgentMetricsCollectorCore:
    """Core functionality for agent metrics collection."""
    
    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self._init_data_structures()
        self._init_performance_tracking()
        self._init_components()
    
    def _init_data_structures(self) -> None:
        """Initialize core data structures."""
        self._operation_records = deque(maxlen=self.max_buffer_size)
        self._active_operations: Dict[str, AgentOperationRecord] = {}
        self._agent_metrics: Dict[str, AgentMetrics] = defaultdict(AgentMetrics)
    
    def _init_performance_tracking(self) -> None:
        """Initialize performance tracking windows."""
        self._performance_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
    
    def _init_components(self) -> None:
        """Initialize modular components."""
        alert_thresholds = self._get_alert_thresholds()
        self._reader = MetricReader(self._operation_records, self._agent_metrics)
        self._aggregator = MetricAggregator(self._agent_metrics, self._performance_windows)
        self._formatter = MetricFormatter()
        self._publisher = MetricPublisher(alert_thresholds)

    def _get_alert_thresholds(self) -> Dict[str, float]:
        """Get alert threshold configuration."""
        return {
            'error_rate': 0.2, 'timeout': 30.0,
            'memory': 1024.0, 'cpu': 80.0
        }

    async def start_operation(
        self, 
        agent_name: str, 
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking an agent operation."""
        record = create_operation_record(agent_name, operation_type, metadata)
        return self._register_and_log_operation(record)

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
        record = self._get_and_remove_operation(operation_id)
        if not record:
            return None
        
        completion_data = self._build_completion_data(
            success, failure_type, error_message, memory_usage_mb, cpu_usage_percent, metadata
        )
        return await self._finalize_and_process_operation(record, completion_data)
    
    def _get_and_remove_operation(self, operation_id: str) -> Optional[AgentOperationRecord]:
        """Get and remove operation from active tracking."""
        if operation_id not in self._active_operations:
            logger.warning(f"Operation {operation_id} not found")
            return None
        return self._active_operations.pop(operation_id)
    
    def _register_and_log_operation(self, record: AgentOperationRecord) -> str:
        """Register operation and log start."""
        self._active_operations[record.operation_id] = record
        logger.debug(f"Started tracking {record.agent_name} operation {record.operation_id}")
        return record.operation_id

    def _build_completion_data(self, success: bool, failure_type: Optional[FailureType], error_message: Optional[str], 
                              memory_usage_mb: float, cpu_usage_percent: float, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build completion data dictionary."""
        basic_data = {'success': success, 'failure_type': failure_type, 'error_message': error_message}
        resource_data = {'memory_usage_mb': memory_usage_mb, 'cpu_usage_percent': cpu_usage_percent, 'metadata': metadata}
        return {**basic_data, **resource_data}

    async def _finalize_and_process_operation(self, record: AgentOperationRecord, completion_data: Dict[str, Any]) -> AgentOperationRecord:
        """Finalize operation record and process completion."""
        self._formatter.finalize_operation_record(record, completion_data)
        await self._process_completed_operation(record)
        return record
    
    
    
    async def _process_completed_operation(self, record: AgentOperationRecord) -> None:
        """Process completed operation with metrics and alerts."""
        self._operation_records.append(record)
        await self._update_agent_metrics(record)
        await self._track_performance(record)
        await self._check_alert_conditions(record)

    async def record_timeout(
        self, 
        operation_id: str, 
        timeout_duration_ms: float
    ) -> None:
        """Record a timeout for an operation."""
        completion_data = self._formatter.create_timeout_completion_data(timeout_duration_ms)
        await self._end_operation_with_data(operation_id, completion_data)

    async def record_validation_error(
        self, 
        operation_id: str, 
        validation_error: str
    ) -> None:
        """Record a validation error for an operation."""
        completion_data = self._formatter.create_validation_error_completion_data(validation_error)
        await self._end_operation_with_data(operation_id, completion_data)

    async def _end_operation_with_data(self, operation_id: str, completion_data: Dict[str, Any]) -> None:
        """End operation with pre-built completion data."""
        await self.end_operation(
            operation_id=operation_id, success=completion_data['success'],
            failure_type=completion_data['failure_type'], error_message=completion_data['error_message']
        )

    async def _update_agent_metrics(self, record: AgentOperationRecord) -> None:
        """Update aggregated metrics for an agent."""
        agent_name = record.agent_name
        metrics = self._aggregator.get_or_init_agent_metrics(agent_name)
        update_agent_metrics(metrics, record)
        self._aggregator.update_execution_time_avg(agent_name, record.execution_time_ms)
    


    async def _track_performance(self, record: AgentOperationRecord) -> None:
        """Track performance metrics in time windows."""
        agent_name = record.agent_name
        self._track_execution_time(agent_name, record.execution_time_ms)
        self._track_memory_usage(agent_name, record.memory_usage_mb)
        self._track_cpu_usage(agent_name, record.cpu_usage_percent)
    
    def _track_execution_time(self, agent_name: str, execution_time_ms: float) -> None:
        """Track execution time performance."""
        exec_key = f"{agent_name}:execution_time"
        self._performance_windows[exec_key].append(execution_time_ms)
    
    def _track_memory_usage(self, agent_name: str, memory_usage_mb: float) -> None:
        """Track memory usage performance."""
        if memory_usage_mb > 0:
            mem_key = f"{agent_name}:memory"
            self._performance_windows[mem_key].append(memory_usage_mb)
    
    def _track_cpu_usage(self, agent_name: str, cpu_usage_percent: float) -> None:
        """Track CPU usage performance."""
        if cpu_usage_percent > 0:
            cpu_key = f"{agent_name}:cpu"
            self._performance_windows[cpu_key].append(cpu_usage_percent)

    async def _check_alert_conditions(self, record: AgentOperationRecord) -> None:
        """Check if alert conditions are met."""
        agent_metrics = self._agent_metrics[record.agent_name]
        await self._publisher.check_alert_conditions(record, agent_metrics)

    def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get current metrics for an agent."""
        return self._reader.get_agent_metrics(agent_name)

    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        return self._reader.get_all_agent_metrics()

    def get_active_operations(self) -> Dict[str, AgentOperationRecord]:
        """Get currently active operations."""
        return self._active_operations.copy()

    def get_recent_operations(
        self, 
        agent_name: Optional[str] = None,
        hours: int = 1
    ) -> List[AgentOperationRecord]:
        """Get recent operations within time window."""
        return self._reader.get_recent_operations(agent_name, hours)
    
    

    def get_health_score(self, agent_name: str) -> float:
        """Calculate health score for an agent (0.0 to 1.0)."""
        metrics = self._agent_metrics.get(agent_name)
        if not metrics:
            return 1.0
        return calculate_health_score(metrics)

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide agent metrics overview."""
        operation_stats = self._aggregator.calculate_operation_stats()
        agent_stats = self._aggregator.calculate_agent_stats()
        system_stats = self._get_system_stats()
        return self._formatter.format_system_overview(operation_stats, agent_stats, system_stats)
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system-level statistics."""
        buffer_utilization = len(self._operation_records) / self.max_buffer_size
        return self._aggregator.calculate_system_stats(len(self._active_operations), buffer_utilization)
    
    

    async def cleanup_old_data(self, hours: int = 24) -> None:
        """Clean up old operation records."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        self._operation_records = self._reader.filter_recent_records(cutoff_time, self.max_buffer_size)
        logger.info(f"Cleaned up agent metrics data older than {hours} hours")
    
