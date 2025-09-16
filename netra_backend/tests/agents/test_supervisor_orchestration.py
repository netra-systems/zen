import pytest
"""
Supervisor Agent Orchestration Tests - Index
Central index for all supervisor orchestration tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""""

# Import all supervisor orchestration test modules

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from netra_backend.tests.agents.test_supervisor_basic import SupervisorOrchestrationTests as TestSupervisorOrchestration
from netra_backend.tests.agents.test_supervisor_patterns import (
ResourceManagementTests as TestResourceManagement,
WorkflowPatternsTests as TestWorkflowPatterns,
)

# Re-export all test classes for pytest discovery
__all__ = [
"TestSupervisorOrchestration",
"TestWorkflowPatterns",
"TestResourceManagement"
]