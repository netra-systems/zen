"""Strong type definitions for Quality Routes and monitoring services."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from netra_backend.app.core.resilience.monitor import AlertSeverity

# Import types only for type checking to avoid circular dependencies  
if TYPE_CHECKING:
    pass


class QualityLevel(str, Enum):
    """Quality levels for content assessment."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class ContentType(str, Enum):
    """Types of content for quality validation."""
    OPTIMIZATION = "optimization"
    DATA_ANALYSIS = "data_analysis"
    ACTION_PLAN = "action_plan"
    REPORT = "report"
    TRIAGE = "triage"
    ERROR_MESSAGE = "error"
    GENERAL = "general"




class MetricType(str, Enum):
    """Types of quality metrics."""
    SPECIFICITY = "specificity"
    ACTIONABILITY = "actionability"
    QUANTIFICATION = "quantification"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    NOVELTY = "novelty"
    CLARITY = "clarity"
    OVERALL = "overall"


class User(BaseModel):
    """Strongly typed User model for quality routes."""
    id: str = Field(description="User identifier")
    email: str = Field(description="User email address")
    role: str = Field(description="User role")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(description="User creation timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")


class QualityMetrics(BaseModel):
    """Comprehensive quality metrics for content validation."""
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall quality score")
    quality_level: QualityLevel = Field(description="Quality level assessment")
    specificity_score: float = Field(ge=0.0, le=100.0, description="Specificity score")
    actionability_score: float = Field(ge=0.0, le=100.0, description="Actionability score")
    quantification_score: float = Field(ge=0.0, le=100.0, description="Quantification score")
    relevance_score: float = Field(ge=0.0, le=100.0, description="Relevance score")
    completeness_score: float = Field(ge=0.0, le=100.0, description="Completeness score")
    novelty_score: float = Field(ge=0.0, le=100.0, description="Novelty score")
    clarity_score: float = Field(ge=0.0, le=100.0, description="Clarity score")
    word_count: int = Field(ge=0, description="Word count")
    generic_phrase_count: int = Field(ge=0, description="Count of generic phrases")
    circular_reasoning_detected: bool = Field(description="Whether circular reasoning was detected")
    hallucination_risk: float = Field(ge=0.0, le=1.0, description="Risk of hallucination")
    redundancy_ratio: float = Field(ge=0.0, le=1.0, description="Redundancy ratio")
    issues: List[str] = Field(default_factory=list, description="Identified issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class QualityValidationResult(BaseModel):
    """Result of quality validation process."""
    passed: bool = Field(description="Whether content passed validation")
    metrics: QualityMetrics = Field(description="Detailed quality metrics")
    retry_suggested: bool = Field(description="Whether retry is suggested")
    retry_prompt_adjustments: List[str] = Field(default_factory=list, description="Suggested prompt adjustments")
    validation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Validation timestamp")
    validation_duration_ms: float = Field(description="Time taken for validation")


class QualityValidationRequest(BaseModel):
    """Request model for content validation."""
    content: str = Field(min_length=1, description="Content to validate")
    content_type: str = Field(default="general", description="Type of content")
    strict_mode: bool = Field(default=False, description="Apply strict validation")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    user_id: Optional[str] = Field(default=None, description="User requesting validation")


class QualityValidationResponse(BaseModel):
    """Response model for content validation."""
    passed: bool = Field(description="Whether content passed validation")
    metrics: Dict[str, Any] = Field(description="Quality metrics as dictionary")
    retry_suggested: bool = Field(description="Whether retry is suggested")
    retry_adjustments: List[str] = Field(description="Suggested retry adjustments")
    validation_id: str = Field(description="Unique validation identifier")
    timestamp: datetime = Field(description="Validation timestamp")


class QualityAlert(BaseModel):
    """Quality alert with detailed information."""
    id: str = Field(description="Unique alert identifier")
    timestamp: datetime = Field(description="Alert timestamp")
    severity: AlertSeverity = Field(description="Alert severity")
    metric_type: MetricType = Field(description="Type of metric that triggered alert")
    agent: str = Field(description="Agent that triggered the alert")
    message: str = Field(description="Alert message")
    current_value: float = Field(description="Current metric value")
    threshold: float = Field(description="Threshold that was exceeded")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional alert details")
    acknowledged: bool = Field(default=False, description="Whether alert has been acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="User who acknowledged alert")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Acknowledgment timestamp")
    resolved: bool = Field(default=False, description="Whether alert has been resolved")
    resolved_by: Optional[str] = Field(default=None, description="User who resolved alert")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution timestamp")


class AlertAcknowledgement(BaseModel):
    """Model for acknowledging alerts."""
    alert_id: str = Field(description="Alert ID to acknowledge")
    action: Literal["acknowledge", "resolve"] = Field(description="Action to take")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Optional notes")
    user_id: str = Field(description="User performing the action")


class AlertAcknowledgementResponse(BaseModel):
    """Response for alert acknowledgement."""
    success: bool = Field(description="Whether action was successful")
    alert_id: str = Field(description="Alert that was acted upon")
    action: str = Field(description="Action that was performed")
    user_id: str = Field(description="User who performed action")
    timestamp: datetime = Field(description="Action timestamp")
    message: Optional[str] = Field(default=None, description="Additional message")


class AgentQualityProfile(BaseModel):
    """Quality profile for a specific agent."""
    agent_name: str = Field(description="Name of the agent")
    total_validations: int = Field(ge=0, description="Total validations performed")
    passed_validations: int = Field(ge=0, description="Number of passed validations")
    failed_validations: int = Field(ge=0, description="Number of failed validations")
    average_quality_score: float = Field(ge=0.0, le=100.0, description="Average quality score")
    improvement_trend: Literal["improving", "declining", "stable"] = Field(description="Quality trend")
    last_validation: Optional[datetime] = Field(default=None, description="Last validation timestamp")
    alerts_generated: int = Field(ge=0, description="Number of alerts generated")
    common_issues: List[str] = Field(default_factory=list, description="Common quality issues")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")


class QualityDashboardData(BaseModel):
    """Data for quality dashboard."""
    summary: Dict[str, Any] = Field(description="Summary statistics")
    recent_alerts: List[QualityAlert] = Field(description="Recent quality alerts")
    agent_profiles: Dict[str, AgentQualityProfile] = Field(description="Agent quality profiles")
    quality_trends: Dict[str, List[float]] = Field(description="Quality trends over time")
    top_issues: List[str] = Field(description="Most common quality issues")
    system_health: Dict[str, Any] = Field(description="Overall system health metrics")
    period_hours: int = Field(description="Time period for data")
    user_id: Optional[str] = Field(default=None, description="User requesting dashboard")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Dashboard generation timestamp")


class QualityReportType(str, Enum):
    """Types of quality reports."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    AGENT_SPECIFIC = "agent_specific"
    TREND_ANALYSIS = "trend_analysis"


class QualityReport(BaseModel):
    """Comprehensive quality report."""
    report_type: QualityReportType = Field(description="Type of report")
    generated_at: datetime = Field(description="Report generation timestamp")
    generated_by: str = Field(description="User who generated report")
    period_days: int = Field(description="Period covered by report")
    data: Dict[str, Any] = Field(description="Report data")
    summary: Optional[str] = Field(default=None, description="Executive summary")
    key_findings: List[str] = Field(default_factory=list, description="Key findings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Report metadata")


class QualityStatistics(BaseModel):
    """Statistical analysis of quality metrics."""
    total_validations: int = Field(description="Total number of validations")
    average_score: float = Field(description="Average quality score")
    median_score: float = Field(description="Median quality score")
    score_distribution: Dict[str, int] = Field(description="Distribution of scores by range")
    pass_rate: float = Field(description="Percentage of validations that passed")
    top_issues: List[str] = Field(description="Most common issues")
    improvement_areas: List[str] = Field(description="Areas needing improvement")
    content_type_breakdown: Dict[str, Dict[str, Any]] = Field(description="Statistics by content type")
    agent_performance: Dict[str, float] = Field(description="Performance by agent")
    timestamp: datetime = Field(description="Statistics timestamp")
    content_type_filter: Optional[str] = Field(default=None, description="Content type filter applied")


class QualityMonitoringConfig(BaseModel):
    """Configuration for quality monitoring."""
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    interval_seconds: int = Field(default=60, ge=10, le=3600, description="Monitoring interval")
    alert_thresholds: Dict[str, float] = Field(description="Alert thresholds for metrics")
    notification_settings: Dict[str, Any] = Field(default_factory=dict, description="Notification settings")
    retention_days: int = Field(default=30, ge=1, le=365, description="Data retention period")
    auto_acknowledge_resolved: bool = Field(default=True, description="Auto-acknowledge resolved alerts")


class QualityServiceHealth(BaseModel):
    """Health status of quality services."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(description="Overall health status")
    services: Dict[str, str] = Field(description="Status of individual services")
    statistics: Dict[str, int] = Field(description="Service statistics")
    timestamp: datetime = Field(description="Health check timestamp")
    error: Optional[str] = Field(default=None, description="Error message if unhealthy")
    uptime_percentage: Optional[float] = Field(default=None, description="Service uptime percentage")
    response_time_ms: Optional[float] = Field(default=None, description="Average response time")


class QualityThresholdCheck(BaseModel):
    """Result of quality threshold checking."""
    metric: str = Field(description="Metric name")
    value: float = Field(description="Current metric value")
    threshold: float = Field(description="Threshold value")
    alert: bool = Field(description="Whether an alert should be triggered")
    severity: AlertSeverity = Field(description="Alert severity if triggered")
    message: Optional[str] = Field(default=None, description="Alert message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Check timestamp")


class QualityTrendData(BaseModel):
    """Quality trend data over time."""
    date: str = Field(description="Date for this data point")
    data: QualityDashboardData = Field(description="Dashboard data for this date")
    comparison_previous: Optional[Dict[str, float]] = Field(default=None, description="Comparison with previous period")
    notable_changes: List[str] = Field(default_factory=list, description="Notable changes from previous period")


# Quality Validator Interface (Single Source of Truth)
class QualityValidatorInterface(ABC):
    """Interface for all quality validator implementations - prevents duplicate validator classes"""
    
    @abstractmethod
    async def validate_content(
        self, 
        content: str, 
        content_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityValidationResult:
        """Validate content and return detailed quality results"""
        pass
    
    @abstractmethod
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        pass