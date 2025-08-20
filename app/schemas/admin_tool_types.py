"""
Strong type definitions for Admin Tool Dispatcher operations following Netra conventions.
"""

from typing import Dict, Any, Optional, List, Union, Literal
from datetime import datetime, UTC
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class AdminToolType(str, Enum):
    """Types of admin tools available"""
    CORPUS_MANAGEMENT = "corpus_management"
    SYNTHETIC_DATA = "synthetic_data"
    USER_ADMIN = "user_admin"
    SYSTEM_CONFIG = "system_config"
    MONITORING = "monitoring"
    SECURITY = "security"
    DATA_EXPORT = "data_export"
    BACKUP_RESTORE = "backup_restore"
    PERFORMANCE_TUNING = "performance_tuning"


class ToolPermission(str, Enum):
    """Permission levels for admin tools"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ToolStatus(str, Enum):
    """Status of tool execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionContext(BaseModel):
    """Context for tool execution with audit trail"""
    user_id: str
    user_role: str
    session_id: str
    ip_address: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    environment: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Base response for all admin tools"""
    tool_name: str
    tool_type: AdminToolType
    status: ToolStatus
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(use_enum_values=True)


class ToolSuccessResponse(ToolResponse):
    """Successful tool execution response"""
    status: Literal[ToolStatus.COMPLETED] = ToolStatus.COMPLETED
    data: Any
    affected_resources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ToolFailureResponse(ToolResponse):
    """Failed tool execution response"""
    status: Literal[ToolStatus.FAILED] = ToolStatus.FAILED
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = Field(default=None)
    recoverable: bool = Field(default=True)
    suggested_action: Optional[str] = Field(default=None)


class ToolCancellationResponse(ToolResponse):
    """Cancelled tool execution response"""
    status: Literal[ToolStatus.CANCELLED] = ToolStatus.CANCELLED
    cancellation_reason: str
    partial_results: Optional[Any] = Field(default=None)


class AdminToolInfo(BaseModel):
    """Information about an admin tool"""
    name: str
    type: AdminToolType
    description: str
    required_permissions: List[ToolPermission]
    parameters: List[Dict[str, Any]]
    supports_batch: bool = Field(default=False)
    supports_async: bool = Field(default=True)
    timeout_seconds: int = Field(default=300)
    rate_limit: Optional[Dict[str, int]] = Field(default=None)
    capabilities: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class CorpusOperation(BaseModel):
    """Corpus management operations"""
    operation: Literal["create", "update", "delete", "search", "index", "optimize"]
    corpus_id: Optional[str] = Field(default=None)
    corpus_name: Optional[str] = Field(default=None)
    documents: Optional[List[Dict[str, Any]]] = Field(default=None)
    query: Optional[str] = Field(default=None)
    filters: Optional[Dict[str, Any]] = Field(default=None)
    options: Dict[str, Any] = Field(default_factory=dict)


class CorpusOperationResponse(ToolSuccessResponse):
    """Response for corpus operations"""
    operation: str
    documents_affected: int
    index_status: Optional[str] = Field(default=None)
    search_results: Optional[List[Dict[str, Any]]] = Field(default=None)
    statistics: Dict[str, Any] = Field(default_factory=dict)


class SyntheticDataRequest(BaseModel):
    """Request for synthetic data generation"""
    data_type: str
    count: int = Field(ge=1, le=100000)
    data_schema: Dict[str, Any] = Field(description="Schema for generated data")
    constraints: Optional[Dict[str, Any]] = Field(default=None)
    format: Literal["json", "csv", "parquet", "sql"] = "json"
    seed: Optional[int] = Field(default=None)
    quality_checks: bool = Field(default=True)


class SyntheticDataResponse(ToolSuccessResponse):
    """Response for synthetic data generation"""
    records_generated: int
    data_location: str
    format: str
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    sample_data: List[Dict[str, Any]] = Field(default_factory=list)
    generation_time_seconds: float


class UserAdminOperation(BaseModel):
    """User administration operations"""
    operation: Literal["create", "update", "delete", "suspend", "activate", "reset_password", "update_permissions"]
    user_id: Optional[str] = Field(default=None)
    user_data: Optional[Dict[str, Any]] = Field(default=None)
    permissions: Optional[List[str]] = Field(default=None)
    reason: Optional[str] = Field(default=None)


class UserAdminResponse(ToolSuccessResponse):
    """Response for user admin operations"""
    operation: str
    user_id: str
    changes_applied: Dict[str, Any] = Field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = Field(default=None)
    notifications_sent: List[str] = Field(default_factory=list)


class SystemConfigOperation(BaseModel):
    """System configuration operations"""
    operation: Literal["get", "update", "reload", "validate", "export", "import"]
    config_section: Optional[str] = Field(default=None)
    config_data: Optional[Dict[str, Any]] = Field(default=None)
    backup_current: bool = Field(default=True)
    dry_run: bool = Field(default=False)


class SystemConfigResponse(ToolSuccessResponse):
    """Response for system config operations"""
    operation: str
    config_section: Optional[str] = Field(default=None)
    changes: Dict[str, Any] = Field(default_factory=dict)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    backup_created: bool = Field(default=False)
    backup_location: Optional[str] = Field(default=None)


class MonitoringRequest(BaseModel):
    """Request for monitoring operations"""
    metric_type: Literal["system", "application", "database", "api", "custom"]
    time_range: Dict[str, datetime]
    aggregation: Optional[Literal["sum", "avg", "min", "max", "count"]] = Field(default="avg")
    filters: Optional[Dict[str, Any]] = Field(default=None)
    group_by: Optional[List[str]] = Field(default=None)


class MonitoringResponse(ToolSuccessResponse):
    """Response for monitoring operations"""
    metric_type: str
    time_range: Dict[str, str]
    metrics: List[Dict[str, Any]]
    aggregated_values: Dict[str, float] = Field(default_factory=dict)
    alerts_triggered: List[Dict[str, Any]] = Field(default_factory=list)
    visualization_url: Optional[str] = Field(default=None)


class AdminToolMetrics(BaseModel):
    """Metrics for admin tool usage"""
    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    p95_execution_time_ms: float
    p99_execution_time_ms: float
    last_execution: Optional[datetime] = Field(default=None)
    error_rate: float = Field(ge=0.0, le=1.0)
    most_common_errors: List[Dict[str, Any]] = Field(default_factory=list)
    usage_by_user: Dict[str, int] = Field(default_factory=dict)
    usage_by_hour: Dict[int, int] = Field(default_factory=dict)


class ToolPermissionCheck(BaseModel):
    """Permission check result for admin tool access"""
    tool_name: str
    user_id: str
    required_permissions: List[str]
    has_access: bool
    missing_permissions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(use_enum_values=True)


class AdminToolAuditLog(BaseModel):
    """Audit log entry for admin tool usage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_name: str
    tool_type: AdminToolType
    user_id: str
    user_role: str
    operation: str
    parameters: Dict[str, Any]
    result: ToolStatus
    execution_time_ms: float
    affected_resources: List[str] = Field(default_factory=list)
    ip_address: str
    session_id: str
    error_message: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)