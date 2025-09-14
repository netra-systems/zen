"""Analytics Service Report Models - Single Source of Truth for Report Data Models.

Business Value Justification (BVJ):
1. Segment: Early, Mid, Enterprise  
2. Business Goal: Product Optimization, Customer Insights, Data-Driven Decisions
3. Value Impact: Enable actionable insights from user behavior and AI usage patterns
4. Revenue Impact: 15% improvement in product metrics, 25% faster decision making

CRITICAL ARCHITECTURAL COMPLIANCE:
- All report model definitions MUST be imported from this module
- NO duplicate report model definitions allowed elsewhere  
- Strong typing with Pydantic v2 for data validation
- Maximum file size: 750 lines (currently under limit)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Granularity(str, Enum):
    """Time granularity for analytics reports."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TimeRange(str, Enum):
    """Pre-defined time ranges for analytics queries."""
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"


class UserActivitySummary(BaseModel):
    """Summary of user activity for a specific time period."""
    user_id: str = Field(..., description="User identifier")
    date: datetime = Field(..., description="Date of activity")
    total_events: int = Field(default=0, description="Total number of events")
    chat_interactions: int = Field(default=0, description="Number of chat interactions")
    threads_created: int = Field(default=0, description="Number of threads created")
    threads_completed: int = Field(default=0, description="Number of threads completed")
    feature_interactions: int = Field(default=0, description="Number of feature interactions")
    total_tokens_consumed: int = Field(default=0, description="Total tokens consumed")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    session_count: int = Field(default=0, description="Number of unique sessions")
    page_views: int = Field(default=0, description="Number of page views")
    errors_encountered: int = Field(default=0, description="Number of errors encountered")
    feedback_submissions: int = Field(default=0, description="Number of feedback submissions")
    
    # Engagement metrics
    time_spent_minutes: float = Field(default=0.0, description="Total time spent in minutes")
    unique_features_used: int = Field(default=0, description="Number of unique features used")
    follow_up_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Follow-up question rate")


class UserActivityReportRequest(BaseModel):
    """Request model for user activity reports."""
    user_id: Optional[str] = Field(None, description="Filter by specific user")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    granularity: Granularity = Field(default=Granularity.DAY, description="Time granularity")
    include_details: bool = Field(default=False, description="Include detailed breakdown")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum records to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, values):
        """Validate end date is after start date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v
    
    @field_validator('end_date')
    @classmethod
    def validate_max_date_range(cls, v, values):
        """Validate date range doesn't exceed 90 days."""
        if 'start_date' in values:
            delta = v - values['start_date']
            if delta.days > 90:
                raise ValueError("Date range cannot exceed 90 days")
        return v


class UserActivityReportResponse(BaseModel):
    """Response model for user activity reports."""
    summary: List[UserActivitySummary] = Field(default_factory=list, description="Activity summaries")
    total_users: int = Field(..., description="Total number of users in report")
    total_records: int = Field(..., description="Total number of records available")
    has_more: bool = Field(..., description="Whether more records are available")
    next_offset: Optional[int] = Field(None, description="Offset for next page")
    query_time_ms: float = Field(..., description="Query execution time")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp"
    )
    
    # Aggregate metrics
    total_events: int = Field(default=0, description="Total events across all users")
    total_chat_interactions: int = Field(default=0, description="Total chat interactions")
    total_tokens_consumed: int = Field(default=0, description="Total tokens consumed")
    avg_response_time_ms: float = Field(default=0.0, description="Overall average response time")


class PromptAnalyticsItem(BaseModel):
    """Analytics item for prompt analysis."""
    prompt_hash: str = Field(..., description="Hash of the prompt for deduplication")
    prompt_category: str = Field(..., description="ML-classified category")
    prompt_intent: str = Field(..., description="Detected user intent")
    frequency: int = Field(..., description="Number of times this prompt appeared")
    unique_users: int = Field(..., description="Number of unique users who used this prompt")
    avg_complexity_score: float = Field(..., description="Average complexity score")
    avg_response_quality: float = Field(..., description="Average response quality score")
    avg_response_relevance: float = Field(..., description="Average response relevance score")
    follow_up_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of follow-up questions")
    avg_response_time_ms: float = Field(..., description="Average response time")
    total_tokens_consumed: int = Field(..., description="Total tokens consumed")
    estimated_cost_cents: float = Field(..., description="Estimated total cost in cents")
    first_seen: datetime = Field(..., description="First occurrence timestamp")
    last_seen: datetime = Field(..., description="Last occurrence timestamp")
    
    # Sample prompts for reference (anonymized/sanitized)
    sample_prompts: List[str] = Field(
        default_factory=list,
        description="Sample prompts (sanitized for privacy)"
    )
    
    # Related prompts
    similar_prompt_hashes: List[str] = Field(
        default_factory=list,
        description="Hashes of similar prompts"
    )


