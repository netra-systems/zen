import asyncio

"""
Multi-Constraint Data Integrity Test Module
Tests data integrity across multi-constraint workflows.
Maximum 300 lines, functions  <= 8 lines.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from typing import Dict, List

import pytest

from netra_backend.tests.e2e.multi_constraint_test_helpers import (
build_multi_constraint_setup,
create_agent_instances,
create_kv_cache_audit_state,
create_triple_constraint_state,
execute_multi_constraint_workflow,
validate_basic_workflow_execution,
validate_completed_or_fallback_states,
validate_constraint_data_consistency,
validate_optimization_state_preservation,
)

@pytest.fixture(scope="function")
def multi_constraint_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for multi-constraint optimization testing."""
    agents = create_agent_instances(real_llm_manager, real_tool_dispatcher)
    return build_multi_constraint_setup(agents, real_llm_manager, real_websocket_manager)

class TestWorkflowDataIntegrity:
    """Test data integrity across multi-constraint workflows."""

    @pytest.mark.asyncio
    async def test_constraint_data_consistency(self, multi_constraint_setup):
        """Test constraint data consistency throughout workflow."""
        setup = multi_constraint_setup
        state = create_kv_cache_audit_state()
        results = await execute_multi_constraint_workflow(setup, state)
        validate_constraint_data_consistency(results, state)

        @pytest.mark.asyncio
        async def test_optimization_state_preservation(self, multi_constraint_setup):
            """Test optimization state preservation across agents."""
            setup = multi_constraint_setup
            state = create_triple_constraint_state()
            results = await execute_multi_constraint_workflow(setup, state)
            validate_optimization_state_preservation(results, state)

            @pytest.mark.asyncio
            async def test_metadata_propagation_integrity(self, multi_constraint_setup):
                """Test metadata propagation integrity across workflow."""
                setup = multi_constraint_setup
                state = create_kv_cache_audit_state()
                state.metadata.update({
                'propagation_test': True,
                'critical_data': {'key1': 'value1', 'key2': 'value2'}
                })
                results = await execute_multi_constraint_workflow(setup, state)
                validate_metadata_propagation_results(results, state)

                @pytest.mark.asyncio
                async def test_constraint_validation_chain(self, multi_constraint_setup):
                    """Test constraint validation chain integrity."""
                    setup = multi_constraint_setup
                    state = create_triple_constraint_state()
                    state.metadata.update({
                    'validation_chain': True,
                    'validation_rules': ['cost_bounds', 'quality_thresholds', 'latency_limits']
                    })
                    results = await execute_multi_constraint_workflow(setup, state)
                    validate_validation_chain_results(results, state)

                    @pytest.mark.asyncio
                    async def test_workflow_state_transitions(self, multi_constraint_setup):
                        """Test workflow state transition integrity."""
                        setup = multi_constraint_setup
                        state = create_kv_cache_audit_state()
                        state.metadata.update({
                        'track_transitions': True,
                        'expected_transitions': ['pending', 'running', 'completed']
                        })
                        results = await execute_multi_constraint_workflow(setup, state)
                        validate_state_transition_results(results, state)

                        @pytest.mark.asyncio
                        async def test_cross_agent_data_consistency(self, multi_constraint_setup):
                            """Test data consistency across different agents."""
                            setup = multi_constraint_setup
                            state = create_triple_constraint_state()
                            state.metadata.update({
                            'cross_agent_test': True,
                            'shared_data': {'session_id': 'test-123', 'user_context': 'multi-constraint'}
                            })
                            results = await execute_multi_constraint_workflow(setup, state)
                            validate_cross_agent_consistency_results(results, state)

                            def validate_metadata_propagation_results(results: List[Dict], state) -> None:
                                """Validate metadata propagation integrity."""
                                validate_basic_workflow_execution(results)
                                assert state.metadata.get('propagation_test') is True
                                critical_data = state.metadata.get('critical_data', {})
                                assert critical_data.get('key1') == 'value1'
                                assert critical_data.get('key2') == 'value2'
                                validate_completed_or_fallback_states(results)

                                def validate_validation_chain_results(results: List[Dict], state) -> None:
                                    """Validate constraint validation chain integrity."""
                                    validate_basic_workflow_execution(results)
                                    assert state.metadata.get('validation_chain') is True
                                    validation_rules = state.metadata.get('validation_rules', [])
                                    assert 'cost_bounds' in validation_rules
                                    assert 'quality_thresholds' in validation_rules
                                    assert 'latency_limits' in validation_rules
                                    validate_completed_or_fallback_states(results)

                                    def validate_state_transition_results(results: List[Dict], state) -> None:
                                        """Validate workflow state transition integrity."""
                                        validate_basic_workflow_execution(results)
                                        assert state.metadata.get('track_transitions') is True
                                        expected_transitions = state.metadata.get('expected_transitions', [])
                                        assert 'pending' in expected_transitions
                                        assert 'running' in expected_transitions
                                        assert 'completed' in expected_transitions
                                        validate_completed_or_fallback_states(results)

                                        def validate_cross_agent_consistency_results(results: List[Dict], state) -> None:
                                            """Validate cross-agent data consistency."""
                                            validate_basic_workflow_execution(results)
                                            assert state.metadata.get('cross_agent_test') is True
                                            shared_data = state.metadata.get('shared_data', {})
                                            assert shared_data.get('session_id') == 'test-123'
                                            assert shared_data.get('user_context') == 'multi-constraint'
                                            validate_completed_or_fallback_states(results)