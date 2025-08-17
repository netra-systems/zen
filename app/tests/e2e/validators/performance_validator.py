"""
Performance Validation Framework for E2E Agent Testing
Validates latency, throughput, resource usage, and performance regression.
Maximum 300 lines, functions ≤8 lines.
"""

import time
import psutil
import asyncio
from typing import Dict, List, Any, Optional, Callable, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, UTC
from statistics import median, quantiles
from app.agents.state import DeepAgentState
from app.tests.e2e.state_validation_utils import StateIntegrityChecker


class LatencyMetrics(BaseModel):
    """Latency measurement metrics."""
    p50_ms: float = Field(default=0.0, description="50th percentile latency")
    p95_ms: float = Field(default=0.0, description="95th percentile latency")
    p99_ms: float = Field(default=0.0, description="99th percentile latency")
    mean_ms: float = Field(default=0.0, description="Mean latency")
    max_ms: float = Field(default=0.0, description="Maximum latency")
    min_ms: float = Field(default=0.0, description="Minimum latency")


class ThroughputMetrics(BaseModel):
    """Throughput measurement metrics."""
    requests_per_second: float = Field(default=0.0, description="Requests per second")
    tokens_per_second: float = Field(default=0.0, description="Tokens processed per second")
    operations_per_minute: float = Field(default=0.0, description="Operations per minute")
    peak_throughput: float = Field(default=0.0, description="Peak throughput achieved")


class ResourceMetrics(BaseModel):
    """Resource usage metrics."""
    cpu_percent_avg: float = Field(default=0.0, description="Average CPU usage")
    cpu_percent_peak: float = Field(default=0.0, description="Peak CPU usage")
    memory_mb_avg: float = Field(default=0.0, description="Average memory usage MB")
    memory_mb_peak: float = Field(default=0.0, description="Peak memory usage MB")
    io_operations_per_second: float = Field(default=0.0, description="I/O operations per second")
    network_bytes_per_second: float = Field(default=0.0, description="Network bytes per second")


class PerformanceThresholds(BaseModel):
    """Performance threshold configuration."""
    max_latency_p99_ms: float = Field(default=2000.0, description="Max P99 latency threshold")
    min_throughput_rps: float = Field(default=16.67, description="Min throughput (1000/min)")
    max_cpu_percent: float = Field(default=80.0, description="Max CPU usage threshold")
    max_memory_mb: float = Field(default=1024.0, description="Max memory usage threshold")
    max_error_rate_percent: float = Field(default=0.1, description="Max error rate threshold")


class PerformanceRegression(BaseModel):
    """Performance regression detection result."""
    regression_detected: bool = Field(default=False)
    latency_regression_percent: float = Field(default=0.0)
    throughput_regression_percent: float = Field(default=0.0)
    resource_regression_percent: float = Field(default=0.0)
    regression_details: List[str] = Field(default_factory=list)


class BenchmarkComparison(BaseModel):
    """Benchmark comparison result."""
    baseline_met: bool = Field(default=False)
    performance_improvement_percent: float = Field(default=0.0)
    benchmark_details: Dict[str, float] = Field(default_factory=dict)
    comparison_summary: List[str] = Field(default_factory=list)


