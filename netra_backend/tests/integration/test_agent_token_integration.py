"""Integration tests for BaseAgent token tracking and context metadata integration."""

import pytest
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_defaults import LLMModel


class TestAgentTokenIntegration:
    """Test integration of token tracking with BaseAgent and UserExecutionContext."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = BaseAgent(name="TestTokenAgent")
        self.context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

    def test_track_llm_usage_basic(self):
        """Test basic LLM usage tracking through agent."""
        # Track usage
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            operation_type="execution"
        )
        
        # Verify metadata was updated
        assert "token_usage" in self.context.metadata
        token_usage = self.context.metadata["token_usage"]
        
        assert len(token_usage["operations"]) == 1
        assert token_usage["cumulative_cost"] > 0.0
        assert token_usage["cumulative_tokens"] == 150
        
        operation = token_usage["operations"][0]
        assert operation["agent"] == "TestTokenAgent"
        assert operation["operation_type"] == "execution"
        assert operation["input_tokens"] == 100
        assert operation["output_tokens"] == 50

    def test_track_llm_usage_cumulative(self):
        """Test cumulative tracking across multiple operations."""
        # First operation
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            operation_type="thinking"
        )
        
        # Second operation
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=200,
            output_tokens=100,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            operation_type="execution"
        )
        
        # Verify cumulative tracking
        token_usage = self.context.metadata["token_usage"]
        assert len(token_usage["operations"]) == 2
        assert token_usage["cumulative_tokens"] == 450  # (100+50) + (200+100)
        assert token_usage["cumulative_cost"] > 0.0

    def test_optimize_prompt_for_context(self):
        """Test prompt optimization with context metadata storage."""
        original_prompt = "Please kindly help me with this task in order to complete it properly"
        
        optimized_prompt = self.agent.optimize_prompt_for_context(
            context=self.context,
            prompt=original_prompt,
            target_reduction=20
        )
        
        # Verify optimization occurred
        assert optimized_prompt != original_prompt
        assert len(optimized_prompt) < len(original_prompt)
        
        # Verify metadata was stored
        assert "prompt_optimizations" in self.context.metadata
        optimizations = self.context.metadata["prompt_optimizations"]
        
        assert len(optimizations) == 1
        optimization = optimizations[0]
        assert optimization["agent"] == "TestTokenAgent"
        assert optimization["tokens_saved"] > 0
        assert optimization["reduction_percent"] > 0
        assert optimization["cost_savings"] >= 0

    def test_get_cost_optimization_suggestions(self):
        """Test getting cost optimization suggestions."""
        # First add some usage to generate suggestions
        for i in range(5):
            self.agent.track_llm_usage(
                context=self.context,
                input_tokens=500,  # High usage to trigger suggestions
                output_tokens=250,
                model=LLMModel.GEMINI_2_5_FLASH.value
            )
        
        suggestions = self.agent.get_cost_optimization_suggestions(self.context)
        
        # Verify suggestions were returned and stored
        assert isinstance(suggestions, list)
        assert "cost_optimization_suggestions" in self.context.metadata
        assert self.context.metadata["cost_optimization_suggestions"] == suggestions

    def test_get_token_usage_summary(self):
        """Test getting token usage summary."""
        # Add some usage
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        summary = self.agent.get_token_usage_summary(self.context)
        
        # Verify summary includes both global and current session data
        assert "agents_tracked" in summary
        assert "current_session" in summary
        assert summary["current_session"]["operations_count"] == 1
        assert summary["current_session"]["cumulative_tokens"] == 150

    @pytest.mark.asyncio
    async def test_emit_thinking_with_token_context(self):
        """Test that emit_thinking includes token information when context provided."""
        # Mock the WebSocket adapter
        self.agent._websocket_adapter.emit_thinking = AsyncNone  # TODO: Use real service instance
        
        # Add token usage to context
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Emit thinking with context
        await self.agent.emit_thinking(
            thought="I'm processing the request",
            context=self.context
        )
        
        # Verify the enhanced message was sent
        self.agent._websocket_adapter.emit_thinking.assert_called_once()
        call_args = self.agent._websocket_adapter.emit_thinking.call_args
        enhanced_thought = call_args[0][0]
        
        # Should include token information
        assert "Tokens:" in enhanced_thought
        assert "Cost:" in enhanced_thought
        assert "I'm processing the request" in enhanced_thought

    @pytest.mark.asyncio
    async def test_emit_thinking_without_context(self):
        """Test that emit_thinking works normally without context."""
        # Mock the WebSocket adapter
        self.agent._websocket_adapter.emit_thinking = AsyncNone  # TODO: Use real service instance
        
        # Emit thinking without context
        await self.agent.emit_thinking("I'm processing the request")
        
        # Verify the original message was sent unchanged
        self.agent._websocket_adapter.emit_thinking.assert_called_once_with(
            "I'm processing the request", None
        )

    @pytest.mark.asyncio
    async def test_emit_agent_completed_with_cost_analysis(self):
        """Test that emit_agent_completed includes cost analysis."""
        # Mock the WebSocket adapter
        self.agent._websocket_adapter.emit_agent_completed = AsyncNone  # TODO: Use real service instance
        
        # Add token usage and optimizations to context
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        self.agent.optimize_prompt_for_context(
            context=self.context,
            prompt="Please help me with this task"
        )
        
        # Get suggestions to populate metadata
        self.agent.get_cost_optimization_suggestions(self.context)
        
        # Emit completion with context
        await self.agent.emit_agent_completed(
            result={"status": "completed"},
            context=self.context
        )
        
        # Verify enhanced result was sent
        self.agent._websocket_adapter.emit_agent_completed.assert_called_once()
        call_args = self.agent._websocket_adapter.emit_agent_completed.call_args
        enhanced_result = call_args[0][0]
        
        # Should include cost analysis
        assert "cost_analysis" in enhanced_result
        assert enhanced_result["cost_analysis"]["total_operations"] == 1
        assert enhanced_result["cost_analysis"]["cumulative_cost"] > 0.0
        
        # Should include optimization summary
        assert "optimization_summary" in enhanced_result
        assert enhanced_result["optimization_summary"]["optimizations_applied"] == 1

    @pytest.mark.asyncio
    async def test_emit_agent_completed_without_context(self):
        """Test that emit_agent_completed works normally without context."""
        # Mock the WebSocket adapter
        self.agent._websocket_adapter.emit_agent_completed = AsyncNone  # TODO: Use real service instance
        
        original_result = {"status": "completed"}
        
        # Emit completion without context
        await self.agent.emit_agent_completed(result=original_result)
        
        # Verify the original result was sent
        self.agent._websocket_adapter.emit_agent_completed.assert_called_once_with(
            original_result
        )


class TestMultipleAgentTokenTracking:
    """Test token tracking across multiple agents."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent1 = BaseAgent(name="Agent1")
        self.agent2 = BaseAgent(name="Agent2")
        self.context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

    def test_multiple_agents_separate_tracking(self):
        """Test that different agents track separately but share context metadata."""
        # Agent1 usage
        self.agent1.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Agent2 usage
        self.agent2.track_llm_usage(
            context=self.context,
            input_tokens=200,
            output_tokens=100,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Verify context has operations from both agents
        token_usage = self.context.metadata["token_usage"]
        assert len(token_usage["operations"]) == 2
        
        agents_in_ops = [op["agent"] for op in token_usage["operations"]]
        assert "Agent1" in agents_in_ops
        assert "Agent2" in agents_in_ops
        
        # Total tokens should be combined
        assert token_usage["cumulative_tokens"] == 450  # (100+50) + (200+100)

    def test_agent_specific_summaries(self):
        """Test that each agent maintains its own usage statistics."""
        # Add usage to both agents
        self.agent1.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        self.agent2.track_llm_usage(
            context=self.context,
            input_tokens=200,
            output_tokens=100,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Get summaries from each agent
        summary1 = self.agent1.get_token_usage_summary(self.context)
        summary2 = self.agent2.get_token_usage_summary(self.context)
        
        # Both should see the same global data
        assert summary1["agents_tracked"] == summary2["agents_tracked"]
        assert summary1["current_session"] == summary2["current_session"]
        
        # But each should have their own agent in the global tracking
        assert "Agent1" in summary1["agents"]
        assert "Agent2" in summary2["agents"]


class TestTokenTrackingEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = BaseAgent(name="EdgeCaseAgent")
        self.context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

    def test_track_usage_with_zero_tokens(self):
        """Test tracking with zero tokens."""
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=0,
            output_tokens=0,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        token_usage = self.context.metadata["token_usage"]
        assert len(token_usage["operations"]) == 1
        assert token_usage["cumulative_tokens"] == 0
        assert token_usage["cumulative_cost"] == 0.0

    def test_optimize_empty_prompt(self):
        """Test optimizing an empty prompt."""
        optimized = self.agent.optimize_prompt_for_context(
            context=self.context,
            prompt=""
        )
        
        assert optimized == ""
        assert "prompt_optimizations" in self.context.metadata
        
        optimization = self.context.metadata["prompt_optimizations"][0]
        assert optimization["tokens_saved"] == 0
        assert optimization["reduction_percent"] == 0.0

    def test_suggestions_without_usage_data(self):
        """Test getting suggestions without any usage data."""
        suggestions = self.agent.get_cost_optimization_suggestions(self.context)
        
        # Should return "no data" suggestion
        assert len(suggestions) >= 1
        assert any(s["type"] == "no_data" for s in suggestions)

    @pytest.mark.asyncio
    async def test_emit_thinking_with_empty_token_operations(self):
        """Test emit_thinking when token_usage exists but has no operations."""
        # Mock the WebSocket adapter
        self.agent._websocket_adapter.emit_thinking = AsyncNone  # TODO: Use real service instance
        
        # Set up context with empty token usage
        self.context.metadata["token_usage"] = {
            "operations": [],
            "cumulative_cost": 0.0,
            "cumulative_tokens": 0
        }
        
        await self.agent.emit_thinking(
            thought="Processing request",
            context=self.context
        )
        
        # Should emit original thought without enhancement
        self.agent._websocket_adapter.emit_thinking.assert_called_once_with(
            "Processing request", None
        )

    def test_disabled_token_counter(self):
        """Test behavior when token counter is disabled."""
        self.agent.token_counter.disable()
        
        # Tracking should report as disabled
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Context metadata should not be updated
        assert "token_usage" not in self.context.metadata

    def test_context_metadata_preservation(self):
        """Test that existing metadata is preserved when adding token data."""
        # Add some existing metadata
        self.context.metadata["existing_key"] = "existing_value"
        
        # Add token usage
        self.agent.track_llm_usage(
            context=self.context,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Existing metadata should be preserved
        assert self.context.metadata["existing_key"] == "existing_value"
        assert "token_usage" in self.context.metadata


class TestTokenTrackingPerformance:
    """Test performance aspects of token tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = BaseAgent(name="PerformanceAgent")
        self.context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

    def test_many_operations_performance(self):
        """Test performance with many tracking operations."""
        import time
        
        start_time = time.time()
        
        # Perform many tracking operations
        for i in range(100):
            self.agent.track_llm_usage(
                context=self.context,
                input_tokens=50 + i,
                output_tokens=25 + i,
                model=LLMModel.GEMINI_2_5_FLASH.value,
                operation_type=f"operation_{i % 5}"  # 5 different operation types
            )
        
        end_time = time.time()
        
        # Should complete quickly (under 1 second for 100 operations)
        assert (end_time - start_time) < 1.0
        
        # Verify all operations were tracked
        token_usage = self.context.metadata["token_usage"]
        assert len(token_usage["operations"]) == 100
        
        # Verify cumulative calculations are correct
        expected_total = sum(75 + 2*i for i in range(100))  # (50+25) + 2*i for each operation
        assert token_usage["cumulative_tokens"] == expected_total

    def test_large_prompt_optimization(self):
        """Test optimization of very large prompts."""
        # Create a large prompt with lots of redundancy
        large_prompt = "Please kindly help me " * 100 + "with this task " * 50
        
        start_time = time.time()
        
        optimized = self.agent.optimize_prompt_for_context(
            context=self.context,
            prompt=large_prompt
        )
        
        end_time = time.time()
        
        # Should optimize quickly even for large prompts
        assert (end_time - start_time) < 0.5
        
        # Should achieve significant reduction
        assert len(optimized) < len(large_prompt)
        
        optimization = self.context.metadata["prompt_optimizations"][0]
        assert optimization["tokens_saved"] > 0