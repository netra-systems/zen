"""
Supervisor Agent Orchestration Tests - Index
Central index for all supervisor orchestration tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all supervisor orchestration test modules
from tests.agents.test_supervisor_basic import TestSupervisorOrchestration
from tests.agents.test_supervisor_patterns import (
    TestWorkflowPatterns,
    TestResourceManagement
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestSupervisorOrchestration",
    "TestWorkflowPatterns",
    "TestResourceManagement"
]