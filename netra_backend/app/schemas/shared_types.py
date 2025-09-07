"""Shared Types Schema Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Code Consistency - Provide shared type definitions
- Value Impact: Ensures consistent typing across all modules
- Strategic Impact: Reduces type-related bugs and improves maintainability

This module provides shared type definitions used across multiple components.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, Field

# Type alias for nested JSON structures
NestedJsonDict = Dict[str, Any]


class AgentStatus(str, Enum):
    """Status of an agent."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BackoffStrategy(str, Enum):
    """Retry backoff strategies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    RANDOM = "random"


class JitterType(str, Enum):
    """Jitter types for retry strategies."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


class CacheKey(BaseModel):
    """Cache key definition."""
    namespace: str
    key: str
    version: Optional[str] = None
    
    def full_key(self) -> str:
        """Get the full cache key."""
        parts = [self.namespace, self.key]
        if self.version:
            parts.append(self.version)
        return ":".join(parts)


class ErrorContext(BaseModel):
    """Context for error reporting."""
    operation: str
    module: Optional[str] = None
    function: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    retry_count: int = 0
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    details: Optional[Dict[str, Any]] = None
    component: Optional[str] = None
    agent_name: Optional[str] = None
    
    @staticmethod
    def generate_trace_id() -> str:
        """Generate a unique trace ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def set_request_id(request_id: str) -> None:
        """Set the request ID for the current context.
        
        This is a compatibility method for services expecting this functionality.
        In practice, request_id should be set via the instance attribute.
        """
        # This is a static method for compatibility
        # Actual request_id is stored in the instance
        pass


class EventContext(BaseModel):
    """Context for event tracking."""
    event_type: str
    timestamp: float
    source: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceMetrics(BaseModel):
    """Performance metrics."""
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    throughput: Optional[float] = None
    latency_p95: Optional[float] = None
    latency_p99: Optional[float] = None


class DataQualityMetrics(BaseModel):
    """Data quality metrics."""
    completeness: float = Field(ge=0, le=1, description="Completeness score (0-1)")
    accuracy: float = Field(ge=0, le=1, description="Accuracy score (0-1)")
    consistency: float = Field(ge=0, le=1, description="Consistency score (0-1)")
    validity: float = Field(ge=0, le=1, description="Validity score (0-1)")
    timeliness: float = Field(ge=0, le=1, description="Timeliness score (0-1)")
    total_records: int = Field(ge=0, description="Total number of records")
    valid_records: int = Field(ge=0, description="Number of valid records")


class ValidationResult(BaseModel):
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    score: Optional[float] = Field(None, ge=0, le=100, description="Validation score (0-100)")


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_type: JitterType = JitterType.EQUAL
    enabled: bool = True


class ServiceHealth(BaseModel):
    """Health status of a service."""
    service_name: str
    is_healthy: bool
    response_time_ms: float
    last_check: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class WebSocketConnectionConfig(BaseModel):
    """Configuration for WebSocket connections."""
    url: str
    timeout_seconds: float = 30.0
    reconnect_attempts: int = 3
    reconnect_delay_seconds: float = 1.0
    heartbeat_interval_seconds: float = 30.0
    max_message_size: int = 1024 * 1024  # 1MB


class AnomalyDetail(BaseModel):
    """Details of an anomaly detection."""
    metric_name: str
    value: float
    expected_value: float
    deviation: float
    severity: AnomalySeverity
    timestamp: float
    context: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionResponse(BaseModel):
    """Response from anomaly detection."""
    anomalies_detected: List[AnomalyDetail]
    total_anomalies: int
    detection_time_ms: float
    model_version: str
    confidence_threshold: float


class CorrelationAnalysis(BaseModel):
    """Results of correlation analysis."""
    metric_pairs: List[tuple]
    correlation_coefficients: List[float]
    p_values: List[float]
    significant_correlations: List[tuple]
    analysis_time_ms: float


class DataAnalysisResponse(BaseModel):
    """Response from data analysis."""
    analysis_id: str
    status: str
    results: Dict[str, Any]
    metrics: PerformanceMetrics
    created_at: float
    completed_at: Optional[float] = None


class ProcessingResult(BaseModel):
    """Result of a processing operation."""
    success: bool
    processed_items: int
    failed_items: int
    errors: List[str] = Field(default_factory=list)
    processing_time_ms: float
    output_data: Optional[Dict[str, Any]] = None


class UsagePattern(BaseModel):
    """Usage pattern analysis."""
    pattern_id: str
    pattern_type: str
    frequency: float
    confidence: float = Field(ge=0, le=1, description="Confidence score (0-1)")
    time_range: tuple
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgentConfig(BaseModel):
    """Base configuration for agents."""
    name: str
    enabled: bool = True
    timeout_seconds: float = 30.0
    max_retries: int = 3
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BaseAgentInterface(ABC):
    """Abstract interface for agents."""
    
    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """Execute the agent with given input data."""
        pass
    
    @abstractmethod
    def get_status(self) -> AgentStatus:
        """Get the current status of the agent."""
        pass


class ToolExecutionContext(BaseModel):
    """Context for tool execution."""
    tool_name: str
    user_id: str
    request_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_config: Optional[RetryConfig] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Export all types
__all__ = [
    "AgentStatus",
    "AnomalyDetail",
    "AnomalyDetectionResponse",
    "AnomalySeverity",
    "ApiResponse",
    "BackoffStrategy",
    "BaseAgentConfig", 
    "BaseAgentInterface",
    "CacheKey",
    "CorrelationAnalysis",
    "DataAnalysisResponse",
    "DataQualityMetrics",
    "ErrorContext",
    "EventContext",
    "JitterType",
    "NestedJsonDict",
    "PerformanceMetrics",
    "ProcessingResult",
    "RetryConfig",
    "ServiceHealth",
    "ToolExecutionContext",
    "UsagePattern",
    "ValidationResult",
    "WebSocketConnectionConfig",
]