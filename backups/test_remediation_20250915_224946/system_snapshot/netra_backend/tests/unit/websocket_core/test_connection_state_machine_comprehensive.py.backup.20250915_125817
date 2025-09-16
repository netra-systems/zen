"""
Comprehensive Unit Tests for WebSocket ConnectionStateMachine

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Risk Reduction for $500K+ ARR WebSocket Infrastructure
- Value Impact: Protect critical WebSocket race condition fixes that enable chat-based AI value delivery
- Strategic Impact: Prevent regression of "every 3 minutes staging failure" that blocks user interactions

CRITICAL TESTING REQUIREMENTS:
1. Tests MUST FAIL on old broken implementation (without proper state separation)
2. Tests MUST PASS on new implementation with ApplicationConnectionState management
3. Cover ALL race condition scenarios that caused production failures
4. Validate thread safety and concurrent access patterns
5. Ensure integration with existing is_websocket_connected_and_ready() function

ROOT CAUSE ADDRESSED: 
The system previously conflated "WebSocket accepted" (transport ready) with "ready to process messages" 
(fully operational). This state machine enforces proper separation and prevents race conditions.
"""
import asyncio
import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Callable, Optional
from unittest.mock import Mock, MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from shared.isolated_environment import get_env
from test_framework.base import BaseTestCase, AsyncTestCase
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, StateTransitionInfo, ConnectionStateMachine, ConnectionStateMachineRegistry, get_connection_state_registry, get_connection_state_machine, is_connection_ready_for_messages

class TestApplicationConnectionState(BaseTestCase):
    """Test ApplicationConnectionState enum and helper methods."""

    def test_state_classification_methods(self):
        """Test state classification helper methods work correctly."""
        operational_states = [ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING, ApplicationConnectionState.IDLE, ApplicationConnectionState.DEGRADED]
        for state in operational_states:
            assert ApplicationConnectionState.is_operational(state), f'{state} should be operational'
        setup_states = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY]
        for state in setup_states:
            assert ApplicationConnectionState.is_setup_phase(state), f'{state} should be setup phase'
            assert not ApplicationConnectionState.is_operational(state), f'{state} should not be operational during setup'
        terminal_states = [ApplicationConnectionState.CLOSED, ApplicationConnectionState.FAILED]
        for state in terminal_states:
            assert ApplicationConnectionState.is_terminal(state), f'{state} should be terminal'
            assert not ApplicationConnectionState.is_operational(state), f'{state} should not be operational'

    def test_state_enum_completeness(self):
        """Test that all expected states are defined and have correct values."""
        expected_states = {'connecting', 'accepted', 'authenticated', 'services_ready', 'processing_ready', 'processing', 'idle', 'degraded', 'reconnecting', 'closing', 'closed', 'failed'}
        actual_states = {state.value for state in ApplicationConnectionState}
        assert actual_states == expected_states, f'State enum mismatch: {actual_states} vs {expected_states}'

