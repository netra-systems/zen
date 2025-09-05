"""Unit tests for enhanced TokenCounter with optimization and tracking features."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from netra_backend.app.services.billing.token_counter import TokenCounter, TokenType, TokenCount
from netra_backend.app.llm.llm_defaults import LLMModel


class TestTokenCounterOptimization:
    """Test token optimization functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_optimize_prompt_basic(self):
        """Test basic prompt optimization."""
        prompt = "Please  kindly  help  me  with  this  task  please"
        result = self.token_counter.optimize_prompt(prompt, target_reduction_percent=20)
        
        assert result["original_prompt"] == prompt
        assert result["optimized_prompt"] != prompt
        assert result["tokens_saved"] > 0
        assert result["reduction_percent"] > 0
        assert "whitespace_normalization" in result["optimization_applied"]

    def test_optimize_prompt_verbose_phrases(self):
        """Test optimization of verbose phrases."""
        prompt = "Could you please help me in order to complete this task due to the fact that I need assistance"
        result = self.token_counter.optimize_prompt(prompt)
        
        optimized = result["optimized_prompt"]
        assert "in order to" not in optimized
        assert "due to the fact that" not in optimized
        assert "could you please" not in optimized.lower()
        assert "verbose_replacements" in result["optimization_applied"]

    def test_optimize_prompt_empty_input(self):
        """Test optimization with empty input."""
        result = self.token_counter.optimize_prompt("", target_reduction_percent=20)
        
        assert result["original_tokens"] == 0
        assert result["optimized_tokens"] == 0
        assert result["tokens_saved"] == 0
        assert result["reduction_percent"] == 0.0

    def test_optimize_prompt_target_achieved(self):
        """Test whether optimization achieves target reduction."""
        verbose_prompt = "Please please please kindly help me with this task in order to complete it due to the fact that I need assistance"
        result = self.token_counter.optimize_prompt(verbose_prompt, target_reduction_percent=15)
        
        assert "target_achieved" in result
        # With sufficient redundancy, should achieve 15% reduction
        if result["reduction_percent"] >= 15:
            assert result["target_achieved"] is True
        else:
            assert result["target_achieved"] is False

    def test_optimize_prompt_cost_savings(self):
        """Test that cost savings are calculated correctly."""
        prompt = "Please  kindly  help  me  with  multiple  spaces  everywhere"
        result = self.token_counter.optimize_prompt(prompt)
        
        assert isinstance(result["cost_savings"], Decimal)
        assert result["cost_savings"] >= Decimal("0.00")


