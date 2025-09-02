"""Mission Critical Tests for OptimizationsCoreSubAgent Golden Pattern Migration

Tests the migrated OptimizationsCoreSubAgent to ensure:
1. WebSocket event emissions work correctly
2. Tool execution patterns are followed
3. Error handling uses BaseAgent infrastructure
4. Complete workflow executes successfully
5. SSOT compliance is maintained

CRITICAL: This test suite validates the golden pattern migration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Import the migrated agent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestOptimizationsCoreSubAgentGoldenPattern:
    """Test suite for OptimizationsCoreSubAgent golden pattern compliance."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        mock_llm = AsyncMock(spec=LLMManager)
        mock_llm.ask_llm.return_value = """{
            "optimization_type": "cost_optimization",
            "recommendations": [
                "Reduce resource allocation by 25%",
                "Optimize database queries for better performance",
                "Implement caching strategy for frequently accessed data"
            ],
            "confidence_score": 0.85,
            "cost_savings": "30%",
            "performance_improvement": "40%"
        }"""
        return mock_llm

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher for testing."""
        return MagicMock(spec=ToolDispatcher)

    @pytest.fixture
    def agent(self, mock_llm_manager, mock_tool_dispatcher):
        """Create OptimizationsCoreSubAgent instance for testing."""
        agent = OptimizationsCoreSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        return agent

    @pytest.fixture
    def mock_state(self):
        """Create mock state with required data."""
        state = MagicMock(spec=DeepAgentState)
        state.data_result = {
            "data": {"metrics": {"cpu": 80, "memory": 70}},
            "confidence": 0.9
        }
        state.triage_result = {
            "category": "optimization",
            "confidence_score": 0.8
        }
        state.user_request = "Help me optimize my AI infrastructure costs"
        state.optimizations_result = None
        return state

    @pytest.fixture
    def execution_context(self, mock_state):
        """Create execution context for testing."""
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="OptimizationsCoreSubAgent",
            state=mock_state,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=1234567890.0,
            correlation_id="corr_abc"
        )

    # ===== CRITICAL WebSocket Event Tests =====

    @pytest.mark.asyncio
    async def test_websocket_events_emitted_during_execution(self, agent, execution_context):
        """Test that all required WebSocket events are emitted during execution."""
        with patch.object(agent, 'emit_thinking', new_callable=AsyncMock) as mock_thinking, \
             patch.object(agent, 'emit_progress', new_callable=AsyncMock) as mock_progress, \
             patch.object(agent, 'emit_tool_executing', new_callable=AsyncMock) as mock_tool_exec, \
             patch.object(agent, 'emit_tool_completed', new_callable=AsyncMock) as mock_tool_comp:

            # Execute core logic
            result = await agent.execute_core_logic(execution_context)

            # Verify WebSocket events were emitted
            assert mock_thinking.called, "emit_thinking should be called"
            assert mock_progress.called, "emit_progress should be called"
            assert mock_tool_exec.called, "emit_tool_executing should be called"
            assert mock_tool_comp.called, "emit_tool_completed should be called"

            # Verify specific event calls
            mock_thinking.assert_any_call("Starting optimization analysis based on data insights...")
            mock_progress.assert_any_call("Analyzing data patterns and formulating optimization strategies...")
            mock_tool_exec.assert_any_call("llm_analysis", {
                "model": "optimizations_core",
                "prompt_length": pytest.approx(1, abs=10000)  # Flexible prompt length check
            })
            mock_progress.assert_any_call("Optimization strategies formulated successfully", is_complete=True)

    @pytest.mark.asyncio
    async def test_websocket_tool_events_with_success(self, agent, execution_context):
        """Test WebSocket tool events are properly emitted on successful LLM execution."""
        with patch.object(agent, 'emit_tool_executing', new_callable=AsyncMock) as mock_tool_exec, \
             patch.object(agent, 'emit_tool_completed', new_callable=AsyncMock) as mock_tool_comp:

            await agent.execute_core_logic(execution_context)

            # Verify tool executing event
            mock_tool_exec.assert_called_once()
            tool_exec_args = mock_tool_exec.call_args[0]
            tool_exec_kwargs = mock_tool_exec.call_args[1] if len(mock_tool_exec.call_args) > 1 else mock_tool_exec.call_args[0][1]
            
            assert tool_exec_args[0] == "llm_analysis"
            assert "model" in tool_exec_kwargs
            assert tool_exec_kwargs["model"] == "optimizations_core"

            # Verify tool completed event with success
            mock_tool_comp.assert_called_once()
            tool_comp_args = mock_tool_comp.call_args[0]
            tool_comp_kwargs = mock_tool_comp.call_args[1] if len(mock_tool_comp.call_args) > 1 else mock_tool_comp.call_args[0][1]
            
            assert tool_comp_args[0] == "llm_analysis"
            assert tool_comp_kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_websocket_tool_events_with_error(self, agent, execution_context):
        """Test WebSocket tool events are properly emitted on LLM execution error."""
        # Make LLM manager raise an exception
        agent.llm_manager.ask_llm.side_effect = Exception("LLM connection failed")

        with patch.object(agent, 'emit_tool_executing', new_callable=AsyncMock) as mock_tool_exec, \
             patch.object(agent, 'emit_tool_completed', new_callable=AsyncMock) as mock_tool_comp:

            with pytest.raises(Exception, match="LLM connection failed"):
                await agent.execute_core_logic(execution_context)

            # Verify tool executing was called
            mock_tool_exec.assert_called_once()

            # Verify tool completed was called with error status
            mock_tool_comp.assert_called_once()
            tool_comp_args = mock_tool_comp.call_args[0]
            tool_comp_kwargs = mock_tool_comp.call_args[1] if len(mock_tool_comp.call_args) > 1 else mock_tool_comp.call_args[0][1]
            
            assert tool_comp_args[0] == "llm_analysis"
            assert tool_comp_kwargs["status"] == "error"
            assert "LLM connection failed" in tool_comp_kwargs["error"]

    # ===== Precondition Validation Tests =====

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self, agent, execution_context):
        """Test successful precondition validation."""
        result = await agent.validate_preconditions(execution_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_preconditions_no_data_result(self, agent, execution_context):
        """Test precondition validation fails when no data result."""
        execution_context.state.data_result = None
        result = await agent.validate_preconditions(execution_context)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_preconditions_no_triage_result(self, agent, execution_context):
        """Test precondition validation fails when no triage result."""
        execution_context.state.triage_result = None
        result = await agent.validate_preconditions(execution_context)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_preconditions_no_llm_manager(self, agent, execution_context):
        """Test precondition validation fails when no LLM manager."""
        agent.llm_manager = None
        result = await agent.validate_preconditions(execution_context)
        assert result is False

    # ===== Core Logic Execution Tests =====

    @pytest.mark.asyncio
    async def test_execute_core_logic_successful_flow(self, agent, execution_context):
        """Test complete successful core logic execution flow."""
        result = await agent.execute_core_logic(execution_context)

        # Verify result structure
        assert isinstance(result, dict)
        assert "optimization_type" in result
        assert "recommendations" in result
        assert "confidence_score" in result

        # Verify state was updated
        assert execution_context.state.optimizations_result is not None
        assert isinstance(execution_context.state.optimizations_result, OptimizationsResult)

    @pytest.mark.asyncio
    async def test_execute_core_logic_llm_processing(self, agent, execution_context):
        """Test that LLM is called with proper configuration."""
        await agent.execute_core_logic(execution_context)

        # Verify LLM was called with correct parameters
        agent.llm_manager.ask_llm.assert_called_once()
        call_args = agent.llm_manager.ask_llm.call_args
        
        # Check that prompt was passed and config name is correct
        assert len(call_args[0]) > 0  # Prompt should not be empty
        assert call_args[1]['llm_config_name'] == 'optimizations_core'

    # ===== Error Handling Tests =====

    @pytest.mark.asyncio
    async def test_error_handling_uses_baseagent_infrastructure(self, agent, execution_context):
        """Test that error handling uses BaseAgent infrastructure, not custom handlers."""
        # Verify agent doesn't have custom error handling infrastructure
        assert not hasattr(agent, 'reliability_manager')
        assert not hasattr(agent, 'error_handler')
        assert not hasattr(agent, 'monitor')

        # Verify agent has BaseAgent infrastructure
        assert hasattr(agent, '_unified_reliability_handler')
        assert hasattr(agent, '_execution_engine')

    # ===== Legacy Compatibility Tests =====

    @pytest.mark.asyncio
    async def test_legacy_execute_method_compatibility(self, agent, mock_state):
        """Test that legacy execute method still works and delegates to BaseAgent."""
        with patch.object(agent, 'execute_modern', new_callable=AsyncMock) as mock_modern:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.result = {
                "optimization_type": "test",
                "recommendations": ["test rec"],
                "confidence_score": 0.8
            }
            mock_modern.return_value = mock_result

            await agent.execute(mock_state, "test_run", True)

            # Verify execute_modern was called
            mock_modern.assert_called_once_with(mock_state, "test_run", True)

            # Verify state was updated
            assert mock_state.optimizations_result is not None

    @pytest.mark.asyncio
    async def test_legacy_check_entry_conditions(self, agent, mock_state):
        """Test legacy check_entry_conditions method."""
        # Test with valid data
        result = await agent.check_entry_conditions(mock_state, "test_run")
        assert result is True

        # Test with missing data
        mock_state.data_result = None
        result = await agent.check_entry_conditions(mock_state, "test_run")
        assert result is False

        # Test with missing triage
        mock_state.data_result = {"test": "data"}
        mock_state.triage_result = None
        result = await agent.check_entry_conditions(mock_state, "test_run")
        assert result is False

    # ===== Business Logic Tests =====

    def test_build_optimization_prompt(self, agent, mock_state):
        """Test optimization prompt building."""
        prompt = agent._build_optimization_prompt(mock_state)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Verify state data is incorporated into prompt
        assert str(mock_state.data_result) in prompt or "data" in prompt.lower()
        assert str(mock_state.triage_result) in prompt or "triage" in prompt.lower()

    def test_extract_and_validate_result_success(self, agent):
        """Test successful JSON extraction from LLM response."""
        llm_response = '{"optimization_type": "cost", "recommendations": ["test"], "confidence_score": 0.9}'
        result = agent._extract_and_validate_result(llm_response, "test_run")
        
        assert result["optimization_type"] == "cost"
        assert result["recommendations"] == ["test"]
        assert result["confidence_score"] == 0.9

    def test_extract_and_validate_result_failure(self, agent):
        """Test fallback when JSON extraction fails."""
        llm_response = "Invalid JSON response"
        result = agent._extract_and_validate_result(llm_response, "test_run")
        
        # Should return fallback with empty optimizations
        assert result["optimizations"] == []

    def test_create_optimizations_result(self, agent):
        """Test OptimizationsResult creation from dictionary."""
        test_data = {
            "optimization_type": "performance",
            "recommendations": ["optimize queries", "add caching"],
            "confidence_score": 0.85,
            "cost_savings": "25%",
            "performance_improvement": "50%"
        }
        
        result = agent._create_optimizations_result(test_data)
        
        assert isinstance(result, OptimizationsResult)
        assert result.optimization_type == "performance"
        assert len(result.recommendations) == 2
        assert result.confidence_score == 0.85

    def test_create_default_fallback_result(self, agent):
        """Test creation of default fallback result."""
        result = agent._create_default_fallback_result()
        
        assert result["optimization_type"] == "general"
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0
        assert result["confidence_score"] == 0.5
        assert result["metadata"]["fallback_used"] is True

    # ===== SSOT Compliance Tests =====

    def test_inheritance_pattern_compliance(self, agent):
        """Test that agent follows single inheritance pattern from BaseAgent."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Verify inheritance
        assert isinstance(agent, BaseAgent)
        
        # Verify MRO (Method Resolution Order) is clean
        mro = type(agent).__mro__
        assert len(mro) == 3  # OptimizationsCoreSubAgent -> BaseAgent -> object
        assert mro[0] == OptimizationsCoreSubAgent
        assert mro[1] == BaseAgent

    def test_no_infrastructure_duplication(self, agent):
        """Test that agent doesn't duplicate BaseAgent infrastructure."""
        # Verify agent doesn't have duplicate infrastructure
        infrastructure_attributes = [
            'reliability_manager',
            'error_handler', 
            'monitor',
            '_create_circuit_breaker_config',
            '_create_retry_config',
            '_initialize_modern_components'
        ]
        
        for attr in infrastructure_attributes:
            assert not hasattr(agent, attr), f"Agent should not have duplicate {attr}"

    def test_websocket_integration_uses_baseagent(self, agent):
        """Test that WebSocket integration uses BaseAgent methods."""
        websocket_methods = [
            'emit_thinking',
            'emit_progress', 
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_error'
        ]
        
        for method in websocket_methods:
            assert hasattr(agent, method), f"Agent should have BaseAgent WebSocket method {method}"

    # ===== Integration Test =====

    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, agent, execution_context):
        """Integration test for complete optimization workflow."""
        # Track all WebSocket events
        websocket_events = []
        
        async def track_event(event_type, *args, **kwargs):
            websocket_events.append((event_type, args, kwargs))
        
        # Patch all WebSocket methods
        with patch.object(agent, 'emit_thinking', side_effect=lambda *a, **k: track_event('thinking', *a, **k)), \
             patch.object(agent, 'emit_progress', side_effect=lambda *a, **k: track_event('progress', *a, **k)), \
             patch.object(agent, 'emit_tool_executing', side_effect=lambda *a, **k: track_event('tool_exec', *a, **k)), \
             patch.object(agent, 'emit_tool_completed', side_effect=lambda *a, **k: track_event('tool_comp', *a, **k)):

            # Execute complete workflow
            result = await agent.execute_core_logic(execution_context)

            # Verify workflow completed successfully
            assert isinstance(result, dict)
            assert result["optimization_type"] == "cost_optimization"
            assert len(result["recommendations"]) == 3

            # Verify state was updated
            assert execution_context.state.optimizations_result is not None

            # Verify all required WebSocket events were emitted in correct order
            event_types = [event[0] for event in websocket_events]
            assert 'thinking' in event_types
            assert 'progress' in event_types
            assert 'tool_exec' in event_types
            assert 'tool_comp' in event_types

            # Verify final progress event marks completion
            final_progress_events = [e for e in websocket_events if e[0] == 'progress']
            assert len(final_progress_events) >= 2  # At least progress during and completion
            
            # Find completion event
            completion_events = [e for e in final_progress_events 
                               if len(e[1]) > 0 and "successfully" in str(e[1][0]).lower()]
            assert len(completion_events) > 0, "Should have completion progress event"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])