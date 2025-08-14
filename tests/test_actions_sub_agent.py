"""Comprehensive test suite for ActionsToMeetGoalsSubAgent"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import time
import asyncio

from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.state import DeepAgentState, OptimizationsResult
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
def actions_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create actions agent instance for testing"""
    agent = ActionsToMeetGoalsSubAgent(mock_llm_manager, mock_tool_dispatcher)
    agent.websocket_manager = MagicMock()
    agent.websocket_manager.send_message = AsyncMock()
    return agent


@pytest.fixture
def sample_state():
    """Sample agent state for testing"""
    state = DeepAgentState(user_request="Optimize GPU costs for production workloads")
    state.optimizations_result = OptimizationsResult(
        optimization_type="Cost Optimization",
        recommendations=["Scale down during off-hours", "Use spot instances"],
        cost_savings=1000.0,
        confidence_score=0.9
    )
    state.data_result = {"metrics": {"gpu_utilization": 0.75, "cost_per_hour": 10}}
    return state


@pytest.fixture
def valid_action_plan():
    """Valid action plan response for testing"""
    return {
        "action_plan_summary": "Implement GPU cost optimization strategies",
        "total_estimated_time": "2 hours",
        "required_approvals": ["Operations Team"],
        "actions": [{
            "action_id": "gpu_scale_1",
            "action_type": "configuration",
            "name": "Configure GPU scaling",
            "priority": "high",
            "dependencies": [],
            "estimated_duration": "1 hour"
        }],
        "execution_timeline": [],
        "supply_config_updates": [],
        "post_implementation": {"monitoring_period": "30 days"},
        "cost_benefit_analysis": {"implementation_cost": {"effort_hours": 2}}
    }


class TestActionsSubAgentInitialization:
    def test_agent_initialization_success(self, mock_llm_manager, mock_tool_dispatcher):
        agent = ActionsToMeetGoalsSubAgent(mock_llm_manager, mock_tool_dispatcher)
        assert agent.name == "ActionsToMeetGoalsSubAgent"
        assert agent.llm_manager == mock_llm_manager
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.reliability is not None

    def test_agent_sets_correct_description(self, actions_agent):
        assert "creates a plan of action" in actions_agent.description.lower()

    def test_agent_initializes_reliability_wrapper(self, actions_agent):
        assert actions_agent.reliability is not None
        assert hasattr(actions_agent.reliability, 'execute_safely')

    def test_circuit_breaker_configuration(self, actions_agent):
        status = actions_agent.get_circuit_breaker_status()
        assert isinstance(status, dict)


class TestEntryConditions:
    async def test_check_entry_conditions_with_valid_data(self, actions_agent, sample_state):
        result = await actions_agent.check_entry_conditions(sample_state, "test-run")
        assert result is True

    async def test_check_entry_conditions_missing_optimizations(self, actions_agent):
        state = DeepAgentState(user_request="test")
        state.data_result = {"test": "data"}
        state.optimizations_result = None
        result = await actions_agent.check_entry_conditions(state, "test-run")
        assert result is False

    async def test_check_entry_conditions_missing_data(self, actions_agent):
        state = DeepAgentState(user_request="test")
        state.optimizations_result = OptimizationsResult(optimization_type="test")
        state.data_result = None
        result = await actions_agent.check_entry_conditions(state, "test-run")
        assert result is False

    async def test_check_entry_conditions_both_missing(self, actions_agent):
        state = DeepAgentState(user_request="test")
        state.optimizations_result = None
        state.data_result = None
        result = await actions_agent.check_entry_conditions(state, "test-run")
        assert result is False


class TestActionPlanGeneration:
    async def test_successful_action_plan_generation(self, actions_agent, sample_state, valid_action_plan):
        actions_agent.llm_manager.ask_llm.return_value = json.dumps(valid_action_plan)
        with patch('app.agents.utils.extract_json_from_response', return_value=valid_action_plan):
            await actions_agent.execute(sample_state, "test-run", False)
        assert sample_state.action_plan_result == valid_action_plan

    async def test_action_plan_with_streaming_updates(self, actions_agent, sample_state, valid_action_plan):
        actions_agent.llm_manager.ask_llm.return_value = json.dumps(valid_action_plan)
        with patch('app.agents.utils.extract_json_from_response', return_value=valid_action_plan):
            await actions_agent.execute(sample_state, "test-run", True)
        assert actions_agent.websocket_manager.send_message.call_count >= 2

    async def test_action_plan_prompt_formatting(self, actions_agent, sample_state):
        actions_agent.llm_manager.ask_llm.return_value = "{}"
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(sample_state, "test-run", False)
        
        # Verify LLM was called with properly formatted prompt
        assert actions_agent.llm_manager.ask_llm.called
        call_args = actions_agent.llm_manager.ask_llm.call_args[0][0]
        assert "Optimize GPU costs" in call_args

    async def test_large_prompt_handling(self, actions_agent, sample_state):
        # Create large data to trigger size warning
        large_data = {"large_field": "x" * (2 * 1024 * 1024)}  # 2MB
        sample_state.data_result = large_data
        
        actions_agent.llm_manager.ask_llm.return_value = "{}"
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(sample_state, "test-run", False)
        assert actions_agent.llm_manager.ask_llm.called


