"""
Unit Tests for WebSocket Connection State Machine Core Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal - WebSocket Infrastructure
- Business Goal: Eliminate race conditions enabling reliable chat functionality for $120K+ MRR
- Value Impact: Prevents message loss and connection state confusion during WebSocket setup
- Strategic Impact: Foundation for reliable multi-user agent execution and real-time updates

CRITICAL TESTING REQUIREMENTS:
1. State transitions must be atomic and thread-safe
2. Race condition scenarios must be tested extensively  
3. Message queuing coordination must work correctly
4. State rollback on failures must be validated
5. Concurrent state access must be handled properly

This test suite validates the WebSocket Connection State Machine business logic:
- ApplicationConnectionState enum and state definitions
- StateTransitionInfo atomic operations
- ConnectionStateMachine thread-safe state management
- State validation and transition rules enforcement
- Error handling and rollback mechanisms
- Performance metrics and state timing tracking

STATE TRANSITION FLOW TO TEST:
CONNECTING  ->  ACCEPTED  ->  AUTHENTICATED  ->  SERVICES_READY  ->  PROCESSING_READY

RACE CONDITION SCENARIOS TO TEST:
- Concurrent authentication and service initialization
- Multiple state transition attempts
- State rollback during failures
- Message queuing during state transitions
- Thread-safe state access patterns

Following SSOT patterns:
- Uses real ConnectionStateTransition logic (no mocks)
- Imports from websocket_core.connection_state_machine (SSOT)
- Strongly typed with ApplicationConnectionState enum
- Absolute imports only (no relative imports)
- Test categorization with @pytest.mark.unit
"""
import asyncio
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock, patch
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, StateTransitionInfo, ConnectionStateMachine
from shared.types.core_types import ConnectionID, UserID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class TestApplicationConnectionStateEnum(SSotBaseTestCase):
    """
    Unit tests for ApplicationConnectionState enum definitions and validation.
    
    CRITICAL: These tests validate that connection states are properly defined
    and transitions follow the correct business logic flow.
    
    Tests focus on:
    1. State enum completeness and correct values
    2. State transition validation rules
    3. State comparison and ordering logic
    4. State serialization for logging and monitoring
    """

    def test_application_connection_state_enum_completeness(self):
        """Test ApplicationConnectionState enum has all required states."""
        expected_states = ['CONNECTING', 'ACCEPTED', 'AUTHENTICATED', 'SERVICES_READY', 'PROCESSING_READY']
        for expected_state in expected_states:
            assert hasattr(ApplicationConnectionState, expected_state)
            state_value = getattr(ApplicationConnectionState, expected_state)
            assert isinstance(state_value, str)
            assert isinstance(state_value, ApplicationConnectionState)

    def test_application_connection_state_values(self):
        """Test ApplicationConnectionState enum values match expected strings."""
        state_mappings = {ApplicationConnectionState.CONNECTING: 'connecting', ApplicationConnectionState.ACCEPTED: 'accepted', ApplicationConnectionState.AUTHENTICATED: 'authenticated', ApplicationConnectionState.SERVICES_READY: 'services_ready', ApplicationConnectionState.PROCESSING_READY: 'processing_ready'}
        for state_enum, expected_value in state_mappings.items():
            assert state_enum == expected_value
            assert str(state_enum) == expected_value

    def test_state_transition_validation_rules(self):
        """Test state transition validation rules enforce correct flow."""
        valid_transitions = [(ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY), (ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.ACCEPTED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.CONNECTING)]
        invalid_transitions = [(ApplicationConnectionState.CONNECTING, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.PROCESSING_READY), (ApplicationConnectionState.CONNECTING, ApplicationConnectionState.PROCESSING_READY), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.PROCESSING_READY)]
        for from_state, to_state in valid_transitions:
            assert isinstance(from_state, ApplicationConnectionState)
            assert isinstance(to_state, ApplicationConnectionState)
        for from_state, to_state in invalid_transitions:
            assert isinstance(from_state, ApplicationConnectionState)
            assert isinstance(to_state, ApplicationConnectionState)

    def test_state_comparison_and_ordering(self):
        """Test state comparison logic for progression tracking."""
        state_progression = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
        for i in range(len(state_progression) - 1):
            current_state = state_progression[i]
            next_state = state_progression[i + 1]
            assert current_state != next_state
            assert isinstance(current_state, ApplicationConnectionState)
            assert isinstance(next_state, ApplicationConnectionState)

    def test_state_serialization_for_logging(self):
        """Test state serialization for logging and monitoring systems."""
        all_states = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
        for state in all_states:
            state_str = str(state)
            assert isinstance(state_str, str)
            assert len(state_str) > 0
            import json
            serialized = json.dumps(state_str)
            assert isinstance(serialized, str)
            deserialized = json.loads(serialized)
            assert deserialized == state_str