class TestConnectionStateMachineCore(BaseTestCase):
    """Test core ConnectionStateMachine functionality."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.connection_id = ConnectionID('test-connection-123')
        self.user_id = UserID('test-user-456')
        self.callbacks: Set[Callable] = set()

    def test_initialization_sets_correct_defaults(self):
        """Test that ConnectionStateMachine initializes with correct default state and settings."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id, self.callbacks)
        assert machine.current_state == ApplicationConnectionState.CONNECTING
        assert machine.connection_id == str(self.connection_id)
        assert machine.user_id == self.user_id
        assert not machine.is_operational
        assert not machine.is_ready_for_messages
        assert not machine.can_process_messages()
        metrics = machine.get_metrics()
        assert metrics['current_state'] == 'connecting'
        assert metrics['total_transitions'] == 0
        assert metrics['failed_transitions'] == 0
        assert metrics['transition_failures'] == 0
        assert 'setup_duration' in metrics
        assert 'last_activity' in metrics

    def test_valid_state_transitions_follow_defined_path(self):
        """Test that valid state transitions work correctly through the complete setup path."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        transitions = []

        def track_transition(info: StateTransitionInfo):
            transitions.append((info.from_state, info.to_state))
        machine.add_state_change_callback(track_transition)
        assert machine.transition_to(ApplicationConnectionState.ACCEPTED, 'websocket_accepted')
        assert machine.current_state == ApplicationConnectionState.ACCEPTED
        assert machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'auth_completed')
        assert machine.current_state == ApplicationConnectionState.AUTHENTICATED
        assert machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'services_initialized')
        assert machine.current_state == ApplicationConnectionState.SERVICES_READY
        assert machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'setup_complete')
        assert machine.current_state == ApplicationConnectionState.PROCESSING_READY
        assert machine.is_operational
        assert machine.is_ready_for_messages
        assert machine.can_process_messages()
        expected_transitions = [(ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED), (ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED), (ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY), (ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY)]
        assert transitions == expected_transitions
        metrics = machine.get_metrics()
        assert metrics['setup_duration_seconds'] >= 0
        assert len(metrics['setup_phases_completed']) >= 3

    def test_invalid_state_transitions_are_rejected(self):
        """Test that invalid state transitions are properly rejected with rollback."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        initial_state = machine.current_state
        initial_metrics = machine.get_metrics()
        result = machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'invalid_skip')
        assert not result
        assert machine.current_state == initial_state
        metrics = machine.get_metrics()
        assert metrics['failed_transitions'] == initial_metrics['failed_transitions'] + 1
        assert metrics['transition_failures'] == 1
        result = machine.transition_to(ApplicationConnectionState.PROCESSING, 'another_invalid')
        assert not result
        assert machine.current_state == initial_state
        metrics = machine.get_metrics()
        assert metrics['failed_transitions'] == initial_metrics['failed_transitions'] + 2
        assert metrics['transition_failures'] == 2

    def test_force_failed_state_emergency_mechanism(self):
        """Test emergency force_failed_state mechanism works correctly."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        machine.transition_to(ApplicationConnectionState.ACCEPTED)
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        assert machine.current_state == ApplicationConnectionState.AUTHENTICATED
        emergency_reason = 'Critical security breach detected'
        machine.force_failed_state(emergency_reason)
        assert machine.current_state == ApplicationConnectionState.FAILED
        assert not machine.is_operational
        assert not machine.can_process_messages()
        history = machine.get_state_history()
        emergency_transition = history[-1]
        assert emergency_transition.to_state == ApplicationConnectionState.FAILED
        assert emergency_reason in emergency_transition.reason
        assert emergency_transition.metadata.get('emergency_transition') is True
        metrics = machine.get_metrics()
        assert metrics['transition_failures'] >= 5

    def test_state_transition_history_tracking(self):
        """Test that all state transitions are properly tracked in history."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        transitions = [(ApplicationConnectionState.ACCEPTED, 'websocket_ready'), (ApplicationConnectionState.AUTHENTICATED, 'user_validated'), (ApplicationConnectionState.SERVICES_READY, 'deps_loaded'), (ApplicationConnectionState.PROCESSING_READY, 'fully_operational')]
        for target_state, reason in transitions:
            machine.transition_to(target_state, reason, {'test_metadata': True})
        history = machine.get_state_history()
        assert len(history) == len(transitions)
        for i, (expected_state, expected_reason) in enumerate(transitions):
            transition_info = history[i]
            assert transition_info.to_state == expected_state
            assert transition_info.reason == expected_reason
            assert transition_info.metadata.get('test_metadata') is True
            assert isinstance(transition_info.timestamp, datetime)

    def test_callback_notification_system(self):
        """Test that state change callbacks are properly notified."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        callback_calls = []

        def callback1(info: StateTransitionInfo):
            callback_calls.append(('callback1', info.from_state, info.to_state))

        def callback2(info: StateTransitionInfo):
            callback_calls.append(('callback2', info.from_state, info.to_state))
        machine.add_state_change_callback(callback1)
        machine.add_state_change_callback(callback2)
        machine.transition_to(ApplicationConnectionState.ACCEPTED, 'test_transition')
        assert len(callback_calls) == 2
        assert ('callback1', ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED) in callback_calls
        assert ('callback2', ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED) in callback_calls
        machine.remove_state_change_callback(callback1)
        callback_calls.clear()
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'auth_done')
        assert len(callback_calls) == 1
        assert callback_calls[0] == ('callback2', ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED)

class TestConnectionStateMachineRaceConditions(AsyncTestCase):
    """Test race condition scenarios that the state machine prevents."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.connection_id = ConnectionID('race-test-connection')
        self.user_id = UserID('race-test-user')

    @pytest.mark.asyncio
    async def test_concurrent_transition_race_condition_reproduction(self):
        """
        CRITICAL: Test concurrent state transitions that caused the $500K+ staging failures.
        
        This test reproduces the exact race condition where multiple components
        tried to transition the connection state simultaneously, leading to inconsistent state.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        transition_results = []
        state_conflicts = []

        def track_state_conflicts(info: StateTransitionInfo):
            current_time = time.time()
            state_conflicts.append((current_time, info.from_state, info.to_state))
        machine.add_state_change_callback(track_state_conflicts)

        async def attempt_transition(target_state: ApplicationConnectionState, reason: str, delay: float=0):
            """Attempt a state transition with optional delay to create race windows."""
            if delay > 0:
                await asyncio.sleep(delay)
            result = machine.transition_to(target_state, reason)
            transition_results.append((target_state, reason, result, time.time()))
            return result
        tasks = [attempt_transition(ApplicationConnectionState.ACCEPTED, 'websocket_accepted', 0.001), attempt_transition(ApplicationConnectionState.AUTHENTICATED, 'auth_completed', 0.002), attempt_transition(ApplicationConnectionState.SERVICES_READY, 'services_ready', 0.003), attempt_transition(ApplicationConnectionState.PROCESSING_READY, 'all_ready', 0.004)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_transitions = [r for r in transition_results if r[2] is True]
        failed_transitions = [r for r in transition_results if r[2] is False]
        assert len(successful_transitions) > 0, 'At least some transitions should succeed'
        final_state = machine.current_state
        assert final_state in [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY], f'Final state {final_state} should be a valid progression state'
        history = machine.get_state_history()
        for i in range(1, len(history)):
            prev_transition = history[i - 1]
            curr_transition = history[i]
            assert machine._is_valid_transition(prev_transition.to_state, curr_transition.to_state), f'Invalid transition detected in history: {prev_transition.to_state} -> {curr_transition.to_state}'
        self.record_metric('concurrent_transitions_attempted', len(tasks))
        self.record_metric('successful_transitions', len(successful_transitions))
        self.record_metric('failed_transitions', len(failed_transitions))
        self.record_metric('final_state', final_state.value)

    @pytest.mark.asyncio
    async def test_processing_ready_vs_transport_ready_race(self):
        """
        CRITICAL: Test the core race that caused staging failures.
        
        This reproduces the exact issue where WebSocket transport was ready
        but application processing was not ready, leading to "Need to call 'accept' first" errors.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        assert machine.transition_to(ApplicationConnectionState.ACCEPTED, 'transport_ready')
        assert machine.current_state == ApplicationConnectionState.ACCEPTED
        assert not machine.is_ready_for_messages
        assert not machine.can_process_messages()
        race_condition_window_start = time.time()

        async def simulate_message_processing_attempt():
            """Simulate message processing during the race window - should fail."""
            if machine.can_process_messages():
                return {'status': 'processed', 'error': None}
            else:
                return {'status': 'failed', 'error': 'Connection not ready for message processing'}

        async def simulate_application_setup():
            """Simulate application setup completing."""
            await asyncio.sleep(0.005)
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'auth_complete')
            await asyncio.sleep(0.005)
            machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'services_loaded')
            await asyncio.sleep(0.005)
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'app_ready')
            return {'status': 'setup_complete'}
        message_result, setup_result = await asyncio.gather(simulate_message_processing_attempt(), simulate_application_setup())
        race_condition_window_end = time.time()
        race_window_duration = race_condition_window_end - race_condition_window_start
        assert message_result['status'] == 'failed', 'Message processing should fail during race window'
        assert 'not ready' in message_result['error'], 'Error should indicate connection not ready'
        assert setup_result['status'] == 'setup_complete'
        assert machine.current_state == ApplicationConnectionState.PROCESSING_READY
        assert machine.is_ready_for_messages
        assert machine.can_process_messages()
        self.record_metric('race_window_duration_ms', race_window_duration * 1000)
        self.record_metric('transport_ready_state', 'ACCEPTED')
        self.record_metric('processing_ready_prevented_race', True)

    @pytest.mark.asyncio
    async def test_staging_three_minute_failure_reproduction(self):
        """
        CRITICAL: Reproduce the exact "every 3 minutes staging failure" pattern.
        
        This test simulates the specific timing and load patterns that caused
        regular failures in the staging environment every ~3 minutes.
        """
        machines = []
        failure_count = 0
        success_count = 0
        connection_count = 10
        for i in range(connection_count):
            conn_id = ConnectionID(f'staging-conn-{i}')
            user_id = UserID(f'staging-user-{i}')
            machine = ConnectionStateMachine(conn_id, user_id)
            machines.append(machine)

        async def simulate_staging_connection_setup(machine: ConnectionStateMachine, setup_delay: float):
            """Simulate the staging connection setup process with realistic timing."""
            try:
                machine.transition_to(ApplicationConnectionState.ACCEPTED, 'websocket_accepted')
                await asyncio.sleep(setup_delay * 0.3)
                if not machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'auth_validated'):
                    raise Exception('Auth transition failed')
                await asyncio.sleep(setup_delay * 0.6)
                if not machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'services_initialized'):
                    raise Exception('Services transition failed')
                await asyncio.sleep(setup_delay * 0.1)
                if not machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'fully_ready'):
                    raise Exception('Final readiness transition failed')
                if not machine.can_process_messages():
                    raise Exception('Machine not ready for message processing after setup')
                return {'connection_id': machine.connection_id, 'status': 'success', 'setup_time': setup_delay}
            except Exception as e:
                return {'connection_id': machine.connection_id, 'status': 'failed', 'error': str(e)}
        setup_tasks = []
        for i, machine in enumerate(machines):
            start_delay = i * 0.01
            base_setup_time = 0.01
            variance = random.uniform(0.5, 2.0)
            setup_delay = base_setup_time * variance

            async def delayed_setup(delay, mach, sdelay):
                await asyncio.sleep(delay)
                return await simulate_staging_connection_setup(mach, sdelay)
            task = asyncio.create_task(delayed_setup(start_delay, machine, setup_delay))
            setup_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*setup_tasks, return_exceptions=True)
        end_time = time.time()
        total_duration = end_time - start_time
        for result in results:
            if isinstance(result, Exception):
                failure_count += 1
            elif isinstance(result, dict) and result.get('status') == 'failed':
                failure_count += 1
            else:
                success_count += 1
        failure_rate = failure_count / connection_count
        success_rate = success_count / connection_count
        assert failure_rate < 0.2, f'Failure rate too high: {failure_rate:.2%} (expected < 20%)'
        assert success_rate > 0.8, f'Success rate too low: {success_rate:.2%} (expected > 80%)'
        successful_machines = [m for m in machines if m.current_state == ApplicationConnectionState.PROCESSING_READY]
        assert len(successful_machines) >= max(1, success_count - 2), 'State machine count should be close to success count'
        self.record_metric('total_connections', connection_count)
        self.record_metric('success_count', success_count)
        self.record_metric('failure_count', failure_count)
        self.record_metric('success_rate', success_rate)
        self.record_metric('failure_rate', failure_rate)
        self.record_metric('total_duration_seconds', total_duration)
        self.record_metric('staging_pattern_reproduced', True)

    def test_high_load_state_corruption_scenario(self):
        """
        Test state machine integrity under high concurrent load.
        
        This test ensures that the state machine maintains data integrity
        even when under heavy concurrent access pressure.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        corruption_detected = False
        state_snapshots = []

        def capture_state_snapshot():
            """Capture current state for corruption analysis."""
            snapshot = {'current_state': machine.current_state, 'is_operational': machine.is_operational, 'is_ready': machine.is_ready_for_messages, 'can_process': machine.can_process_messages(), 'metrics': machine.get_metrics(), 'timestamp': time.time()}
            state_snapshots.append(snapshot)
            return snapshot

        def concurrent_state_accessor():
            """Simulate concurrent state access from multiple threads."""
            for _ in range(100):
                try:
                    state = machine.current_state
                    operational = machine.is_operational
                    ready = machine.is_ready_for_messages
                    can_process = machine.can_process_messages()
                    metrics = machine.get_metrics()
                    if state == ApplicationConnectionState.PROCESSING_READY:
                        if not (operational and ready and can_process):
                            nonlocal corruption_detected
                            corruption_detected = True
                    time.sleep(0.001)
                except Exception as e:
                    corruption_detected = True

        def concurrent_state_transitioner():
            """Simulate concurrent state transitions."""
            for i in range(50):
                try:
                    if machine.current_state == ApplicationConnectionState.CONNECTING:
                        machine.transition_to(ApplicationConnectionState.ACCEPTED, f'transition_{i}')
                    elif machine.current_state == ApplicationConnectionState.ACCEPTED:
                        machine.transition_to(ApplicationConnectionState.AUTHENTICATED, f'transition_{i}')
                    elif machine.current_state == ApplicationConnectionState.AUTHENTICATED:
                        machine.transition_to(ApplicationConnectionState.SERVICES_READY, f'transition_{i}')
                    elif machine.current_state == ApplicationConnectionState.SERVICES_READY:
                        machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f'transition_{i}')
                    time.sleep(0.002)
                except Exception as e:
                    corruption_detected = True
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for _ in range(4):
                futures.append(executor.submit(concurrent_state_accessor))
            for _ in range(2):
                futures.append(executor.submit(concurrent_state_transitioner))
            for _ in range(10):
                futures.append(executor.submit(capture_state_snapshot))
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    corruption_detected = True
        end_time = time.time()
        duration = end_time - start_time
        assert not corruption_detected, 'State machine corruption detected under concurrent load'
        final_state = machine.current_state
        final_metrics = machine.get_metrics()
        assert final_state in ApplicationConnectionState, f'Invalid final state: {final_state}'
        if ApplicationConnectionState.is_operational(final_state):
            assert machine.is_operational, 'Operational state mismatch'
        if final_state in [ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING, ApplicationConnectionState.IDLE, ApplicationConnectionState.DEGRADED]:
            assert machine.is_ready_for_messages, 'Message readiness mismatch'
        self.record_metric('high_load_duration_seconds', duration)
        self.record_metric('state_snapshots_captured', len(state_snapshots))
        self.record_metric('corruption_detected', corruption_detected)
        self.record_metric('final_state', final_state.value)
        self.record_metric('concurrent_threads', 8)

    @pytest.mark.asyncio
    async def test_callback_notification_race_conditions(self):
        """
        Test callback notification system under race conditions.
        
        Ensures that callback notifications are delivered reliably even
        when state transitions happen rapidly and concurrently.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        callback_invocations = []
        callback_errors = []

        def callback_fast(info: StateTransitionInfo):
            """Fast callback that completes quickly."""
            callback_invocations.append(('fast', info.from_state, info.to_state, time.time()))

        def callback_slow(info: StateTransitionInfo):
            """Slow callback that takes time to process."""
            time.sleep(0.01)
            callback_invocations.append(('slow', info.from_state, info.to_state, time.time()))

        def callback_error_prone(info: StateTransitionInfo):
            """Callback that sometimes throws errors."""
            if random.random() < 0.3:
                callback_errors.append(('error', info.from_state, info.to_state))
                raise Exception('Simulated callback error')
            callback_invocations.append(('error_prone', info.from_state, info.to_state, time.time()))
        machine.add_state_change_callback(callback_fast)
        machine.add_state_change_callback(callback_slow)
        machine.add_state_change_callback(callback_error_prone)

        async def rapid_transitions():
            """Execute rapid state transitions."""
            transitions = [ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY]
            for i, state in enumerate(transitions):
                success = machine.transition_to(state, f'rapid_transition_{i}')
                if success:
                    await asyncio.sleep(0.001)
            return len([t for t in transitions if machine.current_state != ApplicationConnectionState.CONNECTING])
        start_time = time.time()
        transitions_completed = await rapid_transitions()
        end_time = time.time()
        duration = end_time - start_time
        await asyncio.sleep(0.1)
        total_expected_invocations = transitions_completed * 3
        total_actual_invocations = len(callback_invocations)
        total_callback_errors = len(callback_errors)
        success_rate = total_actual_invocations / (total_expected_invocations - total_callback_errors)
        assert success_rate > 0.8, f'Callback success rate too low: {success_rate:.2%}'
        fast_callbacks = [c for c in callback_invocations if c[0] == 'fast']
        if len(fast_callbacks) > 1:
            for i in range(1, len(fast_callbacks)):
                prev_time = fast_callbacks[i - 1][3]
                curr_time = fast_callbacks[i][3]
                assert curr_time >= prev_time, 'Callback ordering violated'
        self.record_metric('transitions_completed', transitions_completed)
        self.record_metric('callback_invocations', total_actual_invocations)
        self.record_metric('callback_errors', total_callback_errors)
        self.record_metric('callback_success_rate', success_rate)
        self.record_metric('rapid_transition_duration_ms', duration * 1000)

    def test_transition_failure_rollback_races(self):
        """
        Test rollback mechanism under race conditions.
        
        Ensures that when transitions fail, the rollback mechanism
        works correctly even under concurrent access.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        machine.transition_to(ApplicationConnectionState.ACCEPTED)
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        initial_state = machine.current_state
        rollback_attempts = []

        def attempt_invalid_transition_with_rollback():
            """Attempt invalid transitions to trigger rollback."""
            try:
                original_state = machine.current_state
                result = machine.transition_to(ApplicationConnectionState.CLOSED, 'invalid_direct_close')
                rollback_attempts.append({'original_state': original_state, 'attempted_state': ApplicationConnectionState.CLOSED, 'result': result, 'final_state': machine.current_state, 'timestamp': time.time()})
                return result
            except Exception as e:
                rollback_attempts.append({'error': str(e), 'timestamp': time.time()})
                return False
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_invalid_transition_with_rollback) for _ in range(10)]
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(False)
        failed_results = [r for r in results if not r]
        assert len(failed_results) >= len(results) // 2, f'At least half of invalid transitions should fail, got {len(failed_results)}/{len(results)}'
        final_state = machine.current_state
        valid_final_states = [ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.CLOSED, ApplicationConnectionState.FAILED]
        assert final_state in valid_final_states, f'Final state {final_state} should be valid after rollback attempts'
        if ApplicationConnectionState.is_terminal(final_state):
            assert not machine.is_operational, 'Terminal states should not be operational'
        else:
            expected_operational = ApplicationConnectionState.is_operational(final_state)
            assert machine.is_operational == expected_operational, f'Operational status mismatch for state {final_state}'
        metrics = machine.get_metrics()
        assert metrics['failed_transitions'] > 0, 'Failed transitions should be recorded'
        self.record_metric('rollback_attempts', len(rollback_attempts))
        self.record_metric('final_state_after_rollbacks', final_state.value)
        self.record_metric('state_integrity_maintained', True)

class TestConnectionStateMachineSSotIntegration(BaseTestCase):
    """Test integration with existing SSOT functions and patterns."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.connection_id = ConnectionID('ssot-test-connection')
        self.user_id = UserID('ssot-test-user')

    def test_integration_with_is_websocket_connected_and_ready_function(self):
        """
        Test integration with existing is_websocket_connected_and_ready() function.
        
        This ensures the state machine enhances but doesn't break existing functionality.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        registry = get_connection_state_registry()
        registered_machine = registry.register_connection(self.connection_id, self.user_id)
        machine = registered_machine
        assert not is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.ACCEPTED)
        assert not is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        assert not is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.SERVICES_READY)
        assert not is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        assert is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.DEGRADED)
        assert is_connection_ready_for_messages(self.connection_id)
        machine.transition_to(ApplicationConnectionState.CLOSING)
        assert not is_connection_ready_for_messages(self.connection_id)

    def test_registry_pattern_validation(self):
        """Test the ConnectionStateMachineRegistry follows SSOT patterns."""
        registry = get_connection_state_registry()
        registry2 = get_connection_state_registry()
        assert registry is registry2, 'Registry should be singleton'
        machine = registry.register_connection(self.connection_id, self.user_id)
        assert isinstance(machine, ConnectionStateMachine)
        assert machine.connection_id == str(self.connection_id)
        assert machine.user_id == self.user_id
        retrieved_machine = registry.get_connection_state_machine(self.connection_id)
        assert retrieved_machine is machine, 'Should retrieve same machine instance'
        machine2 = registry.register_connection(self.connection_id, self.user_id)
        assert machine2 is machine, 'Duplicate registration should return existing machine'
        stats = registry.get_registry_stats()
        assert stats['total_connections'] >= 1
        assert 'state_distribution' in stats
        assert 'operational_connections' in stats
        machine.transition_to(ApplicationConnectionState.ACCEPTED)
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        machine.transition_to(ApplicationConnectionState.SERVICES_READY)
        machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        operational = registry.get_all_operational_connections()
        if machine.is_operational:
            assert str(self.connection_id) in operational
        else:
            assert str(self.connection_id) not in operational
        machine.force_failed_state('test cleanup')
        cleanup_count = registry.cleanup_closed_connections()
        assert cleanup_count >= 1, 'Should clean up failed connections'

    def test_connection_state_machine_lifecycle(self):
        """Test complete connection lifecycle following SSOT patterns."""
        registry = get_connection_state_registry()
        machine = registry.register_connection(self.connection_id, self.user_id)
        lifecycle_events = []

        def track_lifecycle(info: StateTransitionInfo):
            lifecycle_events.append({'from': info.from_state.value, 'to': info.to_state.value, 'reason': info.reason, 'timestamp': info.timestamp})
        machine.add_state_change_callback(track_lifecycle)
        setup_transitions = [(ApplicationConnectionState.ACCEPTED, 'websocket_handshake_complete'), (ApplicationConnectionState.AUTHENTICATED, 'jwt_validation_success'), (ApplicationConnectionState.SERVICES_READY, 'dependencies_loaded'), (ApplicationConnectionState.PROCESSING_READY, 'setup_complete')]
        for target_state, reason in setup_transitions:
            current_state_before = machine.current_state
            success = machine.transition_to(target_state, reason)
            if not success:
                print(f'Failed transition from {current_state_before} to {target_state}: {reason}')
                print(f'Machine metrics: {machine.get_metrics()}')
            assert success, f'Setup transition from {current_state_before} to {target_state} should succeed: {reason}'
        assert machine.is_operational
        assert machine.can_process_messages()
        machine.transition_to(ApplicationConnectionState.PROCESSING, 'message_received')
        machine.transition_to(ApplicationConnectionState.IDLE, 'message_processed')
        machine.transition_to(ApplicationConnectionState.PROCESSING, 'another_message')
        machine.transition_to(ApplicationConnectionState.CLOSING, 'user_disconnect')
        machine.transition_to(ApplicationConnectionState.CLOSED, 'cleanup_complete')
        expected_transitions = len(setup_transitions) + 4
        assert len(lifecycle_events) >= expected_transitions, f'Expected at least {expected_transitions} transitions, got {len(lifecycle_events)}'
        assert not machine.is_operational
        assert not machine.can_process_messages()
        cleanup_count = registry.cleanup_closed_connections()
        assert cleanup_count >= 1
        retrieved = registry.get_connection_state_machine(self.connection_id)
        assert retrieved is None, 'Connection should be cleaned up'

    def test_error_handling_and_recovery_patterns(self):
        """Test error handling and recovery following SSOT patterns."""
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        machine.transition_to(ApplicationConnectionState.ACCEPTED)
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED)
        machine.transition_to(ApplicationConnectionState.SERVICES_READY)
        machine.transition_to(ApplicationConnectionState.PROCESSING_READY)
        machine.transition_to(ApplicationConnectionState.DEGRADED, 'service_unavailable')
        assert machine.is_operational
        assert machine.is_ready_for_messages
        can_process = machine.can_process_messages()
        machine.transition_to(ApplicationConnectionState.RECONNECTING, 'attempting_recovery')
        assert not machine.is_operational
        machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'services_restored')
        machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'recovery_complete')
        assert machine.is_operational
        assert machine.can_process_messages()
        machine.force_failed_state('unrecoverable_error')
        assert machine.current_state == ApplicationConnectionState.FAILED
        assert not machine.is_operational
        assert not machine.can_process_messages()
        retry_machine = ConnectionStateMachine(ConnectionID('retry-test'), UserID('retry-user'))
        retry_machine.force_failed_state('test_failure')
        retry_success = retry_machine.transition_to(ApplicationConnectionState.CONNECTING, 'retry_attempt')

class TestConnectionStateMachineBusinessValue(BaseTestCase):
    """Test business value validation scenarios."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.connection_id = ConnectionID('business-test-connection')
        self.user_id = UserID('business-test-user')

    def test_message_processing_readiness_validation(self):
        """
        Test message processing readiness validation for business value delivery.
        
        This ensures that the state machine prevents messages from being processed
        before the connection is fully ready, which directly impacts user experience.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        business_critical_messages = [{'type': 'user_chat_message', 'content': 'Help me analyze this data'}, {'type': 'agent_execution_request', 'agent': 'data_analysis', 'priority': 'high'}, {'type': 'tool_execution', 'tool': 'database_query', 'sensitivity': 'high'}]

        def attempt_message_processing(message: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate message processing with business value validation."""
            if not machine.can_process_messages():
                return {'status': 'rejected', 'reason': 'connection_not_ready', 'business_impact': 'user_experience_degraded', 'message_type': message.get('type')}
            return {'status': 'processed', 'business_impact': 'user_value_delivered', 'message_type': message.get('type'), 'processing_time': 0.1}
        readiness_scenarios = [(ApplicationConnectionState.CONNECTING, 'initial_connection'), (ApplicationConnectionState.ACCEPTED, 'transport_ready'), (ApplicationConnectionState.AUTHENTICATED, 'security_ready'), (ApplicationConnectionState.SERVICES_READY, 'business_logic_ready'), (ApplicationConnectionState.PROCESSING_READY, 'fully_operational')]
        processing_results = []
        for target_state, scenario_description in readiness_scenarios:
            if target_state != ApplicationConnectionState.CONNECTING:
                machine.transition_to(target_state, scenario_description)
            scenario_results = []
            for message in business_critical_messages:
                result = attempt_message_processing(message)
                result['connection_state'] = machine.current_state.value
                result['scenario'] = scenario_description
                scenario_results.append(result)
            processing_results.extend(scenario_results)
        rejected_before_ready = [r for r in processing_results if r['status'] == 'rejected' and r['connection_state'] != 'processing_ready']
        processed_when_ready = [r for r in processing_results if r['status'] == 'processed' and r['connection_state'] == 'processing_ready']
        assert len(rejected_before_ready) > 0, 'Messages should be rejected before connection is fully ready'
        assert len(processed_when_ready) == len(business_critical_messages), 'All messages should be processed when connection is fully ready'
        premature_processing = [r for r in processing_results if r['status'] == 'processed' and r['connection_state'] != 'processing_ready']
        assert len(premature_processing) == 0, f'No business-critical messages should be processed prematurely: {premature_processing}'
        self.record_metric('total_message_attempts', len(processing_results))
        self.record_metric('rejected_before_ready', len(rejected_before_ready))
        self.record_metric('processed_when_ready', len(processed_when_ready))
        self.record_metric('premature_processing_prevented', len(premature_processing) == 0)

    def test_setup_duration_tracking_for_performance_slas(self):
        """
        Test setup duration tracking for performance SLA compliance.
        
        Business value: Ensures connection setup times meet performance SLAs
        required for good user experience and customer satisfaction.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        sla_targets = {'max_setup_duration_seconds': 5.0, 'target_setup_duration_seconds': 2.0, 'critical_setup_duration_seconds': 10.0}
        setup_start_time = time.time()
        setup_phases = [(ApplicationConnectionState.ACCEPTED, 0.1, 'websocket_handshake'), (ApplicationConnectionState.AUTHENTICATED, 0.5, 'jwt_validation'), (ApplicationConnectionState.SERVICES_READY, 1.0, 'service_loading'), (ApplicationConnectionState.PROCESSING_READY, 0.2, 'final_checks')]
        phase_durations = []
        for target_state, phase_duration, phase_name in setup_phases:
            phase_start = time.time()
            time.sleep(phase_duration * 0.1)
            success = machine.transition_to(target_state, phase_name)
            assert success, f'Setup phase {phase_name} should succeed'
            phase_end = time.time()
            actual_phase_duration = phase_end - phase_start
            phase_durations.append({'phase': phase_name, 'target_duration': phase_duration, 'actual_duration': actual_phase_duration, 'state': target_state.value})
        setup_end_time = time.time()
        final_metrics = machine.get_metrics()
        total_setup_duration = final_metrics['setup_duration_seconds']
        meets_critical_sla = total_setup_duration < sla_targets['critical_setup_duration_seconds']
        meets_max_sla = total_setup_duration < sla_targets['max_setup_duration_seconds']
        meets_target_sla = total_setup_duration < sla_targets['target_setup_duration_seconds']
        assert meets_critical_sla, f"Setup duration {total_setup_duration:.3f}s exceeds critical SLA {sla_targets['critical_setup_duration_seconds']}s"
        assert machine.can_process_messages(), 'Machine should be ready for messages after setup'
        assert machine.is_operational, 'Machine should be operational after setup'
        setup_efficiency = sla_targets['target_setup_duration_seconds'] / max(total_setup_duration, 0.001)
        performance_grade = 'A' if meets_target_sla else 'B' if meets_max_sla else 'C' if meets_critical_sla else 'F'
        self.record_metric('setup_duration_seconds', total_setup_duration)
        self.record_metric('meets_target_sla', meets_target_sla)
        self.record_metric('meets_max_sla', meets_max_sla)
        self.record_metric('meets_critical_sla', meets_critical_sla)
        self.record_metric('setup_efficiency_ratio', setup_efficiency)
        self.record_metric('performance_grade', performance_grade)
        self.record_metric('phase_durations', phase_durations)
        setup_phases_completed = final_metrics['setup_phases_completed']
        expected_phases = ['accepted', 'authenticated', 'services_ready', 'processing_ready']
        assert len(setup_phases_completed) >= 3, f'Should have completed at least 3 setup phases, got: {setup_phases_completed}'

    def test_graceful_degradation_scenarios(self):
        """
        Test graceful degradation scenarios that preserve business value.
        
        Business value: Ensures the system continues to provide value even
        when some services are unavailable, rather than failing completely.
        """
        machine = ConnectionStateMachine(self.connection_id, self.user_id)
        machine.transition_to(ApplicationConnectionState.ACCEPTED, 'normal_setup')
        machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'normal_setup')
        machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'normal_setup')
        machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'normal_setup')
        assert machine.can_process_messages(), 'Should be fully operational initially'
        degradation_scenarios = [{'name': 'llm_service_unavailable', 'reason': 'LLM service temporarily unavailable', 'impact': 'reduced_ai_capabilities', 'can_process_basic': True, 'can_process_ai': False}, {'name': 'database_readonly', 'reason': 'Database in read-only mode', 'impact': 'no_data_writes', 'can_process_basic': True, 'can_process_ai': True}, {'name': 'auth_service_slow', 'reason': 'Auth service experiencing high latency', 'impact': 'slower_auth_operations', 'can_process_basic': True, 'can_process_ai': True}]
        degradation_results = []
        for scenario in degradation_scenarios:
            machine.transition_to(ApplicationConnectionState.DEGRADED, scenario['reason'])
            basic_message_result = self._simulate_basic_message_processing(machine)
            ai_message_result = self._simulate_ai_message_processing(machine, scenario)
            scenario_result = {'scenario_name': scenario['name'], 'machine_operational': machine.is_operational, 'machine_ready': machine.is_ready_for_messages, 'can_process_messages': machine.can_process_messages(), 'basic_processing': basic_message_result, 'ai_processing': ai_message_result, 'business_continuity': basic_message_result['success'] or ai_message_result['success']}
            degradation_results.append(scenario_result)
            assert machine.is_operational, f"Should remain operational in degraded mode: {scenario['name']}"
            assert machine.is_ready_for_messages, f"Should remain ready for messages: {scenario['name']}"
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"recovery_from_{scenario['name']}")
            assert machine.can_process_messages(), f"Should recover full capability: {scenario['name']}"
        scenarios_with_continuity = [r for r in degradation_results if r['business_continuity']]
        continuity_rate = len(scenarios_with_continuity) / len(degradation_scenarios)
        assert continuity_rate >= 0.8, f'Business continuity rate too low: {continuity_rate:.1%}'
        scenarios_with_basic_function = [r for r in degradation_results if r['basic_processing']['success']]
        basic_function_rate = len(scenarios_with_basic_function) / len(degradation_scenarios)
        assert basic_function_rate >= 0.9, f'Basic function availability too low: {basic_function_rate:.1%}'
        self.record_metric('degradation_scenarios_tested', len(degradation_scenarios))
        self.record_metric('business_continuity_rate', continuity_rate)
        self.record_metric('basic_function_availability_rate', basic_function_rate)
        self.record_metric('degradation_results', degradation_results)

    def _simulate_basic_message_processing(self, machine: ConnectionStateMachine) -> Dict[str, Any]:
        """Simulate basic message processing that should work even in degraded mode."""
        if not machine.is_ready_for_messages:
            return {'success': False, 'reason': 'not_ready', 'business_impact': 'service_unavailable'}
        return {'success': True, 'message_type': 'basic_text', 'business_impact': 'basic_communication_maintained', 'degraded_mode': machine.current_state == ApplicationConnectionState.DEGRADED}

    def _simulate_ai_message_processing(self, machine: ConnectionStateMachine, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate AI message processing that might be affected in degraded mode."""
        if not machine.can_process_messages():
            return {'success': False, 'reason': 'cannot_process', 'business_impact': 'ai_features_unavailable'}
        ai_available = scenario.get('can_process_ai', False)
        if machine.current_state == ApplicationConnectionState.DEGRADED and (not ai_available):
            return {'success': False, 'message_type': 'ai_request', 'reason': 'ai_service_degraded', 'business_impact': 'ai_features_temporarily_unavailable'}
        return {'success': True, 'message_type': 'ai_request', 'business_impact': 'full_ai_capabilities_available', 'degraded_mode': machine.current_state == ApplicationConnectionState.DEGRADED}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')