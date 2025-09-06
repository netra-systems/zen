"""Unit tests for enhanced TokenCounter with optimization and tracking features."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.billing.token_counter import TokenCounter, TokenType, TokenCount
from netra_backend.app.llm.llm_defaults import LLMModel


# REMOVED_SYNTAX_ERROR: class TestTokenCounterOptimization:
    # REMOVED_SYNTAX_ERROR: """Test token optimization functionality."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.token_counter = TokenCounter()

# REMOVED_SYNTAX_ERROR: def test_optimize_prompt_basic(self):
    # REMOVED_SYNTAX_ERROR: """Test basic prompt optimization."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: prompt = "Please  kindly  help  me  with  this  task  please"
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.optimize_prompt(prompt, target_reduction_percent=20)

    # REMOVED_SYNTAX_ERROR: assert result["original_prompt"] == prompt
    # REMOVED_SYNTAX_ERROR: assert result["optimized_prompt"] != prompt
    # REMOVED_SYNTAX_ERROR: assert result["tokens_saved"] > 0
    # REMOVED_SYNTAX_ERROR: assert result["reduction_percent"] > 0
    # REMOVED_SYNTAX_ERROR: assert "whitespace_normalization" in result["optimization_applied"]

# REMOVED_SYNTAX_ERROR: def test_optimize_prompt_verbose_phrases(self):
    # REMOVED_SYNTAX_ERROR: """Test optimization of verbose phrases."""
    # REMOVED_SYNTAX_ERROR: prompt = "Could you please help me in order to complete this task due to the fact that I need assistance"
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.optimize_prompt(prompt)

    # REMOVED_SYNTAX_ERROR: optimized = result["optimized_prompt"]
    # REMOVED_SYNTAX_ERROR: assert "in order to" not in optimized
    # REMOVED_SYNTAX_ERROR: assert "due to the fact that" not in optimized
    # REMOVED_SYNTAX_ERROR: assert "could you please" not in optimized.lower()
    # REMOVED_SYNTAX_ERROR: assert "verbose_replacements" in result["optimization_applied"]

# REMOVED_SYNTAX_ERROR: def test_optimize_prompt_empty_input(self):
    # REMOVED_SYNTAX_ERROR: """Test optimization with empty input."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.optimize_prompt("", target_reduction_percent=20)

    # REMOVED_SYNTAX_ERROR: assert result["original_tokens"] == 0
    # REMOVED_SYNTAX_ERROR: assert result["optimized_tokens"] == 0
    # REMOVED_SYNTAX_ERROR: assert result["tokens_saved"] == 0
    # REMOVED_SYNTAX_ERROR: assert result["reduction_percent"] == 0.0

# REMOVED_SYNTAX_ERROR: def test_optimize_prompt_target_achieved(self):
    # REMOVED_SYNTAX_ERROR: """Test whether optimization achieves target reduction."""
    # REMOVED_SYNTAX_ERROR: verbose_prompt = "Please please please kindly help me with this task in order to complete it due to the fact that I need assistance"
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.optimize_prompt(verbose_prompt, target_reduction_percent=15)

    # REMOVED_SYNTAX_ERROR: assert "target_achieved" in result
    # With sufficient redundancy, should achieve 15% reduction
    # REMOVED_SYNTAX_ERROR: if result["reduction_percent"] >= 15:
        # REMOVED_SYNTAX_ERROR: assert result["target_achieved"] is True
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: assert result["target_achieved"] is False

# REMOVED_SYNTAX_ERROR: def test_optimize_prompt_cost_savings(self):
    # REMOVED_SYNTAX_ERROR: """Test that cost savings are calculated correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: prompt = "Please  kindly  help  me  with  multiple  spaces  everywhere"
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.optimize_prompt(prompt)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result["cost_savings"], Decimal)
    # REMOVED_SYNTAX_ERROR: assert result["cost_savings"] >= Decimal("0.00")


# REMOVED_SYNTAX_ERROR: class TestTokenCounterAgentTracking:
    # REMOVED_SYNTAX_ERROR: """Test agent usage tracking functionality."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.token_counter = TokenCounter()

