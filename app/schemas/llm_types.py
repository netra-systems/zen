"""
Strong type definitions for LLM operations following Netra conventions.
"""

from typing import Dict, Any, Optional, List, Union, Literal, TypeVar, Generic
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"
    VERTEXAI = "vertexai"
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


class LLMConfig(BaseModel):
    """Configuration for LLM instance"""
    provider: LLMProvider
    model: Union[LLMModel, str]  # Allow string for custom models
    api_key: Optional[str] = Field(default=None, exclude=True)  # Exclude from serialization
    api_base: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    request_timeout: int = Field(default=60, gt=0)
    retry_attempts: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, gt=0)
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    model_config = ConfigDict(extra='allow')  # Allow additional provider-specific configs


class LLMRequest(BaseModel):
    """Request to LLM"""
    messages: List[LLMMessage]
    config: Optional[LLMConfig] = None
    stream: bool = Field(default=False)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, str]]] = None
    response_format: Optional[Dict[str, str]] = None  # For structured output
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Response from LLM"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: LLMProvider
    model: str
    choices: List[Dict[str, Any]]  # Provider-specific format
    usage: TokenUsage
    created_at: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: float
    cached: bool = Field(default=False)
    finish_reason: Optional[str] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class LLMStreamChunk(BaseModel):
    """Single chunk in streaming response"""
    id: str
    delta: Dict[str, Any]
    index: int
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


class LLMCache(BaseModel):
    """Cache entry for LLM responses"""
    key: str
    request: LLMRequest
    response: LLMResponse
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    hit_count: int = Field(default=0)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class LLMMetrics(BaseModel):
    """Metrics for LLM usage"""
    provider: LLMProvider
    model: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class LLMProviderStatus(BaseModel):
    """Status of an LLM provider"""
    provider: LLMProvider
    available: bool
    health_check_time: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None


class StructuredOutputSchema(BaseModel):
    """Schema for structured output generation"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]  # JSON Schema
    strict: bool = Field(default=True)
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class LLMFunction(BaseModel):
    """Function definition for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    required: List[str] = Field(default_factory=list)


class LLMTool(BaseModel):
    """Tool definition for tool use"""
    type: Literal["function"]
    function: LLMFunction


T = TypeVar('T', bound=BaseModel)


class LLMInstance(Generic[T]):
    """Generic LLM instance with strong typing"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Optional[Any] = None  # Provider-specific client
        self._cache: Dict[str, LLMCache] = {}
        self._metrics: LLMMetrics = LLMMetrics(
            provider=config.provider,
            model=str(config.model)
        )
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM"""
        raise NotImplementedError
    
    async def generate_structured(
        self, 
        request: LLMRequest, 
        schema: StructuredOutputSchema,
        response_model: type[T]
    ) -> T:
        """Generate structured output matching schema"""
        raise NotImplementedError
    
    async def stream(self, request: LLMRequest) -> List[LLMStreamChunk]:
        """Stream response from LLM"""
        raise NotImplementedError
    
    def get_metrics(self) -> LLMMetrics:
        """Get usage metrics"""
        return self._metrics
    
    def clear_cache(self) -> None:
        """Clear response cache"""
        self._cache.clear()


class LLMManagerConfig(BaseModel):
    """Configuration for LLM Manager"""
    default_provider: LLMProvider
    default_model: Union[LLMModel, str]
    providers: Dict[LLMProvider, LLMConfig]
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600)
    max_cache_size_mb: int = Field(default=100)
    fallback_providers: List[LLMProvider] = Field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None
    concurrent_requests: int = Field(default=10, gt=0)
    health_check_interval_seconds: int = Field(default=300)


class LLMError(BaseModel):
    """Structured LLM error"""
    error_type: Literal["api", "rate_limit", "timeout", "validation", "unknown"]
    message: str
    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    details: Dict[str, Any] = Field(default_factory=dict)


# Aliases and additional types for backward compatibility
GenerationConfig = LLMConfig  # Alias for backward compatibility
LLMCacheEntry = LLMCache  # Alias
StructuredLLMResponse = LLMResponse  # Structured responses use same base


class LLMConfigInfo(BaseModel):
    """Information about LLM configuration"""
    provider: str
    model_name: str
    api_key_configured: bool
    generation_config: LLMConfig
    enabled: bool = True


class LLMManagerStats(BaseModel):
    """Statistics for LLM Manager"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0


class MockLLMResponse(BaseModel):
    """Mock response for testing"""
    content: str
    model: str = "mock"
    provider: str = "mock"


class LLMValidationError(Exception):
    """Validation error for LLM operations"""
    pass


class LLMHealthCheck(BaseModel):
    """Health check result for LLM"""
    healthy: bool
    provider: str
    model: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class BatchLLMRequest(BaseModel):
    """Batch request for multiple LLM calls"""
    requests: List[LLMRequest]
    parallel: bool = True
    max_concurrent: int = 5


class BatchLLMResponse(BaseModel):
    """Batch response from multiple LLM calls"""
    responses: List[LLMResponse]
    failed_indices: List[int] = Field(default_factory=list)
    total_time_ms: float