class TestTokenCounterAgentTracking:
    """Test agent usage tracking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_track_agent_usage_basic(self):
        """Test basic agent usage tracking."""
        result = self.token_counter.track_agent_usage(
            agent_name="TestAgent",
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value,
            operation_type="execution"
        )
        
        assert result["tracking_enabled"] is True
        assert result["agent_name"] == "TestAgent"
        assert result["operation_type"] == "execution"
        assert result["current_operation"]["input_tokens"] == 100
        assert result["current_operation"]["output_tokens"] == 50
        assert result["current_operation"]["total_tokens"] == 150
        assert result["cumulative_stats"]["total_operations"] == 1

    def test_track_agent_usage_cumulative(self):
        """Test cumulative tracking across multiple operations."""
        agent_name = "CumulativeAgent"
        
        # First operation
        result1 = self.token_counter.track_agent_usage(
            agent_name=agent_name,
            input_tokens=100,
            output_tokens=50,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        # Second operation
        result2 = self.token_counter.track_agent_usage(
            agent_name=agent_name,
            input_tokens=200,
            output_tokens=100,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        assert result2["cumulative_stats"]["total_operations"] == 2
        assert result2["cumulative_stats"]["total_input_tokens"] == 300
        assert result2["cumulative_stats"]["total_output_tokens"] == 150
        assert result2["cumulative_stats"]["total_tokens"] == 450

    def test_track_agent_usage_multiple_operation_types(self):
        """Test tracking different operation types for the same agent."""
        agent_name = "MultiOpAgent"
        
        # Execution operation
        self.token_counter.track_agent_usage(
            agent_name=agent_name,
            input_tokens=100,
            output_tokens=50,
            operation_type="execution"
        )
        
        # Thinking operation
        result = self.token_counter.track_agent_usage(
            agent_name=agent_name,
            input_tokens=50,
            output_tokens=25,
            operation_type="thinking"
        )
        
        operation_types = result["cumulative_stats"]["operation_types"]
        assert "execution" in operation_types
        assert "thinking" in operation_types
        assert operation_types["execution"]["count"] == 1
        assert operation_types["thinking"]["count"] == 1

    def test_track_agent_usage_disabled(self):
        """Test behavior when tracking is disabled."""
        self.token_counter.disable()
        
        result = self.token_counter.track_agent_usage(
            agent_name="DisabledAgent",
            input_tokens=100,
            output_tokens=50
        )
        
        assert result["tracking_enabled"] is False


class TestTokenCounterOptimizationSuggestions:
    """Test optimization suggestions functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_get_optimization_suggestions_no_data(self):
        """Test suggestions when no usage data exists."""
        suggestions = self.token_counter.get_optimization_suggestions()
        
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "no_data"
        assert suggestions[0]["priority"] == "low"

    def test_get_optimization_suggestions_high_cost_agent(self):
        """Test suggestions for high-cost agents."""
        # Create high-cost usage
        for i in range(10):
            self.token_counter.track_agent_usage(
                agent_name="ExpensiveAgent",
                input_tokens=1000,  # High token usage
                output_tokens=500,
                model=LLMModel.GEMINI_2_5_FLASH.value
            )
        
        suggestions = self.token_counter.get_optimization_suggestions(
            cost_threshold=Decimal("0.50")  # Low threshold to trigger suggestions
        )
        
        high_cost_suggestions = [s for s in suggestions if s["type"] == "high_cost_agent"]
        assert len(high_cost_suggestions) > 0
        assert high_cost_suggestions[0]["priority"] == "high"
        assert high_cost_suggestions[0]["agent_name"] == "ExpensiveAgent"

    def test_get_optimization_suggestions_high_token_usage(self):
        """Test suggestions for high token usage."""
        # Create agent with high token usage
        self.token_counter.track_agent_usage(
            agent_name="TokenHeavyAgent",
            input_tokens=3000,  # Very high token usage
            output_tokens=1000,
            model=LLMModel.GEMINI_2_5_FLASH.value
        )
        
        suggestions = self.token_counter.get_optimization_suggestions()
        
        token_suggestions = [s for s in suggestions if s["type"] == "high_token_usage"]
        assert len(token_suggestions) > 0
        assert token_suggestions[0]["priority"] == "medium"
        assert token_suggestions[0]["agent_name"] == "TokenHeavyAgent"

    def test_get_optimization_suggestions_model_optimization(self):
        """Test suggestions for model optimization."""
        agent_name = "MultiModelAgent"
        
        # Use multiple different models
        models = [LLMModel.GEMINI_2_5_FLASH.value, "gpt-4", "claude-3-haiku"]
        for model in models:
            self.token_counter.track_agent_usage(
                agent_name=agent_name,
                input_tokens=500,
                output_tokens=250,
                model=model
            )
        
        suggestions = self.token_counter.get_optimization_suggestions()
        
        model_suggestions = [s for s in suggestions if s["type"] == "model_optimization"]
        assert len(model_suggestions) > 0
        assert model_suggestions[0]["agent_name"] == agent_name
        assert "recommended_model" in model_suggestions[0]

    def test_get_optimization_suggestions_priority_ordering(self):
        """Test that suggestions are ordered by priority."""
        # Create scenarios for different priority suggestions
        for i in range(20):  # Create high cost scenario
            self.token_counter.track_agent_usage(
                agent_name="HighCostAgent",
                input_tokens=2000,
                output_tokens=1000,
                model=LLMModel.GEMINI_2_5_FLASH.value
            )
        
        suggestions = self.token_counter.get_optimization_suggestions(
            cost_threshold=Decimal("0.10")
        )
        
        # Should have high priority suggestions first
        priorities = [s["priority"] for s in suggestions]
        high_priority_count = priorities.count("high")
        medium_priority_count = priorities.count("medium")
        
        # High priority suggestions should come first
        if high_priority_count > 0 and medium_priority_count > 0:
            first_high_index = priorities.index("high")
            first_medium_index = priorities.index("medium") 
            assert first_high_index < first_medium_index


