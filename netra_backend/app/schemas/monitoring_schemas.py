"""GCP Error Reporting Schemas - Single Source of Truth for Error Data Models.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Reduce MTTR by 40% through structured error data
3. Value Impact: Enables automated error analysis and trend detection
4. Revenue Impact: +$15K MRR from enhanced reliability monitoring

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (currently under limit)
- All GCP error model definitions MUST be imported from this module
- NO duplicate error model definitions allowed elsewhere
- Strong typing with Pydantic for data validation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """GCP Error severity levels."""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"  
    WARNING = "WARNING"
    INFO = "INFO"


class ErrorStatus(str, Enum):
    """GCP Error status types."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    MUTED = "MUTED"


class ErrorContext(BaseModel):
    """Additional context for GCP errors."""
    request_id: Optional[str] = Field(None, description="Request ID if available")
    user_id: Optional[str] = Field(None, description="User ID if available")
    environment: Optional[str] = Field(None, description="Environment (staging/production)")
    response_code: Optional[int] = Field(None, description="HTTP response code")
    method: Optional[str] = Field(None, description="HTTP method")
    url: Optional[str] = Field(None, description="Request URL")
    user_agent: Optional[str] = Field(None, description="User agent string")


class GCPErrorGroup(BaseModel):
    """GCP Error Group data model."""
    id: str = Field(..., description="Unique error group identifier")
    name: str = Field(..., description="Error group name")
    group_id: str = Field(..., description="GCP group ID")
    tracking_issues: List[Dict[str, str]] = Field(default_factory=list, description="Tracking issues")
    resolution_status: ErrorStatus = Field(default=ErrorStatus.OPEN, description="Resolution status")


class GCPErrorEvent(BaseModel):
    """Individual GCP error event data model."""
    event_time: datetime = Field(..., description="When the error occurred")
    message: str = Field(..., description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    source_location: Optional[Dict[str, Any]] = Field(None, description="Source location info")
    context: ErrorContext = Field(default_factory=ErrorContext, description="Error context")
    http_request: Optional[Dict[str, Any]] = Field(None, description="HTTP request details")


class GCPError(BaseModel):
    """Complete GCP Error data model matching spec requirements."""
    id: str = Field(..., description="Unique error identifier")
    message: str = Field(..., description="Error message")
    stack_trace: Optional[str] = Field(None, description="Full stack trace")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    severity: ErrorSeverity = Field(..., description="Error severity level")
    occurrences: int = Field(default=1, description="Number of occurrences")
    first_seen: datetime = Field(..., description="First occurrence time")
    last_seen: datetime = Field(..., description="Last occurrence time")
    status: ErrorStatus = Field(default=ErrorStatus.OPEN, description="Error status")
    affected_users: int = Field(default=0, description="Estimated affected users")
    context: ErrorContext = Field(default_factory=ErrorContext, description="Additional context")
    group: Optional[GCPErrorGroup] = Field(None, description="Error group information")
    recent_events: List[GCPErrorEvent] = Field(default_factory=list, description="Recent error events")


class ErrorQuery(BaseModel):
    """Query parameters for fetching GCP errors."""
    status: ErrorStatus = Field(default=ErrorStatus.OPEN, description="Error status filter")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum errors to return")
    service: Optional[str] = Field(None, description="Filter by service name")
    severity: Optional[ErrorSeverity] = Field(None, description="Filter by severity")
    time_range: str = Field(default="24h", description="Time range for errors")
    page_token: Optional[str] = Field(None, description="Pagination token")


class ErrorSummary(BaseModel):
    """Summary statistics for error data."""
    total_errors: int = Field(default=0, description="Total number of errors")
    critical_errors: int = Field(default=0, description="Number of critical errors")
    error_errors: int = Field(default=0, description="Number of error-level errors")
    warning_errors: int = Field(default=0, description="Number of warnings")
    info_errors: int = Field(default=0, description="Number of info messages")
    open_errors: int = Field(default=0, description="Number of open errors")
    resolved_errors: int = Field(default=0, description="Number of resolved errors")
    affected_services: List[str] = Field(default_factory=list, description="List of affected services")
    time_range_start: datetime = Field(..., description="Query time range start")
    time_range_end: datetime = Field(..., description="Query time range end")


class ErrorResponse(BaseModel):
    """Response format for error API endpoints."""
    errors: List[GCPError] = Field(default_factory=list, description="List of formatted error objects")
    summary: ErrorSummary = Field(..., description="Summary statistics")
    next_page_token: Optional[str] = Field(None, description="Pagination token for next page")
    total_count: int = Field(default=0, description="Total number of errors available")


class ErrorDetailResponse(BaseModel):
    """Detailed error response for individual errors."""
    error: GCPError = Field(..., description="Detailed error with stack trace")
    occurrences: List[GCPErrorEvent] = Field(default_factory=list, description="Recent occurrences")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    related_errors: List[str] = Field(default_factory=list, description="Related error IDs")


class ErrorResolution(BaseModel):
    """Error resolution request data."""
    resolution_note: str = Field(..., description="Resolution description")
    resolved_by: Optional[str] = Field(None, description="User who resolved the error")
    resolution_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GCPCredentialsConfig(BaseModel):
    """GCP credentials configuration."""
    project_id: str = Field(..., description="GCP project ID")
    credentials_path: Optional[str] = Field(None, description="Path to service account JSON")
    use_default_credentials: bool = Field(default=True, description="Use default application credentials")


class GCPErrorServiceConfig(BaseModel):
    """Configuration for GCP Error Service."""
    project_id: str = Field(..., description="GCP project ID")
    credentials: GCPCredentialsConfig = Field(..., description="GCP credentials configuration")
    rate_limit_per_minute: int = Field(default=1000, description="API rate limit per minute")
    batch_size: int = Field(default=100, description="Batch size for API requests")
    timeout_seconds: int = Field(default=30, description="API request timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    enable_pii_redaction: bool = Field(default=True, description="Enable PII redaction")


# Export all schemas
__all__ = [
    "ErrorSeverity",
    "ErrorStatus", 
    "ErrorContext",
    "GCPErrorGroup",
    "GCPErrorEvent",
    "GCPError",
    "ErrorQuery",
    "ErrorSummary",
    "ErrorResponse",
    "ErrorDetailResponse",
    "ErrorResolution",
    "GCPCredentialsConfig",
    "GCPErrorServiceConfig"
]