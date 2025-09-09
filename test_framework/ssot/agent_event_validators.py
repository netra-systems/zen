"""
SSOT Agent Event Validators - Single Source of Truth for WebSocket Agent Event Validation

This module provides the CANONICAL validation functions for the 5 critical WebSocket events
that deliver 90% of business value ($500K+ ARR) through real-time AI interactions.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Chat Infrastructure
- Business Goal: Revenue Protection - Ensure all critical events enable substantive AI chat value
- Value Impact: Validates the 5 events that power user-visible AI responses and insights
- Strategic Impact: Prevents silent failures that would block revenue-generating chat interactions

CRITICAL: These are the 5 MISSION CRITICAL events that MUST be sent for every agent execution:
1. agent_started - User sees AI began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

If ANY of these events are missing, revenue is lost because users don't see AI value delivery.

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance SPEC/core.xml - Single Source of Truth patterns
@compliance SPEC/type_safety.xml - Strongly typed event validation
"""

import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set, Optional, Union, Tuple
from loguru import logger

# Import SSOT types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env


class CriticalAgentEventType(Enum):
    """
    The 5 MISSION CRITICAL WebSocket agent events that deliver business value.
    
    CRITICAL: If ANY of these events are missing from agent execution,
    the user does not see AI value delivery and revenue is lost.
    """
    # Core business value events - THESE MUST ALL BE SENT
    AGENT_STARTED = "agent_started"       # User sees AI began work
    AGENT_THINKING = "agent_thinking"     # Real-time reasoning visibility
    TOOL_EXECUTING = "tool_executing"     # Tool usage transparency  
    TOOL_COMPLETED = "tool_completed"     # Tool results display
    AGENT_COMPLETED = "agent_completed"   # Final results ready
    
    # Supporting events (important but not revenue-critical)
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    THREAD_UPDATE = "thread_update"
    MESSAGE_CREATED = "message_created"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"


