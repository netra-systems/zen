"""
WebSocket Connection State Machine Race Condition Unit Tests

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Risk Reduction
- Value Impact: Prevents WebSocket state machine corruption during concurrent operations
- Strategic Impact: Protects $500K+ ARR by ensuring reliable chat connection lifecycle

CRITICAL RACE CONDITION REPRODUCTION TESTS:
These tests target the ApplicationConnectionState machine race conditions that occur
in GCP Cloud Run environments where multiple threads attempt state transitions
simultaneously, leading to inconsistent connection states.

Specific Race Conditions Targeted:
1. Concurrent state transitions causing invalid final states
2. State transition validation bypassed during high concurrency
3. State history corruption during rapid transitions
4. Callback notification failures during state changes

CRITICAL: These tests are designed to FAIL initially to prove race condition reproduction.
"""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, patch
from dataclasses import dataclass
from datetime import datetime, timezone
import pytest
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, ConnectionStateMachine, ConnectionStateMachineRegistry, StateTransitionInfo, get_connection_state_registry
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from test_framework.base import BaseTestCase

@dataclass
class RaceConditionEvent:
    """Track race condition events for analysis."""
    timestamp: float
    event_type: str
    thread_id: int
    state_before: Optional[ApplicationConnectionState]
    state_after: Optional[ApplicationConnectionState]
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ConnectionStateMachineRaceConditionTest(BaseTestCase):
    """
    Unit tests for connection state machine race conditions.
    
    CRITICAL: These tests simulate high-concurrency scenarios that naturally
    occur in GCP Cloud Run to reproduce state machine race conditions.
    """

    def setup_method(self):
        """Set up race condition test environment."""
        super().setup_method()
        self.connection_id = ConnectionID('race_conn_12345')
        self.user_id = ensure_user_id('race_user_12345')
        self.race_events: List[RaceConditionEvent] = []
        self.state_inconsistencies: List[str] = []
        self.callback_failures: List[str] = []
        self.transition_violations: List[str] = []
        self.start_barrier = threading.Barrier(5)
        self.race_condition_detected = threading.Event()
        self.state_machine = ConnectionStateMachine(connection_id=self.connection_id, user_id=self.user_id)
        self.callback_invocations = []
        self.state_machine.add_state_change_callback(self._track_state_change)

    def _track_state_change(self, transition_info: StateTransitionInfo):
        """Track state change callbacks for race condition analysis."""
        self.callback_invocations.append({'timestamp': time.time(), 'from_state': transition_info.from_state.value, 'to_state': transition_info.to_state.value, 'reason': transition_info.reason, 'thread_id': threading.get_ident()})

    def _record_race_event(self, event_type: str, thread_id: int, state_before: Optional[ApplicationConnectionState], state_after: Optional[ApplicationConnectionState], success: bool, error: Optional[str]=None, metadata: Optional[Dict[str, Any]]=None):
        """Record race condition event for analysis."""
        event = RaceConditionEvent(timestamp=time.time(), event_type=event_type, thread_id=thread_id, state_before=state_before, state_after=state_after, success=success, error=error, metadata=metadata)
        self.race_events.append(event)

    def test_concurrent_state_transitions_race_condition(self):
        """
        Test 1: Concurrent state transitions causing invalid final states.
        
        CRITICAL: This test reproduces race conditions where multiple threads
        attempt state transitions simultaneously, causing state corruption.
        
        Expected Race Condition: Multiple threads transition through states
        simultaneously, resulting in invalid final states or transition validation bypassed.
        """

        def concurrent_transition_worker(worker_id: int):
            """Worker function that attempts state transitions concurrently."""
            thread_id = threading.get_ident()
            try:
                self.start_barrier.wait(timeout=5.0)
                state_before = self.state_machine.current_state
                transitions = [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
                for i, target_state in enumerate(transitions):
                    if i > 0:
                        time.sleep(0.001 * (worker_id % 3))
                    success = self.state_machine.transition_to(target_state, reason=f'Worker {worker_id} transition {i}', metadata={'worker_id': worker_id, 'transition_index': i})
                    current_state = self.state_machine.current_state
                    self._record_race_event(event_type='state_transition', thread_id=thread_id, state_before=state_before, state_after=current_state, success=success, metadata={'worker_id': worker_id, 'target_state': target_state.value, 'transition_index': i})
                    state_before = current_state
                    if not success and current_state != ApplicationConnectionState.FAILED:
                        self.transition_violations.append(f'Worker {worker_id}: Transition to {target_state} failed but state machine in {current_state} (not FAILED)')
                        self.race_condition_detected.set()
            except Exception as e:
                self._record_race_event(event_type='worker_exception', thread_id=thread_id, state_before=None, state_after=self.state_machine.current_state, success=False, error=str(e), metadata={'worker_id': worker_id})
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=concurrent_transition_worker, args=(worker_id,), name=f'RaceWorker-{worker_id}')
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)
        successful_transitions = [e for e in self.race_events if e.success]
        failed_transitions = [e for e in self.race_events if not e.success]
        worker_exceptions = [e for e in self.race_events if e.event_type == 'worker_exception']
        final_state = self.state_machine.current_state
        state_history = self.state_machine.get_state_history()
        if len(set((e.thread_id for e in self.race_events))) < 3:
            self.state_inconsistencies.append(f'Insufficient concurrent execution - only {len(set((e.thread_id for e in self.race_events)))} threads')
        invalid_transitions = []
        for event in self.race_events:
            if event.success and event.state_before and event.state_after:
                if not self._is_valid_state_transition(event.state_before, event.state_after):
                    invalid_transitions.append(f'Invalid transition: {event.state_before} -> {event.state_after}')
        print(f'\n=== RACE CONDITION ANALYSIS ===')
        print(f'Total race events: {len(self.race_events)}')
        print(f'Successful transitions: {len(successful_transitions)}')
        print(f'Failed transitions: {len(failed_transitions)}')
        print(f'Worker exceptions: {len(worker_exceptions)}')
        print(f'Final state: {final_state}')
        print(f'State history length: {len(state_history)}')
        print(f'Transition violations: {len(self.transition_violations)}')
        print(f'Invalid transitions: {len(invalid_transitions)}')
        print(f'Callback invocations: {len(self.callback_invocations)}')
        race_detected = len(self.transition_violations) > 0 or len(invalid_transitions) > 0 or len(worker_exceptions) > 0 or self.race_condition_detected.is_set()
        if not race_detected:
            self.state_inconsistencies.append('CRITICAL: No race conditions detected - test may not be reproducing conditions properly')
        pytest.fail(f'Concurrent state transition race condition test completed. Race detected: {race_detected}, Violations: {len(self.transition_violations)}, Invalid transitions: {len(invalid_transitions)}, Final state: {final_state}')

    def _is_valid_state_transition(self, from_state: ApplicationConnectionState, to_state: ApplicationConnectionState) -> bool:
        """Check if state transition is valid according to state machine rules."""
        valid_transitions = {ApplicationConnectionState.CONNECTING: {ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED}, ApplicationConnectionState.ACCEPTED: {ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED}, ApplicationConnectionState.AUTHENTICATED: {ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.DEGRADED, ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED}, ApplicationConnectionState.SERVICES_READY: {ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.DEGRADED, ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED}}
        return to_state in valid_transitions.get(from_state, set())

    def test_state_transition_validation_bypass_race(self):
        """
        Test 2: State transition validation bypassed during high concurrency.
        
        This test attempts to bypass state transition validation by overwhelming
        the state machine with concurrent requests that could skip validation checks.
        """
        validation_bypasses = []
        validation_checks = []

        def validation_bypass_worker(worker_id: int):
            """Worker that attempts to bypass validation through timing."""
            thread_id = threading.get_ident()
            try:
                self.start_barrier.wait(timeout=5.0)
                invalid_transitions = [ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.CONNECTING, ApplicationConnectionState.FAILED, ApplicationConnectionState.PROCESSING]
                for target_state in invalid_transitions:
                    state_before = self.state_machine.current_state
                    success = self.state_machine.transition_to(target_state, reason=f'Validation bypass attempt {worker_id}', metadata={'bypass_attempt': True, 'worker_id': worker_id})
                    state_after = self.state_machine.current_state
                    validation_checks.append({'worker_id': worker_id, 'thread_id': thread_id, 'state_before': state_before.value, 'target_state': target_state.value, 'state_after': state_after.value, 'success': success, 'timestamp': time.time()})
                    if success and (not self._is_valid_state_transition(state_before, state_after)):
                        validation_bypasses.append({'worker_id': worker_id, 'invalid_transition': f'{state_before} -> {state_after}', 'timestamp': time.time()})
                        self.transition_violations.append(f'VALIDATION BYPASSED: {state_before} -> {state_after} by worker {worker_id}')
            except Exception as e:
                validation_checks.append({'worker_id': worker_id, 'error': str(e), 'timestamp': time.time()})
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=validation_bypass_worker, args=(worker_id,), name=f'BypassWorker-{worker_id}')
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
        successful_bypasses = len(validation_bypasses)
        total_attempts = len(validation_checks)
        unique_final_states = set((check.get('state_after') for check in validation_checks if 'state_after' in check))
        print(f'\n=== VALIDATION BYPASS ANALYSIS ===')
        print(f'Total validation attempts: {total_attempts}')
        print(f'Successful bypasses: {successful_bypasses}')
        print(f'Unique final states: {unique_final_states}')
        print(f'Transition violations: {len(self.transition_violations)}')
        if successful_bypasses > 0:
            print('CRITICAL: Validation bypasses detected!')
            for bypass in validation_bypasses:
                print(f"  - Worker {bypass['worker_id']}: {bypass['invalid_transition']}")
        pytest.fail(f'State transition validation race test completed. Bypasses detected: {successful_bypasses}, Total attempts: {total_attempts}, Violations: {len(self.transition_violations)}')

    def test_state_history_corruption_race(self):
        """
        Test 3: State history corruption during rapid transitions.
        
        This test checks if concurrent state transitions corrupt the state
        history tracking, which could lead to inconsistent connection debugging.
        """
        history_snapshots = []
        history_inconsistencies = []

        def history_corruption_worker(worker_id: int):
            """Worker that performs transitions while monitoring history."""
            thread_id = threading.get_ident()
            try:
                self.start_barrier.wait(timeout=5.0)
                transitions = [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY]
                for i, target_state in enumerate(transitions):
                    history_before = list(self.state_machine.get_state_history())
                    success = self.state_machine.transition_to(target_state, reason=f'History test worker {worker_id} step {i}', metadata={'worker_id': worker_id, 'step': i})
                    history_after = list(self.state_machine.get_state_history())
                    snapshot = {'worker_id': worker_id, 'thread_id': thread_id, 'step': i, 'target_state': target_state.value, 'success': success, 'history_before_length': len(history_before), 'history_after_length': len(history_after), 'timestamp': time.time()}
                    history_snapshots.append(snapshot)
                    if success:
                        expected_length = len(history_before) + 1
                        actual_length = len(history_after)
                        if actual_length != expected_length:
                            inconsistency = {'worker_id': worker_id, 'step': i, 'expected_length': expected_length, 'actual_length': actual_length, 'difference': actual_length - expected_length}
                            history_inconsistencies.append(inconsistency)
                    time.sleep(0.001)
            except Exception as e:
                history_snapshots.append({'worker_id': worker_id, 'error': str(e), 'timestamp': time.time()})
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=history_corruption_worker, args=(worker_id,), name=f'HistoryWorker-{worker_id}')
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
        final_history = self.state_machine.get_state_history()
        successful_snapshots = [s for s in history_snapshots if 'error' not in s]
        expected_total_transitions = sum((3 for s in successful_snapshots if s.get('success', False)))
        actual_total_transitions = len(final_history)
        print(f'\n=== HISTORY CORRUPTION ANALYSIS ===')
        print(f'Total history snapshots: {len(history_snapshots)}')
        print(f'Successful snapshots: {len(successful_snapshots)}')
        print(f'History inconsistencies: {len(history_inconsistencies)}')
        print(f'Expected total transitions: {expected_total_transitions}')
        print(f'Actual total transitions: {actual_total_transitions}')
        print(f'History length difference: {actual_total_transitions - expected_total_transitions}')
        if history_inconsistencies:
            print('History inconsistencies detected:')
            for inc in history_inconsistencies:
                print(f"  - Worker {inc['worker_id']} step {inc['step']}: expected {inc['expected_length']}, got {inc['actual_length']}")
        corruption_detected = len(history_inconsistencies) > 0 or abs(actual_total_transitions - expected_total_transitions) > 2
        pytest.fail(f'State history corruption race test completed. Corruption detected: {corruption_detected}, Inconsistencies: {len(history_inconsistencies)}, History length delta: {actual_total_transitions - expected_total_transitions}')

    def test_callback_notification_race_condition(self):
        """
        Test 4: Callback notification failures during state changes.
        
        This test verifies that state change callbacks are properly notified
        during concurrent state transitions without race conditions.
        """
        callback_errors = []
        notification_order_violations = []

        def failing_callback(transition_info: StateTransitionInfo):
            """Callback that simulates failures during concurrent notifications."""
            thread_id = threading.get_ident()
            try:
                time.sleep(0.001)
                current_time = time.time()
                if hasattr(self, '_last_callback_time'):
                    if current_time < self._last_callback_time:
                        notification_order_violations.append({'thread_id': thread_id, 'current_time': current_time, 'last_time': self._last_callback_time, 'transition': f'{transition_info.from_state} -> {transition_info.to_state}'})
                self._last_callback_time = current_time
                if len(self.callback_invocations) > 10:
                    if thread_id % 3 == 0:
                        raise Exception(f'Callback failure simulation in thread {thread_id}')
            except Exception as e:
                callback_errors.append({'thread_id': thread_id, 'error': str(e), 'transition': f'{transition_info.from_state} -> {transition_info.to_state}', 'timestamp': time.time()})
        self.state_machine.add_state_change_callback(failing_callback)

        def callback_race_worker(worker_id: int):
            """Worker that triggers state changes to test callback race conditions."""
            try:
                self.start_barrier.wait(timeout=5.0)
                for i in range(3):
                    if i == 0:
                        target_state = ApplicationConnectionState.ACCEPTED
                    elif i == 1:
                        target_state = ApplicationConnectionState.AUTHENTICATED
                    else:
                        target_state = ApplicationConnectionState.SERVICES_READY
                    self.state_machine.transition_to(target_state, reason=f'Callback race test {worker_id}-{i}', metadata={'worker_id': worker_id, 'iteration': i})
                    time.sleep(0.002)
            except Exception as e:
                callback_errors.append({'worker_id': worker_id, 'worker_error': str(e), 'timestamp': time.time()})
        self._last_callback_time = time.time()
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=callback_race_worker, args=(worker_id,), name=f'CallbackWorker-{worker_id}')
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
        total_transitions = len(self.callback_invocations)
        callback_failures = len(callback_errors)
        order_violations = len(notification_order_violations)
        print(f'\n=== CALLBACK RACE CONDITION ANALYSIS ===')
        print(f'Total callback invocations: {total_transitions}')
        print(f'Callback failures: {callback_failures}')
        print(f'Order violations: {order_violations}')
        if callback_failures > 0:
            print('Callback failures detected:')
            for error in callback_errors[:5]:
                print(f'  - {error}')
        if order_violations > 0:
            print('Notification order violations detected:')
            for violation in notification_order_violations[:3]:
                print(f'  - {violation}')
        race_detected = callback_failures > 0 or order_violations > 0
        pytest.fail(f'Callback notification race test completed. Race detected: {race_detected}, Callback failures: {callback_failures}, Order violations: {order_violations}')

    def teardown_method(self):
        """Clean up test environment."""
        print(f'\n=== RACE CONDITION TEST SUMMARY ===')
        print(f'Total race events recorded: {len(self.race_events)}')
        print(f'State inconsistencies: {len(self.state_inconsistencies)}')
        print(f'Transition violations: {len(self.transition_violations)}')
        print(f'Callback failures: {len(self.callback_failures)}')
        registry = get_connection_state_registry()
        registry.unregister_connection(self.connection_id)
        super().teardown_method()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')