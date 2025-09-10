"""
SSOT WebSocket Event Validator - Consolidated Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Chat Infrastructure  
- Business Goal: Revenue Protection - Protects $500K+ ARR through consistent validation
- Value Impact: Validates the 5 critical events that power user-visible AI responses and insights
- Strategic Impact: Prevents silent failures that would block revenue-generating chat interactions

This module consolidates two previous EventValidator implementations:
1. Production: netra_backend.app.services.websocket_error_validator (business value scoring)
2. SSOT Framework: test_framework.ssot.agent_event_validators (sequence validation)

CRITICAL: These are the 5 MISSION CRITICAL events that MUST be sent for every agent execution:
1. agent_started - User sees AI began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

If ANY of these events are missing, revenue is lost because users don't see AI value delivery.

CONSOLIDATION NOTES:
- Merged ValidationResult classes preserving all fields
- Merged Event Type Definitions with comprehensive coverage
- Consolidated validation methods from both implementations
- Preserved all business logic and error handling patterns
- Maintained backward compatibility for all existing APIs
- Added comprehensive docstrings and type hints

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance SPEC/core.xml - Single Source of Truth patterns
@compliance SPEC/type_safety.xml - Strongly typed event validation

Migration Date: 2025-09-10
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/214
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Consolidated imports from both original implementations
from netra_backend.app.logging_config import central_logger
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


# Consolidated Enums and Types

class EventCriticality(Enum):
    """Event criticality levels for business value assessment."""
    MISSION_CRITICAL = "mission_critical"  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
    BUSINESS_VALUE = "business_value"     # progress_update, custom events
    OPERATIONAL = "operational"           # connection events, cleanup events


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
class ValidationResult:
    """
    Consolidated result of event validation with business value metrics.
    
    This dataclass merges fields from both original ValidationResult classes:
    - Production: ValidationResult (websocket_error_validator.py)
    - SSOT Framework: AgentEventValidationResult (agent_event_validators.py)
    """
    is_valid: bool
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    criticality: EventCriticality = EventCriticality.OPERATIONAL
    business_impact: Optional[str] = None
    
    # Business value tracking (from SSOT framework)
    missing_critical_events: Set[str] = field(default_factory=set)
    received_events: List[str] = field(default_factory=list)
    event_timing: Dict[str, float] = field(default_factory=dict)
    business_value_score: float = 0.0  # 0-100 score based on critical events received
    revenue_impact: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    validation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
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


# Main Consolidated Validator Class

class UnifiedEventValidator:
    """
    SSOT WebSocket Event Validator - Consolidated implementation from two previous validators.
    
    Business Value: Protects $500K+ ARR through consistent validation of 5 critical 
    agent events that deliver real-time AI value to users.
    
    This class consolidates functionality from:
    1. WebSocketEventValidator (websocket_error_validator.py) - business value scoring
    2. AgentEventValidator (agent_event_validators.py) - sequence validation
    
    Key Features:
    - Validates all 5 mission-critical WebSocket events
    - Provides business value scoring and revenue impact assessment
    - Supports both real-time validation and batch validation
    - Includes comprehensive error handling with loud failure patterns
    - Maintains full backward compatibility with existing APIs
    """
    
    # Mission critical events that must never fail silently
    MISSION_CRITICAL_EVENTS = {
        "agent_started", "agent_thinking", "tool_executing", 
        "tool_completed", "agent_completed"
    }
    
    # Required fields for each event type
    EVENT_SCHEMAS = {
        "agent_started": {"run_id", "agent_name", "timestamp", "payload"},
        "agent_thinking": {"run_id", "agent_name", "timestamp", "payload"},
        "tool_executing": {"run_id", "agent_name", "timestamp", "payload"},
        "tool_completed": {"run_id", "agent_name", "timestamp", "payload"},
        "agent_completed": {"run_id", "agent_name", "timestamp", "payload"},
        "progress_update": {"run_id", "timestamp", "payload"},
        "agent_error": {"run_id", "agent_name", "timestamp", "payload"},
    }
    
    def __init__(self, 
                 user_context: Optional[StronglyTypedUserExecutionContext] = None,
                 strict_mode: bool = True,
                 timeout_seconds: float = 30.0):
        """
        Initialize unified event validator.
        
        Args:
            user_context: Optional strongly typed user execution context
            strict_mode: If True, require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
        """
        self.user_context = user_context
        self.strict_mode = strict_mode
        self.timeout_seconds = timeout_seconds
        
        # Validation statistics (from production validator)
        self.validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "mission_critical_failures": 0,
            "last_reset": datetime.now(timezone.utc)
        }
        
        # Event tracking (from SSOT framework validator)
        self.received_events: List[WebSocketEventMessage] = []
        self.event_timestamps: Dict[str, float] = {}
        self.validation_start_time = time.time()
        self.critical_events_received: Set[str] = set()
        self.event_sequence: List[str] = []
        
        # Environment access
        try:
            self.env = get_env()
        except Exception:
            self.env = None
        
        logger.info(f"UnifiedEventValidator initialized in {'strict' if strict_mode else 'permissive'} mode")
    
    def get_required_critical_events(self) -> Set[str]:
        """Get the set of required critical events."""
        return {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
    
    def validate_event(self, event: Dict[str, Any], user_id: str, 
                      connection_id: Optional[str] = None) -> ValidationResult:
        """
        Validate a WebSocket event with comprehensive error checking.
        
        This is the main validation method from the production validator,
        enhanced with business value tracking from the SSOT framework.
        
        Args:
            event: Event data to validate
            user_id: Target user ID
            connection_id: Optional connection ID
            
        Returns:
            ValidationResult with validation outcome and error details
        """
        self.validation_stats["total_validations"] += 1
        
        try:
            # Basic event structure validation
            result = self._validate_basic_structure(event)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Event type specific validation
            event_type = event.get("type", "unknown")
            result = self._validate_event_type(event, event_type)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Mission critical event validation
            if event_type in self.MISSION_CRITICAL_EVENTS:
                result = self._validate_mission_critical_event(event, event_type)
                if not result.is_valid:
                    self.validation_stats["mission_critical_failures"] += 1
                    self.validation_stats["failed_validations"] += 1
                    self._log_mission_critical_failure(result, event, user_id, connection_id)
                    return result
            
            # User context validation
            result = self._validate_user_context(event, user_id)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Success case - record event for business value tracking
            self.record_event(event)
            
            logger.debug(f"✅ Event validation passed: {event_type} for user {user_id[:8]}...")
            return ValidationResult(
                is_valid=True,
                criticality=self._get_event_criticality(event_type),
                received_events=[event_type],
                business_value_score=self._calculate_current_business_value_score()
            )
            
        except Exception as e:
            self.validation_stats["failed_validations"] += 1
            logger.critical(f"🚨 CRITICAL: Event validation exception: {e}")
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: Event validation system failure")
            logger.critical(f"🚨 Impact: Event may be malformed or cause downstream issues")
            # Log stack trace for debugging
            import traceback
            logger.critical(f"🚨 Stack trace: {traceback.format_exc()}")
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation system failure: {e}",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event validation system failure - all events at risk"
            )
    
    def record_event(self, event_data: Union[Dict[str, Any], WebSocketEventMessage]) -> bool:
        """
        Record a WebSocket event for business value tracking.
        
        This method is from the SSOT framework validator, integrated into
        the unified validator for comprehensive event tracking.
        
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
    
    def validate_connection_ready(self, user_id: str, connection_id: str, 
                                 websocket_manager: Optional[Any] = None) -> ValidationResult:
        """
        Validate that connection is ready for event emission.
        
        This method is from the production validator, ensuring connection
        readiness before event emission.
        
        Args:
            user_id: User ID for the connection
            connection_id: Connection ID to validate
            websocket_manager: Optional WebSocket manager to check against
            
        Returns:
            ValidationResult with connection readiness status
        """
        try:
            # Basic parameter validation
            if not user_id or not user_id.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Empty or invalid user_id",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="User cannot receive events - complete chat failure"
                )
            
            if not connection_id or not connection_id.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Empty or invalid connection_id",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="Connection not identifiable - events will be lost"
                )
            
            # WebSocket manager validation
            if websocket_manager is None:
                return ValidationResult(
                    is_valid=False,
                    error_message="WebSocket manager not available",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="No WebSocket infrastructure - all events will fail"
                )
            
            # Connection state validation (if manager supports it)
            if hasattr(websocket_manager, 'is_connection_active'):
                try:
                    is_active = websocket_manager.is_connection_active(connection_id)
                    if not is_active:
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Connection {connection_id} is not active",
                            criticality=EventCriticality.BUSINESS_VALUE,
                            business_impact="User will not receive real-time updates"
                        )
                except Exception as check_error:
                    logger.warning(f"⚠️ Could not check connection status: {check_error}")
                    # Continue with validation - connection check failure is not fatal
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.critical(f"🚨 CRITICAL: Connection validation exception: {e}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Connection validation failure: {e}",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Connection validation system failure"
            )
    
    def validate_event_sequence(self) -> Tuple[bool, List[str]]:
        """
        Validate that events are received in logical order.
        
        This method is from the SSOT framework validator, providing
        comprehensive sequence validation.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        if not self.event_sequence:
            return True, []
        
        # Get critical events in sequence
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
        
        This method is from the SSOT framework validator, providing
        comprehensive timing validation.
        
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
        
        This method is from the SSOT framework validator, providing
        comprehensive content validation.
        
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
    
    def perform_full_validation(self) -> ValidationResult:
        """
        Perform comprehensive validation of all received events.
        
        This method is from the SSOT framework validator, providing
        complete validation with business value assessment.
        
        Returns:
            ValidationResult with complete validation results
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
        result = ValidationResult(
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
    
    def wait_for_critical_events(self, timeout: Optional[float] = None) -> ValidationResult:
        """
        Wait for all critical events to be received.
        
        This method is from the SSOT framework validator, allowing
        async waiting for event completion.
        
        Args:
            timeout: Optional timeout override
            
        Returns:
            ValidationResult once complete or timeout
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
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics for monitoring.
        
        This method is from the production validator, providing
        comprehensive statistics tracking.
        """
        uptime = (datetime.now(timezone.utc) - self.validation_stats["last_reset"]).total_seconds()
        total = self.validation_stats["total_validations"]
        failed = self.validation_stats["failed_validations"]
        
        success_rate = ((total - failed) / total * 100) if total > 0 else 100
        
        return {
            "total_validations": total,
            "failed_validations": failed,
            "mission_critical_failures": self.validation_stats["mission_critical_failures"],
            "success_rate": success_rate,
            "uptime_seconds": uptime,
            "last_reset": self.validation_stats["last_reset"].isoformat(),
            "business_value_score": self._calculate_current_business_value_score(),
            "critical_events_received": len(self.critical_events_received),
            "total_events_received": len(self.received_events)
        }
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "mission_critical_failures": 0,
            "last_reset": datetime.now(timezone.utc)
        }
        
        # Also reset event tracking
        self.received_events.clear()
        self.event_timestamps.clear()
        self.critical_events_received.clear()
        self.event_sequence.clear()
        self.validation_start_time = time.time()
        
        logger.info("WebSocket event validation statistics and event tracking reset")
    
    # Private validation methods (consolidated from both implementations)
    
    def _validate_basic_structure(self, event: Any) -> ValidationResult:
        """Validate basic event structure."""
        if not isinstance(event, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Event is not a dictionary",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Malformed event - cannot be processed"
            )
        
        if "type" not in event:
            return ValidationResult(
                is_valid=False,
                error_message="Event missing required 'type' field",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event type unknown - cannot be routed"
            )
        
        if not event.get("type") or not isinstance(event["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Event 'type' field is empty or not a string",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Invalid event type - cannot be processed"
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_event_type(self, event: Dict[str, Any], event_type: str) -> ValidationResult:
        """Validate event type specific requirements."""
        if event_type in self.EVENT_SCHEMAS:
            required_fields = self.EVENT_SCHEMAS[event_type]
            missing_fields = required_fields - event.keys()
            
            if missing_fields:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Event missing required fields: {missing_fields}",
                    criticality=self._get_event_criticality(event_type),
                    business_impact=f"Incomplete {event_type} event - user experience degraded"
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_mission_critical_event(self, event: Dict[str, Any], event_type: str) -> ValidationResult:
        """Validate mission critical events with strict requirements."""
        # Validate run_id is present and valid
        run_id = event.get("run_id")
        if not run_id or not isinstance(run_id, str) or not run_id.strip():
            return ValidationResult(
                is_valid=False,
                error_message=f"Mission critical event {event_type} missing valid run_id",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event cannot be traced to user execution - chat value lost"
            )
        
        # Validate agent_name for agent events
        if event_type.startswith("agent_") or event_type.startswith("tool_"):
            agent_name = event.get("agent_name")
            if not agent_name or not isinstance(agent_name, str) or not agent_name.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Mission critical event {event_type} missing valid agent_name",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="User cannot identify which AI agent is working"
                )
        
        # Validate payload structure
        payload = event.get("payload")
        if payload is not None and not isinstance(payload, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Mission critical event {event_type} has invalid payload structure",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event payload malformed - user cannot receive complete information"
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_user_context(self, event: Dict[str, Any], user_id: str) -> ValidationResult:
        """Validate user context for security."""
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            return ValidationResult(
                is_valid=False,
                error_message="Invalid user_id for event routing",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event cannot be routed to user - complete failure"
            )
        
        # Check for potential cross-user leakage in event data
        event_user_id = event.get("user_id")
        if event_user_id and event_user_id != user_id:
            return ValidationResult(
                is_valid=False,
                error_message=f"Event contains different user_id ({event_user_id}) than target ({user_id[:8]}...)",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="SECURITY BREACH: Cross-user event leakage detected"
            )
        
        return ValidationResult(is_valid=True)
    
    def _get_event_criticality(self, event_type: str) -> EventCriticality:
        """Determine event criticality level."""
        if event_type in self.MISSION_CRITICAL_EVENTS:
            return EventCriticality.MISSION_CRITICAL
        elif event_type in {"progress_update", "custom"}:
            return EventCriticality.BUSINESS_VALUE
        else:
            return EventCriticality.OPERATIONAL
    
    def _calculate_current_business_value_score(self) -> float:
        """Calculate current business value score based on received events."""
        required_events = self.get_required_critical_events()
        if not required_events:
            return 100.0
        
        return (len(self.critical_events_received) / len(required_events)) * 100
    
    def _log_validation_failure(self, result: ValidationResult, event: Any, 
                               user_id: str, connection_id: Optional[str]):
        """Log validation failure with appropriate severity."""
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        log_level = logger.critical if result.criticality == EventCriticality.MISSION_CRITICAL else logger.error
        
        log_level(f"🚨 EVENT VALIDATION FAILURE: {result.error_message}")
        log_level(f"🚨 Event: {event_type}, User: {user_id[:8]}..., Connection: {connection_id}")
        log_level(f"🚨 Criticality: {result.criticality.value}")
        
        if result.business_impact:
            log_level(f"🚨 BUSINESS IMPACT: {result.business_impact}")
    
    def _log_mission_critical_failure(self, result: ValidationResult, event: Any, 
                                     user_id: str, connection_id: Optional[str]):
        """Log mission critical event failure with maximum visibility."""
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        logger.critical(f"🚨 MISSION CRITICAL EVENT VALIDATION FAILURE")
        logger.critical(f"🚨 Event Type: {event_type}")
        logger.critical(f"🚨 Error: {result.error_message}")
        logger.critical(f"🚨 User: {user_id[:8]}..., Connection: {connection_id}")
        logger.critical(f"🚨 BUSINESS VALUE AT RISK: {result.business_impact}")
        logger.critical(f"🚨 This is a CRITICAL FAILURE requiring immediate attention")
        logger.critical(f"🚨 Mission critical events MUST NOT fail - chat value depends on them")


# Backward Compatibility Aliases and Global Functions

# Global validator instance for backward compatibility
_unified_validator_instance: Optional[UnifiedEventValidator] = None

def get_websocket_validator() -> UnifiedEventValidator:
    """
    Get the global WebSocket event validator instance.
    
    This function provides backward compatibility with the production
    websocket_error_validator.py implementation.
    """
    global _unified_validator_instance
    if _unified_validator_instance is None:
        _unified_validator_instance = UnifiedEventValidator()
    return _unified_validator_instance

def reset_websocket_validator():
    """Reset the global validator instance (for testing)."""
    global _unified_validator_instance
    _unified_validator_instance = None

# SSOT Framework compatibility functions

def validate_agent_events(
    events: List[Union[Dict[str, Any], WebSocketEventMessage]],
    user_context: Optional[StronglyTypedUserExecutionContext] = None,
    strict_mode: bool = True
) -> ValidationResult:
    """
    SSOT function to validate a list of agent events.
    
    This function provides backward compatibility with the SSOT framework
    agent_event_validators.py implementation.
    
    Args:
        events: List of events to validate
        user_context: Optional user execution context
        strict_mode: If True, require ALL 5 critical events
        
    Returns:
        ValidationResult with validation results
    """
    validator = UnifiedEventValidator(user_context=user_context, strict_mode=strict_mode)
    
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

# Backward compatibility aliases
WebSocketEventValidator = UnifiedEventValidator
AgentEventValidator = UnifiedEventValidator
AgentEventValidationResult = ValidationResult

# SSOT Exports
__all__ = [
    # Main classes
    "UnifiedEventValidator",
    "ValidationResult", 
    "WebSocketEventMessage",
    
    # Enums
    "EventCriticality",
    "CriticalAgentEventType",
    
    # Functions
    "get_websocket_validator",
    "reset_websocket_validator",
    "validate_agent_events",
    "assert_critical_events_received",
    "get_critical_event_types",
    "create_mock_critical_events",
    
    # Backward compatibility aliases
    "WebSocketEventValidator",
    "AgentEventValidator", 
    "AgentEventValidationResult"
]