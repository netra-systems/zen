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
        start_time = datetime.now(UTC)
        
        self._active_operations[operation_id] = {
            "corpus_id": corpus_id,
            "operation_type": operation_type,
            "start_time": start_time,
            "start_timestamp": time.time()
        }
        
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
        end_time = datetime.now(UTC)
        duration_ms = int((time.time() - operation_data["start_timestamp"]) * 1000)
        
        return OperationMetrics(
            operation_type=operation_data["operation_type"],
            start_time=operation_data["start_time"],
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            records_processed=records_processed,
            throughput_per_second=self._calculate_throughput(records_processed, duration_ms)
        )
    
    def _calculate_throughput(self, records: Optional[int], duration_ms: int) -> Optional[float]:
        """Calculate throughput in records per second"""
        if not records or duration_ms <= 0:
            return None
        return (records * 1000.0) / duration_ms
    
    async def _record_operation_metrics(self, corpus_id: str, metrics: OperationMetrics):
        """Record operation metrics internally"""
        operation_key = f"{corpus_id}:{metrics.operation_type}"
        
        # Track timing
        self._operation_times[operation_key].append(metrics.duration_ms)
        
        # Track success/failure
        if metrics.success:
            self._success_counts[operation_key]["success"] += 1
        else:
            self._success_counts[operation_key]["failure"] += 1
        
        # Buffer for export
        self._metrics_buffer.append({
            "corpus_id": corpus_id,
            "metrics": metrics,
            "timestamp": datetime.now(UTC)
        })
        
        logger.debug(f"Recorded metrics for {operation_key}: {metrics.duration_ms}ms, success={metrics.success}")
    
    async def record_generation_time(self, corpus_id: str, duration_ms: int):
        """Record generation time metric"""
        metric = self._create_generation_time_metric(corpus_id, duration_ms)
        await self._store_metric(metric)
    
    def _create_generation_time_metric(self, corpus_id: str, duration_ms: int) -> CorpusMetric:
        """Create generation time metric."""
        return CorpusMetric(
            metric_id=str(uuid.uuid4()),
            corpus_id=corpus_id,
            metric_type=MetricType.GENERATION_TIME,
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.now(UTC),
            tags={"source": "generation"},
            metadata={"operation": "content_generation"}
        )
    
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
        return self._calculate_success_rate_from_counts(counts)
    
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
    
    def _calculate_success_rate_from_counts(self, counts: Dict[str, int]) -> float:
        """Calculate success rate from success/failure counts."""
        total = counts["success"] + counts["failure"]
        return counts["success"] / total if total > 0 else 0.0
    
    def get_average_generation_time(self, corpus_id: str, operation_type: str = None) -> float:
        """Get average generation time"""
        times = self._get_operation_times_for_corpus(corpus_id, operation_type)
        return self._calculate_average_time(times)
    
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
    
    def _calculate_average_time(self, times: List[float]) -> float:
        """Calculate average time from list of times."""
        return sum(times) / len(times) if times else 0.0
    
    def get_time_series_data(
        self, 
        corpus_id: str, 
        metric_type: str,
        time_range_minutes: int = 60
    ) -> List[TimeSeriesPoint]:
        """Get time series data for visualization"""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_range_minutes)
        points = self._extract_time_series_points(corpus_id, metric_type, cutoff_time)
        return sorted(points, key=lambda x: x.timestamp)
    
    def _extract_time_series_points(self, corpus_id: str, metric_type: str, cutoff_time: datetime) -> List[TimeSeriesPoint]:
        """Extract time series points from metrics buffer."""
        points = []
        for entry in self._metrics_buffer:
            if self._is_entry_valid_for_time_series(entry, corpus_id, cutoff_time):
                point = self._create_time_series_point(entry, metric_type)
                if point:
                    points.append(point)
        return points
    
    def _is_entry_valid_for_time_series(self, entry: Dict, corpus_id: str, cutoff_time: datetime) -> bool:
        """Check if entry is valid for time series data."""
        if entry.get("timestamp", datetime.min.replace(tzinfo=UTC)) < cutoff_time:
            return False
        return "metrics" in entry and entry.get("corpus_id") == corpus_id
    
    def _create_time_series_point(self, entry: Dict, metric_type: str) -> Optional[TimeSeriesPoint]:
        """Create time series point from entry."""
        metrics = entry["metrics"]
        value = self._extract_metric_value(metrics, metric_type)
        if value is not None:
            return TimeSeriesPoint(
                timestamp=entry["timestamp"],
                value=value,
                tags={"operation": metrics.operation_type}
            )
        return None
    
    def _extract_metric_value(self, metrics: OperationMetrics, metric_type: str) -> Optional[float]:
        """Extract specific metric value from operation metrics"""
        mapping = {
            "duration": metrics.duration_ms,
            "throughput": metrics.throughput_per_second,
            "records": metrics.records_processed,
            "success": 1.0 if metrics.success else 0.0
        }
        return mapping.get(metric_type)
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status"""
        return {
            "active_operations": len(self._active_operations),
            "buffered_metrics": len(self._metrics_buffer),
            "tracked_corpus_operations": len(self._operation_times),
            "success_counters": len(self._success_counts),
            "buffer_utilization": len(self._metrics_buffer) / self.max_buffer_size
        }
    
    async def clear_old_data(self, age_hours: int = 24):
        """Clear old data from buffers"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=age_hours)
        self._metrics_buffer = self._filter_recent_metrics(cutoff_time)
        logger.info(f"Cleared metrics data older than {age_hours} hours")
    
    def _filter_recent_metrics(self, cutoff_time: datetime) -> deque:
        """Filter and return recent metrics from buffer."""
        filtered_buffer = deque(maxlen=self.max_buffer_size)
        for entry in self._metrics_buffer:
            if entry.get("timestamp", datetime.min.replace(tzinfo=UTC)) >= cutoff_time:
                filtered_buffer.append(entry)
        return filtered_buffer