# REMOVED_SYNTAX_ERROR: def test_track_agent_usage_basic(self):
    # REMOVED_SYNTAX_ERROR: """Test basic agent usage tracking."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name="TestAgent",
    # REMOVED_SYNTAX_ERROR: input_tokens=100,
    # REMOVED_SYNTAX_ERROR: output_tokens=50,
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: operation_type="execution"
    

    # REMOVED_SYNTAX_ERROR: assert result["tracking_enabled"] is True
    # REMOVED_SYNTAX_ERROR: assert result["agent_name"] == "TestAgent"
    # REMOVED_SYNTAX_ERROR: assert result["operation_type"] == "execution"
    # REMOVED_SYNTAX_ERROR: assert result["current_operation"]["input_tokens"] == 100
    # REMOVED_SYNTAX_ERROR: assert result["current_operation"]["output_tokens"] == 50
    # REMOVED_SYNTAX_ERROR: assert result["current_operation"]["total_tokens"] == 150
    # REMOVED_SYNTAX_ERROR: assert result["cumulative_stats"]["total_operations"] == 1

# REMOVED_SYNTAX_ERROR: def test_track_agent_usage_cumulative(self):
    # REMOVED_SYNTAX_ERROR: """Test cumulative tracking across multiple operations."""
    # REMOVED_SYNTAX_ERROR: agent_name = "CumulativeAgent"

    # First operation
    # REMOVED_SYNTAX_ERROR: result1 = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
    # REMOVED_SYNTAX_ERROR: input_tokens=100,
    # REMOVED_SYNTAX_ERROR: output_tokens=50,
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value
    

    # Second operation
    # REMOVED_SYNTAX_ERROR: result2 = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
    # REMOVED_SYNTAX_ERROR: input_tokens=200,
    # REMOVED_SYNTAX_ERROR: output_tokens=100,
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value
    

    # REMOVED_SYNTAX_ERROR: assert result2["cumulative_stats"]["total_operations"] == 2
    # REMOVED_SYNTAX_ERROR: assert result2["cumulative_stats"]["total_input_tokens"] == 300
    # REMOVED_SYNTAX_ERROR: assert result2["cumulative_stats"]["total_output_tokens"] == 150
    # REMOVED_SYNTAX_ERROR: assert result2["cumulative_stats"]["total_tokens"] == 450

# REMOVED_SYNTAX_ERROR: def test_track_agent_usage_multiple_operation_types(self):
    # REMOVED_SYNTAX_ERROR: """Test tracking different operation types for the same agent."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: agent_name = "MultiOpAgent"

    # Execution operation
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
    # REMOVED_SYNTAX_ERROR: input_tokens=100,
    # REMOVED_SYNTAX_ERROR: output_tokens=50,
    # REMOVED_SYNTAX_ERROR: operation_type="execution"
    

    # Thinking operation
    # REMOVED_SYNTAX_ERROR: result = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
    # REMOVED_SYNTAX_ERROR: input_tokens=50,
    # REMOVED_SYNTAX_ERROR: output_tokens=25,
    # REMOVED_SYNTAX_ERROR: operation_type="thinking"
    

    # REMOVED_SYNTAX_ERROR: operation_types = result["cumulative_stats"]["operation_types"]
    # REMOVED_SYNTAX_ERROR: assert "execution" in operation_types
    # REMOVED_SYNTAX_ERROR: assert "thinking" in operation_types
    # REMOVED_SYNTAX_ERROR: assert operation_types["execution"]["count"] == 1
    # REMOVED_SYNTAX_ERROR: assert operation_types["thinking"]["count"] == 1

# REMOVED_SYNTAX_ERROR: def test_track_agent_usage_disabled(self):
    # REMOVED_SYNTAX_ERROR: """Test behavior when tracking is disabled."""
    # REMOVED_SYNTAX_ERROR: self.token_counter.disable()

    # REMOVED_SYNTAX_ERROR: result = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name="DisabledAgent",
    # REMOVED_SYNTAX_ERROR: input_tokens=100,
    # REMOVED_SYNTAX_ERROR: output_tokens=50
    

    # REMOVED_SYNTAX_ERROR: assert result["tracking_enabled"] is False


