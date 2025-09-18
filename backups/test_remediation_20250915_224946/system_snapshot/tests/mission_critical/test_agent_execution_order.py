'''
Mission Critical Test: Verify Agent Execution Order is Logical
Date: 2025-09-04
Purpose: Ensure agents execute in correct dependency order (data before optimization)
'''

import pytest
from typing import Dict, Any, List
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig


class TestAgentExecutionOrder:
    """Verify agent execution follows logical dependency chain."""

    def test_sufficient_data_workflow_order(self):
        """Test that data collection happens BEFORE optimization in sufficient data workflow."""
    # Create mock objects
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with sufficient data
        triage_result = {"data_sufficiency": "sufficient"}

    # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

    # Verify correct order
        assert agent_order == ["triage", "data", "optimization", "actions", "reporting"], \
        "formatted_string"

    # Verify dependencies
        step_dict = {step.agent_name: step for step in steps}

        assert step_dict["triage"].dependencies == []
        assert step_dict["data"].dependencies == ["triage"]
        assert step_dict["optimization"].dependencies == ["data"], \
        "Optimization MUST depend on data!"
        assert step_dict["actions"].dependencies == ["optimization"]
        assert step_dict["reporting"].dependencies == ["actions"]

    def test_partial_data_workflow_order(self):
        """Test that data_helper runs early in partial data workflow."""
        pass
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with partial data
        triage_result = {"data_sufficiency": "partial"}

    # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

    # Verify data_helper comes early (right after triage)
        assert agent_order[0] == "triage"
        assert agent_order[1] == "data_helper", \
        "Data helper must run early to identify gaps!"

    # Verify data comes before optimization
        data_index = agent_order.index("data")
        opt_index = agent_order.index("optimization")
        assert data_index < opt_index, \
        "formatted_string"

    # Full expected order
        assert agent_order == ["triage", "data_helper", "data", "optimization", "actions", "reporting"]

    def test_insufficient_data_workflow_order(self):
        """Test minimal workflow for insufficient data."""
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with insufficient data
        triage_result = {"data_sufficiency": "insufficient"}

    # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

    # Should be minimal - just triage and data_helper
        assert agent_order == ["triage", "data_helper"], \
        "Insufficient data should only run triage and data_helper!"

    def test_default_fallback_workflow_order(self):
        """Test that default/unknown workflow uses correct order."""
        pass
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate unknown data sufficiency
        triage_result = {"data_sufficiency": "unknown"}

    # Get the workflow steps
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
        agent_order = [step.agent_name for step in steps]

    # Default should use the logical order
        assert agent_order == ["triage", "data", "optimization", "actions", "reporting"], \
        "formatted_string"

    def test_all_steps_marked_sequential(self):
        """Verify all steps are marked for sequential execution."""
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Test all workflow types
        for data_sufficiency in ["sufficient", "partial", "insufficient", "unknown"]:
        triage_result = {"data_sufficiency": data_sufficiency}
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        for step in steps:
            # Check strategy is SEQUENTIAL
        assert str(step.strategy).endswith("SEQUENTIAL"), \
        "formatted_string"

            # Check metadata flag
        assert step.metadata.get("requires_sequential") == True, \
        "formatted_string"

    def test_dependency_chain_integrity(self):
        """Verify each agent depends on the previous one in the chain."""
        pass
        orchestrator = WorkflowOrchestrator(None, None, None)

    # Test sufficient data workflow (most complete)
        triage_result = {"data_sufficiency": "sufficient"}
        steps = orchestrator._define_workflow_based_on_triage(triage_result)

        for i, step in enumerate(steps):
        if i == 0:
            # First step should have no dependencies
        assert step.dependencies == [], \
        "formatted_string"
        else:
                # Each step should depend on the previous
        prev_step = steps[i-1]
        assert prev_step.agent_name in step.dependencies, \
        "formatted_string"


        if __name__ == "__main__":
        print("Running Agent Execution Order Tests...")
        print("=" * 60)

        test = TestAgentExecutionOrder()

                    # Run all tests
        tests = [ )
        ("Sufficient Data Order", test.test_sufficient_data_workflow_order),
        ("Partial Data Order", test.test_partial_data_workflow_order),
        ("Insufficient Data Order", test.test_insufficient_data_workflow_order),
        ("Default Fallback Order", test.test_default_fallback_workflow_order),
        ("Sequential Execution", test.test_all_steps_marked_sequential),
        ("Dependency Chain", test.test_dependency_chain_integrity),
                    

        passed = 0
        failed = 0

        for test_name, test_func in tests:
        try:
        test_func()
        print("formatted_string")
        passed += 1
        except AssertionError as e:
        print("formatted_string")
        print("formatted_string")
        failed += 1
        except Exception as e:
        print("formatted_string")
        print("formatted_string")
        failed += 1

        print("=" * 60)
        print("formatted_string")

        if failed == 0:
        print(" )
        [SUCCESS] All agent execution order tests passed!")
        print("Agents will execute in logical order: Triage -> Data -> Optimization -> Actions -> Reporting")
        else:
        print(" )
        [FAILURE] Some tests failed - agent execution order may be incorrect!")
        sys.exit(1)
