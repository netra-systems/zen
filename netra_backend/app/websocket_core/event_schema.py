"""
WebSocket Event Schema - Single Source of Truth (SSOT)

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Fix Issue #984 - WebSocket events missing critical fields
- Value Impact: Unified event structure prevents test/production schema mismatches
- Strategic Impact: Ensures consistent event delivery for $500K+ ARR chat functionality

CRITICAL: This module defines the unified event schema for ALL WebSocket events.
Both tests and production code MUST use these definitions to prevent schema drift.

Architecture: Single Source of Truth for event structures that serve the 5 critical events:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency (requires tool_name)
4. tool_completed - Tool results display (requires tool_name, results)
5. agent_completed - User knows response is ready
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid

from pydantic import BaseModel, Field
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class WebSocketEventType(str, Enum):
    """Standard WebSocket event types - SSOT for all event type definitions."""
    # Critical agent lifecycle events (REQUIRED for chat functionality)
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    
    # Additional agent events
    AGENT_FAILED = "agent_failed"
    AGENT_ERROR = "agent_error"
    AGENT_FALLBACK = "agent_fallback"
    
    # Tool events  
    TOOL_STARTED = "tool_started"
    TOOL_ERROR = "tool_error"
    
    # Streaming events
    STREAM_CHUNK = "stream_chunk"
    PARTIAL_RESULT = "partial_result"
    FINAL_REPORT = "final_report"
    
    # Connection events
    CONNECTION_ESTABLISHED = "connection_established"
    PING = "ping"
    PONG = "pong"
    HEARTBEAT = "heartbeat"
    
    # User interaction
    USER_MESSAGE = "user_message"
    CHAT_MESSAGE = "chat_message"
    USER_TYPING = "user_typing"
    
    # System events
    ERROR = "error"
    SYSTEM_MESSAGE = "system_message"


@dataclass
class WebSocketEventSchema:
    """
    SSOT: Unified WebSocket event schema definition.
    
    This schema ensures consistency between test expectations and production events.
    All event creation MUST use this schema to prevent Issue #984 recurrence.
    """
    # Core identification fields (REQUIRED for all events)
    type: str  # Event type (from WebSocketEventType)
    timestamp: float  # Unix timestamp
    event_id: str  # Unique event identifier
    
    # Context fields (REQUIRED for agent events)
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    
    # Agent information (REQUIRED for agent events)
    agent_name: Optional[str] = None
    
    # Tool information (REQUIRED for tool events - Issue #984 fix)
    tool_name: Optional[str] = None  # CRITICAL: Missing field causing test failures
    
    # Event data payload
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Tool execution results (REQUIRED for tool_completed - Issue #984 fix)
    results: Optional[Dict[str, Any]] = None  # CRITICAL: Missing field causing test failures
    
    # Additional contextual fields
    message: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event schema after creation."""
        # Generate event_id if not provided
        if not self.event_id:
            self.event_id = UnifiedIdGenerator.generate_base_id(
                f"evt_{self.type}",
                include_random=True,
                random_length=8
            )
        
        # Set timestamp if not provided
        if not self.timestamp:
            self.timestamp = time.time()


