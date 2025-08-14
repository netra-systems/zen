"""
Response-related type definitions for LLM operations.
Following Netra conventions with strong typing.
"""

from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

if TYPE_CHECKING:
    from app.schemas.llm_types import LLMProvider, TokenUsage
    from app.schemas.llm_request_types import LLMRequest
else:
    # Import the actual types for runtime resolution
    try:
        from app.schemas.llm_types import LLMProvider, TokenUsage
        from app.schemas.llm_request_types import LLMRequest
    except ImportError:
        # If imports fail, define placeholder types
        LLMProvider = 'LLMProvider'
        TokenUsage = 'TokenUsage'
        LLMRequest = 'LLMRequest'


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


class BatchLLMResponse(BaseModel):
    """Batch response from multiple LLM calls"""
    responses: List[LLMResponse]
    failed_indices: List[int] = Field(default_factory=list)
    total_time_ms: float


def _default_token_usage():
    """Create default token usage for mock responses"""
    from app.schemas.llm_types import TokenUsage
    return TokenUsage(
        prompt_tokens=10, 
        completion_tokens=20, 
        total_tokens=30
    )


class MockLLMResponse(BaseModel):
    """Mock LLM response for testing"""
    content: str
    model: str = "mock-model"
    usage: TokenUsage = Field(default_factory=_default_token_usage)
    response_time_ms: float = 100.0


class E2ETestInfrastructure(BaseModel):
    """E2E test infrastructure configuration"""
    supervisor: Any  # Agent supervisor instance
    quality_service: Any  # Quality gate service instance
    corpus_service: Any  # Corpus service instance


class E2ETestResult(BaseModel):
    """E2E test execution result"""
    success: bool
    prompt: str
    execution_time: float
    quality_passed: bool
    response_length: int
    state: Optional[Any] = None
    response: str
    error: Optional[str] = None