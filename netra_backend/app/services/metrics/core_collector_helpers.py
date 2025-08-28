"""
Core metrics collector helper functions.
Contains utility functions for metrics calculation and data processing.
"""

import time
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.schemas.metrics import (
    CorpusMetric,
    MetricType,
    OperationMetrics,
    TimeSeriesPoint,
)


def create_operation_data(corpus_id: str, operation_type: str) -> Dict[str, Any]:
    """Create operation tracking data."""
    start_time = datetime.now(UTC)
    return {
        "corpus_id": corpus_id,
        "operation_type": operation_type,
        "start_time": start_time,
        "start_timestamp": time.time()
    }


def calculate_timing_data(start_timestamp: float, start_time: datetime) -> Dict[str, Any]:
    """Calculate timing data for operation metrics."""
    end_time = datetime.now(UTC)
    duration_ms = int((time.time() - start_timestamp) * 1000)
    return {"end_time": end_time, "duration_ms": duration_ms}


def prepare_base_metrics_data(operation_data: Dict[str, Any], success: bool, 
                             error_message: Optional[str], records_processed: Optional[int]) -> Dict[str, Any]:
    """Prepare base metrics data."""
    return {
        "operation_type": operation_data["operation_type"],
        "start_time": operation_data["start_time"],
        "success": success,
        "error_message": error_message,
        "records_processed": records_processed
    }


def build_operation_metrics(base_data: Dict[str, Any], timing_data: Dict[str, Any], 
                           throughput: Optional[float]) -> OperationMetrics:
    """Build OperationMetrics object from base and timing data."""
    return OperationMetrics(
        operation_type=base_data["operation_type"],
        start_time=base_data["start_time"],
        end_time=timing_data["end_time"],
        duration_ms=timing_data["duration_ms"],
        success=base_data["success"],
        error_message=base_data["error_message"],
        records_processed=base_data["records_processed"],
        throughput_per_second=throughput
    )


def calculate_throughput(records: Optional[int], duration_ms: int) -> Optional[float]:
    """Calculate throughput in records per second"""
    if not records or duration_ms <= 0:
        return None
    return (records * 1000.0) / duration_ms


def get_generation_metric_base_fields(corpus_id: str, duration_ms: int) -> Dict[str, Any]:
    """Get base fields for generation time metric."""
    return {
        "metric_id": str(uuid.uuid4()),
        "corpus_id": corpus_id,
        "metric_type": MetricType.GENERATION_TIME,
        "value": duration_ms,
        "unit": "milliseconds",
        "timestamp": datetime.now(UTC)
    }


def get_generation_metric_additional_fields() -> Dict[str, Any]:
    """Get additional fields for generation time metric."""
    return {
        "tags": {"source": "generation"},
        "metadata": {"operation": "content_generation"}
    }


def calculate_success_rate_from_counts(counts: Dict[str, int]) -> float:
    """Calculate success rate from success/failure counts."""
    total = counts["success"] + counts["failure"]
    return counts["success"] / total if total > 0 else 0.0


def calculate_average_time(times: List[float]) -> float:
    """Calculate average time from list of times."""
    return sum(times) / len(times) if times else 0.0


def is_entry_valid_for_time_series(entry: Dict, corpus_id: str, cutoff_time: datetime) -> bool:
    """Check if entry is valid for time series data."""
    if entry.get("timestamp", datetime.min.replace(tzinfo=UTC)) < cutoff_time:
        return False
    return "metrics" in entry and entry.get("corpus_id") == corpus_id


def create_time_series_point(entry: Dict, metric_type: str) -> Optional[TimeSeriesPoint]:
    """Create time series point from entry."""
    metrics = entry["metrics"]
    value = extract_metric_value(metrics, metric_type)
    if value is not None:
        return TimeSeriesPoint(
            timestamp=entry["timestamp"],
            value=value,
            tags={"operation": metrics.operation_type}
        )
    return None


def extract_metric_value(metrics: OperationMetrics, metric_type: str) -> Optional[float]:
    """Extract specific metric value from operation metrics"""
    mapping = {
        "duration": metrics.duration_ms,
        "throughput": metrics.throughput_per_second,
        "records": metrics.records_processed,
        "success": 1.0 if metrics.success else 0.0
    }
    return mapping.get(metric_type)


def filter_recent_metrics(metrics_buffer: deque, cutoff_time: datetime, max_buffer_size: int) -> deque:
    """Filter and return recent metrics from buffer."""
    filtered_buffer = deque(maxlen=max_buffer_size)
    for entry in metrics_buffer:
        if entry.get("timestamp", datetime.min.replace(tzinfo=UTC)) >= cutoff_time:
            filtered_buffer.append(entry)
    return filtered_buffer