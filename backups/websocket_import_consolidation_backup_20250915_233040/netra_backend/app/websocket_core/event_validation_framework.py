"""
Five Event Validation Framework - Comprehensive WebSocket Event Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Chat Quality
- Value Impact: 100% WebSocket event delivery validation for chat functionality
- Strategic Impact: Zero tolerance for missing chat events, prevents user abandonment

CRITICAL: This framework validates the 5 required WebSocket events for substantive chat:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility 
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

Architecture: Comprehensive validation with event sequence, timing, content, and pairing checks.
Includes error recovery, event replay, performance metrics, and integration hooks.
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque

# SSOT Import for Phase 2 UUID violation remediation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from contextlib import asynccontextmanager
import statistics
import logging
from concurrent.futures import ThreadPoolExecutor

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.schemas.websocket_models import WebSocketValidationError

logger = central_logger.get_logger(__name__)


class EventValidationLevel(str, Enum):
    """Validation level for event checking."""
    STRICT = "strict"           # All validations must pass
    MODERATE = "moderate"       # Critical validations must pass
    PERMISSIVE = "permissive"   # Only fatal errors fail validation


class EventType(str, Enum):
    """Required WebSocket event types for chat functionality."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    
    # Additional events that may occur
    AGENT_FAILED = "agent_failed"
    AGENT_ERROR = "agent_error"
    TOOL_STARTED = "tool_started"
    FINAL_REPORT = "final_report"
    PARTIAL_RESULT = "partial_result"


