"""
LLM Configuration Types
Basic types for LLM configuration
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentTool(BaseModel):
    """Agent tool configuration"""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class AuditContext(BaseModel):
    """Audit context for tracking operations"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None


class CacheConfiguration(BaseModel):
    """Cache configuration settings"""
    enabled: bool = True
    ttl_seconds: Optional[int] = 3600
    max_size: Optional[int] = 1000


class CapacityPlanningContext(BaseModel):
    """Context for capacity planning operations"""
    time_window: Optional[str] = None
    resource_type: Optional[str] = None
    metrics: Optional[List[str]] = None


class ComparisonMetrics(BaseModel):
    """Metrics for comparison operations"""
    baseline: Optional[Dict[str, Any]] = None
    current: Optional[Dict[str, Any]] = None
    threshold: Optional[float] = None


class ConfigValidationError(BaseModel):
    """Configuration validation error details"""
    field: str
    message: str
    value: Optional[Any] = None


class CostEstimationContext(BaseModel):
    """Context for cost estimation operations"""
    time_period: Optional[str] = None
    resource_units: Optional[int] = None
    pricing_model: Optional[str] = None


class ExportFormat(str, Enum):
    """Export format options"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    XLSX = "xlsx"


class LLMCapability(str, Enum):
    """LLM capability types"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"


class LLMProvider(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    GEMINI = "gemini"


class ModelEndpoint(BaseModel):
    """Model endpoint configuration"""
    url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = 30


class OptimizationContext(BaseModel):
    """Context for optimization operations"""
    target_metric: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    optimization_type: Optional[str] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics data"""
    latency_ms: Optional[float] = None
    throughput: Optional[float] = None
    error_rate: Optional[float] = None
    success_rate: Optional[float] = None


class QueryContext(BaseModel):
    """Context for query operations"""
    filters: Optional[Dict[str, Any]] = None
    sort_order: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class RecommendationEngine(BaseModel):
    """Recommendation engine configuration"""
    algorithm: str
    parameters: Optional[Dict[str, Any]] = None
    confidence_threshold: Optional[float] = 0.8


class ResourceConfiguration(BaseModel):
    """Resource configuration settings"""
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    disk_limit: Optional[str] = None


class UsageAnalysisContext(BaseModel):
    """Context for usage analysis operations"""
    time_range: Optional[str] = None
    user_segments: Optional[List[str]] = None
    metrics_to_analyze: Optional[List[str]] = None


class WorkflowContext(BaseModel):
    """Context for workflow operations"""
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


class UsageMetrics(BaseModel):
    """Usage metrics data"""
    total_requests: Optional[int] = None
    successful_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    average_response_time: Optional[float] = None


class WorkloadCharacteristics(BaseModel):
    """Workload characteristics"""
    workload_type: Optional[str] = None
    peak_usage: Optional[Dict[str, Any]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    scaling_patterns: Optional[List[Dict[str, Any]]] = None