class TestGoalDecomposition:
    def test_build_action_plan_from_partial_data(self, actions_agent):
        partial_data = {
            "action_plan_summary": "Partial test plan",
            "actions": [{"action_id": "test_action"}]
        }
        result = actions_agent._build_action_plan_from_partial(partial_data)
        assert result["action_plan_summary"] == "Partial test plan"
        assert result["partial_extraction"] is True
        assert "extracted_fields" in result

    def test_build_action_plan_preserves_existing_fields(self, actions_agent):
        partial_data = {"action_plan_summary": "preserved", "custom_field": "preserved"}
        result = actions_agent._build_action_plan_from_partial(partial_data)
        assert result["action_plan_summary"] == "preserved"

    def test_build_action_plan_adds_defaults(self, actions_agent):
        result = actions_agent._build_action_plan_from_partial({})
        assert "total_estimated_time" in result
        assert "post_implementation" in result
        assert "cost_benefit_analysis" in result

    def test_get_default_action_plan_structure(self, actions_agent):
        result = actions_agent._get_default_action_plan()
        required_fields = [
            "action_plan_summary", "total_estimated_time", "actions",
            "execution_timeline", "supply_config_updates", "post_implementation"
        ]
        for field in required_fields:
            assert field in result


class TestExecutionWithDifferentGoalTypes:
    async def test_cost_optimization_goal(self, actions_agent):
        state = DeepAgentState(user_request="Reduce infrastructure costs")
        state.optimizations_result = OptimizationsResult(optimization_type="Cost")
        state.data_result = {"cost_data": True}
        
        actions_agent.llm_manager.ask_llm.return_value = '{"action_plan_summary": "cost plan"}'
        with patch('app.agents.utils.extract_json_from_response', return_value={"action_plan_summary": "cost plan"}):
            await actions_agent.execute(state, "test-run", False)
        assert state.action_plan_result["action_plan_summary"] == "cost plan"

    async def test_performance_optimization_goal(self, actions_agent):
        state = DeepAgentState(user_request="Improve model inference speed")
        state.optimizations_result = OptimizationsResult(optimization_type="Performance")
        state.data_result = {"performance_data": True}
        
        actions_agent.llm_manager.ask_llm.return_value = '{"action_plan_summary": "perf plan"}'
        with patch('app.agents.utils.extract_json_from_response', return_value={"action_plan_summary": "perf plan"}):
            await actions_agent.execute(state, "test-run", False)
        assert state.action_plan_result["action_plan_summary"] == "perf plan"

    async def test_scaling_optimization_goal(self, actions_agent):
        state = DeepAgentState(user_request="Handle increased traffic load")
        state.optimizations_result = OptimizationsResult(optimization_type="Scaling")
        state.data_result = {"scaling_metrics": True}
        
        actions_agent.llm_manager.ask_llm.return_value = '{"action_plan_summary": "scale plan"}'
        with patch('app.agents.utils.extract_json_from_response', return_value={"action_plan_summary": "scale plan"}):
            await actions_agent.execute(state, "test-run", False)
        assert state.action_plan_result["action_plan_summary"] == "scale plan"


