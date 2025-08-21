"""
Supervisor Agent Orchestration Tests - Index
Central index for all supervisor orchestration tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all supervisor orchestration test modules

# Add project root to path

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.agents.test_supervisor_basic import TestSupervisorOrchestration
from netra_backend.tests.agents.test_supervisor_patterns import (

# Add project root to path
    TestWorkflowPatterns,
    TestResourceManagement
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestSupervisorOrchestration",
    "TestWorkflowPatterns",
    "TestResourceManagement"
]