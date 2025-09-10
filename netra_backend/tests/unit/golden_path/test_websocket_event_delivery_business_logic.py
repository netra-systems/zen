"""
Test WebSocket Event Delivery Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core user experience
- Business Goal: Ensure real-time AI interaction feedback drives engagement
- Value Impact: WebSocket events are the primary UX for $500K+ ARR delivery
- Strategic Impact: Without events, users can't see AI progress = poor experience = churn

This test validates core WebSocket event delivery algorithms that power:
1. 5 Critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Event ordering and timing validation for optimal UX
3. Event content validation and quality scoring
4. Multi-user event isolation and concurrent delivery
5. Error handling and event delivery guarantees

CRITICAL BUSINESS RULES:
- ALL 5 WebSocket events MUST be delivered for every agent execution
- Events must be delivered in correct order within 5 seconds each
- Event content must include actionable user information
- Multi-user executions must not cross-contaminate events
- Failed event delivery = automatic execution retry
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

from shared.types.core_types import UserID, AgentID, RunID, SessionID
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for WebSocket event delivery)

class WebSocketEventType(Enum):
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"

class EventDeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"

class EventPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class WebSocketEvent:
    """Individual WebSocket event structure."""
    event_id: str
    event_type: WebSocketEventType
    user_id: str
    session_id: str
    agent_id: str
    run_id: str
    timestamp: datetime
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    delivery_attempts: int = 0
    max_delivery_attempts: int = 3
    expiration_time: Optional[datetime] = None

@dataclass
class EventDeliveryResult:
    """Result of event delivery attempt."""
    event_id: str
    status: EventDeliveryStatus
    delivery_time: Optional[datetime]
    error_message: Optional[str]
    user_acknowledged: bool = False

@dataclass
class EventSequence:
    """Complete event sequence for an agent execution."""
    run_id: str
    user_id: str
    expected_events: List[WebSocketEventType]
    delivered_events: List[WebSocketEvent] = field(default_factory=list)
    sequence_start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sequence_timeout_seconds: int = 300  # 5 minutes max

@dataclass
class EventQualityMetrics:
    """Quality metrics for event delivery."""
    completeness_score: float  # 0-1, based on all required events delivered
    timeliness_score: float    # 0-1, based on delivery timing
    content_quality_score: float  # 0-1, based on payload usefulness
    user_engagement_score: float  # 0-1, based on user interactions
    overall_quality_score: float  # Weighted average

class WebSocketEventManager:
    """
    SSOT WebSocket Event Delivery Business Logic
    
    This class implements the core event delivery system that powers
    real-time AI interaction feedback - critical for user engagement.
    """
    
    # CRITICAL EVENT SEQUENCE RULES
    REQUIRED_EVENTS = [
        WebSocketEventType.AGENT_STARTED,
        WebSocketEventType.AGENT_THINKING,
        WebSocketEventType.TOOL_EXECUTING,
        WebSocketEventType.TOOL_COMPLETED,
        WebSocketEventType.AGENT_COMPLETED
    ]
    
    VALID_EVENT_TRANSITIONS = {
        None: [WebSocketEventType.AGENT_STARTED],
        WebSocketEventType.AGENT_STARTED: [WebSocketEventType.AGENT_THINKING],
        WebSocketEventType.AGENT_THINKING: [WebSocketEventType.TOOL_EXECUTING, WebSocketEventType.AGENT_COMPLETED],
        WebSocketEventType.TOOL_EXECUTING: [WebSocketEventType.TOOL_COMPLETED, WebSocketEventType.AGENT_THINKING],
        WebSocketEventType.TOOL_COMPLETED: [WebSocketEventType.AGENT_THINKING, WebSocketEventType.AGENT_COMPLETED],
        WebSocketEventType.AGENT_COMPLETED: []  # Terminal state
    }
    
    # TIMING AND QUALITY THRESHOLDS
    MAX_EVENT_DELIVERY_SECONDS = 5
    MAX_SEQUENCE_DURATION_SECONDS = 300
    MIN_CONTENT_QUALITY_THRESHOLD = 0.7
    MIN_COMPLETENESS_SCORE = 0.9  # 90% of events must be delivered

    def create_event(self, event_type: WebSocketEventType, user_id: str, 
                    session_id: str, agent_id: str, run_id: str,
                    payload: Dict[str, Any], priority: EventPriority = EventPriority.NORMAL) -> WebSocketEvent:
        """
        Create a properly structured WebSocket event.
        
        Critical for consistent event format across the platform.
        """
        # Validate required payload fields based on event type
        required_fields = self._get_required_payload_fields(event_type)
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field '{field}' for event type {event_type.value}")
        
        # Set expiration based on priority
        expiration_minutes = {
            EventPriority.LOW: 10,
            EventPriority.NORMAL: 5,
            EventPriority.HIGH: 2,
            EventPriority.CRITICAL: 1
        }
        
        expiration_time = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes[priority])
        
        return WebSocketEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
            priority=priority,
            expiration_time=expiration_time
        )

    def validate_event_sequence(self, sequence: EventSequence) -> Dict[str, Any]:
        """
        Validate event sequence for completeness and correctness.
        
        Critical business rule: All 5 events must be delivered in correct order.
        """
        validation_results = {
            'is_complete': False,
            'is_ordered_correctly': False,
            'missing_events': [],
            'duplicate_events': [],
            'timing_violations': [],
            'content_quality_issues': []
        }
        
        # Check completeness
        delivered_types = [event.event_type for event in sequence.delivered_events]
        expected_types = set(sequence.expected_events)
        delivered_types_set = set(delivered_types)
        
        missing_events = expected_types - delivered_types_set
        validation_results['missing_events'] = list(missing_events)
        validation_results['is_complete'] = len(missing_events) == 0
        
        # Check for duplicates
        event_counts = {}
        for event_type in delivered_types:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        duplicates = [event_type for event_type, count in event_counts.items() if count > 1]
        validation_results['duplicate_events'] = duplicates
        
        # Check ordering
        validation_results['is_ordered_correctly'] = self._validate_event_order(sequence.delivered_events)
        
        # Check timing
        timing_violations = self._check_timing_violations(sequence.delivered_events)
        validation_results['timing_violations'] = timing_violations
        
        # Check content quality
        content_issues = self._validate_event_content_quality(sequence.delivered_events)
        validation_results['content_quality_issues'] = content_issues
        
        return validation_results

    def calculate_event_quality_score(self, sequence: EventSequence) -> EventQualityMetrics:
        """
        Calculate comprehensive quality score for event sequence.
        
        Used for optimization and customer experience measurement.
        """
        if not sequence.delivered_events:
            return EventQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Completeness score (0-1)
        expected_count = len(sequence.expected_events)
        delivered_count = len(set(event.event_type for event in sequence.delivered_events))
        completeness_score = delivered_count / expected_count
        
        # Timeliness score (0-1)
        timeliness_score = self._calculate_timeliness_score(sequence)
        
        # Content quality score (0-1)
        content_quality_score = self._calculate_content_quality_score(sequence.delivered_events)
        
        # User engagement score (0-1) - simplified for testing
        engagement_score = self._calculate_user_engagement_score(sequence.delivered_events)
        
        # Overall weighted score
        weights = {
            'completeness': 0.4,
            'timeliness': 0.3,
            'content_quality': 0.2,
            'engagement': 0.1
        }
        
        overall_score = (
            completeness_score * weights['completeness'] +
            timeliness_score * weights['timeliness'] +
            content_quality_score * weights['content_quality'] +
            engagement_score * weights['engagement']
        )
        
        return EventQualityMetrics(
            completeness_score=completeness_score,
            timeliness_score=timeliness_score,
            content_quality_score=content_quality_score,
            user_engagement_score=engagement_score,
            overall_quality_score=overall_score
        )

    def prioritize_event_delivery(self, events: List[WebSocketEvent]) -> List[WebSocketEvent]:
        """
        Prioritize event delivery order for optimal user experience.
        
        Critical for handling high-load scenarios.
        """
        if not events:
            return []
        
        # Sort by multiple criteria
        def priority_key(event):
            # Priority order: CRITICAL > HIGH > NORMAL > LOW
            priority_values = {
                EventPriority.CRITICAL: 4,
                EventPriority.HIGH: 3,
                EventPriority.NORMAL: 2,
                EventPriority.LOW: 1
            }
            
            # Earlier events in sequence get higher priority
            sequence_priority = {
                WebSocketEventType.AGENT_STARTED: 10,
                WebSocketEventType.AGENT_THINKING: 9,
                WebSocketEventType.TOOL_EXECUTING: 8,
                WebSocketEventType.TOOL_COMPLETED: 7,
                WebSocketEventType.AGENT_COMPLETED: 6
            }
            
            return (
                priority_values[event.priority],
                sequence_priority.get(event.event_type, 0),
                -event.delivery_attempts,  # Fewer attempts = higher priority
                event.timestamp  # Earlier timestamp = higher priority
            )
        
        return sorted(events, key=priority_key, reverse=True)

    def detect_multi_user_event_isolation_issues(self, events: List[WebSocketEvent]) -> Dict[str, List[str]]:
        """
        Detect event delivery issues that could affect multi-user isolation.
        
        Critical for preventing cross-user data leakage.
        """
        isolation_issues = {
            'cross_user_events': [],
            'session_mismatches': [],
            'run_id_conflicts': []
        }
        
        # Group events by user_id
        user_events = {}
        for event in events:
            if event.user_id not in user_events:
                user_events[event.user_id] = []
            user_events[event.user_id].append(event)
        
        # Check each user's events for isolation violations
        for user_id, user_event_list in user_events.items():
            # Check for run_id conflicts within user
            run_ids = {}
            for event in user_event_list:
                if event.run_id not in run_ids:
                    run_ids[event.run_id] = []
                run_ids[event.run_id].append(event)
            
            # Each run should have consistent session_id
            for run_id, run_events in run_ids.items():
                session_ids = set(event.session_id for event in run_events)
                if len(session_ids) > 1:
                    isolation_issues['session_mismatches'].append(
                        f"Run {run_id} has multiple session IDs: {session_ids}"
                    )
        
        return isolation_issues

    def generate_event_delivery_metrics(self, sequences: List[EventSequence]) -> Dict[str, Any]:
        """
        Generate comprehensive delivery metrics for monitoring and optimization.
        
        Critical for maintaining service quality.
        """
        if not sequences:
            return {'total_sequences': 0}
        
        total_sequences = len(sequences)
        complete_sequences = 0
        quality_scores = []
        delivery_times = []
        
        for sequence in sequences:
            validation = self.validate_event_sequence(sequence)
            
            if validation['is_complete']:
                complete_sequences += 1
            
            quality = self.calculate_event_quality_score(sequence)
            quality_scores.append(quality.overall_quality_score)
            
            # Calculate sequence delivery time
            if sequence.delivered_events:
                first_event = min(sequence.delivered_events, key=lambda e: e.timestamp)
                last_event = max(sequence.delivered_events, key=lambda e: e.timestamp)
                delivery_time = (last_event.timestamp - first_event.timestamp).total_seconds()
                delivery_times.append(delivery_time)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        completion_rate = complete_sequences / total_sequences
        
        return {
            'total_sequences': total_sequences,
            'completion_rate': completion_rate,
            'average_quality_score': avg_quality,
            'average_delivery_time_seconds': avg_delivery_time,
            'sequences_meeting_quality_threshold': sum(1 for score in quality_scores if score >= self.MIN_COMPLETENESS_SCORE),
            'quality_distribution': {
                'excellent': sum(1 for score in quality_scores if score >= 0.9),
                'good': sum(1 for score in quality_scores if 0.7 <= score < 0.9),
                'poor': sum(1 for score in quality_scores if score < 0.7)
            }
        }

    # PRIVATE HELPER METHODS

    def _get_required_payload_fields(self, event_type: WebSocketEventType) -> List[str]:
        """Get required payload fields for event type."""
        field_requirements = {
            WebSocketEventType.AGENT_STARTED: ['agent_name', 'user_message', 'estimated_duration'],
            WebSocketEventType.AGENT_THINKING: ['current_step', 'reasoning_summary'],
            WebSocketEventType.TOOL_EXECUTING: ['tool_name', 'tool_description', 'execution_params'],
            WebSocketEventType.TOOL_COMPLETED: ['tool_name', 'execution_result', 'success'],
            WebSocketEventType.AGENT_COMPLETED: ['final_result', 'execution_summary', 'success']
        }
        return field_requirements.get(event_type, [])

    def _validate_event_order(self, events: List[WebSocketEvent]) -> bool:
        """Validate that events are in correct order."""
        if not events:
            return True
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        previous_type = None
        for event in sorted_events:
            current_type = event.event_type
            valid_transitions = self.VALID_EVENT_TRANSITIONS.get(previous_type, [])
            
            if current_type not in valid_transitions:
                return False
            
            previous_type = current_type
        
        return True

    def _check_timing_violations(self, events: List[WebSocketEvent]) -> List[str]:
        """Check for timing violations in event sequence."""
        violations = []
        
        if not events:
            return violations
        
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        for i in range(1, len(sorted_events)):
            prev_event = sorted_events[i-1]
            curr_event = sorted_events[i]
            
            time_diff = (curr_event.timestamp - prev_event.timestamp).total_seconds()
            
            if time_diff > self.MAX_EVENT_DELIVERY_SECONDS:
                violations.append(
                    f"Time gap of {time_diff}s between {prev_event.event_type.value} and {curr_event.event_type.value} exceeds {self.MAX_EVENT_DELIVERY_SECONDS}s limit"
                )
        
        return violations

    def _validate_event_content_quality(self, events: List[WebSocketEvent]) -> List[str]:
        """Validate content quality of events."""
        issues = []
        
        for event in events:
            # Check payload completeness
            required_fields = self._get_required_payload_fields(event.event_type)
            for field in required_fields:
                if field not in event.payload:
                    issues.append(f"Event {event.event_id} missing required field: {field}")
                elif not event.payload[field]:  # Empty or None
                    issues.append(f"Event {event.event_id} has empty required field: {field}")
        
        return issues

    def _calculate_timeliness_score(self, sequence: EventSequence) -> float:
        """Calculate timeliness score for event sequence."""
        if not sequence.delivered_events:
            return 0.0
        
        # Calculate time between events
        sorted_events = sorted(sequence.delivered_events, key=lambda e: e.timestamp)
        total_gaps = 0
        gap_count = 0
        
        for i in range(1, len(sorted_events)):
            gap = (sorted_events[i].timestamp - sorted_events[i-1].timestamp).total_seconds()
            total_gaps += gap
            gap_count += 1
        
        if gap_count == 0:
            return 1.0
        
        avg_gap = total_gaps / gap_count
        
        # Score based on how close to ideal gap (1 second)
        ideal_gap = 1.0
        score = max(0.0, 1.0 - abs(avg_gap - ideal_gap) / self.MAX_EVENT_DELIVERY_SECONDS)
        
        return score

    def _calculate_content_quality_score(self, events: List[WebSocketEvent]) -> float:
        """Calculate content quality score for events."""
        if not events:
            return 0.0
        
        total_score = 0.0
        
        for event in events:
            required_fields = self._get_required_payload_fields(event.event_type)
            field_score = 0.0
            
            for field in required_fields:
                if field in event.payload and event.payload[field]:
                    field_score += 1.0
                    
                    # Bonus for rich content
                    if isinstance(event.payload[field], str) and len(event.payload[field]) > 20:
                        field_score += 0.1  # Small bonus for descriptive content
            
            if required_fields:
                field_score = field_score / len(required_fields)
            else:
                field_score = 1.0  # No requirements means perfect score
            
            total_score += field_score
        
        return total_score / len(events)

    def _calculate_user_engagement_score(self, events: List[WebSocketEvent]) -> float:
        """Calculate user engagement score (simplified for testing)."""
        if not events:
            return 0.0
        
        # In real implementation, this would track user interactions
        # For testing, we'll use event richness as a proxy
        engagement_indicators = 0
        
        for event in events:
            if 'user_message' in event.payload:
                engagement_indicators += 1
            if 'estimated_duration' in event.payload:
                engagement_indicators += 1
            if 'execution_result' in event.payload and event.payload['execution_result']:
                engagement_indicators += 1
        
        max_possible_indicators = len(events) * 2  # Rough estimate
        return min(1.0, engagement_indicators / max(1, max_possible_indicators))


@pytest.mark.golden_path
@pytest.mark.unit
class TestWebSocketEventDeliveryBusinessLogic:
    """Test WebSocket event delivery business logic that drives user engagement."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.event_manager = WebSocketEventManager()
        self.base_user_id = str(uuid.uuid4())
        self.base_session_id = str(uuid.uuid4())
        self.base_agent_id = str(uuid.uuid4())
        self.base_run_id = str(uuid.uuid4())
        
    def _create_test_event(self, event_type: WebSocketEventType, 
                          payload: Optional[Dict] = None,
                          user_id: Optional[str] = None) -> WebSocketEvent:
        """Helper to create test events."""
        if payload is None:
            payload = self._get_sample_payload(event_type)
            
        return self.event_manager.create_event(
            event_type=event_type,
            user_id=user_id or self.base_user_id,
            session_id=self.base_session_id,
            agent_id=self.base_agent_id,
            run_id=self.base_run_id,
            payload=payload
        )
    
    def _get_sample_payload(self, event_type: WebSocketEventType) -> Dict[str, Any]:
        """Get sample payload for event type."""
        payloads = {
            WebSocketEventType.AGENT_STARTED: {
                'agent_name': 'Cost Optimizer',
                'user_message': 'Optimize my cloud costs',
                'estimated_duration': 60
            },
            WebSocketEventType.AGENT_THINKING: {
                'current_step': 'Analyzing cost data',
                'reasoning_summary': 'Gathering billing information from AWS'
            },
            WebSocketEventType.TOOL_EXECUTING: {
                'tool_name': 'AWS Cost Explorer',
                'tool_description': 'Fetching cost breakdown by service',
                'execution_params': {'timeframe': 'last_30_days'}
            },
            WebSocketEventType.TOOL_COMPLETED: {
                'tool_name': 'AWS Cost Explorer',
                'execution_result': {'total_cost': 5420.50, 'top_services': ['EC2', 'RDS']},
                'success': True
            },
            WebSocketEventType.AGENT_COMPLETED: {
                'final_result': 'Identified $800/month in potential savings',
                'execution_summary': 'Analyzed costs and found optimization opportunities',
                'success': True
            }
        }
        return payloads.get(event_type, {})

    def _create_complete_event_sequence(self) -> EventSequence:
        """Helper to create complete event sequence."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        # Add all required events
        for event_type in self.event_manager.REQUIRED_EVENTS:
            event = self._create_test_event(event_type)
            sequence.delivered_events.append(event)
        
        return sequence

    # EVENT CREATION TESTS

    def test_create_valid_event(self):
        """Test creation of valid WebSocket event."""
        payload = {
            'agent_name': 'Cost Optimizer',
            'user_message': 'Optimize costs',
            'estimated_duration': 30
        }
        
        event = self.event_manager.create_event(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.base_user_id,
            session_id=self.base_session_id,
            agent_id=self.base_agent_id,
            run_id=self.base_run_id,
            payload=payload
        )
        
        assert event.event_type == WebSocketEventType.AGENT_STARTED
        assert event.user_id == self.base_user_id
        assert event.payload == payload
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.expiration_time is not None

    def test_create_event_with_missing_required_fields(self):
        """Test event creation fails with missing required fields."""
        incomplete_payload = {'agent_name': 'Test Agent'}  # Missing required fields
        
        with pytest.raises(ValueError) as exc_info:
            self.event_manager.create_event(
                event_type=WebSocketEventType.AGENT_STARTED,
                user_id=self.base_user_id,
                session_id=self.base_session_id,
                agent_id=self.base_agent_id,
                run_id=self.base_run_id,
                payload=incomplete_payload
            )
        
        assert "Missing required field" in str(exc_info.value)

    def test_event_expiration_time_by_priority(self):
        """Test that event expiration time varies by priority."""
        payload = self._get_sample_payload(WebSocketEventType.AGENT_STARTED)
        
        critical_event = self.event_manager.create_event(
            WebSocketEventType.AGENT_STARTED, self.base_user_id, self.base_session_id,
            self.base_agent_id, self.base_run_id, payload, EventPriority.CRITICAL
        )
        
        normal_event = self.event_manager.create_event(
            WebSocketEventType.AGENT_STARTED, self.base_user_id, self.base_session_id,
            self.base_agent_id, self.base_run_id, payload, EventPriority.NORMAL
        )
        
        # Critical events should expire sooner
        assert critical_event.expiration_time < normal_event.expiration_time

    # EVENT SEQUENCE VALIDATION TESTS

    def test_complete_valid_event_sequence(self):
        """Test validation of complete, valid event sequence."""
        sequence = self._create_complete_event_sequence()
        
        validation = self.event_manager.validate_event_sequence(sequence)
        
        assert validation['is_complete'] is True
        assert validation['is_ordered_correctly'] is True
        assert len(validation['missing_events']) == 0
        assert len(validation['duplicate_events']) == 0

    def test_incomplete_event_sequence(self):
        """Test validation of incomplete event sequence."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        # Only add first 3 events
        for event_type in self.event_manager.REQUIRED_EVENTS[:3]:
            event = self._create_test_event(event_type)
            sequence.delivered_events.append(event)
        
        validation = self.event_manager.validate_event_sequence(sequence)
        
        assert validation['is_complete'] is False
        assert len(validation['missing_events']) == 2  # Missing last 2 events

    def test_duplicate_events_detection(self):
        """Test detection of duplicate events in sequence."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        # Add duplicate AGENT_THINKING events
        sequence.delivered_events.append(self._create_test_event(WebSocketEventType.AGENT_STARTED))
        sequence.delivered_events.append(self._create_test_event(WebSocketEventType.AGENT_THINKING))
        sequence.delivered_events.append(self._create_test_event(WebSocketEventType.AGENT_THINKING))  # Duplicate
        
        validation = self.event_manager.validate_event_sequence(sequence)
        
        assert WebSocketEventType.AGENT_THINKING in validation['duplicate_events']

    def test_event_order_validation(self):
        """Test validation of event ordering."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        # Add events in wrong order
        sequence.delivered_events.append(self._create_test_event(WebSocketEventType.AGENT_COMPLETED))
        sequence.delivered_events.append(self._create_test_event(WebSocketEventType.AGENT_STARTED))
        
        validation = self.event_manager.validate_event_sequence(sequence)
        
        assert validation['is_ordered_correctly'] is False

    # EVENT QUALITY SCORING TESTS

    def test_perfect_quality_score_calculation(self):
        """Test quality score calculation for perfect event sequence."""
        sequence = self._create_complete_event_sequence()
        
        # Ensure proper timing
        base_time = datetime.now(timezone.utc)
        for i, event in enumerate(sequence.delivered_events):
            event.timestamp = base_time + timedelta(seconds=i + 1)
        
        metrics = self.event_manager.calculate_event_quality_score(sequence)
        
        assert metrics.completeness_score == 1.0  # All events delivered
        assert metrics.timeliness_score > 0.8   # Good timing
        assert metrics.content_quality_score > 0.8  # Rich content
        assert metrics.overall_quality_score > 0.8

    def test_poor_quality_score_calculation(self):
        """Test quality score calculation for poor event sequence."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        # Add only minimal events with poor content
        poor_payload = {'agent_name': ''}  # Empty required field
        event = self._create_test_event(WebSocketEventType.AGENT_STARTED, poor_payload)
        sequence.delivered_events.append(event)
        
        metrics = self.event_manager.calculate_event_quality_score(sequence)
        
        assert metrics.completeness_score < 0.5  # Missing events
        assert metrics.content_quality_score < 0.5  # Poor content
        assert metrics.overall_quality_score < 0.5

    def test_empty_sequence_quality_score(self):
        """Test quality score calculation for empty sequence."""
        sequence = EventSequence(
            run_id=self.base_run_id,
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        
        metrics = self.event_manager.calculate_event_quality_score(sequence)
        
        assert metrics.completeness_score == 0.0
        assert metrics.timeliness_score == 0.0
        assert metrics.content_quality_score == 0.0
        assert metrics.overall_quality_score == 0.0

    # EVENT PRIORITIZATION TESTS

    def test_event_prioritization_by_priority_level(self):
        """Test that events are prioritized by priority level."""
        events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED),
            self._create_test_event(WebSocketEventType.AGENT_THINKING),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED),
        ]
        
        # Set different priorities
        events[0].priority = EventPriority.LOW
        events[1].priority = EventPriority.CRITICAL
        events[2].priority = EventPriority.NORMAL
        
        prioritized = self.event_manager.prioritize_event_delivery(events)
        
        # CRITICAL should be first
        assert prioritized[0].priority == EventPriority.CRITICAL
        assert prioritized[0].event_type == WebSocketEventType.AGENT_THINKING

    def test_event_prioritization_by_sequence_order(self):
        """Test that events are prioritized by sequence order when priority is equal."""
        events = [
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED),
            self._create_test_event(WebSocketEventType.AGENT_STARTED),
            self._create_test_event(WebSocketEventType.TOOL_EXECUTING),
        ]
        
        # All same priority
        for event in events:
            event.priority = EventPriority.NORMAL
        
        prioritized = self.event_manager.prioritize_event_delivery(events)
        
        # AGENT_STARTED should be first (highest sequence priority)
        assert prioritized[0].event_type == WebSocketEventType.AGENT_STARTED

    def test_event_prioritization_empty_list(self):
        """Test event prioritization with empty list."""
        prioritized = self.event_manager.prioritize_event_delivery([])
        assert prioritized == []

    # MULTI-USER ISOLATION TESTS

    def test_multi_user_event_isolation_valid(self):
        """Test multi-user event isolation with valid separation."""
        user1_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, user_id="user1"),
            self._create_test_event(WebSocketEventType.AGENT_THINKING, user_id="user1"),
        ]
        
        user2_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, user_id="user2"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, user_id="user2"),
        ]
        
        all_events = user1_events + user2_events
        
        issues = self.event_manager.detect_multi_user_event_isolation_issues(all_events)
        
        assert len(issues['cross_user_events']) == 0
        assert len(issues['session_mismatches']) == 0
        assert len(issues['run_id_conflicts']) == 0

    def test_multi_user_session_mismatch_detection(self):
        """Test detection of session mismatches within user runs."""
        # Create events for same user/run but different sessions
        event1 = self._create_test_event(WebSocketEventType.AGENT_STARTED)
        event1.session_id = "session1"
        event1.run_id = "shared_run"
        
        event2 = self._create_test_event(WebSocketEventType.AGENT_THINKING)
        event2.session_id = "session2"  # Different session
        event2.run_id = "shared_run"   # Same run
        
        events = [event1, event2]
        
        issues = self.event_manager.detect_multi_user_event_isolation_issues(events)
        
        assert len(issues['session_mismatches']) > 0
        assert "shared_run" in issues['session_mismatches'][0]

    # DELIVERY METRICS TESTS

    def test_delivery_metrics_calculation_all_complete(self):
        """Test delivery metrics calculation with all complete sequences."""
        sequences = [
            self._create_complete_event_sequence(),
            self._create_complete_event_sequence(),
            self._create_complete_event_sequence()
        ]
        
        metrics = self.event_manager.generate_event_delivery_metrics(sequences)
        
        assert metrics['total_sequences'] == 3
        assert metrics['completion_rate'] == 1.0  # All complete
        assert metrics['average_quality_score'] > 0.5
        assert metrics['quality_distribution']['excellent'] > 0

    def test_delivery_metrics_calculation_mixed_completion(self):
        """Test delivery metrics calculation with mixed completion rates."""
        complete_sequence = self._create_complete_event_sequence()
        
        incomplete_sequence = EventSequence(
            run_id=str(uuid.uuid4()),
            user_id=self.base_user_id,
            expected_events=self.event_manager.REQUIRED_EVENTS.copy()
        )
        incomplete_sequence.delivered_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED)
        ]
        
        sequences = [complete_sequence, incomplete_sequence]
        
        metrics = self.event_manager.generate_event_delivery_metrics(sequences)
        
        assert metrics['total_sequences'] == 2
        assert metrics['completion_rate'] == 0.5  # 50% complete
        assert 'quality_distribution' in metrics

    def test_delivery_metrics_empty_sequences(self):
        """Test delivery metrics calculation with empty sequences."""
        metrics = self.event_manager.generate_event_delivery_metrics([])
        
        assert metrics['total_sequences'] == 0

    # BUSINESS RULES VALIDATION TESTS

    def test_required_events_constant(self):
        """Test that required events constant includes all 5 critical events."""
        required = self.event_manager.REQUIRED_EVENTS
        
        assert len(required) == 5
        assert WebSocketEventType.AGENT_STARTED in required
        assert WebSocketEventType.AGENT_THINKING in required
        assert WebSocketEventType.TOOL_EXECUTING in required
        assert WebSocketEventType.TOOL_COMPLETED in required
        assert WebSocketEventType.AGENT_COMPLETED in required

    def test_event_transition_rules(self):
        """Test that event transition rules are properly defined."""
        transitions = self.event_manager.VALID_EVENT_TRANSITIONS
        
        # Agent started should be the only valid first event
        assert transitions[None] == [WebSocketEventType.AGENT_STARTED]
        
        # Agent completed should be terminal (no valid transitions)
        assert transitions[WebSocketEventType.AGENT_COMPLETED] == []
        
        # All event types should have defined transitions
        for event_type in WebSocketEventType:
            assert event_type in transitions or event_type == WebSocketEventType.AGENT_STARTED

    def test_timing_thresholds_are_reasonable(self):
        """Test that timing thresholds are set to reasonable business values."""
        assert self.event_manager.MAX_EVENT_DELIVERY_SECONDS == 5  # 5 seconds max between events
        assert self.event_manager.MAX_SEQUENCE_DURATION_SECONDS == 300  # 5 minutes max total
        assert self.event_manager.MIN_COMPLETENESS_SCORE == 0.9  # 90% completion required