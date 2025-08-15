"""
Core base type definitions for LLM operations.
These are foundational types with no dependencies on other LLM schema modules.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"
    VERTEXAI = "vertexai"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class LLMModel(str, Enum):
    """Available LLM models"""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    CLAUDE_35_SONNET = "claude-3.5-sonnet"
    GEMINI_PRO = "gemini-pro"
    GEMINI_ULTRA = "gemini-ultra"
    GEMINI_25_PRO = "gemini-2.5-pro"
    GEMINI_25_FLASH = "gemini-2.5-flash"
    GEMINI_20_FLASH = "gemini-2.0-flash"
    LLAMA_3_70B = "llama-3-70b"
    LLAMA_3_8B = "llama-3-8b"
    MISTRAL_LARGE = "mistral-large"
    MIXTRAL_8X7B = "mixtral-8x7b"


class LLMRole(str, Enum):
    """Message roles in LLM conversations"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class TokenUsage(BaseModel):
    """Token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: Optional[int] = None
    
    @property
    def cost_estimate(self) -> Optional[float]:
        """Estimate cost based on token usage"""
        # This would need provider-specific pricing
        return None


class LLMMessage(BaseModel):
    """Strongly typed LLM message"""
    role: LLMRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Union[str, dict]]] = None
    tool_calls: Optional[List[Dict[str, Union[str, dict]]]] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class LLMError(BaseModel):
    """Structured LLM error"""
    error_type: str  # "api", "rate_limit", "timeout", "validation", "unknown"
    message: str
    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    details: Dict[str, Any] = Field(default_factory=dict)


class LLMHealthCheck(BaseModel):
    """Health check result for LLM"""
    config_name: str
    healthy: bool
    response_time_ms: float
    last_checked: datetime
    error: Optional[str] = None


class LLMConfigInfo(BaseModel):
    """Information about LLM configuration"""
    name: str
    provider: LLMProvider
    model_name: str
    api_key_configured: bool
    generation_config: Dict[str, Any]
    enabled: bool = True


class LLMManagerStats(BaseModel):
    """Statistics for LLM Manager"""
    total_requests: int = 0
    cached_responses: int = 0
    cache_hit_rate: float = 0.0
    average_response_time_ms: float = 0.0
    active_configs: List[str] = Field(default_factory=list)
    enabled: bool = True