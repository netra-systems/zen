"""
Modern execution pattern tests for ActionsToMeetGoalsSubAgent
Tests for BaseExecutionInterface, ExecutionEngine, and modern patterns.
Compliance: <300 lines, 8-line max functions, modular design.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.state import DeepAgentState, ActionPlanResult
from app.agents.base.interface import ExecutionContext, ExecutionResult
from app.agents.base.errors import ValidationError
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing"""
    mock = MagicMock(spec=LLMManager)
    mock.ask_llm = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher for testing"""
    return MagicMock(spec=ToolDispatcher)


@pytest.fixture
def modern_actions_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create ActionsToMeetGoalsSubAgent with modern components mocked"""
    with patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_reliability_wrapper') as mock_reliability, \
         patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_fallback_strategy') as mock_fallback, \
         patch('app.agents.actions_to_meet_goals_sub_agent.ExecutionMonitor') as mock_monitor, \
         patch('app.agents.actions_to_meet_goals_sub_agent.ReliabilityManager') as mock_reliability_mgr, \
         patch('app.agents.actions_to_meet_goals_sub_agent.BaseExecutionEngine') as mock_exec_engine:
        
        # Mock modern components
        mock_monitor.return_value.get_health_status = MagicMock(return_value={"status": "healthy"})
        mock_monitor.return_value.get_agent_metrics = MagicMock(return_value={"metrics": {}})
        
        mock_reliability_mgr.return_value.get_health_status = MagicMock(return_value={"status": "healthy"})
        mock_reliability_mgr.return_value.get_circuit_breaker_status = MagicMock(return_value={"state": "closed"})
        
        mock_exec_engine.return_value.execute = AsyncMock()
        
        # Mock legacy components for compatibility
        mock_reliability.return_value = MagicMock()
        mock_reliability.return_value.execute_safely = AsyncMock()
        mock_reliability.return_value.get_health_status = MagicMock(return_value={"status": "healthy"})
        
        mock_fallback.return_value = MagicMock()
        mock_fallback.return_value.execute_with_fallback = AsyncMock()
        
        agent = ActionsToMeetGoalsSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent._send_update = AsyncMock()
        return agent


@pytest.fixture
def sample_execution_context():
    """Sample execution context for testing"""
    state = DeepAgentState(user_request="Create action plan for cost optimization")
    state.optimizations_result = {"optimization_type": "cost_reduction"}
    state.data_result = {"analysis_type": "cost_analysis"}
    
    return ExecutionContext(
        run_id="test-run-id",
        agent_name="ActionsToMeetGoalsSubAgent",
        state=state,
        stream_updates=True,
        metadata={"description": "Test execution"}
    )


