"""
Strong type definitions for LLM operations following Netra conventions.
Main types module that aggregates and extends base types.
"""

from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from datetime import datetime, UTC
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import uuid

# Import base types (no circular dependencies)
from app.schemas.llm_base_types import (
    LLMProvider, LLMModel, LLMRole, TokenUsage, LLMMessage, 
    LLMError, LLMHealthCheck, LLMConfigInfo, LLMManagerStats
)

T = TypeVar('T', bound=BaseModel)


class LLMResponse(BaseModel):
    """Response from LLM generation"""
    content: str = Field(description="Generated content")
    provider: LLMProvider
    model: str = Field(description="Model used for generation")
    usage: Optional[TokenUsage] = Field(default=None, description="Token usage information")
    response_time_ms: float = Field(default=0.0, description="Response time in milliseconds")
    cached: bool = Field(default=False, description="Whether response was cached")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GenerationConfig(BaseModel):
    """Configuration for LLM generation operations"""
    num_traces: int = Field(default=1000, ge=1, description="Number of traces to generate")
    num_logs: Optional[int] = Field(default=None, ge=1, description="Number of logs to generate (defaults to num_traces)")
    workload_distribution: Dict[str, float] = Field(default_factory=dict, description="Distribution of workload types")
    time_window_hours: int = Field(default=24, ge=1, le=8760, description="Time window in hours")
    domain_focus: str = Field(default="general", description="Domain focus for generation")
    error_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Error rate for generation")
    corpus_id: Optional[str] = Field(default=None, description="Corpus ID to use for generation")
    batch_size: int = Field(default=100, ge=1, description="Batch size for processing")

    @property
    def effective_num_logs(self) -> int:
        """Get effective number of logs (num_logs or num_traces)"""
        return self.num_logs if self.num_logs is not None else self.num_traces


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
    health_check_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None


class LLMInstance(ABC, Generic[T]):
    """Generic LLM instance with strong typing"""
    
    def _init_client_and_cache(self) -> None:
        """Initialize client and cache components."""
        self._client: Optional[Any] = None  # Provider-specific client
        self._cache: Dict[str, 'LLMCache'] = {}
    
    def _init_metrics(self, config: 'LLMConfig') -> LLMMetrics:
        """Initialize metrics for the LLM instance."""
        return LLMMetrics(
            provider=config.provider,
            model=str(config.model)
        )
    
    def __init__(self, config: 'LLMConfig'):
        self.config = config
        self._init_client_and_cache()
        self._metrics = self._init_metrics(config)
    
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


# Note: Imports from other LLM schema modules are handled in app.llm.schemas 
# to avoid circular dependencies. This module contains only core types and interfaces.

# Aliases for backward compatibility - these will be properly defined when imported

# Context classes for different optimization scenarios
class BaseContext(BaseModel):
    """Base context for optimization scenarios"""
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class CostOptimizationContext(BaseContext):
    """Context for cost optimization scenarios"""
    current_cost: float = Field(default=0.0, description="Current cost")
    target_reduction: float = Field(default=0.3, description="Target cost reduction")

class LatencyOptimizationContext(BaseContext):
    """Context for latency optimization scenarios"""
    current_latency_ms: float = Field(default=100.0, description="Current latency in ms")
    target_latency_ms: float = Field(default=50.0, description="Target latency in ms")

class CapacityPlanningContext(BaseContext):
    """Context for capacity planning scenarios"""
    current_capacity: int = Field(default=1000, description="Current capacity")
    projected_growth: float = Field(default=1.5, description="Projected growth factor")

class FunctionOptimizationContext(BaseContext):
    """Context for function optimization scenarios"""
    function_name: str = Field(default="", description="Function to optimize")
    performance_target: str = Field(default="faster", description="Performance target")

class ModelSelectionContext(BaseContext):
    """Context for model selection scenarios"""
    use_case: str = Field(default="general", description="Use case")
    requirements: List[str] = Field(default_factory=list, description="Requirements")

class AuditContext(BaseContext):
    """Context for audit scenarios"""
    audit_type: str = Field(default="compliance", description="Type of audit")
    scope: str = Field(default="full", description="Audit scope")

class MultiObjectiveContext(BaseContext):
    """Context for multi-objective optimization"""
    objectives: List[str] = Field(default_factory=list, description="Optimization objectives")

class ToolMigrationContext(BaseContext):
    """Context for tool migration scenarios"""
    source_tool: str = Field(default="", description="Source tool")
    target_tool: str = Field(default="", description="Target tool")

class RollbackAnalysisContext(BaseContext):
    """Context for rollback analysis"""
    deployment_id: str = Field(default="", description="Deployment ID")
    issues: List[str] = Field(default_factory=list, description="Issues found")

class DefaultContext(BaseContext):
    """Default context for general scenarios"""
    scenario: str = Field(default="general", description="Scenario type")

# Metrics classes
class CostMetrics(BaseModel):
    """Metrics for cost tracking"""
    total_cost: float = Field(default=0.0)
    cost_per_request: float = Field(default=0.0)
    cost_reduction: float = Field(default=0.0)

class FeatureMetrics(BaseModel):
    """Metrics for feature tracking"""
    feature_count: int = Field(default=0)
    feature_quality: float = Field(default=0.0)

class LatencyMetrics(BaseModel):
    """Metrics for latency tracking"""
    avg_latency_ms: float = Field(default=0.0)
    p95_latency_ms: float = Field(default=0.0)
    p99_latency_ms: float = Field(default=0.0)

# E2E Test Infrastructure classes
class E2ETestInfrastructure(BaseModel):
    """Infrastructure for E2E testing"""
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    environment: str = Field(default="test")
    services: List[str] = Field(default_factory=list)

class E2ETestResult(BaseModel):
    """Result of an E2E test"""
    test_id: str
    passed: bool = Field(default=False)
    duration_ms: float = Field(default=0.0)
    error: Optional[str] = None
# through the main llm/schemas.py module