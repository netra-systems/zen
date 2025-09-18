"""
Performance Analysis Classes for E2E Agent Testing
Classes for regression detection and benchmark comparison.
Maximum 300 lines, functions  <= 8 lines.
"""

from typing import Dict, List, Optional, Tuple

from netra_backend.tests.e2e.validators.performance_metrics import (
    BenchmarkComparison,
    LatencyMetrics,
    PerformanceRegression,
    PerformanceValidationResult,
    ResourceMetrics,
    ThroughputMetrics,
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
        
        regressions = self._calculate_all_regressions(current_metrics)
        regression = self._populate_regression_results(regression, regressions)
        return regression
    
    def _calculate_all_regressions(self, current_metrics: PerformanceValidationResult) -> Tuple[float, float, float]:
        """Calculate all regression types."""
        latency_regression = self._check_latency_regression(current_metrics.latency_metrics)
        throughput_regression = self._check_throughput_regression(current_metrics.throughput_metrics)
        resource_regression = self._check_resource_regression(current_metrics.resource_metrics)
        return latency_regression, throughput_regression, resource_regression
    
    def _populate_regression_results(self, regression: PerformanceRegression, regressions: Tuple[float, float, float]) -> PerformanceRegression:
        """Populate regression results with calculated values."""
        regression.regression_detected = any(r > self.regression_threshold for r in regressions)
        regression.latency_regression_percent = regressions[0] * 100
        regression.throughput_regression_percent = regressions[1] * 100
        regression.resource_regression_percent = regressions[2] * 100
        if regression.regression_detected:
            regression.regression_details = self._generate_regression_details(*regressions)
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
        self._add_regression_detail(details, "Latency", latency, threshold_pct)
        self._add_regression_detail(details, "Throughput", throughput, threshold_pct)
        self._add_regression_detail(details, "Resource", resource, threshold_pct)
        return details
    
    def _add_regression_detail(self, details: List[str], metric_name: str, value: float, threshold_pct: float) -> None:
        """Add regression detail if threshold exceeded."""
        if value > self.regression_threshold:
            details.append(f"{metric_name} regression: {value*100:.1f}% (threshold: {threshold_pct}%)")

class BenchmarkComparator:
    """Compares performance against benchmarks."""
    
    def __init__(self, benchmarks: Optional[Dict[str, float]] = None):
        self.benchmarks = benchmarks or self._get_default_benchmarks()
    
    def compare_to_baseline(self, metrics: PerformanceValidationResult) -> BenchmarkComparison:
        """Compare metrics to baseline benchmarks."""
        comparison = BenchmarkComparison()
        benchmark_results = self._evaluate_benchmark_thresholds(metrics)
        comparison.baseline_met = all(benchmark_results)
        comparison.benchmark_details = self._calculate_benchmark_details(metrics)
        comparison.comparison_summary = self._generate_comparison_summary(metrics)
        return comparison
    
    def _evaluate_benchmark_thresholds(self, metrics: PerformanceValidationResult) -> List[bool]:
        """Evaluate benchmark thresholds."""
        latency_meets = metrics.latency_metrics.p99_ms <= self.benchmarks.get('max_latency_p99_ms', 2000)
        throughput_meets = metrics.throughput_metrics.requests_per_second >= self.benchmarks.get('min_throughput_rps', 16.67)
        resource_meets = metrics.resource_metrics.memory_mb_peak <= self.benchmarks.get('max_memory_mb', 1024)
        return [latency_meets, throughput_meets, resource_meets]
    
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
        self._add_latency_summary(summary, metrics.latency_metrics.p99_ms)
        self._add_throughput_summary(summary, metrics.throughput_metrics.requests_per_second)
        return summary
    
    def _add_latency_summary(self, summary: List[str], latency_p99: float) -> None:
        """Add latency benchmark summary."""
        if latency_p99 <= self.benchmarks.get('max_latency_p99_ms', 2000):
            summary.append("Latency benchmark met")
        else:
            summary.append("Latency benchmark exceeded")
    
    def _add_throughput_summary(self, summary: List[str], rps: float) -> None:
        """Add throughput benchmark summary."""
        if rps >= self.benchmarks.get('min_throughput_rps', 16.67):
            summary.append("Throughput benchmark met")
        else:
            summary.append("Throughput benchmark not met")