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
import json
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

# Business SLA thresholds for performance logging
SLA_INDIVIDUAL_VALIDATION_MS = 1.0  # Individual event validation should complete in <1ms
SLA_BATCH_VALIDATION_MS = 10.0      # Batch validation should complete in <10ms
SLA_CRITICAL_EVENT_GAP_SEC = 15.0   # Critical events should not have >15s gaps

# Revenue impact thresholds for business logging
REVENUE_IMPACT_THRESHOLDS = {
    "NONE": 0,      # All events received - no revenue impact
    "LOW": 1,       # 1 missing event - minor UX degradation
    "MEDIUM": 2,    # 2 missing events - noticeable UX issues  
    "HIGH": 3,      # 3+ missing events - major UX failure
    "CRITICAL": 999 # agent_completed missing - users never see results
}

def create_structured_log_data(
    event_type: str,
    user_id: str,
    error_type: str = "unknown",
    business_impact: str = "unknown",
    revenue_risk: str = "NONE",
    remediation_action: str = "No action specified",
    **additional_fields
) -> Dict[str, Any]:
    """
    Create structured log data with business context for monitoring systems.
    
    Args:
        event_type: The WebSocket event type that failed
        user_id: Affected user ID (truncated for security)
        error_type: Type of error (validation_failure, missing_field, security_breach, etc.)
        business_impact: Description of business impact
        revenue_risk: Revenue risk level (NONE, LOW, MEDIUM, HIGH, CRITICAL)
        remediation_action: Specific steps to fix the issue
        **additional_fields: Additional structured data
        
    Returns:
        Dictionary of structured log data compatible with JSON logging
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id[:8] + "..." if user_id and len(user_id) > 8 else user_id,
        "error_type": error_type,
        "business_impact": business_impact,
        "revenue_risk": revenue_risk,
        "remediation_action": remediation_action,
        "component": "websocket_event_validator",
        "subsystem": "chat_infrastructure",
        "business_value_protection": "500K_plus_ARR",
        **additional_fields
    }

def get_business_aware_log_level(criticality: 'EventCriticality', missing_events: int = 0, 
                                security_breach: bool = False) -> str:
    """
    Determine business-aware log level based on impact to revenue and user experience.
    
    Args:
        criticality: Event criticality level
        missing_events: Number of missing critical events
        security_breach: Whether this represents a security issue
        
    Returns:
        Log level string (CRITICAL, ERROR, WARNING, INFO)
    """
    if security_breach:
        return "CRITICAL"  # Security breaches are always critical
    
    if criticality == EventCriticality.MISSION_CRITICAL:
        if missing_events == 0:
            return "INFO"  # Single mission critical event succeeded
        elif missing_events == 1:
            return "WARNING"  # One mission critical event missing
        else:
            return "CRITICAL"  # Multiple mission critical events missing
    
    if missing_events >= 3:
        return "ERROR"  # Major UX failure
    elif missing_events >= 1:
        return "WARNING"  # Minor UX degradation
    else:
        return "INFO"  # Normal operation

def get_enhanced_error_message(base_error: str, event_type: str, context: Dict[str, Any]) -> str:
    """
    Convert generic error messages to business-context enhanced error messages.
    
    Args:
        base_error: Original generic error message
        event_type: The WebSocket event type
        context: Additional context for enhancement
        
    Returns:
        Enhanced error message with business context and remediation steps
    """
    # Enhanced error message templates
    enhanced_messages = {
        "Event missing required fields": (
            f"CRITICAL: {event_type} event missing required fields - users cannot see AI processing, "
            f"breaking 90% of platform value. IMMEDIATE ACTION: Verify AgentExecutionTracker includes "
            f"all required fields. Missing fields: {context.get('missing_fields', 'unknown')}"
        ),
        "Event missing required 'type' field": (
            f"CRITICAL: WebSocket event completely malformed - missing 'type' field. This breaks the "
            f"entire chat experience for users. IMMEDIATE ACTION: Check event creation in agent execution "
            f"pipeline - all events must include 'type' field. User: {context.get('user_id', 'unknown')}"
        ),
        "Mission critical event": (
            f"CRITICAL: {event_type} is mission-critical for $500K+ ARR protection. Users will not see "
            f"AI value delivery without this event. IMMEDIATE ACTION: Check agent execution tracker and "
            f"ensure all 5 critical events are sent. Context: {context.get('specific_issue', 'unknown')}"
        ),
        "Event contains different user_id": (
            f"SECURITY BREACH: Cross-user event leakage detected in {event_type} event. This violates "
            f"enterprise security guarantees. IMMEDIATE ACTION: Check user context isolation in agent "
            f"execution. Expected user: {context.get('expected_user', 'unknown')}, "
            f"Found user: {context.get('found_user', 'unknown')}"
        ),
        "Connection not active": (
            f"CONNECTION FAILURE: WebSocket connection inactive for {event_type} event delivery. Users "
            f"will not receive real-time AI progress updates. IMMEDIATE ACTION: Check WebSocket connection "
            f"health in unified_manager.py. Connection: {context.get('connection_id', 'unknown')}"
        )
    }
    
    # Try to find enhanced message by matching base error patterns
    for pattern, enhanced in enhanced_messages.items():
        if pattern in base_error:
            return enhanced
    
    # Fallback: enhance with event context
    return (
        f"VALIDATION FAILURE: {base_error} for {event_type} event. This may impact user experience. "
        f"RECOMMENDED ACTION: Check event creation pipeline and ensure all required fields are present. "
        f"Context: {json.dumps(context, default=str)}"
    )


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
                 timeout_seconds: float = 30.0,
                 validation_mode: str = "realtime"):
        """
        Initialize unified event validator with dual validation modes.
        
        Args:
            user_context: Optional strongly typed user execution context
            strict_mode: If True, require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
            validation_mode: "realtime" for individual events, "sequence" for complete validation
        """
        self.user_context = user_context
        self.strict_mode = strict_mode
        self.timeout_seconds = timeout_seconds
        self.validation_mode = validation_mode
        
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
        
        logger.info(f"UnifiedEventValidator initialized in {'strict' if strict_mode else 'permissive'} mode, validation_mode: {validation_mode}")
    
    def get_required_critical_events(self) -> Set[str]:
        """Get the set of required critical events."""
        return {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
    
    def validate_with_mode(self, event_or_events, user_id: str, 
                          connection_id: Optional[str] = None) -> ValidationResult:
        """
        Validate events based on configured validation mode.
        
        This method provides the dual validation mode functionality:
        - "realtime" mode: Validates individual events as they arrive
        - "sequence" mode: Validates complete event sequences for business value
        
        Args:
            event_or_events: Single event (dict) for realtime, list for sequence
            user_id: Target user ID
            connection_id: Optional connection ID
            
        Returns:
            ValidationResult with mode-appropriate validation
        """
        if self.validation_mode == "realtime":
            # Individual event validation (production validator style)
            if not isinstance(event_or_events, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Realtime mode requires single event dict",
                    criticality=EventCriticality.MISSION_CRITICAL
                )
            return self.validate_event(event_or_events, user_id, connection_id)
            
        elif self.validation_mode == "sequence":
            # Complete sequence validation (SSOT framework style)
            if not isinstance(event_or_events, list):
                return ValidationResult(
                    is_valid=False,
                    error_message="Sequence mode requires list of events",
                    criticality=EventCriticality.MISSION_CRITICAL
                )
            
            # Record all events first
            for event in event_or_events:
                self.record_event(event)
            
            # Perform complete validation
            return self.perform_full_validation()
            
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unknown validation mode: {self.validation_mode}",
                criticality=EventCriticality.MISSION_CRITICAL
            )
    
    def validate_event(self, event: Dict[str, Any], user_id: str, 
                      connection_id: Optional[str] = None) -> ValidationResult:
        """
        Validate a WebSocket event with comprehensive error checking and performance SLA monitoring.
        
        This is the main validation method from the production validator,
        enhanced with business value tracking and performance logging.
        
        Args:
            event: Event data to validate
            user_id: Target user ID
            connection_id: Optional connection ID
            
        Returns:
            ValidationResult with validation outcome and error details
        """
        start_time = time.time()
        self.validation_stats["total_validations"] += 1
        
        try:
            # Basic event structure validation
            result = self._validate_basic_structure(event)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                self._log_performance_with_sla_context(start_time, "validation_failure", event.get("type", "unknown"))
                return result
            
            # Event type specific validation
            event_type = event.get("type", "unknown")
            result = self._validate_event_type(event, event_type)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                self._log_performance_with_sla_context(start_time, "validation_failure", event_type)
                return result
            
            # Mission critical event validation
            if event_type in self.MISSION_CRITICAL_EVENTS:
                result = self._validate_mission_critical_event(event, event_type)
                if not result.is_valid:
                    self.validation_stats["mission_critical_failures"] += 1
                    self.validation_stats["failed_validations"] += 1
                    self._log_mission_critical_failure(result, event, user_id, connection_id)
                    self._log_performance_with_sla_context(start_time, "mission_critical_failure", event_type)
                    return result
            
            # User context validation
            result = self._validate_user_context(event, user_id)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                self._log_performance_with_sla_context(start_time, "validation_failure", event_type)
                return result
            
            # Success case - record event for business value tracking
            self.record_event(event)
            
            # Log successful validation with performance context
            validation_time_ms = (time.time() - start_time) * 1000
            if validation_time_ms > SLA_INDIVIDUAL_VALIDATION_MS:
                logger.warning(
                    f"⚠️ SLA BREACH: Event validation took {validation_time_ms:.2f}ms "
                    f"(SLA: <{SLA_INDIVIDUAL_VALIDATION_MS}ms). Event: {event_type}, User: {user_id[:8]}..."
                )
                logger.warning(
                    f"⚠️ BUSINESS IMPACT: Slow validation may delay real-time chat updates for users"
                )
            else:
                logger.debug(f"✅ Event validation passed: {event_type} for user {user_id[:8]}... ({validation_time_ms:.2f}ms)")
            
            return ValidationResult(
                is_valid=True,
                criticality=self._get_event_criticality(event_type),
                received_events=[event_type],
                business_value_score=self._calculate_current_business_value_score()
            )
            
        except Exception as e:
            validation_time_ms = (time.time() - start_time) * 1000
            self.validation_stats["failed_validations"] += 1
            
            # Enhanced exception logging with business context
            structured_exception_data = create_structured_log_data(
                event_type=event.get("type", "unknown") if isinstance(event, dict) else "malformed",
                user_id=user_id,
                error_type="validation_system_exception",
                business_impact="Event validation system failure - all events at risk",
                revenue_risk="CRITICAL",
                remediation_action="Check validation pipeline, verify event structure, review error logs",
                exception_type=type(e).__name__,
                validation_duration_ms=validation_time_ms,
                connection_id=connection_id
            )
            
            logger.critical(f"🚨 CRITICAL SYSTEM FAILURE: Event validation exception: {e}")
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: Entire validation system compromised")
            logger.critical(f"🚨 REVENUE IMPACT: All WebSocket events at risk for user {user_id[:8]}...")
            logger.critical(f"🚨 PERFORMANCE IMPACT: Validation failed after {validation_time_ms:.2f}ms")
            logger.critical(f"🚨 Structured Exception Data: {json.dumps(structured_exception_data, indent=2)}")
            
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
    
    def _log_performance_with_sla_context(self, start_time: float, outcome: str, event_type: str):
        """Log performance metrics with SLA context and business impact."""
        validation_time_ms = (time.time() - start_time) * 1000
        
        if validation_time_ms > SLA_INDIVIDUAL_VALIDATION_MS:
            # SLA breach - log with business context
            structured_perf_data = {
                "validation_duration_ms": validation_time_ms,
                "sla_threshold_ms": SLA_INDIVIDUAL_VALIDATION_MS,
                "sla_breach": True,
                "event_type": event_type,
                "outcome": outcome,
                "business_impact": "Delayed real-time updates may degrade user experience",
                "remediation_action": "Optimize validation pipeline, check for blocking operations"
            }
            
            logger.warning(
                f"⚠️ PERFORMANCE SLA BREACH: {event_type} validation took {validation_time_ms:.2f}ms "
                f"(SLA: <{SLA_INDIVIDUAL_VALIDATION_MS}ms). Outcome: {outcome}"
            )
            logger.warning(
                f"⚠️ BUSINESS IMPACT: Users may experience delayed chat responses"
            )
            logger.warning(f"⚠️ Performance Data: {json.dumps(structured_perf_data)}")
        else:
            # Within SLA - debug level logging
            logger.debug(
                f"✅ Performance OK: {event_type} validation completed in {validation_time_ms:.2f}ms "
                f"(SLA: <{SLA_INDIVIDUAL_VALIDATION_MS}ms). Outcome: {outcome}"
            )
    
    def _get_remediation_action(self, result: ValidationResult, event_type: str) -> str:
        """Get specific remediation action based on validation failure type."""
        error_message = result.error_message or ""
        
        if "missing required fields" in error_message:
            return (
                f"1. Check AgentExecutionTracker.{event_type}() method. "
                f"2. Verify all required fields are populated. "
                f"3. Test event creation in development environment. "
                f"4. Review EVENT_SCHEMAS in event_validator.py"
            )
        elif "missing valid run_id" in error_message:
            return (
                f"1. Check AgentExecutionTracker.start() includes run_id generation. "
                f"2. Verify UserExecutionContext contains valid run_id. "
                f"3. Check agent_execution_core.py for proper ID propagation. "
                f"4. Test complete agent flow end-to-end"
            )
        elif "cross-user" in error_message.lower():
            return (
                f"1. SECURITY CRITICAL - Check UserExecutionContext isolation. "
                f"2. Verify agent_execution_core.py user context handling. "
                f"3. Review factory pattern implementation for user isolation. "
                f"4. Run security audit on multi-user execution paths"
            )
        elif "connection not active" in error_message.lower():
            return (
                f"1. Check WebSocket connection health in unified_manager.py. "
                f"2. Verify connection cleanup and reconnection logic. "
                f"3. Test WebSocket stability under load. "
                f"4. Review connection pooling configuration"
            )
        else:
            return (
                f"1. Review validation logs for specific error details. "
                f"2. Check {event_type} event creation pipeline. "
                f"3. Verify event structure matches EVENT_SCHEMAS. "
                f"4. Test event flow in development environment"
            )
    
    def _get_mission_critical_remediation(self, event_type: str, error_message: str) -> str:
        """Get mission critical specific remediation actions."""
        base_action = self._get_remediation_action(
            ValidationResult(is_valid=False, error_message=error_message), 
            event_type
        )
        
        mission_critical_prefix = (
            f"IMMEDIATE ACTION for {event_type} (MISSION CRITICAL): "
            f"This event is essential for $500K+ ARR protection. "
        )
        
        event_specific_actions = {
            "agent_started": "Check AgentExecutionTracker.start() and verify agent registration.",
            "agent_completed": "Check AgentExecutionTracker.complete() - users MUST see results.",
            "tool_executing": "Check ToolDispatcher integration and tool event emission.",
            "tool_completed": "Check tool completion handlers and result propagation.",
            "agent_thinking": "Check reasoning event emission in agent execution loop."
        }
        
        specific_action = event_specific_actions.get(event_type, "Check agent execution pipeline.")
        
        return f"{mission_critical_prefix} {specific_action} {base_action}"
    
    def _get_mission_critical_error_message(self, event_type: str, error_message: str, user_id: str) -> str:
        """Get enhanced mission critical error message with business context."""
        business_context = {
            "agent_started": (
                f"Users cannot see that AI processing has begun. This creates the impression that "
                f"the system is broken or unresponsive, leading to user abandonment."
            ),
            "agent_completed": (
                f"Users will NEVER see their AI results. This represents complete chat failure "
                f"and total loss of business value for the user interaction."
            ),
            "tool_executing": (
                f"Users cannot see AI problem-solving transparency. This reduces trust in AI "
                f"decision-making and perceived value of the platform."
            ),
            "tool_completed": (
                f"Users cannot see actionable insights from AI tools. This delivers incomplete "
                f"value and reduces the effectiveness of AI recommendations."
            ),
            "agent_thinking": (
                f"Users have no visibility into AI reasoning process. This creates uncertainty "
                f"about whether the system is processing their request effectively."
            )
        }
        
        context = business_context.get(event_type, "Critical chat functionality compromised")
        
        return (
            f"{event_type.upper()} EVENT FAILURE for user {user_id[:8]}... - {error_message}. "
            f"BUSINESS IMPACT: {context} REVENUE IMPACT: Direct threat to $500K+ ARR from "
            f"degraded chat experience (90% of platform value)."
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
        Validate event timing constraints with enhanced business context logging.
        
        This method is from the SSOT framework validator, providing
        comprehensive timing validation with SLA context.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Check overall execution time
        total_time = time.time() - self.validation_start_time
        if total_time > self.timeout_seconds:
            error_msg = f"Agent execution exceeded timeout: {total_time:.2f}s > {self.timeout_seconds}s"
            errors.append(error_msg)
            
            # Log with business context
            logger.warning(
                f"⚠️ EXECUTION TIMEOUT: Agent took {total_time:.2f}s (timeout: {self.timeout_seconds}s)"
            )
            logger.warning(
                f"⚠️ BUSINESS IMPACT: Users may perceive system as slow or unresponsive"
            )
        
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
                    if gap > SLA_CRITICAL_EVENT_GAP_SEC:
                        error_msg = f"Long gap between {prev_event.event_type} and {curr_event.event_type}: {gap:.2f}s"
                        errors.append(error_msg)
                        
                        # Enhanced logging with business impact
                        logger.warning(
                            f"⚠️ EVENT GAP SLA BREACH: {gap:.2f}s gap between {prev_event.event_type} and {curr_event.event_type} "
                            f"(SLA: <{SLA_CRITICAL_EVENT_GAP_SEC}s)"
                        )
                        logger.warning(
                            f"⚠️ BUSINESS IMPACT: Users experience long delays between AI progress updates"
                        )
                        
                        # Log structured data for monitoring
                        structured_timing_data = create_structured_log_data(
                            event_type="timing_gap_breach",
                            user_id="system",
                            error_type="performance_degradation",
                            business_impact=f"Users experience {gap:.2f}s delay between AI progress updates",
                            revenue_risk="LOW",
                            remediation_action="Check agent execution pipeline for blocking operations or resource constraints",
                            gap_duration_sec=gap,
                            sla_threshold_sec=SLA_CRITICAL_EVENT_GAP_SEC,
                            prev_event=prev_event.event_type,
                            curr_event=curr_event.event_type
                        )
                        logger.warning(f"⚠️ Timing Data: {json.dumps(structured_timing_data)}")
        
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
        Perform comprehensive validation of all received events with enhanced business logging.
        
        This method is from the SSOT framework validator, providing
        complete validation with business value assessment and SLA monitoring.
        
        Returns:
            ValidationResult with complete validation results
        """
        start_time = time.time()
        
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
        
        # Performance logging with SLA context
        validation_time_ms = (time.time() - start_time) * 1000
        if validation_time_ms > SLA_BATCH_VALIDATION_MS:
            logger.warning(
                f"⚠️ BATCH SLA BREACH: Full validation took {validation_time_ms:.2f}ms "
                f"(SLA: <{SLA_BATCH_VALIDATION_MS}ms). Events processed: {len(self.received_events)}"
            )
            logger.warning(
                f"⚠️ BUSINESS IMPACT: Slow batch validation may delay agent execution completion signals"
            )
        
        # Enhanced business logging for validation results
        if result.is_valid:
            structured_success_data = create_structured_log_data(
                event_type="batch_validation",
                user_id="system",
                error_type="none",
                business_impact=f"All critical events received - full chat value delivered",
                revenue_risk="NONE",
                remediation_action="No action required",
                validation_duration_ms=validation_time_ms,
                events_processed=len(self.received_events),
                business_value_score=result.business_value_score,
                critical_events_received=len(self.critical_events_received)
            )
            
            logger.info(f"✅ BUSINESS VALUE DELIVERED: Agent event validation PASSED")
            logger.info(f"✅ Business value score: {result.business_value_score:.1f}% ({len(self.critical_events_received)}/{len(required_events)} critical events)")
            logger.info(f"✅ Chat functionality: FULLY OPERATIONAL - Users receive complete AI experience")
            logger.debug(f"✅ Success Data: {json.dumps(structured_success_data, indent=2)}")
        else:
            # Enhanced failure logging with business context
            structured_failure_data = create_structured_log_data(
                event_type="batch_validation",
                user_id="system",
                error_type="business_value_degradation",
                business_impact=f"Missing {len(missing_events)} critical events - chat value compromised",
                revenue_risk=result.revenue_impact,
                remediation_action=self._get_batch_validation_remediation(missing_events, all_errors),
                validation_duration_ms=validation_time_ms,
                events_processed=len(self.received_events),
                business_value_score=result.business_value_score,
                missing_events=list(missing_events),
                sequence_errors=sequence_errors,
                timing_errors=timing_errors,
                content_errors=content_errors
            )
            
            if result.revenue_impact == "CRITICAL":
                logger.critical(f"🚨 CRITICAL BUSINESS FAILURE: Agent event validation FAILED")
                logger.critical(f"🚨 Revenue impact: {result.revenue_impact} - Users may receive NO AI value")
                logger.critical(f"🚨 Missing critical events: {missing_events}")
                logger.critical(f"🚨 Business value score: {result.business_value_score:.1f}% (UNACCEPTABLE)")
                logger.critical(f"🚨 Chat functionality: SEVERELY COMPROMISED - $500K+ ARR at risk")
            elif result.revenue_impact in ["HIGH", "MEDIUM"]:
                logger.error(f"❌ MAJOR UX DEGRADATION: Agent event validation FAILED")
                logger.error(f"❌ Revenue impact: {result.revenue_impact} - Users receive degraded AI experience")
                logger.error(f"❌ Missing events: {missing_events} - Business value score: {result.business_value_score:.1f}%")
            else:
                logger.warning(f"⚠️ MINOR UX ISSUE: Agent event validation FAILED")
                logger.warning(f"⚠️ Revenue impact: {result.revenue_impact} - Slight degradation in chat experience")
            
            logger.error(f"❌ Failure Data: {json.dumps(structured_failure_data, indent=2)}")
        
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
    
    def _get_batch_validation_remediation(self, missing_events: Set[str], all_errors: List[str]) -> str:
        """Get specific remediation actions for batch validation failures."""
        remediation_steps = []
        
        if missing_events:
            remediation_steps.append(
                f"MISSING EVENTS: Check agent execution pipeline for {missing_events}. "
                f"Verify AgentExecutionTracker emits all 5 critical events."
            )
        
        if any("sequence" in error for error in all_errors):
            remediation_steps.append(
                "SEQUENCE ERRORS: Check agent execution order - agent_started must come before agent_completed."
            )
        
        if any("timeout" in error or "gap" in error for error in all_errors):
            remediation_steps.append(
                "TIMING ERRORS: Check for stalled agent execution. Review agent timeout configuration."
            )
        
        if any("content" in error or "missing data" in error for error in all_errors):
            remediation_steps.append(
                "CONTENT ERRORS: Check event payload structure. Verify all required fields are populated."
            )
        
        if not remediation_steps:
            remediation_steps.append("Review agent execution logs and event emission pipeline.")
        
        return " ".join(remediation_steps)
    
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
        """Log validation failure with enhanced business context and structured data."""
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        # Determine business-aware log level
        missing_events = len(result.missing_critical_events) if hasattr(result, 'missing_critical_events') else 0
        is_security_issue = "cross-user" in (result.error_message or "").lower() or "security" in (result.business_impact or "").lower()
        business_log_level = get_business_aware_log_level(result.criticality, missing_events, is_security_issue)
        
        # Create enhanced error message with business context
        context = {
            'missing_fields': getattr(result, 'missing_fields', None),
            'user_id': user_id[:8] + "..." if user_id else None,
            'connection_id': connection_id,
            'specific_issue': result.error_message,
            'revenue_impact': getattr(result, 'revenue_impact', 'UNKNOWN')
        }
        enhanced_error = get_enhanced_error_message(result.error_message or "Unknown validation error", event_type, context)
        
        # Create structured log data for monitoring systems
        structured_data = create_structured_log_data(
            event_type=event_type,
            user_id=user_id,
            error_type="event_validation_failure",
            business_impact=result.business_impact or f"Validation failure for {event_type} event",
            revenue_risk=getattr(result, 'revenue_impact', 'UNKNOWN'),
            remediation_action=self._get_remediation_action(result, event_type),
            connection_id=connection_id,
            criticality=result.criticality.value,
            missing_events_count=missing_events,
            business_value_score=getattr(result, 'business_value_score', 0.0)
        )
        
        # Log with appropriate severity based on business impact
        if business_log_level == "CRITICAL":
            logger.critical(f"🚨 CRITICAL BUSINESS IMPACT: {enhanced_error}")
            logger.critical(f"🚨 Structured Data: {json.dumps(structured_data, indent=2)}")
        elif business_log_level == "ERROR":
            logger.error(f"❌ MAJOR UX FAILURE: {enhanced_error}")
            logger.error(f"❌ Structured Data: {json.dumps(structured_data, indent=2)}")
        elif business_log_level == "WARNING":
            logger.warning(f"⚠️ UX DEGRADATION: {enhanced_error}")
            logger.warning(f"⚠️ Structured Data: {json.dumps(structured_data, indent=2)}")
        else:
            logger.info(f"ℹ️ VALIDATION INFO: {enhanced_error}")
            logger.info(f"ℹ️ Structured Data: {json.dumps(structured_data, indent=2)}")
        
        # Additional business context logging
        if result.criticality == EventCriticality.MISSION_CRITICAL:
            logger.critical(f"💰 REVENUE PROTECTION ALERT: Mission critical event {event_type} failed validation")
            logger.critical(f"💰 This directly impacts the $500K+ ARR protected by WebSocket event delivery")
            logger.critical(f"💰 Chat functionality (90% of platform value) may be degraded for user {user_id[:8]}...")
    
    def _log_mission_critical_failure(self, result: ValidationResult, event: Any, 
                                     user_id: str, connection_id: Optional[str]):
        """Log mission critical event failure with maximum business visibility and actionable remediation."""
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        # Create comprehensive structured data for mission critical failures
        structured_data = create_structured_log_data(
            event_type=event_type,
            user_id=user_id,
            error_type="mission_critical_failure",
            business_impact=f"CRITICAL: {event_type} event failure blocks revenue-generating chat functionality",
            revenue_risk="CRITICAL",
            remediation_action=self._get_mission_critical_remediation(event_type, result.error_message),
            connection_id=connection_id,
            affected_user_count=1,
            revenue_at_risk="$500K+ ARR",
            platform_value_impact="90% of platform value",
            urgency="IMMEDIATE",
            escalation_required=True
        )
        
        # Enhanced mission critical error message with specific business context
        enhanced_error = self._get_mission_critical_error_message(event_type, result.error_message, user_id)
        
        # LOUD logging for mission critical failures
        logger.critical("" + "=" * 100)
        logger.critical("🚨🚨🚨 MISSION CRITICAL BUSINESS FAILURE 🚨🚨🚨")
        logger.critical("=" * 100)
        logger.critical(f"💥 CRITICAL FAILURE: {enhanced_error}")
        logger.critical(f"💥 Event Type: {event_type} (MISSION CRITICAL for user experience)")
        logger.critical(f"💥 Affected User: {user_id[:8]}... (Connection: {connection_id})")
        logger.critical(f"💥 Revenue Impact: CRITICAL - $500K+ ARR at risk")
        logger.critical(f"💥 Business Impact: {result.business_impact}")
        logger.critical(f"💥 Platform Value Impact: 90% of chat functionality affected")
        logger.critical("=" * 100)
        logger.critical("🔧 IMMEDIATE REMEDIATION REQUIRED:")
        logger.critical(f"🔧 {self._get_mission_critical_remediation(event_type, result.error_message)}")
        logger.critical("=" * 100)
        logger.critical(f"📊 Structured Monitoring Data: {json.dumps(structured_data, indent=2)}")
        logger.critical("=" * 100)
        
        # Additional context based on specific event type
        if event_type == "agent_started":
            logger.critical("🎯 SPECIFIC IMPACT: Users cannot see that AI processing has begun")
            logger.critical("🎯 USER EXPERIENCE: Users may think the system is broken or unresponsive")
        elif event_type == "agent_completed":
            logger.critical("🎯 SPECIFIC IMPACT: Users will NEVER see their AI results")
            logger.critical("🎯 USER EXPERIENCE: Complete chat failure - users get no value")
        elif event_type == "tool_executing":
            logger.critical("🎯 SPECIFIC IMPACT: Users cannot see AI problem-solving in progress")
            logger.critical("🎯 USER EXPERIENCE: Reduced transparency in AI decision-making")
        elif event_type == "tool_completed":
            logger.critical("🎯 SPECIFIC IMPACT: Users cannot see actionable insights from AI tools")
            logger.critical("🎯 USER EXPERIENCE: Incomplete information delivery")
        
        # Performance impact logging if applicable
        if hasattr(self, 'validation_stats'):
            failure_rate = (self.validation_stats['mission_critical_failures'] / 
                          max(self.validation_stats['total_validations'], 1)) * 100
            logger.critical(f"📈 SYSTEM HEALTH: Mission critical failure rate: {failure_rate:.2f}%")
            if failure_rate > 1.0:  # More than 1% mission critical failure rate is alarming
                logger.critical(f"📈 ALERT: Mission critical failure rate exceeds acceptable threshold (1.0%)")


