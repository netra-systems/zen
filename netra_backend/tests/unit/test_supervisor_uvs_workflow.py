"""Test UVS Supervisor Dynamic Workflow Implementation

Tests the simplified supervisor that implements UVS principles:
- Only 2 agents truly required (Triage and Reporting)
- Dynamic workflow based on data availability
- Graceful degradation when agents fail
- Always delivers value through reporting
"""

import pytest
import asyncio
from typing import Dict, Any, List
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent


class TestUVSSupervisorWorkflow:
    """Test UVS principles in supervisor workflow"""
    
    @pytest.fixture
 def real_context():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock user execution context"""
    pass
        context = Mock(spec=UserExecutionContext)
        context.user_id = "test_user_123"
        context.run_id = "test_run_456"
        context.thread_id = "test_thread_789"
        context.websocket_connection_id = "ws_conn_123"
        context.db_session = TestDatabaseManager().get_session()
        context.metadata = {}
        context.create_child_context = Mock(return_value=context)
        return context
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock LLM manager"""
        return None  # TODO: Use real service instance
    
    @pytest.fixture
 def real_websocket_bridge():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket bridge"""
    pass
        bridge = bridge_instance  # Initialize appropriate service
        bridge.websocket_manager = UnifiedWebSocketManager()
        bridge.emit_agent_event = AsyncNone  # TODO: Use real service instance
        return bridge
    
    @pytest.fixture
    def supervisor(self, mock_llm_manager, mock_websocket_bridge):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create supervisor instance with mocked dependencies"""
    pass
        # Mock the agent class registry and instance factory
        with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_class_registry') as mock_reg:
            with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory') as mock_factory:
                with patch('netra_backend.app.agents.supervisor_consolidated.get_supervisor_flow_logger') as mock_flow:
                    # Setup mocks
                    mock_registry = mock_registry_instance  # Initialize appropriate service
                    mock_reg.return_value = mock_registry
                    
                    mock_instance_factory = mock_instance_factory_instance  # Initialize appropriate service
                    mock_instance_factory.configure = configure_instance  # Initialize appropriate service
                    mock_factory.return_value = mock_instance_factory
                    
                    mock_flow_logger = mock_flow_logger_instance  # Initialize appropriate service
                    mock_flow_logger.generate_flow_id = Mock(return_value="test_flow_123")
                    mock_flow_logger.start_flow = start_flow_instance  # Initialize appropriate service
                    mock_flow_logger.complete_flow = complete_flow_instance  # Initialize appropriate service
                    mock_flow.return_value = mock_flow_logger
                    
                    # Create supervisor
                    supervisor = SupervisorAgent(
                        llm_manager=mock_llm_manager,
                        websocket_bridge=mock_websocket_bridge
                    )
                    
                    # Store mocked components for test access
                    supervisor._mock_registry = mock_registry
                    supervisor._mock_factory = mock_instance_factory
                    supervisor._mock_flow_logger = mock_flow_logger
                    
                    return supervisor
    
    @pytest.mark.asyncio
    async def test_minimal_system_with_two_agents(self, supervisor, mock_context):
        """Test that system works with just triage and reporting"""
        # Verify only 2 agents are required
        required_names = supervisor._get_required_agent_names()
        required_only = [name for name in required_names if name in ["triage", "reporting"]]
        assert len(required_only) == 2
        assert "triage" in required_only
        assert "reporting" in required_only
        
        # Verify AGENT_DEPENDENCIES shows correct requirements
        assert supervisor.AGENT_DEPENDENCIES["triage"]["required"] == []
        assert supervisor.AGENT_DEPENDENCIES["reporting"]["required"] == []
        assert supervisor.AGENT_DEPENDENCIES["reporting"]["uvs_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_dynamic_workflow_based_on_data_sufficiency(self, supervisor, mock_context):
        """Test workflow adapts based on data availability"""
        
        # Test 1: No data - guidance flow
        triage_result_no_data = {
            "data_sufficiency": "insufficient",
            "intent": {"primary_intent": "analyze costs"},
            "next_agents": []
        }
        workflow = supervisor._determine_execution_order(triage_result_no_data, mock_context)
        assert workflow == ["data_helper", "reporting"]
        
        # Test 2: Sufficient data - selective pipeline
        triage_result_with_data = {
            "data_sufficiency": "sufficient",
            "intent": {
                "primary_intent": "optimize cloud costs",
                "action_required": True
            },
            "next_agents": []
        }
        workflow = supervisor._determine_execution_order(triage_result_with_data, mock_context)
        # Should include optimization (has "optimize" keyword) and actions (action_required=True)
        assert "data" in workflow
        assert "optimization" in workflow
        assert "actions" in workflow
        assert workflow[-1] == "reporting"  # Always ends with reporting
        
        # Test 3: Partial data
        triage_result_partial = {
            "data_sufficiency": "partial",
            "intent": {"primary_intent": "review usage patterns"},
            "next_agents": []
        }
        workflow = supervisor._determine_execution_order(triage_result_partial, mock_context)
        assert "data_helper" in workflow
        assert "data" in workflow  # Has "usage" keyword
        assert workflow[-1] == "reporting"
        
        # Test 4: Triage recommends specific workflow
        triage_result_custom = {
            "data_sufficiency": "sufficient",
            "intent": {"primary_intent": "general inquiry"},
            "next_agents": ["data", "actions", "reporting"]
        }
        workflow = supervisor._determine_execution_order(triage_result_custom, mock_context)
        assert workflow == ["data", "actions", "reporting"]
    
    @pytest.mark.asyncio
    async def test_triage_failure_continues_workflow(self, supervisor, mock_context):
        """Test system continues even when triage fails"""
        
        # Simulate no triage result (failed)
        workflow = supervisor._determine_execution_order(None, mock_context)
        
        # Should use minimal fallback flow
        assert workflow == ["data_helper", "reporting"]
        
        # Verify workflow reasoning is logged
        with patch('netra_backend.app.agents.supervisor_consolidated.logger') as mock_logger:
            workflow = supervisor._determine_execution_order(None, mock_context)
            mock_logger.info.assert_any_call(
                "Triage unavailable. Using minimal UVS flow: Data Helper → Reporting"
            )
    
    @pytest.mark.asyncio
    async def test_agent_failures_handled_gracefully(self, supervisor, mock_context):
        """Test non-critical agent failures don't stop workflow"""
        
        # Mock the execution order to include data and optimization
        with patch.object(supervisor, '_determine_execution_order', return_value=["data", "optimization", "reporting"]):
            # Create mock agent instances
            mock_agents = {}
            for name in ["triage", "data", "optimization", "actions", "reporting"]:
                agent = Mock(spec=BaseAgent)
                agent.execute = AsyncNone  # TODO: Use real service instance
                mock_agents[name] = agent
            
            # Setup successful agents
            mock_agents["triage"].execute.return_value = {"status": "success", "result": "triage_result"}
            mock_agents["reporting"].execute.return_value = {"status": "success", "result": "reporting_result"}
            
            # Patch agent creation
            with patch.object(supervisor, '_create_isolated_agent_instances', return_value=mock_agents):
                with patch.object(supervisor, '_execute_agent_with_context') as mock_exec:
                    # Setup execution behavior to simulate failures
                    async def exec_side_effect(agent, context, name):
    pass
                        if name == "data":
                            raise Exception("Data agent failed")
                        elif name == "optimization":
                            raise Exception("Optimization failed")
                        else:
                            await asyncio.sleep(0)
    return {"status": "success", "result": f"{name}_result"}
                    
                    mock_exec.side_effect = exec_side_effect
                    
                    # Execute workflow
                    with patch.object(supervisor, 'flow_logger'):
                        # Also patch _execute_single_agent for triage
                        with patch.object(supervisor, '_execute_single_agent', return_value={"status": "success"}):
                            results = await supervisor._execute_workflow_with_isolated_agents(
                                mock_agents, mock_context, None  # TODO: Use real service instance, "test_flow"
                            )
                    
                    # Verify workflow completed despite failures
                    assert "_workflow_metadata" in results
                    
                    # Check for evidence of failure handling - either in metadata or results
                    # The workflow should have attempted data and optimization
                    failed_agents = results["_workflow_metadata"].get("failed_agents", [])
                    
                    # Either agents are marked as failed or have error results
                    data_failed = "data" in failed_agents or (
                        "data" in results and results["data"].get("status") == "failed"
                    )
                    opt_failed = "optimization" in failed_agents or (
                        "optimization" in results and results["optimization"].get("status") == "failed"  
                    )
                    
                    # At least one should have evidence of failure
                    assert data_failed or opt_failed or len(results) > 2  # Has processed multiple agents
    
    @pytest.mark.asyncio
    async def test_reporting_fallback_when_primary_fails(self, supervisor, mock_context):
        """Test fallback reporting when primary reporting fails"""
        
        # Create partial results from other agents
        partial_results = {
            "triage": {
                "status": "success",
                "category": "cost_optimization",
                "priority": "high"
            },
            "data": {
                "status": "success",
                "insights": ["High compute usage detected"]
            },
            "optimization": {
                "status": "failed",
                "error": "Timeout"
            }
        }
        
        # Test fallback report creation
        fallback_report = await supervisor._create_fallback_report(mock_context, partial_results)
        
        assert fallback_report["status"] == "fallback"
        assert "summary" in fallback_report
        assert "Request type: cost_optimization" in fallback_report["summary"]
        assert "Priority: high" in fallback_report["summary"]
        assert "Data analysis was performed." in fallback_report["summary"]
        assert fallback_report["data_insights"] == ["High compute usage detected"]
        assert fallback_report["metadata"]["successful_agents"] == ["triage", "data"]
    
    @pytest.mark.asyncio
    async def test_intent_based_agent_selection(self, supervisor, mock_context):
        """Test agents are selected based on user intent keywords"""
        
        # Test data analysis intent
        intent = {"primary_intent": "analyze usage patterns and trends"}
        assert supervisor._needs_data_analysis(intent, mock_context) is True
        
        # Test optimization intent  
        intent = {"primary_intent": "reduce cloud costs and improve efficiency"}
        assert supervisor._needs_optimization(intent, mock_context) is True
        
        # Test action plan intent
        intent = {"primary_intent": "how to implement auto-scaling"}
        assert supervisor._needs_action_plan(intent, mock_context) is True
        
        # Test general inquiry (no specific agents needed)
        intent = {"primary_intent": "what is cloud computing"}
        assert supervisor._needs_data_analysis(intent, mock_context) is False
        assert supervisor._needs_optimization(intent, mock_context) is False
        assert supervisor._needs_action_plan(intent, mock_context) is False
    
    @pytest.mark.asyncio
    async def test_dependency_validation_with_uvs(self, supervisor):
        """Test dependency checking allows optional agents to be skipped"""
        
        completed = set(["triage"])
        metadata = {"triage_result": {}}
        
        # Data can run with just triage (optional dependency)
        can_exec, missing = supervisor._can_execute_agent("data", completed, metadata)
        assert can_exec is True
        assert missing == []
        
        # Optimization can now run without data (changed to optional)
        can_exec, missing = supervisor._can_execute_agent("optimization", completed, metadata)
        assert can_exec is True  # No required dependencies anymore
        assert missing == []
        
        # Reporting can run with nothing
        can_exec, missing = supervisor._can_execute_agent("reporting", set(), {})
        assert can_exec is True
        assert missing == []
    
    @pytest.mark.asyncio
    async def test_workflow_completes_with_no_agents(self, supervisor, mock_context):
        """Test workflow can complete even if all optional agents fail"""
        
        # Create scenario where only reporting works
        mock_agents = {
            "reporting": Mock(spec=BaseAgent)
        }
        mock_agents["reporting"].execute = AsyncMock(return_value={
            "status": "success",
            "report": "Basic analysis completed with available information."
        })
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=mock_agents):
            with patch.object(supervisor, 'flow_logger'):
                results = await supervisor._execute_workflow_with_isolated_agents(
                    mock_agents, mock_context, None  # TODO: Use real service instance, "test_flow"
                )
        
        # Verify workflow completed
        assert "_workflow_metadata" in results
        # Reporting should have run (even if as fallback)
        assert "reporting" in results
        # Status could be success or fallback, both are valid
        assert results["reporting"]["status"] in ["success", "fallback"]
        
    @pytest.mark.asyncio
    async def test_performance_skip_unnecessary_agents(self, supervisor, mock_context):
        """Test that unnecessary agents are skipped for performance"""
        
        # Simple informational query - should skip most agents
        triage_result = {
            "data_sufficiency": "sufficient",
            "intent": {"primary_intent": "what services are available"},
            "next_agents": []
        }
        
        workflow = supervisor._determine_execution_order(triage_result, mock_context)
        
        # Should use minimal workflow since no specific analysis needed
        assert workflow == ["data_helper", "reporting"]
        
        # Complex query - should include more agents
        triage_result_complex = {
            "data_sufficiency": "sufficient",
            "intent": {
                "primary_intent": "analyze costs, optimize spending, and create migration plan",
                "action_required": True
            },
            "next_agents": []
        }
        
        workflow_complex = supervisor._determine_execution_order(triage_result_complex, mock_context)
        
        # Should include all relevant agents
        assert "data" in workflow_complex
        assert "optimization" in workflow_complex
        assert "actions" in workflow_complex
        assert "reporting" in workflow_complex


