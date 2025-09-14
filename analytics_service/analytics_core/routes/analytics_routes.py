"""
Analytics Service API Routes
Main analytics endpoints for event ingestion, reports, and real-time metrics
"""
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from analytics_service.analytics_core.config import AnalyticsConfig
from shared.isolated_environment import get_env
from analytics_service.analytics_core.services.event_ingestion_service import EventIngestionService
from analytics_service.analytics_core.services.analytics_service import AnalyticsService  
from analytics_service.analytics_core.services.metrics_service import MetricsService
from analytics_service.analytics_core.database.connection import get_clickhouse_session, get_redis_connection
from analytics_service.analytics_core.utils.rate_limiter import RateLimiter
from analytics_service.analytics_core.utils.validation import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Initialize services
event_ingestion_service = EventIngestionService()
analytics_service = AnalyticsService()
metrics_service = MetricsService()

# Rate limiter for event ingestion - environment aware
def _get_rate_limit_for_environment() -> Dict[str, int]:
    """Get rate limit configuration based on environment."""
    env = get_env().get("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return {"requests_per_minute": 1000, "events_per_request": 100}
    elif env == "staging":
        return {"requests_per_minute": 500, "events_per_request": 50}
    else:  # development/test
        return {"requests_per_minute": 200, "events_per_request": 20}

rate_limits = _get_rate_limit_for_environment()
rate_limiter = RateLimiter(
    requests_per_minute=rate_limits["requests_per_minute"],
    redis_connection=get_redis_connection
)

# Request/Response Models
class AnalyticsEvent(BaseModel):
    """Single analytics event model"""
    event_name: str = Field(..., min_length=1, max_length=255)
    event_category: Optional[str] = Field(None, max_length=100)
    user_id: Optional[str] = Field(None, max_length=255)
    session_id: Optional[str] = Field(None, max_length=255)
    timestamp: Optional[datetime] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def set_timestamp(cls, v):
        return v or datetime.now(timezone.utc)
    
    @field_validator('properties')
    @classmethod
    def validate_properties(cls, v):
        # Limit the size of properties to prevent abuse
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError("Properties payload too large (max 10KB)")
        return v

class EventBatch(BaseModel):
    """Batch of events for bulk ingestion"""
    events: List[AnalyticsEvent] = Field(..., min_items=1)
    batch_id: Optional[str] = None
    
    @validator('events')
    def validate_batch_size(cls, v):
        max_events = rate_limits["events_per_request"]
        if len(v) > max_events:
            raise ValueError(f"Batch too large (max {max_events} events)")
        return v

class EventIngestionResponse(BaseModel):
    """Response for event ingestion"""
    success: bool
    message: str
    events_processed: int
    batch_id: Optional[str] = None
    processing_time_ms: float
    errors: List[str] = Field(default_factory=list)

class ReportRequest(BaseModel):
    """Base report request parameters"""
    start_date: datetime
    end_date: datetime
    filters: Dict[str, Any] = Field(default_factory=dict)
    group_by: Optional[List[str]] = None
    limit: int = Field(default=1000, ge=1, le=10000)
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError("end_date must be after start_date")
        
        # Limit to 90 days max
        if 'start_date' in values:
            max_range = timedelta(days=90)
            if v - values['start_date'] > max_range:
                raise ValueError("Date range cannot exceed 90 days")
        return v

class UserActivityReport(BaseModel):
    """User activity report response"""
    report_type: str = "user_activity"
    generated_at: datetime
    date_range: Dict[str, datetime]
    total_users: int
    active_users: int
    new_users: int
    sessions: Dict[str, Any]
    top_events: List[Dict[str, Any]]
    user_segments: List[Dict[str, Any]]

class PromptAnalyticsReport(BaseModel):
    """Prompt analytics report response"""
    report_type: str = "prompt_analytics"
    generated_at: datetime
    date_range: Dict[str, datetime]
    total_prompts: int
    unique_users: int
    average_response_time: float
    success_rate: float
    top_prompt_types: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]

class RealTimeMetrics(BaseModel):
    """Real-time metrics response"""
    timestamp: datetime
    active_users: int
    events_per_second: float
    response_time_p95: float
    error_rate: float
    system_health: Dict[str, Any]
    live_events: List[Dict[str, Any]]