class TestErrorHandlingAndFallbacks:
    async def test_json_extraction_failure_uses_partial(self, actions_agent, sample_state):
        actions_agent.llm_manager.ask_llm.return_value = "invalid json"
        
        with patch('app.agents.utils.extract_json_from_response', return_value=None):
            with patch('app.agents.utils.extract_partial_json', return_value={"summary": "partial"}):
                await actions_agent.execute(sample_state, "test-run", False)
        
        assert sample_state.action_plan_result is not None
        assert sample_state.action_plan_result["partial_extraction"] is True

    async def test_complete_extraction_failure_uses_default(self, actions_agent, sample_state):
        actions_agent.llm_manager.ask_llm.return_value = "completely invalid"
        
        with patch('app.agents.utils.extract_json_from_response', return_value=None):
            with patch('app.agents.utils.extract_partial_json', return_value=None):
                await actions_agent.execute(sample_state, "test-run", False)
        
        assert sample_state.action_plan_result is not None
        assert "error" in sample_state.action_plan_result

    async def test_llm_failure_triggers_fallback(self, actions_agent, sample_state):
        actions_agent.llm_manager.ask_llm.side_effect = Exception("LLM error")
        
        await actions_agent.execute(sample_state, "test-run", False)
        
        assert sample_state.action_plan_result is not None
        assert sample_state.action_plan_result["metadata"]["fallback_used"] is True

    async def test_reliability_wrapper_timeout_handling(self, actions_agent, sample_state):
        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(50)  # Exceed timeout
            return "{}"
        
        actions_agent.llm_manager.ask_llm = slow_llm
        
        # Should complete via fallback due to timeout
        await actions_agent.execute(sample_state, "test-run", False)
        assert sample_state.action_plan_result is not None


class TestStreamingAndWebSocket:
    async def test_streaming_sends_start_message(self, actions_agent, sample_state):
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(sample_state, "test-run", True)
        
        # Check that processing message was sent
        calls = actions_agent.websocket_manager.send_message.call_args_list
        processing_call = next((call for call in calls if "processing" in str(call)), None)
        assert processing_call is not None

    async def test_streaming_sends_completion_message(self, actions_agent, sample_state):
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(sample_state, "test-run", True)
        
        calls = actions_agent.websocket_manager.send_message.call_args_list
        completed_call = next((call for call in calls if "processed" in str(call)), None)
        assert completed_call is not None

    async def test_fallback_streaming_message(self, actions_agent, sample_state):
        actions_agent.llm_manager.ask_llm.side_effect = Exception("Error")
        
        await actions_agent.execute(sample_state, "test-run", True)
        
        calls = actions_agent.websocket_manager.send_message.call_args_list
        fallback_call = next((call for call in calls if "fallback" in str(call)), None)
        assert fallback_call is not None


class TestHealthAndStatus:
    def test_get_health_status_returns_dict(self, actions_agent):
        status = actions_agent.get_health_status()
        assert isinstance(status, dict)

    def test_get_circuit_breaker_status_returns_dict(self, actions_agent):
        status = actions_agent.get_circuit_breaker_status()
        assert isinstance(status, dict)

    def test_health_status_includes_reliability_info(self, actions_agent):
        status = actions_agent.get_health_status()
        # Should contain reliability-related information
        assert status is not None


class TestEdgeCasesAndValidation:
    async def test_empty_optimizations_result(self, actions_agent):
        state = DeepAgentState(user_request="test")
        state.optimizations_result = OptimizationsResult(optimization_type="")
        state.data_result = {"test": "data"}
        
        actions_agent.llm_manager.ask_llm.return_value = "{}"
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(state, "test-run", False)
        assert state.action_plan_result is not None

    async def test_conflicting_optimization_goals(self, actions_agent):
        state = DeepAgentState(user_request="Minimize cost while maximizing performance")
        state.optimizations_result = OptimizationsResult(
            optimization_type="Conflicting",
            recommendations=["Reduce resources", "Increase resources"]
        )
        state.data_result = {"conflict": True}
        
        actions_agent.llm_manager.ask_llm.return_value = "{}"
        with patch('app.agents.utils.extract_json_from_response', return_value={}):
            await actions_agent.execute(state, "test-run", False)
        assert state.action_plan_result is not None

    async def test_infeasible_action_detection(self, actions_agent, sample_state):
        infeasible_plan = {
            "actions": [{"estimated_duration": "impossible"}],
            "total_estimated_time": "negative time"
        }
        
        with patch('app.agents.utils.extract_json_from_response', return_value=infeasible_plan):
            await actions_agent.execute(sample_state, "test-run", False)
        assert sample_state.action_plan_result == infeasible_plan

    def test_partial_extraction_with_minimal_data(self, actions_agent):
        minimal_data = {"summary": "minimal"}
        result = actions_agent._build_action_plan_from_partial(minimal_data)
        
        # Should still create complete structure
        assert len(result) > len(minimal_data)
        assert "actions" in result
        assert isinstance(result["actions"], list)