# Backward Compatibility Aliases and Global Functions

# Global validator instance for backward compatibility
_unified_validator_instance: Optional[UnifiedEventValidator] = None

def get_websocket_validator() -> UnifiedEventValidator:
    """
    Get the global WebSocket event validator instance.
    
    This function provides backward compatibility with the production
    websocket_error_validator.py implementation (realtime mode).
    """
    global _unified_validator_instance
    if _unified_validator_instance is None:
        _unified_validator_instance = UnifiedEventValidator(validation_mode="realtime")
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
    agent_event_validators.py implementation (sequence mode).
    
    Args:
        events: List of events to validate
        user_context: Optional user execution context
        strict_mode: If True, require ALL 5 critical events
        
    Returns:
        ValidationResult with validation results
    """
    validator = UnifiedEventValidator(
        user_context=user_context, 
        strict_mode=strict_mode,
        validation_mode="sequence"
    )
    
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
            timestamp=base_time.replace(microsecond=100000),
            data={"agent": agent_name, "progress": "thinking"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.TOOL_EXECUTING.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(microsecond=200000),
            data={"tool": tool_name, "status": "executing"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.TOOL_COMPLETED.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(microsecond=300000),
            data={"tool": tool_name, "status": "completed", "result": "mock result"}
        ),
        WebSocketEventMessage(
            event_type=CriticalAgentEventType.AGENT_COMPLETED.value,
            user_id=user_id,
            thread_id=thread_id,
            timestamp=base_time.replace(microsecond=400000),
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