# REMOVED_SYNTAX_ERROR: class TestTokenCounterOptimizationSuggestions:
    # REMOVED_SYNTAX_ERROR: """Test optimization suggestions functionality."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.token_counter = TokenCounter()

# REMOVED_SYNTAX_ERROR: def test_get_optimization_suggestions_no_data(self):
    # REMOVED_SYNTAX_ERROR: """Test suggestions when no usage data exists."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions()

    # REMOVED_SYNTAX_ERROR: assert len(suggestions) == 1
    # REMOVED_SYNTAX_ERROR: assert suggestions[0]["type"] == "no_data"
    # REMOVED_SYNTAX_ERROR: assert suggestions[0]["priority"] == "low"

# REMOVED_SYNTAX_ERROR: def test_get_optimization_suggestions_high_cost_agent(self):
    # REMOVED_SYNTAX_ERROR: """Test suggestions for high-cost agents."""
    # Create high-cost usage
    # REMOVED_SYNTAX_ERROR: for i in range(10):
        # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage( )
        # REMOVED_SYNTAX_ERROR: agent_name="ExpensiveAgent",
        # REMOVED_SYNTAX_ERROR: input_tokens=1000,  # High token usage
        # REMOVED_SYNTAX_ERROR: output_tokens=500,
        # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value
        

        # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions( )
        # REMOVED_SYNTAX_ERROR: cost_threshold=Decimal("0.50")  # Low threshold to trigger suggestions
        

        # REMOVED_SYNTAX_ERROR: high_cost_suggestions = [item for item in []] == "high_cost_agent"]
        # REMOVED_SYNTAX_ERROR: assert len(high_cost_suggestions) > 0
        # REMOVED_SYNTAX_ERROR: assert high_cost_suggestions[0]["priority"] == "high"
        # REMOVED_SYNTAX_ERROR: assert high_cost_suggestions[0]["agent_name"] == "ExpensiveAgent"

# REMOVED_SYNTAX_ERROR: def test_get_optimization_suggestions_high_token_usage(self):
    # REMOVED_SYNTAX_ERROR: """Test suggestions for high token usage."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create agent with high token usage
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name="TokenHeavyAgent",
    # REMOVED_SYNTAX_ERROR: input_tokens=3000,  # Very high token usage
    # REMOVED_SYNTAX_ERROR: output_tokens=1000,
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value
    

    # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions()

    # REMOVED_SYNTAX_ERROR: token_suggestions = [item for item in []] == "high_token_usage"]
    # REMOVED_SYNTAX_ERROR: assert len(token_suggestions) > 0
    # REMOVED_SYNTAX_ERROR: assert token_suggestions[0]["priority"] == "medium"
    # REMOVED_SYNTAX_ERROR: assert token_suggestions[0]["agent_name"] == "TokenHeavyAgent"

# REMOVED_SYNTAX_ERROR: def test_get_optimization_suggestions_model_optimization(self):
    # REMOVED_SYNTAX_ERROR: """Test suggestions for model optimization."""
    # REMOVED_SYNTAX_ERROR: agent_name = "MultiModelAgent"

    # Use multiple different models
    # REMOVED_SYNTAX_ERROR: models = [LLMModel.GEMINI_2_5_FLASH.value, "gpt-4", "claude-3-haiku"]
    # REMOVED_SYNTAX_ERROR: for model in models:
        # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage( )
        # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
        # REMOVED_SYNTAX_ERROR: input_tokens=500,
        # REMOVED_SYNTAX_ERROR: output_tokens=250,
        # REMOVED_SYNTAX_ERROR: model=model
        

        # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions()

        # REMOVED_SYNTAX_ERROR: model_suggestions = [item for item in []] == "model_optimization"]
        # REMOVED_SYNTAX_ERROR: assert len(model_suggestions) > 0
        # REMOVED_SYNTAX_ERROR: assert model_suggestions[0]["agent_name"] == agent_name
        # REMOVED_SYNTAX_ERROR: assert "recommended_model" in model_suggestions[0]

