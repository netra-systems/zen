"""Model cascading for CLQT optimization in NACIS.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Optimizes cost-latency-quality-throughput through tiered model routing.
"""

import os
from enum import Enum
from typing import Dict


class ModelTier(Enum):
    """Model tiers for CLQT optimization."""
    TIER1 = "fast"  # Intent classification, simple tasks
    TIER2 = "balanced"  # Research, extraction, summarization
    TIER3 = "powerful"  # Complex analysis, final synthesis


class ModelCascade:
    """Manages model cascading for optimal performance."""
    
    def __init__(self):
        self._init_model_tiers()
        self._init_task_mappings()
    
    def _init_model_tiers(self) -> None:
        """Initialize model tier configurations."""
        # Use NACIS-specific env vars if available, fallback to defaults
        self.model_tiers = {
            ModelTier.TIER1: os.getenv("NACIS_TIER1_MODEL", "triage_llm"),
            ModelTier.TIER2: os.getenv("NACIS_TIER2_MODEL", "default_llm"),
            ModelTier.TIER3: os.getenv("NACIS_TIER3_MODEL", "quality_llm"),
        }
    
    def _init_task_mappings(self) -> None:
        """Initialize task to model tier mappings."""
        self.task_model_mapping = {
            "intent_classification": ModelTier.TIER1,
            "research": ModelTier.TIER2,
            "extraction": ModelTier.TIER2,
            "summarization": ModelTier.TIER2,
            "analysis": ModelTier.TIER3,
            "synthesis": ModelTier.TIER3,
            "validation": ModelTier.TIER2,
        }
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get optimal model for task type."""
        tier = self._determine_tier(task_type)
        return self.model_tiers.get(tier, "default_llm")
    
    def _determine_tier(self, task_type: str) -> ModelTier:
        """Determine model tier for task."""
        task_lower = task_type.lower()
        for task_key, tier in self.task_model_mapping.items():
            if task_key in task_lower:
                return tier
        return ModelTier.TIER2  # Default to balanced
    
    def get_model_for_agent(self, agent_name: str, action: str) -> str:
        """Get model for specific agent action."""
        task_type = self._infer_task_type(agent_name, action)
        return self.get_model_for_task(task_type)
    
    def _infer_task_type(self, agent_name: str, action: str) -> str:
        """Infer task type from agent and action."""
        if "research" in action.lower():
            return "research"
        elif "analysis" in action.lower():
            return "analysis"
        elif "validate" in action.lower():
            return "validation"
        return "extraction"
    
    def estimate_cost_tier(self, tier: ModelTier) -> float:
        """Estimate relative cost for model tier."""
        cost_map = {
            ModelTier.TIER1: 0.1,  # Cheapest
            ModelTier.TIER2: 0.5,  # Medium
            ModelTier.TIER3: 1.0,  # Most expensive
        }
        return cost_map.get(tier, 0.5)