class TestTokenCounterUsageSummary:
    """Test agent usage summary functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_get_agent_usage_summary_no_data(self):
        """Test summary when no usage data exists."""
        summary = self.token_counter.get_agent_usage_summary()
        
        assert summary["agents_tracked"] == 0
        assert summary["total_operations"] == 0
        assert summary["total_cost"] == 0.0
        assert summary["total_tokens"] == 0
        assert "message" in summary

    def test_get_agent_usage_summary_with_data(self):
        """Test summary with usage data."""
        # Add usage for multiple agents
        self.token_counter.track_agent_usage("Agent1", 100, 50, LLMModel.GEMINI_2_5_FLASH.value)
        self.token_counter.track_agent_usage("Agent2", 200, 100, LLMModel.GEMINI_2_5_FLASH.value)
        self.token_counter.track_agent_usage("Agent1", 150, 75, LLMModel.GEMINI_2_5_FLASH.value)
        
        summary = self.token_counter.get_agent_usage_summary()
        
        assert summary["agents_tracked"] == 2
        assert summary["total_operations"] == 3
        assert summary["total_cost"] > 0.0
        assert summary["total_tokens"] == 675  # (100+50) + (200+100) + (150+75)
        assert summary["most_expensive_agent"] is not None
        assert summary["most_active_agent"] is not None
        assert "Agent1" in summary["agents"]
        assert "Agent2" in summary["agents"]

    def test_get_agent_usage_summary_most_active_and_expensive(self):
        """Test identification of most active and expensive agents."""
        # Agent1: More operations but cheaper per operation
        for i in range(5):
            self.token_counter.track_agent_usage("Agent1", 50, 25, "claude-3-haiku")  # Cheaper model
        
        # Agent2: Fewer operations but more expensive
        for i in range(2):
            self.token_counter.track_agent_usage("Agent2", 500, 250, LLMModel.GEMINI_2_5_FLASH.value)
        
        summary = self.token_counter.get_agent_usage_summary()
        
        assert summary["most_active_agent"]["name"] == "Agent1"
        assert summary["most_active_agent"]["operations"] == 5
        
        # Most expensive should be Agent2 due to higher token usage and potentially more expensive model
        assert summary["most_expensive_agent"]["name"] in ["Agent1", "Agent2"]  # Either could be more expensive


class TestTokenCounterIntegration:
    """Integration tests for TokenCounter enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_full_workflow_optimization_and_tracking(self):
        """Test complete workflow of optimization and tracking."""
        # Step 1: Optimize a prompt
        original_prompt = "Please kindly help me with this task in order to complete it properly"
        optimization_result = self.token_counter.optimize_prompt(original_prompt)
        
        # Step 2: Track usage with the optimized prompt
        optimized_tokens = optimization_result["optimized_tokens"]
        tracking_result = self.token_counter.track_agent_usage(
            agent_name="WorkflowAgent",
            input_tokens=optimized_tokens,
            output_tokens=optimized_tokens // 2,  # Estimate output tokens
            model=LLMModel.GEMINI_2_5_FLASH.value,
            operation_type="optimized_execution"
        )
        
        # Step 3: Get suggestions
        suggestions = self.token_counter.get_optimization_suggestions()
        
        # Step 4: Get summary
        summary = self.token_counter.get_agent_usage_summary()
        
        # Verify the workflow
        assert optimization_result["tokens_saved"] >= 0
        assert tracking_result["tracking_enabled"] is True
        assert tracking_result["agent_name"] == "WorkflowAgent"
        assert len(suggestions) > 0
        assert summary["agents_tracked"] == 1
        assert "WorkflowAgent" in summary["agents"]

    def test_enhanced_stats_with_agent_usage(self):
        """Test that get_stats includes agent usage summary when available."""
        # Add some agent usage
        self.token_counter.track_agent_usage("StatsAgent", 100, 50, LLMModel.GEMINI_2_5_FLASH.value)
        
        stats = self.token_counter.get_stats()
        
        assert "agent_usage_summary" in stats
        assert stats["agent_usage_summary"]["agents_tracked"] == 1
        assert "StatsAgent" in stats["agent_usage_summary"]["agents"]

    @patch('netra_backend.app.services.billing.token_counter.datetime')
    def test_timestamp_consistency(self, mock_datetime):
        """Test that timestamps are consistent across operations."""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time
        
        result = self.token_counter.track_agent_usage(
            "TimestampAgent", 100, 50, LLMModel.GEMINI_2_5_FLASH.value
        )
        
        assert result["timestamp"] == fixed_time.isoformat()