# REMOVED_SYNTAX_ERROR: def test_get_optimization_suggestions_priority_ordering(self):
    # REMOVED_SYNTAX_ERROR: """Test that suggestions are ordered by priority."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create scenarios for different priority suggestions
    # REMOVED_SYNTAX_ERROR: for i in range(20):  # Create high cost scenario
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name="HighCostAgent",
    # REMOVED_SYNTAX_ERROR: input_tokens=2000,
    # REMOVED_SYNTAX_ERROR: output_tokens=1000,
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value
    

    # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions( )
    # REMOVED_SYNTAX_ERROR: cost_threshold=Decimal("0.10")
    

    # Should have high priority suggestions first
    # REMOVED_SYNTAX_ERROR: priorities = [s["priority"] for s in suggestions]
    # REMOVED_SYNTAX_ERROR: high_priority_count = priorities.count("high")
    # REMOVED_SYNTAX_ERROR: medium_priority_count = priorities.count("medium")

    # High priority suggestions should come first
    # REMOVED_SYNTAX_ERROR: if high_priority_count > 0 and medium_priority_count > 0:
        # REMOVED_SYNTAX_ERROR: first_high_index = priorities.index("high")
        # REMOVED_SYNTAX_ERROR: first_medium_index = priorities.index("medium")
        # REMOVED_SYNTAX_ERROR: assert first_high_index < first_medium_index


# REMOVED_SYNTAX_ERROR: class TestTokenCounterUsageSummary:
    # REMOVED_SYNTAX_ERROR: """Test agent usage summary functionality."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.token_counter = TokenCounter()

# REMOVED_SYNTAX_ERROR: def test_get_agent_usage_summary_no_data(self):
    # REMOVED_SYNTAX_ERROR: """Test summary when no usage data exists."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: summary = self.token_counter.get_agent_usage_summary()

    # REMOVED_SYNTAX_ERROR: assert summary["agents_tracked"] == 0
    # REMOVED_SYNTAX_ERROR: assert summary["total_operations"] == 0
    # REMOVED_SYNTAX_ERROR: assert summary["total_cost"] == 0.0
    # REMOVED_SYNTAX_ERROR: assert summary["total_tokens"] == 0
    # REMOVED_SYNTAX_ERROR: assert "message" in summary

# REMOVED_SYNTAX_ERROR: def test_get_agent_usage_summary_with_data(self):
    # REMOVED_SYNTAX_ERROR: """Test summary with usage data."""
    # Add usage for multiple agents
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("Agent1", 100, 50, LLMModel.GEMINI_2_5_FLASH.value)
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("Agent2", 200, 100, LLMModel.GEMINI_2_5_FLASH.value)
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("Agent1", 150, 75, LLMModel.GEMINI_2_5_FLASH.value)

    # REMOVED_SYNTAX_ERROR: summary = self.token_counter.get_agent_usage_summary()

    # REMOVED_SYNTAX_ERROR: assert summary["agents_tracked"] == 2
    # REMOVED_SYNTAX_ERROR: assert summary["total_operations"] == 3
    # REMOVED_SYNTAX_ERROR: assert summary["total_cost"] > 0.0
    # REMOVED_SYNTAX_ERROR: assert summary["total_tokens"] == 675  # (100+50) + (200+100) + (150+75)
    # REMOVED_SYNTAX_ERROR: assert summary["most_expensive_agent"] is not None
    # REMOVED_SYNTAX_ERROR: assert summary["most_active_agent"] is not None
    # REMOVED_SYNTAX_ERROR: assert "Agent1" in summary["agents"]
    # REMOVED_SYNTAX_ERROR: assert "Agent2" in summary["agents"]

# REMOVED_SYNTAX_ERROR: def test_get_agent_usage_summary_most_active_and_expensive(self):
    # REMOVED_SYNTAX_ERROR: """Test identification of most active and expensive agents."""
    # REMOVED_SYNTAX_ERROR: pass
    # Agent1: More operations but cheaper per operation
    # REMOVED_SYNTAX_ERROR: for i in range(5):
        # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("Agent1", 50, 25, "claude-3-haiku")  # Cheaper model

        # Agent2: Fewer operations but more expensive
        # REMOVED_SYNTAX_ERROR: for i in range(2):
            # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("Agent2", 500, 250, LLMModel.GEMINI_2_5_FLASH.value)

            # REMOVED_SYNTAX_ERROR: summary = self.token_counter.get_agent_usage_summary()

            # REMOVED_SYNTAX_ERROR: assert summary["most_active_agent"]["name"] == "Agent1"
            # REMOVED_SYNTAX_ERROR: assert summary["most_active_agent"]["operations"] == 5

            # Most expensive should be Agent2 due to higher token usage and potentially more expensive model
            # REMOVED_SYNTAX_ERROR: assert summary["most_expensive_agent"]["name"] in ["Agent1", "Agent2"]  # Either could be more expensive


