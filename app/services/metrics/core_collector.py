"""
Core metrics collection for corpus operations
Handles generation time tracking and success rate monitoring
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
import time
import uuid

from app.logging_config import central_logger
from app.schemas.Metrics import (
    CorpusMetric, MetricType, OperationMetrics, TimeSeriesPoint
)
from .core_collector_helpers import (
    create_operation_data, calculate_timing_data, prepare_base_metrics_data,
    build_operation_metrics, calculate_throughput, get_generation_metric_base_fields,
    get_generation_metric_additional_fields, calculate_success_rate_from_counts,
    calculate_average_time, is_entry_valid_for_time_series, create_time_series_point,
    extract_metric_value, filter_recent_metrics
)

logger = central_logger.get_logger(__name__)


class CoreMetricsCollector:
    """Collects core operational metrics for corpus operations"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._operation_times = defaultdict(lambda: deque(maxlen=max_buffer_size))
        self._success_counts = defaultdict(lambda: {"success": 0, "failure": 0})
        self._active_operations = {}
        self._metrics_buffer = deque(maxlen=max_buffer_size)
    
    async def start_operation(self, corpus_id: str, operation_type: str) -> str:
        """Start tracking an operation"""
        operation_id = str(uuid.uuid4())
        operation_data = create_operation_data(corpus_id, operation_type)
        self._active_operations[operation_id] = operation_data
        logger.debug(f"Started tracking operation {operation_id} for corpus {corpus_id}")
        return operation_id
    
    async def end_operation(
        self, 
        operation_id: str, 
        success: bool = True,
        records_processed: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[OperationMetrics]:
        """End operation tracking and record metrics"""
        operation_data = self._get_and_remove_operation_data(operation_id)
        if not operation_data:
            return None
        return await self._process_operation_completion(operation_data, success, records_processed, error_message)
    
    async def _process_operation_completion(self, operation_data: Dict[str, Any], success: bool, 
                                          records_processed: Optional[int], error_message: Optional[str]) -> OperationMetrics:
        """Process operation completion and create metrics."""
        metrics = self._create_operation_metrics(operation_data, success, records_processed, error_message)
        await self._record_operation_metrics(operation_data["corpus_id"], metrics)
        return metrics
    
    def _get_and_remove_operation_data(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get and remove operation data from active tracking."""
        if operation_id not in self._active_operations:
            logger.warning(f"Operation {operation_id} not found in active operations")
            return None
        return self._active_operations.pop(operation_id)
    
    def _create_operation_metrics(self, operation_data: Dict[str, Any], success: bool, 
                                 records_processed: Optional[int], error_message: Optional[str]) -> OperationMetrics:
        """Create operation metrics from operation data."""
        timing_data = calculate_timing_data(operation_data["start_timestamp"], operation_data["start_time"])
        base_data = prepare_base_metrics_data(operation_data, success, error_message, records_processed)
        throughput = calculate_throughput(records_processed, timing_data["duration_ms"])
        return build_operation_metrics(base_data, timing_data, throughput)
    
    async def _record_operation_metrics(self, corpus_id: str, metrics: OperationMetrics):
        """Record operation metrics internally"""
        operation_key = f"{corpus_id}:{metrics.operation_type}"
        self._track_timing_metrics(operation_key, metrics.duration_ms)
        self._track_success_failure_metrics(operation_key, metrics.success)
        self._buffer_metrics_for_export(corpus_id, metrics)
        logger.debug(f"Recorded metrics for {operation_key}: {metrics.duration_ms}ms, success={metrics.success}")
    
    def _track_timing_metrics(self, operation_key: str, duration_ms: int) -> None:
        """Track timing metrics for operation."""
        self._operation_times[operation_key].append(duration_ms)
    
    def _track_success_failure_metrics(self, operation_key: str, success: bool) -> None:
        """Track success/failure metrics for operation."""
        if success:
            self._success_counts[operation_key]["success"] += 1
        else:
            self._success_counts[operation_key]["failure"] += 1
    
    def _buffer_metrics_for_export(self, corpus_id: str, metrics: OperationMetrics) -> None:
        """Buffer metrics for export."""
        self._metrics_buffer.append({
            "corpus_id": corpus_id,
            "metrics": metrics,
            "timestamp": datetime.now(UTC)
        })
    
    async def record_generation_time(self, corpus_id: str, duration_ms: int):
        """Record generation time metric"""
        metric = self._create_generation_time_metric(corpus_id, duration_ms)
        await self._store_metric(metric)
    
    def _create_generation_time_metric(self, corpus_id: str, duration_ms: int) -> CorpusMetric:
        """Create generation time metric."""
        base_fields = get_generation_metric_base_fields(corpus_id, duration_ms)
        additional_fields = get_generation_metric_additional_fields()
        return CorpusMetric(**base_fields, **additional_fields)
    
    async def _store_metric(self, metric: CorpusMetric):
        """Store individual metric"""
        self._metrics_buffer.append({
            "type": "individual_metric",
            "metric": metric,
            "timestamp": datetime.now(UTC)
        })
    
    def get_success_rate(self, corpus_id: str, operation_type: str = None) -> float:
        """Calculate success rate for operations"""
        counts = self._get_success_counts_for_corpus(corpus_id, operation_type)
        return calculate_success_rate_from_counts(counts)
    
    def _get_success_counts_for_corpus(self, corpus_id: str, operation_type: Optional[str]) -> Dict[str, int]:
        """Get success counts for corpus and operation type."""
        if operation_type:
            key = f"{corpus_id}:{operation_type}"
            return self._success_counts.get(key, {"success": 0, "failure": 0})
        return self._aggregate_corpus_success_counts(corpus_id)
    
    def _aggregate_corpus_success_counts(self, corpus_id: str) -> Dict[str, int]:
        """Aggregate success counts for all operations in corpus."""
        counts = {"success": 0, "failure": 0}
        for key, data in self._success_counts.items():
            if key.startswith(f"{corpus_id}:"):
                counts["success"] += data["success"]
                counts["failure"] += data["failure"]
        return counts
    
    def get_average_generation_time(self, corpus_id: str, operation_type: str = None) -> float:
        """Get average generation time"""
        times = self._get_operation_times_for_corpus(corpus_id, operation_type)
        return calculate_average_time(times)
    
    def _get_operation_times_for_corpus(self, corpus_id: str, operation_type: Optional[str]) -> List[float]:
        """Get operation times for corpus and operation type."""
        if operation_type:
            key = f"{corpus_id}:{operation_type}"
            return list(self._operation_times.get(key, []))
        return self._aggregate_corpus_operation_times(corpus_id)
    
    def _aggregate_corpus_operation_times(self, corpus_id: str) -> List[float]:
        """Aggregate operation times for all operations in corpus."""
        times = []
        for key, data in self._operation_times.items():
            if key.startswith(f"{corpus_id}:"):
                times.extend(list(data))
        return times
    
    def get_time_series_data(
        self, 
        corpus_id: str, 
        metric_type: str,
        time_range_minutes: int = 60
    ) -> List[TimeSeriesPoint]:
        """Get time series data for visualization"""
        cutoff_time = self._calculate_cutoff_time(time_range_minutes)
        points = self._extract_time_series_points(corpus_id, metric_type, cutoff_time)
        return sorted(points, key=lambda x: x.timestamp)
    
    def _extract_time_series_points(self, corpus_id: str, metric_type: str, cutoff_time: datetime) -> List[TimeSeriesPoint]:
        """Extract time series points from metrics buffer."""
        points = []
        for entry in self._metrics_buffer:
            point = self._process_buffer_entry(entry, corpus_id, metric_type, cutoff_time)
            if point:
                points.append(point)
        return points
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status"""
        operational_stats = self._get_operational_stats()
        buffer_stats = self._get_buffer_stats()
        return {**operational_stats, **buffer_stats}
    
    async def clear_old_data(self, age_hours: int = 24):
        """Clear old data from buffers"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=age_hours)
        self._metrics_buffer = filter_recent_metrics(self._metrics_buffer, cutoff_time, self.max_buffer_size)
        logger.info(f"Cleared metrics data older than {age_hours} hours")
    
    def _calculate_cutoff_time(self, time_range_minutes: int) -> datetime:
        """Calculate cutoff time for time series data."""
        return datetime.now(UTC) - timedelta(minutes=time_range_minutes)
    
    def _process_buffer_entry(self, entry: Dict, corpus_id: str, metric_type: str, cutoff_time: datetime) -> Optional[TimeSeriesPoint]:
        """Process buffer entry and create time series point if valid."""
        if is_entry_valid_for_time_series(entry, corpus_id, cutoff_time):
            return create_time_series_point(entry, metric_type)
        return None
    
    def _get_operational_stats(self) -> Dict[str, int]:
        """Get operational statistics."""
        return {
            "active_operations": len(self._active_operations),
            "tracked_corpus_operations": len(self._operation_times),
            "success_counters": len(self._success_counts)
        }
    
    def _get_buffer_stats(self) -> Dict[str, float]:
        """Get buffer-related statistics."""
        return {
            "buffered_metrics": len(self._metrics_buffer),
            "buffer_utilization": len(self._metrics_buffer) / self.max_buffer_size
        }