"""
Agent Scaling Workflows Test Suite - Modular Index
Imports all scaling workflow tests from focused modules.
Maximum 300 lines, functions ≤8 lines.
"""

# Import all test modules to ensure they're discovered by pytest

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from tests.test_capacity_planning import TestCapacityPlanningWorkflows
from tests.test_rate_limit_analysis import TestRateLimitImpactAnalysis
from tests.test_scaling_edge_cases import TestScalingEdgeCases
from tests.test_scaling_integrity import TestScalingWorkflowIntegrity
from tests.test_scaling_metrics import TestScalingMetricsValidation
from tests.test_usage_increase_analysis import (
    TestUsageIncreaseAnalysis,
)

# Add project root to path

# Re-export test classes for backward compatibility
__all__ = [
    'TestUsageIncreaseAnalysis',
    'TestRateLimitImpactAnalysis', 
    'TestCapacityPlanningWorkflows',
    'TestScalingMetricsValidation',
    'TestScalingWorkflowIntegrity',
    'TestScalingEdgeCases'
]