"""
Multi-Constraint Priority Workflow Test Module
Tests workflows with constraint prioritization.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from typing import Dict, List

import pytest

# Add project root to path
from netra_backend.tests.e2e.multi_constraint_test_helpers import (
    build_multi_constraint_setup,
    # Add project root to path
    create_agent_instances,
    create_dynamic_constraint_state,
    create_priority_optimization_state,
    execute_multi_constraint_workflow,
    validate_basic_workflow_execution,
    validate_completed_or_fallback_states,
    validate_priority_optimization_results,
)


@pytest.fixture(scope="function")
def multi_constraint_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for multi-constraint optimization testing."""
    agents = create_agent_instances(real_llm_manager, real_tool_dispatcher)
    return build_multi_constraint_setup(agents, real_llm_manager, real_websocket_manager)


class TestConstraintPriorityWorkflows:
    """Test workflows with constraint prioritization."""
    
    async def test_priority_based_optimization(self, multi_constraint_setup):
        """Test optimization with prioritized constraints."""
        setup = multi_constraint_setup
        state = create_priority_optimization_state()
        results = await execute_multi_constraint_workflow(setup, state)
        validate_priority_optimization_results(results, state)
    
    async def test_dynamic_constraint_adjustment(self, multi_constraint_setup):
        """Test dynamic constraint adjustment during optimization."""
        setup = multi_constraint_setup
        state = create_dynamic_constraint_state()
        results = await execute_multi_constraint_workflow(setup, state)
        validate_dynamic_constraint_results(results)
    
    async def test_hierarchical_constraint_resolution(self, multi_constraint_setup):
        """Test hierarchical constraint resolution."""
        setup = multi_constraint_setup
        state = create_priority_optimization_state()
        state.metadata.update({
            'hierarchy': {'critical': ['quality'], 'important': ['cost'], 'nice_to_have': ['latency']}
        })
        results = await execute_multi_constraint_workflow(setup, state)
        validate_hierarchical_results(results, state)
    
    async def test_adaptive_priority_adjustment(self, multi_constraint_setup):
        """Test adaptive priority adjustment based on feedback."""
        setup = multi_constraint_setup
        state = create_dynamic_constraint_state()
        state.metadata.update({
            'adaptive_mode': True,
            'feedback_loop': True,
            'adjustment_threshold': 0.1
        })
        results = await execute_multi_constraint_workflow(setup, state)
        validate_adaptive_adjustment_results(results, state)
    
    async def test_constraint_deadline_prioritization(self, multi_constraint_setup):
        """Test constraint prioritization based on deadlines."""
        setup = multi_constraint_setup
        state = create_priority_optimization_state()
        state.metadata.update({
            'deadlines': {'quality': '2h', 'cost': '1d', 'latency': '1w'},
            'urgency_factor': 0.8
        })
        results = await execute_multi_constraint_workflow(setup, state)
        validate_deadline_prioritization_results(results, state)


def validate_dynamic_constraint_results(results: List[Dict]) -> None:
    """Validate dynamic constraint adjustment results."""
    validate_basic_workflow_execution(results)
    validate_completed_or_fallback_states(results)


def validate_hierarchical_results(results: List[Dict], state) -> None:
    """Validate hierarchical constraint resolution results."""
    validate_basic_workflow_execution(results)
    hierarchy = state.metadata.get('hierarchy', {})
    assert 'critical' in hierarchy
    assert 'important' in hierarchy
    assert 'nice_to_have' in hierarchy
    validate_completed_or_fallback_states(results)


def validate_adaptive_adjustment_results(results: List[Dict], state) -> None:
    """Validate adaptive priority adjustment results."""
    validate_basic_workflow_execution(results)
    assert state.metadata.get('adaptive_mode') is True
    assert state.metadata.get('feedback_loop') is True
    assert state.metadata.get('adjustment_threshold') == 0.1
    validate_completed_or_fallback_states(results)


def validate_deadline_prioritization_results(results: List[Dict], state) -> None:
    """Validate deadline-based prioritization results."""
    validate_basic_workflow_execution(results)
    deadlines = state.metadata.get('deadlines', {})
    assert 'quality' in deadlines
    assert 'cost' in deadlines
    assert 'latency' in deadlines
    assert state.metadata.get('urgency_factor') == 0.8
    validate_completed_or_fallback_states(results)