#!/usr/bin/env python
"""
Event Sequence Validator - MISSION CRITICAL for Business Value

Business Value Justification:
- Segment: Platform/Internal - Chat infrastructure validation  
- Business Goal: Ensure WebSocket events deliver substantive chat value in correct sequence
- Value Impact: Validates event ordering that enables user trust and engagement
- Revenue Impact: Protects chat functionality sequence that generates customer conversions

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- WebSocket events enable substantive chat interactions - they serve business goal
- Tests must FAIL HARD when business value is compromised
- Event sequence MUST be correct for user engagement and trust
- Real WebSocket connections and services (no mocks)

THE 5 CRITICAL WEBSOCKET EVENTS FOR BUSINESS VALUE (in correct order):
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)  
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance SPEC/core.xml - Event sequence critical for business value delivery
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.websocket_core.types import MessageType
from test_framework.ssot.real_websocket_test_client import WebSocketEvent

logger = logging.getLogger(__name__)


class EventSequenceState(str, Enum):
    """States for event sequence validation."""
    NOT_STARTED = "not_started"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class BusinessValueImpact(str, Enum):
    """Business value impact levels for sequence violations."""
    CRITICAL = "critical"      # Revenue impact, user abandonment
    HIGH = "high"             # User confusion, reduced trust
    MEDIUM = "medium"         # Minor UX degradation
    LOW = "low"              # Technical issue, no user impact


@dataclass
class EventSequenceRule:
    """Defines a rule for event sequence validation."""
    name: str
    event_types: List[str]
    required_order: bool = True
    max_gap_seconds: Optional[float] = None
    business_impact: BusinessValueImpact = BusinessValueImpact.HIGH
    description: str = ""


@dataclass
class EventSequenceViolation:
    """Represents a violation of event sequence rules."""
    rule_name: str
    violation_type: str
    expected_event: str
    actual_event: str
    expected_position: int
    actual_position: int
    timestamp: float
    business_impact: BusinessValueImpact
    user_facing: bool = True
    description: str = ""


@dataclass
class EventSequenceResult:
    """Result of event sequence validation."""
    sequence_name: str
    state: EventSequenceState
    total_events: int
    violations: List[EventSequenceViolation] = field(default_factory=list)
    completion_time: Optional[float] = None
    business_value_preserved: bool = True
    user_engagement_risk: float = 0.0  # 0.0 = no risk, 1.0 = complete failure


class EventSequenceValidator:
    """
    MISSION CRITICAL: Event Sequence Validator for Business Value Protection
    
    This validator ensures WebSocket events occur in the correct sequence required
    for delivering substantive chat value and maintaining user engagement.
    
    CRITICAL FEATURES:
    - Validates the 5 critical events occur in correct order
    - Measures timing gaps between events
    - Calculates business value impact of violations
    - Fails hard when user engagement is at risk
    - Real-time validation during event streams
    """
    
    # CRITICAL: Business-value sequence rules
    CRITICAL_BUSINESS_SEQUENCES = [
        EventSequenceRule(
            name="agent_execution_flow",
            event_types=["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
            required_order=True,
            max_gap_seconds=30.0,  # Max 30s between critical events
            business_impact=BusinessValueImpact.CRITICAL,
            description="Core agent execution flow that delivers AI value to users"
        ),
        EventSequenceRule(
            name="user_feedback_loop", 
            event_types=["agent_started", "agent_thinking", "agent_completed"],
            required_order=True,
            max_gap_seconds=60.0,  # Allow longer for simple flows
            business_impact=BusinessValueImpact.HIGH,
            description="Minimum feedback loop to maintain user engagement"
        ),
        EventSequenceRule(
            name="tool_execution_cycle",
            event_types=["tool_executing", "tool_completed"],
            required_order=True,
            max_gap_seconds=20.0,  # Tools should complete quickly
            business_impact=BusinessValueImpact.MEDIUM,
            description="Tool execution transparency for user trust"
        )
    ]
    
    def __init__(self, user_id: str, session_id: str, timeout_seconds: float = 120.0):
        """Initialize event sequence validator.
        
        Args:
            user_id: User ID for this validation session
            session_id: Session ID for tracking
            timeout_seconds: Maximum time to wait for sequence completion
        """
        self.user_id = user_id
        self.session_id = session_id
        self.timeout_seconds = timeout_seconds
        
        # Event tracking
        self.received_events: List[Tuple[float, WebSocketEvent]] = []
        self.sequence_states: Dict[str, EventSequenceState] = {}
        self.sequence_results: Dict[str, EventSequenceResult] = {}
        
        # Initialize sequence tracking
        for rule in self.CRITICAL_BUSINESS_SEQUENCES:
            self.sequence_states[rule.name] = EventSequenceState.NOT_STARTED
            self.sequence_results[rule.name] = EventSequenceResult(
                sequence_name=rule.name,
                state=EventSequenceState.NOT_STARTED,
                total_events=0
            )
        
        # Metrics
        self.validation_start_time = time.time()
        self.first_event_time: Optional[float] = None
        self.last_event_time: Optional[float] = None
        
        logger.info(f"EventSequenceValidator initialized for user {user_id}, session {session_id}")
    
    def add_event(self, event: WebSocketEvent) -> List[EventSequenceViolation]:
        """Add an event and validate sequence rules.
        
        Args:
            event: WebSocket event to validate
            
        Returns:
            List of sequence violations detected
        """
        event_time = time.time()
        self.received_events.append((event_time, event))
        
        if self.first_event_time is None:
            self.first_event_time = event_time
        self.last_event_time = event_time
        
        violations = []
        
        # Validate against each sequence rule
        for rule in self.CRITICAL_BUSINESS_SEQUENCES:
            rule_violations = self._validate_event_against_rule(event, event_time, rule)
            violations.extend(rule_violations)
            
            # Add violations to sequence result
            result = self.sequence_results[rule.name]
            result.violations.extend(rule_violations)
            
            # Update sequence state
            self._update_sequence_state(rule, event, event_time)
        
        # Log violations immediately for mission-critical visibility
        for violation in violations:
            if violation.business_impact in [BusinessValueImpact.CRITICAL, BusinessValueImpact.HIGH]:
                logger.error(f"🚨 BUSINESS VALUE VIOLATION: {violation.description}")
            else:
                logger.warning(f"⚠️ Sequence violation: {violation.description}")
        
        return violations
    
    def _validate_event_against_rule(
        self, 
        event: WebSocketEvent, 
        event_time: float, 
        rule: EventSequenceRule
    ) -> List[EventSequenceViolation]:
        """Validate a single event against a sequence rule."""
        violations = []
        
        if event.event_type not in rule.event_types:
            return violations  # Event not relevant to this rule
        
        # Get current sequence for this rule
        rule_events = [
            (t, e) for t, e in self.received_events 
            if e.event_type in rule.event_types
        ]
        
        if not rule_events:
            return violations  # No events yet for this rule
        
        current_position = len(rule_events) - 1
        expected_position = rule.event_types.index(event.event_type)
        
        # Check order requirement
        if rule.required_order:
            # Find the position of this event type in the expected sequence
            if current_position != expected_position:
                # Check if we're getting events out of order
                actual_sequence = [e.event_type for _, e in rule_events]
                expected_sequence = rule.event_types[:len(actual_sequence)]
                
                if actual_sequence != expected_sequence:
                    violation = EventSequenceViolation(
                        rule_name=rule.name,
                        violation_type="out_of_order",
                        expected_event=expected_sequence[current_position] if current_position < len(expected_sequence) else "unknown",
                        actual_event=event.event_type,
                        expected_position=expected_position,
                        actual_position=current_position,
                        timestamp=event_time,
                        business_impact=rule.business_impact,
                        description=f"Event '{event.event_type}' received out of order in {rule.name}"
                    )
                    violations.append(violation)
        
        # Check timing gaps
        if rule.max_gap_seconds and len(rule_events) > 1:
            previous_time = rule_events[-2][0]
            gap = event_time - previous_time
            
            if gap > rule.max_gap_seconds:
                violation = EventSequenceViolation(
                    rule_name=rule.name,
                    violation_type="timing_gap",
                    expected_event=f"within {rule.max_gap_seconds}s",
                    actual_event=f"after {gap:.1f}s",
                    expected_position=current_position,
                    actual_position=current_position,
                    timestamp=event_time,
                    business_impact=rule.business_impact,
                    description=f"Gap of {gap:.1f}s exceeds maximum {rule.max_gap_seconds}s for {rule.name}"
                )
                violations.append(violation)
        
        return violations
    
    def _update_sequence_state(self, rule: EventSequenceRule, event: WebSocketEvent, event_time: float):
        """Update the state of a sequence based on received event."""
        result = self.sequence_results[rule.name]
        result.total_events += 1
        
        # Determine new state
        if rule.event_types[0] == event.event_type:
            # First event in sequence
            self.sequence_states[rule.name] = EventSequenceState.STARTED
            result.state = EventSequenceState.STARTED
        elif rule.event_types[-1] == event.event_type:
            # Last event in sequence
            self.sequence_states[rule.name] = EventSequenceState.COMPLETED
            result.state = EventSequenceState.COMPLETED
            result.completion_time = event_time - self.validation_start_time
        else:
            # Middle events
            self.sequence_states[rule.name] = EventSequenceState.IN_PROGRESS
            result.state = EventSequenceState.IN_PROGRESS
    
    def validate_complete_sequences(self) -> Dict[str, EventSequenceResult]:
        """Validate all sequences and return results.
        
        Returns:
            Dictionary mapping sequence names to validation results
        """
        current_time = time.time()
        
        for rule in self.CRITICAL_BUSINESS_SEQUENCES:
            result = self.sequence_results[rule.name]
            
            # Check for timeout
            if (current_time - self.validation_start_time) > self.timeout_seconds:
                if result.state not in [EventSequenceState.COMPLETED, EventSequenceState.FAILED]:
                    result.state = EventSequenceState.TIMEOUT
                    self.sequence_states[rule.name] = EventSequenceState.TIMEOUT
            
            # Calculate business value impact
            result.business_value_preserved, result.user_engagement_risk = self._calculate_business_impact(rule, result)
        
        return self.sequence_results.copy()
    
    def _calculate_business_impact(self, rule: EventSequenceRule, result: EventSequenceResult) -> Tuple[bool, float]:
        """Calculate business value impact and user engagement risk.
        
        Returns:
            Tuple of (business_value_preserved, user_engagement_risk)
        """
        # Base risk on sequence completion
        if result.state == EventSequenceState.COMPLETED:
            base_risk = 0.0
        elif result.state == EventSequenceState.IN_PROGRESS:
            base_risk = 0.3
        elif result.state == EventSequenceState.TIMEOUT:
            base_risk = 0.8
        else:
            base_risk = 1.0
        
        # Increase risk based on violations
        violation_risk = 0.0
        for violation in result.violations:
            if violation.business_impact == BusinessValueImpact.CRITICAL:
                violation_risk += 0.5
            elif violation.business_impact == BusinessValueImpact.HIGH:
                violation_risk += 0.3
            elif violation.business_impact == BusinessValueImpact.MEDIUM:
                violation_risk += 0.1
            else:
                violation_risk += 0.05
        
        total_risk = min(1.0, base_risk + violation_risk)
        business_value_preserved = total_risk < 0.5  # Threshold for business value
        
        return business_value_preserved, total_risk
    
    def assert_business_value_preserved(self, max_risk_threshold: float = 0.5) -> None:
        """Assert that business value is preserved across all sequences.
        
        Args:
            max_risk_threshold: Maximum acceptable user engagement risk (0.0-1.0)
            
        Raises:
            AssertionError: If business value is compromised
        """
        results = self.validate_complete_sequences()
        
        critical_failures = []
        high_risk_sequences = []
        
        for sequence_name, result in results.items():
            if not result.business_value_preserved:
                critical_failures.append(f"{sequence_name}: Business value NOT preserved")
            
            if result.user_engagement_risk > max_risk_threshold:
                high_risk_sequences.append(
                    f"{sequence_name}: Risk {result.user_engagement_risk:.1%} > {max_risk_threshold:.1%}"
                )
        
        if critical_failures or high_risk_sequences:
            failure_details = []
            
            if critical_failures:
                failure_details.append("CRITICAL BUSINESS VALUE FAILURES:")
                failure_details.extend(critical_failures)
            
            if high_risk_sequences:
                failure_details.append("HIGH USER ENGAGEMENT RISK:")
                failure_details.extend(high_risk_sequences)
            
            error_message = (
                "🚨 BUSINESS VALUE COMPROMISED - WebSocket event sequences failed!\n"
                + "\n".join(failure_details) + "\n\n"
                "This indicates chat functionality will not deliver substantive AI value to users."
            )
            
            logger.error(error_message)
            raise AssertionError(error_message)
    
    def assert_critical_events_received(self) -> None:
        """Assert that all critical business events were received.
        
        Raises:
            AssertionError: If critical events are missing
        """
        critical_event_types = {"agent_started", "agent_completed"}
        received_event_types = {event.event_type for _, event in self.received_events}
        
        missing_events = critical_event_types - received_event_types
        
        if missing_events:
            error_message = (
                f"🚨 CRITICAL EVENTS MISSING: {missing_events}\n"
                f"Received: {received_event_types}\n"
                "Users cannot see AI value delivery without these events!"
            )
            logger.error(error_message)
            raise AssertionError(error_message)
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get comprehensive validation summary.
        
        Returns:
            Dictionary with validation metrics and results
        """
        results = self.validate_complete_sequences()
        
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "validation_duration": time.time() - self.validation_start_time,
            "total_events_received": len(self.received_events),
            "sequence_results": {
                name: {
                    "state": result.state.value,
                    "total_events": result.total_events,
                    "violations": len(result.violations),
                    "completion_time": result.completion_time,
                    "business_value_preserved": result.business_value_preserved,
                    "user_engagement_risk": result.user_engagement_risk
                }
                for name, result in results.items()
            },
            "critical_violations": [
                {
                    "rule": v.rule_name,
                    "type": v.violation_type,
                    "impact": v.business_impact.value,
                    "description": v.description
                }
                for result in results.values()
                for v in result.violations
                if v.business_impact in [BusinessValueImpact.CRITICAL, BusinessValueImpact.HIGH]
            ]
        }


