"""
Cost calculation service for LLM operations.
Provides accurate cost tracking and budget management.
Maximum 300 lines, functions ≤8 lines.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Dict, Optional, Tuple

from pydantic import BaseModel

from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage


class CostTier(str, Enum):
    """Cost tier categories for model selection"""
    ECONOMY = "economy"      # Lowest cost models
    BALANCED = "balanced"    # Good cost-performance ratio
    PREMIUM = "premium"      # Highest performance models


class ModelCostInfo(BaseModel):
    """Cost information for a specific model"""
    provider: LLMProvider
    model_name: str
    prompt_cost_per_1k: Decimal  # Cost per 1k prompt tokens
    completion_cost_per_1k: Decimal  # Cost per 1k completion tokens
    cost_tier: CostTier
    performance_score: float  # 0-100, higher = better performance


class CostCalculatorService:
    """Service for calculating LLM usage costs"""
    
    def __init__(self):
        self._model_pricing = self._initialize_pricing()
        self._default_costs = self._get_default_costs()
    
    def calculate_cost(self, usage: TokenUsage, provider: LLMProvider, model: str) -> Decimal:
        """Calculate cost for token usage"""
        pricing = self._get_model_pricing(provider, model)
        prompt_cost = self._calculate_prompt_cost(usage.prompt_tokens, pricing)
        completion_cost = self._calculate_completion_cost(usage.completion_tokens, pricing)
        return prompt_cost + completion_cost
    
    def get_cost_optimal_model(self, provider: LLMProvider, cost_tier: CostTier) -> Optional[str]:
        """Get most cost-optimal model for provider and tier"""
        models = self._get_models_by_tier(provider, cost_tier)
        return self._select_best_cost_performance(models)
    
    def estimate_budget_impact(self, token_count: int, provider: LLMProvider, model: str) -> Decimal:
        """Estimate budget impact for projected token usage"""
        pricing = self._get_model_pricing(provider, model)
        # Assume 70% prompt, 30% completion tokens for estimation
        prompt_tokens = int(token_count * 0.7)
        completion_tokens = int(token_count * 0.3)
        return self._calculate_total_cost(prompt_tokens, completion_tokens, pricing)
    
    def _get_openai_pricing(self) -> Dict[str, ModelCostInfo]:
        """Get OpenAI model pricing configuration."""
        return {
            "openai_gpt-4": ModelCostInfo(
                provider=LLMProvider.OPENAI, model_name="gpt-4",
                prompt_cost_per_1k=Decimal("0.03"), completion_cost_per_1k=Decimal("0.06"),
                cost_tier=CostTier.PREMIUM, performance_score=95.0
            ),
            "openai_gpt-4-turbo": ModelCostInfo(
                provider=LLMProvider.OPENAI, model_name="gpt-4-turbo",
                prompt_cost_per_1k=Decimal("0.01"), completion_cost_per_1k=Decimal("0.03"),
                cost_tier=CostTier.BALANCED, performance_score=92.0
            ),
            "openai_gpt-3.5-turbo": ModelCostInfo(
                provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo",
                prompt_cost_per_1k=Decimal("0.0015"), completion_cost_per_1k=Decimal("0.002"),
                cost_tier=CostTier.ECONOMY, performance_score=75.0
            )
        }
    
    def _get_anthropic_pricing(self) -> Dict[str, ModelCostInfo]:
        """Get Anthropic model pricing configuration."""
        return {
            "anthropic_claude-3-opus": ModelCostInfo(
                provider=LLMProvider.ANTHROPIC, model_name="claude-3-opus",
                prompt_cost_per_1k=Decimal("0.015"), completion_cost_per_1k=Decimal("0.075"),
                cost_tier=CostTier.PREMIUM, performance_score=96.0
            ),
            "anthropic_claude-3.5-sonnet": ModelCostInfo(
                provider=LLMProvider.ANTHROPIC, model_name="claude-3.5-sonnet",
                prompt_cost_per_1k=Decimal("0.003"), completion_cost_per_1k=Decimal("0.015"),
                cost_tier=CostTier.BALANCED, performance_score=90.0
            ),
            "anthropic_claude-3-haiku": ModelCostInfo(
                provider=LLMProvider.ANTHROPIC, model_name="claude-3-haiku",
                prompt_cost_per_1k=Decimal("0.00025"), completion_cost_per_1k=Decimal("0.00125"),
                cost_tier=CostTier.ECONOMY, performance_score=70.0
            )
        }
    
    def _get_google_pricing(self) -> Dict[str, ModelCostInfo]:
        """Get Google/Gemini model pricing configuration."""
        return {
            "google_gemini-2.5-pro": ModelCostInfo(
                provider=LLMProvider.GOOGLE, model_name="gemini-2.5-pro",
                prompt_cost_per_1k=Decimal("0.0035"), completion_cost_per_1k=Decimal("0.0105"),
                cost_tier=CostTier.BALANCED, performance_score=88.0
            ),
            "google_gemini-2.5-flash": ModelCostInfo(
                provider=LLMProvider.GOOGLE, model_name="gemini-2.5-flash",
                prompt_cost_per_1k=Decimal("0.000075"), completion_cost_per_1k=Decimal("0.0003"),
                cost_tier=CostTier.ECONOMY, performance_score=72.0
            )
        }
    
    def _initialize_pricing(self) -> Dict[str, ModelCostInfo]:
        """Initialize model pricing database"""
        pricing = {}
        pricing.update(self._get_openai_pricing())
        pricing.update(self._get_anthropic_pricing())
        pricing.update(self._get_google_pricing())
        return pricing
    
    def _get_default_costs(self) -> ModelCostInfo:
        """Get default cost structure for unknown models"""
        return ModelCostInfo(
            provider=LLMProvider.OPENAI, model_name="unknown",
            prompt_cost_per_1k=Decimal("0.001"), completion_cost_per_1k=Decimal("0.002"),
            cost_tier=CostTier.ECONOMY, performance_score=50.0
        )
    
    def _get_model_pricing(self, provider: LLMProvider, model: str) -> ModelCostInfo:
        """Get pricing info for specific model"""
        key = f"{provider.value}_{model}"
        return self._model_pricing.get(key, self._default_costs)
    
    def _calculate_prompt_cost(self, tokens: int, pricing: ModelCostInfo) -> Decimal:
        """Calculate cost for prompt tokens"""
        if tokens <= 0:
            return Decimal("0")
        return (Decimal(tokens) / Decimal("1000")) * pricing.prompt_cost_per_1k
    
    def _calculate_completion_cost(self, tokens: int, pricing: ModelCostInfo) -> Decimal:
        """Calculate cost for completion tokens"""
        if tokens <= 0:
            return Decimal("0")
        return (Decimal(tokens) / Decimal("1000")) * pricing.completion_cost_per_1k
    
    def _calculate_total_cost(self, prompt_tokens: int, completion_tokens: int, pricing: ModelCostInfo) -> Decimal:
        """Calculate total cost for token usage"""
        prompt_cost = self._calculate_prompt_cost(prompt_tokens, pricing)
        completion_cost = self._calculate_completion_cost(completion_tokens, pricing)
        return prompt_cost + completion_cost
    
    def _get_models_by_tier(self, provider: LLMProvider, tier: CostTier) -> list[ModelCostInfo]:
        """Get models by provider and cost tier"""
        return [
            info for info in self._model_pricing.values() 
            if info.provider == provider and info.cost_tier == tier
        ]
    
    def _select_best_cost_performance(self, models: list[ModelCostInfo]) -> Optional[str]:
        """Select model with best cost-performance ratio"""
        if not models:
            return None
        # Sort by performance score descending, then by cost ascending
        best_model = max(models, key=lambda m: m.performance_score)
        return best_model.model_name


class BudgetManager:
    """Manages budget constraints and spending tracking"""
    
    def __init__(self, daily_budget: Decimal = Decimal("100.00")):
        self.daily_budget = daily_budget
        self.current_spending = Decimal("0.00")
        self.cost_calculator = CostCalculatorService()
    
    def check_budget_impact(self, usage: TokenUsage, provider: LLMProvider, model: str) -> bool:
        """Check if operation would exceed budget"""
        cost = self.cost_calculator.calculate_cost(usage, provider, model)
        return (self.current_spending + cost) <= self.daily_budget
    
    def record_usage(self, usage: TokenUsage, provider: LLMProvider, model: str) -> Decimal:
        """Record usage and return cost"""
        cost = self.cost_calculator.calculate_cost(usage, provider, model)
        self.current_spending += cost
        return cost
    
    def get_remaining_budget(self) -> Decimal:
        """Get remaining budget amount"""
        return max(Decimal("0"), self.daily_budget - self.current_spending)
    
    def _calculate_remaining_ratio(self) -> Decimal:
        """Calculate remaining budget ratio."""
        return self.get_remaining_budget() / self.daily_budget
    
    def recommend_cost_tier(self) -> CostTier:
        """Recommend cost tier based on remaining budget"""
        remaining_ratio = self._calculate_remaining_ratio()
        if remaining_ratio > Decimal("0.5"):
            return CostTier.BALANCED
        elif remaining_ratio > Decimal("0.2"):
            return CostTier.ECONOMY
        else:
            return CostTier.ECONOMY
    
    def reset_daily_spending(self):
        """Reset daily spending counter"""
        self.current_spending = Decimal("0.00")


def create_cost_calculator() -> CostCalculatorService:
    """Factory function for cost calculator"""
    return CostCalculatorService()


def create_budget_manager(daily_budget: Optional[Decimal] = None) -> BudgetManager:
    """Factory function for budget manager"""
    budget = daily_budget or Decimal("100.00")
    return BudgetManager(budget)


# Cost optimization utilities
def optimize_model_selection(
    provider: LLMProvider, 
    target_cost_tier: CostTier, 
    calculator: CostCalculatorService
) -> Optional[str]:
    """Optimize model selection based on cost tier"""
    return calculator.get_cost_optimal_model(provider, target_cost_tier)


def calculate_cost_savings(
    original_usage: TokenUsage, original_provider: LLMProvider, original_model: str,
    optimized_usage: TokenUsage, optimized_provider: LLMProvider, optimized_model: str,
    calculator: CostCalculatorService
) -> Decimal:
    """Calculate cost savings from optimization"""
    original_cost = calculator.calculate_cost(original_usage, original_provider, original_model)
    optimized_cost = calculator.calculate_cost(optimized_usage, optimized_provider, optimized_model)
    return original_cost - optimized_cost