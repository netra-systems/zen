"""Centralized Pricing Configuration for Billing System.

This module provides a single source of truth for all pricing configurations,
eliminating duplication across billing services.

Business Value Justification (BVJ):
- Segment: All tiers (pricing affects entire billing pipeline)
- Business Goal: Consistent pricing and easier management
- Value Impact: Eliminates pricing discrepancies and simplifies updates
- Strategic Impact: Central pricing control for revenue optimization
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, Any
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.schemas.UserPlan import PlanTier


class ModelProvider(Enum):
    """LLM Model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class PricingConfig:
    """Centralized pricing configuration for all billing services."""
    
    def __init__(self):
        """Initialize pricing configuration."""
        self._initialize_tier_pricing()
        self._initialize_model_pricing()
        self._initialize_usage_pricing()
        self._initialize_tax_rates()
    
    def _initialize_tier_pricing(self) -> None:
        """Initialize plan tier base pricing."""
        self.tier_base_pricing = {
            PlanTier.FREE: Decimal('0'),
            PlanTier.PRO: Decimal('29'),
            PlanTier.ENTERPRISE: Decimal('299'),
            PlanTier.DEVELOPER: Decimal('0'),  # Internal use
        }
        
        # Usage-based pricing by tier
        self.tier_usage_pricing = {
            PlanTier.FREE: {
                "api_calls": Decimal('0.0'),
                "ai_operations": Decimal('0.0'),
                "data_storage": Decimal('0.0'),
                "llm_tokens": Decimal('0.0'),
                "agent_execution": Decimal('0.0'),
                "websocket_connection": Decimal('0.0'),
            },
            PlanTier.PRO: {
                "api_calls": Decimal('0.001'),
                "ai_operations": Decimal('0.01'),
                "data_storage": Decimal('0.1'),
                "llm_tokens": Decimal('0.00002'),
                "agent_execution": Decimal('0.005'),
                "websocket_connection": Decimal('0.0001'),
            },
            PlanTier.ENTERPRISE: {
                "api_calls": Decimal('0.0005'),
                "ai_operations": Decimal('0.005'),
                "data_storage": Decimal('0.05'),
                "llm_tokens": Decimal('0.00001'),
                "agent_execution": Decimal('0.003'),
                "websocket_connection": Decimal('0.00005'),
            },
            PlanTier.DEVELOPER: {
                "api_calls": Decimal('0.0'),
                "ai_operations": Decimal('0.0'),
                "data_storage": Decimal('0.0'),
                "llm_tokens": Decimal('0.0'),
                "agent_execution": Decimal('0.0'),
                "websocket_connection": Decimal('0.0'),
            }
        }
    
    def _initialize_model_pricing(self) -> None:
        """Initialize LLM model pricing per 1K tokens."""
        self.model_pricing = {
            # OpenAI Models
            LLMModel.GEMINI_2_5_FLASH.value: {
                "provider": ModelProvider.OPENAI,
                "input": Decimal("0.03"),
                "output": Decimal("0.06"),
                "tier": "premium"
            },
            LLMModel.GEMINI_2_5_FLASH.value: {
                "provider": ModelProvider.OPENAI,
                "input": Decimal("0.01"),
                "output": Decimal("0.03"),
                "tier": "balanced"
            },
            LLMModel.GEMINI_2_5_FLASH.value: {
                "provider": ModelProvider.OPENAI,
                "input": Decimal("0.0015"),
                "output": Decimal("0.002"),
                "tier": "economy"
            },
            "gpt-3.5-turbo-instruct": {
                "provider": ModelProvider.OPENAI,
                "input": Decimal("0.0015"),
                "output": Decimal("0.002"),
                "tier": "economy"
            },
            
            # Anthropic Models
            LLMModel.GEMINI_2_5_FLASH.value: {
                "provider": ModelProvider.ANTHROPIC,
                "input": Decimal("0.015"),
                "output": Decimal("0.075"),
                "tier": "premium"
            },
            "claude-3.5-sonnet": {
                "provider": ModelProvider.ANTHROPIC,
                "input": Decimal("0.003"),
                "output": Decimal("0.015"),
                "tier": "balanced"
            },
            LLMModel.GEMINI_2_5_FLASH.value: {
                "provider": ModelProvider.ANTHROPIC,
                "input": Decimal("0.003"),
                "output": Decimal("0.015"),
                "tier": "balanced"
            },
            "claude-3-haiku": {
                "provider": ModelProvider.ANTHROPIC,
                "input": Decimal("0.00025"),
                "output": Decimal("0.00125"),
                "tier": "economy"
            },
            "claude-instant": {
                "provider": ModelProvider.ANTHROPIC,
                "input": Decimal("0.0008"),
                "output": Decimal("0.0024"),
                "tier": "economy"
            },
            
            # Google Models
            "gemini-2.5-pro": {
                "provider": ModelProvider.GOOGLE,
                "input": Decimal("0.0035"),
                "output": Decimal("0.0105"),
                "tier": "balanced"
            },
            "gemini-2.5-flash": {
                "provider": ModelProvider.GOOGLE,
                "input": Decimal("0.000075"),
                "output": Decimal("0.0003"),
                "tier": "economy"
            },
            "gemini-pro": {
                "provider": ModelProvider.GOOGLE,
                "input": Decimal("0.0005"),
                "output": Decimal("0.0015"),
                "tier": "economy"
            },
            "palm-2": {
                "provider": ModelProvider.GOOGLE,
                "input": Decimal("0.0005"),
                "output": Decimal("0.0015"),
                "tier": "economy"
            },
            
            # Default for unknown models
            "default": {
                "provider": ModelProvider.OPENAI,
                "input": Decimal("0.001"),
                "output": Decimal("0.002"),
                "tier": "economy"
            }
        }
    
    def _initialize_usage_pricing(self) -> None:
        """Initialize general usage pricing."""
        self.usage_base_pricing = {
            "api_call": Decimal("0.001"),
            "llm_tokens": Decimal("0.00002"),
            "storage": Decimal("0.023"),  # per GB-month
            "compute": Decimal("0.10"),   # per CPU hour
            "bandwidth": Decimal("0.09"), # per GB
            "websocket_connection": Decimal("0.0001"), # per connection-minute
            "agent_execution": Decimal("0.005")  # per execution
        }
    
    def _initialize_tax_rates(self) -> None:
        """Initialize tax rates by region."""
        self.tax_rates = {
            "default": Decimal("0.08"),     # 8% default
            "enterprise": Decimal("0.00"),  # No tax for enterprise
            "eu": Decimal("0.20"),          # 20% VAT
            "canada": Decimal("0.13"),      # 13% HST
            "us": Decimal("0.08"),          # 8% average US sales tax
        }
    
    # Public API Methods
    
    def get_tier_base_price(self, tier: PlanTier) -> Decimal:
        """Get base monthly price for a tier."""
        return self.tier_base_pricing.get(tier, Decimal('0'))
    
    def get_tier_usage_pricing(self, tier: PlanTier) -> Dict[str, Decimal]:
        """Get usage pricing for a tier."""
        return self.tier_usage_pricing.get(tier, self.tier_usage_pricing[PlanTier.FREE]).copy()
    
    def get_model_pricing(self, model: str) -> Dict[str, Any]:
        """Get pricing for a specific model."""
        return self.model_pricing.get(model, self.model_pricing["default"]).copy()
    
    def get_all_model_pricing(self) -> Dict[str, Dict[str, Any]]:
        """Get pricing for all models."""
        return {k: v.copy() for k, v in self.model_pricing.items()}
    
    def get_usage_base_pricing(self) -> Dict[str, Decimal]:
        """Get base usage pricing."""
        return self.usage_base_pricing.copy()
    
    def get_tax_rate(self, region: str = "default") -> Decimal:
        """Get tax rate for a region."""
        return self.tax_rates.get(region, self.tax_rates["default"])
    
    def get_all_tax_rates(self) -> Dict[str, Decimal]:
        """Get all tax rates."""
        return self.tax_rates.copy()
    
    def update_tier_pricing(self, tier: PlanTier, base_price: Decimal = None, 
                           usage_pricing: Dict[str, Decimal] = None) -> None:
        """Update pricing for a tier."""
        if base_price is not None:
            self.tier_base_pricing[tier] = base_price
        
        if usage_pricing:
            if tier not in self.tier_usage_pricing:
                self.tier_usage_pricing[tier] = {}
            self.tier_usage_pricing[tier].update(usage_pricing)
    
    def update_model_pricing(self, model: str, input_price: Decimal, 
                           output_price: Decimal, provider: ModelProvider = None,
                           tier: str = "economy") -> None:
        """Update pricing for a model."""
        self.model_pricing[model] = {
            "provider": provider or ModelProvider.OPENAI,
            "input": input_price,
            "output": output_price,
            "tier": tier
        }
    
    def update_tax_rate(self, region: str, rate: Decimal) -> None:
        """Update tax rate for a region."""
        self.tax_rates[region] = rate
    
    def get_supported_tiers(self) -> list[PlanTier]:
        """Get list of supported plan tiers."""
        return list(self.tier_base_pricing.keys())
    
    def get_supported_models(self) -> list[str]:
        """Get list of supported models (excluding default)."""
        return [model for model in self.model_pricing.keys() if model != "default"]
    
    def get_models_by_provider(self, provider: ModelProvider) -> list[str]:
        """Get models for a specific provider."""
        return [
            model for model, config in self.model_pricing.items()
            if config.get("provider") == provider and model != "default"
        ]
    
    def get_models_by_tier(self, tier: str) -> list[str]:
        """Get models by cost tier (economy, balanced, premium)."""
        return [
            model for model, config in self.model_pricing.items()
            if config.get("tier") == tier and model != "default"
        ]


# Global instance - single source of truth
pricing_config = PricingConfig()


# Convenience functions for backward compatibility
def get_tier_base_price(tier: PlanTier) -> Decimal:
    """Get base monthly price for a tier."""
    return pricing_config.get_tier_base_price(tier)


def get_tier_usage_pricing(tier: PlanTier) -> Dict[str, Decimal]:
    """Get usage pricing for a tier."""
    return pricing_config.get_tier_usage_pricing(tier)


def get_model_pricing(model: str) -> Dict[str, Any]:
    """Get pricing for a specific model."""
    return pricing_config.get_model_pricing(model)


def get_tax_rate(region: str = "default") -> Decimal:
    """Get tax rate for a region."""
    return pricing_config.get_tax_rate(region)