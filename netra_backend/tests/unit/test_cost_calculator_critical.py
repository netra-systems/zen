"""
BUSINESS CRITICAL: Cost Calculator Accuracy & Model Pricing

BVJ: Growth & Enterprise (80% revenue) - Protects core value proposition.
Prevents $100K+ ARR loss from pricing errors. Direct impact on conversions.
Maximum 300 lines, functions  <= 8 lines.
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Tuple

import pytest

from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage

from netra_backend.app.services.cost_calculator import (
    CostCalculatorService,
    CostTier,
    ModelCostInfo,
)

class TestCriticalPricingAccuracy:
    """Revenue-protecting pricing accuracy tests."""
    
    @pytest.fixture
    def calculator(self):
        """Create cost calculator for critical tests."""
        return CostCalculatorService()
    
    @pytest.fixture
    def enterprise_scenario(self):
        """Enterprise customer: 50M tokens/month scenario."""
        return TokenUsage(prompt_tokens=35000000, completion_tokens=15000000, total_tokens=50000000)
    
    def test_openai_pricing_precision_enterprise(self, calculator, enterprise_scenario):
        """Test OpenAI pricing precision for enterprise revenue scenarios."""
        # Use default MID tier for base pricing
        gpt4 = calculator.calculate_cost(enterprise_scenario, LLMProvider.OPENAI, "gpt-4")
        gpt4_turbo = calculator.calculate_cost(enterprise_scenario, LLMProvider.OPENAI, "gpt-4-turbo")
        gpt35 = calculator.calculate_cost(enterprise_scenario, LLMProvider.OPENAI, "gpt-3.5-turbo")
        assert gpt4 > gpt4_turbo > gpt35
        # Updated expected values for MID tier (no multiplier)
        # gpt-4: (35M/1000 * 0.03) + (15M/1000 * 0.06) = 1050 + 900 = 1950.00
        # gpt-3.5-turbo: (35M/1000 * 0.001) + (15M/1000 * 0.002) = 35 + 30 = 65.00
        assert gpt4 == Decimal("1950.00") and gpt35 == Decimal("65.00")
    
    def test_anthropic_pricing_precision_enterprise(self, calculator, enterprise_scenario):
        """Test Anthropic pricing precision for enterprise decisions."""
        opus = calculator.calculate_cost(enterprise_scenario, LLMProvider.ANTHROPIC, "claude-3-opus")
        sonnet = calculator.calculate_cost(enterprise_scenario, LLMProvider.ANTHROPIC, "claude-3.5-sonnet")
        haiku = calculator.calculate_cost(enterprise_scenario, LLMProvider.ANTHROPIC, "claude-3-haiku")
        assert opus > sonnet > haiku
        # Updated expected values for MID tier
        # opus: (35M/1000 * 0.015) + (15M/1000 * 0.075) = 525 + 1125 = 1650.00
        # haiku: (35M/1000 * 0.00025) + (15M/1000 * 0.00125) = 8.75 + 18.75 = 27.5
        assert opus == Decimal("1650.00") and haiku == Decimal("27.5")
    
    def test_google_pricing_competitive_advantage(self, calculator, enterprise_scenario):
        """Test Google Gemini competitive pricing advantage."""
        pro = calculator.calculate_cost(enterprise_scenario, LLMProvider.GOOGLE, "gemini-2.5-pro")
        flash = calculator.calculate_cost(enterprise_scenario, LLMProvider.GOOGLE, "gemini-2.5-flash")
        assert flash < pro
        # Updated expected values for MID tier
        # pro: (35M/1000 * 0.0035) + (15M/1000 * 0.0105) = 122.5 + 157.5 = 280.0
        # flash: (35M/1000 * 0.000075) + (15M/1000 * 0.0003) = 2.625 + 4.5 = 7.125
        assert flash == Decimal("7.125") and pro == Decimal("280.0")
    
    def test_cost_savings_calculation_accuracy(self, calculator, enterprise_scenario):
        """Test cost savings calculations for tier upgrade justification."""
        expensive = calculator.calculate_cost(enterprise_scenario, LLMProvider.OPENAI, "gpt-4")
        optimized = calculator.calculate_cost(enterprise_scenario, LLMProvider.GOOGLE, "gemini-2.5-flash")
        savings = expensive - optimized
        percentage = (savings / expensive) * Decimal("100")
        # Updated expected values: 1950.0 - 7.125 = 1942.875
        assert savings == Decimal("1942.875") and percentage > Decimal("99")

class TestCriticalTokenPrecision:
    """Token precision tests for billing accuracy."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for precision tests."""
        return CostCalculatorService()
    
    def test_fractional_token_precision(self, calculator):
        """Test precision for fractional token scenarios."""
        usage = TokenUsage(prompt_tokens=1001, completion_tokens=503, total_tokens=1504)
        cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        # gpt-3.5-turbo: prompt=0.001, completion=0.002
        expected = (Decimal("1001") / Decimal("1000")) * Decimal("0.001") + (Decimal("503") / Decimal("1000")) * Decimal("0.002")
        # 1.001 * 0.001 + 0.503 * 0.002 = 0.001001 + 0.001006 = 0.002007
        assert cost == expected == Decimal("0.002007")
    
    def test_rounding_consistency_across_models(self, calculator):
        """Test rounding consistency across all model calculations."""
        usage = TokenUsage(prompt_tokens=1337, completion_tokens=666, total_tokens=2003)
        costs = self._calculate_costs_across_providers(calculator, usage)
        self._assert_decimal_precision_consistency(costs)
    
    def _calculate_costs_across_providers(self, calculator, usage):
        """Calculate costs across different providers."""
        providers = [
            (LLMProvider.OPENAI, "gpt-3.5-turbo"),
            (LLMProvider.ANTHROPIC, "claude-3-haiku"),
            (LLMProvider.GOOGLE, "gemini-2.5-pro")
        ]
        return [calculator.calculate_cost(usage, provider, model) for provider, model in providers]
    
    def _assert_decimal_precision_consistency(self, costs):
        """Assert all costs have consistent decimal precision."""
        for cost in costs:
            # Allow up to 10 decimal places for high precision calculations
            assert len(str(cost).split('.')[-1]) <= 10
    
    def test_maximum_token_limit_handling(self, calculator):
        """Test handling of maximum possible token counts."""
        max_usage = TokenUsage(prompt_tokens=2147483647, completion_tokens=2147483647, total_tokens=4294967294)
        cost = calculator.calculate_cost(max_usage, LLMProvider.OPENAI, "gpt-4")
        assert isinstance(cost, Decimal) and cost == Decimal("193273.52823")

