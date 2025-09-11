"""
Strong type definitions for service layer operations following Netra conventions.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, Protocol, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# SSOT ID Manager instance for consistent ID generation
_id_manager = UnifiedIDManager()


class ServiceStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"


class OperationType(str, Enum):
    """CRUD operation types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    SEARCH = "search"
    BATCH_CREATE = "batch_create"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"


class ServiceValidationError(BaseModel):
    """Structured validation error for service responses"""
    field: str
    message: str
    code: str
    value: Optional[Any] = None
    suggestion: Optional[str] = None


class ServiceResponse(BaseModel, Generic[TypeVar('T')]):
    """Generic service response wrapper"""
    success: bool
    data: Optional[TypeVar('T')] = None
    errors: List[ServiceValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"


class FilterParams(BaseModel):
    """Filter parameters for queries"""
    field: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "starts_with", "ends_with"]
    value: Union[str, int, float, bool, List[Union[str, int, float, bool]]]


class SearchParams(BaseModel):
    """Search parameters"""
    query: str
    fields: Optional[List[str]] = None
    filters: List[FilterParams] = Field(default_factory=list)
    pagination: Optional[PaginationParams] = None
    include_metadata: bool = Field(default=False)


class PaginatedResponse(BaseModel, Generic[TypeVar('T')]):
    """Paginated response wrapper"""
    items: List[TypeVar('T')]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class BatchOperationResult(BaseModel):
    """Result of a batch operation"""
    operation: OperationType
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: float
    failed_items: List[Dict[str, Any]] = Field(default_factory=list)


class ServiceCacheConfig(BaseModel):
    """Cache configuration for services"""
    enabled: bool = Field(default=True)
    ttl_seconds: int = Field(default=300)
    max_size: int = Field(default=1000)
    eviction_policy: Literal["lru", "lfu", "fifo"] = "lru"
    key_prefix: str = ""


class ServiceConfig(BaseModel):
    """Base configuration for services"""
    name: str
    version: str = "1.0.0"
    cache_config: Optional[ServiceCacheConfig] = None
    rate_limit_per_minute: Optional[int] = None
    timeout_seconds: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    retry_delay_ms: int = Field(default=1000)
    circuit_breaker_enabled: bool = Field(default=False)
    circuit_breaker_threshold: int = Field(default=5)
    metadata: Dict[str, Any] = Field(default_factory=dict)


ModelType = TypeVar('ModelType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class CRUDServiceInterface(Protocol[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Protocol for CRUD services with strong typing"""
    
    async def create(self, schema: CreateSchemaType) -> ServiceResponse[ModelType]:
        """Create a new entity"""
        ...
    
    async def get(self, id: Union[str, int]) -> ServiceResponse[ModelType]:
        """Get entity by ID"""
        ...
    
    async def update(self, id: Union[str, int], schema: UpdateSchemaType) -> ServiceResponse[ModelType]:
        """Update entity"""
        ...
    
    async def delete(self, id: Union[str, int]) -> ServiceResponse[bool]:
        """Delete entity"""
        ...
    
    async def list(self, params: Optional[PaginationParams] = None) -> ServiceResponse[PaginatedResponse[ModelType]]:
        """List entities with pagination"""
        ...
    
    async def search(self, params: SearchParams) -> ServiceResponse[PaginatedResponse[ModelType]]:
        """Search entities"""
        ...


class ServiceMetrics(BaseModel):
    """Metrics for service monitoring"""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    active_connections: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    uptime_seconds: float = 0.0


class ServiceHealthCheck(BaseModel):
    """Health check result for a service"""
    service_name: str
    status: ServiceStatus
    checks: Dict[str, bool] = Field(default_factory=dict)
    message: Optional[str] = None
    response_time_ms: float
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceDependency(BaseModel):
    """Service dependency definition"""
    name: str
    type: Literal["database", "cache", "api", "queue", "storage", "other"]
    required: bool = Field(default=True)
    health_check_url: Optional[str] = None
    timeout_seconds: int = Field(default=5)
    fallback_enabled: bool = Field(default=False)


class ServiceContext(BaseModel):
    """Context for service operations"""
    request_id: str = Field(default_factory=lambda: _id_manager.generate_id(IDType.REQUEST))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceAuditLog(BaseModel):
    """Audit log entry for service operations"""
    id: str = Field(default_factory=lambda: _id_manager.generate_id(IDType.METRIC))
    service_name: str
    operation: OperationType
    entity_type: str
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    result: Literal["success", "failure"]
    error_message: Optional[str] = None
    context: ServiceContext
    duration_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceEvent(BaseModel):
    """Event emitted by services"""
    event_type: str
    service_name: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: ServiceContext
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceCapability(BaseModel):
    """Service capability definition"""
    name: str
    description: str
    enabled: bool = Field(default=True)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    required_permissions: List[str] = Field(default_factory=list)


class ServiceRegistry(BaseModel):
    """Service registry entry"""
    name: str
    version: str
    description: str
    endpoint: str
    status: ServiceStatus
    capabilities: List[ServiceCapability] = Field(default_factory=list)
    dependencies: List[ServiceDependency] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_health_check: Optional[datetime] = None


class TransactionContext(BaseModel):
    """Context for transactional operations"""
    transaction_id: str = Field(default_factory=lambda: _id_manager.generate_id(IDType.TRANSACTION))
    isolation_level: Literal["read_uncommitted", "read_committed", "repeatable_read", "serializable"] = "read_committed"
    timeout_seconds: int = Field(default=30)
    savepoints: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)