"""Simple test for UVS Requirements - Only 2 Required Agents.

This test validates the simplified UVS architecture without complex dependencies.
"""

import pytest
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator


class TestUVSSimplified:
    """Test UVS requirements with simplified approach."""
    
    def test_workflow_orchestrator_dynamic_flow(self):
        """Test that WorkflowOrchestrator implements dynamic workflow based on triage."""
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        # Test sufficient data workflow
        triage_result = {"data_sufficiency": "sufficient"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify workflow has all agents for sufficient data
        agent_names = [step.agent_name for step in workflow_steps]
        assert "triage" in agent_names, "Triage must be in workflow"
        assert "data" in agent_names, "Data agent should run with sufficient data"
        assert "optimization" in agent_names, "Optimization should run with sufficient data"
        assert "reporting" in agent_names, "Reporting must always be included"
        
        # Verify reporting has no hard dependencies (UVS)
        reporting_step = next(s for s in workflow_steps if s.agent_name == "reporting")
        assert reporting_step.dependencies == [], "Reporting should have no hard dependencies with UVS"
        
        # Test insufficient data workflow (DEFAULT FLOW)
        triage_result = {"data_sufficiency": "insufficient"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify default flow
        agent_names = [step.agent_name for step in workflow_steps]
        assert agent_names == ["triage", "data_helper", "reporting"], \
            f"Default flow should be Triage → Data Helper → Reporting, got {agent_names}"
        
        # Test partial data workflow
        triage_result = {"data_sufficiency": "partial"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        agent_names = [step.agent_name for step in workflow_steps]
        assert "triage" in agent_names, "Triage must be in workflow"
        assert "data_helper" in agent_names, "Data helper should assist with partial data"
        assert "reporting" in agent_names, "Reporting must always be included"
        
        # Test unknown/failed triage (MINIMAL FLOW)
        triage_result = {"data_sufficiency": "unknown"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify minimal flow
        agent_names = [step.agent_name for step in workflow_steps]
        assert "data_helper" in agent_names, "Data helper provides initial guidance"
        assert "reporting" in agent_names, "Reporting handles all scenarios"
        assert agent_names[-1] == "reporting", "Reporting is always last"
    
    def test_workflow_adapts_to_all_scenarios(self):
        """Test that workflow correctly adapts to different data sufficiency levels."""
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        # Define test scenarios
        scenarios = [
            ("sufficient", ["triage", "data", "optimization", "actions", "reporting"]),
            ("partial", ["triage", "data_helper", "data", "reporting"]),
            ("insufficient", ["triage", "data_helper", "reporting"]),
            ("unknown", ["data_helper", "reporting"]),
            ("", ["data_helper", "reporting"]),  # Empty string
            (None, ["data_helper", "reporting"]),  # None value
        ]
        
        for data_sufficiency, expected_agents in scenarios:
            if data_sufficiency is not None:
                triage_result = {"data_sufficiency": data_sufficiency}
            else:
                triage_result = {}
            
            workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
            agent_names = [step.agent_name for step in workflow_steps]
            
            assert agent_names == expected_agents, \
                f"For data_sufficiency='{data_sufficiency}', expected {expected_agents}, got {agent_names}"
            
            # Always verify reporting is last and has no dependencies
            assert agent_names[-1] == "reporting", f"Reporting must be last for {data_sufficiency}"
            reporting_step = next(s for s in workflow_steps if s.agent_name == "reporting")
            assert reporting_step.dependencies == [], f"Reporting must have no dependencies for {data_sufficiency}"
    
    def test_uvs_principles(self):
        """Test that core UVS principles are implemented."""
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        # Principle 1: Reporting is ALWAYS included
        for sufficiency in ["sufficient", "partial", "insufficient", "unknown", None]:
            triage_result = {"data_sufficiency": sufficiency} if sufficiency else {}
            workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
            agent_names = [step.agent_name for step in workflow_steps]
            assert "reporting" in agent_names, f"Reporting must be included for {sufficiency}"
        
        # Principle 2: Default flow is Triage → Data Helper → Reporting
        default_flow = orchestrator._define_workflow_based_on_triage({"data_sufficiency": "insufficient"})
        default_names = [step.agent_name for step in default_flow]
        assert default_names == ["triage", "data_helper", "reporting"], "Default flow must be correct"
        
        # Principle 3: Workflow is dynamic based on data availability
        sufficient_flow = orchestrator._define_workflow_based_on_triage({"data_sufficiency": "sufficient"})
        insufficient_flow = orchestrator._define_workflow_based_on_triage({"data_sufficiency": "insufficient"})
        
        sufficient_names = [step.agent_name for step in sufficient_flow]
        insufficient_names = [step.agent_name for step in insufficient_flow]
        
        assert sufficient_names != insufficient_names, "Workflow must change based on data availability"
        assert len(sufficient_names) > len(insufficient_names), "More agents run with sufficient data"
        
        # Principle 4: Reporting can handle all scenarios (no hard dependencies)
        for workflow in [sufficient_flow, insufficient_flow]:
            reporting_step = next(s for s in workflow if s.agent_name == "reporting")
            assert reporting_step.dependencies == [], "Reporting must have no hard dependencies"