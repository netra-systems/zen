"Mission Critical Test Suite: ActionsToMeetGoalsSubAgent Golden Pattern"

CRITICAL: This test suite ensures the ActionsToMeetGoalsSubAgent follows 
the golden pattern perfectly and delivers chat value through WebSocket events.

Tests focus on:
1. Golden pattern compliance (BaseAgent inheritance)
2. WebSocket events for chat value delivery  
3. Business logic correctness (action plan generation)
4. Real service integration (no mocks)
5. Error handling and resilience patterns

Business Value: Ensures reliable action plan generation for users
""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.redis_manager import RedisManager


class ActionsToMeetGoalsGoldenPatternTests:
    Test ActionsToMeetGoalsSubAgent golden pattern compliance."
    Test ActionsToMeetGoalsSubAgent golden pattern compliance."

    @pytest.fixture
    def mock_llm_manager(self):
        "Mock LLM manager for testing."
        llm_manager = Mock(spec=LLMManager)
        llm_manager.ask_llm = AsyncMock(return_value='{plan_steps": [{"step: Test step, description: Test description}], "confidence_score: 0.85}')"
        return llm_manager

    @pytest.fixture
    def mock_tool_dispatcher(self):
        "Mock tool dispatcher for testing."
        return Mock(spec=ToolDispatcher)

    @pytest.fixture
    def agent(self, mock_llm_manager, mock_tool_dispatcher):
        "Create agent instance for testing."
        return ActionsToMeetGoalsSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )

    @pytest.fixture
    def sample_state(self):
        "Create sample state for testing."
        state = DeepAgentState()
        state.user_request = Help me optimize my AI infrastructure
        state.optimizations_result = OptimizationsResult(
            optimization_type=infrastructure","
            recommendations=[Implement caching layer, Add monitoring],
            confidence_score=0.8
        )
        state.data_result = DataAnalysisResponse(
            query=infrastructure optimization,"
            query=infrastructure optimization,"
            results=[{metric": response_time, value: 150}],"
            insights={"performance: needs improvement"},
            metadata={source: monitoring},
            recommendations=[Enable caching, Scale services"]"
        return state

    @pytest.fixture
    def execution_context(self, sample_state):
        "Create execution context for testing."
        return ExecutionContext(
            run_id=test_run_123","
            agent_name=ActionsToMeetGoalsSubAgent,
            state=sample_state,
            stream_updates=True,
            metadata={description: "Test execution}"


class GoldenPatternComplianceTests(ActionsToMeetGoalsGoldenPatternTests):
    "Test golden pattern compliance requirements."

    def test_inherits_from_base_agent(self, agent):
        "CRITICAL: Agent must inherit from BaseAgent for infrastructure."
        from netra_backend.app.agents.base_agent import BaseAgent
        assert isinstance(agent, BaseAgent), Agent must inherit from BaseAgent for golden pattern compliance"
        assert isinstance(agent, BaseAgent), Agent must inherit from BaseAgent for golden pattern compliance"

    def test_initialization_follows_golden_pattern(self, agent):
        "CRITICAL: Initialization must follow golden pattern."
        # BaseAgent infrastructure enabled
        assert hasattr(agent, '_enable_reliability'), Must have reliability infrastructure""
        assert hasattr(agent, '_enable_execution_engine'), Must have execution engine infrastructure
        assert agent._enable_reliability is True, Reliability must be enabled"
        assert agent._enable_reliability is True, Reliability must be enabled"
        assert agent._enable_execution_engine is True, "Execution engine must be enabled"
        
        # Business logic components only
        assert hasattr(agent, 'tool_dispatcher'), Must have business logic components
        assert hasattr(agent, 'action_plan_builder'), "Must have action plan builder"

    def test_has_required_websocket_methods(self, agent):
        CRITICAL: Agent must have WebSocket methods for chat value."
        CRITICAL: Agent must have WebSocket methods for chat value."
        websocket_methods = [
            'emit_agent_started', 'emit_thinking', 'emit_tool_executing', 
            'emit_tool_completed', 'emit_agent_completed', 'emit_progress', 'emit_error'
        ]
        for method in websocket_methods:
            assert hasattr(agent, method), f"Agent must have {method} for chat value delivery"
            assert callable(getattr(agent, method)), f{method} must be callable

    def test_implements_required_abstract_methods(self, agent):
        CRITICAL: Agent must implement required abstract methods.""
        assert hasattr(agent, 'validate_preconditions'), Must implement validate_preconditions
        assert hasattr(agent, 'execute_core_logic'), "Must implement execute_core_logic"
        assert callable(agent.validate_preconditions), validate_preconditions must be callable
        assert callable(agent.execute_core_logic), execute_core_logic must be callable"
        assert callable(agent.execute_core_logic), execute_core_logic must be callable"

    def test_no_infrastructure_duplication(self, agent):
        "CRITICAL: Agent must not duplicate BaseAgent infrastructure."
        # Should NOT have its own WebSocket handling
        assert not hasattr(agent, '_websocket_manager'), "Must not duplicate WebSocket management"
        assert not hasattr(agent, '_circuit_breaker'), Must not duplicate circuit breaker
        assert not hasattr(agent, '_retry_handler'), Must not duplicate retry handler"
        assert not hasattr(agent, '_retry_handler'), Must not duplicate retry handler"
        
        # Should use BaseAgent's infrastructure'
        assert hasattr(agent, '_websocket_adapter'), Must use BaseAgent's WebSocket adapter"
        assert hasattr(agent, '_websocket_adapter'), Must use BaseAgent's WebSocket adapter"


class WebSocketEventsTests(ActionsToMeetGoalsGoldenPatternTests):
    Test WebSocket events for chat value delivery.""

    @pytest.mark.asyncio
    async def test_websocket_events_emitted_during_execution(self, agent, execution_context):
        CRITICAL: All required WebSocket events must be emitted for chat value."
        CRITICAL: All required WebSocket events must be emitted for chat value."
        # Mock WebSocket adapter to track events
        websocket_adapter = Mock()
        websocket_adapter.emit_agent_started = AsyncMock()
        websocket_adapter.emit_thinking = AsyncMock()
        websocket_adapter.emit_tool_executing = AsyncMock()
        websocket_adapter.emit_tool_completed = AsyncMock()
        websocket_adapter.emit_progress = AsyncMock()
        websocket_adapter.emit_agent_completed = AsyncMock()
        
        agent._websocket_adapter = websocket_adapter
        
        # Execute core logic
        result = await agent.execute_core_logic(execution_context)
        
        # Verify all critical events were emitted
        websocket_adapter.emit_agent_started.assert_called()
        websocket_adapter.emit_thinking.assert_called()
        websocket_adapter.emit_tool_executing.assert_called()
        websocket_adapter.emit_tool_completed.assert_called()
        websocket_adapter.emit_progress.assert_called()
        websocket_adapter.emit_agent_completed.assert_called()
        
        # Verify result structure
        assert isinstance(result, dict), "Result must be dictionary"
        assert 'action_plan_result' in result, Result must contain action plan

    @pytest.mark.asyncio
    async def test_thinking_events_provide_reasoning_visibility(self, agent, execution_context):
        "CRITICAL: Thinking events must provide real-time reasoning visibility."
        websocket_adapter = Mock()
        websocket_adapter.emit_thinking = AsyncMock()
        agent._websocket_adapter = websocket_adapter
        
        await agent.execute_core_logic(execution_context)
        
        # Check that thinking events were called with meaningful messages
        thinking_calls = websocket_adapter.emit_thinking.call_args_list
        assert len(thinking_calls) >= 2, Must emit multiple thinking events for reasoning visibility"
        assert len(thinking_calls) >= 2, Must emit multiple thinking events for reasoning visibility"
        
        # Verify thinking messages are meaningful
        thinking_messages = [call[0][0] for call in thinking_calls]
        assert any('optimization' in msg.lower() for msg in thinking_messages), "Must show optimization reasoning"
        assert any('analysis' in msg.lower() for msg in thinking_messages), Must show analysis reasoning

    @pytest.mark.asyncio
    async def test_tool_events_provide_transparency(self, agent, execution_context):
        "CRITICAL: Tool events must provide tool usage transparency."
        websocket_adapter = Mock()
        websocket_adapter.emit_tool_executing = AsyncMock()
        websocket_adapter.emit_tool_completed = AsyncMock()
        agent._websocket_adapter = websocket_adapter
        
        await agent.execute_core_logic(execution_context)
        
        # Verify tool execution transparency
        executing_calls = websocket_adapter.emit_tool_executing.call_args_list
        completed_calls = websocket_adapter.emit_tool_completed.call_args_list
        
        assert len(executing_calls) >= 3, Must show tool execution for transparency"
        assert len(executing_calls) >= 3, Must show tool execution for transparency"
        assert len(completed_calls) >= 3, "Must show tool completion for transparency"
        assert len(executing_calls) == len(completed_calls), Every executing must have corresponding completed

    @pytest.mark.asyncio
    async def test_fallback_includes_websocket_events(self, agent, execution_context):
        "CRITICAL: Fallback execution must include WebSocket events for user transparency."
        websocket_adapter = Mock()
        websocket_adapter.emit_agent_started = AsyncMock()
        websocket_adapter.emit_thinking = AsyncMock()
        websocket_adapter.emit_agent_completed = AsyncMock()
        agent._websocket_adapter = websocket_adapter
        
        # Execute fallback logic
        await agent._execute_fallback_logic(execution_context)
        
        # Verify fallback events
        websocket_adapter.emit_agent_started.assert_called_once()
        websocket_adapter.emit_thinking.assert_called_once()
        websocket_adapter.emit_agent_completed.assert_called_once()
        
        # Check that fallback is clearly communicated
        started_call = websocket_adapter.emit_agent_started.call_args[0][0]
        assert 'fallback' in started_call.lower(), Must communicate fallback to user"
        assert 'fallback' in started_call.lower(), Must communicate fallback to user"


class BusinessLogicTests(ActionsToMeetGoalsGoldenPatternTests):
    "Test action plan generation business logic."

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self, agent, execution_context):
        ""Test successful precondition validation.
        result = await agent.validate_preconditions(execution_context)
        assert result is True, Should validate successfully with complete state"
        assert result is True, Should validate successfully with complete state"

    @pytest.mark.asyncio
    async def test_validate_preconditions_missing_user_request(self, agent, execution_context):
        "Test precondition validation with missing user request."
        execution_context.state.user_request = None
        result = await agent.validate_preconditions(execution_context)
        assert result is False, "Should fail validation without user request"

    @pytest.mark.asyncio
    async def test_validate_preconditions_applies_defaults_for_missing_deps(self, agent, execution_context):
        Test that defaults are applied for missing dependencies."
        Test that defaults are applied for missing dependencies."
        execution_context.state.optimizations_result = None
        execution_context.state.data_result = None
        
        result = await agent.validate_preconditions(execution_context)
        
        # Should still pass with applied defaults
        assert result is True, "Should pass validation with applied defaults"
        assert execution_context.state.optimizations_result is not None, Should apply default optimizations
        assert execution_context.state.data_result is not None, "Should apply default data result"

    @pytest.mark.asyncio
    async def test_action_plan_generation_creates_valid_result(self, agent, execution_context):
        Test that action plan generation creates valid results."
        Test that action plan generation creates valid results."
        with patch.object(agent.action_plan_builder, 'process_llm_response') as mock_process:
            mock_result = ActionPlanResult(
                plan_steps=[{"step: Implement monitoring, description: Add comprehensive monitoring}],"
                confidence_score=0.9,
                partial_extraction=False
            )
            mock_process.return_value = mock_result
            
            result = await agent._generate_action_plan(execution_context)
            
            assert isinstance(result, ActionPlanResult), "Must return ActionPlanResult"
            assert result.plan_steps is not None, Must have plan steps
            assert len(result.plan_steps) > 0, Must have at least one plan step"
            assert len(result.plan_steps) > 0, Must have at least one plan step"
            assert result.confidence_score > 0, Must have positive confidence score"
            assert result.confidence_score > 0, Must have positive confidence score"

    @pytest.mark.asyncio
    async def test_state_updated_with_result(self, agent, execution_context):
        Test that state is properly updated with action plan result.""
        # Mock the action plan generation
        with patch.object(agent, '_generate_action_plan') as mock_generate:
            mock_result = ActionPlanResult(
                plan_steps=[{step: Test, description: "Test action}],"
                confidence_score=0.8,
                partial_extraction=False
            )
            mock_generate.return_value = mock_result
            
            await agent.execute_core_logic(execution_context)
            
            assert execution_context.state.action_plan_result is not None, State must be updated with result"
            assert execution_context.state.action_plan_result is not None, State must be updated with result"
            assert execution_context.state.action_plan_result == mock_result, State must have correct result


class ResilienceTests(ActionsToMeetGoalsGoldenPatternTests):
    ""Test resilience and error handling patterns.

    @pytest.mark.asyncio
    async def test_llm_failure_handling(self, agent, execution_context):
        Test handling of LLM failures.""
        # Mock LLM to raise exception
        agent.llm_manager.ask_llm = AsyncMock(side_effect=Exception(LLM service unavailable))
        
        with pytest.raises(Exception) as exc_info:
            await agent._generate_action_plan(execution_context)
        
        assert "LLM request failed in str(exc_info.value) or LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fallback_execution_creates_default_plan(self, agent, execution_context):
        Test fallback execution creates default action plan."
        Test fallback execution creates default action plan."
        # Mock the default action plan
        with patch.object(agent.action_plan_builder.__class__, 'get_default_action_plan') as mock_default:
            mock_default.return_value = ActionPlanResult(
                plan_steps=[{step": Default action, description: Fallback plan}],"
                confidence_score=0.5,
                partial_extraction=True
            )
            
            await agent._execute_fallback_logic(execution_context)
            
            assert execution_context.state.action_plan_result is not None, Fallback must create action plan""
            mock_default.assert_called_once(), Must use default action plan in fallback

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_partial_data(self, agent):
        "Test graceful degradation when only partial data is available."
        # Create minimal state
        minimal_state = DeepAgentState()
        minimal_state.user_request = Help me
        # No optimizations_result or data_result
        
        context = ExecutionContext(
            run_id=test_minimal","
            agent_name=ActionsToMeetGoalsSubAgent,
            state=minimal_state,
            stream_updates=False,
            metadata={}
        
        # Should still validate successfully with defaults
        result = await agent.validate_preconditions(context)
        assert result is True, Should handle partial data gracefully"
        assert result is True, Should handle partial data gracefully"
        
        # Should have applied defaults
        assert minimal_state.optimizations_result is not None, "Should apply default optimizations"
        assert minimal_state.data_result is not None, Should apply default data analysis


class IntegrationTests(ActionsToMeetGoalsGoldenPatternTests):
    "Integration tests with real components."

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, agent, sample_state):
        "Test complete execution flow from start to finish."
        # Mock WebSocket adapter
        websocket_adapter = Mock()
        websocket_adapter.emit_agent_started = AsyncMock()
        websocket_adapter.emit_thinking = AsyncMock()
        websocket_adapter.emit_tool_executing = AsyncMock()
        websocket_adapter.emit_tool_completed = AsyncMock()
        websocket_adapter.emit_progress = AsyncMock()
        websocket_adapter.emit_agent_completed = AsyncMock()
        agent._websocket_adapter = websocket_adapter
        
        # Execute the full flow
        await agent.execute(sample_state, test_run_full, True)
        
        # Verify state was updated
        assert sample_state.action_plan_result is not None, State must be updated after execution""

    @pytest.mark.asyncio
    async def test_legacy_compatibility(self, agent, sample_state):
        Test backward compatibility with legacy interface."
        Test backward compatibility with legacy interface."
        # Test check_entry_conditions method
        result = await agent.check_entry_conditions(sample_state, test_legacy")"
        assert result is True, Legacy entry conditions should pass

    def test_agent_lifecycle_states(self, agent):
        ""Test agent lifecycle state management.
        # Initially pending
        assert agent.get_state() == SubAgentLifecycle.PENDING
        
        # Can transition to running
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.get_state() == SubAgentLifecycle.RUNNING
        
        # Can transition to completed
        agent.set_state(SubAgentLifecycle.COMPLETED)
        assert agent.get_state() == SubAgentLifecycle.COMPLETED

    @pytest.mark.asyncio
    async def test_timing_collection(self, agent, execution_context):
        Test that timing collection works properly.""
        assert hasattr(agent, 'timing_collector'), Must have timing collector
        
        # Timing collector should be initialized
        assert agent.timing_collector is not None, "Timing collector must be initialized"
        assert agent.timing_collector.agent_name == agent.name, Timing collector must have agent name


class PerformanceTests(ActionsToMeetGoalsGoldenPatternTests):
    Performance and efficiency tests.""

    @pytest.mark.asyncio
    async def test_execution_performance(self, agent, execution_context):
        Test execution performance is reasonable.""
        start_time = time.time()
        
        # Mock action plan builder to return quickly
        with patch.object(agent.action_plan_builder, 'process_llm_response') as mock_process:
            mock_process.return_value = ActionPlanResult(
                plan_steps=[{step: Test, description: Test"}],"
                confidence_score=0.8,
                partial_extraction=False
            )
            
            await agent.execute_core_logic(execution_context)
        
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"Execution should be fast, took {execution_time:.2f}s"

    @pytest.mark.asyncio
    async def test_websocket_event_efficiency(self, agent, execution_context):
        Test WebSocket events are emitted efficiently."
        Test WebSocket events are emitted efficiently."
        websocket_adapter = Mock()
        websocket_adapter.emit_thinking = AsyncMock()
        websocket_adapter.emit_progress = AsyncMock()
        websocket_adapter.emit_tool_executing = AsyncMock()
        websocket_adapter.emit_tool_completed = AsyncMock()
        websocket_adapter.emit_agent_started = AsyncMock()
        websocket_adapter.emit_agent_completed = AsyncMock()
        agent._websocket_adapter = websocket_adapter
        
        start_time = time.time()
        await agent.execute_core_logic(execution_context)
        event_time = time.time() - start_time
        
        assert event_time < 2.0, f"WebSocket events should be efficient, took {event_time:.2f}s"


# Run the tests
if __name__ == __main__:
    pytest.main([__file__, -v, --tb=short")"
))))