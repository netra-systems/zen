"""
Performance Validation Framework for E2E Agent Testing
Validates latency, throughput, resource usage, and performance regression.
Maximum 300 lines, functions ≤8 lines.

This module provides a unified interface for performance validation by importing
components from the modular performance validation system.
"""

# Import all components for backward compatibility
from .performance_metrics import (
    LatencyMetrics,
    ThroughputMetrics, 
    ResourceMetrics,
    PerformanceThresholds,
    PerformanceRegression,
    BenchmarkComparison,
    PerformanceValidationResult
)

from .performance_measurer import (
    LatencyMeasurer,
    ThroughputTracker,
    ResourceMonitor
)

from .performance_analyzer import (
    RegressionDetector,
    BenchmarkComparator
)

from .performance_validator_core import (
    PerformanceValidator
)

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