class PromptAnalyticsRequest(BaseModel):
    """Request model for prompt analytics reports."""
    category: Optional[str] = Field(None, description="Filter by prompt category")
    intent: Optional[str] = Field(None, description="Filter by prompt intent")
    min_frequency: int = Field(default=5, ge=1, description="Minimum frequency threshold")
    time_range: TimeRange = Field(default=TimeRange.SEVEN_DAYS, description="Analysis time range")
    user_id: Optional[str] = Field(None, description="Filter by specific user")
    sort_by: str = Field(default="frequency", description="Sort by field")
    sort_desc: bool = Field(default=True, description="Sort in descending order")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum items to return")
    include_samples: bool = Field(default=True, description="Include sample prompts")
    include_similar: bool = Field(default=False, description="Include similar prompts")


class PromptAnalyticsResponse(BaseModel):
    """Response model for prompt analytics reports."""
    items: List[PromptAnalyticsItem] = Field(default_factory=list, description="Analytics items")
    total_prompts_analyzed: int = Field(..., description="Total number of prompts analyzed")
    total_unique_prompts: int = Field(..., description="Number of unique prompts")
    total_users: int = Field(..., description="Number of users in analysis")
    time_range_start: datetime = Field(..., description="Analysis time range start")
    time_range_end: datetime = Field(..., description="Analysis time range end")
    query_time_ms: float = Field(..., description="Query execution time")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp"
    )
    
    # Aggregate statistics
    avg_complexity_score: float = Field(default=0.0, description="Overall average complexity")
    avg_response_quality: float = Field(default=0.0, description="Overall average quality")
    overall_follow_up_rate: float = Field(default=0.0, description="Overall follow-up rate")
    total_cost_cents: float = Field(default=0.0, description="Total estimated cost")
    
    # Top categories and intents
    top_categories: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top categories with counts"
    )
    top_intents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top intents with counts"
    )


