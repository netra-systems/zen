"""
Performance Metrics Models for E2E Agent Testing
Pydantic models for performance validation results.
Maximum 300 lines, functions  <= 8 lines.
"""

from typing import Dict, List

from pydantic import BaseModel, Field

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