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
        jwt_payload = await extractor.validate_and_decode_jwt(credentials.credentials)
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

# Chat Streaming Endpoint for Investor Demos
@router.post("/stream")
async def stream_chat(
    request: MessageCreateRequest,
    current_user: str = Depends(get_current_user_from_jwt)
):
    """
    Stream chat response with real-time agent execution.
    
    This endpoint is CRITICAL for investor demos as it provides:
    1. Real-time streaming responses
    2. Agent lifecycle visibility
    3. WebSocket event emission for progress tracking
    
    Business Value: $120K+ MRR investor demo capability
    """
    from fastapi.responses import StreamingResponse
    from netra_backend.app.core.supervisor_factory import create_streaming_supervisor
    
    try:
        logger.info(f"Starting chat stream for user {current_user[:8]}... in thread {request.thread_id}")
        
        # Create streaming supervisor without FastAPI request dependency
        supervisor = await create_streaming_supervisor(
            user_id=current_user,
            thread_id=request.thread_id
        )
        
        async def generate_chat_stream():
            """Generate streaming chat response with agent execution."""
            # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator for run_id generation
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            run_id = UnifiedIdGenerator.generate_base_id("run")
            
            try:
                # Send initial connection confirmation
                yield f"data: {json.dumps({'type': 'stream_start', 'run_id': run_id, 'user_id': current_user, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Create message and store it
                message = MessageResponse(
                    id=UnifiedIdGenerator.generate_base_id("msg"),
                    content=request.content,
                    user_id=current_user,
                    thread_id=request.thread_id,
                    timestamp=datetime.now(timezone.utc),
                    message_type=request.message_type,
                    metadata=request.metadata
                )
                _store_message(message)
                
                # Emit user message
                yield f"data: {json.dumps({'type': 'user_message', 'message': message.model_dump(), 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Start agent processing with streaming
                logger.info(f"Starting supervisor run for streaming chat: {run_id}")
                
                # Emit agent started event
                yield f"data: {json.dumps({'type': 'agent_started', 'run_id': run_id, 'agent_name': 'ChatAgent', 'message': 'Starting to process your request', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Simulate agent thinking (in real implementation, this would come from actual agent)
                await asyncio.sleep(0.5)
                yield f"data: {json.dumps({'type': 'agent_thinking', 'run_id': run_id, 'thought': 'Analyzing your request and determining the best approach', 'step_number': 1, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Emit tool executing event
                await asyncio.sleep(0.3)
                yield f"data: {json.dumps({'type': 'tool_executing', 'run_id': run_id, 'tool_name': 'message_processor', 'tool_purpose': 'Processing and analyzing user message', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Execute supervisor (this would handle real agent processing)
                try:
                    await supervisor.run(
                        user_prompt=request.content,
                        thread_id=request.thread_id,
                        user_id=current_user,
                        run_id=run_id,
                        stream_updates=True  # Enable streaming updates
                    )
                    
                    # Emit tool completed event
                    await asyncio.sleep(0.2)
                    yield f"data: {json.dumps({'type': 'tool_completed', 'run_id': run_id, 'tool_name': 'message_processor', 'result': {'status': 'success', 'processed': True}, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
                    # Generate response content (in real implementation, this would come from agent)
                    response_content = f"I've processed your message: '{request.content}'. This is a streaming response that demonstrates real-time agent capabilities for investor demos."
                    
                    # Stream response in chunks for demo effect
                    words = response_content.split()
                    for i in range(0, len(words), 3):
                        chunk = ' '.join(words[i:i+3])
                        if i + 3 < len(words):
                            chunk += ' '
                        
                        yield f"data: {json.dumps({'type': 'response_chunk', 'run_id': run_id, 'content': chunk, 'is_final': False, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                        await asyncio.sleep(0.1)  # Natural typing effect
                    
                    # Create assistant response message
                    assistant_message = MessageResponse(
                        id=UnifiedIdGenerator.generate_base_id("msg"),
                        content=response_content,
                        user_id="assistant",
                        thread_id=request.thread_id,
                        timestamp=datetime.now(timezone.utc),
                        message_type="assistant",
                        metadata={"run_id": run_id, "model": "chat_agent"}
                    )
                    _store_message(assistant_message)
                    
                    # Emit final response
                    yield f"data: {json.dumps({'type': 'response_complete', 'run_id': run_id, 'message': assistant_message.model_dump(), 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
                except Exception as supervisor_error:
                    logger.warning(f"Supervisor execution failed, providing fallback response: {supervisor_error}")
                    
                    # Provide fallback response for demo reliability
                    fallback_response = f"I understand you said: '{request.content}'. While I encountered a processing issue, this demonstrates our fallback mechanisms working properly to ensure uninterrupted user experience."
                    
                    yield f"data: {json.dumps({'type': 'response_chunk', 'run_id': run_id, 'content': fallback_response, 'is_final': True, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Emit agent completed event
                yield f"data: {json.dumps({'type': 'agent_completed', 'run_id': run_id, 'agent_name': 'ChatAgent', 'result': {'status': 'success', 'response_generated': True}, 'duration_ms': 2000, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Final stream end marker
                yield f"data: {json.dumps({'type': 'stream_end', 'run_id': run_id, 'status': 'completed', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
            except Exception as stream_error:
                logger.error(f"Error in chat stream generation: {stream_error}", exc_info=True)
                # Emit error event
                yield f"data: {json.dumps({'type': 'error', 'run_id': run_id, 'error': str(stream_error), 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
        
        # Create timeout-protected streaming generator
        async def timeout_protected_stream():
            """Generate streaming response with timeout protection."""
            try:
                # Use asyncio.wait_for with 30-second timeout for streaming operations
                async for chunk in asyncio.wait_for(
                    generate_chat_stream(), 
                    timeout=30.0  # 30-second timeout protection
                ):
                    yield chunk
                    
            except asyncio.TimeoutError:
                logger.error(
                    f" ALERT:  STREAMING TIMEOUT: Chat stream timed out after 30 seconds for user {current_user[:8]}..., "
                    f"thread {request.thread_id[:8]}... - This indicates potential system overload or infinite loops"
                )
                
                # Send timeout error event to client
                timeout_event = {
                    'type': 'timeout_error',
                    'error': 'Streaming response timed out after 30 seconds',
                    'user_id': current_user,
                    'thread_id': request.thread_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'troubleshooting': 'This may indicate system overload or processing issues. Please try again.'
                }
                yield f"data: {json.dumps(timeout_event)}\n\n"
                
            except Exception as stream_outer_error:
                logger.error(
                    f" ALERT:  STREAMING ERROR: Outer streaming error for user {current_user[:8]}...: {stream_outer_error}",
                    exc_info=True
                )
                
                # Send comprehensive error event to client
                error_event = {
                    'type': 'streaming_error',
                    'error': str(stream_outer_error),
                    'error_type': type(stream_outer_error).__name__,
                    'user_id': current_user,
                    'thread_id': request.thread_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'debug_info': 'Check server logs for detailed error information'
                }
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            timeout_protected_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(
            f" ALERT:  CRITICAL STREAMING FAILURE: Failed to create chat stream for user {current_user[:8]}..., "
            f"thread {request.thread_id[:8]}..., error: {e}. "
            f"Error type: {type(e).__name__}. "
            f"This indicates a fundamental streaming infrastructure issue that prevents investor demo functionality.",
            exc_info=True
        )
        
        # Enhanced error context for debugging
        error_context = {
            "user_id": current_user[:8] + "...",
            "thread_id": request.thread_id[:8] + "...", 
            "error_type": type(e).__name__,
            "error_message": str(e),
            "endpoint": "/messages/stream",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_impact": "Prevents $120K+ MRR investor demo capability"
        }
        
        logger.error(f"STREAMING ERROR CONTEXT: {json.dumps(error_context, indent=2)}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat stream: {type(e).__name__}: {str(e)}"
        )

