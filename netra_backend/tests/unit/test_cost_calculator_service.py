"""
CRITICAL REVENUE-INTEGRITY TESTS: Cost Calculator Service Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise + Mid-tier (80% revenue)
- Business Goal: Ensure accurate cost calculations for billing
- Value Impact: Prevents $50K+ MRR loss from pricing errors
- Revenue Impact: Direct impact on 20% performance fee capture

Tests ALL cost calculation scenarios for business-critical accuracy.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import Mock, patch

from app.services.cost_calculator import (
    CostCalculatorService, BudgetManager, CostTier, ModelCostInfo,
    create_cost_calculator, create_budget_manager, optimize_model_selection,
    calculate_cost_savings
)
from app.schemas.llm_base_types import LLMProvider, TokenUsage


# Global fixtures for token usage scenarios (shared across test classes)
@pytest.fixture
def enterprise_usage():
    """10M tokens/month enterprise scenario."""
    return TokenUsage(prompt_tokens=7000000, completion_tokens=3000000, total_tokens=10000000)

@pytest.fixture
def mid_tier_usage():
    """Mid-tier customer optimization scenario."""
    return TokenUsage(prompt_tokens=70000, completion_tokens=30000, total_tokens=100000)

@pytest.fixture
def free_tier_usage():
    """Free tier approaching limits."""
    return TokenUsage(prompt_tokens=7000, completion_tokens=3000, total_tokens=10000)


class TestCostCalculatorService:
    """Revenue-critical tests for cost calculation accuracy."""
    
    @pytest.fixture
    def calculator(self):
        """Create cost calculator instance."""
        return CostCalculatorService()

    def test_openai_gpt4_cost_calculation(self, calculator, enterprise_usage):
        """Test GPT-4 cost calculation for enterprise usage."""
        cost = calculator.calculate_cost(enterprise_usage, LLMProvider.OPENAI, "gpt-4")
        expected = (Decimal("7000000") / Decimal("1000")) * Decimal("0.03") + \
                  (Decimal("3000000") / Decimal("1000")) * Decimal("0.06")
        assert cost == expected
        assert cost == Decimal("390.00")  # $390 for 10M tokens

    def test_anthropic_claude_opus_cost_calculation(self, calculator, enterprise_usage):
        """Test Claude Opus cost calculation for enterprise usage."""
        cost = calculator.calculate_cost(enterprise_usage, LLMProvider.ANTHROPIC, "claude-3-opus")
        expected = (Decimal("7000000") / Decimal("1000")) * Decimal("0.015") + \
                  (Decimal("3000000") / Decimal("1000")) * Decimal("0.075")
        assert cost == expected
        assert cost == Decimal("330.00")  # $330 for 10M tokens

    def test_google_gemini_flash_economy_calculation(self, calculator, enterprise_usage):
        """Test Gemini Flash economy tier calculation."""
        cost = calculator.calculate_cost(enterprise_usage, LLMProvider.GOOGLE, "gemini-2.5-flash")
        expected = (Decimal("7000000") / Decimal("1000")) * Decimal("0.000075") + \
                  (Decimal("3000000") / Decimal("1000")) * Decimal("0.0003")
        assert cost == expected
        assert cost == Decimal("1.425")  # $1.43 for 10M tokens - massive savings

    def test_zero_tokens_cost_calculation(self, calculator):
        """Test zero tokens returns zero cost."""
        usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-4")
        assert cost == Decimal("0")

    def test_negative_tokens_handled_safely(self, calculator):
        """Test negative token counts handled safely."""
        usage = TokenUsage(prompt_tokens=-100, completion_tokens=-50, total_tokens=-150)
        cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-4")
        assert cost == Decimal("0")

    def test_massive_usage_spike_calculation(self, calculator):
        """Test calculation for massive usage spikes."""
        spike_usage = TokenUsage(prompt_tokens=100000000, completion_tokens=50000000, total_tokens=150000000)
        cost = calculator.calculate_cost(spike_usage, LLMProvider.OPENAI, "gpt-4")
        expected = Decimal("100000") * Decimal("0.03") + Decimal("50000") * Decimal("0.06")
        assert cost == expected
        assert cost == Decimal("6000.00")  # $6000 for 150M tokens

    def test_unknown_model_uses_defaults(self, calculator, mid_tier_usage):
        """Test unknown model falls back to default pricing."""
        cost = calculator.calculate_cost(mid_tier_usage, LLMProvider.OPENAI, "unknown-model")
        expected = (Decimal("70000") / Decimal("1000")) * Decimal("0.001") + \
                  (Decimal("30000") / Decimal("1000")) * Decimal("0.002")
        assert cost == expected
        assert cost == Decimal("0.13")

    def test_cost_tier_optimization_openai(self, calculator):
        """Test cost tier optimization for OpenAI."""
        economy_model = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.ECONOMY)
        balanced_model = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.BALANCED)
        premium_model = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.PREMIUM)
        
        assert economy_model == "gpt-3.5-turbo"
        assert balanced_model == "gpt-4-turbo"
        assert premium_model == "gpt-4"

    def test_budget_impact_estimation(self, calculator):
        """Test budget impact estimation accuracy."""
        impact = calculator.estimate_budget_impact(100000, LLMProvider.OPENAI, "gpt-4")
        # 70% prompt (70k * 0.03/1k) + 30% completion (30k * 0.06/1k)
        expected = Decimal("2.1") + Decimal("1.8")
        assert impact == expected
        assert impact == Decimal("3.9")

    def test_multi_model_cost_aggregation(self, calculator, mid_tier_usage):
        """Test multi-model cost aggregation."""
        openai_cost = calculator.calculate_cost(mid_tier_usage, LLMProvider.OPENAI, "gpt-4")
        anthropic_cost = calculator.calculate_cost(mid_tier_usage, LLMProvider.ANTHROPIC, "claude-3.5-sonnet")
        google_cost = calculator.calculate_cost(mid_tier_usage, LLMProvider.GOOGLE, "gemini-2.5-flash")
        
        total_cost = openai_cost + anthropic_cost + google_cost
        assert total_cost > Decimal("0")
        assert openai_cost == Decimal("3.9")  # Most expensive
        assert google_cost < Decimal("1")     # Most economical


class TestBudgetManager:
    """Tests for budget management and spending tracking."""
    
    @pytest.fixture
    def budget_manager(self):
        """Create budget manager with $100 daily budget."""
        return BudgetManager(daily_budget=Decimal("100.00"))
    
    @pytest.fixture
    def enterprise_budget_manager(self):
        """Create budget manager for enterprise ($1000 daily budget)."""
        return BudgetManager(daily_budget=Decimal("1000.00"))

    def test_budget_impact_check_within_limits(self, budget_manager, free_tier_usage):
        """Test budget check when within limits."""
        can_proceed = budget_manager.check_budget_impact(
            free_tier_usage, LLMProvider.OPENAI, "gpt-3.5-turbo"
        )
        assert can_proceed is True

    def test_budget_impact_check_exceeds_limits(self, budget_manager, enterprise_usage):
        """Test budget check when exceeding limits."""
        can_proceed = budget_manager.check_budget_impact(
            enterprise_usage, LLMProvider.OPENAI, "gpt-4"
        )
        assert can_proceed is False

    def test_usage_recording_updates_spending(self, budget_manager, free_tier_usage):
        """Test usage recording updates current spending."""
        initial_spending = budget_manager.current_spending
        cost = budget_manager.record_usage(free_tier_usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        assert budget_manager.current_spending > initial_spending
        assert cost > Decimal("0")
        assert budget_manager.current_spending == initial_spending + cost

    def test_remaining_budget_calculation(self, budget_manager):
        """Test remaining budget calculation accuracy."""
        initial_remaining = budget_manager.get_remaining_budget()
        assert initial_remaining == Decimal("100.00")
        
        budget_manager.current_spending = Decimal("30.00")
        remaining = budget_manager.get_remaining_budget()
        assert remaining == Decimal("70.00")

    def test_cost_tier_recommendation_logic(self, budget_manager):
        """Test cost tier recommendation based on remaining budget."""
        # High budget -> BALANCED
        budget_manager.current_spending = Decimal("20.00")  # 80% remaining
        tier = budget_manager.recommend_cost_tier()
        assert tier == CostTier.BALANCED
        
        # Medium budget -> ECONOMY
        budget_manager.current_spending = Decimal("70.00")  # 30% remaining
        tier = budget_manager.recommend_cost_tier()
        assert tier == CostTier.ECONOMY
        
        # Low budget -> ECONOMY
        budget_manager.current_spending = Decimal("85.00")  # 15% remaining
        tier = budget_manager.recommend_cost_tier()
        assert tier == CostTier.ECONOMY

    def test_daily_spending_reset(self, budget_manager):
        """Test daily spending reset functionality."""
        budget_manager.current_spending = Decimal("50.00")
        budget_manager.reset_daily_spending()
        assert budget_manager.current_spending == Decimal("0.00")


class TestCostOptimizationUtilities:
    """Tests for cost optimization utility functions."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for optimization tests."""
        return CostCalculatorService()

    def test_optimize_model_selection(self, calculator):
        """Test model selection optimization utility."""
        model = optimize_model_selection(LLMProvider.ANTHROPIC, CostTier.ECONOMY, calculator)
        assert model == "claude-3-haiku"

    def test_calculate_cost_savings_optimization(self, calculator):
        """Test cost savings calculation from optimization."""
        original_usage = TokenUsage(prompt_tokens=10000, completion_tokens=5000, total_tokens=15000)
        optimized_usage = TokenUsage(prompt_tokens=10000, completion_tokens=5000, total_tokens=15000)
        
        savings = calculate_cost_savings(
            original_usage, LLMProvider.OPENAI, "gpt-4",
            optimized_usage, LLMProvider.GOOGLE, "gemini-2.5-flash",
            calculator
        )
        
        assert savings > Decimal("0")  # Should show significant savings
        expected_original = Decimal("0.6")  # GPT-4 cost
        expected_optimized = Decimal("0.0021")  # Gemini Flash cost
        assert abs(savings - (expected_original - expected_optimized)) < Decimal("0.01")


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_cost_calculator_factory(self):
        """Test cost calculator factory function."""
        calculator = create_cost_calculator()
        assert isinstance(calculator, CostCalculatorService)
        assert calculator._model_pricing is not None

    def test_create_budget_manager_factory_default(self):
        """Test budget manager factory with default budget."""
        manager = create_budget_manager()
        assert isinstance(manager, BudgetManager)
        assert manager.daily_budget == Decimal("100.00")

    def test_create_budget_manager_factory_custom(self):
        """Test budget manager factory with custom budget."""
        custom_budget = Decimal("500.00")
        manager = create_budget_manager(custom_budget)
        assert manager.daily_budget == custom_budget


