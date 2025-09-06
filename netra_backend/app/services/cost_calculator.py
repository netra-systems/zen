"""Cost Calculator Service

Calculates LLM usage costs based on token consumption and provider pricing.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from netra_backend.app.schemas.llm_types import LLMProvider, TokenUsage

logger = logging.getLogger(__name__)


class CostTier(Enum):
    """Cost tiers for different customer segments."""
    FREE = "free"
    EARLY = "early" 
    MID = "mid"
    ENTERPRISE = "enterprise"
    # Additional tier values for cost optimization
    ECONOMY = "economy"
    BALANCED = "balanced"
    PREMIUM = "premium"


@dataclass
class ModelCostInfo:
    """Cost information for a specific model."""
    prompt_cost_per_1k: Decimal
    completion_cost_per_1k: Decimal
    model_name: str
    provider: LLMProvider
    cost_tier: Optional['CostTier'] = None
    performance_score: Optional[float] = None
    
    def calculate_cost(self, usage: TokenUsage) -> Decimal:
        """Calculate cost for token usage."""
        prompt_cost = (Decimal(usage.prompt_tokens) / 1000) * self.prompt_cost_per_1k
        completion_cost = (Decimal(usage.completion_tokens) / 1000) * self.completion_cost_per_1k
        return prompt_cost + completion_cost


class CostCalculatorService:
    """Service for calculating LLM usage costs."""
    
    def __init__(self):
        self._model_costs = self._initialize_model_costs()
    
    def _initialize_model_costs(self) -> Dict[str, ModelCostInfo]:
        """Initialize model cost information."""
        return {
            # OpenAI models
            "gpt-4": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.03"),
                completion_cost_per_1k=Decimal("0.06"),
                model_name="gpt-4",
                provider=LLMProvider.OPENAI
            ),
            "gpt-4-turbo": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.01"),
                completion_cost_per_1k=Decimal("0.03"),
                model_name="gpt-4-turbo",
                provider=LLMProvider.OPENAI
            ),
            "gpt-3.5-turbo": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.001"),
                completion_cost_per_1k=Decimal("0.002"),
                model_name="gpt-3.5-turbo",
                provider=LLMProvider.OPENAI
            ),
            # Anthropic models
            "claude-3-opus": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.015"),
                completion_cost_per_1k=Decimal("0.075"),
                model_name="claude-3-opus",
                provider=LLMProvider.ANTHROPIC
            ),
            "claude-3.5-sonnet": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.003"),
                completion_cost_per_1k=Decimal("0.015"),
                model_name="claude-3.5-sonnet",
                provider=LLMProvider.ANTHROPIC
            ),
            "claude-3-sonnet": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.003"),
                completion_cost_per_1k=Decimal("0.015"),
                model_name="claude-3-sonnet",
                provider=LLMProvider.ANTHROPIC
            ),
            "claude-3-haiku": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.00025"),
                completion_cost_per_1k=Decimal("0.00125"),
                model_name="claude-3-haiku",
                provider=LLMProvider.ANTHROPIC
            ),
            # Google models
            "gemini-2.5-pro": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.0035"),
                completion_cost_per_1k=Decimal("0.0105"),
                model_name="gemini-2.5-pro",
                provider=LLMProvider.GOOGLE
            ),
            "gemini-2.5-flash": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.000075"),
                completion_cost_per_1k=Decimal("0.0003"),
                model_name="gemini-2.5-flash",
                provider=LLMProvider.GOOGLE
            ),
            # Default fallback
            "default": ModelCostInfo(
                prompt_cost_per_1k=Decimal("0.001"),
                completion_cost_per_1k=Decimal("0.002"),
                model_name="default",
                provider=LLMProvider.OPENAI
            ),
        }
    
    def calculate_cost(
        self, 
        usage: TokenUsage, 
        provider: LLMProvider, 
        model_name: str,
        tier: CostTier = CostTier.MID
    ) -> Decimal:
        """Calculate cost for LLM usage.
        
        Args:
            usage: Token usage statistics
            provider: LLM provider
            model_name: Name of the model used
            tier: Customer tier for pricing
            
        Returns:
            Decimal: Cost in USD
        """
        # Validate inputs
        if usage.total_tokens <= 0:
            return Decimal("0")
        
        # Get model cost info
        model_key = f"{model_name}".lower()
        model_cost = self._model_costs.get(model_key, self._model_costs["default"])
        
        # Calculate base cost
        base_cost = model_cost.calculate_cost(usage)
        
        # Apply tier multiplier
        tier_multiplier = self._get_tier_multiplier(tier)
        final_cost = base_cost * tier_multiplier
        
        logger.debug(
            f"Cost calculation: {usage.total_tokens} tokens, "
            f"model={model_name}, tier={tier.value}, cost=${final_cost}"
        )
        
        return final_cost
    
    def _get_tier_multiplier(self, tier: CostTier) -> Decimal:
        """Get pricing multiplier for customer tier."""
        multipliers = {
            CostTier.FREE: Decimal("2.0"),  # Higher cost to encourage upgrades
            CostTier.EARLY: Decimal("0.8"),  # 20% discount
            CostTier.MID: Decimal("1.0"),    # Standard pricing
            CostTier.ENTERPRISE: Decimal("0.6"),  # 40% discount
            CostTier.ECONOMY: Decimal("1.0"),    # Standard pricing for cost optimization
            CostTier.BALANCED: Decimal("1.0"),   # Standard pricing for balanced tier  
            CostTier.PREMIUM: Decimal("1.0"),    # Standard pricing for premium tier
        }
        return multipliers.get(tier, Decimal("1.0"))
    
    def get_model_info(self, model_name: str) -> Optional[ModelCostInfo]:
        """Get cost information for a specific model."""
        return self._model_costs.get(model_name.lower())
    
    def estimate_monthly_cost(
        self, 
        daily_usage: TokenUsage, 
        provider: LLMProvider,
        model_name: str,
        tier: CostTier = CostTier.MID
    ) -> Decimal:
        """Estimate monthly cost based on daily usage."""
        daily_cost = self.calculate_cost(daily_usage, provider, model_name, tier)
        return daily_cost * Decimal("30")  # Approximate month
    
    def get_available_models(self) -> Dict[str, ModelCostInfo]:
        """Get all available models and their cost information."""
        return self._model_costs.copy()
    
    def calculate_savings(
        self,
        usage: TokenUsage,
        current_tier: CostTier,
        target_tier: CostTier,
        provider: LLMProvider,
        model_name: str
    ) -> Dict[str, Any]:
        """Calculate potential savings from tier upgrade."""
        current_cost = self.calculate_cost(usage, provider, model_name, current_tier)
        target_cost = self.calculate_cost(usage, provider, model_name, target_tier)
        
        savings = current_cost - target_cost
        savings_percentage = (savings / current_cost * 100) if current_cost > 0 else Decimal("0")
        
        return {
            "current_cost": current_cost,
            "target_cost": target_cost,
            "savings": savings,
            "savings_percentage": savings_percentage,
            "recommended": savings > Decimal("10.0")  # Recommend if saves $10+
        }
    
    def get_cost_optimal_model(self, provider: LLMProvider, tier: CostTier) -> str:
        """Get the cost-optimal model for a provider and tier.
        
        Args:
            provider: LLM provider
            tier: Cost tier (economy, balanced, premium)
            
        Returns:
            str: Recommended model name
        """
        provider_models = {
            LLMProvider.OPENAI: {
                CostTier.FREE: "gpt-3.5-turbo",  # Cheapest
                CostTier.ECONOMY: "gpt-3.5-turbo",
                CostTier.EARLY: "gpt-3.5-turbo",
                CostTier.BALANCED: "gpt-4-turbo",
                CostTier.MID: "gpt-4-turbo",
                CostTier.PREMIUM: "gpt-4",
                CostTier.ENTERPRISE: "gpt-4"
            },
            LLMProvider.ANTHROPIC: {
                CostTier.FREE: "claude-3-haiku",
                CostTier.ECONOMY: "claude-3-haiku",
                CostTier.EARLY: "claude-3-haiku", 
                CostTier.BALANCED: "claude-3.5-sonnet",
                CostTier.MID: "claude-3.5-sonnet",
                CostTier.PREMIUM: "claude-3-opus",
                CostTier.ENTERPRISE: "claude-3-opus"
            },
            LLMProvider.GOOGLE: {
                CostTier.FREE: "gemini-2.5-flash",
                CostTier.ECONOMY: "gemini-2.5-flash",
                CostTier.EARLY: "gemini-2.5-flash",
                CostTier.BALANCED: "gemini-2.5-pro", 
                CostTier.MID: "gemini-2.5-pro",
                CostTier.PREMIUM: "gemini-2.5-pro",
                CostTier.ENTERPRISE: "gemini-2.5-pro"
            }
        }
        
        return provider_models.get(provider, {}).get(tier, "gpt-3.5-turbo")
    
    def estimate_budget_impact(
        self, 
        monthly_tokens: int, 
        provider: LLMProvider, 
        model_name: str,
        tier: CostTier = CostTier.MID
    ) -> Decimal:
        """Estimate budget impact for monthly token usage.
        
        Args:
            monthly_tokens: Total monthly token usage
            provider: LLM provider
            model_name: Model name
            tier: Cost tier
            
        Returns:
            Decimal: Estimated monthly cost in USD
        """
        # Assume 70% prompt, 30% completion split
        prompt_tokens = int(monthly_tokens * 0.7)
        completion_tokens = int(monthly_tokens * 0.3)
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, 
            total_tokens=monthly_tokens
        )
        
        return self.calculate_cost(usage, provider, model_name, tier)


# Global instance
_cost_calculator_service: Optional[CostCalculatorService] = None


def get_cost_calculator() -> CostCalculatorService:
    """Get global cost calculator service instance."""
    global _cost_calculator_service
    if _cost_calculator_service is None:
        _cost_calculator_service = CostCalculatorService()
    return _cost_calculator_service


def calculate_cost_savings(
    usage: TokenUsage,
    current_tier: CostTier,
    target_tier: CostTier,
    provider: LLMProvider,
    model_name: str
) -> Dict[str, Any]:
    """Convenience function to calculate cost savings."""
    return get_cost_calculator().calculate_savings(usage, current_tier, target_tier, provider, model_name)


def create_cost_calculator() -> CostCalculatorService:
    """Factory function to create a cost calculator instance."""
    return CostCalculatorService()