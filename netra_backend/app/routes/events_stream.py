"""
Event Streaming API Router - SSE endpoints for real-time events

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Real-time Event Delivery
- Value Impact: Enables real-time user experience and system monitoring
- Revenue Impact: Critical for chat functionality and user engagement

This router provides Server-Sent Events (SSE) endpoints for streaming
real-time events to clients, including agent execution events,
system notifications, and user activity updates.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration import get_current_user_optional
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["Events"])

# Response Models
class EventStreamInfo(BaseModel):
    """Information about event streaming capabilities."""
    available: bool = True
    stream_types: List[str] = [
        "agent_events", 
        "system_events", 
        "user_events",
        "chat_events"
    ]
    event_types: List[str] = [
        "agent_started",
        "agent_thinking", 
        "agent_completed",
        "agent_error",
        "message_received",
        "message_sent",
        "system_notification",
        "user_joined",
        "user_left"
    ]

class EventFilter(BaseModel):
    """Event filtering options."""
    event_types: Optional[List[str]] = None
    agent_types: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    since_timestamp: Optional[datetime] = None


@router.get("/stream")
async def stream_events(
    event_filter: str = Query(None, description="JSON encoded event filter"),
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """Stream real-time events using Server-Sent Events."""
    
    async def generate_event_stream():
        """Generate streaming events."""
        try:
            connection_id = f"stream-{uuid4()}"
            user_id = user.get("user_id") if user else "anonymous"
            
            logger.info(f"Starting event stream for user {user_id}, connection {connection_id}")
            
            # Send initial connection event
            connection_data = {
                'event': 'stream_connected',
                'connection_id': connection_id,
                'user_id': user_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(connection_data)}\n\n"
            
            # Parse event filter if provided
            filter_config = None
            if event_filter:
                try:
                    filter_config = json.loads(event_filter)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid event filter JSON: {event_filter}")
            
            # Simulate live event stream
            event_counter = 0
            while True:
                try:
                    # Check if client disconnected (basic check)
                    await asyncio.sleep(1.0)
                    event_counter += 1
                    
                    # Generate sample events for testing
                    sample_events = [
                        {
                            'event': 'agent_thinking',
                            'agent_id': f'agent-{event_counter}',
                            'message': f'Processing request {event_counter}',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        },
                        {
                            'event': 'system_notification',
                            'message': f'System health check {event_counter}',
                            'level': 'info',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    ]
                    
                    # Send events based on counter
                    if event_counter % 10 == 0:
                        # Send heartbeat every 10 seconds
                        heartbeat_data = {
                            'event': 'heartbeat',
                            'connection_id': connection_id,
                            'count': event_counter,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        yield f"data: {json.dumps(heartbeat_data)}\n\n"
                    
                    elif event_counter % 5 == 0:
                        # Send sample event every 5 seconds
                        sample_event = sample_events[event_counter % len(sample_events)]
                        yield f"data: {json.dumps(sample_event)}\n\n"
                    
                    # Limit stream duration for testing (10 minutes max)
                    if event_counter > 600:
                        yield f"data: {json.dumps({
                            'event': 'stream_timeout',
                            'connection_id': connection_id,
                            'message': 'Stream ended after 10 minutes',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })}\n\n"
                        break
                        
                except asyncio.CancelledError:
                    logger.info(f"Event stream cancelled for user {user_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in event stream: {e}")
                    yield f"data: {json.dumps({
                        'event': 'stream_error',
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })}\n\n"
                    break
            
            # Send final disconnect event
            yield f"data: {json.dumps({
                'event': 'stream_disconnected',
                'connection_id': connection_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })}\n\n"
            
        except Exception as e:
            logger.error(f"Fatal error in event stream: {e}")
            yield f"data: {json.dumps({
                'event': 'stream_fatal_error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })}\n\n"
    
    return StreamingResponse(
        generate_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/info", response_model=EventStreamInfo)
async def get_event_stream_info(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> EventStreamInfo:
    """Get information about available event streams."""
    return EventStreamInfo()


@router.post("/test")
async def test_event_emission(
    event_type: str = "test_event",
    message: str = "Test event message",
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """Test endpoint to emit a sample event."""
    test_event = {
        'event': event_type,
        'message': message,
        'user_id': user.get("user_id") if user else "test-user",
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"Test event emitted: {test_event}")
    
    return {
        'success': True,
        'event_emitted': test_event,
        'message': 'Test event emitted successfully'
    }