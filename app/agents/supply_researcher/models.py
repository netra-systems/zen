"""
Supply Researcher Models

Data models and enums for supply research operations.
Maintains type safety under 300-line limit.
"""

from typing import Dict, List, Any
from enum import Enum


class ResearchType(Enum):
    PRICING = "pricing"
    CAPABILITIES = "capabilities"
    AVAILABILITY = "availability"
    MARKET_OVERVIEW = "market_overview"
    NEW_MODEL = "new_model"
    DEPRECATION = "deprecation"


class ProviderPatterns:
    """Provider patterns for model identification"""
    
    @staticmethod
    def get_patterns() -> Dict[str, List[str]]:
        """Get provider patterns for extraction"""
        return {
            "openai": ["gpt", "davinci", "curie", "babbage", "ada"],
            "anthropic": ["claude"],
            "google": ["gemini", "palm", "bard"],
            "mistral": ["mistral", "mixtral"],
            "cohere": ["command", "generate"],
            "ai21": ["jurassic", "j2"]
        }