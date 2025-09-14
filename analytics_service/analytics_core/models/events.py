"""Analytics Service Event Models - Single Source of Truth for Event Data Models.

Business Value Justification (BVJ):
1. Segment: Early, Mid, Enterprise
2. Business Goal: Customer Insights, Product Optimization, Retention
3. Value Impact: Deep visibility into user behavior and AI usage patterns  
4. Revenue Impact: 20% reduction in churn, 15% increase in feature adoption

CRITICAL ARCHITECTURAL COMPLIANCE:
- All event model definitions MUST be imported from this module
- NO duplicate event model definitions allowed elsewhere
- Strong typing with Pydantic v2 for data validation
- Maximum file size: 750 lines (currently under limit)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Types of analytics events that can be captured."""
    CHAT_INTERACTION = "chat_interaction"
    THREAD_LIFECYCLE = "thread_lifecycle"
    FEATURE_USAGE = "feature_usage"
    SURVEY_RESPONSE = "survey_response"
    FEEDBACK_SUBMISSION = "feedback_submission"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_TRACKING = "error_tracking"


class EventCategory(str, Enum):
    """Categories for grouping events by their nature and purpose."""
    USER_INTERACTION = "user_interaction"
    TECHNICAL = "technical"
    BUSINESS = "business"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Types of messages in chat interactions."""
    USER_PROMPT = "user_prompt"
    AI_RESPONSE = "ai_response"
    SYSTEM_MESSAGE = "system_message"


class ThreadAction(str, Enum):
    """Actions that can occur in thread lifecycle."""
    CREATED = "created"
    CONTINUED = "continued"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuestionType(str, Enum):
    """Types of survey questions."""
    PAIN_PERCEPTION = "pain_perception"
    MAGIC_WAND = "magic_wand"
    SPENDING = "spending"
    PLANNING = "planning"


class FeedbackType(str, Enum):
    """Types of feedback submissions."""
    NPS = "nps"
    CSAT = "csat"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


class MetricType(str, Enum):
    """Types of performance metrics."""
    PAGE_LOAD = "page_load"
    API_CALL = "api_call"
    WEBSOCKET = "websocket"
    RENDER = "render"


class UserImpact(str, Enum):
    """Impact levels for error tracking."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventContext(BaseModel):
    """Context information for all analytics events."""
    user_id: str = Field(..., description="Unique user identifier")
    session_id: str = Field(..., description="Session identifier")
    page_path: str = Field(..., description="Current page path")
    page_title: Optional[str] = Field(None, description="Current page title")
    referrer: Optional[str] = Field(None, description="Page referrer")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="Hashed IP address for privacy")
    country_code: Optional[str] = Field(None, description="Country code")
    gtm_container_id: Optional[str] = Field(None, description="GTM container ID")
    environment: str = Field(default="production", description="Environment name")
    app_version: Optional[str] = Field(None, description="Application version")


class ChatInteractionProperties(BaseModel):
    """Properties specific to chat interaction events."""
    thread_id: str = Field(..., description="Unique chat thread identifier")
    message_id: str = Field(..., description="Individual message identifier")
    message_type: MessageType = Field(..., description="Type of message")
    prompt_text: Optional[str] = Field(None, description="User's prompt text (sanitized)")
    prompt_length: int = Field(..., description="Character count of prompt")
    response_length: Optional[int] = Field(None, description="Character count of AI response")
    response_time_ms: Optional[float] = Field(None, description="Time to receive response")
    model_used: Optional[str] = Field(None, description="AI model identifier")
    tokens_consumed: Optional[int] = Field(None, description="Token count for request")
    is_follow_up: bool = Field(..., description="Whether this is a follow-up question")


class ThreadLifecycleProperties(BaseModel):
    """Properties specific to thread lifecycle events."""
    thread_id: str = Field(..., description="Unique thread identifier")
    action: ThreadAction = Field(..., description="Action performed on thread")
    message_count: Optional[int] = Field(None, description="Total messages in thread")
    duration_seconds: Optional[float] = Field(None, description="Thread duration")