class AgentStartedEvent(BaseModel):
    """SSOT schema for agent_started events."""
    type: str = WebSocketEventType.AGENT_STARTED
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_agent_started"))
    
    # Required fields
    user_id: str
    thread_id: str
    run_id: str
    agent_name: str
    
    # Optional fields
    message: Optional[str] = None
    status: str = "starting"
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentThinkingEvent(BaseModel):
    """SSOT schema for agent_thinking events."""
    type: str = WebSocketEventType.AGENT_THINKING
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_agent_thinking"))
    
    # Required fields
    user_id: str
    thread_id: str
    run_id: str
    agent_name: str
    
    # Thinking-specific fields
    thought: Optional[str] = None  # The agent's reasoning
    reasoning: Optional[str] = None  # Alternative field name
    progress: Optional[str] = None  # Progress indicator
    step: Optional[str] = None  # Current step
    
    # Optional fields
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutingEvent(BaseModel):
    """SSOT schema for tool_executing events - Issue #984 fix."""
    type: str = WebSocketEventType.TOOL_EXECUTING
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_tool_executing"))
    
    # Required fields
    user_id: str
    thread_id: str
    run_id: str
    agent_name: str
    tool_name: str  # CRITICAL: This field was missing (Issue #984)
    
    # Tool execution specific fields
    parameters: Optional[Dict[str, Any]] = None
    tool_purpose: Optional[str] = None
    estimated_duration_ms: Optional[float] = None
    
    # Optional fields
    message: Optional[str] = None
    status: str = "executing"
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolCompletedEvent(BaseModel):
    """SSOT schema for tool_completed events - Issue #984 fix."""
    type: str = WebSocketEventType.TOOL_COMPLETED
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_tool_completed"))
    
    # Required fields
    user_id: str
    thread_id: str
    run_id: str
    agent_name: str
    tool_name: str  # CRITICAL: This field was missing (Issue #984)
    
    # Tool completion specific fields
    results: Optional[Dict[str, Any]] = None  # CRITICAL: This field was missing (Issue #984)
    success: Optional[bool] = None
    duration_ms: Optional[float] = None
    
    # Optional fields
    message: Optional[str] = None
    status: str = "completed"
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentCompletedEvent(BaseModel):
    """SSOT schema for agent_completed events."""
    type: str = WebSocketEventType.AGENT_COMPLETED
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_agent_completed"))
    
    # Required fields
    user_id: str
    thread_id: str
    run_id: str
    agent_name: str
    
    # Completion specific fields
    final_response: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    duration_ms: Optional[float] = None
    
    # Optional fields
    message: Optional[str] = None
    status: str = "completed"
    success: Optional[bool] = True
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(BaseModel):
    """SSOT schema for error events."""
    type: str = WebSocketEventType.ERROR
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("evt_error"))
    
    # Required fields
    user_id: str
    thread_id: str
    error: str
    
    # Optional fields
    run_id: Optional[str] = None
    agent_name: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    recovery_suggestions: Optional[List[str]] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def create_agent_started_event(
    user_id: str,
    thread_id: str,
    run_id: str,
    agent_name: str,
    message: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized agent_started event."""
    event = AgentStartedEvent(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        message=message,
        **kwargs
    )
    return event.model_dump()


def create_agent_thinking_event(
    user_id: str,
    thread_id: str,
    run_id: str,
    agent_name: str,
    thought: Optional[str] = None,
    reasoning: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized agent_thinking event."""
    event = AgentThinkingEvent(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        thought=thought,
        reasoning=reasoning,
        **kwargs
    )
    return event.model_dump()


def create_tool_executing_event(
    user_id: str,
    thread_id: str,
    run_id: str,
    agent_name: str,
    tool_name: str,  # CRITICAL: Required field (Issue #984 fix)
    parameters: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized tool_executing event - Issue #984 fix."""
    event = ToolExecutingEvent(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        tool_name=tool_name,
        parameters=parameters,
        **kwargs
    )
    return event.model_dump()


def create_tool_completed_event(
    user_id: str,
    thread_id: str,
    run_id: str,
    agent_name: str,
    tool_name: str,  # CRITICAL: Required field (Issue #984 fix)
    results: Optional[Dict[str, Any]] = None,  # CRITICAL: Required field (Issue #984 fix)
    success: Optional[bool] = None,
    duration_ms: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized tool_completed event - Issue #984 fix."""
    event = ToolCompletedEvent(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        tool_name=tool_name,
        results=results,
        success=success,
        duration_ms=duration_ms,
        **kwargs
    )
    return event.model_dump()


def create_agent_completed_event(
    user_id: str,
    thread_id: str,
    run_id: str,
    agent_name: str,
    final_response: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized agent_completed event."""
    event = AgentCompletedEvent(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        final_response=final_response,
        result=result,
        **kwargs
    )
    return event.model_dump()


def create_error_event(
    user_id: str,
    thread_id: str,
    error: str,
    run_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized error event."""
    event = ErrorEvent(
        user_id=user_id,
        thread_id=thread_id,
        error=error,
        run_id=run_id,
        agent_name=agent_name,
        **kwargs
    )
    return event.model_dump()


def validate_event_schema(event: Dict[str, Any], event_type: str) -> List[str]:
    """
    Validate event matches the expected schema for its type.
    
    Args:
        event: Event dictionary to validate
        event_type: Expected event type
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Basic validation
    if not event.get('type'):
        errors.append("Missing 'type' field")
    elif event['type'] != event_type:
        errors.append(f"Type mismatch: expected {event_type}, got {event['type']}")
    
    if not event.get('timestamp'):
        errors.append("Missing 'timestamp' field")
    
    if not event.get('event_id'):
        errors.append("Missing 'event_id' field")
    
    # Type-specific validation
    if event_type == WebSocketEventType.AGENT_STARTED:
        required_fields = ['user_id', 'thread_id', 'run_id', 'agent_name']
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field for agent_started: {field}")
    
    elif event_type == WebSocketEventType.AGENT_THINKING:
        required_fields = ['user_id', 'thread_id', 'run_id', 'agent_name']
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field for agent_thinking: {field}")
    
    elif event_type == WebSocketEventType.TOOL_EXECUTING:
        required_fields = ['user_id', 'thread_id', 'run_id', 'agent_name', 'tool_name']
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field for tool_executing: {field}")
        
        # CRITICAL: tool_name is required for tool events (Issue #984 fix)
        if not event.get('tool_name'):
            errors.append("CRITICAL: tool_name is required for tool_executing events")
    
    elif event_type == WebSocketEventType.TOOL_COMPLETED:
        required_fields = ['user_id', 'thread_id', 'run_id', 'agent_name', 'tool_name']
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field for tool_completed: {field}")
        
        # CRITICAL: tool_name and results are required for tool completion (Issue #984 fix)
        if not event.get('tool_name'):
            errors.append("CRITICAL: tool_name is required for tool_completed events")
        
        if 'results' not in event:
            errors.append("CRITICAL: results field is required for tool_completed events")
    
    elif event_type == WebSocketEventType.AGENT_COMPLETED:
        required_fields = ['user_id', 'thread_id', 'run_id', 'agent_name']
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field for agent_completed: {field}")
    
    return errors


# Export event creation functions as the primary API
__all__ = [
    'WebSocketEventType',
    'WebSocketEventSchema',
    'AgentStartedEvent',
    'AgentThinkingEvent', 
    'ToolExecutingEvent',
    'ToolCompletedEvent',
    'AgentCompletedEvent',
    'ErrorEvent',
    'create_agent_started_event',
    'create_agent_thinking_event',
    'create_tool_executing_event',
    'create_tool_completed_event',
    'create_agent_completed_event',
    'create_error_event',
    'validate_event_schema'
]