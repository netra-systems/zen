"""
E2E Validation Framework Package
Comprehensive validation for agent workflows with stage-by-stage checkpoints.
"""

from netra_backend.tests.stage_validator import (
    StageValidator,
    InputValidator,
    ProcessingValidator,
    OutputValidator,
    StageValidationResult,
    InputValidationResult,
    ProcessingValidationResult,
    OutputValidationResult
)

from netra_backend.tests.data_integrity_validator import (
    DataIntegrityValidator,
    TypeSafetyValidator,
    DataFlowTracker,
    ReferentialIntegrityChecker,
    AuditTrailValidator,
    StateConsistencyValidator,
    DataIntegrityValidationResult,
    TypeSafetyResult,
    DataFlowResult,
    ReferentialIntegrityResult,
    AuditTrailResult,
    StateConsistencyResult
)

from netra_backend.tests.performance_validator import (
    PerformanceValidator,
    LatencyMeasurer,
    ThroughputTracker,
    ResourceMonitor,
    RegressionDetector,
    BenchmarkComparator,
    PerformanceValidationResult,
    LatencyMetrics,
    ThroughputMetrics,
    ResourceMetrics,
    PerformanceThresholds,
    PerformanceRegression,
    BenchmarkComparison
)

__all__ = [
    # Stage validation
    "StageValidator",
    "InputValidator", 
    "ProcessingValidator",
    "OutputValidator",
    "StageValidationResult",
    "InputValidationResult",
    "ProcessingValidationResult", 
    "OutputValidationResult",
    
    # Data integrity validation
    "DataIntegrityValidator",
    "TypeSafetyValidator",
    "DataFlowTracker",
    "ReferentialIntegrityChecker",
    "AuditTrailValidator",
    "StateConsistencyValidator",
    "DataIntegrityValidationResult",
    "TypeSafetyResult",
    "DataFlowResult",
    "ReferentialIntegrityResult",
    "AuditTrailResult",
    "StateConsistencyResult",
    
    # Performance validation
    "PerformanceValidator",
    "LatencyMeasurer",
    "ThroughputTracker", 
    "ResourceMonitor",
    "RegressionDetector",
    "BenchmarkComparator",
    "PerformanceValidationResult",
    "LatencyMetrics",
    "ThroughputMetrics",
    "ResourceMetrics",
    "PerformanceThresholds",
    "PerformanceRegression",
    "BenchmarkComparison"
]