class FeatureUsageProperties(BaseModel):
    """Properties specific to feature usage events."""
    feature_name: str = Field(..., description="Feature identifier")
    action: str = Field(..., description="Specific action taken")
    success: bool = Field(..., description="Whether action succeeded")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    duration_ms: Optional[float] = Field(None, description="Action duration")


class SurveyResponseProperties(BaseModel):
    """Properties specific to survey response events."""
    survey_id: str = Field(..., description="Survey campaign identifier")
    question_id: str = Field(..., description="Individual question identifier")
    question_type: QuestionType = Field(..., description="Type of question")
    response_value: Optional[str] = Field(None, description="Response text or value")
    response_scale: Optional[int] = Field(None, ge=1, le=10, description="Numeric scale response (1-10)")
    ai_spend_last_month: Optional[float] = Field(None, description="Reported AI spending")
    ai_spend_next_quarter: Optional[float] = Field(None, description="Planned AI spending")


class FeedbackSubmissionProperties(BaseModel):
    """Properties specific to feedback submission events."""
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    score: Optional[int] = Field(None, description="Numeric score if applicable")
    comment: Optional[str] = Field(None, description="Free text feedback")
    context_thread_id: Optional[str] = Field(None, description="Related thread if applicable")


class PerformanceMetricProperties(BaseModel):
    """Properties specific to performance metric events."""
    metric_type: MetricType = Field(..., description="Type of metric")
    duration_ms: float = Field(..., description="Operation duration")
    success: bool = Field(..., description="Whether operation succeeded")
    error_details: Optional[str] = Field(None, description="Error information if failed")


class ErrorTrackingProperties(BaseModel):
    """Properties specific to error tracking events."""
    error_type: str = Field(..., description="Error classification")
    error_message: str = Field(..., description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    user_impact: UserImpact = Field(..., description="Impact level on user")


# Union type for all property types
EventProperties = Union[
    ChatInteractionProperties,
    ThreadLifecycleProperties,
    FeatureUsageProperties,
    SurveyResponseProperties,
    FeedbackSubmissionProperties,
    PerformanceMetricProperties,
    ErrorTrackingProperties
]


class AnalyticsEvent(BaseModel):
    """Core analytics event model with validation."""
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC"
    )
    event_type: EventType = Field(..., description="Type of event")
    event_category: str = Field(..., description="Event category for grouping")
    event_action: str = Field(..., description="Specific action performed")
    event_label: Optional[str] = Field(None, description="Optional event label")
    event_value: Optional[float] = Field(None, description="Optional numeric value")
    
    # Event-specific properties
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data as JSON"
    )
    
    # User context
    context: EventContext = Field(..., description="Event context information")

    @field_validator('properties')
    @classmethod
    def validate_properties(cls, v, values):
        """Validate properties match event type requirements."""
        if 'event_type' not in values:
            return v
            
        event_type = values['event_type']
        
        # Basic validation - could be extended with specific property validation
        if event_type == EventType.CHAT_INTERACTION:
            required_fields = ['thread_id', 'message_id', 'message_type', 'prompt_length', 'is_follow_up']
        elif event_type == EventType.THREAD_LIFECYCLE:
            required_fields = ['thread_id', 'action']
        elif event_type == EventType.FEATURE_USAGE:
            required_fields = ['feature_name', 'action', 'success']
        elif event_type == EventType.SURVEY_RESPONSE:
            required_fields = ['survey_id', 'question_id', 'question_type']
        elif event_type == EventType.FEEDBACK_SUBMISSION:
            required_fields = ['feedback_type']
        elif event_type == EventType.PERFORMANCE_METRIC:
            required_fields = ['metric_type', 'duration_ms', 'success']
        elif event_type == EventType.ERROR_TRACKING:
            required_fields = ['error_type', 'error_message', 'user_impact']
        else:
            return v
            
        # Check required fields exist
        missing_fields = [field for field in required_fields if field not in v]
        if missing_fields:
            raise ValueError(f"Missing required properties for {event_type}: {missing_fields}")
            
        return v


