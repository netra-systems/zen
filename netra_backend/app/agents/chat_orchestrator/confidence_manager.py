"""Confidence management for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures appropriate confidence thresholds for cache decisions.
"""

import hashlib
from enum import Enum

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType


class ConfidenceLevel(Enum):
    """Confidence levels for cache decisions."""
    HIGH = 0.9  # Use cache
    MEDIUM = 0.7  # Verify with quick research
    LOW = 0.5  # Full research required


class ConfidenceManager:
    """Manages confidence thresholds and cache decisions."""
    
    def __init__(self):
        self._init_confidence_thresholds()
        self._init_cache_ttl_mapping()
    
    def _init_confidence_thresholds(self) -> None:
        """Initialize confidence thresholds for different data types."""
        self.confidence_thresholds = {
            IntentType.PRICING_INQUIRY: ConfidenceLevel.HIGH.value,
            IntentType.BENCHMARKING: ConfidenceLevel.HIGH.value,
            IntentType.TCO_ANALYSIS: ConfidenceLevel.MEDIUM.value,
            IntentType.OPTIMIZATION_ADVICE: ConfidenceLevel.MEDIUM.value,
            IntentType.GENERAL_INQUIRY: ConfidenceLevel.LOW.value,
        }
    
    def _init_cache_ttl_mapping(self) -> None:
        """Initialize cache TTL mappings."""
        self.ttl_mapping = {
            IntentType.PRICING_INQUIRY: 3600,  # 1 hour - volatile
            IntentType.BENCHMARKING: 3600,  # 1 hour
            IntentType.TCO_ANALYSIS: 86400,  # 24 hours
            IntentType.OPTIMIZATION_ADVICE: 86400,  # 24 hours
            IntentType.GENERAL_INQUIRY: 604800,  # 1 week
        }
    
    def get_threshold(self, intent: IntentType) -> float:
        """Get confidence threshold for intent type."""
        return self.confidence_thresholds.get(intent, ConfidenceLevel.HIGH.value)
    
    def get_cache_ttl(self, intent: IntentType) -> int:
        """Get cache TTL for intent type."""
        return self.ttl_mapping.get(intent, 3600)
    
    def generate_cache_key(self, context: ExecutionContext, intent: IntentType) -> str:
        """Generate semantic cache key."""
        user_request = self._extract_request(context)
        key_data = f"{intent.value}:{user_request}"
        hash_value = hashlib.sha256(key_data.encode()).hexdigest()
        return hash_value[:32]
    
    def _extract_request(self, context: ExecutionContext) -> str:
        """Extract user request from context."""
        if context.state and context.state.user_request:
            return context.state.user_request
        return ""
    
    def should_cache_result(self, confidence: float, intent: IntentType) -> bool:
        """Determine if result should be cached."""
        min_confidence = ConfidenceLevel.MEDIUM.value
        volatile_intents = [IntentType.PRICING_INQUIRY, IntentType.BENCHMARKING]
        if intent in volatile_intents:
            return confidence >= ConfidenceLevel.HIGH.value
        return confidence >= min_confidence