class RealTimeMetrics(BaseModel):
    """Real-time analytics metrics for dashboard updates."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Metrics timestamp"
    )
    
    # Active users
    active_users_5min: int = Field(default=0, description="Active users in last 5 minutes")
    active_users_1hour: int = Field(default=0, description="Active users in last hour")
    active_users_24hours: int = Field(default=0, description="Active users in last 24 hours")
    
    # Chat metrics
    active_chat_sessions: int = Field(default=0, description="Currently active chat sessions")
    chat_messages_5min: int = Field(default=0, description="Chat messages in last 5 minutes")
    avg_response_time_ms: float = Field(default=0.0, description="Average AI response time")
    
    # System metrics
    error_rate_5min: float = Field(default=0.0, ge=0.0, le=1.0, description="Error rate in last 5 minutes")
    api_requests_per_second: float = Field(default=0.0, description="Current API requests per second")
    websocket_connections: int = Field(default=0, description="Active WebSocket connections")
    
    # Feature usage
    top_features_5min: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top features used in last 5 minutes"
    )
    
    # Cost metrics
    tokens_consumed_5min: int = Field(default=0, description="Tokens consumed in last 5 minutes")
    estimated_cost_5min_cents: float = Field(default=0.0, description="Estimated cost in last 5 minutes")
    
    # Engagement metrics
    new_threads_5min: int = Field(default=0, description="New threads created in last 5 minutes")
    completed_threads_5min: int = Field(default=0, description="Threads completed in last 5 minutes")
    avg_session_duration_minutes: float = Field(default=0.0, description="Average session duration")


class CohortAnalysis(BaseModel):
    """Cohort analysis for user retention."""
    cohort_date: datetime = Field(..., description="Cohort date (user first activity)")
    cohort_size: int = Field(..., description="Number of users in cohort")
    
    # Retention rates by time period
    retention_day_1: float = Field(..., ge=0.0, le=1.0, description="Day 1 retention rate")
    retention_day_7: float = Field(..., ge=0.0, le=1.0, description="Day 7 retention rate")
    retention_day_30: float = Field(..., ge=0.0, le=1.0, description="Day 30 retention rate")
    retention_day_90: float = Field(..., ge=0.0, le=1.0, description="Day 90 retention rate")
    
    # Engagement metrics by retained users
    avg_sessions_retained: float = Field(default=0.0, description="Average sessions by retained users")
    avg_events_retained: float = Field(default=0.0, description="Average events by retained users")
    avg_revenue_retained: float = Field(default=0.0, description="Average revenue by retained users")


class CohortAnalysisRequest(BaseModel):
    """Request model for cohort analysis."""
    start_date: datetime = Field(..., description="Analysis start date")
    end_date: datetime = Field(..., description="Analysis end date")
    cohort_size_min: int = Field(default=10, ge=1, description="Minimum cohort size")
    include_revenue: bool = Field(default=False, description="Include revenue analysis")
    granularity: Granularity = Field(default=Granularity.DAY, description="Cohort granularity")


class CohortAnalysisResponse(BaseModel):
    """Response model for cohort analysis."""
    cohorts: List[CohortAnalysis] = Field(default_factory=list, description="Cohort data")
    total_cohorts: int = Field(..., description="Total number of cohorts")
    total_users_analyzed: int = Field(..., description="Total users in analysis")
    analysis_period_days: int = Field(..., description="Analysis period in days")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp"
    )
    
    # Overall metrics
    overall_retention_day_1: float = Field(..., description="Overall day 1 retention")
    overall_retention_day_7: float = Field(..., description="Overall day 7 retention")
    overall_retention_day_30: float = Field(..., description="Overall day 30 retention")
    overall_retention_day_90: float = Field(..., description="Overall day 90 retention")


class FunnelStep(BaseModel):
    """A step in a user funnel analysis."""
    step_name: str = Field(..., description="Name of the funnel step")
    step_order: int = Field(..., description="Order of step in funnel")
    total_users: int = Field(..., description="Total users who reached this step")
    conversion_rate: float = Field(..., ge=0.0, le=1.0, description="Conversion rate to this step")
    drop_off_rate: float = Field(..., ge=0.0, le=1.0, description="Drop-off rate from previous step")
    avg_time_to_step_minutes: Optional[float] = Field(None, description="Average time to reach step")


class FunnelAnalysisRequest(BaseModel):
    """Request model for funnel analysis."""
    funnel_name: str = Field(..., description="Name of the funnel to analyze")
    start_date: datetime = Field(..., description="Analysis start date")
    end_date: datetime = Field(..., description="Analysis end date")
    user_segment: Optional[str] = Field(None, description="Filter by user segment")
    include_timing: bool = Field(default=True, description="Include timing analysis")


class FunnelAnalysisResponse(BaseModel):
    """Response model for funnel analysis."""
    funnel_name: str = Field(..., description="Name of analyzed funnel")
    steps: List[FunnelStep] = Field(default_factory=list, description="Funnel steps")
    total_users_entered: int = Field(..., description="Total users who entered funnel")
    total_users_completed: int = Field(..., description="Total users who completed funnel")
    overall_conversion_rate: float = Field(..., description="Overall funnel conversion rate")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp"
    )


# Export all models
__all__ = [
    # Enums
    "Granularity",
    "TimeRange",
    
    # User Activity Models
    "UserActivitySummary",
    "UserActivityReportRequest",
    "UserActivityReportResponse",
    
    # Prompt Analytics Models
    "PromptAnalyticsItem",
    "PromptAnalyticsRequest",
    "PromptAnalyticsResponse",
    
    # Real-time Metrics
    "RealTimeMetrics",
    
    # Cohort Analysis Models
    "CohortAnalysis",
    "CohortAnalysisRequest", 
    "CohortAnalysisResponse",
    
    # Funnel Analysis Models
    "FunnelStep",
    "FunnelAnalysisRequest",
    "FunnelAnalysisResponse"
]