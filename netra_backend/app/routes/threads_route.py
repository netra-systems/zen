"""Thread Management Routes

Handles thread CRUD operations and thread history.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import get_current_active_user
from netra_backend.app.dependencies import DbDep
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.thread_helpers import (
    handle_auto_rename_request,
    handle_create_thread_request,
    handle_delete_thread_request,
    handle_get_messages_request,
    handle_get_thread_request,
    handle_list_threads_request,
    handle_route_with_error_logging,
    handle_update_thread_request,
)
from netra_backend.app.services.thread_analytics import thread_analytics
from netra_backend.app.services.thread_service import thread_service

logger = central_logger.get_logger(__name__)

router = APIRouter(
    prefix="/api/threads",
    tags=["threads"],
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

class ThreadCreate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None

class ThreadResponse(BaseModel):
    id: str
    object: str = "thread"
    title: Optional[str] = None
    created_at: int
    updated_at: Optional[int] = None
    metadata: Optional[dict] = None
    message_count: int = 0

@router.get("", response_model=List[ThreadResponse])
@router.get("/", response_model=List[ThreadResponse], include_in_schema=False)
async def list_threads(
    db: DbDep, current_user = Depends(get_current_active_user),
    limit: int = Query(20, le=100), offset: int = Query(0, ge=0)
):
    """List all threads for the current user"""
    handler = lambda: handle_list_threads_request(db, current_user.id, offset, limit)
    return await handle_route_with_error_logging(handler, "listing threads")

@router.post("", response_model=ThreadResponse)
@router.post("/", response_model=ThreadResponse, include_in_schema=False)
async def create_thread(
    thread_data: ThreadCreate, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Create a new thread"""
    handler = lambda: handle_create_thread_request(db, thread_data, current_user.id)
    return await handle_route_with_error_logging(handler, "creating thread")

@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Get a specific thread"""
    handler = lambda: handle_get_thread_request(db, thread_id, current_user.id)
    return await handle_route_with_error_logging(handler, f"getting thread {thread_id}")

@router.put("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str, thread_update: ThreadUpdate, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Update a thread"""
    handler = lambda: handle_update_thread_request(db, thread_id, thread_update, current_user.id)
    return await handle_route_with_error_logging(handler, f"updating thread {thread_id}")

@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Delete (archive) a thread"""
    handler = lambda: handle_delete_thread_request(db, thread_id, current_user.id)
    return await handle_route_with_error_logging(handler, f"deleting thread {thread_id}")

@router.get("/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str, db: DbDep, current_user = Depends(get_current_active_user),
    limit: int = Query(50, le=100), offset: int = Query(0, ge=0)
):
    """Get messages for a specific thread"""
    handler = lambda: handle_get_messages_request(db, thread_id, current_user.id, limit, offset)
    return await handle_route_with_error_logging(handler, f"getting messages for thread {thread_id}")


class SendMessageRequest(BaseModel):
    """Request model for sending a message to a thread."""
    message: str = Field(..., description="Message content to send")
    metadata: Optional[dict] = Field(None, description="Additional message metadata")


class SendMessageResponse(BaseModel):
    """Response model for sending a message to a thread."""
    id: str = Field(..., description="Message ID")
    thread_id: str = Field(..., description="Thread ID")
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user/assistant)")
    created_at: int = Field(..., description="Creation timestamp")


@router.post("/{thread_id}/messages", response_model=SendMessageResponse)
async def send_thread_message(
    thread_id: str, 
    request: SendMessageRequest,
    db: DbDep, 
    current_user = Depends(get_current_active_user)
):
    """Send a message to a specific thread"""
    from netra_backend.app.routes.utils.thread_helpers import handle_send_message_request
    
    handler = lambda: handle_send_message_request(
        db, thread_id, request, current_user.id
    )
    return await handle_route_with_error_logging(
        handler, f"sending message to thread {thread_id}"
    )

@router.post("/{thread_id}/auto-rename")
async def auto_rename_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Automatically generate a title for thread based on first message"""
    handler = lambda: handle_auto_rename_request(db, thread_id, current_user.id)
    return await handle_route_with_error_logging(handler, f"auto-renaming thread {thread_id}")

@router.post("/statistics")
async def get_thread_statistics(
    stats_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Get thread usage statistics - NOT IMPLEMENTED"""
    # TODO: Implement thread statistics using ThreadRepository
    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="Thread statistics not implemented")

@router.post("/analytics/dashboard")
async def get_analytics_dashboard(
    dashboard_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Get thread analytics dashboard"""
    return await thread_analytics.get_analytics_dashboard(dashboard_request)

@router.post("/analytics")
async def get_thread_analytics(
    analytics_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Get thread analytics data"""
    return await thread_analytics.get_dashboard_data(analytics_request)

@router.post("/bulk")
async def bulk_thread_operations(
    bulk_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Perform bulk operations on threads - NOT IMPLEMENTED"""
    # TODO: Implement bulk operations using ThreadRepository
    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="Bulk thread operations not implemented")

@router.post("/sentiment")
async def analyze_thread_sentiment(
    sentiment_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Analyze sentiment of threads"""
    return thread_service.analyze_sentiment(sentiment_request)

@router.post("/metrics")
async def get_thread_metrics(
    metrics_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Get thread performance metrics"""
    return thread_service.get_performance_metrics(metrics_request)

@router.post("/cleanup")
async def cleanup_old_threads(
    cleanup_request: dict,
    current_user = Depends(get_current_active_user)
):
    """Cleanup old inactive threads"""
    return thread_service.cleanup_old_threads(cleanup_request)