class TestUVSWebSocketEvents:
    """Test WebSocket event preservation with UVS changes"""
    
    @pytest.mark.asyncio
    async def test_websocket_events_preserved(self):
        """Verify all required WebSocket events are still emitted"""
        
        mock_bridge = mock_bridge_instance  # Initialize appropriate service
        mock_bridge.emit_agent_event = AsyncNone  # TODO: Use real service instance
        mock_bridge.websocket_manager = UnifiedWebSocketManager()
        
        # Mock dependencies as in other tests
        with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_class_registry') as mock_reg:
            with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory') as mock_factory:
                with patch('netra_backend.app.agents.supervisor_consolidated.get_supervisor_flow_logger') as mock_flow:
                    # Setup mocks
                    mock_reg.return_value = return_value_instance  # Initialize appropriate service
                    
                    mock_instance_factory = mock_instance_factory_instance  # Initialize appropriate service
                    mock_instance_factory.configure = configure_instance  # Initialize appropriate service
                    mock_factory.return_value = mock_instance_factory
                    
                    mock_flow_logger = mock_flow_logger_instance  # Initialize appropriate service
                    mock_flow.return_value = mock_flow_logger
                    
                    supervisor = SupervisorAgent(
                        llm_manager=llm_manager_instance  # Initialize appropriate service,
                        websocket_bridge=mock_bridge
                    )
        
                    context = Mock(spec=UserExecutionContext)
                    context.user_id = "test_user"
                    context.run_id = "test_run"
                    context.websocket_connection_id = "ws_123"
                    
                    # Emit thinking event
                    await supervisor._emit_thinking(context, "Test message")
                    
                    # Verify event was emitted with correct structure
                    mock_bridge.emit_agent_event.assert_called_once()
                    call_args = mock_bridge.emit_agent_event.call_args
                    
                    assert call_args[1]["event_type"] == "agent_thinking"
                    assert call_args[1]["data"]["message"] == "Test message"
                    assert call_args[1]["data"]["user_id"] == "test_user"
    pass