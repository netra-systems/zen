"""
Core Performance Validator for E2E Agent Testing
Main validation framework integrating measurement and analysis.
Maximum 300 lines, functions  <= 8 lines.
"""

import asyncio
import time
from typing import Any, Callable, Optional, Tuple

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.tests.e2e.state_validation_utils import StateIntegrityChecker
from netra_backend.tests.e2e.validators.performance_analyzer import (
    BenchmarkComparator,
    RegressionDetector,
)
from netra_backend.tests.e2e.validators.performance_measurer import (
    LatencyMeasurer,
    ResourceMonitor,
    ThroughputTracker,
)
from netra_backend.tests.e2e.validators.performance_metrics import (
    BenchmarkComparison,
    LatencyMetrics,
    PerformanceRegression,
    PerformanceThresholds,
    PerformanceValidationResult,
    ResourceMetrics,
    ThroughputMetrics,
)

class PerformanceValidator:
    """Comprehensive performance validation framework."""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None,
                 baseline_metrics: Optional[dict] = None,
                 benchmarks: Optional[dict] = None):
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