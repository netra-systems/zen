# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Mission Critical Test: Verify Agent Execution Order is Logical
# REMOVED_SYNTAX_ERROR: Date: 2025-09-04
# REMOVED_SYNTAX_ERROR: Purpose: Ensure agents execute in correct dependency order (data before optimization)
# REMOVED_SYNTAX_ERROR: '''

import pytest
from typing import Dict, Any, List
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.execution_context import PipelineStep


# REMOVED_SYNTAX_ERROR: class TestAgentExecutionOrder:
    # REMOVED_SYNTAX_ERROR: """Verify agent execution follows logical dependency chain."""

# REMOVED_SYNTAX_ERROR: def test_sufficient_data_workflow_order(self):
    # REMOVED_SYNTAX_ERROR: """Test that data collection happens BEFORE optimization in sufficient data workflow."""
    # Create mock objects
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with sufficient data
    # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": "sufficient"}

    # Get the workflow steps
    # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
    # REMOVED_SYNTAX_ERROR: agent_order = [step.agent_name for step in steps]

    # Verify correct order
    # REMOVED_SYNTAX_ERROR: assert agent_order == ["triage", "data", "optimization", "actions", "reporting"], \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

    # Verify dependencies
    # REMOVED_SYNTAX_ERROR: step_dict = {step.agent_name: step for step in steps}

    # REMOVED_SYNTAX_ERROR: assert step_dict["triage"].dependencies == []
    # REMOVED_SYNTAX_ERROR: assert step_dict["data"].dependencies == ["triage"]
    # REMOVED_SYNTAX_ERROR: assert step_dict["optimization"].dependencies == ["data"], \
    # REMOVED_SYNTAX_ERROR: "Optimization MUST depend on data!"
    # REMOVED_SYNTAX_ERROR: assert step_dict["actions"].dependencies == ["optimization"]
    # REMOVED_SYNTAX_ERROR: assert step_dict["reporting"].dependencies == ["actions"]

# REMOVED_SYNTAX_ERROR: def test_partial_data_workflow_order(self):
    # REMOVED_SYNTAX_ERROR: """Test that data_helper runs early in partial data workflow."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with partial data
    # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": "partial"}

    # Get the workflow steps
    # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
    # REMOVED_SYNTAX_ERROR: agent_order = [step.agent_name for step in steps]

    # Verify data_helper comes early (right after triage)
    # REMOVED_SYNTAX_ERROR: assert agent_order[0] == "triage"
    # REMOVED_SYNTAX_ERROR: assert agent_order[1] == "data_helper", \
    # REMOVED_SYNTAX_ERROR: "Data helper must run early to identify gaps!"

    # Verify data comes before optimization
    # REMOVED_SYNTAX_ERROR: data_index = agent_order.index("data")
    # REMOVED_SYNTAX_ERROR: opt_index = agent_order.index("optimization")
    # REMOVED_SYNTAX_ERROR: assert data_index < opt_index, \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

    # Full expected order
    # REMOVED_SYNTAX_ERROR: assert agent_order == ["triage", "data_helper", "data", "optimization", "actions", "reporting"]

# REMOVED_SYNTAX_ERROR: def test_insufficient_data_workflow_order(self):
    # REMOVED_SYNTAX_ERROR: """Test minimal workflow for insufficient data."""
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate triage result with insufficient data
    # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": "insufficient"}

    # Get the workflow steps
    # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
    # REMOVED_SYNTAX_ERROR: agent_order = [step.agent_name for step in steps]

    # Should be minimal - just triage and data_helper
    # REMOVED_SYNTAX_ERROR: assert agent_order == ["triage", "data_helper"], \
    # REMOVED_SYNTAX_ERROR: "Insufficient data should only run triage and data_helper!"

