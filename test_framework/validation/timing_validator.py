#!/usr/bin/env python
"""
Timing Validator - MISSION CRITICAL for Business Value

Business Value Justification:
- Segment: Platform/Internal - Chat performance validation  
- Business Goal: Ensure WebSocket events deliver value within acceptable timeframes
- Value Impact: Validates response timing that maintains user engagement and prevents abandonment
- Revenue Impact: Protects against slow responses that drive users to competitors

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- WebSocket events must deliver business value within user attention spans
- Tests must FAIL HARD when timing compromises user engagement
- Event timing MUST meet performance standards that preserve user trust
- Real WebSocket connections with actual timing measurement

BUSINESS VALUE TIMING REQUIREMENTS:
- agent_started: Must appear within 2s of user request (immediate feedback)
- agent_thinking: Must update every 5-10s (maintain engagement) 
- tool_executing: Must start within 5s of thinking (show progress)
- tool_completed: Must complete within 30s (avoid abandonment)
- agent_completed: Must deliver final value within 60s total

@compliance CLAUDE.md - Event timing critical for user engagement
@compliance SPEC/core.xml - Performance standards protect business value
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics

from test_framework.ssot.real_websocket_test_client import WebSocketEvent

logger = logging.getLogger(__name__)


class TimingCriticality(str, Enum):
    """Criticality levels for timing requirements."""
    CRITICAL = "critical"      # Direct revenue impact, user abandonment risk
    HIGH = "high"             # User frustration, reduced satisfaction  
    MEDIUM = "medium"         # Minor UX degradation
    LOW = "low"              # Technical optimization only


class TimingViolationType(str, Enum):
    """Types of timing violations."""
    INITIAL_DELAY = "initial_delay"           # Too long before first event
    RESPONSE_TIMEOUT = "response_timeout"     # Event took too long to arrive
    UPDATE_GAP = "update_gap"                 # Too long between updates
    SEQUENCE_TIMEOUT = "sequence_timeout"     # Overall sequence too slow
    EXCESSIVE_LATENCY = "excessive_latency"   # Individual event latency too high
    ABANDONMENT_RISK = "abandonment_risk"     # Timing likely to cause user exit


@dataclass
class TimingRequirement:
    """Defines timing requirements for events."""
    event_type: str
    max_initial_delay_ms: Optional[float] = None    # Max time for first occurrence
    max_response_time_ms: Optional[float] = None    # Max time for event processing
    max_update_gap_ms: Optional[float] = None       # Max time between recurring events
    min_frequency_ms: Optional[float] = None        # Min time between occurrences
    criticality: TimingCriticality = TimingCriticality.MEDIUM
    business_context: str = ""


@dataclass
class TimingViolation:
    """Represents a timing violation."""
    event_type: str
    violation_type: TimingViolationType
    expected_ms: float
    actual_ms: float
    criticality: TimingCriticality
    timestamp: float
    business_impact: str
    user_abandonment_risk: float = 0.0  # 0.0-1.0, higher means more likely to abandon
    description: str = ""


@dataclass
class EventTiming:
    """Timing data for a specific event."""
    event_type: str
    timestamp: float
    processing_time_ms: Optional[float] = None
    latency_ms: Optional[float] = None
    gap_from_previous_ms: Optional[float] = None


@dataclass
class TimingValidationResult:
    """Result of timing validation."""
    session_id: str
    total_events: int
    total_duration_ms: float
    violations: List[TimingViolation] = field(default_factory=list)
    performance_score: float = 1.0  # 0.0-1.0, higher is better
    user_engagement_preserved: bool = True
    abandonment_risk_score: float = 0.0  # 0.0-1.0, higher means more likely to abandon


class TimingValidator:
    """
    MISSION CRITICAL: Timing Validator for Business Value Protection
    
    This validator ensures WebSocket events are delivered within timeframes that
    preserve user engagement, prevent abandonment, and maintain business value.
    
    CRITICAL FEATURES:
    - Validates event timing against business requirements
    - Measures user engagement preservation through timing
    - Calculates abandonment risk based on response delays
    - Tracks performance degradation over sessions
    - Fails hard when timing compromises business value
    """
    
    # CRITICAL: Business-value timing requirements
    BUSINESS_TIMING_REQUIREMENTS = [
        TimingRequirement(
            event_type="agent_started",
            max_initial_delay_ms=2000.0,     # 2s max - users need immediate feedback
            max_response_time_ms=1000.0,     # 1s processing time
            criticality=TimingCriticality.CRITICAL,
            business_context="Immediate feedback prevents user confusion and abandonment"
        ),
        TimingRequirement(
            event_type="agent_thinking", 
            max_initial_delay_ms=3000.0,     # 3s after agent_started
            max_update_gap_ms=8000.0,        # 8s max between thinking updates
            max_response_time_ms=2000.0,     # 2s processing
            criticality=TimingCriticality.HIGH,
            business_context="Regular updates maintain engagement during processing"
        ),
        TimingRequirement(
            event_type="tool_executing",
            max_initial_delay_ms=5000.0,     # 5s after thinking starts
            max_response_time_ms=2000.0,     # 2s to start execution
            criticality=TimingCriticality.HIGH,
            business_context="Shows progress and AI capability to maintain trust"
        ),
        TimingRequirement(
            event_type="tool_completed",
            max_response_time_ms=30000.0,    # 30s max for tool completion
            criticality=TimingCriticality.HIGH,
            business_context="Tool results must arrive before user loses interest"
        ),
        TimingRequirement(
            event_type="agent_completed",
            max_initial_delay_ms=60000.0,    # 60s total for complete response
            max_response_time_ms=5000.0,     # 5s to finalize response
            criticality=TimingCriticality.CRITICAL,
            business_context="Final results must deliver value within user attention span"
        )
    ]
    
    # User abandonment risk thresholds (based on research)
    ABANDONMENT_RISK_THRESHOLDS = {
        0: 0.05,      # 0-5s: Very low risk
        5: 0.15,      # 5-10s: Low risk
        10: 0.30,     # 10-20s: Medium risk  
        20: 0.60,     # 20-40s: High risk
        40: 0.85,     # 40s+: Very high risk
        60: 0.95      # 60s+: Almost certain abandonment
    }
    
    def __init__(self, user_id: str, session_id: str, session_start_time: Optional[float] = None):
        """Initialize timing validator.
        
        Args:
            user_id: User ID for validation context
            session_id: Session ID for tracking  
            session_start_time: When the session started (defaults to now)
        """
        self.user_id = user_id
        self.session_id = session_id
        self.session_start_time = session_start_time or time.time()
        
        # Event tracking
        self.event_timings: List[EventTiming] = []
        self.first_event_time: Optional[float] = None
        self.last_event_time: Optional[float] = None
        self.event_type_timings: Dict[str, List[EventTiming]] = {}
        
        # Violation tracking
        self.violations: List[TimingViolation] = []
        self.critical_violations = 0
        self.abandonment_risk_events = 0
        
        logger.info(f"TimingValidator initialized for user {user_id}, session {session_id}")
    
    def record_event(self, event: WebSocketEvent, processing_start_time: Optional[float] = None) -> List[TimingViolation]:
        """Record an event and validate its timing.
        
        Args:
            event: WebSocket event to record
            processing_start_time: When processing started (for latency calculation)
            
        Returns:
            List of timing violations detected
        """
        current_time = time.time()
        
        # Calculate processing time and latency
        processing_time_ms = None
        if processing_start_time:
            processing_time_ms = (current_time - processing_start_time) * 1000
        
        latency_ms = None
        if hasattr(event, 'timestamp') and event.timestamp:
            try:
                if isinstance(event.timestamp, (int, float)):
                    event_time = event.timestamp
                else:
                    event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')).timestamp()
                latency_ms = (current_time - event_time) * 1000
            except (ValueError, AttributeError):
                pass
        
        # Calculate gap from previous event
        gap_from_previous_ms = None
        if self.last_event_time:
            gap_from_previous_ms = (current_time - self.last_event_time) * 1000
        
        # Record timing
        timing = EventTiming(
            event_type=event.event_type,
            timestamp=current_time,
            processing_time_ms=processing_time_ms,
            latency_ms=latency_ms,
            gap_from_previous_ms=gap_from_previous_ms
        )
        
        self.event_timings.append(timing)
        
        if event.event_type not in self.event_type_timings:
            self.event_type_timings[event.event_type] = []
        self.event_type_timings[event.event_type].append(timing)
        
        # Track first/last event times
        if self.first_event_time is None:
            self.first_event_time = current_time
        self.last_event_time = current_time
        
        # Validate timing requirements
        violations = self._validate_event_timing(timing)
        self.violations.extend(violations)
        
        # Count critical violations
        for violation in violations:
            if violation.criticality == TimingCriticality.CRITICAL:
                self.critical_violations += 1
            if violation.user_abandonment_risk > 0.7:
                self.abandonment_risk_events += 1
        
        # Log critical violations immediately
        for violation in violations:
            if violation.criticality == TimingCriticality.CRITICAL:
                logger.error(f"🚨 CRITICAL TIMING VIOLATION: {violation.description}")
            elif violation.user_abandonment_risk > 0.6:
                logger.warning(f"⚠️ HIGH ABANDONMENT RISK: {violation.description}")
        
        return violations
    
    def _validate_event_timing(self, timing: EventTiming) -> List[TimingViolation]:
        """Validate timing for a single event."""
        violations = []
        
        # Find timing requirements for this event type
        requirements = [req for req in self.BUSINESS_TIMING_REQUIREMENTS if req.event_type == timing.event_type]
        
        for requirement in requirements:
            violations.extend(self._check_timing_requirement(timing, requirement))
        
        # Universal timing checks
        violations.extend(self._check_universal_timing_rules(timing))
        
        return violations
    
    def _check_timing_requirement(self, timing: EventTiming, requirement: TimingRequirement) -> List[TimingViolation]:
        """Check a specific timing requirement."""
        violations = []
        
        # Check initial delay (time from session start to first occurrence)
        if requirement.max_initial_delay_ms and len(self.event_type_timings[timing.event_type]) == 1:
            initial_delay_ms = (timing.timestamp - self.session_start_time) * 1000
            if initial_delay_ms > requirement.max_initial_delay_ms:
                abandonment_risk = self._calculate_abandonment_risk(initial_delay_ms / 1000)
                violations.append(TimingViolation(
                    event_type=timing.event_type,
                    violation_type=TimingViolationType.INITIAL_DELAY,
                    expected_ms=requirement.max_initial_delay_ms,
                    actual_ms=initial_delay_ms,
                    criticality=requirement.criticality,
                    timestamp=timing.timestamp,
                    business_impact=f"Initial delay of {initial_delay_ms:.0f}ms may cause user confusion/abandonment",
                    user_abandonment_risk=abandonment_risk,
                    description=f"{timing.event_type} took {initial_delay_ms:.0f}ms to appear (max: {requirement.max_initial_delay_ms:.0f}ms)"
                ))
        
        # Check response time (processing time)
        if requirement.max_response_time_ms and timing.processing_time_ms:
            if timing.processing_time_ms > requirement.max_response_time_ms:
                violations.append(TimingViolation(
                    event_type=timing.event_type,
                    violation_type=TimingViolationType.RESPONSE_TIMEOUT,
                    expected_ms=requirement.max_response_time_ms,
                    actual_ms=timing.processing_time_ms,
                    criticality=requirement.criticality,
                    timestamp=timing.timestamp,
                    business_impact=f"Slow processing reduces perceived AI performance",
                    user_abandonment_risk=self._calculate_abandonment_risk(timing.processing_time_ms / 1000),
                    description=f"{timing.event_type} processing took {timing.processing_time_ms:.0f}ms (max: {requirement.max_response_time_ms:.0f}ms)"
                ))
        
        # Check update gap (time between recurring events of same type)
        if requirement.max_update_gap_ms and timing.gap_from_previous_ms:
            previous_same_type = [t for t in reversed(self.event_type_timings[timing.event_type][:-1])]
            if previous_same_type:
                gap_ms = (timing.timestamp - previous_same_type[0].timestamp) * 1000
                if gap_ms > requirement.max_update_gap_ms:
                    abandonment_risk = self._calculate_abandonment_risk(gap_ms / 1000)
                    violations.append(TimingViolation(
                        event_type=timing.event_type,
                        violation_type=TimingViolationType.UPDATE_GAP,
                        expected_ms=requirement.max_update_gap_ms,
                        actual_ms=gap_ms,
                        criticality=requirement.criticality,
                        timestamp=timing.timestamp,
                        business_impact="Long gaps between updates reduce engagement",
                        user_abandonment_risk=abandonment_risk,
                        description=f"{timing.event_type} gap of {gap_ms:.0f}ms exceeds max {requirement.max_update_gap_ms:.0f}ms"
                    ))
        
        return violations
    
    def _check_universal_timing_rules(self, timing: EventTiming) -> List[TimingViolation]:
        """Check universal timing rules that apply to all events."""
        violations = []
        
        # Check excessive latency (network/processing delays)
        if timing.latency_ms and timing.latency_ms > 5000:  # 5s latency is unacceptable
            violations.append(TimingViolation(
                event_type=timing.event_type,
                violation_type=TimingViolationType.EXCESSIVE_LATENCY,
                expected_ms=5000.0,
                actual_ms=timing.latency_ms,
                criticality=TimingCriticality.HIGH,
                timestamp=timing.timestamp,
                business_impact="High latency makes system feel unresponsive",
                user_abandonment_risk=self._calculate_abandonment_risk(timing.latency_ms / 1000),
                description=f"{timing.event_type} latency {timing.latency_ms:.0f}ms exceeds acceptable 5000ms"
            ))
        
        # Check total session duration for abandonment risk
        session_duration_s = timing.timestamp - self.session_start_time
        if session_duration_s > 90:  # 90s+ sessions have high abandonment risk
            violations.append(TimingViolation(
                event_type=timing.event_type,
                violation_type=TimingViolationType.ABANDONMENT_RISK,
                expected_ms=90000.0,
                actual_ms=session_duration_s * 1000,
                criticality=TimingCriticality.CRITICAL,
                timestamp=timing.timestamp,
                business_impact="Extended session duration increases abandonment risk",
                user_abandonment_risk=0.8,
                description=f"Session duration {session_duration_s:.0f}s approaches user attention limit"
            ))
        
        return violations
    
    def _calculate_abandonment_risk(self, delay_seconds: float) -> float:
        """Calculate user abandonment risk based on delay.
        
        Args:
            delay_seconds: Delay in seconds
            
        Returns:
            Abandonment risk score (0.0-1.0)
        """
        # Find the appropriate threshold
        for threshold_s, risk in sorted(self.ABANDONMENT_RISK_THRESHOLDS.items()):
            if delay_seconds <= threshold_s:
                return risk
        
        # If delay exceeds all thresholds, return maximum risk
        return 0.95
    
    def validate_overall_timing(self) -> TimingValidationResult:
        """Validate overall timing performance for the session.
        
        Returns:
            TimingValidationResult with comprehensive timing analysis
        """
        if not self.event_timings:
            return TimingValidationResult(
                session_id=self.session_id,
                total_events=0,
                total_duration_ms=0.0,
                performance_score=0.0,
                user_engagement_preserved=False,
                abandonment_risk_score=1.0
            )
        
        total_duration_ms = (self.last_event_time - self.session_start_time) * 1000
        
        # Calculate performance score based on violations
        performance_score = 1.0
        for violation in self.violations:
            if violation.criticality == TimingCriticality.CRITICAL:
                performance_score -= 0.3
            elif violation.criticality == TimingCriticality.HIGH:
                performance_score -= 0.2
            elif violation.criticality == TimingCriticality.MEDIUM:
                performance_score -= 0.1
            else:
                performance_score -= 0.05
        
        performance_score = max(0.0, performance_score)
        
        # Calculate overall abandonment risk
        if self.violations:
            abandonment_risks = [v.user_abandonment_risk for v in self.violations if v.user_abandonment_risk > 0]
            abandonment_risk_score = max(abandonment_risks) if abandonment_risks else 0.0
        else:
            abandonment_risk_score = self._calculate_abandonment_risk(total_duration_ms / 1000)
        
        # Determine if user engagement is preserved
        user_engagement_preserved = (
            performance_score >= 0.7 and
            abandonment_risk_score <= 0.3 and
            self.critical_violations == 0
        )
        
        return TimingValidationResult(
            session_id=self.session_id,
            total_events=len(self.event_timings),
            total_duration_ms=total_duration_ms,
            violations=self.violations.copy(),
            performance_score=performance_score,
            user_engagement_preserved=user_engagement_preserved,
            abandonment_risk_score=abandonment_risk_score
        )
    
    def assert_performance_standards_met(self, min_performance_score: float = 0.7, max_abandonment_risk: float = 0.3) -> None:
        """Assert that timing performance meets business standards.
        
        Args:
            min_performance_score: Minimum acceptable performance score (0.0-1.0)
            max_abandonment_risk: Maximum acceptable abandonment risk (0.0-1.0)
            
        Raises:
            AssertionError: If performance standards are not met
        """
        result = self.validate_overall_timing()
        
        failures = []
        critical_issues = []
        
        if result.performance_score < min_performance_score:
            failures.append(f"Performance score {result.performance_score:.2f} < required {min_performance_score:.2f}")
        
        if result.abandonment_risk_score > max_abandonment_risk:
            failures.append(f"Abandonment risk {result.abandonment_risk_score:.2f} > acceptable {max_abandonment_risk:.2f}")
        
        if not result.user_engagement_preserved:
            critical_issues.append("User engagement NOT preserved due to timing issues")
        
        if self.critical_violations > 0:
            critical_issues.append(f"{self.critical_violations} CRITICAL timing violations detected")
        
        if critical_issues or failures:
            error_parts = []
            
            if critical_issues:
                error_parts.append("CRITICAL TIMING ISSUES:")
                error_parts.extend(critical_issues)
            
            if failures:
                error_parts.append("PERFORMANCE FAILURES:")
                error_parts.extend(failures)
            
            # Add top violations for context
            if self.violations:
                worst_violations = sorted(self.violations, key=lambda v: v.user_abandonment_risk, reverse=True)[:3]
                error_parts.append("WORST VIOLATIONS:")
                for v in worst_violations:
                    error_parts.append(f"- {v.description} (abandonment risk: {v.user_abandonment_risk:.1%})")
            
            error_message = (
                "🚨 TIMING PERFORMANCE FAILURE - WebSocket events too slow for business value!\n"
                + "\n".join(error_parts) + "\n\n"
                f"Session duration: {result.total_duration_ms:.0f}ms, Events: {result.total_events}\n"
                "This timing will cause user frustration and abandonment."
            )
            
            logger.error(error_message)
            raise AssertionError(error_message)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive timing performance summary.
        
        Returns:
            Dictionary with timing metrics and analysis
        """
        result = self.validate_overall_timing()
        
        # Calculate per-event-type statistics
        event_type_stats = {}
        for event_type, timings in self.event_type_timings.items():
            if timings:
                processing_times = [t.processing_time_ms for t in timings if t.processing_time_ms]
                gaps = [t.gap_from_previous_ms for t in timings if t.gap_from_previous_ms]
                
                event_type_stats[event_type] = {
                    "count": len(timings),
                    "avg_processing_time_ms": statistics.mean(processing_times) if processing_times else None,
                    "max_processing_time_ms": max(processing_times) if processing_times else None,
                    "avg_gap_ms": statistics.mean(gaps) if gaps else None,
                    "max_gap_ms": max(gaps) if gaps else None
                }
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_duration_ms": result.total_duration_ms,
            "total_events": result.total_events,
            "performance_score": result.performance_score,
            "user_engagement_preserved": result.user_engagement_preserved,
            "abandonment_risk_score": result.abandonment_risk_score,
            "total_violations": len(result.violations),
            "critical_violations": self.critical_violations,
            "abandonment_risk_events": self.abandonment_risk_events,
            "event_type_statistics": event_type_stats,
            "critical_timing_violations": [
                {
                    "event_type": v.event_type,
                    "violation_type": v.violation_type.value,
                    "expected_ms": v.expected_ms,
                    "actual_ms": v.actual_ms,
                    "abandonment_risk": v.user_abandonment_risk,
                    "description": v.description,
                    "business_impact": v.business_impact
                }
                for v in result.violations
                if v.criticality == TimingCriticality.CRITICAL or v.user_abandonment_risk > 0.5
            ]
        }