class TestCriticalModelRecommendations:
    """Model recommendation tests for customer value."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for recommendation tests."""
        return CostCalculatorService()
    
    def test_economy_tier_recommendations_all_providers(self, calculator):
        """Test economy tier recommendations maximize cost savings."""
        openai = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.ECONOMY)
        anthropic = calculator.get_cost_optimal_model(LLMProvider.ANTHROPIC, CostTier.ECONOMY)
        google = calculator.get_cost_optimal_model(LLMProvider.GOOGLE, CostTier.ECONOMY)
        assert openai == "gpt-3.5-turbo" and anthropic == "claude-3-haiku"
        assert google == "gemini-2.5-flash"
    
    def test_balanced_tier_cost_performance_optimization(self, calculator):
        """Test balanced tier maximizes value for money."""
        openai = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.BALANCED)
        anthropic = calculator.get_cost_optimal_model(LLMProvider.ANTHROPIC, CostTier.BALANCED)
        google = calculator.get_cost_optimal_model(LLMProvider.GOOGLE, CostTier.BALANCED)
        assert openai == "gpt-4-turbo" and anthropic == "claude-3.5-sonnet"
        assert google == "gemini-2.5-pro"
    
    def test_premium_tier_performance_selection(self, calculator):
        """Test premium tier selects highest performance models."""
        openai_premium = calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.PREMIUM)
        anthropic_premium = calculator.get_cost_optimal_model(LLMProvider.ANTHROPIC, CostTier.PREMIUM)
        
        assert openai_premium == "gpt-4"
        assert anthropic_premium == "claude-3-opus"

class TestCriticalBudgetProjections:
    """Budget projection tests for enterprise sales."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for budget tests."""
        return CostCalculatorService()
    
    def test_enterprise_budget_impact_estimation(self, calculator):
        """Test enterprise budget impact estimation accuracy."""
        monthly = calculator.estimate_budget_impact(100000000, LLMProvider.OPENAI, "gpt-4")
        annual = monthly * Decimal("12")
        assert monthly == Decimal("3900.00") and annual == Decimal("46800.00")
    
    def test_optimization_savings_roi_calculation(self, calculator):
        """Test ROI calculations for optimization recommendations."""
        baseline = calculator.estimate_budget_impact(10000000, LLMProvider.OPENAI, "gpt-4")
        optimized = calculator.estimate_budget_impact(10000000, LLMProvider.GOOGLE, "gemini-2.5-flash")
        monthly = baseline - optimized
        annual = monthly * Decimal("12")
        assert monthly == Decimal("388.575000") and annual == Decimal("4662.900000")

class TestCriticalErrorScenarios:
    """Error scenario tests for customer trust."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for error scenario tests."""
        return CostCalculatorService()
    
    def test_invalid_model_graceful_degradation(self, calculator):
        """Test graceful degradation for invalid models."""
        usage = TokenUsage(prompt_tokens=10000, completion_tokens=5000, total_tokens=15000)
        cost = calculator.calculate_cost(usage, LLMProvider.OPENAI, "invalid-model-xyz")
        assert isinstance(cost, Decimal) and cost == Decimal("0.02")
    
    def test_zero_division_protection(self, calculator):
        """Test protection against zero division errors."""
        zero_usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        providers = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE]
        costs = [calculator.calculate_cost(zero_usage, p, "any-model") for p in providers]
        assert all(cost == Decimal("0") for cost in costs)
    
    def test_negative_input_sanitization(self, calculator):
        """Test sanitization of negative inputs."""
        negative_usage = TokenUsage(prompt_tokens=-1000, completion_tokens=-500, total_tokens=-1500)
        
        cost = calculator.calculate_cost(negative_usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Negative inputs must be handled gracefully, return zero
        assert cost == Decimal("0")

class TestCriticalPerformanceRequirements:
    """Performance tests for cost calculations."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for performance tests."""
        return CostCalculatorService()
    
    def test_batch_calculation_performance(self, calculator):
        """Test batch calculation performance for real-time usage."""
        import time
        usage_batch = [TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500) for _ in range(100)]
        start = time.time()
        total = sum(calculator.calculate_cost(u, LLMProvider.OPENAI, "gpt-3.5-turbo") for u in usage_batch)
        assert (time.time() - start) < 0.01 and total > Decimal("0")
    
    def test_concurrent_calculation_consistency(self, calculator):
        """Test calculation consistency under concurrent access."""
        usage = TokenUsage(prompt_tokens=5000, completion_tokens=2500, total_tokens=7500)
        costs = [calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo") for _ in range(10)]
        # gpt-3.5-turbo: (5000/1000 * 0.001) + (2500/1000 * 0.002) = 0.005 + 0.005 = 0.01
        assert all(cost == costs[0] for cost in costs) and costs[0] == Decimal("0.01")