class PerformanceValidationResult(BaseModel):
    """Comprehensive performance validation result."""
    latency_metrics: LatencyMetrics
    throughput_metrics: ThroughputMetrics
    resource_metrics: ResourceMetrics
    thresholds_met: bool = Field(default=False)
    regression_analysis: PerformanceRegression
    benchmark_comparison: BenchmarkComparison
    overall_performance_valid: bool = Field(default=False)


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
        
        return LatencyMetrics(
            p50_ms=percentiles[0],
            p95_ms=percentiles[1],
            p99_ms=percentiles[2],
            mean_ms=sum(self.measurements) / len(self.measurements),
            max_ms=max(self.measurements),
            min_ms=min(self.measurements)
        )
    
    def _calculate_percentiles(self, sorted_values: List[float]) -> List[float]:
        """Calculate P50, P95, P99 percentiles."""
        if len(sorted_values) == 1:
            return [sorted_values[0]] * 3
        
        p50 = median(sorted_values)
        
        # Calculate P95 and P99
        if len(sorted_values) >= 20:  # Sufficient data for percentiles
            quartiles = quantiles(sorted_values, n=100)
            p95 = quartiles[94] if len(quartiles) > 94 else sorted_values[-1]
            p99 = quartiles[98] if len(quartiles) > 98 else sorted_values[-1]
        else:
            # Fallback for small datasets
            p95_idx = int(0.95 * len(sorted_values))
            p99_idx = int(0.99 * len(sorted_values))
            p95 = sorted_values[min(p95_idx, len(sorted_values) - 1)]
            p99 = sorted_values[min(p99_idx, len(sorted_values) - 1)]
        
        return [p50, p95, p99]


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
        
        rps = self.request_count / elapsed_time
        tokens_per_sec = self.token_count / elapsed_time
        ops_per_min = (self.operation_count / elapsed_time) * 60
        peak_throughput = max(self.throughput_samples) if self.throughput_samples else rps
        
        return ThroughputMetrics(
            requests_per_second=rps,
            tokens_per_second=tokens_per_sec,
            operations_per_minute=ops_per_min,
            peak_throughput=peak_throughput
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
            cpu_percent = process.cpu_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.cpu_samples.append(cpu_percent)
            self.memory_samples.append(memory_mb)
            
            # Sample I/O if available
            try:
                io_counters = process.io_counters()
                self.io_samples.append(io_counters.read_count + io_counters.write_count)
            except (AttributeError, psutil.AccessDenied):
                pass
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def calculate_metrics(self) -> ResourceMetrics:
        """Calculate resource usage metrics."""
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        cpu_peak = max(self.cpu_samples) if self.cpu_samples else 0
        memory_avg = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
        memory_peak = max(self.memory_samples) if self.memory_samples else 0
        
        return ResourceMetrics(
            cpu_percent_avg=cpu_avg,
            cpu_percent_peak=cpu_peak,
            memory_mb_avg=memory_avg,
            memory_mb_peak=memory_peak,
            io_operations_per_second=0.0,  # Placeholder
            network_bytes_per_second=0.0   # Placeholder
        )


class RegressionDetector:
    """Detects performance regressions."""
    
    def __init__(self, baseline_metrics: Optional[Dict[str, float]] = None):
        self.baseline_metrics = baseline_metrics or {}
        self.regression_threshold = 0.1  # 10% regression threshold
    
    def detect_regression(self, current_metrics: PerformanceValidationResult) -> PerformanceRegression:
        """Detect performance regression."""
        regression = PerformanceRegression()
        
        if not self.baseline_metrics:
            return regression
        
        # Check latency regression
        latency_regression = self._check_latency_regression(current_metrics.latency_metrics)
        
        # Check throughput regression
        throughput_regression = self._check_throughput_regression(current_metrics.throughput_metrics)
        
        # Check resource regression
        resource_regression = self._check_resource_regression(current_metrics.resource_metrics)
        
        regression.regression_detected = any([latency_regression > self.regression_threshold,
                                            throughput_regression > self.regression_threshold,
                                            resource_regression > self.regression_threshold])
        
        regression.latency_regression_percent = latency_regression * 100
        regression.throughput_regression_percent = throughput_regression * 100
        regression.resource_regression_percent = resource_regression * 100
        
        if regression.regression_detected:
            regression.regression_details = self._generate_regression_details(
                latency_regression, throughput_regression, resource_regression)
        
        return regression
    
    def _check_latency_regression(self, current: LatencyMetrics) -> float:
        """Check for latency regression."""
        baseline_p99 = self.baseline_metrics.get('latency_p99_ms', 0)
        if baseline_p99 > 0:
            return max(0, (current.p99_ms - baseline_p99) / baseline_p99)
        return 0.0
    
    def _check_throughput_regression(self, current: ThroughputMetrics) -> float:
        """Check for throughput regression."""
        baseline_rps = self.baseline_metrics.get('throughput_rps', 0)
        if baseline_rps > 0:
            return max(0, (baseline_rps - current.requests_per_second) / baseline_rps)
        return 0.0
    
    def _check_resource_regression(self, current: ResourceMetrics) -> float:
        """Check for resource usage regression."""
        baseline_memory = self.baseline_metrics.get('memory_mb_peak', 0)
        if baseline_memory > 0:
            return max(0, (current.memory_mb_peak - baseline_memory) / baseline_memory)
        return 0.0
    
    def _generate_regression_details(self, latency: float, throughput: float, 
                                   resource: float) -> List[str]:
        """Generate regression details."""
        details = []
        threshold_pct = self.regression_threshold * 100
        
        if latency > self.regression_threshold:
            details.append(f"Latency regression: {latency*100:.1f}% (threshold: {threshold_pct}%)")
        if throughput > self.regression_threshold:
            details.append(f"Throughput regression: {throughput*100:.1f}% (threshold: {threshold_pct}%)")
        if resource > self.regression_threshold:
            details.append(f"Resource regression: {resource*100:.1f}% (threshold: {threshold_pct}%)")
        
        return details


class BenchmarkComparator:
    """Compares performance against benchmarks."""
    
    def __init__(self, benchmarks: Optional[Dict[str, float]] = None):
        self.benchmarks = benchmarks or self._get_default_benchmarks()
    
    def compare_to_baseline(self, metrics: PerformanceValidationResult) -> BenchmarkComparison:
        """Compare metrics to baseline benchmarks."""
        comparison = BenchmarkComparison()
        
        latency_meets = metrics.latency_metrics.p99_ms <= self.benchmarks.get('max_latency_p99_ms', 2000)
        throughput_meets = metrics.throughput_metrics.requests_per_second >= self.benchmarks.get('min_throughput_rps', 16.67)
        resource_meets = metrics.resource_metrics.memory_mb_peak <= self.benchmarks.get('max_memory_mb', 1024)
        
        comparison.baseline_met = all([latency_meets, throughput_meets, resource_meets])
        comparison.benchmark_details = self._calculate_benchmark_details(metrics)
        comparison.comparison_summary = self._generate_comparison_summary(metrics)
        
        return comparison
    
    def _get_default_benchmarks(self) -> Dict[str, float]:
        """Get default performance benchmarks."""
        return {
            'max_latency_p99_ms': 2000.0,
            'min_throughput_rps': 16.67,  # 1000 requests per minute
            'max_memory_mb': 1024.0,
            'max_cpu_percent': 80.0
        }
    
    def _calculate_benchmark_details(self, metrics: PerformanceValidationResult) -> Dict[str, float]:
        """Calculate detailed benchmark comparisons."""
        return {
            'latency_vs_benchmark': (metrics.latency_metrics.p99_ms / self.benchmarks.get('max_latency_p99_ms', 2000)) * 100,
            'throughput_vs_benchmark': (metrics.throughput_metrics.requests_per_second / self.benchmarks.get('min_throughput_rps', 16.67)) * 100,
            'memory_vs_benchmark': (metrics.resource_metrics.memory_mb_peak / self.benchmarks.get('max_memory_mb', 1024)) * 100
        }
    
    def _generate_comparison_summary(self, metrics: PerformanceValidationResult) -> List[str]:
        """Generate benchmark comparison summary."""
        summary = []
        
        if metrics.latency_metrics.p99_ms <= self.benchmarks.get('max_latency_p99_ms', 2000):
            summary.append("Latency benchmark met")
        else:
            summary.append("Latency benchmark exceeded")
        
        if metrics.throughput_metrics.requests_per_second >= self.benchmarks.get('min_throughput_rps', 16.67):
            summary.append("Throughput benchmark met")
        else:
            summary.append("Throughput benchmark not met")
        
        return summary


class PerformanceValidator:
    """Comprehensive performance validation framework."""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None,
                 baseline_metrics: Optional[Dict[str, float]] = None,
                 benchmarks: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.latency_measurer = LatencyMeasurer()
        self.throughput_tracker = ThroughputTracker()
        self.resource_monitor = ResourceMonitor()
        self.regression_detector = RegressionDetector(baseline_metrics)
        self.benchmark_comparator = BenchmarkComparator(benchmarks)
        self.integrity_checker = StateIntegrityChecker()
    
    async def validate_stage_performance(self, stage_name: str,
                                       stage_function: Callable,
                                       *args, **kwargs) -> PerformanceValidationResult:
        """Validate performance of a single stage."""
        operation_id = f"{stage_name}_{int(time.time())}"
        await self._execute_stage_with_monitoring(operation_id, stage_function, *args, **kwargs)
        metrics = self._calculate_all_metrics()
        thresholds_met = self._validate_thresholds(metrics[0], metrics[1], metrics[2])
        regression_analysis = self._detect_regressions(metrics, thresholds_met)
        benchmark_comparison = self._compare_benchmarks(metrics, thresholds_met, regression_analysis)
        overall_valid = thresholds_met and not regression_analysis.regression_detected and benchmark_comparison.baseline_met
        return self._create_performance_result(metrics, thresholds_met, regression_analysis, benchmark_comparison, overall_valid)
    
    async def _execute_stage_with_monitoring(self, operation_id: str, stage_function: Callable, *args, **kwargs):
        """Execute stage with monitoring."""
        self.resource_monitor.start_monitoring()
        self.latency_measurer.start_measurement(operation_id)
        try:
            result = await self._execute_with_monitoring(stage_function, *args, **kwargs)
            self.throughput_tracker.record_request()
        except Exception:
            pass  # Record error but continue with performance analysis
        finally:
            self.latency_measurer.end_measurement(operation_id)
            self.resource_monitor.stop_monitoring()
    
    def _calculate_all_metrics(self) -> Tuple[LatencyMetrics, ThroughputMetrics, ResourceMetrics]:
        """Calculate all performance metrics."""
        latency_metrics = self.latency_measurer.calculate_metrics()
        throughput_metrics = self.throughput_tracker.calculate_metrics()
        resource_metrics = self.resource_monitor.calculate_metrics()
        return latency_metrics, throughput_metrics, resource_metrics
    
    def _detect_regressions(self, metrics: Tuple[LatencyMetrics, ThroughputMetrics, ResourceMetrics], 
                           thresholds_met: bool) -> PerformanceRegression:
        """Detect performance regressions."""
        return self.regression_detector.detect_regression(
            PerformanceValidationResult(
                latency_metrics=metrics[0], throughput_metrics=metrics[1], resource_metrics=metrics[2],
                thresholds_met=thresholds_met, regression_analysis=PerformanceRegression(),
                benchmark_comparison=BenchmarkComparison()
            )
        )
    
    def _compare_benchmarks(self, metrics: Tuple[LatencyMetrics, ThroughputMetrics, ResourceMetrics],
                           thresholds_met: bool, regression_analysis: PerformanceRegression) -> BenchmarkComparison:
        """Compare performance to benchmarks."""
        return self.benchmark_comparator.compare_to_baseline(
            PerformanceValidationResult(
                latency_metrics=metrics[0], throughput_metrics=metrics[1], resource_metrics=metrics[2],
                thresholds_met=thresholds_met, regression_analysis=regression_analysis,
                benchmark_comparison=BenchmarkComparison()
            )
        )
    
    def _create_performance_result(self, metrics: Tuple[LatencyMetrics, ThroughputMetrics, ResourceMetrics],
                                  thresholds_met: bool, regression_analysis: PerformanceRegression,
                                  benchmark_comparison: BenchmarkComparison, overall_valid: bool) -> PerformanceValidationResult:
        """Create final performance validation result."""
        return PerformanceValidationResult(
            latency_metrics=metrics[0], throughput_metrics=metrics[1], resource_metrics=metrics[2],
            thresholds_met=thresholds_met, regression_analysis=regression_analysis,
            benchmark_comparison=benchmark_comparison, overall_performance_valid=overall_valid
        )
    
    async def _execute_with_monitoring(self, stage_function: Callable, *args, **kwargs) -> Any:
        """Execute function with resource monitoring."""
        # Sample resources during execution
        monitor_task = asyncio.create_task(self._monitor_resources())
        
        try:
            result = await stage_function(*args, **kwargs)
            return result
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_resources(self) -> None:
        """Continuously monitor resources."""
        while True:
            self.resource_monitor.sample_resources()
            self.throughput_tracker.record_throughput_sample()
            await asyncio.sleep(0.1)  # Sample every 100ms
    
    def _validate_thresholds(self, latency: LatencyMetrics, throughput: ThroughputMetrics,
                           resource: ResourceMetrics) -> bool:
        """Validate performance against thresholds."""
        latency_ok = latency.p99_ms <= self.thresholds.max_latency_p99_ms
        throughput_ok = throughput.requests_per_second >= self.thresholds.min_throughput_rps
        cpu_ok = resource.cpu_percent_peak <= self.thresholds.max_cpu_percent
        memory_ok = resource.memory_mb_peak <= self.thresholds.max_memory_mb
        
        return all([latency_ok, throughput_ok, cpu_ok, memory_ok])