# Convenience functions for common patterns

def validate_agent_execution_sequence(events: List[WebSocketEvent], user_id: str = "test_user") -> EventSequenceValidator:
    """Validate a complete agent execution event sequence.
    
    Args:
        events: List of WebSocket events to validate
        user_id: User ID for validation context
        
    Returns:
        EventSequenceValidator with results
    """
    validator = EventSequenceValidator(user_id=user_id, session_id=f"validation_{int(time.time())}")
    
    for event in events:
        validator.add_event(event)
    
    # Assert business value is preserved
    validator.assert_business_value_preserved()
    validator.assert_critical_events_received()
    
    return validator


def create_test_event_sequence() -> List[WebSocketEvent]:
    """Create a test sequence of WebSocket events for validation testing.
    
    Returns:
        List of properly sequenced WebSocket events
    """
    base_data = {
        "user_id": "test_user",
        "session_id": "test_session",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    events = [
        WebSocketEvent(event_type="agent_started", data={"agent_id": "test_agent", **base_data}),
        WebSocketEvent(event_type="agent_thinking", data={"content": "Processing request...", **base_data}),
        WebSocketEvent(event_type="tool_executing", data={"tool_name": "web_search", **base_data}),
        WebSocketEvent(event_type="tool_completed", data={"tool_name": "web_search", "result": {"status": "success"}, **base_data}),
        WebSocketEvent(event_type="agent_completed", data={"result": {"status": "completed"}, **base_data})
    ]
    
    return events