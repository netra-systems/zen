"""Data models for DataSubAgent."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from netra_backend.app.core.serialization.unified_json_handler import (
    parse_dict_field,
    parse_string_list_field,
)

# Import shared models to avoid duplication
from netra_backend.app.schemas.shared_types import (
    AnomalyDetail,
    AnomalyDetectionResponse,
    AnomalySeverity,
    CorrelationAnalysis,
    DataAnalysisResponse,
    DataQualityMetrics,
    PerformanceMetrics,
    UsagePattern,
)

# Shared models are now imported from app.schemas.shared_types


# Shared models are now imported from app.schemas.shared_types


class BatchProcessingResult(BaseModel):
    """Result of batch processing operations."""
    total_items: int = Field(ge=0)
    successful_items: int = Field(ge=0)
    failed_items: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=100.0)
    processing_time_ms: float = Field(ge=0.0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    @field_validator('success_rate')
    @classmethod
    def calculate_success_rate(cls, v: float) -> float:
        """Validate success rate is between 0 and 100."""
        if not 0.0 <= v <= 100.0:
            raise ValueError('Success rate must be between 0 and 100')
        return v


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    hit_rate: float = Field(ge=0.0, le=100.0)
    miss_rate: float = Field(ge=0.0, le=100.0)
    total_requests: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    cache_misses: int = Field(ge=0)
    average_lookup_time_ms: float = Field(ge=0.0)
    
    @field_validator('miss_rate')
    @classmethod
    def calculate_miss_rate(cls, v: float) -> float:
        """Validate miss rate is between 0 and 100."""
        if not 0.0 <= v <= 100.0:
            raise ValueError('Miss rate must be between 0 and 100')
        return v


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