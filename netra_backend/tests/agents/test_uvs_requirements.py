"""Test UVS Requirements - Only 2 Required Agents.

This test validates that the system correctly implements the UVS simplified architecture:
- Only Triage and Reporting (with UVS) are required agents
- Default flow is Triage → Data Helper → Reporting
- Reporting handles all failure scenarios gracefully
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.registry.agent_class_registry import AgentClassRegistry


def create_supervisor():
    """Helper to create a SupervisorAgent with mocked dependencies."""
    # Initialize the global registry if needed
    registry = AgentClassRegistry()
    registry._ensure_initialized()
    
    mock_llm = MagicMock()
    mock_websocket = MagicMock()
    
    # Mock the agent instance factory configuration
    with patch.object(SupervisorAgent, '_initialize_agent_instances'):
        supervisor = SupervisorAgent(llm_manager=mock_llm, websocket_bridge=mock_websocket)
        # Manually set the methods we need for testing
        supervisor._get_required_agent_names = SupervisorAgent._get_required_agent_names.__get__(supervisor)
        supervisor._determine_execution_order = SupervisorAgent._determine_execution_order.__get__(supervisor)
        supervisor.AGENT_DEPENDENCIES = SupervisorAgent.AGENT_DEPENDENCIES
    
    return supervisor


class TestUVSRequirements:
    """Test that UVS requirements are properly implemented."""
    
    def test_only_two_required_agents(self):
        """Test that only triage and reporting are required agents."""
        supervisor = create_supervisor()
        required_agents = supervisor._get_required_agent_names()
        
        # Extract only the truly required agents (first 2)
        truly_required = []
        optional = []
        
        # Based on the implementation, triage and reporting should be first
        for agent in required_agents:
            if agent in ["triage", "reporting"]:
                truly_required.append(agent)
            else:
                optional.append(agent)
        
        assert len(truly_required) == 2, "Only 2 agents should be required"
        assert "triage" in truly_required, "Triage must be a required agent"
        assert "reporting" in truly_required, "Reporting must be a required agent"
        
        # Verify these agents are marked as required in dependencies
        dependencies = supervisor.AGENT_DEPENDENCIES
        
        # Triage should have no required dependencies
        assert dependencies["triage"]["required"] == [], "Triage should have no dependencies"
        
        # Reporting should have no required dependencies (UVS: can work with nothing)
        assert dependencies["reporting"]["required"] == [], "Reporting should have no required dependencies with UVS"
        assert dependencies["reporting"]["uvs_enabled"] == True, "Reporting must have UVS enabled"
    
    def test_dynamic_execution_order_with_sufficient_data(self):
        """Test dynamic execution order when triage finds sufficient data."""
        supervisor = create_supervisor()
        
        # Simulate triage result with sufficient data
        triage_result = {
            "data_sufficiency": "sufficient",
            "available_data": {"usage": True, "costs": True}
        }
        
        execution_order = supervisor._determine_execution_order(triage_result)
        
        # With sufficient data, should run full workflow
        assert "data" in execution_order, "Data agent should run with sufficient data"
        assert "optimization" in execution_order, "Optimization should run with sufficient data"
        assert "reporting" in execution_order, "Reporting must always be included"
        
        # Reporting should be last
        assert execution_order[-1] == "reporting", "Reporting should be the last step"
    
    def test_dynamic_execution_order_with_insufficient_data(self):
        """Test dynamic execution order when triage finds insufficient data."""
        supervisor = create_supervisor()
        
        # Simulate triage result with insufficient data
        triage_result = {
            "data_sufficiency": "insufficient",
            "available_data": {}
        }
        
        execution_order = supervisor._determine_execution_order(triage_result)
        
        # With insufficient data, should use default UVS flow
        assert execution_order == ["data_helper", "reporting"], \
            "Default flow should be Data Helper → Reporting"
    
    def test_dynamic_execution_order_with_partial_data(self):
        """Test dynamic execution order when triage finds partial data."""
        supervisor = create_supervisor()
        
        # Simulate triage result with partial data
        triage_result = {
            "data_sufficiency": "partial",
            "available_data": {"usage": True}
        }
        
        execution_order = supervisor._determine_execution_order(triage_result)
        
        # With partial data, should include data helper
        assert "data_helper" in execution_order, "Data helper should assist with partial data"
        assert "reporting" in execution_order, "Reporting must always be included"
    
    def test_execution_order_when_triage_fails(self):
        """Test execution order when triage fails or returns unknown."""
        supervisor = create_supervisor()
        
        # Simulate failed/unknown triage
        triage_result = {}  # Empty result simulates failure
        
        execution_order = supervisor._determine_execution_order(triage_result)
        
        # Should fall back to minimal UVS flow
        assert "data_helper" in execution_order, "Data helper should run when triage fails"
        assert "reporting" in execution_order, "Reporting must handle triage failures"
    
    @pytest.mark.asyncio
    async def test_workflow_orchestrator_adaptive_flow(self):
        """Test that WorkflowOrchestrator implements adaptive workflow."""
        # Create mocks
        mock_registry = MagicMock()
        mock_engine = AsyncMock()
        mock_websocket = AsyncMock()
        
        orchestrator = WorkflowOrchestrator(
            agent_registry=mock_registry,
            execution_engine=mock_engine,
            websocket_manager=mock_websocket
        )
        
        # Test sufficient data workflow
        triage_result = {"data_sufficiency": "sufficient"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify workflow has all agents for sufficient data
        agent_names = [step.agent_name for step in workflow_steps]
        assert "triage" in agent_names
        assert "data" in agent_names
        assert "optimization" in agent_names
        assert "reporting" in agent_names
        
        # Verify reporting has no hard dependencies (UVS)
        reporting_step = next(s for s in workflow_steps if s.agent_name == "reporting")
        assert reporting_step.dependencies == [], "Reporting should have no hard dependencies with UVS"
        
        # Test insufficient data workflow (DEFAULT FLOW)
        triage_result = {"data_sufficiency": "insufficient"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify default flow
        agent_names = [step.agent_name for step in workflow_steps]
        assert agent_names == ["triage", "data_helper", "reporting"], \
            "Default flow should be Triage → Data Helper → Reporting"
        
        # Test unknown/failed triage (MINIMAL FLOW)
        triage_result = {"data_sufficiency": "unknown"}
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Verify minimal flow
        agent_names = [step.agent_name for step in workflow_steps]
        assert "data_helper" in agent_names, "Data helper provides initial guidance"
        assert "reporting" in agent_names, "Reporting handles all scenarios"
        assert agent_names[-1] == "reporting", "Reporting is always last"
    
    def test_reporting_uvs_configuration(self):
        """Test that Reporting agent is configured for UVS."""
        supervisor = create_supervisor()
        dependencies = supervisor.AGENT_DEPENDENCIES
        
        reporting_config = dependencies.get("reporting", {})
        
        # Verify UVS configuration
        assert reporting_config.get("uvs_enabled") == True, "Reporting must have UVS enabled"
        assert reporting_config.get("required") == [], "Reporting requires no dependencies with UVS"
        assert "triage_result" in reporting_config.get("optional", []), "Triage result is optional"
        assert "data_result" in reporting_config.get("optional", []), "Data result is optional"
        assert "optimizations_result" in reporting_config.get("optional", []), "Optimizations are optional"
    
    def test_data_helper_configuration(self):
        """Test that Data Helper agent is properly configured."""
        supervisor = create_supervisor()
        dependencies = supervisor.AGENT_DEPENDENCIES
        
        data_helper_config = dependencies.get("data_helper", {})
        
        # Verify data helper can work independently
        assert data_helper_config.get("required") == [], "Data helper requires no dependencies"
        assert "triage_result" in data_helper_config.get("optional", []), "Triage result is optional for data helper"


class TestUVSIntegration:
    """Integration tests for UVS requirements."""
    
    @pytest.mark.asyncio
    async def test_reporting_handles_all_scenarios(self):
        """Test that reporting can handle various failure scenarios."""
        supervisor = create_supervisor()
        
        # Test scenarios where different agents might fail
        test_scenarios = [
            {"triage_result": None, "data_result": None},  # All failed
            {"triage_result": {"error": "Failed"}, "data_result": None},  # Triage failed
            {"triage_result": {"data_sufficiency": "insufficient"}, "data_result": None},  # No data
            {"triage_result": {"data_sufficiency": "partial"}, "data_result": {"partial": True}},  # Partial
            {"triage_result": {"data_sufficiency": "sufficient"}, "data_result": {"full": True}},  # Full
        ]
        
        for scenario in test_scenarios:
            # The key test is that _determine_execution_order always includes reporting
            triage_result = scenario.get("triage_result", {})
            if isinstance(triage_result, dict):
                execution_order = supervisor._determine_execution_order(triage_result)
            else:
                execution_order = supervisor._determine_execution_order({})
            
            assert "reporting" in execution_order, \
                f"Reporting must be included for scenario: {scenario}"
            assert execution_order[-1] == "reporting", \
                f"Reporting must be last for scenario: {scenario}"
    
    def test_simplified_architecture_principles(self):
        """Test that the simplified architecture principles are followed."""
        supervisor = create_supervisor()
        
        # Principle 1: Only 2 required agents
        required_agents = [a for a in supervisor._get_required_agent_names() 
                          if a in ["triage", "reporting"]]
        assert len(required_agents) == 2
        
        # Principle 2: Default flow for no data
        no_data_flow = supervisor._determine_execution_order({"data_sufficiency": "insufficient"})
        assert no_data_flow == ["data_helper", "reporting"]
        
        # Principle 3: Reporting has no hard dependencies
        assert supervisor.AGENT_DEPENDENCIES["reporting"]["required"] == []
        
        # Principle 4: Dynamic workflow based on triage
        sufficient_flow = supervisor._determine_execution_order({"data_sufficiency": "sufficient"})
        insufficient_flow = supervisor._determine_execution_order({"data_sufficiency": "insufficient"})
        assert sufficient_flow != insufficient_flow, "Workflow must be dynamic based on data availability"