"""Unit tests for WebSocket event ordering validation in Golden Path messages.

These tests validate strict event ordering requirements that protect the $500K+ ARR
business value by ensuring users receive WebSocket events in the correct sequence
for optimal user experience and system reliability.

Business Value: Free/Early/Mid/Enterprise - Event Ordering Integrity
Ensures WebSocket events are delivered in the correct order to maintain user confidence
and enable proper real-time progress tracking during AI agent executions.

EVENT ORDERING REQUIREMENTS:
1. Sequential Dependencies: Each event depends on previous events being completed
2. Temporal Ordering: Events must be delivered in chronological order
3. State Consistency: Event order must maintain consistent system state
4. User Experience: Proper ordering ensures logical progress indication
5. Error Recovery: Out-of-order events must be detected and recovered

Test Coverage:
- Sequential event validation
- Out-of-order event detection
- Missing event detection
- Event dependency validation
- Temporal ordering verification
- Recovery from ordering violations
"""

import asyncio
import pytest
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)


class EventType(Enum):
    """Enumeration of WebSocket event types with ordering constraints."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


class EventOrderingViolationType(Enum):
    """Types of event ordering violations."""
    OUT_OF_ORDER = "out_of_order"
    MISSING_DEPENDENCY = "missing_dependency"
    DUPLICATE_EVENT = "duplicate_event"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    INVALID_TRANSITION = "invalid_transition"


class EventOrderingValidator:
    """Validator for WebSocket event ordering in Golden Path sequences."""

    def __init__(self):
        self.event_sequence = []
        self.event_states = {event_type: False for event_type in EventType}
        self.ordering_violations = []
        self.dependency_graph = self._build_dependency_graph()
        self.temporal_violations = []
        self.state_transitions = []

    def _build_dependency_graph(self) -> Dict[EventType, List[EventType]]:
        """Build event dependency graph for validation."""
        return {
            EventType.AGENT_STARTED: [],  # No dependencies
            EventType.AGENT_THINKING: [EventType.AGENT_STARTED],
            EventType.TOOL_EXECUTING: [EventType.AGENT_THINKING],
            EventType.TOOL_COMPLETED: [EventType.TOOL_EXECUTING],
            EventType.AGENT_COMPLETED: [EventType.TOOL_COMPLETED]
        }

    def validate_event_order(self, event_type: EventType, event_data: Dict[str, Any],
                           timestamp: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Validate that an event can be processed in the current sequence."""
        timestamp = timestamp or datetime.now(timezone.utc)

        # Check for duplicate events
        if self.event_states[event_type]:
            violation = {
                'type': EventOrderingViolationType.DUPLICATE_EVENT,
                'event_type': event_type,
                'timestamp': timestamp,
                'message': f"Duplicate {event_type.value} event detected"
            }
            self.ordering_violations.append(violation)
            return False, violation['message']

        # Check dependencies
        dependencies = self.dependency_graph[event_type]
        missing_deps = [dep for dep in dependencies if not self.event_states[dep]]

        if missing_deps:
            violation = {
                'type': EventOrderingViolationType.MISSING_DEPENDENCY,
                'event_type': event_type,
                'missing_dependencies': missing_deps,
                'timestamp': timestamp,
                'message': f"Missing dependencies for {event_type.value}: {[d.value for d in missing_deps]}"
            }
            self.ordering_violations.append(violation)
            return False, violation['message']

        # Check temporal ordering
        if not self._validate_temporal_order(event_type, timestamp):
            violation = {
                'type': EventOrderingViolationType.TEMPORAL_INCONSISTENCY,
                'event_type': event_type,
                'timestamp': timestamp,
                'message': f"Temporal ordering violation for {event_type.value}"
            }
            self.ordering_violations.append(violation)
            return False, violation['message']

        # Valid event - record it
        self.event_states[event_type] = True
        self.event_sequence.append({
            'event_type': event_type,
            'timestamp': timestamp,
            'data': event_data
        })
        self.state_transitions.append((len(self.event_sequence) - 1, event_type, timestamp))

        return True, None

    def _validate_temporal_order(self, event_type: EventType, timestamp: datetime) -> bool:
        """Validate temporal ordering of events."""
        if not self.event_sequence:
            return True

        last_event = self.event_sequence[-1]
        last_timestamp = last_event['timestamp']

        # Events must be in chronological order
        if timestamp < last_timestamp:
            self.temporal_violations.append({
                'current_event': event_type,
                'current_timestamp': timestamp,
                'last_event': last_event['event_type'],
                'last_timestamp': last_timestamp,
                'time_delta': (timestamp - last_timestamp).total_seconds()
            })
            return False

        return True

    def get_expected_next_events(self) -> List[EventType]:
        """Get list of events that can be validly processed next."""
        valid_next = []

        for event_type, dependencies in self.dependency_graph.items():
            if self.event_states[event_type]:
                continue  # Already processed

            # Check if all dependencies are satisfied
            if all(self.event_states[dep] for dep in dependencies):
                valid_next.append(event_type)

        return valid_next

    def get_sequence_completion_status(self) -> Dict[str, Any]:
        """Get status of sequence completion."""
        total_events = len(EventType)
        completed_events = sum(1 for state in self.event_states.values() if state)

        return {
            'total_events': total_events,
            'completed_events': completed_events,
            'completion_percentage': (completed_events / total_events) * 100,
            'is_complete': completed_events == total_events,
            'next_expected': self.get_expected_next_events(),
            'violations_count': len(self.ordering_violations)
        }

    def reset_validator(self):
        """Reset validator for new sequence validation."""
        self.event_sequence = []
        self.event_states = {event_type: False for event_type in EventType}
        self.ordering_violations = []
        self.temporal_violations = []
        self.state_transitions = []


