"""
Agent Scaling Workflows Test Suite - Modular Index
Imports all scaling workflow tests from focused modules.
Maximum 300 lines, functions ≤8 lines.
"""

# Import all test modules to ensure they're discovered by pytest
from netra_backend.tests.e2e.test_usage_increase_analysis import TestUsageIncreaseAnalysis
from netra_backend.tests.e2e.test_rate_limit_analysis import TestRateLimitImpactAnalysis
from netra_backend.tests.e2e.test_capacity_planning import TestCapacityPlanningWorkflows
from netra_backend.tests.e2e.test_scaling_metrics import TestScalingMetricsValidation
from netra_backend.tests.e2e.test_scaling_integrity import TestScalingWorkflowIntegrity
from netra_backend.tests.e2e.test_scaling_edge_cases import TestScalingEdgeCases

# Re-export test classes for backward compatibility
__all__ = [
    'TestUsageIncreaseAnalysis',
    'TestRateLimitImpactAnalysis', 
    'TestCapacityPlanningWorkflows',
    'TestScalingMetricsValidation',
    'TestScalingWorkflowIntegrity',
    'TestScalingEdgeCases'
]