# REMOVED_SYNTAX_ERROR: def test_default_fallback_workflow_order(self):
    # REMOVED_SYNTAX_ERROR: """Test that default/unknown workflow uses correct order."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Simulate unknown data sufficiency
    # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": "unknown"}

    # Get the workflow steps
    # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # Extract agent names in order
    # REMOVED_SYNTAX_ERROR: agent_order = [step.agent_name for step in steps]

    # Default should use the logical order
    # REMOVED_SYNTAX_ERROR: assert agent_order == ["triage", "data", "optimization", "actions", "reporting"], \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_all_steps_marked_sequential(self):
    # REMOVED_SYNTAX_ERROR: """Verify all steps are marked for sequential execution."""
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Test all workflow types
    # REMOVED_SYNTAX_ERROR: for data_sufficiency in ["sufficient", "partial", "insufficient", "unknown"]:
        # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": data_sufficiency}
        # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

        # REMOVED_SYNTAX_ERROR: for step in steps:
            # Check strategy is SEQUENTIAL
            # REMOVED_SYNTAX_ERROR: assert str(step.strategy).endswith("SEQUENTIAL"), \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # Check metadata flag
            # REMOVED_SYNTAX_ERROR: assert step.metadata.get("requires_sequential") == True, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_dependency_chain_integrity(self):
    # REMOVED_SYNTAX_ERROR: """Verify each agent depends on the previous one in the chain."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: orchestrator = WorkflowOrchestrator(None, None, None)

    # Test sufficient data workflow (most complete)
    # REMOVED_SYNTAX_ERROR: triage_result = {"data_sufficiency": "sufficient"}
    # REMOVED_SYNTAX_ERROR: steps = orchestrator._define_workflow_based_on_triage(triage_result)

    # REMOVED_SYNTAX_ERROR: for i, step in enumerate(steps):
        # REMOVED_SYNTAX_ERROR: if i == 0:
            # First step should have no dependencies
            # REMOVED_SYNTAX_ERROR: assert step.dependencies == [], \
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: else:
                # Each step should depend on the previous
                # REMOVED_SYNTAX_ERROR: prev_step = steps[i-1]
                # REMOVED_SYNTAX_ERROR: assert prev_step.agent_name in step.dependencies, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # REMOVED_SYNTAX_ERROR: print("Running Agent Execution Order Tests...")
                    # REMOVED_SYNTAX_ERROR: print("=" * 60)

                    # REMOVED_SYNTAX_ERROR: test = TestAgentExecutionOrder()

                    # Run all tests
                    # REMOVED_SYNTAX_ERROR: tests = [ )
                    # REMOVED_SYNTAX_ERROR: ("Sufficient Data Order", test.test_sufficient_data_workflow_order),
                    # REMOVED_SYNTAX_ERROR: ("Partial Data Order", test.test_partial_data_workflow_order),
                    # REMOVED_SYNTAX_ERROR: ("Insufficient Data Order", test.test_insufficient_data_workflow_order),
                    # REMOVED_SYNTAX_ERROR: ("Default Fallback Order", test.test_default_fallback_workflow_order),
                    # REMOVED_SYNTAX_ERROR: ("Sequential Execution", test.test_all_steps_marked_sequential),
                    # REMOVED_SYNTAX_ERROR: ("Dependency Chain", test.test_dependency_chain_integrity),
                    

                    # REMOVED_SYNTAX_ERROR: passed = 0
                    # REMOVED_SYNTAX_ERROR: failed = 0

                    # REMOVED_SYNTAX_ERROR: for test_name, test_func in tests:
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: test_func()
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                            # REMOVED_SYNTAX_ERROR: passed += 1
                            # REMOVED_SYNTAX_ERROR: except AssertionError as e:
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: failed += 1
                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: failed += 1

                                    # REMOVED_SYNTAX_ERROR: print("=" * 60)
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                    # REMOVED_SYNTAX_ERROR: if failed == 0:
                                        # REMOVED_SYNTAX_ERROR: print(" )
                                        # REMOVED_SYNTAX_ERROR: [SUCCESS] All agent execution order tests passed!")
                                        # REMOVED_SYNTAX_ERROR: print("Agents will execute in logical order: Triage -> Data -> Optimization -> Actions -> Reporting")
                                        # REMOVED_SYNTAX_ERROR: else:
                                            # REMOVED_SYNTAX_ERROR: print(" )
                                            # REMOVED_SYNTAX_ERROR: [FAILURE] Some tests failed - agent execution order may be incorrect!")
                                            # REMOVED_SYNTAX_ERROR: sys.exit(1)