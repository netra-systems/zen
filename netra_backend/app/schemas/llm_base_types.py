"""
LLM Base Types
Basic types for LLM operations that are shared across modules
"""

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel


class LLMProvider(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


class TokenUsage(BaseModel):
    """Token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0