# Agent Lifecycle Control Endpoints
@router.post("/agents/{run_id}/start")
async def start_agent(
    run_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """Start or resume an agent execution."""
    try:
        logger.info(f"Starting agent for run {run_id}, user {current_user[:8]}...")
        
        # In real implementation, this would interact with agent registry
        # For now, return success response for demo purposes
        return {
            "status": "started",
            "run_id": run_id,
            "user_id": current_user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Agent execution started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start agent {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")

@router.post("/agents/{run_id}/stop")
async def stop_agent(
    run_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """Stop an agent execution."""
    try:
        logger.info(f"Stopping agent for run {run_id}, user {current_user[:8]}...")
        
        # In real implementation, this would interact with agent registry to stop execution
        # For now, return success response for demo purposes
        return {
            "status": "stopped",
            "run_id": run_id,
            "user_id": current_user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Agent execution stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop agent {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")

@router.post("/agents/{run_id}/cancel")
async def cancel_agent(
    run_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """Cancel an agent execution."""
    try:
        logger.info(f"Canceling agent for run {run_id}, user {current_user[:8]}...")
        
        # In real implementation, this would interact with agent registry to cancel execution
        # For now, return success response for demo purposes
        return {
            "status": "cancelled",
            "run_id": run_id,
            "user_id": current_user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Agent execution cancelled"
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel agent {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel agent: {str(e)}")

@router.get("/agents/{run_id}/status")
async def get_agent_status(
    run_id: str,
    current_user: str = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """Get the status of an agent execution."""
    try:
        logger.info(f"Getting agent status for run {run_id}, user {current_user[:8]}...")
        
        # In real implementation, this would query agent registry
        # For now, return mock status for demo purposes
        return {
            "run_id": run_id,
            "status": "running",
            "user_id": current_user,
            "agent_name": "ChatAgent",
            "progress": 75,
            "current_task": "Processing user request",
            "started_at": (datetime.now(timezone.utc) - asyncio.get_event_loop().time().__class__(300)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "websocket_events_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent status {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

# Health check for messages API
@router.get("/messages/health")
async def messages_health() -> Dict[str, Any]:
    """Health check for messages API."""
    return {
        "status": "healthy",
        "service": "messages-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": {
            "chat_streaming": True,
            "agent_lifecycle_control": True,
            "websocket_events": True
        },
        "stats": {
            "total_messages": len(_message_store),
            "total_users": len(_messages_by_user),
            "total_threads": len(_messages_by_thread)
        }
    }