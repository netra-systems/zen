"""Confidence management for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Manages confidence thresholds and cache management for intelligent routing decisions.
"""

import hashlib
from enum import Enum
from typing import Dict, Any

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType


class ConfidenceLevel(Enum):
    """Confidence level thresholds for execution decisions."""
    LOW = 0.5
    MEDIUM = 0.7
    HIGH = 0.85
    VERY_HIGH = 0.95


class ConfidenceManager:
    """Manages confidence thresholds and caching decisions."""
    
    def __init__(self):
        self._intent_thresholds = self._init_intent_thresholds()
        self._cache_ttl_mapping = self._init_cache_ttl_mapping()
    
    def _init_intent_thresholds(self) -> Dict[IntentType, float]:
        """Initialize confidence thresholds for different intents."""
        return {
            IntentType.TCO_ANALYSIS: ConfidenceLevel.HIGH.value,
            IntentType.BENCHMARKING: ConfidenceLevel.HIGH.value,
            IntentType.PRICING_INQUIRY: ConfidenceLevel.MEDIUM.value,
            IntentType.OPTIMIZATION_ADVICE: ConfidenceLevel.HIGH.value,
            IntentType.MARKET_RESEARCH: ConfidenceLevel.MEDIUM.value,
            IntentType.TECHNICAL_QUESTION: ConfidenceLevel.MEDIUM.value,
            IntentType.GENERAL_INQUIRY: ConfidenceLevel.LOW.value,
        }
    
    def _init_cache_ttl_mapping(self) -> Dict[IntentType, int]:
        """Initialize cache TTL (time-to-live) for different intents."""
        return {
            IntentType.TCO_ANALYSIS: 1800,  # 30 minutes
            IntentType.BENCHMARKING: 3600,  # 1 hour
            IntentType.PRICING_INQUIRY: 900,  # 15 minutes (pricing changes frequently)
            IntentType.OPTIMIZATION_ADVICE: 1800,  # 30 minutes
            IntentType.MARKET_RESEARCH: 7200,  # 2 hours
            IntentType.TECHNICAL_QUESTION: 3600,  # 1 hour
            IntentType.GENERAL_INQUIRY: 1800,  # 30 minutes
        }
    
    def get_threshold(self, intent: IntentType) -> float:
        """Get confidence threshold for given intent."""
        return self._intent_thresholds.get(intent, ConfidenceLevel.MEDIUM.value)
    
    def get_cache_ttl(self, intent: IntentType) -> int:
        """Get cache TTL for given intent."""
        return self._cache_ttl_mapping.get(intent, 1800)  # Default 30 minutes
    
    def generate_cache_key(self, context: ExecutionContext, intent: IntentType) -> str:
        """Generate cache key for context and intent."""
        # Create a stable key from context components
        key_components = [
            context.state.user_request if context.state and context.state.user_request else "",
            intent.value,
            str(context.user_id) if hasattr(context, 'user_id') else "unknown"
        ]
        
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def should_escalate(self, confidence: float, intent: IntentType) -> bool:
        """Determine if query should be escalated to higher tier model."""
        threshold = self.get_threshold(intent)
        return confidence < threshold
    
    def get_quality_requirement(self, intent: IntentType) -> float:
        """Get quality requirement based on intent criticality."""
        quality_mapping = {
            IntentType.TCO_ANALYSIS: 0.9,  # High accuracy required
            IntentType.BENCHMARKING: 0.85,  # High accuracy required
            IntentType.PRICING_INQUIRY: 0.8,  # Accuracy important
            IntentType.OPTIMIZATION_ADVICE: 0.85,  # High accuracy required
            IntentType.MARKET_RESEARCH: 0.75,  # Moderate accuracy
            IntentType.TECHNICAL_QUESTION: 0.8,  # Accuracy important
            IntentType.GENERAL_INQUIRY: 0.7,  # Basic accuracy
        }
        return quality_mapping.get(intent, 0.75)