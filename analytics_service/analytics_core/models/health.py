"""Analytics Service Health Models - Single Source of Truth for Health Check Data Models.

Business Value Justification (BVJ):
1. Segment: Platform/Internal, Early, Mid, Enterprise
2. Business Goal: System Reliability, Operational Excellence, Risk Reduction
3. Value Impact: Proactive monitoring and rapid issue detection for analytics service
4. Strategic Impact: Ensures 99.9% uptime for critical analytics functionality

CRITICAL ARCHITECTURAL COMPLIANCE:
- All health model definitions MUST be imported from this module
- NO duplicate health model definitions allowed elsewhere
- Strong typing with Pydantic v2 for data validation
- Maximum file size: 300 lines (currently under limit)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels for system components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health information for a specific system component."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Current health status")
    last_check: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last health check timestamp"
    )
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional component-specific details"
    )
    
    # Resource utilization (if applicable)
    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="CPU usage percentage")
    memory_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Memory usage percentage")
    disk_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Disk usage percentage")
    
    # Connection/capacity info
    active_connections: Optional[int] = Field(None, ge=0, description="Number of active connections")
    max_connections: Optional[int] = Field(None, ge=0, description="Maximum allowed connections")
    
    # Uptime information
    uptime_seconds: Optional[float] = Field(None, ge=0.0, description="Component uptime in seconds")


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoints."""
    overall_status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp"
    )
    service_name: str = Field(default="analytics_service", description="Name of the service")
    service_version: Optional[str] = Field(None, description="Service version")
    environment: str = Field(default="production", description="Environment name")
    
    # Component health details
    components: List[ComponentHealth] = Field(
        default_factory=list,
        description="Health status of individual components"
    )
    
    # Summary counts
    healthy_components: int = Field(default=0, description="Number of healthy components")
    degraded_components: int = Field(default=0, description="Number of degraded components")
    unhealthy_components: int = Field(default=0, description="Number of unhealthy components")
    total_components: int = Field(default=0, description="Total number of components")
    
    # Service-specific metrics
    total_events_processed: Optional[int] = Field(None, description="Total events processed since start")
    events_per_second: Optional[float] = Field(None, description="Current events per second rate")
    error_rate_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Current error rate percentage")
    
    # Database connectivity
    clickhouse_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="ClickHouse database status")
    clickhouse_response_time_ms: Optional[float] = Field(None, description="ClickHouse response time")
    redis_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="Redis cache status")
    redis_response_time_ms: Optional[float] = Field(None, description="Redis response time")
    
    # Data freshness checks
    latest_event_timestamp: Optional[datetime] = Field(None, description="Timestamp of latest processed event")
    data_lag_minutes: Optional[float] = Field(None, description="Data lag in minutes")
    
    # Additional system information
    system_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional system information"
    )


class HealthCheckSummary(BaseModel):
    """Summary model for multiple health checks over time."""
    service_name: str = Field(..., description="Name of the service")
    start_time: datetime = Field(..., description="Start time of the summary period")
    end_time: datetime = Field(..., description="End time of the summary period")
    
    # Availability metrics
    total_checks: int = Field(..., ge=0, description="Total number of health checks")
    successful_checks: int = Field(..., ge=0, description="Number of successful checks")
    availability_percent: float = Field(..., ge=0.0, le=100.0, description="Availability percentage")
    
    # Response time statistics
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    min_response_time_ms: float = Field(default=0.0, description="Minimum response time")
    max_response_time_ms: float = Field(default=0.0, description="Maximum response time")
    p95_response_time_ms: float = Field(default=0.0, description="95th percentile response time")
    p99_response_time_ms: float = Field(default=0.0, description="99th percentile response time")
    
    # Error summary
    total_errors: int = Field(default=0, description="Total number of errors")
    unique_error_types: int = Field(default=0, description="Number of unique error types")
    most_common_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most common error types and their counts"
    )
    
    # Component reliability
    component_availability: Dict[str, float] = Field(
        default_factory=dict,
        description="Availability percentage by component"
    )


class HealthAlert(BaseModel):
    """Model for health-related alerts."""
    alert_id: str = Field(..., description="Unique alert identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Alert timestamp"
    )
    severity: str = Field(..., description="Alert severity level")
    component: str = Field(..., description="Affected component")
    message: str = Field(..., description="Alert message")
    status: HealthStatus = Field(..., description="Current status of affected component")
    
    # Alert metadata
    alert_type: str = Field(..., description="Type of alert")
    duration_minutes: Optional[float] = Field(None, description="Duration of the issue in minutes")
    resolved: bool = Field(default=False, description="Whether the alert has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    
    # Context information
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the alert"
    )


# Export all models
__all__ = [
    # Enums
    "HealthStatus",
    
    # Core Health Models
    "ComponentHealth",
    "HealthCheckResponse",
    "HealthCheckSummary",
    "HealthAlert"
]