class EventOrderingValidationTests(SSotAsyncTestCase):
    """Test WebSocket event ordering validation for Golden Path business value."""

    def setup_method(self, method):
        """Set up test fixtures for event ordering validation."""
        super().setup_method(method)
        self.validator = EventOrderingValidator()
        self.run_id = str(uuid.uuid4())
        self.base_event_data = {
            'run_id': self.run_id,
            'agent_name': 'test_agent',
            'user_id': 'test_user'
        }

    async def test_valid_sequential_event_processing(self):
        """Test processing of events in valid sequential order."""
        # Define valid event sequence
        valid_sequence = [
            (EventType.AGENT_STARTED, {'action': 'initialization'}),
            (EventType.AGENT_THINKING, {'reasoning': 'analyzing request'}),
            (EventType.TOOL_EXECUTING, {'tool': 'data_processor', 'params': {}}),
            (EventType.TOOL_COMPLETED, {'tool': 'data_processor', 'result': 'success'}),
            (EventType.AGENT_COMPLETED, {'response': 'task completed'})
        ]

        # Process each event in sequence
        for event_type, event_data in valid_sequence:
            full_data = {**self.base_event_data, **event_data}
            is_valid, error_message = self.validator.validate_event_order(event_type, full_data)

            assert is_valid, f"Event {event_type.value} should be valid: {error_message}"
            assert error_message is None, f"Should have no error message for valid event"

        # Validate sequence completion
        status = self.validator.get_sequence_completion_status()
        assert status['is_complete'], "Sequence should be complete"
        assert status['completion_percentage'] == 100.0, "Should be 100% complete"
        assert len(status['next_expected']) == 0, "No events should be expected next"
        assert status['violations_count'] == 0, "Should have no violations"

    async def test_out_of_order_event_detection(self):
        """Test detection of out-of-order events."""
        # Try to process thinking before started
        is_valid, error = self.validator.validate_event_order(
            EventType.AGENT_THINKING,
            {**self.base_event_data, 'reasoning': 'premature thinking'}
        )

        assert not is_valid, "Out-of-order event should be invalid"
        assert "Missing dependencies" in error, "Should indicate missing dependencies"
        assert len(self.validator.ordering_violations) == 1, "Should record violation"

        violation = self.validator.ordering_violations[0]
        assert violation['type'] == EventOrderingViolationType.MISSING_DEPENDENCY
        assert EventType.AGENT_STARTED in violation['missing_dependencies']

    async def test_missing_event_detection(self):
        """Test detection of missing events in sequence."""
        # Start with agent_started
        self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'started'}
        )

        # Skip agent_thinking and try tool_executing
        is_valid, error = self.validator.validate_event_order(
            EventType.TOOL_EXECUTING,
            {**self.base_event_data, 'tool': 'premature_tool'}
        )

        assert not is_valid, "Should detect missing agent_thinking event"
        assert "Missing dependencies" in error, "Should indicate missing dependencies"

        # Validate violation details
        violation = self.validator.ordering_violations[0]
        assert violation['event_type'] == EventType.TOOL_EXECUTING
        assert EventType.AGENT_THINKING in violation['missing_dependencies']

    async def test_duplicate_event_prevention(self):
        """Test prevention of duplicate events in sequence."""
        # Process agent_started normally
        is_valid, _ = self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'first_start'}
        )
        assert is_valid, "First agent_started should be valid"

        # Try to process agent_started again
        is_valid, error = self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'duplicate_start'}
        )

        assert not is_valid, "Duplicate event should be invalid"
        assert "Duplicate" in error, "Should indicate duplicate event"
        assert len(self.validator.ordering_violations) == 1, "Should record duplicate violation"

        violation = self.validator.ordering_violations[0]
        assert violation['type'] == EventOrderingViolationType.DUPLICATE_EVENT
        assert violation['event_type'] == EventType.AGENT_STARTED

    async def test_event_dependency_validation(self):
        """Test validation of event dependencies."""
        # Test each event type's dependencies
        dependency_tests = [
            (EventType.AGENT_THINKING, [EventType.AGENT_STARTED]),
            (EventType.TOOL_EXECUTING, [EventType.AGENT_THINKING]),
            (EventType.TOOL_COMPLETED, [EventType.TOOL_EXECUTING]),
            (EventType.AGENT_COMPLETED, [EventType.TOOL_COMPLETED])
        ]

        for event_type, required_deps in dependency_tests:
            # Reset validator for each test
            self.validator.reset_validator()

            # Try to process event without dependencies
            is_valid, error = self.validator.validate_event_order(
                event_type,
                {**self.base_event_data, 'test': f'dependency_test_{event_type.value}'}
            )

            assert not is_valid, f"{event_type.value} should require dependencies"
            assert len(self.validator.ordering_violations) == 1, "Should record dependency violation"

            violation = self.validator.ordering_violations[0]
            assert violation['type'] == EventOrderingViolationType.MISSING_DEPENDENCY

            # Validate all required dependencies are listed
            for dep in required_deps:
                assert dep in violation['missing_dependencies'], \
                    f"Should list {dep.value} as missing dependency"

    async def test_temporal_ordering_verification(self):
        """Test temporal ordering verification with timestamps."""
        base_time = datetime.now(timezone.utc)

        # Create events with proper temporal progression
        events_with_timing = [
            (EventType.AGENT_STARTED, base_time, {'action': 'started'}),
            (EventType.AGENT_THINKING, base_time + timedelta(milliseconds=100), {'reasoning': 'processing'}),
            (EventType.TOOL_EXECUTING, base_time + timedelta(milliseconds=200), {'tool': 'processor'}),
            (EventType.TOOL_COMPLETED, base_time + timedelta(milliseconds=300), {'result': 'done'}),
            (EventType.AGENT_COMPLETED, base_time + timedelta(milliseconds=400), {'response': 'complete'})
        ]

        # Process events with correct temporal order
        for event_type, timestamp, event_data in events_with_timing:
            full_data = {**self.base_event_data, **event_data}
            is_valid, error = self.validator.validate_event_order(event_type, full_data, timestamp)

            assert is_valid, f"Temporally ordered {event_type.value} should be valid"

        # Verify no temporal violations
        assert len(self.validator.temporal_violations) == 0, "Should have no temporal violations"

    async def test_temporal_inconsistency_detection(self):
        """Test detection of temporal inconsistencies in event ordering."""
        base_time = datetime.now(timezone.utc)

        # Start sequence normally
        self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'started'},
            base_time
        )

        self.validator.validate_event_order(
            EventType.AGENT_THINKING,
            {**self.base_event_data, 'reasoning': 'processing'},
            base_time + timedelta(milliseconds=100)
        )

        # Try to add event with earlier timestamp (temporal violation)
        is_valid, error = self.validator.validate_event_order(
            EventType.TOOL_EXECUTING,
            {**self.base_event_data, 'tool': 'time_travel_tool'},
            base_time + timedelta(milliseconds=50)  # Earlier than previous event
        )

        assert not is_valid, "Temporally inconsistent event should be invalid"
        assert "Temporal ordering violation" in error, "Should indicate temporal violation"
        assert len(self.validator.temporal_violations) == 1, "Should record temporal violation"

        temporal_violation = self.validator.temporal_violations[0]
        assert temporal_violation['current_event'] == EventType.TOOL_EXECUTING
        assert temporal_violation['time_delta'] < 0, "Time delta should be negative"

    async def test_expected_next_events_calculation(self):
        """Test calculation of expected next events in sequence."""
        # Initial state - only agent_started should be valid
        next_events = self.validator.get_expected_next_events()
        assert next_events == [EventType.AGENT_STARTED], "Initially only agent_started should be valid"

        # After agent_started, only agent_thinking should be valid
        self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'started'}
        )
        next_events = self.validator.get_expected_next_events()
        assert next_events == [EventType.AGENT_THINKING], "After started, only thinking should be valid"

        # After agent_thinking, only tool_executing should be valid
        self.validator.validate_event_order(
            EventType.AGENT_THINKING,
            {**self.base_event_data, 'reasoning': 'processing'}
        )
        next_events = self.validator.get_expected_next_events()
        assert next_events == [EventType.TOOL_EXECUTING], "After thinking, only tool_executing should be valid"

        # Continue sequence and validate progression
        self.validator.validate_event_order(
            EventType.TOOL_EXECUTING,
            {**self.base_event_data, 'tool': 'processor'}
        )
        next_events = self.validator.get_expected_next_events()
        assert next_events == [EventType.TOOL_COMPLETED], "After executing, only tool_completed should be valid"

        self.validator.validate_event_order(
            EventType.TOOL_COMPLETED,
            {**self.base_event_data, 'result': 'success'}
        )
        next_events = self.validator.get_expected_next_events()
        assert next_events == [EventType.AGENT_COMPLETED], "After completed, only agent_completed should be valid"

        # Final state - no more events expected
        self.validator.validate_event_order(
            EventType.AGENT_COMPLETED,
            {**self.base_event_data, 'response': 'done'}
        )
        next_events = self.validator.get_expected_next_events()
        assert next_events == [], "After agent_completed, no more events should be expected"

    async def test_sequence_completion_status_tracking(self):
        """Test tracking of sequence completion status."""
        # Check initial status
        status = self.validator.get_sequence_completion_status()
        assert status['completed_events'] == 0
        assert status['completion_percentage'] == 0.0
        assert not status['is_complete']
        assert status['violations_count'] == 0

        # Process partial sequence
        events_to_process = [
            (EventType.AGENT_STARTED, {'action': 'started'}),
            (EventType.AGENT_THINKING, {'reasoning': 'processing'})
        ]

        for event_type, event_data in events_to_process:
            self.validator.validate_event_order(event_type, {**self.base_event_data, **event_data})

        # Check intermediate status
        status = self.validator.get_sequence_completion_status()
        assert status['completed_events'] == 2
        assert status['completion_percentage'] == 40.0  # 2/5 * 100
        assert not status['is_complete']
        assert len(status['next_expected']) == 1
        assert status['next_expected'][0] == EventType.TOOL_EXECUTING

    async def test_recovery_from_ordering_violations(self):
        """Test recovery mechanisms from event ordering violations."""
        # Cause a violation by processing events out of order
        self.validator.validate_event_order(
            EventType.TOOL_EXECUTING,
            {**self.base_event_data, 'tool': 'premature_tool'}
        )

        assert len(self.validator.ordering_violations) == 1, "Should have recorded violation"

        # Reset and recover with correct sequence
        self.validator.reset_validator()

        # Process correct sequence
        correct_sequence = [
            (EventType.AGENT_STARTED, {'action': 'recovery_start'}),
            (EventType.AGENT_THINKING, {'reasoning': 'recovery_thinking'}),
            (EventType.TOOL_EXECUTING, {'tool': 'recovery_tool'}),
            (EventType.TOOL_COMPLETED, {'result': 'recovered'}),
            (EventType.AGENT_COMPLETED, {'response': 'recovery_complete'})
        ]

        for event_type, event_data in correct_sequence:
            is_valid, error = self.validator.validate_event_order(
                event_type,
                {**self.base_event_data, **event_data}
            )
            assert is_valid, f"Recovery event {event_type.value} should be valid"

        # Validate successful recovery
        status = self.validator.get_sequence_completion_status()
        assert status['is_complete'], "Should complete sequence after recovery"
        assert status['violations_count'] == 0, "Should have no violations after recovery"

    async def test_complex_ordering_scenario_validation(self):
        """Test complex event ordering scenarios with multiple potential paths."""
        # Simulate complex scenario with conditional events
        # Start normal sequence
        self.validator.validate_event_order(
            EventType.AGENT_STARTED,
            {**self.base_event_data, 'action': 'complex_start'}
        )

        self.validator.validate_event_order(
            EventType.AGENT_THINKING,
            {**self.base_event_data, 'reasoning': 'complex analysis', 'branches': ['A', 'B']}
        )

        # In complex scenarios, we might have multiple tool executions
        # For this validator, we'll simulate the consolidated approach
        self.validator.validate_event_order(
            EventType.TOOL_EXECUTING,
            {**self.base_event_data, 'tool': 'complex_tool', 'sub_operations': ['op1', 'op2']}
        )

        self.validator.validate_event_order(
            EventType.TOOL_COMPLETED,
            {**self.base_event_data, 'result': 'complex_complete', 'all_ops_success': True}
        )

        self.validator.validate_event_order(
            EventType.AGENT_COMPLETED,
            {**self.base_event_data, 'response': 'complex scenario completed'}
        )

        # Validate complex scenario completion
        status = self.validator.get_sequence_completion_status()
        assert status['is_complete'], "Complex scenario should complete successfully"

    async def test_concurrent_sequence_isolation(self):
        """Test isolation of event ordering validation between concurrent sequences."""
        # Create validators for concurrent sequences
        validator_1 = EventOrderingValidator()
        validator_2 = EventOrderingValidator()

        run_id_1 = str(uuid.uuid4())
        run_id_2 = str(uuid.uuid4())

        base_data_1 = {**self.base_event_data, 'run_id': run_id_1}
        base_data_2 = {**self.base_event_data, 'run_id': run_id_2}

        # Process sequences independently
        # Sequence 1: Normal progression
        validator_1.validate_event_order(
            EventType.AGENT_STARTED,
            {**base_data_1, 'sequence': 1}
        )

        # Sequence 2: Start at different time
        validator_2.validate_event_order(
            EventType.AGENT_STARTED,
            {**base_data_2, 'sequence': 2}
        )

        # Continue sequence 1
        validator_1.validate_event_order(
            EventType.AGENT_THINKING,
            {**base_data_1, 'reasoning': 'sequence_1_thinking'}
        )

        # Validate isolation
        status_1 = validator_1.get_sequence_completion_status()
        status_2 = validator_2.get_sequence_completion_status()

        assert status_1['completed_events'] == 2, "Sequence 1 should have 2 events"
        assert status_2['completed_events'] == 1, "Sequence 2 should have 1 event"

        # Validate no cross-contamination
        assert len(validator_1.event_sequence) == 2
        assert len(validator_2.event_sequence) == 1

        for event in validator_1.event_sequence:
            assert event['data']['run_id'] == run_id_1, "Sequence 1 events should be isolated"

        for event in validator_2.event_sequence:
            assert event['data']['run_id'] == run_id_2, "Sequence 2 events should be isolated"

    async def test_performance_impact_of_ordering_validation(self):
        """Test performance impact of event ordering validation."""
        import time

        # Measure validation performance for large number of sequences
        start_time = time.time()

        num_sequences = 100
        validators = []

        for i in range(num_sequences):
            validator = EventOrderingValidator()
            run_id = str(uuid.uuid4())

            # Process complete sequence
            sequence = [
                (EventType.AGENT_STARTED, {'sequence_id': i}),
                (EventType.AGENT_THINKING, {'reasoning': f'batch_{i}'}),
                (EventType.TOOL_EXECUTING, {'tool': f'tool_{i}'}),
                (EventType.TOOL_COMPLETED, {'result': f'result_{i}'}),
                (EventType.AGENT_COMPLETED, {'response': f'complete_{i}'})
            ]

            for event_type, event_data in sequence:
                validator.validate_event_order(
                    event_type,
                    {**self.base_event_data, 'run_id': run_id, **event_data}
                )

            validators.append(validator)

        end_time = time.time()
        total_time = end_time - start_time

        # Validate performance is reasonable
        assert total_time < 5.0, f"Processing {num_sequences} sequences should complete in under 5 seconds, took {total_time:.2f}s"

        # Validate all sequences completed successfully
        for i, validator in enumerate(validators):
            status = validator.get_sequence_completion_status()
            assert status['is_complete'], f"Sequence {i} should be complete"
            assert status['violations_count'] == 0, f"Sequence {i} should have no violations"

    async def test_business_value_ordering_requirements(self):
        """Test that event ordering validation protects business value requirements."""
        # Business requirement: Users must see agent_started before any other events
        # for confidence and transparency

        # Attempt to violate business requirement
        business_violation_attempts = [
            (EventType.AGENT_THINKING, {'business_impact': 'high', 'value': '$100K'}),
            (EventType.TOOL_EXECUTING, {'enterprise_feature': True}),
            (EventType.AGENT_COMPLETED, {'customer_tier': 'enterprise'})
        ]

        for event_type, event_data in business_violation_attempts:
            is_valid, error = self.validator.validate_event_order(
                event_type,
                {**self.base_event_data, **event_data}
            )

            assert not is_valid, f"Business requirement violation for {event_type.value} should be prevented"
            assert len(self.validator.ordering_violations) > 0, "Should record business requirement violation"

            # Reset for next test
            self.validator.reset_validator()

        # Validate business requirement compliance
        # Proper sequence that protects business value
        business_compliant_sequence = [
            (EventType.AGENT_STARTED, {'transparency': True, 'user_confidence': 'high'}),
            (EventType.AGENT_THINKING, {'visible_reasoning': True, 'business_value': '$50K'}),
            (EventType.TOOL_EXECUTING, {'progress_visible': True, 'enterprise_grade': True}),
            (EventType.TOOL_COMPLETED, {'results_available': True, 'value_delivered': True}),
            (EventType.AGENT_COMPLETED, {'customer_satisfaction': 'high', 'roi_positive': True})
        ]

        for event_type, event_data in business_compliant_sequence:
            is_valid, error = self.validator.validate_event_order(
                event_type,
                {**self.base_event_data, **event_data}
            )
            assert is_valid, f"Business compliant {event_type.value} should be valid"

        # Validate business value protection
        status = self.validator.get_sequence_completion_status()
        assert status['is_complete'], "Business compliant sequence should complete"
        assert status['violations_count'] == 0, "Business compliant sequence should have no violations"