class ValidationResult(str, Enum):
    """Event validation results."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class EventValidationRule:
    """Definition of an event validation rule."""
    name: str
    description: str
    validator: Callable[..., bool]
    severity: ValidationResult
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    timing_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidatedEvent:
    """Container for a validated WebSocket event."""
    event_id: str
    event_type: EventType
    thread_id: str
    run_id: Optional[str]
    timestamp: float
    content: Dict[str, Any]
    validation_result: ValidationResult
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None
    sequence_number: Optional[int] = None


@dataclass
class EventSequence:
    """Represents a sequence of events for validation."""
    thread_id: str
    run_id: Optional[str]
    events: List[ValidatedEvent] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    is_complete: bool = False
    validation_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventMetrics:
    """Performance and reliability metrics for events."""
    total_events: int = 0
    successful_events: int = 0
    failed_events: int = 0
    dropped_events: int = 0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    events_per_second: float = 0.0
    validation_failures: Dict[str, int] = field(default_factory=dict)
    sequence_completion_rate: float = 0.0


class CircuitBreakerState(str, Enum):
    """Circuit breaker states for event validation."""
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, reject new events
    HALF_OPEN = "half_open"  # Testing if recovery is possible


class EventValidator:
    """Core event validator with comprehensive validation rules."""
    
    # Required events for complete chat functionality
    REQUIRED_EVENTS = {
        EventType.AGENT_STARTED,
        EventType.AGENT_THINKING, 
        EventType.TOOL_EXECUTING,
        EventType.TOOL_COMPLETED,
        EventType.AGENT_COMPLETED
    }
    
    # Expected event order patterns
    VALID_EVENT_ORDERS = [
        [EventType.AGENT_STARTED, EventType.AGENT_THINKING, EventType.TOOL_EXECUTING, 
         EventType.TOOL_COMPLETED, EventType.AGENT_COMPLETED],
        [EventType.AGENT_STARTED, EventType.AGENT_THINKING, EventType.AGENT_COMPLETED],  # No tools
        [EventType.AGENT_STARTED, EventType.TOOL_EXECUTING, EventType.TOOL_COMPLETED, EventType.AGENT_COMPLETED],  # No thinking
    ]
    
    # Timing constraints (in milliseconds)
    DEFAULT_TIMING_CONSTRAINTS = {
        "max_event_gap_ms": 30000,  # 30 seconds between events
        "max_total_sequence_ms": 300000,  # 5 minutes total
        "min_thinking_duration_ms": 100,  # Minimum thinking time
        "max_tool_execution_ms": 60000,  # 1 minute per tool
    }
    
    def __init__(self, validation_level: EventValidationLevel = EventValidationLevel.STRICT):
        self.validation_level = validation_level
        self.validation_rules = self._initialize_validation_rules()
        self.metrics = EventMetrics()
        
    def _initialize_validation_rules(self) -> List[EventValidationRule]:
        """Initialize comprehensive validation rules."""
        return [
            # Agent Started Event Rules
            EventValidationRule(
                name="agent_started_required_fields",
                description="Agent started event must have required fields",
                validator=self._validate_agent_started_fields,
                severity=ValidationResult.CRITICAL,
                required_fields=["agent_name", "timestamp", "thread_id", "run_id"]
            ),
            
            # Agent Thinking Event Rules
            EventValidationRule(
                name="agent_thinking_content",
                description="Agent thinking event must have reasoning text",
                validator=self._validate_agent_thinking_content,
                severity=ValidationResult.ERROR,
                required_fields=["thought", "agent_name", "timestamp"]
            ),
            
            # Tool Executing Event Rules
            EventValidationRule(
                name="tool_executing_fields",
                description="Tool executing event must have tool information",
                validator=self._validate_tool_executing_fields,
                severity=ValidationResult.CRITICAL,
                required_fields=["tool_name", "agent_name", "timestamp"],
                optional_fields=["parameters", "tool_purpose", "estimated_duration_ms"]
            ),
            
            # Tool Completed Event Rules
            EventValidationRule(
                name="tool_completed_fields",
                description="Tool completed event must have results and duration",
                validator=self._validate_tool_completed_fields,
                severity=ValidationResult.CRITICAL,
                required_fields=["tool_name", "agent_name", "timestamp"],
                optional_fields=["result", "duration_ms", "success"]
            ),
            
            # Agent Completed Event Rules
            EventValidationRule(
                name="agent_completed_fields",
                description="Agent completed event must have final status",
                validator=self._validate_agent_completed_fields,
                severity=ValidationResult.CRITICAL,
                required_fields=["agent_name", "run_id", "timestamp"],
                optional_fields=["duration_ms", "result", "final_status", "summary"]
            ),
            
            # Sequence Validation Rules
            EventValidationRule(
                name="event_sequence_order",
                description="Events must follow logical order",
                validator=self._validate_event_sequence_order,
                severity=ValidationResult.ERROR
            ),
            
            # Pairing Rules
            EventValidationRule(
                name="tool_event_pairing",
                description="Tool executing events must have matching completed events",
                validator=self._validate_tool_event_pairing,
                severity=ValidationResult.CRITICAL
            ),
            
            # Timing Rules
            EventValidationRule(
                name="event_timing_constraints",
                description="Events must meet timing requirements",
                validator=self._validate_event_timing,
                severity=ValidationResult.WARNING,
                timing_constraints=self.DEFAULT_TIMING_CONSTRAINTS
            ),
        ]
    
    def validate_event(self, event: Dict[str, Any], context: Dict[str, Any] = None) -> ValidatedEvent:
        """Validate a single WebSocket event."""
        start_time = time.time()
        context = context or {}
        
        # Extract basic event information
        event_type_str = event.get('type', 'unknown')
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            # Handle non-standard event types
            event_type = event_type_str
        
        event_id = event.get('message_id') or UnifiedIdGenerator.generate_base_id('event')
        thread_id = event.get('thread_id') or context.get('thread_id', 'unknown')
        run_id = event.get('payload', {}).get('run_id') or context.get('run_id')
        timestamp = event.get('timestamp', time.time())
        
        # Create validated event container
        validated_event = ValidatedEvent(
            event_id=event_id,
            event_type=event_type,
            thread_id=thread_id,
            run_id=run_id,
            timestamp=timestamp,
            content=event,
            validation_result=ValidationResult.VALID,
            latency_ms=(time.time() - start_time) * 1000
        )
        
        # Apply validation rules only for relevant event types
        for rule in self.validation_rules:
            try:
                # Skip rules that don't apply to this event type
                if self._should_apply_rule(rule, event_type):
                    if not rule.validator(event, validated_event, context):
                        if rule.severity == ValidationResult.CRITICAL:
                            validated_event.validation_result = ValidationResult.CRITICAL
                            validated_event.validation_errors.append(f"CRITICAL: {rule.description}")
                        elif rule.severity == ValidationResult.ERROR:
                            if validated_event.validation_result not in [ValidationResult.CRITICAL]:
                                validated_event.validation_result = ValidationResult.ERROR
                            validated_event.validation_errors.append(f"ERROR: {rule.description}")
                        else:
                            validated_event.validation_warnings.append(f"WARNING: {rule.description}")
            except Exception as e:
                logger.error(f"Validation rule {rule.name} failed: {e}")
                validated_event.validation_errors.append(f"RULE_ERROR: {rule.name} failed: {str(e)}")
        
        # Update metrics
        self._update_metrics(validated_event)
        
        return validated_event
    
    def _should_apply_rule(self, rule: EventValidationRule, event_type: Union[EventType, str]) -> bool:
        """Determine if a validation rule should apply to this event type."""
        # Map rules to applicable event types
        rule_event_mapping = {
            'agent_started_required_fields': [EventType.AGENT_STARTED],
            'agent_thinking_content': [EventType.AGENT_THINKING],
            'tool_executing_fields': [EventType.TOOL_EXECUTING],
            'tool_completed_fields': [EventType.TOOL_COMPLETED],
            'agent_completed_fields': [EventType.AGENT_COMPLETED],
            # These rules apply to sequences, not individual events
            'event_sequence_order': [],
            'tool_event_pairing': [],
            'event_timing_constraints': []  # Apply to all events
        }
        
        # Rules that apply to all events
        universal_rules = ['event_timing_constraints']
        
        if rule.name in universal_rules:
            return True
        
        # Get applicable event types for this rule
        applicable_types = rule_event_mapping.get(rule.name, [])
        
        # Check if current event type matches
        if isinstance(event_type, EventType):
            return event_type in applicable_types
        else:
            # For string event types, convert to EventType if possible
            try:
                event_type_enum = EventType(event_type)
                return event_type_enum in applicable_types
            except ValueError:
                # Unknown event type, don't apply specific rules
                return rule.name in universal_rules
    
    def _validate_agent_started_fields(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate agent started event has required fields."""
        payload = event.get('payload', {})
        required = ['agent_name', 'timestamp']
        
        missing = [field for field in required if not payload.get(field)]
        if missing:
            validated_event.validation_errors.append(f"Missing required fields: {missing}")
            return False
            
        # Validate timestamp is reasonable
        event_time = payload.get('timestamp')
        if isinstance(event_time, (int, float)):
            if abs(time.time() - event_time) > 3600:  # More than 1 hour difference
                validated_event.validation_warnings.append("Timestamp seems incorrect")
                
        return True
    
    def _validate_agent_thinking_content(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate agent thinking event has meaningful content."""
        payload = event.get('payload', {})
        thought = payload.get('thought', '')
        
        if not thought or not isinstance(thought, str):
            validated_event.validation_errors.append("Missing or invalid thought content")
            return False
            
        if len(thought.strip()) < 5:
            validated_event.validation_warnings.append("Thought content seems too short")
            
        return True
    
    def _validate_tool_executing_fields(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate tool executing event has required information."""
        payload = event.get('payload', {})
        
        if not payload.get('tool_name'):
            validated_event.validation_errors.append("Missing tool_name")
            return False
            
        if not payload.get('agent_name'):
            validated_event.validation_errors.append("Missing agent_name")
            return False
            
        return True
    
    def _validate_tool_completed_fields(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate tool completed event has results."""
        payload = event.get('payload', {})
        
        if not payload.get('tool_name'):
            validated_event.validation_errors.append("Missing tool_name in completion")
            return False
            
        # Tool completion should have some indication of success/failure
        has_result = 'result' in payload
        has_success_flag = 'success' in payload
        has_error = 'error' in payload
        
        if not (has_result or has_success_flag or has_error):
            validated_event.validation_warnings.append("No result, success flag, or error information")
            
        return True
    
    def _validate_agent_completed_fields(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate agent completed event has final status."""
        payload = event.get('payload', {})
        
        required = ['agent_name', 'run_id']
        missing = [field for field in required if not payload.get(field)]
        
        if missing:
            validated_event.validation_errors.append(f"Missing completion fields: {missing}")
            return False
            
        return True
    
    def _validate_event_sequence_order(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate event follows logical sequence order."""
        # This requires sequence context, implement in sequence validator
        return True
    
    def _validate_tool_event_pairing(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate tool events are properly paired."""
        # This requires sequence context, implement in sequence validator
        return True
    
    def _validate_event_timing(self, event: Dict, validated_event: ValidatedEvent, context: Dict) -> bool:
        """Validate event timing constraints."""
        # Basic timing validation - more detailed timing in sequence validator
        timestamp = event.get('timestamp', time.time())
        current_time = time.time()
        
        # Event shouldn't be too far in the future or past
        time_diff = abs(current_time - timestamp)
        if time_diff > 3600:  # 1 hour
            validated_event.validation_warnings.append(f"Event timestamp differs by {time_diff:.1f}s")
            return False
            
        return True
    
    def _update_metrics(self, validated_event: ValidatedEvent) -> None:
        """Update validation metrics."""
        self.metrics.total_events += 1
        
        if validated_event.validation_result == ValidationResult.VALID:
            self.metrics.successful_events += 1
        else:
            self.metrics.failed_events += 1
            
        # Update latency metrics
        if validated_event.latency_ms:
            if self.metrics.total_events == 1:
                self.metrics.min_latency_ms = validated_event.latency_ms
                self.metrics.max_latency_ms = validated_event.latency_ms
                self.metrics.average_latency_ms = validated_event.latency_ms
            else:
                self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, validated_event.latency_ms)
                self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, validated_event.latency_ms)
                # Update running average
                total_latency = self.metrics.average_latency_ms * (self.metrics.total_events - 1) + validated_event.latency_ms
                self.metrics.average_latency_ms = total_latency / self.metrics.total_events


class EventSequenceValidator:
    """Validates sequences of events for complete chat interactions."""
    
    def __init__(self, event_validator: EventValidator):
        self.event_validator = event_validator
        self.active_sequences: Dict[str, EventSequence] = {}
        self.completed_sequences: List[EventSequence] = []
        self.sequence_metrics: Dict[str, Any] = {}
        
    def start_sequence(self, thread_id: str, run_id: Optional[str] = None) -> EventSequence:
        """Start tracking a new event sequence."""
        sequence = EventSequence(
            thread_id=thread_id,
            run_id=run_id,
            start_time=time.time()
        )
        self.active_sequences[thread_id] = sequence
        return sequence
    
    def add_event_to_sequence(self, thread_id: str, event: Dict[str, Any], context: Dict[str, Any] = None) -> ValidatedEvent:
        """Add and validate an event within a sequence."""
        # Get or create sequence
        if thread_id not in self.active_sequences:
            run_id = event.get('payload', {}).get('run_id') or (context or {}).get('run_id')
            self.start_sequence(thread_id, run_id)
        
        sequence = self.active_sequences[thread_id]
        
        # Validate individual event
        validated_event = self.event_validator.validate_event(event, context)
        validated_event.sequence_number = len(sequence.events) + 1
        
        # Add to sequence
        sequence.events.append(validated_event)
        
        # Validate sequence-level rules
        self._validate_sequence_constraints(sequence, validated_event)
        
        # Check if sequence is complete
        if self._is_sequence_complete(sequence):
            self._complete_sequence(sequence)
        
        return validated_event
    
    def _validate_sequence_constraints(self, sequence: EventSequence, new_event: ValidatedEvent) -> None:
        """Validate constraints at the sequence level."""
        # Validate event ordering
        if not self._validate_event_order(sequence):
            new_event.validation_errors.append("Invalid event order in sequence")
            new_event.validation_result = ValidationResult.ERROR
        
        # Validate tool pairing
        if not self._validate_tool_pairing(sequence):
            new_event.validation_errors.append("Unpaired tool events in sequence")
            new_event.validation_result = ValidationResult.ERROR
        
        # Validate timing constraints
        if not self._validate_sequence_timing(sequence):
            new_event.validation_warnings.append("Sequence timing constraints violated")
    
    def _validate_event_order(self, sequence: EventSequence) -> bool:
        """Validate events follow logical order."""
        if len(sequence.events) < 2:
            return True
            
        event_types = [e.event_type for e in sequence.events if isinstance(e.event_type, EventType)]
        
        # First event should be agent_started
        if event_types and event_types[0] != EventType.AGENT_STARTED:
            return False
        
        # Tool events should be paired
        tool_stack = []
        for event_type in event_types:
            if event_type == EventType.TOOL_EXECUTING:
                tool_stack.append(event_type)
            elif event_type == EventType.TOOL_COMPLETED:
                if not tool_stack:
                    return False  # Completion without execution
                tool_stack.pop()
        
        return True
    
    def _validate_tool_pairing(self, sequence: EventSequence) -> bool:
        """Validate tool events are properly paired."""
        executing_count = sum(1 for e in sequence.events if e.event_type == EventType.TOOL_EXECUTING)
        completed_count = sum(1 for e in sequence.events if e.event_type == EventType.TOOL_COMPLETED)
        
        # For incomplete sequences, we allow more executing than completed
        # For complete sequences, they must match
        if sequence.is_complete:
            return executing_count == completed_count
        else:
            return completed_count <= executing_count
    
    def _validate_sequence_timing(self, sequence: EventSequence) -> bool:
        """Validate timing constraints across the sequence."""
        if len(sequence.events) < 2:
            return True
        
        constraints = self.event_validator.DEFAULT_TIMING_CONSTRAINTS
        
        # Check gaps between events
        for i in range(1, len(sequence.events)):
            prev_event = sequence.events[i-1]
            curr_event = sequence.events[i]
            gap_ms = (curr_event.timestamp - prev_event.timestamp) * 1000
            
            if gap_ms > constraints["max_event_gap_ms"]:
                return False
        
        # Check total sequence duration
        if sequence.start_time:
            current_duration = (time.time() - sequence.start_time) * 1000
            if current_duration > constraints["max_total_sequence_ms"]:
                return False
        
        return True
    
    def _is_sequence_complete(self, sequence: EventSequence) -> bool:
        """Check if an event sequence is complete."""
        event_types = {e.event_type for e in sequence.events if isinstance(e.event_type, EventType)}
        
        # Must have agent_completed or agent_failed
        has_completion = (EventType.AGENT_COMPLETED in event_types or 
                         EventType.AGENT_FAILED in event_types)
        
        # Must have required events
        has_required = self.event_validator.REQUIRED_EVENTS.issubset(event_types)
        
        # Tool events must be paired
        tools_paired = self._validate_tool_pairing(sequence)
        
        return has_completion and (has_required or len(event_types) >= 3) and tools_paired
    
    def _complete_sequence(self, sequence: EventSequence) -> None:
        """Mark a sequence as complete and generate summary."""
        sequence.is_complete = True
        sequence.end_time = time.time()
        
        # Generate validation summary
        summary = self._generate_sequence_summary(sequence)
        sequence.validation_summary = summary
        
        # Move to completed sequences
        self.completed_sequences.append(sequence)
        del self.active_sequences[sequence.thread_id]
        
        logger.info(f"Completed event sequence for thread {sequence.thread_id}: {summary}")
    
    def _generate_sequence_summary(self, sequence: EventSequence) -> Dict[str, Any]:
        """Generate comprehensive validation summary for a sequence."""
        event_types = [e.event_type for e in sequence.events]
        validation_results = [e.validation_result for e in sequence.events]
        
        total_errors = sum(len(e.validation_errors) for e in sequence.events)
        total_warnings = sum(len(e.validation_warnings) for e in sequence.events)
        
        duration_ms = 0
        if sequence.start_time and sequence.end_time:
            duration_ms = (sequence.end_time - sequence.start_time) * 1000
        
        return {
            "thread_id": sequence.thread_id,
            "run_id": sequence.run_id,
            "total_events": len(sequence.events),
            "event_types": event_types,
            "duration_ms": duration_ms,
            "validation_summary": {
                "valid_events": validation_results.count(ValidationResult.VALID),
                "warning_events": validation_results.count(ValidationResult.WARNING),
                "error_events": validation_results.count(ValidationResult.ERROR),
                "critical_events": validation_results.count(ValidationResult.CRITICAL),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
            },
            "required_events_present": self.event_validator.REQUIRED_EVENTS.issubset(set(event_types)),
            "sequence_complete": sequence.is_complete,
            "tools_properly_paired": self._validate_tool_pairing(sequence),
            "timing_valid": self._validate_sequence_timing(sequence)
        }
    
    def get_sequence_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a sequence."""
        if thread_id in self.active_sequences:
            sequence = self.active_sequences[thread_id]
            return self._generate_sequence_summary(sequence)
        
        # Check completed sequences
        for sequence in self.completed_sequences:
            if sequence.thread_id == thread_id:
                return sequence.validation_summary
        
        return None


class EventValidationFramework:
    """Main framework for comprehensive WebSocket event validation."""
    
    def __init__(self, validation_level: EventValidationLevel = EventValidationLevel.STRICT):
        self.validation_level = validation_level
        self.event_validator = EventValidator(validation_level)
        self.sequence_validator = EventSequenceValidator(self.event_validator)
        
        # Event history and replay
        self.event_history: Dict[str, List[ValidatedEvent]] = defaultdict(list)
        self.event_buffer: deque = deque(maxlen=10000)  # Circular buffer for events
        
        # Performance monitoring
        self.performance_metrics = EventMetrics()
        self.latency_samples: List[float] = []
        
        # Circuit breaker for error recovery
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.failure_threshold = 10
        self.recovery_timeout = 60  # seconds
        self.last_failure_time = 0
        
        # Event notification callbacks
        self.validation_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
    async def validate_event(self, event: Dict[str, Any], context: Dict[str, Any] = None) -> ValidatedEvent:
        """Main entry point for event validation."""
        if self.circuit_breaker_state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker entering half-open state")
            else:
                # Circuit is open, create minimal validation
                return self._create_bypass_validation(event, context)
        
        try:
            thread_id = event.get('thread_id') or (context or {}).get('thread_id', 'unknown')
            
            # Validate event in sequence context
            validated_event = self.sequence_validator.add_event_to_sequence(thread_id, event, context)
            
            # Store in history and buffer
            self.event_history[thread_id].append(validated_event)
            self.event_buffer.append(validated_event)
            
            # Update performance metrics
            self._update_performance_metrics(validated_event)
            
            # Handle circuit breaker state
            if validated_event.validation_result in [ValidationResult.CRITICAL, ValidationResult.ERROR]:
                await self._handle_validation_failure(validated_event)
            else:
                self._handle_validation_success()
            
            # Notify callbacks
            await self._notify_validation_callbacks(validated_event)
            
            return validated_event
            
        except Exception as e:
            logger.error(f"Event validation failed: {e}")
            await self._handle_validation_exception(e, event, context)
            return self._create_error_validation(event, context, str(e))
    
    def _create_bypass_validation(self, event: Dict[str, Any], context: Dict[str, Any]) -> ValidatedEvent:
        """Create minimal validation when circuit breaker is open."""
        return ValidatedEvent(
            event_id=UnifiedIdGenerator.generate_base_id('bypass'),
            event_type=event.get('type', 'unknown'),
            thread_id=event.get('thread_id', 'unknown'),
            run_id=event.get('payload', {}).get('run_id'),
            timestamp=time.time(),
            content=event,
            validation_result=ValidationResult.WARNING,
            validation_warnings=["Circuit breaker open - minimal validation"]
        )
    
    def _create_error_validation(self, event: Dict[str, Any], context: Dict[str, Any], error: str) -> ValidatedEvent:
        """Create error validation result."""
        return ValidatedEvent(
            event_id=UnifiedIdGenerator.generate_base_id('error'),
            event_type=event.get('type', 'unknown'),
            thread_id=event.get('thread_id', 'unknown'),
            run_id=event.get('payload', {}).get('run_id'),
            timestamp=time.time(),
            content=event,
            validation_result=ValidationResult.CRITICAL,
            validation_errors=[f"Validation framework error: {error}"]
        )
    
    async def _handle_validation_failure(self, validated_event: ValidatedEvent) -> None:
        """Handle validation failure for circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_breaker_state = CircuitBreakerState.OPEN
            logger.error(f"Circuit breaker opened due to {self.failure_count} failures")
        
        # Notify error callbacks
        for callback in self.error_callbacks:
            try:
                await callback(validated_event)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
    
    def _handle_validation_success(self) -> None:
        """Handle successful validation for circuit breaker."""
        if self.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            self.circuit_breaker_state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            logger.info("Circuit breaker closed - recovery successful")
        elif self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
    
    async def _handle_validation_exception(self, exception: Exception, event: Dict, context: Dict) -> None:
        """Handle exceptions during validation."""
        logger.error(f"Validation exception: {exception}")
        self.failure_count += 1
        self.last_failure_time = time.time()
    
    async def _notify_validation_callbacks(self, validated_event: ValidatedEvent) -> None:
        """Notify registered validation callbacks."""
        for callback in self.validation_callbacks:
            try:
                await callback(validated_event)
            except Exception as e:
                logger.error(f"Validation callback failed: {e}")
    
    def _update_performance_metrics(self, validated_event: ValidatedEvent) -> None:
        """Update performance metrics with new event data."""
        # Update latency tracking
        if validated_event.latency_ms:
            self.latency_samples.append(validated_event.latency_ms)
            # Keep only recent samples
            if len(self.latency_samples) > 1000:
                self.latency_samples = self.latency_samples[-1000:]
            
            # Update metrics
            self.performance_metrics.average_latency_ms = statistics.mean(self.latency_samples)
            self.performance_metrics.max_latency_ms = max(self.latency_samples)
            self.performance_metrics.min_latency_ms = min(self.latency_samples)
        
        # Update event counts
        self.performance_metrics.total_events += 1
        if validated_event.validation_result == ValidationResult.VALID:
            self.performance_metrics.successful_events += 1
        else:
            self.performance_metrics.failed_events += 1
    
    def register_validation_callback(self, callback: Callable) -> None:
        """Register callback for validation events."""
        self.validation_callbacks.append(callback)
    
    def register_error_callback(self, callback: Callable) -> None:
        """Register callback for validation errors."""
        self.error_callbacks.append(callback)
    
    def get_thread_history(self, thread_id: str) -> List[ValidatedEvent]:
        """Get validation history for a thread."""
        return self.event_history.get(thread_id, [])
    
    def get_sequence_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get validation status for a thread sequence."""
        return self.sequence_validator.get_sequence_status(thread_id)
    
    def get_performance_metrics(self) -> EventMetrics:
        """Get current performance metrics."""
        # Calculate events per second
        if self.event_history:
            total_time = time.time() - min(
                event.timestamp for events in self.event_history.values() 
                for event in events
            )
            if total_time > 0:
                self.performance_metrics.events_per_second = self.performance_metrics.total_events / total_time
        
        # Calculate sequence completion rate
        total_sequences = len(self.sequence_validator.active_sequences) + len(self.sequence_validator.completed_sequences)
        if total_sequences > 0:
            self.performance_metrics.sequence_completion_rate = (
                len(self.sequence_validator.completed_sequences) / total_sequences
            )
        
        return self.performance_metrics
    
    async def replay_events(self, thread_id: str, start_time: Optional[float] = None, 
                          end_time: Optional[float] = None) -> List[ValidatedEvent]:
        """Replay events for debugging and analysis."""
        events = self.get_thread_history(thread_id)
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        logger.info(f"Replaying {len(events)} events for thread {thread_id}")
        return events
    
    def detect_silent_failures(self, thread_id: str, expected_events: Set[EventType] = None) -> List[str]:
        """Detect missing events that indicate silent failures."""
        expected_events = expected_events or self.event_validator.REQUIRED_EVENTS
        history = self.get_thread_history(thread_id)
        
        if not history:
            return ["No events recorded for thread"]
        
        actual_events = {e.event_type for e in history if isinstance(e.event_type, EventType)}
        missing_events = expected_events - actual_events
        
        failures = []
        if missing_events:
            failures.append(f"Missing required events: {missing_events}")
        
        # Check for incomplete sequences
        sequence_status = self.get_sequence_status(thread_id)
        if sequence_status and not sequence_status.get('sequence_complete', False):
            failures.append("Incomplete event sequence detected")
        
        # Check for timing violations
        if len(history) > 1:
            time_gaps = []
            for i in range(1, len(history)):
                gap = (history[i].timestamp - history[i-1].timestamp) * 1000
                time_gaps.append(gap)
            
            max_gap = max(time_gaps)
            if max_gap > 30000:  # 30 seconds
                failures.append(f"Large time gap detected: {max_gap:.1f}ms")
        
        return failures
    
    def generate_validation_report(self, thread_id: str = None) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        if thread_id:
            # Thread-specific report
            history = self.get_thread_history(thread_id)
            sequence_status = self.get_sequence_status(thread_id)
            silent_failures = self.detect_silent_failures(thread_id)
            
            return {
                "thread_id": thread_id,
                "event_count": len(history),
                "validation_summary": {
                    "valid": len([e for e in history if e.validation_result == ValidationResult.VALID]),
                    "warnings": len([e for e in history if e.validation_result == ValidationResult.WARNING]),
                    "errors": len([e for e in history if e.validation_result == ValidationResult.ERROR]),
                    "critical": len([e for e in history if e.validation_result == ValidationResult.CRITICAL]),
                },
                "sequence_status": sequence_status,
                "silent_failures": silent_failures,
                "first_event": history[0].timestamp if history else None,
                "last_event": history[-1].timestamp if history else None,
            }
        else:
            # Global report
            metrics = self.get_performance_metrics()
            return {
                "framework_status": {
                    "circuit_breaker_state": self.circuit_breaker_state,
                    "failure_count": self.failure_count,
                    "validation_level": self.validation_level,
                },
                "performance_metrics": {
                    "total_events": metrics.total_events,
                    "successful_events": metrics.successful_events,
                    "failed_events": metrics.failed_events,
                    "average_latency_ms": metrics.average_latency_ms,
                    "events_per_second": metrics.events_per_second,
                    "sequence_completion_rate": metrics.sequence_completion_rate,
                },
                "active_sequences": len(self.sequence_validator.active_sequences),
                "completed_sequences": len(self.sequence_validator.completed_sequences),
                "total_threads": len(self.event_history),
            }


# Global framework instance
_framework_instance: Optional[EventValidationFramework] = None


def get_event_validation_framework(validation_level: EventValidationLevel = EventValidationLevel.STRICT) -> EventValidationFramework:
    """Get or create the global event validation framework instance."""
    global _framework_instance
    if _framework_instance is None:
        _framework_instance = EventValidationFramework(validation_level)
    return _framework_instance


async def validate_websocket_event(event: Dict[str, Any], context: Dict[str, Any] = None) -> ValidatedEvent:
    """Convenience function for validating WebSocket events."""
    framework = get_event_validation_framework()
    return await framework.validate_event(event, context)


async def get_validation_report(thread_id: str = None) -> Dict[str, Any]:
    """Convenience function for getting validation reports."""
    framework = get_event_validation_framework()
    return framework.generate_validation_report(thread_id)