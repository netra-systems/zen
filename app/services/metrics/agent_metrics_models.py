"""
Agent metrics data models and enums.
Contains data classes and types for agent metrics collection.
"""

import time
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import uuid


class AgentMetricType(Enum):
    """Types of agent metrics."""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    TIMEOUT_RATE = "timeout_rate"
    VALIDATION_ERROR_RATE = "validation_error_rate"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"


class FailureType(Enum):
    """Types of agent failures."""
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    WEBSOCKET_ERROR = "websocket_error"
    RESOURCE_ERROR = "resource_error"
    DEPENDENCY_ERROR = "dependency_error"


@dataclass
class AgentOperationRecord:
    """Record of a single agent operation."""
    operation_id: str
    agent_name: str
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    failure_type: Optional[FailureType] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentMetrics:
    """Aggregated metrics for an agent."""
    agent_name: str = ""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    avg_execution_time_ms: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    timeout_count: int = 0
    validation_error_count: int = 0
    last_operation_time: Optional[datetime] = None
    failure_breakdown: Dict[FailureType, int] = field(default_factory=dict)


def create_operation_record(
    agent_name: str, 
    operation_type: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> AgentOperationRecord:
    """Create a new operation record."""
    operation_id = _generate_operation_id()
    return _build_operation_record(operation_id, agent_name, operation_type, metadata)


def _generate_operation_id() -> str:
    """Generate unique operation ID."""
    return str(uuid.uuid4())


def _build_operation_record(operation_id: str, agent_name: str, operation_type: str, metadata: Optional[Dict[str, Any]]) -> AgentOperationRecord:
    """Build operation record with provided data."""
    base_record = _create_base_record(operation_id, agent_name, operation_type)
    base_record.metadata = metadata or {}
    return base_record


def _create_base_record(operation_id: str, agent_name: str, operation_type: str) -> AgentOperationRecord:
    """Create base operation record."""
    start_time = datetime.now(UTC)
    return AgentOperationRecord(
        operation_id=operation_id, agent_name=agent_name, 
        operation_type=operation_type, start_time=start_time
    )


def calculate_operation_metrics(record: AgentOperationRecord) -> Dict[str, Any]:
    """Calculate metrics from an operation record."""
    execution_time_ms = _calculate_execution_time(record)
    return _build_metrics_dict(record, execution_time_ms)


def _calculate_execution_time(record: AgentOperationRecord) -> float:
    """Calculate execution time from record timestamps."""
    if record.end_time and record.start_time:
        duration = record.end_time - record.start_time
        return duration.total_seconds() * 1000
    return 0.0


def _build_metrics_dict(record: AgentOperationRecord, execution_time_ms: float) -> Dict[str, Any]:
    """Build metrics dictionary from record data."""
    base_metrics = _get_base_metrics(execution_time_ms, record.success, record.failure_type)
    resource_metrics = _get_resource_metrics(record.memory_usage_mb, record.cpu_usage_percent)
    return {**base_metrics, **resource_metrics}


def _get_base_metrics(execution_time_ms: float, success: bool, failure_type: Optional[FailureType]) -> Dict[str, Any]:
    """Get base metric values."""
    return {
        "execution_time_ms": execution_time_ms,
        "success": success,
        "failure_type": failure_type
    }


def _get_resource_metrics(memory_usage_mb: float, cpu_usage_percent: float) -> Dict[str, Any]:
    """Get resource usage metrics."""
    return {
        "memory_usage_mb": memory_usage_mb,
        "cpu_usage_percent": cpu_usage_percent
    }


def update_agent_metrics(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update agent metrics with new operation record."""
    _update_operation_counts(metrics, record)
    _update_failure_breakdown(metrics, record)
    _calculate_success_rates(metrics)
    _update_specific_error_counts(metrics, record)


def _update_operation_counts(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update basic operation counts."""
    _increment_total_operations(metrics, record)
    _update_success_failure_counts(metrics, record)


def _increment_total_operations(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Increment total operation count and update timestamp."""
    metrics.total_operations += 1
    metrics.last_operation_time = record.end_time


def _update_success_failure_counts(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update success/failure operation counts."""
    if record.success:
        metrics.successful_operations += 1
    else:
        metrics.failed_operations += 1


def _update_failure_breakdown(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update failure breakdown if operation failed."""
    if not record.success and record.failure_type:
        if record.failure_type not in metrics.failure_breakdown:
            metrics.failure_breakdown[record.failure_type] = 0
        metrics.failure_breakdown[record.failure_type] += 1


def _calculate_success_rates(metrics: AgentMetrics) -> None:
    """Calculate success and error rates."""
    if metrics.total_operations > 0:
        metrics.success_rate = metrics.successful_operations / metrics.total_operations
        metrics.error_rate = metrics.failed_operations / metrics.total_operations


def _update_specific_error_counts(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update specific error type counts."""
    if record.failure_type == FailureType.TIMEOUT:
        metrics.timeout_count += 1
    elif record.failure_type == FailureType.VALIDATION_ERROR:
        metrics.validation_error_count += 1


def calculate_health_score(metrics: AgentMetrics) -> float:
    """Calculate health score for an agent (0.0 to 1.0)."""
    if metrics.total_operations == 0:
        return 1.0  # No data means healthy
    factors = _calculate_health_factors(metrics)
    return _compute_final_score(factors)


def _calculate_health_factors(metrics: AgentMetrics) -> Dict[str, float]:
    """Calculate individual health factors."""
    success_factor = metrics.success_rate
    avg_time_factor = max(0.0, 1.0 - (metrics.avg_execution_time_ms / 30000))
    timeout_penalty = min(0.3, metrics.timeout_count / metrics.total_operations)
    validation_penalty = min(0.2, metrics.validation_error_count / metrics.total_operations)
    return {'success': success_factor, 'time': avg_time_factor, 'timeout': timeout_penalty, 'validation': validation_penalty}


def _compute_final_score(factors: Dict[str, float]) -> float:
    """Compute final health score from factors."""
    score = (factors['success'] * 0.5 + 
            factors['time'] * 0.3 - 
            factors['timeout'] - 
            factors['validation'])
    return max(0.0, min(1.0, score))