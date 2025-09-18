"""
Performance Validation Framework for E2E Agent Testing
Validates latency, throughput, resource usage, and performance regression.
Maximum 300 lines, functions  <= 8 lines.

This module provides a unified interface for performance validation by importing
components from the modular performance validation system.
"""

# Import all components for backward compatibility
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
from netra_backend.tests.e2e.validators.performance_validator_core import PerformanceValidator

# Export all classes for external use
__all__ = [
    # Metrics and schemas
    'LatencyMetrics',
    'ThroughputMetrics', 
    'ResourceMetrics',
    'PerformanceThresholds',
    'PerformanceRegression',
    'BenchmarkComparison',
    'PerformanceValidationResult',
    
    # Measurement classes
    'LatencyMeasurer',
    'ThroughputTracker',
    'ResourceMonitor',
    
    # Analysis classes
    'RegressionDetector',
    'BenchmarkComparator',
    
    # Main validator
    'PerformanceValidator'
]