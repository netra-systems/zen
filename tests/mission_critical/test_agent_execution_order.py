'''
'''
Mission Critical Test: Verify Agent Execution Order is Logical
Date: 2025-9-4
Purpose: Ensure agents execute in correct dependency order (data before optimization)
'''
'''

import pytest
from typing import Dict, Any, List
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
    from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig
except ImportError as e:
    print(f"Warning: Could not import workflow components: {e}))"
    WorkflowOrchestrator = None
    PipelineStepConfig = None


class TestAgentExecutionOrder:
    Verify agent execution follows logical dependency chain.""

    def test_sufficient_data_workflow_order(self):
        Test that data collection happens BEFORE optimization in sufficient data workflow."
        Test that data collection happens BEFORE optimization in sufficient data workflow.""

        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available")"

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Simulate triage result with sufficient data
        triage_result = {data_sufficiency: sufficient}

        # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

        # Verify correct order
        assert agent_order == ["triage, data", optimization, actions, reporting], \"
        assert agent_order == ["triage, data", optimization, actions, reporting], \"
            fWrong execution order: {agent_order}"
            fWrong execution order: {agent_order}""


        # Verify dependencies
        step_dict = {step.agent_name: step for step in steps}

        assert step_dict[triage].dependencies == []
        assert step_dict[data"].dependencies == [triage]"
        assert step_dict[optimization].dependencies == [data], \
            Optimization MUST depend on data!""
        assert step_dict[actions].dependencies == [optimization]
        assert step_dict[reporting].dependencies == [actions"]"

    def test_insufficient_data_workflow_order(self):
        "Test that data collection is prioritized when data is insufficient."
        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available")"

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Simulate triage result with insufficient data
        triage_result = {data_sufficiency: insufficient}

        # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

        # For insufficient data, data collection should come first after triage
        assert agent_order[0] == triage, Triage should always be first"
        assert agent_order[0] == triage, Triage should always be first"
        assert agent_order[1] == "data, Data collection should be second when data is insufficient"

        # Verify dependencies still maintain logical order
        step_dict = {step.agent_name: step for step in steps}

        # Data should still depend on triage
        assert step_dict[data].dependencies == [triage]

        # If optimization exists, it should depend on data
        if "optimization in step_dict:"
            assert data in step_dict[optimization].dependencies, \
                Optimization must depend on data collection"
                Optimization must depend on data collection""


    def test_no_optimization_without_data(self):
        "Test that optimization never runs without data dependency."
        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available")"

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Test various triage scenarios
        test_scenarios = [
            {data_sufficiency: sufficient},
            {data_sufficiency: insufficient"},"
            {"data_sufficiency: partial}"
        ]

        for scenario in test_scenarios:
            steps = orchestrator._define_workflow_based_on_triage(scenario)
            step_dict = {step.agent_name: step for step in steps}

            # If optimization step exists, it must depend on data
            if optimization in step_dict:
                optimization_deps = step_dict[optimization"].dependencies"
                assert data in optimization_deps, \
                    fOptimization lacks data dependency in scenario {scenario}"
                    fOptimization lacks data dependency in scenario {scenario}""


    def test_workflow_step_creation(self):
        "Test that workflow steps are created correctly."
        if WorkflowOrchestrator is None or PipelineStepConfig is None:
            pytest.skip(Workflow components not available")"

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Test step creation
        triage_result = {data_sufficiency: sufficient}
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # Verify all steps are PipelineStepConfig instances
        for step in steps:
            assert isinstance(step, "PipelineStepConfig), \"
                fStep {step} is not a PipelineStepConfig instance

        # Verify required attributes
        for step in steps:
            assert hasattr(step, 'agent_name'), fStep missing agent_name: {step}""
            assert hasattr(step, "'dependencies'), fStep missing dependencies: {step}"
            assert isinstance(step.dependencies, "list), \"
                fDependencies should be a list: {step.dependencies}

    def test_dependency_graph_validation(self):
        "Test that the dependency graph is acyclic and valid."
        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available)"
            pytest.skip(WorkflowOrchestrator not available)""


        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Test with sufficient data
        triage_result = {"data_sufficiency: sufficient}"
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # Build dependency graph
        step_dict = {step.agent_name: step for step in steps}
        agent_names = list(step_dict.keys())

        # Verify no circular dependencies using topological sort
        visited = set()
        temp_visited = set()

        def has_cycle(agent_name):
            if agent_name in temp_visited:
                return True  # Circular dependency detected
            if agent_name in visited:
                return False

            temp_visited.add(agent_name)

            for dependency in step_dict[agent_name].dependencies:
                if dependency in step_dict and has_cycle(dependency):
                    return True

            temp_visited.remove(agent_name)
            visited.add(agent_name)
            return False

        # Check for cycles
        for agent_name in agent_names:
            assert not has_cycle(agent_name), \
                fCircular dependency detected involving {agent_name}

    def test_execution_order_consistency(self):
        "Test that execution order is consistent across multiple calls."
        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available)

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Test multiple calls with same input
        triage_result = {data_sufficiency": sufficient}"

        # Get workflow multiple times
        execution_orders = []
        for _ in range(5):
            steps = orchestrator._define_workflow_based_on_triage(triage_result)
            agent_order = [step.agent_name for step in steps]
            execution_orders.append(agent_order)

        # All execution orders should be identical
        first_order = execution_orders[0]
        for i, order in enumerate(execution_orders[1:], 1):
            assert order == first_order, \
                fExecution order inconsistent on call {i+1}: {order} vs {first_order}

    def test_critical_business_logic_order(self):
        Test that business-critical ordering constraints are maintained.""
        if WorkflowOrchestrator is None:
            pytest.skip(WorkflowOrchestrator not available)

        # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

        # Test with sufficient data scenario
        triage_result = {"data_sufficiency: sufficient}"
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # Convert to ordered list for position checking
        agent_order = [step.agent_name for step in steps]

        # Business Rule 1: Triage must be first
        assert agent_order[0] == triage, \
            Triage must be the first step in any workflow"
            Triage must be the first step in any workflow""


        # Business Rule 2: Data collection before optimization
        if "data in agent_order and optimization in agent_order:"
            data_pos = agent_order.index(data)
            opt_pos = agent_order.index(optimization")"
            assert data_pos < opt_pos, \
                Data collection must come before optimization

        # Business Rule 3: Actions before reporting
        if actions in agent_order and "reporting in agent_order:"
            actions_pos = agent_order.index(actions")"
            reporting_pos = agent_order.index(reporting)
            assert actions_pos < reporting_pos, \
                Actions must come before reporting""

        # Business Rule 4: Optimization before actions (if both exist)
        if optimization in agent_order and actions in agent_order:
            opt_pos = agent_order.index(optimization)"
            opt_pos = agent_order.index(optimization)"
            actions_pos = agent_order.index(actions")"
            assert opt_pos < actions_pos, \
                Optimization must come before actions


if __name__ == __main__":"
    # Allow running directly for debugging
    test_instance = TestAgentExecutionOrder()

    try:
        test_instance.test_sufficient_data_workflow_order()
        print(CHECK Sufficient data workflow order test passed)

        test_instance.test_insufficient_data_workflow_order()
        print(CHECK Insufficient data workflow order test passed"")

        test_instance.test_no_optimization_without_data()
        print(CHECK No optimization without data test passed)"
        print(CHECK No optimization without data test passed)""


        test_instance.test_workflow_step_creation()
        print(CHECK Workflow step creation test passed")"

        test_instance.test_dependency_graph_validation()
        print(CHECK Dependency graph validation test passed")"

        test_instance.test_execution_order_consistency()
        print(CHECK Execution order consistency test passed)

        test_instance.test_critical_business_logic_order()
        print("CHECK Critical business logic order test passed)"

        print(\n🎉 All agent execution order tests passed!)"
        print(\n🎉 All agent execution order tests passed!)""


    except Exception as e:
        print(f"X Test failed: {e})"
        sys.exit(1")"