# Edge case and error handling tests
class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for edge case tests."""
        return CostCalculatorService()

    def test_extremely_large_token_counts(self, calculator):
        """Test handling of extremely large token counts."""
        huge_usage = TokenUsage(
            prompt_tokens=999999999, completion_tokens=999999999, total_tokens=1999999998
        )
        cost = calculator.calculate_cost(huge_usage, LLMProvider.OPENAI, "gpt-4")
        assert cost > Decimal("0")
        assert isinstance(cost, Decimal)

    def test_precision_handling_for_small_costs(self, calculator):
        """Test decimal precision for very small costs."""
        tiny_usage = TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        cost = calculator.calculate_cost(tiny_usage, LLMProvider.GOOGLE, "gemini-2.5-flash")
        
        # Should maintain precision for tiny costs
        assert cost > Decimal("0")
        assert len(str(cost).split('.')[-1]) <= 10  # Reasonable decimal places

    def test_model_pricing_key_generation(self, calculator):
        """Test model pricing key generation consistency."""
        pricing = calculator._get_model_pricing(LLMProvider.OPENAI, "gpt-4")
        assert pricing.provider == LLMProvider.OPENAI
        assert pricing.model_name == "gpt-4"
        
        # Test unknown model falls back to defaults
        unknown_pricing = calculator._get_model_pricing(LLMProvider.OPENAI, "unknown")
        assert unknown_pricing == calculator._default_costs