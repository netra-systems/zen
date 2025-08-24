"""
Strong type definitions for data ingestion operations following Netra conventions.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DataSourceType(str, Enum):
    """Supported data source types"""
    DATABASE = "database"
    FILE = "file"
    API = "api"
    STREAM = "stream"
    WEBHOOK = "webhook"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    REDIS_STREAM = "redis_stream"


class DataFormat(str, Enum):
    """Supported data formats"""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"
    XML = "xml"
    PROTOBUF = "protobuf"
    TEXT = "text"
    BINARY = "binary"


class IngestionStatus(str, Enum):
    """Status of ingestion job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class ValidationRule(BaseModel):
    """Data validation rule"""
    field: str
    rule_type: Literal["required", "type", "format", "range", "enum", "pattern", "custom"]
    value: Optional[Union[str, int, float, list, dict]] = None
    error_message: Optional[str] = None
    severity: Literal["error", "warning"] = "error"


class SchemaMapping(BaseModel):
    """Schema mapping configuration"""
    source_field: str
    target_field: str
    transformation: Optional[str] = None  # Expression or function name
    default_value: Optional[Any] = None
    data_type: Optional[str] = None


class DataSource(BaseModel):
    """Data source configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: DataSourceType
    connection_string: Optional[str] = Field(default=None, exclude=True)  # Exclude from serialization
    credentials: Optional[Dict[str, str]] = Field(default=None, exclude=True)
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None


class IngestionConfig(BaseModel):
    """Configuration for data ingestion"""
    source: DataSource
    format: DataFormat
    batch_size: int = Field(default=1000, ge=1)
    parallel_workers: int = Field(default=4, ge=1)
    timeout_seconds: int = Field(default=300, gt=0)
    retry_attempts: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=5, gt=0)
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    schema_mapping: List[SchemaMapping] = Field(default_factory=list)
    deduplication_enabled: bool = Field(default=False)
    deduplication_fields: List[str] = Field(default_factory=list)
    error_handling: Literal["stop", "skip", "log"] = "log"
    max_errors: Optional[int] = Field(default=None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionJob(BaseModel):
    """Ingestion job definition"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    config: IngestionConfig
    schedule: Optional[str] = None  # Cron expression
    status: IngestionStatus = IngestionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionMetrics(BaseModel):
    """Metrics for ingestion job"""
    job_id: str
    total_records: int = 0
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    duplicate_records: int = 0
    processing_rate: float = 0.0  # Records per second
    average_record_size_bytes: float = 0.0
    total_bytes_processed: int = 0
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class DataQualityCheck(BaseModel):
    """Data quality check definition"""
    name: str
    check_type: Literal["completeness", "accuracy", "consistency", "timeliness", "uniqueness", "validity"]
    field: Optional[str] = None
    expression: str  # SQL or Python expression
    threshold: float = Field(ge=0.0, le=1.0)
    severity: Literal["critical", "high", "medium", "low"] = "medium"


class DataQualityReport(BaseModel):
    """Data quality report"""
    job_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    failed_checks: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class TransformationStep(BaseModel):
    """Data transformation step"""
    name: str
    type: Literal["map", "filter", "aggregate", "join", "pivot", "custom"]
    config: Dict[str, Any]
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class DataPipeline(BaseModel):
    """Data pipeline definition"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    source: DataSource
    transformations: List[TransformationStep] = Field(default_factory=list)
    destination: DataSource
    schedule: Optional[str] = None  # Cron expression
    enabled: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None


class StreamingConfig(BaseModel):
    """Configuration for streaming ingestion"""
    window_size_seconds: int = Field(default=60, gt=0)
    checkpoint_interval_seconds: int = Field(default=30, gt=0)
    max_batch_size: int = Field(default=100, gt=0)
    watermark_delay_seconds: int = Field(default=10, ge=0)
    exactly_once_semantics: bool = Field(default=False)


class IngestionEvent(BaseModel):
    """Event during ingestion"""
    job_id: str
    event_type: Literal["started", "progress", "completed", "failed", "warning"]
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataSample(BaseModel):
    """Sample of ingested data"""
    model_config = ConfigDict(populate_by_name=True)
    
    job_id: str
    sample_size: int
    data: List[Dict[str, Any]]
    data_schema: Dict[str, str] = Field(alias="schema")  # Field name to type mapping
    statistics: Dict[str, Any] = Field(default_factory=dict)


class IngestionError(BaseModel):
    """Error during ingestion"""
    job_id: str
    error_type: str
    message: str
    record_number: Optional[int] = None
    record_id: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stack_trace: Optional[str] = None


class DataCatalog(BaseModel):
    """Data catalog entry"""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    source: DataSource
    format: DataFormat
    data_schema: Dict[str, Any] = Field(alias="schema")
    sample_data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: Optional[datetime] = None
    last_accessed: Optional[datetime] = None


class DataLineage(BaseModel):
    """Data lineage information"""
    entity_id: str
    entity_type: str
    upstream: List[Dict[str, str]] = Field(default_factory=list)
    downstream: List[Dict[str, str]] = Field(default_factory=list)
    transformations: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))