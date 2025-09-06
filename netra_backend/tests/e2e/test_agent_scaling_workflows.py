import pytest
"""
Agent Scaling Workflows Test Suite - Modular Index
Imports all scaling workflow tests from focused modules.
Maximum 300 lines, functions <=8 lines.
"""""

# Import all test modules to ensure they're discovered by pytest'

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from netra_backend.tests.e2e.test_capacity_planning import TestCapacityPlanningWorkflows
from netra_backend.tests.e2e.test_rate_limit_analysis import TestRateLimitImpactAnalysis
from netra_backend.tests.e2e.test_usage_increase_analysis import (
TestUsageIncreaseAnalysis,
)

# Re-export test classes for backward compatibility
__all__ = [
'TestUsageIncreaseAnalysis',
'TestRateLimitImpactAnalysis', 
'TestCapacityPlanningWorkflows',
]