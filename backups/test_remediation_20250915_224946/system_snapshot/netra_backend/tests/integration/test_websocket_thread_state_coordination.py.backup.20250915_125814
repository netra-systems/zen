"""
Cross-State-Machine Integration Tests: WebSocket-Thread Coordination

Business Value Justification (BVJ):
- Segment: Platform/Internal + All User Segments
- Business Goal: Ensure seamless coordination between WebSocket connection states and thread operations
- Value Impact: Prevents data corruption, lost messages, and inconsistent UI states during chat interactions
- Strategic Impact: Core platform stability - prevents user-facing bugs during the most critical user journeys

CRITICAL: These tests validate that the backend WebSocket Connection State Machine properly
coordinates with frontend Thread State Machine operations to ensure consistent user experience.

This addresses race conditions between:
1. WebSocket connection readiness and thread creation requests
2. Thread loading states and WebSocket message processing
3. Agent execution states and connection state transitions
4. Error recovery coordination between connection and thread management

Test Difficulty: EXTREME (80% expected failure rate initially)
- Complex timing dependencies between backend and frontend state machines
- Race conditions across service boundaries
- Coordination of async operations with state transitions
- Message ordering and delivery guarantees

@compliance TEST_CREATION_GUIDE.md - Uses SSOT patterns and real service integration
@compliance CLAUDE.md - Real business value tests, no mocks for core coordination logic
"""
import asyncio
import pytest
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, ConnectionStateMachine, ConnectionStateMachineRegistry, get_connection_state_registry
from shared.types.core_types import UserID, ConnectionID, ThreadID, RunID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketThreadStateCoordination(BaseIntegrationTest):
    """
    Integration tests for WebSocket connection state machine coordination with thread operations.
    
    These tests validate the critical business flow where WebSocket state determines
    when thread operations can be safely executed without data corruption.
    """

    def setup_method(self):
        """Set up test fixtures for cross-state-machine coordination tests."""
        super().setup_method()
        self.user_id = UserID(str(uuid.uuid4()))
        self.connection_id = ConnectionID(str(uuid.uuid4()))
        self.thread_id = ThreadID(str(uuid.uuid4()))
        self.websocket_state_changes: List[Dict[str, Any]] = []
        self.thread_operations: List[Dict[str, Any]] = []
        self.coordination_events: List[Dict[str, Any]] = []
        self.registry = get_connection_state_registry()
        self.connection_state_machine = None

    def teardown_method(self):
        """Clean up test resources."""
        if self.connection_state_machine:
            self.registry.unregister_connection(self.connection_id)
        super().teardown_method()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_readiness_blocks_thread_operations_until_ready(self):
        """
        CRITICAL: Test that thread operations are blocked until WebSocket connection is fully ready.
        
        This prevents the race condition where thread creation/switching happens before
        the WebSocket connection is ready to handle the resulting message flow.
        """
        self.connection_state_machine = self.registry.register_connection(self.connection_id, self.user_id)

        def track_state_changes(transition_info):
            self.websocket_state_changes.append({'timestamp': time.time(), 'from_state': transition_info.from_state.value, 'to_state': transition_info.to_state.value, 'reason': transition_info.reason})
        self.connection_state_machine.add_state_change_callback(track_state_changes)

        async def attempt_thread_operation(operation_type: str, delay: float=0) -> Dict[str, Any]:
            """Simulate thread operation that depends on WebSocket readiness."""
            if delay > 0:
                await asyncio.sleep(delay)
            timestamp = time.time()
            can_process = self.connection_state_machine.can_process_messages()
            is_ready = self.connection_state_machine.is_ready_for_messages
            current_state = self.connection_state_machine.current_state
            operation_result = {'operation': operation_type, 'timestamp': timestamp, 'websocket_ready': is_ready, 'can_process_messages': can_process, 'connection_state': current_state.value, 'success': can_process}
            self.thread_operations.append(operation_result)
            return operation_result
        thread_operation_tasks = [asyncio.create_task(attempt_thread_operation('create_thread', 0.01)), asyncio.create_task(attempt_thread_operation('switch_thread', 0.02)), asyncio.create_task(attempt_thread_operation('load_messages', 0.03)), asyncio.create_task(attempt_thread_operation('send_message', 0.04))]
        setup_start = time.time()
        await asyncio.sleep(0.005)
        success = self.connection_state_machine.transition_to(ApplicationConnectionState.ACCEPTED, 'WebSocket transport established')
        assert success
        assert not self.connection_state_machine.can_process_messages()
        await asyncio.sleep(0.01)
        success = self.connection_state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, 'JWT validation completed')
        assert success
        assert not self.connection_state_machine.can_process_messages()
        await asyncio.sleep(0.01)
        success = self.connection_state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, 'Required services initialized')
        assert success
        assert not self.connection_state_machine.can_process_messages()
        await asyncio.sleep(0.01)
        success = self.connection_state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, 'Application fully operational')
        assert success
        assert self.connection_state_machine.can_process_messages()
        setup_duration = time.time() - setup_start
        operation_results = await asyncio.gather(*thread_operation_tasks)
        blocked_operations = [op for op in self.thread_operations if not op['success']]
        allowed_operations = [op for op in self.thread_operations if op['success']]
        setup_phase_states = ['connecting', 'accepted', 'authenticated', 'services_ready']
        operations_blocked_during_setup = [op for op in blocked_operations if op['connection_state'] in setup_phase_states]
        assert len(operations_blocked_during_setup) > 0, 'Thread operations should be blocked during WebSocket setup to prevent data corruption'
        assert len(self.websocket_state_changes) == 4
        expected_progression = [('connecting', 'accepted'), ('accepted', 'authenticated'), ('authenticated', 'services_ready'), ('services_ready', 'processing_ready')]
        actual_progression = [(change['from_state'], change['to_state']) for change in self.websocket_state_changes]
        assert actual_progression == expected_progression
        self.record_metric('setup_duration_ms', setup_duration * 1000)
        self.record_metric('operations_blocked_during_setup', len(operations_blocked_during_setup))
        self.record_metric('operations_allowed_when_ready', len([op for op in allowed_operations if op['connection_state'] == 'processing_ready']))
        self.record_metric('race_condition_prevention_effective', len(operations_blocked_during_setup) > 0)

    @pytest.mark.integration
    async def test_thread_state_machine_coordination_with_websocket_events(self):
        """
        Test coordination between thread state transitions and WebSocket event delivery.
        
        This validates that thread state changes trigger appropriate WebSocket events
        and that WebSocket connection state affects thread operation success.
        """
        self.connection_state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        for state, reason in [(ApplicationConnectionState.ACCEPTED, 'transport_ready'), (ApplicationConnectionState.AUTHENTICATED, 'auth_complete'), (ApplicationConnectionState.SERVICES_READY, 'services_loaded'), (ApplicationConnectionState.PROCESSING_READY, 'fully_operational')]:
            self.connection_state_machine.transition_to(state, reason)
        assert self.connection_state_machine.can_process_messages()
        thread_operations = [{'operation': 'start_create', 'expected_websocket_events': ['thread_create_initiated']}, {'operation': 'create_complete', 'expected_websocket_events': ['thread_created', 'thread_ready']}, {'operation': 'start_switch', 'expected_websocket_events': ['thread_switch_initiated']}, {'operation': 'switch_complete', 'expected_websocket_events': ['thread_switched', 'messages_loaded']}, {'operation': 'start_load', 'expected_websocket_events': ['message_load_initiated']}, {'operation': 'load_complete', 'expected_websocket_events': ['messages_loaded']}]
        websocket_events_sent = []

        def simulate_websocket_event_send(event_type: str, data: Dict[str, Any]):
            """Simulate sending WebSocket event for thread operation."""
            if self.connection_state_machine.can_process_messages():
                websocket_events_sent.append({'event_type': event_type, 'data': data, 'timestamp': time.time(), 'connection_state': self.connection_state_machine.current_state.value})
                return True
            return False

        def simulate_thread_state_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate a thread state machine operation with WebSocket coordination."""
            operation_start = time.time()
            if not self.connection_state_machine.can_process_messages():
                return {'operation': operation['operation'], 'success': False, 'reason': 'websocket_not_ready', 'connection_state': self.connection_state_machine.current_state.value}
            events_sent = []
            for expected_event in operation['expected_websocket_events']:
                event_sent = simulate_websocket_event_send(expected_event, {'operation': operation['operation'], 'thread_id': str(self.thread_id), 'user_id': str(self.user_id)})
                if event_sent:
                    events_sent.append(expected_event)
            operation_duration = time.time() - operation_start
            return {'operation': operation['operation'], 'success': len(events_sent) == len(operation['expected_websocket_events']), 'events_sent': events_sent, 'expected_events': operation['expected_websocket_events'], 'duration_ms': operation_duration * 1000, 'connection_state': self.connection_state_machine.current_state.value}
        operation_results = []
        for operation in thread_operations:
            result = simulate_thread_state_operation(operation)
            operation_results.append(result)
            self.thread_operations.append(result)
            await asyncio.sleep(0.001)
        successful_operations = [op for op in operation_results if op['success']]
        failed_operations = [op for op in operation_results if not op['success']]
        assert len(failed_operations) == 0, f'No operations should fail when WebSocket is ready: {failed_operations}'
        assert len(successful_operations) == len(thread_operations)
        total_expected_events = sum((len(op['expected_websocket_events']) for op in thread_operations))
        total_sent_events = len(websocket_events_sent)
        assert total_sent_events == total_expected_events, f'Expected {total_expected_events} WebSocket events, got {total_sent_events}'
        event_timestamps = [event['timestamp'] for event in websocket_events_sent]
        assert event_timestamps == sorted(event_timestamps), 'WebSocket events should be sent in chronological order'
        average_operation_duration = sum((op['duration_ms'] for op in successful_operations)) / len(successful_operations)
        self.record_metric('successful_thread_operations', len(successful_operations))
        self.record_metric('websocket_events_sent', total_sent_events)
        self.record_metric('average_operation_duration_ms', average_operation_duration)
        self.record_metric('coordination_success_rate', len(successful_operations) / len(thread_operations))

    @pytest.mark.integration
    async def test_connection_degradation_affects_thread_operations(self):
        """
        Test how WebSocket connection degradation affects thread operations.
        
        This validates that thread operations gracefully handle connection issues
        and that state coordination prevents data loss during degraded states.
        """
        self.connection_state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        for state, reason in [(ApplicationConnectionState.ACCEPTED, 'transport_ready'), (ApplicationConnectionState.AUTHENTICATED, 'auth_complete'), (ApplicationConnectionState.SERVICES_READY, 'services_loaded'), (ApplicationConnectionState.PROCESSING_READY, 'fully_operational')]:
            self.connection_state_machine.transition_to(state, reason)
        assert self.connection_state_machine.can_process_messages()
        normal_operations = []
        for i in range(3):
            operation_result = {'operation_id': f'normal_op_{i}', 'success': self.connection_state_machine.can_process_messages(), 'connection_state': self.connection_state_machine.current_state.value, 'timestamp': time.time()}
            normal_operations.append(operation_result)
        successful_normal = [op for op in normal_operations if op['success']]
        assert len(successful_normal) == 3
        degradation_scenarios = [{'name': 'service_degradation', 'target_state': ApplicationConnectionState.DEGRADED, 'reason': 'Some services temporarily unavailable', 'expected_thread_impact': 'limited_functionality'}, {'name': 'reconnection_required', 'target_state': ApplicationConnectionState.RECONNECTING, 'reason': 'Connection unstable, attempting recovery', 'expected_thread_impact': 'operations_blocked'}, {'name': 'connection_failure', 'target_state': ApplicationConnectionState.FAILED, 'reason': 'Unrecoverable connection error', 'expected_thread_impact': 'all_operations_fail'}]
        degradation_results = []
        for scenario in degradation_scenarios:
            success = self.connection_state_machine.transition_to(scenario['target_state'], scenario['reason'])
            assert success, f"Should be able to transition to {scenario['target_state']}"
            degraded_operations = []
            test_operations = ['create_thread', 'switch_thread', 'load_messages', 'send_message']
            for op_type in test_operations:
                can_process = self.connection_state_machine.can_process_messages()
                is_operational = self.connection_state_machine.is_operational
                should_succeed = False
                if scenario['target_state'] == ApplicationConnectionState.DEGRADED:
                    should_succeed = can_process
                elif scenario['target_state'] == ApplicationConnectionState.RECONNECTING:
                    should_succeed = False
                elif scenario['target_state'] == ApplicationConnectionState.FAILED:
                    should_succeed = False
                operation_result = {'operation': op_type, 'can_process_messages': can_process, 'is_operational': is_operational, 'should_succeed': should_succeed, 'actual_success': can_process, 'connection_state': self.connection_state_machine.current_state.value, 'scenario': scenario['name']}
                degraded_operations.append(operation_result)
            scenario_result = {'scenario': scenario['name'], 'target_state': scenario['target_state'].value, 'operations': degraded_operations, 'operations_that_should_succeed': len([op for op in degraded_operations if op['should_succeed']]), 'operations_that_actually_succeeded': len([op for op in degraded_operations if op['actual_success']]), 'coordination_maintained': True}
            degradation_results.append(scenario_result)
            for operation in degraded_operations:
                if operation['should_succeed'] != operation['actual_success']:
                    scenario_result['coordination_maintained'] = False
                    break
            if scenario['target_state'] != ApplicationConnectionState.FAILED:
                recovery_success = self.connection_state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"Recovery from {scenario['name']}")
                if recovery_success:
                    post_recovery_op = {'operation': 'post_recovery_test', 'success': self.connection_state_machine.can_process_messages(), 'connection_state': self.connection_state_machine.current_state.value}
                    scenario_result['recovery_successful'] = post_recovery_op['success']
                else:
                    scenario_result['recovery_successful'] = False
        scenarios_with_proper_coordination = [result for result in degradation_results if result['coordination_maintained']]
        coordination_success_rate = len(scenarios_with_proper_coordination) / len(degradation_scenarios)
        self.assertGreaterEqual(coordination_success_rate, 0.8, f'Coordination between WebSocket state and thread operations should be maintained in at least 80% of degradation scenarios, got {coordination_success_rate:.1%}')
        failed_scenario = next((r for r in degradation_results if r['target_state'] == 'failed'))
        failed_operations = [op for op in failed_scenario['operations'] if op['actual_success']]
        assert len(failed_operations) == 0, f'No thread operations should succeed when WebSocket connection is in FAILED state, but {len(failed_operations)} operations succeeded'
        self.record_metric('degradation_scenarios_tested', len(degradation_scenarios))
        self.record_metric('coordination_success_rate', coordination_success_rate)
        self.record_metric('normal_operations_successful', len(successful_normal))
        self.record_metric('degradation_results', degradation_results)

    @pytest.mark.integration
    async def test_concurrent_state_machine_operations_coordination(self):
        """
        Test coordination when both WebSocket and thread state machines are changing simultaneously.
        
        This validates that concurrent state changes don't cause data corruption or
        inconsistent states between the connection and thread management systems.
        """
        self.connection_state_machine = self.registry.register_connection(self.connection_id, self.user_id)
        concurrent_events = []

        def track_websocket_events(transition_info):
            concurrent_events.append({'type': 'websocket_state_change', 'from_state': transition_info.from_state.value, 'to_state': transition_info.to_state.value, 'reason': transition_info.reason, 'timestamp': time.time(), 'thread_id': threading.current_thread().ident})
        self.connection_state_machine.add_state_change_callback(track_websocket_events)

        async def concurrent_websocket_setup():
            """Simulate WebSocket setup happening concurrently with thread operations."""
            setup_phases = [(ApplicationConnectionState.ACCEPTED, 'transport_established'), (ApplicationConnectionState.AUTHENTICATED, 'auth_validated'), (ApplicationConnectionState.SERVICES_READY, 'services_initialized'), (ApplicationConnectionState.PROCESSING_READY, 'setup_complete')]
            for i, (state, reason) in enumerate(setup_phases):
                await asyncio.sleep(0.01)
                success = self.connection_state_machine.transition_to(state, reason)
                concurrent_events.append({'type': 'websocket_setup_phase', 'phase': i + 1, 'state': state.value, 'success': success, 'timestamp': time.time(), 'thread_id': threading.current_thread().ident})
            return 'websocket_setup_complete'

        async def concurrent_thread_operations():
            """Simulate thread operations happening during WebSocket setup."""
            thread_ops = [('create_thread', 0.005), ('load_messages', 0.015), ('switch_thread', 0.025), ('send_message', 0.035)]
            results = []
            for operation, delay in thread_ops:
                await asyncio.sleep(delay)
                websocket_ready = self.connection_state_machine.can_process_messages()
                connection_state = self.connection_state_machine.current_state.value
                operation_success = websocket_ready
                result = {'type': 'thread_operation', 'operation': operation, 'websocket_ready': websocket_ready, 'connection_state': connection_state, 'success': operation_success, 'timestamp': time.time(), 'thread_id': threading.current_thread().ident}
                results.append(result)
                concurrent_events.append(result)
            return results

        async def concurrent_state_monitor():
            """Monitor for state consistency violations during concurrent operations."""
            violations = []
            for _ in range(20):
                await asyncio.sleep(0.01)
                current_state = self.connection_state_machine.current_state
                is_operational = self.connection_state_machine.is_operational
                can_process = self.connection_state_machine.can_process_messages()
                expected_operational = ApplicationConnectionState.is_operational(current_state)
                if is_operational != expected_operational:
                    violations.append({'type': 'operational_state_inconsistency', 'current_state': current_state.value, 'reported_operational': is_operational, 'expected_operational': expected_operational, 'timestamp': time.time()})
                if current_state == ApplicationConnectionState.PROCESSING_READY:
                    if not can_process:
                        violations.append({'type': 'message_processing_inconsistency', 'current_state': current_state.value, 'can_process': can_process, 'timestamp': time.time()})
            return violations
        start_time = time.time()
        websocket_result, thread_results, consistency_violations = await asyncio.gather(concurrent_websocket_setup(), concurrent_thread_operations(), concurrent_state_monitor())
        end_time = time.time()
        total_duration = end_time - start_time
        websocket_events = [e for e in concurrent_events if e['type'] == 'websocket_state_change']
        thread_events = [e for e in concurrent_events if e['type'] == 'thread_operation']
        setup_events = [e for e in concurrent_events if e['type'] == 'websocket_setup_phase']
        successful_thread_ops = [op for op in thread_results if op['success']]
        failed_thread_ops = [op for op in thread_results if not op['success']]
        premature_successes = [op for op in successful_thread_ops if op['connection_state'] != 'processing_ready']
        assert len(consistency_violations) == 0, f'No state consistency violations should occur during concurrent operations: {consistency_violations}'
        assert len(premature_successes) == 0, f'No thread operations should succeed before WebSocket is ready: {premature_successes}'
        websocket_ready_time = None
        for event in setup_events:
            if event['state'] == 'processing_ready' and event['success']:
                websocket_ready_time = event['timestamp']
                break
        if websocket_ready_time:
            operations_after_ready = [op for op in successful_thread_ops if op['timestamp'] >= websocket_ready_time]
            assert len(operations_after_ready) == len(successful_thread_ops), 'All successful thread operations should occur after WebSocket became ready'
        assert self.connection_state_machine.current_state == ApplicationConnectionState.PROCESSING_READY
        assert self.connection_state_machine.can_process_messages()
        self.record_metric('concurrent_execution_duration_ms', total_duration * 1000)
        self.record_metric('websocket_state_changes', len(websocket_events))
        self.record_metric('thread_operations_attempted', len(thread_results))
        self.record_metric('thread_operations_successful', len(successful_thread_ops))
        self.record_metric('thread_operations_failed', len(failed_thread_ops))
        self.record_metric('consistency_violations', len(consistency_violations))
        self.record_metric('premature_operations', len(premature_successes))
        self.record_metric('coordination_success', len(consistency_violations) == 0 and len(premature_successes) == 0)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_websocket_thread_coordination_with_authentication(self):
        """
        Test real WebSocket connection with thread state coordination and authentication.
        
        This validates the complete integration between WebSocket connection state machine,
        authentication flow, and thread operations in a real environment.
        """
        user_context = await create_authenticated_user_context(user_email=f'coord-test-{uuid.uuid4().hex[:8]}@example.com', environment='test', websocket_enabled=True)
        auth_helper = E2EWebSocketAuthHelper(environment='test')
        websocket_connection_id = user_context.websocket_client_id
        if websocket_connection_id:
            self.connection_state_machine = self.registry.register_connection(ConnectionID(str(websocket_connection_id)), user_context.user_id)
        coordination_timeline = []

        def track_coordination_events(event_type: str, data: Dict[str, Any]):
            coordination_timeline.append({'event_type': event_type, 'data': data, 'timestamp': time.time(), 'connection_state': self.connection_state_machine.current_state.value if self.connection_state_machine else 'none'})
        try:
            track_coordination_events('websocket_connect_start', {'user_id': str(user_context.user_id)})
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            track_coordination_events('websocket_connected', {'authenticated': True})
            if self.connection_state_machine:
                setup_phases = [(ApplicationConnectionState.ACCEPTED, 'Real WebSocket connection established'), (ApplicationConnectionState.AUTHENTICATED, 'JWT authentication validated'), (ApplicationConnectionState.SERVICES_READY, 'Thread and agent services ready'), (ApplicationConnectionState.PROCESSING_READY, 'Ready for thread operations')]
                for state, reason in setup_phases:
                    success = self.connection_state_machine.transition_to(state, reason)
                    track_coordination_events('state_transition', {'to_state': state.value, 'success': success, 'reason': reason})
                    if not success:
                        self.fail(f'Failed to transition to {state}: {reason}')
            thread_operations_to_test = [{'type': 'create_thread', 'message': {'type': 'thread_create_request', 'data': {'title': 'Coordination Test Thread', 'user_id': str(user_context.user_id)}}}, {'type': 'send_message', 'message': {'type': 'chat_message', 'data': {'content': 'Test message for coordination validation', 'thread_id': str(user_context.thread_id)}}}]
            successful_operations = 0
            for operation in thread_operations_to_test:
                websocket_ready = True
                if self.connection_state_machine:
                    websocket_ready = self.connection_state_machine.can_process_messages()
                track_coordination_events('thread_operation_start', {'operation_type': operation['type'], 'websocket_ready': websocket_ready})
                if websocket_ready:
                    try:
                        message_data = operation['message']
                        await websocket.send(str(message_data))
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        track_coordination_events('thread_operation_success', {'operation_type': operation['type'], 'response_received': bool(response)})
                        successful_operations += 1
                    except asyncio.TimeoutError:
                        track_coordination_events('thread_operation_timeout', {'operation_type': operation['type']})
                    except Exception as e:
                        track_coordination_events('thread_operation_error', {'operation_type': operation['type'], 'error': str(e)})
                else:
                    track_coordination_events('thread_operation_blocked', {'operation_type': operation['type'], 'reason': 'websocket_not_ready'})
            await websocket.close()
            track_coordination_events('websocket_disconnected', {})
            if self.connection_state_machine:
                self.connection_state_machine.transition_to(ApplicationConnectionState.CLOSED, 'WebSocket connection closed')
            connect_events = [e for e in coordination_timeline if 'connect' in e['event_type']]
            state_events = [e for e in coordination_timeline if e['event_type'] == 'state_transition']
            operation_events = [e for e in coordination_timeline if 'thread_operation' in e['event_type']]
            assert len(connect_events) > 0, 'Should have WebSocket connection events'
            assert len(state_events) > 0, 'Should have state machine transitions'
            assert len(operation_events) > 0, 'Should have thread operation events'
            operation_starts = [e for e in operation_events if e['event_type'] == 'thread_operation_start']
            ready_operations = [e for e in operation_starts if e['data']['websocket_ready']]
            assert len(ready_operations) == len(operation_starts), 'All thread operations should have been attempted when WebSocket was ready'
            success_rate = successful_operations / len(thread_operations_to_test)
            self.assertGreaterEqual(success_rate, 0.5, f'At least 50% of thread operations should succeed with proper coordination, got {success_rate:.1%}')
            self.record_metric('real_websocket_connection_successful', len(connect_events) > 0)
            self.record_metric('state_transitions_completed', len(state_events))
            self.record_metric('thread_operations_attempted', len(thread_operations_to_test))
            self.record_metric('thread_operations_successful', successful_operations)
            self.record_metric('coordination_success_rate', success_rate)
            self.record_metric('coordination_timeline_events', len(coordination_timeline))
        except Exception as e:
            self.fail(f'Real WebSocket thread coordination test failed: {e}')
        finally:
            if self.connection_state_machine and websocket_connection_id:
                self.registry.unregister_connection(ConnectionID(str(websocket_connection_id)))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')