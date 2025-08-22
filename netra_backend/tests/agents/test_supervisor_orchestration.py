"""
Supervisor Agent Orchestration Tests - Index
Central index for all supervisor orchestration tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all supervisor orchestration test modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.test_supervisor_basic import TestSupervisorOrchestration
from netra_backend.tests.test_supervisor_patterns import (
    TestResourceManagement,
    # Add project root to path
    TestWorkflowPatterns,
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestSupervisorOrchestration",
    "TestWorkflowPatterns",
    "TestResourceManagement"
]