"""Conversations API Routes

Provides REST API endpoints for conversation management.
This implementation acts as an alias for the existing thread infrastructure,
providing conversations as a consumer-friendly view of threads.

Business Value: Platform/All Tiers - Essential conversation management functionality
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
    handle_create_thread_request,
    handle_delete_thread_request,
    handle_get_thread_request,
    handle_list_threads_request,
    handle_route_with_error_logging,
    handle_update_thread_request,
)

logger = central_logger.get_logger(__name__)

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    redirect_slashes=False
)


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class ConversationResponse(BaseModel):
    id: str
    object: str = "conversation"
    title: Optional[str] = None
    created_at: int
    updated_at: Optional[int] = None
    metadata: Optional[dict] = None
    message_count: int = 0


async def list_conversations_handler(db: AsyncSession, user_id: str, offset: int, limit: int):
    """Handle list conversations request - delegates to thread infrastructure."""
    # Reuse existing thread infrastructure
    thread_responses = await handle_list_threads_request(db, user_id, offset, limit)
    
    # Convert thread responses to conversation format
    conversations = []
    for thread in thread_responses:
        conversation = {
            "id": thread["id"],
            "object": "conversation",
            "title": thread.get("title"),
            "created_at": thread["created_at"],
            "updated_at": thread.get("updated_at"),
            "metadata": thread.get("metadata", {}),
            "message_count": thread.get("message_count", 0)
        }
        conversations.append(conversation)
    
    return conversations


async def create_conversation_handler(db: AsyncSession, conversation_data: ConversationCreate, user_id: str):
    """Handle create conversation request - delegates to thread infrastructure."""
    # Convert conversation data to thread data format
    from netra_backend.app.routes.threads_route import ThreadCreate
    thread_data = ThreadCreate(
        title=conversation_data.title,
        metadata=conversation_data.metadata
    )
    
    # Delegate to existing thread creation logic
    thread_response = await handle_create_thread_request(db, thread_data, user_id)
    
    # Convert thread response to conversation format
    return {
        "id": thread_response["id"],
        "object": "conversation",
        "title": thread_response.get("title"),
        "created_at": thread_response["created_at"],
        "updated_at": thread_response.get("updated_at"),
        "metadata": thread_response.get("metadata", {}),
        "message_count": thread_response.get("message_count", 0)
    }


async def get_conversation_handler(db: AsyncSession, conversation_id: str, user_id: str):
    """Handle get conversation request - delegates to thread infrastructure."""
    # Delegate to existing thread get logic
    thread_response = await handle_get_thread_request(db, conversation_id, user_id)
    
    # Convert thread response to conversation format
    return {
        "id": thread_response["id"],
        "object": "conversation",
        "title": thread_response.get("title"),
        "created_at": thread_response["created_at"],
        "updated_at": thread_response.get("updated_at"),
        "metadata": thread_response.get("metadata", {}),
        "message_count": thread_response.get("message_count", 0)
    }


async def update_conversation_handler(db: AsyncSession, conversation_id: str, conversation_update: ConversationUpdate, user_id: str):
    """Handle update conversation request - delegates to thread infrastructure."""
    # Convert conversation update to thread update format
    from netra_backend.app.routes.threads_route import ThreadUpdate
    thread_update = ThreadUpdate(
        title=conversation_update.title,
        metadata=conversation_update.metadata
    )
    
    # Delegate to existing thread update logic
    thread_response = await handle_update_thread_request(db, conversation_id, thread_update, user_id)
    
    # Convert thread response to conversation format
    return {
        "id": thread_response["id"],
        "object": "conversation",
        "title": thread_response.get("title"),
        "created_at": thread_response["created_at"],
        "updated_at": thread_response.get("updated_at"),
        "metadata": thread_response.get("metadata", {}),
        "message_count": thread_response.get("message_count", 0)
    }


async def delete_conversation_handler(db: AsyncSession, conversation_id: str, user_id: str):
    """Handle delete conversation request - delegates to thread infrastructure."""
    # Delegate to existing thread delete logic
    return await handle_delete_thread_request(db, conversation_id, user_id)


@router.get("", response_model=List[ConversationResponse])
@router.get("/", response_model=List[ConversationResponse], include_in_schema=False)
async def list_conversations(
    db: DbDep, 
    current_user = Depends(get_current_active_user),
    limit: int = Query(20, le=100), 
    offset: int = Query(0, ge=0)
):
    """List all conversations for the current user"""
    handler = lambda: list_conversations_handler(db, current_user.id, offset, limit)
    return await handle_route_with_error_logging(handler, "listing conversations")


@router.post("", response_model=ConversationResponse)
@router.post("/", response_model=ConversationResponse, include_in_schema=False)
async def create_conversation(
    conversation_data: ConversationCreate, 
    db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Create a new conversation"""
    handler = lambda: create_conversation_handler(db, conversation_data, current_user.id)
    return await handle_route_with_error_logging(handler, "creating conversation")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str, 
    db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Get a specific conversation"""
    handler = lambda: get_conversation_handler(db, conversation_id, current_user.id)
    return await handle_route_with_error_logging(handler, f"getting conversation {conversation_id}")


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str, 
    conversation_update: ConversationUpdate, 
    db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Update a conversation"""
    handler = lambda: update_conversation_handler(db, conversation_id, conversation_update, current_user.id)
    return await handle_route_with_error_logging(handler, f"updating conversation {conversation_id}")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str, 
    db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Delete (archive) a conversation"""
    handler = lambda: delete_conversation_handler(db, conversation_id, current_user.id)
    return await handle_route_with_error_logging(handler, f"deleting conversation {conversation_id}")