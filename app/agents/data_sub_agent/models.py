"""Data models for DataSubAgent."""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


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
    
    # Enhanced structured fields
    performance_metrics: Optional[PerformanceMetrics] = None
    correlation_analysis: Optional[CorrelationAnalysis] = None
    usage_patterns: List[UsagePattern] = Field(default_factory=list)
    data_quality: Optional[DataQualityMetrics] = None
    anomaly_detection: Optional['AnomalyDetectionResponse'] = None
    
    @validator('execution_time_ms')
    def validate_execution_time(cls, v: float) -> float:
        """Validate execution time is non-negative."""
        if v < 0:
            raise ValueError('Execution time must be non-negative')
        return v
    
    @validator('affected_rows')
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
    
    @validator('anomaly_count')
    def validate_anomaly_count(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure anomaly count matches detected flag."""
        anomalies_detected = values.get('anomalies_detected', False)
        if anomalies_detected and v == 0:
            raise ValueError('Anomaly count must be > 0 when anomalies are detected')
        elif not anomalies_detected and v > 0:
            raise ValueError('Anomaly count must be 0 when no anomalies are detected')
        return v


class BatchProcessingResult(BaseModel):
    """Result of batch processing operations."""
    total_items: int = Field(ge=0)
    successful_items: int = Field(ge=0)
    failed_items: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=100.0)
    processing_time_ms: float = Field(ge=0.0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('success_rate', pre=True, always=True)
    def calculate_success_rate(cls, v: float, values: Dict[str, Any]) -> float:
        """Calculate success rate from successful and total items."""
        total = values.get('total_items', 0)
        successful = values.get('successful_items', 0)
        if total == 0:
            return 0.0
        return (successful / total) * 100.0


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    hit_rate: float = Field(ge=0.0, le=100.0)
    miss_rate: float = Field(ge=0.0, le=100.0)
    total_requests: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    cache_misses: int = Field(ge=0)
    average_lookup_time_ms: float = Field(ge=0.0)
    
    @validator('miss_rate', pre=True, always=True)
    def calculate_miss_rate(cls, v: float, values: Dict[str, Any]) -> float:
        """Calculate miss rate from hit rate."""
        hit_rate = values.get('hit_rate', 0.0)
        return 100.0 - hit_rate


class DataValidationResult(BaseModel):
    """Result of data validation operations."""
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    schema_compliance: float = Field(ge=0.0, le=100.0, default=100.0)
    data_types_valid: bool = True
    constraints_satisfied: bool = True
    validation_time_ms: float = Field(ge=0.0, default=0.0)


class StreamProcessingMetrics(BaseModel):
    """Metrics for stream processing operations."""
    messages_processed: int = Field(ge=0)
    processing_rate_per_second: float = Field(ge=0.0)
    average_latency_ms: float = Field(ge=0.0)
    error_count: int = Field(ge=0)
    backpressure_events: int = Field(ge=0)
    buffer_utilization: float = Field(ge=0.0, le=100.0)
    uptime_percentage: float = Field(ge=0.0, le=100.0)


# Type aliases for better readability
AnalysisResult = Union[DataAnalysisResponse, AnomalyDetectionResponse, BatchProcessingResult]
MetricsResult = Union[PerformanceMetrics, CacheMetrics, StreamProcessingMetrics]
ValidationResult = Union[DataValidationResult, Dict[str, Any]]