class EventIngestionRequest(BaseModel):
    """Request model for event ingestion API."""
    events: List[AnalyticsEvent] = Field(..., description="List of events to ingest")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")
    
    @field_validator('events')
    @classmethod
    def validate_events_not_empty(cls, v):
        """Ensure events list is not empty."""
        if not v:
            raise ValueError("Events list cannot be empty")
        return v
    
    @field_validator('events')
    @classmethod
    def validate_max_batch_size(cls, v):
        """Ensure batch size doesn't exceed limit."""
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 events")
        return v


class EventIngestionResponse(BaseModel):
    """Response model for event ingestion API."""
    success: bool = Field(..., description="Whether ingestion was successful")
    events_processed: int = Field(..., description="Number of events processed")
    events_failed: int = Field(default=0, description="Number of events that failed")
    batch_id: Optional[str] = Field(None, description="Batch identifier if provided")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    event_ids: List[UUID] = Field(default_factory=list, description="List of processed event IDs")


class EventQueryRequest(BaseModel):
    """Request model for querying events."""
    event_types: Optional[List[EventType]] = Field(None, description="Filter by event types")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    session_id: Optional[str] = Field(None, description="Filter by session ID")
    start_time: Optional[datetime] = Field(None, description="Start time for filtering")
    end_time: Optional[datetime] = Field(None, description="End time for filtering")
    page_path: Optional[str] = Field(None, description="Filter by page path")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum events to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    order_by: str = Field(default="timestamp", description="Field to order by")
    order_desc: bool = Field(default=True, description="Order descending")


class EventQueryResponse(BaseModel):
    """Response model for event queries."""
    events: List[AnalyticsEvent] = Field(default_factory=list, description="List of events")
    total_count: int = Field(..., description="Total number of events matching filter")
    has_more: bool = Field(..., description="Whether more events are available")
    next_offset: Optional[int] = Field(None, description="Offset for next page")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")


class EventBatch(BaseModel):
    """Batch of events for bulk processing."""
    events: List[AnalyticsEvent] = Field(..., min_items=1, description="List of events in the batch")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")


class ProcessingResult(BaseModel):
    """Result of event processing operation."""
    processed_count: int = Field(..., description="Number of events successfully processed")
    failed_count: int = Field(default=0, description="Number of events that failed processing")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    success: bool = Field(default=True, description="Overall processing success status")
    
    @validator('success', always=True)
    def validate_success(cls, v, values):
        """Auto-calculate success based on failed count."""
        failed_count = values.get('failed_count', 0)
        return failed_count == 0


# REMOVED: Legacy models have been deprecated and removed to achieve SSOT compliance.
# Use AnalyticsEvent with appropriate properties for all event types.


# Export all models
__all__ = [
    # Enums
    "EventType",
    "EventCategory",
    "MessageType", 
    "ThreadAction",
    "QuestionType",
    "FeedbackType",
    "MetricType",
    "UserImpact",
    
    # Context and Properties
    "EventContext",
    "ChatInteractionProperties",
    "ThreadLifecycleProperties", 
    "FeatureUsageProperties",
    "SurveyResponseProperties",
    "FeedbackSubmissionProperties",
    "PerformanceMetricProperties",
    "ErrorTrackingProperties",
    "EventProperties",
    
    # Core Models
    "AnalyticsEvent",
    
    # API Models
    "EventIngestionRequest",
    "EventIngestionResponse", 
    "EventQueryRequest",
    "EventQueryResponse",
    "EventBatch",
    "ProcessingResult",
    
    # Legacy Models (REMOVED - see comment above for migration guidance)
]