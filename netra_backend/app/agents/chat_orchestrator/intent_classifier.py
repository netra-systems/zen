"""Intent classification module for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Fast and accurate intent classification for routing decisions.
"""

import json
from enum import Enum
from typing import Tuple

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class IntentType(Enum):
    """Types of user intents for routing decisions."""
    TCO_ANALYSIS = "tco_analysis"
    BENCHMARKING = "benchmarking"
    PRICING_INQUIRY = "pricing"
    OPTIMIZATION_ADVICE = "optimization"
    MARKET_RESEARCH = "market_research"
    TECHNICAL_QUESTION = "technical"
    GENERAL_INQUIRY = "general"


class IntentClassifier:
    """Classifies user intent with confidence scoring."""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.classification_model = "triage_llm"  # Tier 1 fast model
    
    async def classify(self, context: ExecutionContext) -> Tuple[IntentType, float]:
        """Classify user intent and assess confidence level."""
        prompt = self._build_classification_prompt(context)
        response = await self.llm_manager.ask_llm(prompt, self.classification_model)
        return self._parse_classification_response(response)
    
    def _build_classification_prompt(self, context: ExecutionContext) -> str:
        """Build prompt for intent classification."""
        user_request = self._extract_user_request(context)
        categories = self._get_category_descriptions()
        return f"""Classify this request into one category:
{categories}

User request: {user_request}

Respond in JSON: {{"intent": "category", "confidence": 0.X}}"""
    
    def _extract_user_request(self, context: ExecutionContext) -> str:
        """Extract user request from context."""
        if context.state and context.state.user_request:
            return context.state.user_request
        return ""
    
    def _get_category_descriptions(self) -> str:
        """Get formatted category descriptions."""
        categories = [
            "- tco_analysis: Total Cost of Ownership calculations",
            "- benchmarking: Performance comparisons",
            "- pricing: Pricing inquiries",
            "- optimization: Optimization advice",
            "- market_research: Market analysis",
            "- technical: Technical questions",
            "- general: General inquiries"
        ]
        return "\n".join(categories)
    
    def _parse_classification_response(self, response: str) -> Tuple[IntentType, float]:
        """Parse intent classification response."""
        try:
            data = json.loads(response)
            intent = self._extract_intent(data)
            confidence = self._extract_confidence(data)
            return intent, confidence
        except (json.JSONDecodeError, ValueError) as e:
            return self._handle_parse_error(response, e)
    
    def _extract_intent(self, data: dict) -> IntentType:
        """Extract intent from parsed data."""
        intent_str = data.get("intent", "general")
        try:
            return IntentType(intent_str)
        except ValueError:
            return IntentType.GENERAL_INQUIRY
    
    def _extract_confidence(self, data: dict) -> float:
        """Extract confidence from parsed data."""
        confidence = data.get("confidence", 0.5)
        return max(0.0, min(1.0, float(confidence)))
    
    def _handle_parse_error(self, response: str, error: Exception) -> Tuple[IntentType, float]:
        """Handle parsing errors gracefully."""
        logger.warning(f"Failed to parse intent response: {error}")
        logger.debug(f"Response was: {response}")
        return IntentType.GENERAL_INQUIRY, 0.5