# Convenience functions

def validate_event_timing_performance(events: List[WebSocketEvent], user_id: str = "test_user") -> TimingValidator:
    """Validate timing performance for a sequence of events.
    
    Args:
        events: List of WebSocket events with timing information
        user_id: User ID for validation context
        
    Returns:
        TimingValidator with results
    """
    session_id = f"timing_validation_{int(time.time())}"
    validator = TimingValidator(user_id=user_id, session_id=session_id)
    
    for event in events:
        validator.record_event(event)
    
    # Assert performance standards are met
    validator.assert_performance_standards_met()
    
    return validator


def create_timing_test_events(delays_ms: List[float]) -> List[WebSocketEvent]:
    """Create test events with specified timing delays for testing.
    
    Args:
        delays_ms: List of delays in milliseconds between events
        
    Returns:
        List of WebSocket events with realistic timing
    """
    events = []
    current_time = time.time()
    
    event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
    
    for i, (event_type, delay_ms) in enumerate(zip(event_types, delays_ms)):
        current_time += delay_ms / 1000.0
        
        event = WebSocketEvent(
            event_type=event_type,
            data={
                "user_id": "test_user",
                "timestamp": datetime.fromtimestamp(current_time, timezone.utc).isoformat(),
                "sequence_number": i
            }
        )
        event.timestamp = current_time
        events.append(event)
    
    return events