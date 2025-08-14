"""
Strong type definitions for LLM operations following Netra conventions.
Core types and base models.
"""

from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, ConfigDict
import uuid


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


class LLMError(BaseModel):
    """Structured LLM error"""
    error_type: str  # "api", "rate_limit", "timeout", "validation", "unknown"
    message: str
    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    details: Dict[str, Any] = Field(default_factory=dict)


T = TypeVar('T', bound=BaseModel)


class LLMInstance(ABC, Generic[T]):
    """Generic LLM instance with strong typing"""
    
    def __init__(self, config: 'LLMConfig'):
        self.config = config
        self._client: Optional[Any] = None  # Provider-specific client
        self._cache: Dict[str, 'LLMCache'] = {}
        self._metrics: LLMMetrics = LLMMetrics(
            provider=config.provider,
            model=str(config.model)
        )
    
    @abstractmethod
    async def generate(self, request: 'LLMRequest') -> 'LLMResponse':
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    async def generate_structured(
        self, 
        request: 'LLMRequest', 
        schema: 'StructuredOutputSchema',
        response_model: type[T]
    ) -> T:
        """Generate structured output matching schema"""
        pass
    
    @abstractmethod
    async def stream(self, request: 'LLMRequest') -> List['LLMStreamChunk']:
        """Stream response from LLM"""
        pass
    
    def get_metrics(self) -> LLMMetrics:
        """Get usage metrics"""
        return self._metrics
    
    def clear_cache(self) -> None:
        """Clear response cache"""
        self._cache.clear()


class LLMValidationError(Exception):
    """Validation error for LLM operations"""
    pass


class LLMHealthCheck(BaseModel):
    """Health check result for LLM"""
    healthy: bool
    provider: str
    model: str


class LLMConfigInfo(BaseModel):
    """Information about LLM configuration"""
    provider: str
    model_name: str
    api_key_configured: bool
    generation_config: 'LLMConfig'
    enabled: bool = True


class LLMManagerStats(BaseModel):
    """Statistics for LLM Manager"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0


# Import types from split modules to maintain backward compatibility
from app.schemas.llm_request_types import (
    LLMRequest,
    BatchLLMRequest,
    StructuredOutputSchema,
    LLMFunction,
    LLMTool
)

from app.schemas.llm_response_types import (
    LLMResponse,
    LLMStreamChunk,
    BatchLLMResponse,
    LLMCache,
    MockLLMResponse
)

from app.schemas.llm_config_types import (
    LLMConfig,
    LLMManagerConfig,
    CostMetrics,
    FeatureMetrics,
    CostOptimizationContext,
    LatencyMetrics,
    InfrastructureConfig,
    LatencyOptimizationContext,
    UsageMetrics,
    RateLimitConfig,
    CapacityPlanningContext,
    FunctionMetrics,
    FunctionOptimizationContext,
    ModelInfo,
    EvaluationMetrics,
    WorkloadCharacteristics,
    ModelSelectionContext,
    CacheConfiguration,
    AuditContext,
    OptimizationObjectives,
    OptimizationConstraints,
    CurrentSystemState,
    MultiObjectiveContext,
    AgentTool,
    MigrationCriteria,
    ToolMigrationContext,
    ComparisonMetrics,
    MetricsComparison,
    RollbackAnalysisContext,
    SystemInfo,
    SystemMetrics,
    DefaultContext
)

# Aliases for backward compatibility
GenerationConfig = LLMConfig  # Alias for backward compatibility
LLMCacheEntry = LLMCache  # Alias
StructuredLLMResponse = LLMResponse  # Structured responses use same base

from app.schemas.llm_response_types import (
    E2ETestInfrastructure,
    E2ETestResult
)

# Models will be rebuilt by importing the rebuilder module when needed
# This ensures proper resolution of forward references