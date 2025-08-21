"""Metrics schema definitions for corpus operations and monitoring"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Union
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics collected"""
    GENERATION_TIME = "generation_time"
    SUCCESS_RATE = "success_rate"
    QUALITY_SCORE = "quality_score"
    RESOURCE_USAGE = "resource_usage"
    VALIDATION_RESULT = "validation_result"
    THROUGHPUT = "throughput"


class ResourceType(str, Enum):
    """Resource types monitored"""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"


class ExportFormat(str, Enum):
    """Supported export formats"""
    JSON = "json"
    PROMETHEUS = "prometheus"
    CSV = "csv"
    INFLUX = "influx"


class CorpusMetric(BaseModel):
    """Individual corpus operation metric"""
    metric_id: str = Field(..., description="Unique metric identifier")
    corpus_id: str = Field(..., description="Associated corpus ID")
    metric_type: MetricType = Field(..., description="Type of metric")
    value: Union[float, int, str] = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(..., description="When metric was recorded")
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")
    metadata: Dict[str, Union[str, int, float]] = Field(default_factory=dict)


class ResourceUsage(BaseModel):
    """Resource usage metrics"""
    resource_type: ResourceType = Field(..., description="Type of resource")
    current_value: float = Field(..., description="Current usage value")
    max_value: Optional[float] = Field(None, description="Maximum recorded value")
    average_value: Optional[float] = Field(None, description="Average over time period")
    unit: str = Field(..., description="Unit (%, MB, etc.)")
    timestamp: datetime = Field(..., description="Measurement timestamp")


class QualityMetrics(BaseModel):
    """Quality assessment metrics"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    validation_score: float = Field(..., ge=0.0, le=1.0, description="Data validation score")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Data completeness")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Data consistency")
    accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Accuracy score")
    timestamp: datetime = Field(..., description="Assessment timestamp")
    issues_detected: List[str] = Field(default_factory=list, description="Detected issues")


class OperationMetrics(BaseModel):
    """Operation-specific metrics"""
    operation_type: str = Field(..., description="Type of operation")
    start_time: datetime = Field(..., description="Operation start time")
    end_time: Optional[datetime] = Field(None, description="Operation end time")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    success: bool = Field(..., description="Whether operation succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    records_processed: Optional[int] = Field(None, description="Number of records processed")
    throughput_per_second: Optional[float] = Field(None, description="Records per second")


class TimeSeriesPoint(BaseModel):
    """Single time series data point"""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: Union[float, int] = Field(..., description="Metric value")
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")


class MetricsSnapshot(BaseModel):
    """Complete metrics snapshot for a corpus"""
    corpus_id: str = Field(..., description="Corpus identifier")
    snapshot_time: datetime = Field(..., description="When snapshot was taken")
    operation_metrics: List[OperationMetrics] = Field(default_factory=list)
    quality_metrics: Optional[QualityMetrics] = Field(None)
    resource_usage: List[ResourceUsage] = Field(default_factory=list)
    custom_metrics: List[CorpusMetric] = Field(default_factory=list)
    total_records: int = Field(default=0, description="Total records in corpus")
    health_status: str = Field(default="unknown", description="Overall health status")


# Legacy metrics for backward compatibility
class EnrichedMetrics(BaseModel):
    """Legacy enriched metrics model"""
    data: Dict[str, str]


class BaselineMetrics(BaseModel):
    """Legacy baseline metrics model"""
    data: Dict[str, str]