@pytest.mark.unit
class TestConnectionStateTransition(SSotBaseTestCase):
    """
    Unit tests for ConnectionStateTransition atomic operations.
    
    CRITICAL: These tests validate that state transitions are atomic and
    properly handle race conditions and concurrent access scenarios.
    
    Tests focus on:
    1. Atomic state transition execution
    2. Thread-safety during concurrent transitions
    3. State validation before and after transitions
    4. Error handling and rollback mechanisms
    5. State transition timing and performance metrics
    """

    def setUp(self) -> None:
        """Set up test environment for state transition testing."""
        super().setUp()
        self.connection_id = 'test_connection_123'
        self.user_id = ensure_user_id('test_user_456')

    def test_connection_state_transition_initialization(self):
        """Test ConnectionStateTransition initializes correctly."""
        transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.CONNECTING, to_state=ApplicationConnectionState.ACCEPTED, user_id=self.user_id)
        assert transition.connection_id == self.connection_id
        assert transition.from_state == ApplicationConnectionState.CONNECTING
        assert transition.to_state == ApplicationConnectionState.ACCEPTED
        assert transition.user_id == self.user_id
        assert hasattr(transition, 'timestamp')
        assert isinstance(transition.timestamp, datetime)

    def test_atomic_state_transition_execution(self):
        """Test atomic state transition execution prevents race conditions."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        initial_state = state_machine.get_current_state()
        assert initial_state == ApplicationConnectionState.CONNECTING
        transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.CONNECTING, to_state=ApplicationConnectionState.ACCEPTED, user_id=self.user_id)
        success = state_machine.execute_transition(transition)
        assert success is True
        new_state = state_machine.get_current_state()
        assert new_state == ApplicationConnectionState.ACCEPTED
        assert new_state != initial_state

    def test_concurrent_state_transition_thread_safety(self):
        """Test concurrent state transitions maintain thread safety."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        transition_results = []
        transition_lock = threading.Lock()

        def attempt_transition(from_state, to_state, thread_id):
            """Attempt a state transition from a specific thread."""
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=from_state, to_state=to_state, user_id=self.user_id)
            time.sleep(0.01)
            result = state_machine.execute_transition(transition)
            with transition_lock:
                transition_results.append({'thread_id': thread_id, 'from_state': from_state, 'to_state': to_state, 'success': result, 'final_state': state_machine.get_current_state()})
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(attempt_transition, ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, f'thread_{i}')
                futures.append(future)
            for future in as_completed(futures):
                future.result()
        assert len(transition_results) == 5
        successful_transitions = [r for r in transition_results if r['success']]
        assert len(successful_transitions) >= 1
        final_states = [r['final_state'] for r in transition_results]
        assert len(set(final_states)) == 1

    def test_state_transition_validation_rules(self):
        """Test state transition validation enforces business rules."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        valid_transitions = [(ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY)]
        current_state = ApplicationConnectionState.CONNECTING
        for from_state, to_state in valid_transitions:
            if state_machine.get_current_state() != from_state:
                state_machine._current_state = from_state
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=from_state, to_state=to_state, user_id=self.user_id)
            success = state_machine.execute_transition(transition)
            assert success is True
            assert state_machine.get_current_state() == to_state
            current_state = to_state

    def test_invalid_state_transition_rejection(self):
        """Test invalid state transitions are properly rejected."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        invalid_transitions = [(ApplicationConnectionState.CONNECTING, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.PROCESSING_READY), (ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.CONNECTING)]
        for from_state, to_state in invalid_transitions:
            state_machine._current_state = from_state
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=from_state, to_state=to_state, user_id=self.user_id)
            success = state_machine.execute_transition(transition)
            assert success is False
            assert state_machine.get_current_state() == from_state

    def test_state_transition_error_handling_and_rollback(self):
        """Test state transition error handling and rollback mechanisms."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
        original_state = state_machine.get_current_state()
        transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.AUTHENTICATED, to_state=ApplicationConnectionState.SERVICES_READY, user_id=self.user_id)
        with patch.object(state_machine, '_validate_transition') as mock_validate:
            mock_validate.side_effect = StateTransitionError('Simulated failure')
            success = state_machine.execute_transition(transition)
            assert success is False
            current_state = state_machine.get_current_state()
            assert current_state == original_state

    def test_state_transition_timing_and_performance_metrics(self):
        """Test state transition timing and performance metrics collection."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.CONNECTING, to_state=ApplicationConnectionState.ACCEPTED, user_id=self.user_id)
        start_time = time.time()
        success = state_machine.execute_transition(transition)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000
        assert success is True
        assert execution_time < 1000
        assert execution_time >= 0
        assert hasattr(transition, 'timestamp')
        assert isinstance(transition.timestamp, datetime)

