"""
Performance Measurement Classes for E2E Agent Testing
Classes for measuring latency, throughput, and resource usage.
Maximum 300 lines, functions  <= 8 lines.
"""

import time
from statistics import median, quantiles
from typing import List, Tuple

import psutil

from netra_backend.tests.e2e.validators.performance_metrics import (
    LatencyMetrics,
    ResourceMetrics,
    ThroughputMetrics,
)

class LatencyMeasurer:
    """Measures latency with percentile calculations."""
    
    def __init__(self):
        self.measurements = []
        self.start_times = {}
    
    def start_measurement(self, operation_id: str) -> None:
        """Start latency measurement for operation."""
        self.start_times[operation_id] = time.perf_counter()
    
    def end_measurement(self, operation_id: str) -> float:
        """End latency measurement and return duration."""
        if operation_id not in self.start_times:
            return 0.0
        duration_ms = (time.perf_counter() - self.start_times[operation_id]) * 1000
        self.measurements.append(duration_ms)
        del self.start_times[operation_id]
        return duration_ms
    
    def calculate_metrics(self) -> LatencyMetrics:
        """Calculate latency metrics from measurements."""
        if not self.measurements:
            return LatencyMetrics()
        
        sorted_measurements = sorted(self.measurements)
        percentiles = self._calculate_percentiles(sorted_measurements)
        basic_stats = self._calculate_basic_stats()
        return self._create_latency_metrics(percentiles, basic_stats)
    
    def _calculate_basic_stats(self) -> Tuple[float, float, float]:
        """Calculate basic statistics."""
        mean_ms = sum(self.measurements) / len(self.measurements)
        max_ms = max(self.measurements)
        min_ms = min(self.measurements)
        return mean_ms, max_ms, min_ms
    
    def _create_latency_metrics(self, percentiles: List[float], basic_stats: Tuple[float, float, float]) -> LatencyMetrics:
        """Create latency metrics object."""
        return LatencyMetrics(
            p50_ms=percentiles[0], p95_ms=percentiles[1], p99_ms=percentiles[2],
            mean_ms=basic_stats[0], max_ms=basic_stats[1], min_ms=basic_stats[2]
        )
    
    def _calculate_percentiles(self, sorted_values: List[float]) -> List[float]:
        """Calculate P50, P95, P99 percentiles."""
        if len(sorted_values) == 1:
            return [sorted_values[0]] * 3
        
        p50 = median(sorted_values)
        p95, p99 = self._calculate_high_percentiles(sorted_values)
        return [p50, p95, p99]
    
    def _calculate_high_percentiles(self, sorted_values: List[float]) -> Tuple[float, float]:
        """Calculate P95 and P99 percentiles."""
        if len(sorted_values) >= 20:
            return self._calculate_quartile_percentiles(sorted_values)
        return self._calculate_fallback_percentiles(sorted_values)
    
    def _calculate_quartile_percentiles(self, sorted_values: List[float]) -> Tuple[float, float]:
        """Calculate percentiles using quartile method."""
        quartiles = quantiles(sorted_values, n=100)
        p95 = quartiles[94] if len(quartiles) > 94 else sorted_values[-1]
        p99 = quartiles[98] if len(quartiles) > 98 else sorted_values[-1]
        return p95, p99
    
    def _calculate_fallback_percentiles(self, sorted_values: List[float]) -> Tuple[float, float]:
        """Calculate percentiles for small datasets."""
        p95_idx = int(0.95 * len(sorted_values))
        p99_idx = int(0.99 * len(sorted_values))
        p95 = sorted_values[min(p95_idx, len(sorted_values) - 1)]
        p99 = sorted_values[min(p99_idx, len(sorted_values) - 1)]
        return p95, p99

class ThroughputTracker:
    """Tracks throughput metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.token_count = 0
        self.operation_count = 0
        self.start_time = time.perf_counter()
        self.throughput_samples = []
    
    def record_request(self, token_count: int = 0) -> None:
        """Record a completed request."""
        self.request_count += 1
        self.token_count += token_count
        self.operation_count += 1
    
    def record_throughput_sample(self) -> None:
        """Record current throughput sample."""
        current_time = time.perf_counter()
        duration = current_time - self.start_time
        if duration > 0:
            current_rps = self.request_count / duration
            self.throughput_samples.append(current_rps)
    
    def calculate_metrics(self) -> ThroughputMetrics:
        """Calculate throughput metrics."""
        elapsed_time = time.perf_counter() - self.start_time
        if elapsed_time <= 0:
            return ThroughputMetrics()
        
        rates = self._calculate_throughput_rates(elapsed_time)
        peak_throughput = max(self.throughput_samples) if self.throughput_samples else rates[0]
        return self._create_throughput_metrics(rates, peak_throughput)
    
    def _calculate_throughput_rates(self, elapsed_time: float) -> Tuple[float, float, float]:
        """Calculate throughput rates."""
        rps = self.request_count / elapsed_time
        tokens_per_sec = self.token_count / elapsed_time
        ops_per_min = (self.operation_count / elapsed_time) * 60
        return rps, tokens_per_sec, ops_per_min
    
    def _create_throughput_metrics(self, rates: Tuple[float, float, float], peak: float) -> ThroughputMetrics:
        """Create throughput metrics object."""
        return ThroughputMetrics(
            requests_per_second=rates[0],
            tokens_per_second=rates[1],
            operations_per_minute=rates[2],
            peak_throughput=peak
        )

class ResourceMonitor:
    """Monitors system resource usage."""
    
    def __init__(self):
        self.cpu_samples = []
        self.memory_samples = []
        self.io_samples = []
        self.network_samples = []
        self.monitoring = False
    
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitoring = True
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self.io_samples.clear()
        self.network_samples.clear()
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitoring = False
    
    def sample_resources(self) -> None:
        """Sample current resource usage."""
        if not self.monitoring:
            return
        try:
            process = psutil.Process()
            self._sample_cpu_memory(process); self._sample_io_operations(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def _sample_cpu_memory(self, process) -> None:
        """Sample CPU and memory usage."""
        cpu_percent = process.cpu_percent()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.cpu_samples.append(cpu_percent)
        self.memory_samples.append(memory_mb)
    
    def _sample_io_operations(self, process) -> None:
        """Sample I/O operations if available."""
        try:
            io_counters = process.io_counters()
            self.io_samples.append(io_counters.read_count + io_counters.write_count)
        except (AttributeError, psutil.AccessDenied):
            pass
    
    def calculate_metrics(self) -> ResourceMetrics:
        """Calculate resource usage metrics."""
        cpu_stats = self._calculate_cpu_statistics()
        memory_stats = self._calculate_memory_statistics()
        return ResourceMetrics(
            cpu_percent_avg=cpu_stats[0], cpu_percent_peak=cpu_stats[1],
            memory_mb_avg=memory_stats[0], memory_mb_peak=memory_stats[1],
            io_operations_per_second=0.0, network_bytes_per_second=0.0
        )
    
    def _calculate_cpu_statistics(self) -> Tuple[float, float]:
        """Calculate CPU statistics."""
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        cpu_peak = max(self.cpu_samples) if self.cpu_samples else 0
        return cpu_avg, cpu_peak
    
    def _calculate_memory_statistics(self) -> Tuple[float, float]:
        """Calculate memory statistics."""
        memory_avg = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
        memory_peak = max(self.memory_samples) if self.memory_samples else 0
        return memory_avg, memory_peak