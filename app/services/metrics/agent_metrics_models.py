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
    agent_name: str
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
    operation_id = str(uuid.uuid4())
    
    return AgentOperationRecord(
        operation_id=operation_id,
        agent_name=agent_name,
        operation_type=operation_type,
        start_time=datetime.now(UTC),
        metadata=metadata or {}
    )


def calculate_operation_metrics(record: AgentOperationRecord) -> Dict[str, Any]:
    """Calculate metrics from an operation record."""
    if record.end_time and record.start_time:
        duration = record.end_time - record.start_time
        execution_time_ms = duration.total_seconds() * 1000
    else:
        execution_time_ms = 0.0
    
    return {
        "execution_time_ms": execution_time_ms,
        "success": record.success,
        "failure_type": record.failure_type,
        "memory_usage_mb": record.memory_usage_mb,
        "cpu_usage_percent": record.cpu_usage_percent
    }


def update_agent_metrics(metrics: AgentMetrics, record: AgentOperationRecord) -> None:
    """Update agent metrics with new operation record."""
    metrics.total_operations += 1
    metrics.last_operation_time = record.end_time
    
    if record.success:
        metrics.successful_operations += 1
    else:
        metrics.failed_operations += 1
        if record.failure_type:
            if record.failure_type not in metrics.failure_breakdown:
                metrics.failure_breakdown[record.failure_type] = 0
            metrics.failure_breakdown[record.failure_type] += 1
    
    # Calculate rates
    if metrics.total_operations > 0:
        metrics.success_rate = metrics.successful_operations / metrics.total_operations
        metrics.error_rate = metrics.failed_operations / metrics.total_operations
    
    # Track specific error types
    if record.failure_type == FailureType.TIMEOUT:
        metrics.timeout_count += 1
    elif record.failure_type == FailureType.VALIDATION_ERROR:
        metrics.validation_error_count += 1


def calculate_health_score(metrics: AgentMetrics) -> float:
    """Calculate health score for an agent (0.0 to 1.0)."""
    if metrics.total_operations == 0:
        return 1.0  # No data means healthy
    
    # Calculate health score based on multiple factors
    success_factor = metrics.success_rate
    
    # Penalize high execution times
    avg_time_factor = max(0.0, 1.0 - (metrics.avg_execution_time_ms / 30000))
    
    # Penalize timeouts and validation errors
    timeout_penalty = min(0.3, metrics.timeout_count / metrics.total_operations)
    validation_penalty = min(0.2, metrics.validation_error_count / metrics.total_operations)
    
    score = (success_factor * 0.5 + 
            avg_time_factor * 0.3 - 
            timeout_penalty - 
            validation_penalty)
    
    return max(0.0, min(1.0, score))