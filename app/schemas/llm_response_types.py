"""
Response-related type definitions for LLM operations.
Following Netra conventions with strong typing.
"""

from typing import Dict, Any, Optional, List, Union, ForwardRef
from datetime import datetime, UTC
from pydantic import BaseModel, Field
import uuid
from app.schemas.llm_base_types import LLMProvider, TokenUsage

# Forward reference for LLMRequest to avoid circular imports
LLMRequest = ForwardRef('LLMRequest')


class LLMResponse(BaseModel):
    """Response from LLM"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: LLMProvider
    model: str
    choices: List[Dict[str, Any]]  # Provider-specific format
    usage: TokenUsage
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = None
    hit_count: int = Field(default=0)
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchLLMResponse(BaseModel):
    """Batch response from multiple LLM calls"""
    responses: List[LLMResponse]
    failed_indices: List[int] = Field(default_factory=list)
    total_time_ms: float




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