@dataclass
class AgentEventValidationResult:
    """Result of agent event validation with business value metrics."""
    is_valid: bool
    missing_critical_events: Set[str] = field(default_factory=set)
    received_events: List[str] = field(default_factory=list)
    event_timing: Dict[str, float] = field(default_factory=dict)
    business_value_score: float = 0.0  # 0-100 score based on critical events received
    revenue_impact: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    validation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Calculate business value score and revenue impact."""
        critical_events = {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
        
        received_critical = set(self.received_events) & critical_events
        self.business_value_score = (len(received_critical) / len(critical_events)) * 100
        
        # Determine revenue impact
        if len(self.missing_critical_events) == 0:
            self.revenue_impact = "NONE"  # All events received - no revenue impact
        elif len(self.missing_critical_events) == 1:
            self.revenue_impact = "LOW"   # 1 missing event - minor UX degradation
        elif len(self.missing_critical_events) == 2:
            self.revenue_impact = "MEDIUM"  # 2 missing events - noticeable UX issues
        elif len(self.missing_critical_events) >= 3:
            self.revenue_impact = "HIGH"    # 3+ missing events - major UX failure
        
        # If agent_completed is missing, it's always CRITICAL (user never sees result)
        if CriticalAgentEventType.AGENT_COMPLETED.value in self.missing_critical_events:
            self.revenue_impact = "CRITICAL"


@dataclass
class WebSocketEventMessage:
    """Strongly typed WebSocket event message for validation."""
    event_type: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    websocket_client_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    
    def __post_init__(self):
        """Ensure timestamp is set and message_id is generated."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.message_id is None:
            self.message_id = f"msg_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.event_type,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "websocket_client_id": self.websocket_client_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "data": self.data,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketEventMessage':
        """Create from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                timestamp = datetime.now(timezone.utc)
        
        return cls(
            event_type=data.get("type", "unknown"),
            thread_id=data.get("thread_id"),
            user_id=data.get("user_id"),
            request_id=data.get("request_id"),
            run_id=data.get("run_id"),
            websocket_client_id=data.get("websocket_client_id"),
            timestamp=timestamp,
            data=data.get("data", {}),
            message_id=data.get("message_id")
        )


class AgentEventValidator:
    """
    SSOT Validator for the 5 critical WebSocket agent events.
    
    This validator ensures that all revenue-critical events are received
    and validates their timing, content, and business value delivery.
    
    CRITICAL: This validator protects $500K+ ARR by ensuring users
    see real-time AI value delivery through WebSocket events.
    """
    
    def __init__(self, 
                 user_context: Optional[StronglyTypedUserExecutionContext] = None,
                 strict_mode: bool = True,
                 timeout_seconds: float = 30.0):
        """
        Initialize agent event validator.
        
        Args:
            user_context: Strongly typed user execution context
            strict_mode: If True, require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
        """
        self.user_context = user_context
        self.strict_mode = strict_mode
        self.timeout_seconds = timeout_seconds
        self.env = get_env()
        
        # Event tracking
        self.received_events: List[WebSocketEventMessage] = []
        self.event_timestamps: Dict[str, float] = {}
        self.validation_start_time = time.time()
        
        # Business value tracking
        self.critical_events_received: Set[str] = set()
        self.event_sequence: List[str] = []
        
        logger.info(f"AgentEventValidator initialized in {'strict' if strict_mode else 'permissive'} mode")
    
    def get_required_critical_events(self) -> Set[str]:
        """Get the set of required critical events."""
        return {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
    
    def record_event(self, event_data: Union[Dict[str, Any], WebSocketEventMessage]) -> bool:
        """
        Record a WebSocket event for validation.
        
        Args:
            event_data: Event data (dict or WebSocketEventMessage)
            
        Returns:
            True if event was recorded successfully
        """
        try:
            # Convert to WebSocketEventMessage if needed
            if isinstance(event_data, dict):
                event = WebSocketEventMessage.from_dict(event_data)
            else:
                event = event_data
            
            # Record event
            self.received_events.append(event)
            self.event_timestamps[event.event_type] = time.time()
            self.event_sequence.append(event.event_type)
            
            # Track critical events
            if event.event_type in self.get_required_critical_events():
                self.critical_events_received.add(event.event_type)
                logger.debug(f"Critical event received: {event.event_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            return False
    
    def validate_event_sequence(self) -> Tuple[bool, List[str]]:
        """
        Validate that events are received in logical order.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        if not self.event_sequence:
            return True, []
        
        # Define expected event flow patterns
        expected_patterns = [
            # Standard agent execution flow
            [
                CriticalAgentEventType.AGENT_STARTED.value,
                CriticalAgentEventType.AGENT_THINKING.value,
                CriticalAgentEventType.TOOL_EXECUTING.value,
                CriticalAgentEventType.TOOL_COMPLETED.value,
                CriticalAgentEventType.AGENT_COMPLETED.value
            ]
        ]
        
        # Check if received sequence matches any expected pattern
        received_critical = [event for event in self.event_sequence 
                           if event in self.get_required_critical_events()]
        
        # Basic validation: agent_started should come before agent_completed
        if (CriticalAgentEventType.AGENT_STARTED.value in received_critical and 
            CriticalAgentEventType.AGENT_COMPLETED.value in received_critical):
            
            started_idx = received_critical.index(CriticalAgentEventType.AGENT_STARTED.value)
            completed_idx = received_critical.index(CriticalAgentEventType.AGENT_COMPLETED.value)
            
            if completed_idx <= started_idx:
                errors.append("agent_completed received before agent_started")
        
        # Validate tool execution flow
        if (CriticalAgentEventType.TOOL_EXECUTING.value in received_critical and 
            CriticalAgentEventType.TOOL_COMPLETED.value in received_critical):
            
            executing_idx = received_critical.index(CriticalAgentEventType.TOOL_EXECUTING.value)
            completed_idx = received_critical.index(CriticalAgentEventType.TOOL_COMPLETED.value)
            
            if completed_idx <= executing_idx:
                errors.append("tool_completed received before tool_executing")
        
        return len(errors) == 0, errors
    
    def validate_event_timing(self) -> Tuple[bool, List[str]]:
        """
        Validate event timing constraints.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Check overall execution time
        total_time = time.time() - self.validation_start_time
        if total_time > self.timeout_seconds:
            errors.append(f"Agent execution exceeded timeout: {total_time:.2f}s > {self.timeout_seconds}s")
        
        # Check for reasonable gaps between critical events
        critical_events = [event for event in self.received_events 
                          if event.event_type in self.get_required_critical_events()]
        
        if len(critical_events) >= 2:
            for i in range(1, len(critical_events)):
                prev_event = critical_events[i-1]
                curr_event = critical_events[i]
                
                if prev_event.timestamp and curr_event.timestamp:
                    gap = (curr_event.timestamp - prev_event.timestamp).total_seconds()
                    
                    # Flag unusually long gaps (may indicate stalled agent)
                    if gap > 15.0:  # 15 second gap is concerning
                        errors.append(
                            f"Long gap between {prev_event.event_type} and {curr_event.event_type}: {gap:.2f}s"
                        )
        
        return len(errors) == 0, errors
    
    def validate_event_content(self) -> Tuple[bool, List[str]]:
        """
        Validate event content for business value delivery.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Validate agent_started content
        started_events = [e for e in self.received_events 
                         if e.event_type == CriticalAgentEventType.AGENT_STARTED.value]
        
        for event in started_events:
            if not event.data:
                errors.append("agent_started event missing data field")
            elif not event.data.get("agent"):
                errors.append("agent_started event missing agent identifier")
        
        # Validate tool execution content
        tool_executing_events = [e for e in self.received_events 
                               if e.event_type == CriticalAgentEventType.TOOL_EXECUTING.value]
        
        for event in tool_executing_events:
            if not event.data:
                errors.append("tool_executing event missing data field")
            elif not event.data.get("tool"):
                errors.append("tool_executing event missing tool identifier")
        
        # Validate tool completion content  
        tool_completed_events = [e for e in self.received_events 
                               if e.event_type == CriticalAgentEventType.TOOL_COMPLETED.value]
        
        for event in tool_completed_events:
            if not event.data:
                errors.append("tool_completed event missing data field")
            elif not event.data.get("tool"):
                errors.append("tool_completed event missing tool identifier")
            # Note: result field is optional - tools may fail
        
        # Validate agent completion content
        completed_events = [e for e in self.received_events 
                          if e.event_type == CriticalAgentEventType.AGENT_COMPLETED.value]
        
        for event in completed_events:
            if not event.data:
                errors.append("agent_completed event missing data field")
            elif not event.data.get("agent"):
                errors.append("agent_completed event missing agent identifier")
            # Note: result field is optional - agents may fail
        
        return len(errors) == 0, errors
    
    def perform_full_validation(self) -> AgentEventValidationResult:
        """
        Perform comprehensive validation of all received events.
        
        Returns:
            AgentEventValidationResult with complete validation results
        """
        # Determine missing critical events
        required_events = self.get_required_critical_events()
        missing_events = required_events - self.critical_events_received
        
        # Perform sub-validations
        sequence_valid, sequence_errors = self.validate_event_sequence()
        timing_valid, timing_errors = self.validate_event_timing()
        content_valid, content_errors = self.validate_event_content()
        
        # Determine overall validity
        is_valid = (
            len(missing_events) == 0 if self.strict_mode else len(missing_events) <= 1
        ) and sequence_valid and timing_valid and content_valid
        
        # Compile error message
        all_errors = sequence_errors + timing_errors + content_errors
        if missing_events:
            all_errors.append(f"Missing critical events: {missing_events}")
        
        error_message = "; ".join(all_errors) if all_errors else None
        
        # Create validation result
        result = AgentEventValidationResult(
            is_valid=is_valid,
            missing_critical_events=missing_events,
            received_events=[e.event_type for e in self.received_events],
            event_timing=self.event_timestamps.copy(),
            error_message=error_message
        )
        
        # Log validation result
        if result.is_valid:
            logger.success(f"Agent event validation PASSED - Business value score: {result.business_value_score:.1f}%")
        else:
            logger.error(f"Agent event validation FAILED - Revenue impact: {result.revenue_impact} - {error_message}")
        
        return result
    
    def wait_for_critical_events(self, timeout: Optional[float] = None) -> AgentEventValidationResult:
        """
        Wait for all critical events to be received.
        
        Args:
            timeout: Optional timeout override
            
        Returns:
            AgentEventValidationResult once complete or timeout
        """
        timeout = timeout or self.timeout_seconds
        start_time = time.time()
        required_events = self.get_required_critical_events()
        
        logger.info(f"Waiting for {len(required_events)} critical events (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            if len(self.critical_events_received) >= len(required_events):
                logger.success("All critical events received!")
                break
            
            # Small sleep to avoid busy waiting
            time.sleep(0.1)
        
        return self.perform_full_validation()


# SSOT Convenience Functions

def validate_agent_events(
    events: List[Union[Dict[str, Any], WebSocketEventMessage]],
    user_context: Optional[StronglyTypedUserExecutionContext] = None,
    strict_mode: bool = True
) -> AgentEventValidationResult:
    """
    SSOT function to validate a list of agent events.
    
    Args:
        events: List of events to validate
        user_context: Optional user execution context
        strict_mode: If True, require ALL 5 critical events
        
    Returns:
        AgentEventValidationResult with validation results
    """
    validator = AgentEventValidator(user_context=user_context, strict_mode=strict_mode)
    
    # Record all events
    for event in events:
        validator.record_event(event)
    
    return validator.perform_full_validation()


def assert_critical_events_received(
    events: List[Union[Dict[str, Any], WebSocketEventMessage]],
    user_context: Optional[StronglyTypedUserExecutionContext] = None,
    custom_error_message: Optional[str] = None
) -> None:
    """
    Assert that all critical agent events are received - raises AssertionError if not.
    
    This is the SSOT assertion function for mission critical tests.
    
    Args:
        events: List of events to validate
        user_context: Optional user execution context  
        custom_error_message: Optional custom error message
        
    Raises:
        AssertionError: If critical events are missing or invalid
    """
    result = validate_agent_events(events, user_context=user_context, strict_mode=True)
    
    if not result.is_valid:
        error_msg = custom_error_message or (
            f"CRITICAL AGENT EVENTS VALIDATION FAILED - Revenue Impact: {result.revenue_impact}\n"
            f"Missing Events: {result.missing_critical_events}\n"
            f"Business Value Score: {result.business_value_score:.1f}%\n"
            f"Error Details: {result.error_message}\n"
            f"This failure blocks revenue-generating chat functionality!"
        )
        raise AssertionError(error_msg)


def get_critical_event_types() -> Set[str]:
    """Get the set of critical agent event types."""
    return {
        CriticalAgentEventType.AGENT_STARTED.value,
        CriticalAgentEventType.AGENT_THINKING.value,
        CriticalAgentEventType.TOOL_EXECUTING.value,
        CriticalAgentEventType.TOOL_COMPLETED.value,
        CriticalAgentEventType.AGENT_COMPLETED.value
    }


def create_mock_critical_events(
    user_id: str = "test-user",
    thread_id: str = "test-thread",
    agent_name: str = "test-agent",
    tool_name: str = "test-tool"
) -> List[WebSocketEventMessage]:
    """
    Create mock critical events for testing.
    
    Args:
        user_id: User ID for events
        thread_id: Thread ID for events
        agent_name: Agent name for events
        tool_name: Tool name for events
        
    Returns:
        List of mock WebSocketEventMessage instances
    """
    base_time = datetime.now(timezone.utc)
    
    return [
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.AGENT_STARTED.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time,
            data={"agent": agent_name, "status": "started"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.AGENT_THINKING.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(second=base_time.second + 1),
            data={"agent": agent_name, "progress": "thinking"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.TOOL_EXECUTING.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(second=base_time.second + 2),
            data={"tool": tool_name, "status": "executing"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.TOOL_COMPLETED.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(second=base_time.second + 3),
            data={"tool": tool_name, "status": "completed", "result": "mock result"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.AGENT_COMPLETED.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(second=base_time.second + 4),
            data={"agent": agent_name, "status": "completed", "result": "mock agent result"}
        )
    ]


# SSOT Exports
__all__ = [
    "CriticalAgentEventType",
    "AgentEventValidationResult", 
    "WebSocketEventMessage",
    "AgentEventValidator",
    "validate_agent_events",
    "assert_critical_events_received",
    "get_critical_event_types",
    "create_mock_critical_events"
]