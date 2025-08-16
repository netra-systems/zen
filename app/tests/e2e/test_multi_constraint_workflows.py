"""
Multi-Constraint Workflows Main Test File
Provides shared fixtures for multi-constraint optimization tests.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import uuid
from typing import Dict

from app.tests.e2e.multi_constraint_test_helpers import (
    create_agent_instances, build_multi_constraint_setup
)


@pytest.fixture(scope="function")
def multi_constraint_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for multi-constraint optimization testing."""
    agents = create_agent_instances(real_llm_manager, real_tool_dispatcher)
    return build_multi_constraint_setup(agents, real_llm_manager, real_websocket_manager)


# Note: Test classes have been moved to separate modules:
# - TestKVCachingAuditWorkflows -> test_multi_constraint_kv_cache.py
# - TestComplexMultiObjectiveOptimization -> test_multi_constraint_optimization.py
# - TestSystemWideOptimizationWorkflows -> test_multi_constraint_system.py
# - TestConstraintPriorityWorkflows -> test_multi_constraint_priority.py
# - TestMultiConstraintEdgeCases -> test_multi_constraint_edge_cases.py
# - TestWorkflowDataIntegrity -> test_multi_constraint_integrity.py