class TestModernExecutionInterface:
    """Test modern BaseExecutionInterface methods"""
    
    async def test_validate_preconditions_success(self, modern_actions_agent, sample_execution_context):
        """Test successful precondition validation"""
        result = await modern_actions_agent.validate_preconditions(sample_execution_context)
        assert result is True

    async def test_validate_preconditions_missing_optimizations(self, modern_actions_agent):
        """Test precondition validation with missing optimizations_result"""
        state = DeepAgentState(user_request="Test request")
        state.data_result = {"test": "data"}
        # Missing optimizations_result
        
        context = ExecutionContext(
            run_id="test-run-id",
            agent_name="ActionsToMeetGoalsSubAgent",
            state=state,
            stream_updates=False,
            metadata={}
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await modern_actions_agent.validate_preconditions(context)
        
        assert "optimizations_result and data_result required" in str(exc_info.value)

    async def test_validate_preconditions_missing_data_result(self, modern_actions_agent):
        """Test precondition validation with missing data_result"""
        state = DeepAgentState(user_request="Test request")
        state.optimizations_result = {"test": "optimization"}
        # Missing data_result
        
        context = ExecutionContext(
            run_id="test-run-id",
            agent_name="ActionsToMeetGoalsSubAgent",
            state=state,
            stream_updates=False,
            metadata={}
        )
        
        with pytest.raises(ValidationError):
            await modern_actions_agent.validate_preconditions(context)

    async def test_execute_core_logic_success(self, modern_actions_agent, sample_execution_context):
        """Test successful core logic execution"""
        with patch.object(modern_actions_agent, '_get_llm_response', return_value='{"action_plan_summary": "test"}'), \
             patch.object(modern_actions_agent, '_process_llm_response') as mock_process:
            
            mock_action_plan = ActionPlanResult(action_plan_summary="Test plan")
            mock_process.return_value = mock_action_plan
            
            result = await modern_actions_agent.execute_core_logic(sample_execution_context)
            
        assert "action_plan_result" in result
        assert sample_execution_context.state.action_plan_result is not None

    async def test_send_status_update_with_stream(self, modern_actions_agent):
        """Test status update with streaming enabled"""
        context = ExecutionContext(
            run_id="test-run-id",
            agent_name="ActionsToMeetGoalsSubAgent",
            state=DeepAgentState(user_request="test"),
            stream_updates=True,
            metadata={}
        )
        
        await modern_actions_agent.send_status_update(context, "executing", "Testing message")
        
        # Verify update was sent with correct mapping
        modern_actions_agent._send_update.assert_called_once_with("test-run-id", {
            "status": "processing",
            "message": "Testing message"
        })

    async def test_send_status_update_without_stream(self, modern_actions_agent):
        """Test status update without streaming"""
        context = ExecutionContext(
            run_id="test-run-id",
            agent_name="ActionsToMeetGoalsSubAgent",
            state=DeepAgentState(user_request="test"),
            stream_updates=False,
            metadata={}
        )
        
        await modern_actions_agent.send_status_update(context, "completed", "Test complete")
        
        # Verify no update was sent when streaming disabled
        modern_actions_agent._send_update.assert_not_called()

    async def test_send_status_update_status_mapping(self, modern_actions_agent):
        """Test status update mapping for different statuses"""
        context = ExecutionContext(
            run_id="test-run-id",
            agent_name="ActionsToMeetGoalsSubAgent",
            state=DeepAgentState(user_request="test"),
            stream_updates=True,
            metadata={}
        )
        
        # Test different status mappings
        test_cases = [
            ("executing", "processing"),
            ("completed", "processed"),
            ("failed", "error"),
            ("unknown", "unknown")  # Unmapped status passes through
        ]
        
        for input_status, expected_status in test_cases:
            modern_actions_agent._send_update.reset_mock()
            await modern_actions_agent.send_status_update(context, input_status, f"Test {input_status}")
            
            modern_actions_agent._send_update.assert_called_once_with("test-run-id", {
                "status": expected_status,
                "message": f"Test {input_status}"
            })


class TestModernExecutionEngine:
    """Test modern execution engine integration"""
    
    async def test_execute_with_modern_engine_success(self, modern_actions_agent):
        """Test execution using modern engine - success path"""
        state = DeepAgentState(user_request="Test request")
        state.optimizations_result = {"test": "opt"}
        state.data_result = {"test": "data"}
        
        # Mock successful execution result
        success_result = ExecutionResult(
            success=True,
            data={"action_plan_result": "test"},
            execution_time=1.5,
            error=None
        )
        modern_actions_agent.execution_engine.execute = AsyncMock(return_value=success_result)
        
        await modern_actions_agent.execute(state, "test-run-id", True)
        
        # Verify modern execution was called
        modern_actions_agent.execution_engine.execute.assert_called_once()

    async def test_execute_with_modern_engine_failure(self, modern_actions_agent):
        """Test execution using modern engine - failure path"""
        state = DeepAgentState(user_request="Test request")
        state.optimizations_result = {"test": "opt"}
        state.data_result = {"test": "data"}
        
        # Mock failure result
        failure_result = ExecutionResult(
            success=False,
            data=None,
            execution_time=0.5,
            error="Test execution error"
        )
        modern_actions_agent.execution_engine.execute = AsyncMock(return_value=failure_result)
        
        await modern_actions_agent.execute(state, "test-run-id", False)
        
        # Verify fallback was applied and state has action plan result
        assert state.action_plan_result is not None

    async def test_execute_fallback_to_legacy(self, modern_actions_agent):
        """Test fallback to legacy execution path"""
        state = DeepAgentState(user_request="Test request")
        state.optimizations_result = {"test": "opt"}
        state.data_result = {"test": "data"}
        
        # Mock modern execution to raise exception
        modern_actions_agent.execution_engine.execute = AsyncMock(side_effect=Exception("Modern engine failed"))
        
        with patch.object(modern_actions_agent, '_execute_fallback_workflow') as mock_fallback:
            await modern_actions_agent.execute(state, "test-run-id", True)
            
            # Verify fallback workflow was called
            mock_fallback.assert_called_once_with(state, "test-run-id", True)


class TestModernHealthMonitoring:
    """Test modern health and monitoring features"""
    
    def test_get_health_status_comprehensive(self, modern_actions_agent):
        """Test comprehensive health status retrieval"""
        status = modern_actions_agent.get_health_status()
        
        assert isinstance(status, dict)
        assert "agent" in status
        assert "modern_health" in status
        assert "reliability" in status
        assert "legacy_health" in status
        assert status["agent"] == "ActionsToMeetGoalsSubAgent"

    def test_get_performance_metrics(self, modern_actions_agent):
        """Test performance metrics retrieval"""
        metrics = modern_actions_agent.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        # Verify monitor.get_agent_metrics was called with correct agent name
        modern_actions_agent.monitor.get_agent_metrics.assert_called_once_with("ActionsToMeetGoalsSubAgent")

    def test_get_circuit_breaker_status(self, modern_actions_agent):
        """Test circuit breaker status retrieval"""
        status = modern_actions_agent.get_circuit_breaker_status()
        
        assert isinstance(status, dict)
        # Verify reliability manager circuit breaker status was called
        modern_actions_agent.reliability_manager.get_circuit_breaker_status.assert_called_once()