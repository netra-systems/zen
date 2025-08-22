"""
Agent Scaling Workflows Test Suite - Modular Index
Imports all scaling workflow tests from focused modules.
Maximum 300 lines, functions ≤8 lines.
"""

# Import all test modules to ensure they're discovered by pytest

import sys
from pathlib import Path

from test_framework import setup_test_path

from netra_backend.tests.test_capacity_planning import TestCapacityPlanningWorkflows
from netra_backend.tests.test_rate_limit_analysis import TestRateLimitImpactAnalysis
from netra_backend.tests.test_scaling_edge_cases import TestScalingEdgeCases
from netra_backend.tests.test_scaling_integrity import TestScalingWorkflowIntegrity
from netra_backend.tests.test_scaling_metrics import TestScalingMetricsValidation
from netra_backend.tests.test_usage_increase_analysis import (
    TestUsageIncreaseAnalysis,
)

# Re-export test classes for backward compatibility
__all__ = [
    'TestUsageIncreaseAnalysis',
    'TestRateLimitImpactAnalysis', 
    'TestCapacityPlanningWorkflows',
    'TestScalingMetricsValidation',
    'TestScalingWorkflowIntegrity',
    'TestScalingEdgeCases'
]