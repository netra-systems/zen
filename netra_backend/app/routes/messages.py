"""
Messages API Router - HTTP endpoint for message operations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Core Chat Functionality  
- Value Impact: Provides HTTP API access to messages for external integrations
- Revenue Impact: Enables third-party integrations and REST-based chat clients

This router provides HTTP endpoints for message operations, complementing
the WebSocket-based real-time messaging system.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.user_context_extractor import get_user_context_extractor

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["Messages"])

# Security
security = HTTPBearer()

# Response Models
class MessageResponse(BaseModel):
    """Response model for individual messages."""
    id: str
    content: str
    user_id: str
    thread_id: str
    timestamp: datetime
    message_type: str = "user"
    metadata: Optional[Dict[str, Any]] = None

class MessagesListResponse(BaseModel):
    """Response model for message lists."""
    messages: List[MessageResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class MessageCreateRequest(BaseModel):
    """Request model for creating messages."""
    content: str = Field(..., min_length=1, max_length=8000)
    thread_id: str = Field(..., min_length=1)
    message_type: str = Field(default="user")
    metadata: Optional[Dict[str, Any]] = None

class MessageCreateResponse(BaseModel):
    """Response model for created messages."""
    message: MessageResponse
    status: str = "created"

# Authentication Helper
async def get_current_user_from_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token."""
    try:
        extractor = get_user_context_extractor()
        
        # Validate and decode JWT
        jwt_payload = extractor.validate_and_decode_jwt(credentials.credentials)
        if not jwt_payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired JWT token"
            )
        
        user_id = jwt_payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="JWT token missing user ID"
            )
        
        return user_id
        
    except Exception as e:
        logger.error(f"JWT authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

# Message Storage (Mock Implementation)
# NOTE: This is a temporary in-memory storage for the initial implementation
# In production, this would connect to the database
_message_store: Dict[str, MessageResponse] = {}
_messages_by_user: Dict[str, List[str]] = {}
_messages_by_thread: Dict[str, List[str]] = {}

def _store_message(message: MessageResponse) -> None:
    """Store message in temporary storage."""
    _message_store[message.id] = message
    
    # Index by user
    if message.user_id not in _messages_by_user:
        _messages_by_user[message.user_id] = []
    _messages_by_user[message.user_id].append(message.id)
    
    # Index by thread
    if message.thread_id not in _messages_by_thread:
        _messages_by_thread[message.thread_id] = []
    _messages_by_thread[message.thread_id].append(message.id)

def _get_user_messages(user_id: str, limit: int = 50, offset: int = 0) -> List[MessageResponse]:
    """Get messages for a user."""
    message_ids = _messages_by_user.get(user_id, [])
    # Sort by timestamp (newest first)
    messages = [_message_store[mid] for mid in message_ids if mid in _message_store]
    messages.sort(key=lambda m: m.timestamp, reverse=True)
    return messages[offset:offset + limit]

def _get_thread_messages(thread_id: str, limit: int = 50, offset: int = 0) -> List[MessageResponse]:
    """Get messages for a thread."""
    message_ids = _messages_by_thread.get(thread_id, [])
    # Sort by timestamp (oldest first for thread view)
    messages = [_message_store[mid] for mid in message_ids if mid in _message_store]
    messages.sort(key=lambda m: m.timestamp)
    return messages[offset:offset + limit]

# API Endpoints

@router.get("/messages", response_model=MessagesListResponse)
async def list_messages(
    thread_id: Optional[str] = Query(None, description="Filter messages by thread ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: str = Depends(get_current_user_from_jwt)
) -> MessagesListResponse:
    """
    List messages for the authenticated user.
    
    This endpoint supports:
    - Getting all user messages (no thread_id)
    - Getting messages for a specific thread (with thread_id)
    - Pagination via limit/offset
    """
    try:
        logger.info(f"Listing messages for user {current_user[:8]}... (thread: {thread_id}, limit: {limit}, offset: {offset})")
        
        if thread_id:
            messages = _get_thread_messages(thread_id, limit, offset)
            total_count = len(_messages_by_thread.get(thread_id, []))
        else:
            messages = _get_user_messages(current_user, limit, offset)
            total_count = len(_messages_by_user.get(current_user, []))
        
        has_more = offset + len(messages) < total_count
        page = (offset // limit) + 1
        
        response = MessagesListResponse(
            messages=messages,
            total_count=total_count,
            page=page,
            page_size=limit,
            has_more=has_more
        )
        
        logger.info(f"Returned {len(messages)} messages for user {current_user[:8]}... (total: {total_count})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing messages for user {current_user}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve messages"
        )

@router.post("/messages", response_model=MessageCreateResponse)
async def create_message(
    request: MessageCreateRequest,
    current_user: str = Depends(get_current_user_from_jwt)
) -> MessageCreateResponse:
    """
    Create a new message.
    
    This endpoint creates a message and stores it. In a real implementation,
    this would also trigger WebSocket events and agent processing.
    """
    try:
        logger.info(f"Creating message for user {current_user[:8]}... in thread {request.thread_id}")
        
        # Create message
        message = MessageResponse(
            id=str(uuid4()),
            content=request.content,
            user_id=current_user,
            thread_id=request.thread_id,
            timestamp=datetime.now(timezone.utc),
            message_type=request.message_type,
            metadata=request.metadata
        )
        
        # Store message
        _store_message(message)
        
        response = MessageCreateResponse(
            message=message,
            status="created"
        )
        
        logger.info(f"Created message {message.id} for user {current_user[:8]}...")
        
        # TODO: In real implementation, trigger WebSocket events and agent processing here
        # This would include:
        # 1. Sending WebSocket message to connected clients
        # 2. Triggering agent processing if needed
        # 3. Storing in database
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message for user {current_user}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create message"
        )

@router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> MessageResponse:
    """
    Get a specific message by ID.
    
    Users can only access their own messages.
    """
    try:
        logger.info(f"Getting message {message_id} for user {current_user[:8]}...")
        
        message = _message_store.get(message_id)
        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found"
            )
        
        # Security check: users can only access their own messages
        if message.user_id != current_user:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own messages"
            )
        
        logger.info(f"Retrieved message {message_id} for user {current_user[:8]}...")
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message {message_id} for user {current_user}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve message"
        )

@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> Dict[str, str]:
    """
    Delete a specific message by ID.
    
    Users can only delete their own messages.
    """
    try:
        logger.info(f"Deleting message {message_id} for user {current_user[:8]}...")
        
        message = _message_store.get(message_id)
        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found"
            )
        
        # Security check: users can only delete their own messages
        if message.user_id != current_user:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only delete your own messages"
            )
        
        # Remove from storage
        del _message_store[message_id]
        
        # Remove from indexes
        if message.user_id in _messages_by_user:
            _messages_by_user[message.user_id] = [
                mid for mid in _messages_by_user[message.user_id] if mid != message_id
            ]
        
        if message.thread_id in _messages_by_thread:
            _messages_by_thread[message.thread_id] = [
                mid for mid in _messages_by_thread[message.thread_id] if mid != message_id
            ]
        
        logger.info(f"Deleted message {message_id} for user {current_user[:8]}...")
        return {"status": "deleted", "message_id": message_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message {message_id} for user {current_user}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete message"
        )

# Health check for messages API
@router.get("/messages/health")
async def messages_health() -> Dict[str, Any]:
    """Health check for messages API."""
    return {
        "status": "healthy",
        "service": "messages-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_messages": len(_message_store),
            "total_users": len(_messages_by_user),
            "total_threads": len(_messages_by_thread)
        }
    }