"""
Shared production types and classes to eliminate duplicate type definitions.
Single source of truth for production types used across multiple modules.
"""

from typing import Dict, Optional, List, AsyncGenerator, Union, Any, Literal
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC
from enum import Enum
import asyncio
from app.core.json_parsing_utils import parse_dict_field, parse_string_list_field

# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.state import DeepAgentState
    from app.llm.llm_manager import LLMManager
    from app.agents.base import BaseSubAgent
    from app.agents.tool_dispatcher import ToolDispatcher

# Type aliases for common patterns to replace Any usage
PrimitiveType = Union[str, int, float, bool, None]
JsonCompatibleDict = Dict[str, PrimitiveType]
NestedJsonDict = Dict[str, Union[PrimitiveType, List[PrimitiveType], Dict[str, PrimitiveType]]]
ExecutionResult = Union[JsonCompatibleDict, List[JsonCompatibleDict], str, bool, None]
ToolParameters = Dict[str, Union[str, int, float, bool]]
ToolResult = Dict[str, Union[str, int, float, bool, List[str]]]
AgentState = 'DeepAgentState'  # Forward reference
# AgentExecutionResult moved to strict_types.py to avoid circular imports


class AgentStatus(str, Enum):
    """Standard agent status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


class ProcessingResult(BaseModel):
    """Standard processing result structure"""
    status: str = Field(..., description="Processing status")
    data: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Result data")
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Processing metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Processing timestamp")


class ErrorContext(BaseModel):
    """Standard error context for consistent error handling across all modules"""
    # Core identifiers  
    trace_id: str = Field(..., description="Unique trace identifier")
    operation: str = Field(..., description="Operation being performed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    
    # Additional context for compatibility with existing code
    correlation_id: Optional[str] = Field(default=None, description="Correlation identifier")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # Agent-specific context
    agent_name: Optional[str] = Field(default=None, description="Agent name")
    operation_name: Optional[str] = Field(default=None, description="Operation name")
    run_id: Optional[str] = Field(default=None, description="Run identifier")
    retry_count: int = Field(default=0, description="Retry count")
    max_retries: int = Field(default=3, description="Maximum retries")
    
    # General context data
    details: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Error details")
    additional_data: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Additional context data")
    
    # Compatibility fields for existing code
    component: Optional[str] = Field(default=None, description="Component name")
    severity: Optional[str] = Field(default=None, description="Error severity")
    error_code: Optional[str] = Field(default=None, description="Error code")


class BaseAgentInterface(ABC):
    """Base interface for agent implementations to ensure consistency"""
    
    @abstractmethod
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher') -> None:
        pass
    
    @abstractmethod
    async def execute(self, state: 'DeepAgentState', session_id: str, **kwargs) -> Any:
        pass
    
    @abstractmethod
    def _init_components(self) -> None:
        pass


class ToolExecutionContext(BaseModel):
    """Context for tool execution with permissions"""
    user_id: str = Field(..., description="User identifier")
    tool_name: str = Field(..., description="Tool being executed")
    requested_action: str = Field(..., description="Requested action")
    user_plan: str = Field(..., description="User subscription plan")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class CacheKey(BaseModel):
    """Standard cache key structure"""
    prefix: str = Field(..., description="Cache key prefix")
    identifier: str = Field(..., description="Unique identifier")
    version: str = Field(default="v1", description="Cache version")
    
    def to_string(self) -> str:
        """Convert to cache key string"""
        return f"{self.prefix}:{self.version}:{self.identifier}"


class ServiceHealth(BaseModel):
    """Standard service health check response"""
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Health metrics")


class ApiResponse(BaseModel):
    """Standard API response structure"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Any] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class EventContext(BaseModel):
    """Context for event processing"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    source: str = Field(..., description="Event source")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: Dict[str, Any] = Field(..., description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


# Common constants and utilities
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_TIMEOUT = 30  # 30 seconds
DEFAULT_RETRY_ATTEMPTS = 3

# =============================================================================
# CONSOLIDATED TYPE DEFINITIONS - SINGLE SOURCE OF TRUTH
# =============================================================================

class RetryConfig(BaseModel):
    """Centralized retry configuration for all components."""
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    base_delay: float = Field(default=1.0, description="Base delay between retries")
    max_delay: float = Field(default=60.0, description="Maximum delay between retries")
    backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")
    timeout_seconds: int = Field(default=600, description="Operation timeout")
    jitter: bool = Field(default=True, description="Add jitter to delays")


class ValidationResult(BaseModel):
    """Centralized validation result for all validation operations."""
    is_valid: bool = Field(..., description="Whether input passed validation")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    sanitized_value: Optional[str] = Field(default=None, description="Sanitized input value")
    confidence_score: float = Field(default=1.0, description="Confidence in validation (0-1)")
    validated_input: Optional[Any] = Field(default=None, description="Validated input object")
    threats_detected: List[str] = Field(default_factory=list, description="Security threats found")


class BaseAgentConfig(BaseModel):
    """Base agent configuration for all agents."""
    retry: RetryConfig = Field(default_factory=RetryConfig)
    default_timeout: float = Field(default=30.0, description="Default operation timeout")
    max_concurrent_operations: int = Field(default=10, description="Max concurrent operations")
    batch_size: int = Field(default=100, description="Default batch processing size")
    failure_threshold: int = Field(default=3, description="Circuit breaker failure threshold")
    reset_timeout: float = Field(default=30.0, description="Circuit breaker reset timeout")


class WebSocketConnectionConfig(BaseModel):
    """Configuration for WebSocket connections."""
    max_attempts: int = Field(default=10, description="Maximum reconnection attempts")
    initial_delay: float = Field(default=1.0, description="Initial reconnection delay")
    max_delay: float = Field(default=60.0, description="Maximum reconnection delay")
    backoff_multiplier: float = Field(default=2.0, description="Backoff multiplier")
    timeout_seconds: int = Field(default=30, description="Connection timeout")
    heartbeat_interval: float = Field(default=30.0, description="Heartbeat interval")
    max_missed_heartbeats: int = Field(default=3, description="Max missed heartbeats")


# Type aliases for common patterns
AgentConfigDict = Dict[str, Any]
ProcessingContextDict = Dict[str, Any]
MetadataDict = Dict[str, Any]


# =============================================================================
# SHARED DATA ANALYSIS TYPES - SINGLE SOURCE OF TRUTH
# =============================================================================

class AnomalySeverity(str, Enum):
    """Anomaly severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyDetail(BaseModel):
    """Details of a detected anomaly."""
    timestamp: datetime
    metric_name: str
    actual_value: float
    expected_value: float
    deviation_percentage: float
    z_score: float
    severity: AnomalySeverity
    description: Optional[str] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics data."""
    latency_p50: float = Field(ge=0.0)
    latency_p95: float = Field(ge=0.0)
    latency_p99: float = Field(ge=0.0)
    throughput_avg: float = Field(ge=0.0)
    throughput_peak: float = Field(ge=0.0)
    error_rate: float = Field(ge=0.0, le=100.0)
    availability: float = Field(ge=0.0, le=100.0, default=99.9)


class CorrelationAnalysis(BaseModel):
    """Correlation analysis results."""
    metric_pairs: List[Dict[str, str]] = Field(default_factory=list)
    correlation_coefficients: List[float] = Field(default_factory=list)
    significance_levels: List[float] = Field(default_factory=list)
    strongest_correlation: Optional[Dict[str, Any]] = None
    weakest_correlation: Optional[Dict[str, Any]] = None


class UsagePattern(BaseModel):
    """Usage pattern analysis."""
    pattern_type: Literal["seasonal", "trending", "cyclical", "irregular"]
    peak_hours: List[int] = Field(default_factory=list)
    low_hours: List[int] = Field(default_factory=list)
    trend_direction: Literal["increasing", "decreasing", "stable"]
    confidence: float = Field(ge=0.0, le=1.0)
    seasonality_detected: bool = False


class DataQualityMetrics(BaseModel):
    """Data quality assessment."""
    completeness: float = Field(ge=0.0, le=100.0)
    accuracy: float = Field(ge=0.0, le=100.0)
    consistency: float = Field(ge=0.0, le=100.0)
    timeliness: float = Field(ge=0.0, le=100.0)
    missing_values_count: int = Field(ge=0)
    duplicate_records_count: int = Field(ge=0)
    overall_score: float = Field(ge=0.0, le=100.0)


class DataAnalysisResponse(BaseModel):
    """Structured response for data analysis operations."""
    query: str = Field(description="The analysis query performed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    insights: Dict[str, Any] = Field(default_factory=dict, description="Key insights from analysis")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the analysis")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    error: Optional[str] = Field(default=None, description="Error message if any")
    execution_time_ms: float = Field(default=0.0, description="Query execution time")
    affected_rows: int = Field(default=0, description="Number of rows processed")
    
    @field_validator('insights', mode='before')
    @classmethod
    def parse_insights(cls, v: Any) -> Dict[str, Any]:
        """Parse insights field from JSON string if needed"""
        return parse_dict_field(v)
    
    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v: Any) -> Dict[str, Any]:
        """Parse metadata field from JSON string if needed"""
        return parse_dict_field(v)
    
    @field_validator('recommendations', mode='before')
    @classmethod
    def parse_recommendations(cls, v: Any) -> List[str]:
        """Parse recommendations field, converting dicts to strings"""
        return parse_string_list_field(v)
    
    # Enhanced structured fields
    performance_metrics: Optional[PerformanceMetrics] = None
    correlation_analysis: Optional[CorrelationAnalysis] = None
    usage_patterns: List[UsagePattern] = Field(default_factory=list)
    data_quality: Optional[DataQualityMetrics] = None
    anomaly_detection: Optional['AnomalyDetectionResponse'] = None
    
    @field_validator('execution_time_ms')
    @classmethod
    def validate_execution_time(cls, v: float) -> float:
        """Validate execution time is non-negative."""
        if v < 0:
            raise ValueError('Execution time must be non-negative')
        return v
    
    @field_validator('affected_rows')
    @classmethod
    def validate_affected_rows(cls, v: int) -> int:
        """Validate affected rows is non-negative."""
        if v < 0:
            raise ValueError('Affected rows must be non-negative')
        return v


class AnomalyDetectionResponse(BaseModel):
    """Structured response for anomaly detection."""
    anomalies_detected: bool = Field(default=False)
    anomaly_count: int = Field(default=0)
    anomaly_details: List[AnomalyDetail] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    severity: AnomalySeverity = AnomalySeverity.LOW
    recommended_actions: List[str] = Field(default_factory=list)
    analysis_period: Dict[str, datetime] = Field(default_factory=dict)
    threshold_used: float = Field(default=2.5)
    
    @field_validator('anomaly_count')
    @classmethod
    def validate_anomaly_count(cls, v: int) -> int:
        """Validate anomaly count is non-negative."""
        if v < 0:
            raise ValueError('Anomaly count must be non-negative')
        return v