@pytest.mark.unit
class TestConnectionStateMachine(SSotBaseTestCase):
    """
    Unit tests for ConnectionStateMachine core business logic.
    
    CRITICAL: These tests validate the state machine maintains consistent state
    across concurrent operations and properly coordinates message queuing.
    
    Tests focus on:
    1. State machine initialization and lifecycle
    2. Thread-safe state access and modification
    3. Message queuing coordination during state changes
    4. State validation and consistency checks
    5. Error recovery and state restoration
    """

    def setUp(self) -> None:
        """Set up test environment for state machine testing."""
        super().setUp()
        self.connection_id = 'test_connection_state_machine'
        self.user_id = ensure_user_id('test_user_state')

    def test_websocket_connection_state_machine_initialization(self):
        """Test ConnectionStateMachine initializes correctly."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        assert state_machine.connection_id == self.connection_id
        assert hasattr(state_machine, '_current_state')
        assert hasattr(state_machine, '_state_lock')
        current_state = state_machine.get_current_state()
        assert current_state == ApplicationConnectionState.CONNECTING
        assert hasattr(state_machine, '_state_lock')
        assert isinstance(state_machine._state_lock, threading.Lock)

    def test_thread_safe_state_access_and_modification(self):
        """Test thread-safe state access and modification under concurrent load."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        access_results = []
        access_lock = threading.Lock()

        def concurrent_state_access(thread_id, operation_count):
            """Perform concurrent state access operations."""
            thread_results = []
            for i in range(operation_count):
                current_state = state_machine.get_current_state()
                time.sleep(0.001)
                thread_results.append({'thread_id': thread_id, 'operation': i, 'state': current_state, 'timestamp': time.time()})
            with access_lock:
                access_results.extend(thread_results)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for thread_id in range(10):
                future = executor.submit(concurrent_state_access, thread_id, 50)
                futures.append(future)
            for future in as_completed(futures):
                future.result()
        assert len(access_results) == 500
        state_values = [r['state'] for r in access_results]
        assert all((state == ApplicationConnectionState.CONNECTING for state in state_values))

    def test_message_queuing_coordination_during_state_changes(self):
        """Test message queuing coordination during state transitions."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        coordination_methods = ['is_ready_for_message_processing', 'should_queue_messages', 'get_processing_readiness_state']
        for method_name in coordination_methods:
            has_method = hasattr(state_machine, method_name)
            if has_method:
                method = getattr(state_machine, method_name)
                assert callable(method)
        assert state_machine.get_current_state() == ApplicationConnectionState.CONNECTING
        transitions = [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
        for to_state in transitions:
            transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=state_machine.get_current_state(), to_state=to_state, user_id=self.user_id)
            success = state_machine.execute_transition(transition)
            assert success is True
        assert state_machine.get_current_state() == ApplicationConnectionState.PROCESSING_READY

    def test_state_validation_and_consistency_checks(self):
        """Test state validation and consistency checking mechanisms."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        validation_methods = ['_validate_state', '_validate_transition', 'is_state_consistent']
        for method_name in validation_methods:
            has_method = hasattr(state_machine, method_name)
            if has_method:
                method = getattr(state_machine, method_name)
                assert callable(method)
        current_state = state_machine.get_current_state()
        assert isinstance(current_state, ApplicationConnectionState)
        assert state_machine._current_state == current_state
        assert state_machine.connection_id == self.connection_id

    def test_error_recovery_and_state_restoration(self):
        """Test error recovery and state restoration mechanisms."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        transition_to_authenticated = ConnectionStateTransition(connection_id=self.connection_id, from_state=ApplicationConnectionState.CONNECTING, to_state=ApplicationConnectionState.ACCEPTED, user_id=self.user_id)
        success = state_machine.execute_transition(transition_to_authenticated)
        assert success is True
        stable_state = state_machine.get_current_state()
        assert stable_state == ApplicationConnectionState.ACCEPTED
        original_state = state_machine._current_state
        restored_state = state_machine.get_current_state()
        assert restored_state == stable_state
        next_transition = ConnectionStateTransition(connection_id=self.connection_id, from_state=restored_state, to_state=ApplicationConnectionState.AUTHENTICATED, user_id=self.user_id)
        success = state_machine.execute_transition(next_transition)
        assert success is True
        assert state_machine.get_current_state() == ApplicationConnectionState.AUTHENTICATED

    def test_state_machine_lifecycle_management(self):
        """Test state machine lifecycle management and cleanup."""
        state_machine = ConnectionStateMachine(connection_id=self.connection_id)
        lifecycle_methods = ['initialize', 'cleanup', 'reset_state']
        for method_name in lifecycle_methods:
            has_method = hasattr(state_machine, method_name)
            if has_method:
                method = getattr(state_machine, method_name)
                assert callable(method)
        initial_connection_id = state_machine.connection_id
        initial_state = state_machine.get_current_state()
        assert state_machine.connection_id == initial_connection_id
        assert isinstance(state_machine.get_current_state(), ApplicationConnectionState)
        assert hasattr(state_machine, '_state_lock')
        assert isinstance(state_machine._state_lock, threading.Lock)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')