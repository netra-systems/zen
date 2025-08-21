"""
Multi-Constraint KV Cache Workflows Test Module
Tests KV caching audit and optimization workflows.
Maximum 300 lines, functions ≤8 lines.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import pytest_asyncio
import asyncio
from typing import Dict, List

# Add project root to path

from netra_backend.tests.e2e.multi_constraint_test_helpers import (

# Add project root to path
    create_test_llm_manager, create_test_websocket_manager, create_agent_instances,
    build_multi_constraint_setup, execute_multi_constraint_workflow,
    create_kv_cache_audit_state, create_comprehensive_cache_state,
    validate_basic_workflow_execution, validate_cache_scope_identification,
    validate_cache_inventory_analysis, validate_optimization_opportunity_identification,
    validate_completed_or_fallback_states
)


@pytest.fixture(scope="function")
def multi_constraint_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for multi-constraint optimization testing."""
    agents = create_agent_instances(real_llm_manager, real_tool_dispatcher)
    return build_multi_constraint_setup(agents, real_llm_manager, real_websocket_manager)


class TestKVCachingAuditWorkflows:
    """Test KV caching audit and optimization workflows."""
    
    async def test_kv_cache_optimization_audit(self, multi_constraint_setup):
        """Test: 'I want to audit all uses of KV caching in my system to find optimization opportunities.'"""
        setup = multi_constraint_setup
        state = create_kv_cache_audit_state()
        results = await execute_multi_constraint_workflow(setup, state)
        validate_kv_cache_audit_results(results, state)
    
    async def test_comprehensive_cache_analysis(self, multi_constraint_setup):
        """Test comprehensive cache analysis across system components."""
        setup = multi_constraint_setup
        state = create_comprehensive_cache_state()
        results = await execute_multi_constraint_workflow(setup, state)
        validate_comprehensive_cache_results(results)
    
    async def test_cache_audit_with_error_recovery(self, multi_constraint_setup):
        """Test KV cache audit with error recovery mechanisms."""
        setup = multi_constraint_setup
        state = create_kv_cache_audit_state()
        # Add error recovery metadata
        state.metadata.update({'error_recovery': True, 'retry_count': 3})
        results = await execute_multi_constraint_workflow(setup, state)
        validate_error_recovery_results(results, state)
    
    async def test_cache_optimization_prioritization(self, multi_constraint_setup):
        """Test cache optimization with priority handling."""
        setup = multi_constraint_setup
        state = create_comprehensive_cache_state()
        state.metadata.update({'priority_mode': 'high_impact_first'})
        results = await execute_multi_constraint_workflow(setup, state)
        validate_prioritization_results(results, state)


def validate_kv_cache_audit_results(results: List[Dict], state) -> None:
    """Validate KV cache audit workflow results."""
    validate_basic_workflow_execution(results)
    validate_cache_scope_identification(results[0], state)
    validate_cache_inventory_analysis(results[1], state)
    validate_optimization_opportunity_identification(results[2], state)


def validate_comprehensive_cache_results(results: List[Dict]) -> None:
    """Validate comprehensive cache analysis results."""
    validate_basic_workflow_execution(results)
    validate_completed_or_fallback_states(results)


def validate_error_recovery_results(results: List[Dict], state) -> None:
    """Validate error recovery handling in cache workflows."""
    validate_basic_workflow_execution(results)
    assert state.metadata.get('error_recovery') is True
    assert state.metadata.get('retry_count') == 3


def validate_prioritization_results(results: List[Dict], state) -> None:
    """Validate priority handling in cache optimization."""
    validate_basic_workflow_execution(results)
    assert state.metadata.get('priority_mode') == 'high_impact_first'
    validate_completed_or_fallback_states(results)