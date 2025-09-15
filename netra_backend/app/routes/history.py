"""History API Routes

Provides REST API endpoints for conversation history management.
This implementation provides access to message history across conversations and threads,
with filtering and pagination capabilities.

Business Value: Platform/All Tiers - Essential conversation history functionality
"""

import time
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import get_current_active_user
from netra_backend.app.dependencies import DbDep
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.thread_helpers import (
    handle_get_messages_request,
    handle_route_with_error_logging,
)
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository

logger = central_logger.get_logger(__name__)

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
    redirect_slashes=False
)


class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    pagination: Dict[str, Any]


class MessageHistoryItem(BaseModel):
    id: str
    conversation_id: str
    thread_id: str
    content: str
    role: str
    timestamp: str
    metadata: Optional[dict] = None


async def get_history_handler(
    db: AsyncSession, 
    user_id: str,
    conversation_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    role: Optional[str] = None,
    content_search: Optional[str] = None,
    include_metadata: bool = False,
    limit: int = 20,
    offset: int = 0,
    order: str = "desc",
    order_by: str = "timestamp"
):
    """Handle get history request with filtering and pagination."""
    
    try:
        # Initialize repositories
        message_repo = MessageRepository()
        thread_repo = ThreadRepository()
        
        history_items = []
        total_count = 0
        
        if conversation_id or thread_id:
            # Get messages for specific conversation/thread
            target_id = conversation_id or thread_id
            
            # Validate thread access and ownership
            thread = await thread_repo.get_by_id(db, target_id)
            if not thread:
                raise HTTPException(status_code=404, detail="Conversation/thread not found")
            
            # Check if user has access to this thread
            # For now, we'll use the thread metadata to check user ownership
            if thread.metadata_ and thread.metadata_.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied to this conversation")
            
            # Get messages for the thread
            messages = await message_repo.get_by_thread(db, target_id, limit)
            
            for message in messages:
                # Convert message to history format
                content = ""
                if message.content and isinstance(message.content, list):
                    for content_item in message.content:
                        if content_item.get("type") == "text" and content_item.get("text"):
                            content = content_item["text"].get("value", "")
                            break
                elif isinstance(message.content, str):
                    content = message.content
                
                history_item = {
                    "id": message.id,
                    "conversation_id": message.thread_id,
                    "thread_id": message.thread_id,
                    "content": content,
                    "role": message.role,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(message.created_at)),
                    "metadata": message.metadata_ if include_metadata else None
                }
                
                # Apply role filter if specified
                if role and message.role != role:
                    continue
                
                # Apply content search if specified
                if content_search and content_search.lower() not in content.lower():
                    continue
                
                history_items.append(history_item)
            
            total_count = len(history_items)
            
        else:
            # Get messages across all user's threads
            user_threads = await thread_repo.get_by_user(db, user_id)
            
            for thread in user_threads:
                messages = await message_repo.get_by_thread(db, thread.id, 1000)  # Get more messages per thread
                
                for message in messages:
                    # Convert message to history format
                    content = ""
                    if message.content and isinstance(message.content, list):
                        for content_item in message.content:
                            if content_item.get("type") == "text" and content_item.get("text"):
                                content = content_item["text"].get("value", "")
                                break
                    elif isinstance(message.content, str):
                        content = message.content
                    
                    # Apply role filter if specified
                    if role and message.role != role:
                        continue
                    
                    # Apply content search if specified
                    if content_search and content_search.lower() not in content.lower():
                        continue
                    
                    history_item = {
                        "id": message.id,
                        "conversation_id": message.thread_id,
                        "thread_id": message.thread_id,
                        "content": content,
                        "role": message.role,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(message.created_at)),
                        "metadata": message.metadata_ if include_metadata else None
                    }
                    
                    history_items.append(history_item)
            
            total_count = len(history_items)
        
        # Apply ordering
        if order_by == "timestamp":
            history_items.sort(
                key=lambda x: x["timestamp"], 
                reverse=(order == "desc")
            )
        
        # Apply pagination
        paginated_items = history_items[offset:offset + limit]
        
        # Create pagination info
        pagination = {
            "limit": limit,
            "offset": offset,
            "total": total_count,
            "has_more": offset + limit < total_count
        }
        
        return {
            "history": paginated_items,
            "pagination": pagination
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.get("", response_model=HistoryResponse)
@router.get("/", response_model=HistoryResponse, include_in_schema=False)
async def get_history(
    db: DbDep,
    current_user = Depends(get_current_active_user),
    conversation_id: Optional[str] = Query(None, description="Filter by conversation ID"),
    thread_id: Optional[str] = Query(None, description="Filter by thread ID"),
    date_from: Optional[str] = Query(None, description="Filter messages from this date (ISO 8601)"),
    date_to: Optional[str] = Query(None, description="Filter messages to this date (ISO 8601)"),
    role: Optional[str] = Query(None, description="Filter by message role (user, assistant, system)"),
    content_search: Optional[str] = Query(None, description="Search in message content"),
    include_metadata: bool = Query(False, description="Include message metadata"),
    limit: int = Query(20, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    order: str = Query("desc", description="Sort order (asc, desc)"),
    order_by: str = Query("timestamp", description="Sort by field (timestamp, created_at)")
):
    """Get conversation history with filtering and pagination"""
    
    # Validate parameters
    if role and role not in ["user", "assistant", "system"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be user, assistant, or system")
    
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order. Must be asc or desc")
    
    if order_by not in ["timestamp", "created_at"]:
        raise HTTPException(status_code=400, detail="Invalid order_by. Must be timestamp or created_at")
    
    handler = lambda: get_history_handler(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        thread_id=thread_id,
        date_from=date_from,
        date_to=date_to,
        role=role,
        content_search=content_search,
        include_metadata=include_metadata,
        limit=limit,
        offset=offset,
        order=order,
        order_by=order_by
    )
    
    return await handle_route_with_error_logging(handler, "retrieving history")


@router.get("/conversation/{conversation_id}", response_model=HistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    db: DbDep,
    current_user = Depends(get_current_active_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    include_metadata: bool = Query(False)
):
    """Get history for a specific conversation"""
    
    handler = lambda: get_history_handler(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        include_metadata=include_metadata
    )
    
    return await handle_route_with_error_logging(handler, f"retrieving history for conversation {conversation_id}")


@router.get("/messages", response_model=HistoryResponse)
async def get_all_messages_history(
    db: DbDep,
    current_user = Depends(get_current_active_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None),
    content_search: Optional[str] = Query(None)
):
    """Get message history across all conversations"""
    
    handler = lambda: get_history_handler(
        db=db,
        user_id=current_user.id,
        role=role,
        content_search=content_search,
        limit=limit,
        offset=offset
    )
    
    return await handle_route_with_error_logging(handler, "retrieving all messages history")


@router.get("/export")
async def export_history(
    db: DbDep,
    current_user = Depends(get_current_active_user),
    conversation_id: Optional[str] = Query(None),
    format: str = Query("json", description="Export format (json, csv)")
):
    """Export conversation history"""
    
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be json or csv")
    
    # For now, return a simple JSON export
    # This could be enhanced to support different formats
    handler = lambda: get_history_handler(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=1000,  # Large limit for export
        offset=0,
        include_metadata=True
    )
    
    return await handle_route_with_error_logging(handler, "exporting history")