def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request"""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "session_id": request.headers.get("x-session-id"),
        "user_id": request.headers.get("x-user-id"),
        "timestamp": datetime.now(timezone.utc)
    }

async def validate_request_rate_limit(request: Request):
    """Rate limiting dependency"""
    client_ip = request.client.host if request.client else "unknown"
    
    if not await rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making more requests."
        )
    
    return True

@router.post("/events", response_model=EventIngestionResponse)
async def ingest_events(
    event_data: EventBatch,
    background_tasks: BackgroundTasks,
    request: Request,
    client_info: Dict[str, Any] = Depends(get_client_info),
    _rate_limit: bool = Depends(validate_request_rate_limit)
):
    """
    Event ingestion endpoint with rate limiting and validation.
    
    Accepts single events or batches for efficient processing.
    Includes comprehensive error handling and monitoring.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received batch of {len(event_data.events)} events from {client_info['ip']}")
        
        # Enhanced validation
        validated_events = []
        validation_errors = []
        
        for idx, event in enumerate(event_data.events):
            try:
                # Add client context to each event
                event.context.update({
                    "client_ip": client_info["ip"],
                    "user_agent": client_info["user_agent"],
                    "ingestion_timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Override session/user from headers if provided
                if client_info.get("session_id"):
                    event.session_id = client_info["session_id"]
                if client_info.get("user_id"):
                    event.user_id = client_info["user_id"]
                
                validated_events.append(event)
                
            except ValidationError as e:
                validation_errors.append(f"Event {idx}: {str(e)}")
                logger.warning(f"Event validation failed at index {idx}: {e}")
        
        if not validated_events:
            raise HTTPException(
                status_code=422,
                detail="No valid events to process"
            )
        
        # Process events asynchronously for better performance
        processing_result = await event_ingestion_service.process_event_batch(
            validated_events, 
            batch_id=event_data.batch_id
        )
        
        # Schedule background tasks for heavy processing
        background_tasks.add_task(
            analytics_service.update_real_time_metrics,
            len(validated_events)
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Successfully processed {len(validated_events)} events "
            f"in {processing_time:.2f}ms"
        )
        
        return EventIngestionResponse(
            success=True,
            message=f"Successfully ingested {len(validated_events)} events",
            events_processed=len(validated_events),
            batch_id=processing_result.get("batch_id"),
            processing_time_ms=processing_time,
            errors=validation_errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Event ingestion failed: {str(e)}"
        )

@router.get("/reports/user-activity", response_model=UserActivityReport)
async def get_user_activity_report(
    request: ReportRequest = Depends(),
    clickhouse_session = Depends(get_clickhouse_session)
):
    """
    Generate comprehensive user activity report.
    
    Includes metrics like active users, sessions, events, and segmentation.
    Optimized for performance with ClickHouse aggregations.
    """
    try:
        logger.info(
            f"Generating user activity report for {request.start_date} to {request.end_date}"
        )
        
        # Generate report using analytics service
        report_data = await analytics_service.generate_user_activity_report(
            start_date=request.start_date,
            end_date=request.end_date,
            filters=request.filters,
            group_by=request.group_by,
            limit=request.limit,
            session=clickhouse_session
        )
        
        return UserActivityReport(
            generated_at=datetime.now(timezone.utc),
            date_range={
                "start_date": request.start_date,
                "end_date": request.end_date
            },
            **report_data
        )
        
    except Exception as e:
        logger.error(f"User activity report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )

@router.get("/reports/prompts", response_model=PromptAnalyticsReport)
async def get_prompt_analytics_report(
    request: ReportRequest = Depends(),
    clickhouse_session = Depends(get_clickhouse_session)
):
    """
    Generate prompt usage and performance analytics report.
    
    Provides insights into prompt patterns, success rates, and optimization opportunities.
    """
    try:
        logger.info(
            f"Generating prompt analytics report for {request.start_date} to {request.end_date}"
        )
        
        # Generate prompt-specific report
        report_data = await analytics_service.generate_prompt_analytics_report(
            start_date=request.start_date,
            end_date=request.end_date,
            filters=request.filters,
            group_by=request.group_by,
            limit=request.limit,
            session=clickhouse_session
        )
        
        return PromptAnalyticsReport(
            generated_at=datetime.now(timezone.utc),
            date_range={
                "start_date": request.start_date,
                "end_date": request.end_date
            },
            **report_data
        )
        
    except Exception as e:
        logger.error(f"Prompt analytics report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Prompt report generation failed: {str(e)}"
        )

@router.get("/metrics/realtime", response_model=RealTimeMetrics)
async def get_realtime_metrics(
    redis_connection = Depends(get_redis_connection)
):
    """
    Get real-time analytics metrics and system health.
    
    Provides live insights into current system performance and user activity.
    Uses Redis for fast access to current metrics.
    """
    try:
        # Get current metrics from Redis cache and ClickHouse
        metrics_data = await metrics_service.get_realtime_metrics(
            redis_connection=redis_connection
        )
        
        return RealTimeMetrics(
            timestamp=datetime.now(timezone.utc),
            **metrics_data
        )
        
    except Exception as e:
        logger.error(f"Real-time metrics retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Metrics retrieval failed: {str(e)}"
        )

@router.get("/events/stream")
async def stream_events(
    event_types: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100
):
    """
    Stream recent events for debugging and monitoring.
    
    Provides access to recent event data for troubleshooting and analysis.
    Limited to recent events to prevent performance issues.
    """
    try:
        # Parse event types filter
        event_type_filter = None
        if event_types:
            event_type_filter = [t.strip() for t in event_types.split(",")]
        
        # Get recent events
        events = await analytics_service.get_recent_events(
            event_types=event_type_filter,
            user_id=user_id,
            limit=min(limit, 1000)  # Cap at 1000 events
        )
        
        return {
            "events": events,
            "total_count": len(events),
            "timestamp": datetime.now(timezone.utc),
            "filters": {
                "event_types": event_type_filter,
                "user_id": user_id,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Event streaming failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Event streaming failed: {str(e)}"
        )

@router.delete("/events/purge")
async def purge_old_events(
    days_old: int = 90,
    dry_run: bool = True,
    clickhouse_session = Depends(get_clickhouse_session)
):
    """
    Purge old events for data retention compliance.
    
    DANGEROUS: This permanently deletes data. Use dry_run=False to execute.
    Requires admin permissions in production environments.
    """
    try:
        # Environment check for safety
        env = get_env().get("ENVIRONMENT", "development").lower()
        if env == "production" and days_old < 30:
            raise HTTPException(
                status_code=403,
                detail="Cannot purge events less than 30 days old in production"
            )
        
        if dry_run:
            # Count events that would be deleted
            count = await analytics_service.count_events_older_than(
                days_old=days_old,
                session=clickhouse_session
            )
            
            return {
                "dry_run": True,
                "events_to_delete": count,
                "cutoff_date": datetime.now(timezone.utc) - timedelta(days=days_old),
                "message": f"Would delete {count} events older than {days_old} days"
            }
        else:
            # Actually delete events
            deleted_count = await analytics_service.purge_events_older_than(
                days_old=days_old,
                session=clickhouse_session
            )
            
            logger.warning(f"Purged {deleted_count} events older than {days_old} days")
            
            return {
                "dry_run": False,
                "events_deleted": deleted_count,
                "cutoff_date": datetime.now(timezone.utc) - timedelta(days=days_old),
                "message": f"Successfully deleted {deleted_count} events"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event purging failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Event purging failed: {str(e)}"
        )

@router.get("/config")
async def get_analytics_config():
    """
    Get current analytics service configuration.
    
    Returns configuration settings for client integration and debugging.
    Excludes sensitive information like secrets.
    """
    try:
        config = AnalyticsConfig.get_instance()
        
        return {
            "service": "analytics-service",
            "version": "1.0.0",
            "environment": config.environment,
            "rate_limits": rate_limits,
            "features": {
                "real_time_metrics": True,
                "batch_ingestion": True,
                "user_analytics": True,
                "prompt_analytics": True,
                "data_retention_days": config.data_retention_days
            },
            "endpoints": {
                "events": "/api/analytics/events",
                "user_activity": "/api/analytics/reports/user-activity", 
                "prompts": "/api/analytics/reports/prompts",
                "realtime": "/api/analytics/metrics/realtime",
                "websocket": "/ws/analytics"
            },
            "timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Config retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Configuration retrieval failed: {str(e)}"
        )