"""
Configuration and optimization context types for LLM operations.
Following Netra conventions with strong typing.
"""

from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.llm_base_types import LLMProvider, LLMModel


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


# Optimization Context Types
class CostMetrics(BaseModel):
    """Cost metrics for optimization"""
    daily: float
    monthly: float
    per_request: float


class FeatureMetrics(BaseModel):
    """Feature performance metrics"""
    current_latency: float
    acceptable_latency: Optional[float] = None
    required_latency: Optional[float] = None
    usage_percentage: float


class CostOptimizationContext(BaseModel):
    """Context for cost optimization scenarios"""
    current_costs: CostMetrics
    features: Dict[str, FeatureMetrics]
    models_in_use: List[str]
    total_requests_daily: int


class LatencyMetrics(BaseModel):
    """Latency performance metrics"""
    p50: float
    p95: float
    p99: float


class InfrastructureConfig(BaseModel):
    """Infrastructure configuration"""
    gpu_type: str
    gpu_count: int
    memory_gb: int


class LatencyOptimizationContext(BaseModel):
    """Context for latency optimization scenarios"""
    current_latency: LatencyMetrics
    target_improvement: float
    budget_constraint: str
    infrastructure: InfrastructureConfig


class UsageMetrics(BaseModel):
    """Usage metrics for capacity planning"""
    requests_per_day: int
    peak_rps: int
    average_rps: int


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    rpm: int  # Requests per minute
    tpm: int  # Tokens per minute


class CapacityPlanningContext(BaseModel):
    """Context for capacity planning scenarios"""
    current_usage: UsageMetrics
    expected_growth: float
    rate_limits: Dict[str, RateLimitConfig]
    cost_per_1k_tokens: Dict[str, float]


class FunctionMetrics(BaseModel):
    """Function performance metrics"""
    avg_execution_time_ms: float
    memory_usage_mb: float
    success_rate: float
    daily_invocations: int


class FunctionOptimizationContext(BaseModel):
    """Context for function optimization scenarios"""
    function_name: str
    current_metrics: FunctionMetrics
    bottlenecks: List[str]
    optimization_methods_available: List[str]


class ModelInfo(BaseModel):
    """Model information"""
    primary: str
    fallback: str


class EvaluationMetrics(BaseModel):
    """Model evaluation metrics"""
    quality_threshold: float
    latency_target_ms: float
    cost_budget_daily: float


class WorkloadCharacteristics(BaseModel):
    """Workload characteristics for model selection"""
    avg_prompt_tokens: int
    avg_completion_tokens: int
    complexity: Literal["low", "medium", "high"]


class ModelSelectionContext(BaseModel):
    """Context for model selection scenarios"""
    current_models: ModelInfo
    candidate_models: List[str]
    evaluation_metrics: EvaluationMetrics
    workload_characteristics: WorkloadCharacteristics


class CacheConfiguration(BaseModel):
    """Cache configuration details"""
    name: str
    size_mb: int
    hit_rate: float
    ttl_seconds: int


class AuditContext(BaseModel):
    """Context for audit scenarios"""
    kv_cache_instances: int
    cache_configurations: List[CacheConfiguration]
    optimization_opportunities: List[str]


class OptimizationObjectives(BaseModel):
    """Multi-objective optimization targets"""
    cost_reduction: float
    latency_improvement: float
    usage_increase: float


class OptimizationConstraints(BaseModel):
    """Constraints for optimization"""
    min_quality_score: float
    max_error_rate: float
    budget_limit: float


class CurrentSystemState(BaseModel):
    """Current system state metrics"""
    daily_cost: float
    avg_latency_ms: float
    daily_requests: int


class MultiObjectiveContext(BaseModel):
    """Context for multi-objective optimization scenarios"""
    objectives: OptimizationObjectives
    constraints: OptimizationConstraints
    current_state: CurrentSystemState


class AgentTool(BaseModel):
    """Agent tool information"""
    name: str
    current_model: str
    usage_frequency: Literal["high", "medium", "low"]
    complexity: Literal["simple", "moderate", "complex"]


class MigrationCriteria(BaseModel):
    """Criteria for tool migration"""
    min_quality_improvement: float
    max_cost_increase: float
    verbosity_options: List[str]


class ToolMigrationContext(BaseModel):
    """Context for tool migration scenarios"""
    agent_tools: List[AgentTool]
    new_model: str
    migration_criteria: MigrationCriteria


class ComparisonMetrics(BaseModel):
    """Metrics for comparison"""
    quality_score: float
    cost_per_1k_tokens: float
    avg_latency_ms: float


class MetricsComparison(BaseModel):
    """Before/after metrics comparison"""
    before: ComparisonMetrics
    after: ComparisonMetrics


class RollbackAnalysisContext(BaseModel):
    """Context for rollback analysis scenarios"""
    upgrade_timestamp: str
    upgraded_model: str
    previous_model: str
    metrics_comparison: MetricsComparison
    affected_endpoints: int


class SystemInfo(BaseModel):
    """System information"""
    version: str
    environment: str
    region: str


class SystemMetrics(BaseModel):
    """System performance metrics"""
    uptime_percentage: float
    error_rate: float
    avg_response_time_ms: float


class DefaultContext(BaseModel):
    """Default context for general scenarios"""
    system_info: SystemInfo
    metrics: SystemMetrics