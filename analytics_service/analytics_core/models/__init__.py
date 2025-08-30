"""Analytics Service Models - Single Source of Truth for All Analytics Data Models.

This module provides convenient access to all analytics model types from their canonical locations.
All models follow Netra's architectural compliance requirements for type safety and SSOT principles.

Business Value Justification (BVJ):
1. Segment: Early, Mid, Enterprise
2. Business Goal: Customer Insights, Product Optimization, System Reliability
3. Value Impact: Structured analytics data capture and reporting
4. Revenue Impact: 20% reduction in churn, 15% increase in feature adoption
"""

# Event models
from .events import (
    # Enums
    EventType,
    EventCategory,
    FeedbackType,
    MessageType,
    MetricType,
    QuestionType,
    ThreadAction,
    UserImpact,
    
    # Context and Properties
    ChatInteractionProperties,
    ErrorTrackingProperties,
    EventContext,
    EventProperties,
    FeatureUsageProperties,
    FeedbackSubmissionProperties,
    PerformanceMetricProperties,
    SurveyResponseProperties,
    ThreadLifecycleProperties,
    
    # Core Models
    AnalyticsEvent,
    
    # API Models
    EventIngestionRequest,
    EventIngestionResponse,
    EventQueryRequest,
    EventQueryResponse,
)

# Health check models
from .health import (
    # Enums
    HealthStatus,
    
    # Core Health Models
    ComponentHealth,
    HealthAlert,
    HealthCheckResponse,
    HealthCheckSummary,
)

# Report models  
from .reports import (
    # Enums
    Granularity,
    TimeRange,
    
    # User Activity Models
    UserActivityReportRequest,
    UserActivityReportResponse,
    UserActivitySummary,
    
    # Prompt Analytics Models
    PromptAnalyticsItem,
    PromptAnalyticsRequest,
    PromptAnalyticsResponse,
    
    # Real-time Metrics
    RealTimeMetrics,
    
    # Cohort Analysis Models
    CohortAnalysis,
    CohortAnalysisRequest,
    CohortAnalysisResponse,
    
    # Funnel Analysis Models
    FunnelAnalysisRequest,
    FunnelAnalysisResponse,
    FunnelStep,
)

__all__ = [
    # Event models - Enums
    "EventType",
    "EventCategory",
    "MessageType", 
    "ThreadAction",
    "QuestionType",
    "FeedbackType",
    "MetricType",
    "UserImpact",
    
    # Event models - Context and Properties
    "EventContext",
    "ChatInteractionProperties",
    "ThreadLifecycleProperties", 
    "FeatureUsageProperties",
    "SurveyResponseProperties",
    "FeedbackSubmissionProperties",
    "PerformanceMetricProperties",
    "ErrorTrackingProperties",
    "EventProperties",
    
    # Event models - Core
    "AnalyticsEvent",
    
    # Event models - API
    "EventIngestionRequest",
    "EventIngestionResponse", 
    "EventQueryRequest",
    "EventQueryResponse",
    
    # Health models - Enums
    "HealthStatus",
    
    # Health models - Core
    "ComponentHealth",
    "HealthCheckResponse",
    "HealthCheckSummary",
    "HealthAlert",
    
    # Report models - Enums
    "Granularity",
    "TimeRange",
    
    # Report models - User Activity
    "UserActivitySummary",
    "UserActivityReportRequest",
    "UserActivityReportResponse",
    
    # Report models - Prompt Analytics
    "PromptAnalyticsItem",
    "PromptAnalyticsRequest",
    "PromptAnalyticsResponse",
    
    # Report models - Real-time
    "RealTimeMetrics",
    
    # Report models - Cohort Analysis
    "CohortAnalysis",
    "CohortAnalysisRequest", 
    "CohortAnalysisResponse",
    
    # Report models - Funnel Analysis
    "FunnelStep",
    "FunnelAnalysisRequest",
    "FunnelAnalysisResponse"
]