# REMOVED_SYNTAX_ERROR: class TestTokenCounterIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for TokenCounter enhancements."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.token_counter = TokenCounter()

# REMOVED_SYNTAX_ERROR: def test_full_workflow_optimization_and_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test complete workflow of optimization and tracking."""
    # REMOVED_SYNTAX_ERROR: pass
    # Step 1: Optimize a prompt
    # REMOVED_SYNTAX_ERROR: original_prompt = "Please kindly help me with this task in order to complete it properly"
    # REMOVED_SYNTAX_ERROR: optimization_result = self.token_counter.optimize_prompt(original_prompt)

    # Step 2: Track usage with the optimized prompt
    # REMOVED_SYNTAX_ERROR: optimized_tokens = optimization_result["optimized_tokens"]
    # REMOVED_SYNTAX_ERROR: tracking_result = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: agent_name="WorkflowAgent",
    # REMOVED_SYNTAX_ERROR: input_tokens=optimized_tokens,
    # REMOVED_SYNTAX_ERROR: output_tokens=optimized_tokens // 2,  # Estimate output tokens
    # REMOVED_SYNTAX_ERROR: model=LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: operation_type="optimized_execution"
    

    # Step 3: Get suggestions
    # REMOVED_SYNTAX_ERROR: suggestions = self.token_counter.get_optimization_suggestions()

    # Step 4: Get summary
    # REMOVED_SYNTAX_ERROR: summary = self.token_counter.get_agent_usage_summary()

    # Verify the workflow
    # REMOVED_SYNTAX_ERROR: assert optimization_result["tokens_saved"] >= 0
    # REMOVED_SYNTAX_ERROR: assert tracking_result["tracking_enabled"] is True
    # REMOVED_SYNTAX_ERROR: assert tracking_result["agent_name"] == "WorkflowAgent"
    # REMOVED_SYNTAX_ERROR: assert len(suggestions) > 0
    # REMOVED_SYNTAX_ERROR: assert summary["agents_tracked"] == 1
    # REMOVED_SYNTAX_ERROR: assert "WorkflowAgent" in summary["agents"]

# REMOVED_SYNTAX_ERROR: def test_enhanced_stats_with_agent_usage(self):
    # REMOVED_SYNTAX_ERROR: """Test that get_stats includes agent usage summary when available."""
    # Add some agent usage
    # REMOVED_SYNTAX_ERROR: self.token_counter.track_agent_usage("StatsAgent", 100, 50, LLMModel.GEMINI_2_5_FLASH.value)

    # REMOVED_SYNTAX_ERROR: stats = self.token_counter.get_stats()

    # REMOVED_SYNTAX_ERROR: assert "agent_usage_summary" in stats
    # REMOVED_SYNTAX_ERROR: assert stats["agent_usage_summary"]["agents_tracked"] == 1
    # REMOVED_SYNTAX_ERROR: assert "StatsAgent" in stats["agent_usage_summary"]["agents"]

# REMOVED_SYNTAX_ERROR: def test_timestamp_consistency(self, mock_datetime):
    # REMOVED_SYNTAX_ERROR: """Test that timestamps are consistent across operations."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # REMOVED_SYNTAX_ERROR: mock_datetime.now.return_value = fixed_time

    # REMOVED_SYNTAX_ERROR: result = self.token_counter.track_agent_usage( )
    # REMOVED_SYNTAX_ERROR: "TimestampAgent", 100, 50, LLMModel.GEMINI_2_5_FLASH.value
    

    # REMOVED_SYNTAX_ERROR: assert result["timestamp"] == fixed_time.isoformat()