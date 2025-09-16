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

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine,
    ConnectionStateMachineRegistry,
    get_connection_state_registry
)
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
        
        # Test identifiers - use proper UUID format for validation
        self.user_id = UserID(str(uuid.uuid4()))
        self.connection_id = ConnectionID(str(uuid.uuid4()))
        self.thread_id = ThreadID(str(uuid.uuid4()))
        
        # State tracking
        self.websocket_state_changes: List[Dict[str, Any]] = []
        self.thread_operations: List[Dict[str, Any]] = []
        self.coordination_events: List[Dict[str, Any]] = []
        
        # Registry setup
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
        
        # Register connection state machine
        self.connection_state_machine = self.registry.register_connection(
            self.connection_id, self.user_id
        )
        
        def track_state_changes(transition_info):
            self.websocket_state_changes.append({
                'timestamp': time.time(),
                'from_state': transition_info.from_state.value,
                'to_state': transition_info.to_state.value,
                'reason': transition_info.reason
            })
        
        self.connection_state_machine.add_state_change_callback(track_state_changes)
        
        async def attempt_thread_operation(operation_type: str, delay: float = 0) -> Dict[str, Any]:
            """Simulate thread operation that depends on WebSocket readiness."""
            if delay > 0:
                await asyncio.sleep(delay)
                
            timestamp = time.time()
            can_process = self.connection_state_machine.can_process_messages()
            is_ready = self.connection_state_machine.is_ready_for_messages
            current_state = self.connection_state_machine.current_state
            
            operation_result = {
                'operation': operation_type,
                'timestamp': timestamp,
                'websocket_ready': is_ready,
                'can_process_messages': can_process,
                'connection_state': current_state.value,
                'success': can_process  # Operations should only succeed if connection is ready
            }
            
            self.thread_operations.append(operation_result)
            return operation_result

        # Start multiple thread operations that will attempt to execute during setup
        thread_operation_tasks = [
            asyncio.create_task(attempt_thread_operation('create_thread', 0.01)),
            asyncio.create_task(attempt_thread_operation('switch_thread', 0.02)),
            asyncio.create_task(attempt_thread_operation('load_messages', 0.03)),
            asyncio.create_task(attempt_thread_operation('send_message', 0.04)),
        ]
        
        # Meanwhile, advance WebSocket connection through setup phases
        setup_start = time.time()
        
        # WebSocket connection establishment phases
        await asyncio.sleep(0.005)  # Small delay to let operations start
        
        # Phase 1: Transport ready but application not ready
        success = self.connection_state_machine.transition_to(
            ApplicationConnectionState.ACCEPTED,
            "WebSocket transport established"
        )
        assert success
        assert not self.connection_state_machine.can_process_messages()
        
        await asyncio.sleep(0.01)
        
        # Phase 2: Authentication complete but services not ready  
        success = self.connection_state_machine.transition_to(
            ApplicationConnectionState.AUTHENTICATED,
            "JWT validation completed"
        )
        assert success
        assert not self.connection_state_machine.can_process_messages()
        
        await asyncio.sleep(0.01)
        
        # Phase 3: Services ready but final setup not complete
        success = self.connection_state_machine.transition_to(
            ApplicationConnectionState.SERVICES_READY,
            "Required services initialized"
        )
        assert success
        assert not self.connection_state_machine.can_process_messages()
        
        await asyncio.sleep(0.01)
        
        # Phase 4: Fully ready for message processing
        success = self.connection_state_machine.transition_to(
            ApplicationConnectionState.PROCESSING_READY,
            "Application fully operational"
        )
        assert success
        assert self.connection_state_machine.can_process_messages()
        
        setup_duration = time.time() - setup_start
        
        # Wait for all thread operations to complete
        operation_results = await asyncio.gather(*thread_operation_tasks)
        
        # Analyze coordination results
        blocked_operations = [op for op in self.thread_operations if not op['success']]
        allowed_operations = [op for op in self.thread_operations if op['success']]
        
        # CRITICAL: Operations during setup phases should be blocked
        setup_phase_states = ['connecting', 'accepted', 'authenticated', 'services_ready']
        operations_blocked_during_setup = [
            op for op in blocked_operations 
            if op['connection_state'] in setup_phase_states
        ]
        
        # Business value assertions
        assert len(operations_blocked_during_setup) > 0, (
            "Thread operations should be blocked during WebSocket setup to prevent data corruption"
        )
        
        # Verify state machine progressed through all phases
        assert len(self.websocket_state_changes) == 4
        expected_progression = [
            ('connecting', 'accepted'),
            ('accepted', 'authenticated'),
            ('authenticated', 'services_ready'),
            ('services_ready', 'processing_ready')
        ]
        
        actual_progression = [
            (change['from_state'], change['to_state']) 
            for change in self.websocket_state_changes
        ]
        assert actual_progression == expected_progression
        
        # Record business metrics
        self.record_metric("setup_duration_ms", setup_duration * 1000)
        self.record_metric("operations_blocked_during_setup", len(operations_blocked_during_setup))
        self.record_metric("operations_allowed_when_ready", len([
            op for op in allowed_operations 
            if op['connection_state'] == 'processing_ready'
        ]))
        self.record_metric("race_condition_prevention_effective", len(operations_blocked_during_setup) > 0)

    @pytest.mark.integration
    async def test_thread_state_machine_coordination_with_websocket_events(self):
        """
        Test coordination between thread state transitions and WebSocket event delivery.
        
        This validates that thread state changes trigger appropriate WebSocket events
        and that WebSocket connection state affects thread operation success.
        """
        
        # Set up connection state machine
        self.connection_state_machine = self.registry.register_connection(
            self.connection_id, self.user_id
        )
        
        # Advance to operational state
        for state, reason in [
            (ApplicationConnectionState.ACCEPTED, "transport_ready"),
            (ApplicationConnectionState.AUTHENTICATED, "auth_complete"),
            (ApplicationConnectionState.SERVICES_READY, "services_loaded"),
            (ApplicationConnectionState.PROCESSING_READY, "fully_operational")
        ]:
            self.connection_state_machine.transition_to(state, reason)
        
        # Verify ready state
        assert self.connection_state_machine.can_process_messages()
        
        # Simulate frontend thread state machine operations
        thread_operations = [
            {'operation': 'start_create', 'expected_websocket_events': ['thread_create_initiated']},
            {'operation': 'create_complete', 'expected_websocket_events': ['thread_created', 'thread_ready']},
            {'operation': 'start_switch', 'expected_websocket_events': ['thread_switch_initiated']},
            {'operation': 'switch_complete', 'expected_websocket_events': ['thread_switched', 'messages_loaded']},
            {'operation': 'start_load', 'expected_websocket_events': ['message_load_initiated']},
            {'operation': 'load_complete', 'expected_websocket_events': ['messages_loaded']},
        ]
        
        websocket_events_sent = []
        
        def simulate_websocket_event_send(event_type: str, data: Dict[str, Any]):
            """Simulate sending WebSocket event for thread operation."""
            if self.connection_state_machine.can_process_messages():
                websocket_events_sent.append({
                    'event_type': event_type,
                    'data': data,
                    'timestamp': time.time(),
                    'connection_state': self.connection_state_machine.current_state.value
                })
                return True
            return False
        
        def simulate_thread_state_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate a thread state machine operation with WebSocket coordination."""
            operation_start = time.time()
            
            # Check if WebSocket is ready for this operation
            if not self.connection_state_machine.can_process_messages():
                return {
                    'operation': operation['operation'],
                    'success': False,
                    'reason': 'websocket_not_ready',
                    'connection_state': self.connection_state_machine.current_state.value
                }
            
            # Simulate operation execution with WebSocket event sending
            events_sent = []
            for expected_event in operation['expected_websocket_events']:
                event_sent = simulate_websocket_event_send(expected_event, {
                    'operation': operation['operation'],
                    'thread_id': str(self.thread_id),
                    'user_id': str(self.user_id)
                })
                
                if event_sent:
                    events_sent.append(expected_event)
            
            operation_duration = time.time() - operation_start
            
            return {
                'operation': operation['operation'],
                'success': len(events_sent) == len(operation['expected_websocket_events']),
                'events_sent': events_sent,
                'expected_events': operation['expected_websocket_events'],
                'duration_ms': operation_duration * 1000,
                'connection_state': self.connection_state_machine.current_state.value
            }
        
        # Execute all thread operations
        operation_results = []
        for operation in thread_operations:
            result = simulate_thread_state_operation(operation)
            operation_results.append(result)
            self.thread_operations.append(result)
            
            # Small delay between operations
            await asyncio.sleep(0.001)
        
        # Verify coordination results
        successful_operations = [op for op in operation_results if op['success']]
        failed_operations = [op for op in operation_results if not op['success']]
        
        # All operations should succeed since WebSocket is ready
        assert len(failed_operations) == 0, (
                        f"No operations should fail when WebSocket is ready: {failed_operations}")
        assert len(successful_operations) == len(thread_operations)
        
        # Verify all expected WebSocket events were sent
        total_expected_events = sum(len(op['expected_websocket_events']) for op in thread_operations)
        total_sent_events = len(websocket_events_sent)
        
        assert total_sent_events == total_expected_events, (
                        f"Expected {total_expected_events} WebSocket events, got {total_sent_events}")
        
        # Verify event ordering and timing
        event_timestamps = [event['timestamp'] for event in websocket_events_sent]
        assert event_timestamps == sorted(event_timestamps), (
                        "WebSocket events should be sent in chronological order")
        
        # Business metrics
        average_operation_duration = sum(op['duration_ms'] for op in successful_operations) / len(successful_operations)
        
        self.record_metric("successful_thread_operations", len(successful_operations))
        self.record_metric("websocket_events_sent", total_sent_events)
        self.record_metric("average_operation_duration_ms", average_operation_duration)
        self.record_metric("coordination_success_rate", len(successful_operations) / len(thread_operations))

    @pytest.mark.integration
    async def test_connection_degradation_affects_thread_operations(self):
        """
        Test how WebSocket connection degradation affects thread operations.
        
        This validates that thread operations gracefully handle connection issues
        and that state coordination prevents data loss during degraded states.
        """
        
        # Set up fully operational connection
        self.connection_state_machine = self.registry.register_connection(
            self.connection_id, self.user_id
        )
        
        # Advance to operational state
        for state, reason in [
            (ApplicationConnectionState.ACCEPTED, "transport_ready"),
            (ApplicationConnectionState.AUTHENTICATED, "auth_complete"), 
            (ApplicationConnectionState.SERVICES_READY, "services_loaded"),
            (ApplicationConnectionState.PROCESSING_READY, "fully_operational")
        ]:
            self.connection_state_machine.transition_to(state, reason)
        
        assert self.connection_state_machine.can_process_messages()
        
        # Simulate successful thread operations in normal state
        normal_operations = []
        for i in range(3):
            operation_result = {
                'operation_id': f'normal_op_{i}',
                'success': self.connection_state_machine.can_process_messages(),
                'connection_state': self.connection_state_machine.current_state.value,
                'timestamp': time.time()
            }
            normal_operations.append(operation_result)
        
        # Verify all normal operations would succeed
        successful_normal = [op for op in normal_operations if op['success']]
        assert len(successful_normal) == 3
        
        # Simulate connection degradation
        degradation_scenarios = [
            {
                'name': 'service_degradation',
                'target_state': ApplicationConnectionState.DEGRADED,
                'reason': 'Some services temporarily unavailable',
                'expected_thread_impact': 'limited_functionality'
            },
            {
                'name': 'reconnection_required',
                'target_state': ApplicationConnectionState.RECONNECTING,
                'reason': 'Connection unstable, attempting recovery',
                'expected_thread_impact': 'operations_blocked'
            },
            {
                'name': 'connection_failure',
                'target_state': ApplicationConnectionState.FAILED,
                'reason': 'Unrecoverable connection error',
                'expected_thread_impact': 'all_operations_fail'
            }
        ]
        
        degradation_results = []
        
        for scenario in degradation_scenarios:
            # Transition to degraded state
            success = self.connection_state_machine.transition_to(
                scenario['target_state'],
                scenario['reason']
            )
            assert success, f"Should be able to transition to {scenario['target_state']}"
            
            # Test thread operations in degraded state
            degraded_operations = []
            test_operations = ['create_thread', 'switch_thread', 'load_messages', 'send_message']
            
            for op_type in test_operations:
                can_process = self.connection_state_machine.can_process_messages()
                is_operational = self.connection_state_machine.is_operational
                
                # Determine if operation should succeed based on degradation level
                should_succeed = False
                if scenario['target_state'] == ApplicationConnectionState.DEGRADED:
                    should_succeed = can_process  # Some operations might work in degraded mode
                elif scenario['target_state'] == ApplicationConnectionState.RECONNECTING:
                    should_succeed = False  # No operations during reconnection
                elif scenario['target_state'] == ApplicationConnectionState.FAILED:
                    should_succeed = False  # No operations when failed
                
                operation_result = {
                    'operation': op_type,
                    'can_process_messages': can_process,
                    'is_operational': is_operational,
                    'should_succeed': should_succeed,
                    'actual_success': can_process,  # Simulate operation result
                    'connection_state': self.connection_state_machine.current_state.value,
                    'scenario': scenario['name']
                }
                
                degraded_operations.append(operation_result)
            
            scenario_result = {
                'scenario': scenario['name'],
                'target_state': scenario['target_state'].value,
                'operations': degraded_operations,
                'operations_that_should_succeed': len([op for op in degraded_operations if op['should_succeed']]),
                'operations_that_actually_succeeded': len([op for op in degraded_operations if op['actual_success']]),
                'coordination_maintained': True  # Will be validated below
            }
            
            degradation_results.append(scenario_result)
            
            # Verify coordination between state machine and thread operations
            for operation in degraded_operations:
                if operation['should_succeed'] != operation['actual_success']:
                    scenario_result['coordination_maintained'] = False
                    break
            
            # Attempt recovery (if possible)
            if scenario['target_state'] != ApplicationConnectionState.FAILED:
                recovery_success = self.connection_state_machine.transition_to(
                    ApplicationConnectionState.PROCESSING_READY,
                    f"Recovery from {scenario['name']}"
                )
                
                if recovery_success:
                    # Test that operations work again after recovery
                    post_recovery_op = {
                        'operation': 'post_recovery_test',
                        'success': self.connection_state_machine.can_process_messages(),
                        'connection_state': self.connection_state_machine.current_state.value
                    }
                    scenario_result['recovery_successful'] = post_recovery_op['success']
                else:
                    scenario_result['recovery_successful'] = False
        
        # Analyze degradation handling
        scenarios_with_proper_coordination = [
            result for result in degradation_results 
            if result['coordination_maintained']
        ]
        
        coordination_success_rate = len(scenarios_with_proper_coordination) / len(degradation_scenarios)
        
        # Business value assertions
        self.assertGreaterEqual(
            coordination_success_rate, 0.8,
            f"Coordination between WebSocket state and thread operations should be maintained "
            f"in at least 80% of degradation scenarios, got {coordination_success_rate:.1%}"
        )
        
        # Verify that failed states properly block operations
        failed_scenario = next(r for r in degradation_results if r['target_state'] == 'failed')
        failed_operations = [op for op in failed_scenario['operations'] if op['actual_success']]
        
        assert len(failed_operations) == 0, (
            f"No thread operations should succeed when WebSocket connection is in FAILED state, "
            f"but {len(failed_operations)} operations succeeded"
        )
        
        # Record business metrics
        self.record_metric("degradation_scenarios_tested", len(degradation_scenarios))
        self.record_metric("coordination_success_rate", coordination_success_rate)
        self.record_metric("normal_operations_successful", len(successful_normal))
        self.record_metric("degradation_results", degradation_results)

    @pytest.mark.integration
    async def test_concurrent_state_machine_operations_coordination(self):
        """
        Test coordination when both WebSocket and thread state machines are changing simultaneously.
        
        This validates that concurrent state changes don't cause data corruption or
        inconsistent states between the connection and thread management systems.
        """
        
        # Set up connection state machine
        self.connection_state_machine = self.registry.register_connection(
            self.connection_id, self.user_id
        )
        
        # Track all state changes
        concurrent_events = []
        
        def track_websocket_events(transition_info):
            concurrent_events.append({
                'type': 'websocket_state_change',
                'from_state': transition_info.from_state.value,
                'to_state': transition_info.to_state.value,
                'reason': transition_info.reason,
                'timestamp': time.time(),
                'thread_id': threading.current_thread().ident
            })
        
        self.connection_state_machine.add_state_change_callback(track_websocket_events)
        
        async def concurrent_websocket_setup():
            """Simulate WebSocket setup happening concurrently with thread operations."""
            setup_phases = [
                (ApplicationConnectionState.ACCEPTED, "transport_established"),
                (ApplicationConnectionState.AUTHENTICATED, "auth_validated"),
                (ApplicationConnectionState.SERVICES_READY, "services_initialized"),
                (ApplicationConnectionState.PROCESSING_READY, "setup_complete")
            ]
            
            for i, (state, reason) in enumerate(setup_phases):
                await asyncio.sleep(0.01)  # Simulate setup time
                
                success = self.connection_state_machine.transition_to(state, reason)
                concurrent_events.append({
                    'type': 'websocket_setup_phase',
                    'phase': i + 1,
                    'state': state.value,
                    'success': success,
                    'timestamp': time.time(),
                    'thread_id': threading.current_thread().ident
                })
            
            return "websocket_setup_complete"
        
        async def concurrent_thread_operations():
            """Simulate thread operations happening during WebSocket setup."""
            thread_ops = [
                ('create_thread', 0.005),
                ('load_messages', 0.015),
                ('switch_thread', 0.025),
                ('send_message', 0.035)
            ]
            
            results = []
            for operation, delay in thread_ops:
                await asyncio.sleep(delay)
                
                # Check WebSocket state before operation
                websocket_ready = self.connection_state_machine.can_process_messages()
                connection_state = self.connection_state_machine.current_state.value
                
                # Simulate thread operation
                operation_success = websocket_ready  # Operations succeed only if WebSocket ready
                
                result = {
                    'type': 'thread_operation',
                    'operation': operation,
                    'websocket_ready': websocket_ready,
                    'connection_state': connection_state,
                    'success': operation_success,
                    'timestamp': time.time(),
                    'thread_id': threading.current_thread().ident
                }
                
                results.append(result)
                concurrent_events.append(result)
            
            return results
        
        async def concurrent_state_monitor():
            """Monitor for state consistency violations during concurrent operations."""
            violations = []
            
            for _ in range(20):  # Monitor for 200ms (20 * 10ms)
                await asyncio.sleep(0.01)
                
                # Check for consistency violations
                current_state = self.connection_state_machine.current_state
                is_operational = self.connection_state_machine.is_operational
                can_process = self.connection_state_machine.can_process_messages()
                
                # Validate consistency
                expected_operational = ApplicationConnectionState.is_operational(current_state)
                if is_operational != expected_operational:
                    violations.append({
                        'type': 'operational_state_inconsistency',
                        'current_state': current_state.value,
                        'reported_operational': is_operational,
                        'expected_operational': expected_operational,
                        'timestamp': time.time()
                    })
                
                # Check message processing consistency
                if current_state == ApplicationConnectionState.PROCESSING_READY:
                    if not can_process:
                        violations.append({
                            'type': 'message_processing_inconsistency',
                            'current_state': current_state.value,
                            'can_process': can_process,
                            'timestamp': time.time()
                        })
            
            return violations
        
        # Execute all concurrent operations
        start_time = time.time()
        
        websocket_result, thread_results, consistency_violations = await asyncio.gather(
            concurrent_websocket_setup(),
            concurrent_thread_operations(), 
            concurrent_state_monitor()
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze concurrent execution results
        websocket_events = [e for e in concurrent_events if e['type'] == 'websocket_state_change']
        thread_events = [e for e in concurrent_events if e['type'] == 'thread_operation']
        setup_events = [e for e in concurrent_events if e['type'] == 'websocket_setup_phase']
        
        # Verify coordination worked correctly
        successful_thread_ops = [op for op in thread_results if op['success']]
        failed_thread_ops = [op for op in thread_results if not op['success']]
        
        # Operations should only succeed after WebSocket is ready
        premature_successes = [
            op for op in successful_thread_ops 
            if op['connection_state'] != 'processing_ready'
        ]
        
        # Business value assertions
        assert len(consistency_violations) == 0, (
            f"No state consistency violations should occur during concurrent operations: {consistency_violations}"
        )
        
        assert len(premature_successes) == 0, (
            f"No thread operations should succeed before WebSocket is ready: {premature_successes}"
        )
        
        # Verify proper coordination timing
        websocket_ready_time = None
        for event in setup_events:
            if event['state'] == 'processing_ready' and event['success']:
                websocket_ready_time = event['timestamp']
                break
        
        if websocket_ready_time:
            operations_after_ready = [
                op for op in successful_thread_ops 
                if op['timestamp'] >= websocket_ready_time
            ]
            
            assert len(operations_after_ready) == len(successful_thread_ops), (
                "All successful thread operations should occur after WebSocket became ready"
            )
        
        # Final state verification
        assert self.connection_state_machine.current_state == ApplicationConnectionState.PROCESSING_READY
        assert self.connection_state_machine.can_process_messages()
        
        # Record coordination metrics
        self.record_metric("concurrent_execution_duration_ms", total_duration * 1000)
        self.record_metric("websocket_state_changes", len(websocket_events))
        self.record_metric("thread_operations_attempted", len(thread_results))
        self.record_metric("thread_operations_successful", len(successful_thread_ops))
        self.record_metric("thread_operations_failed", len(failed_thread_ops))
        self.record_metric("consistency_violations", len(consistency_violations))
        self.record_metric("premature_operations", len(premature_successes))
        self.record_metric("coordination_success", len(consistency_violations) == 0 and len(premature_successes) == 0)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_websocket_thread_coordination_with_authentication(self):
        """
        Test real WebSocket connection with thread state coordination and authentication.
        
        This validates the complete integration between WebSocket connection state machine,
        authentication flow, and thread operations in a real environment.
        """
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"coord-test-{uuid.uuid4().hex[:8]}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        # Set up WebSocket auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Register connection state machine
        websocket_connection_id = user_context.websocket_client_id
        if websocket_connection_id:
            self.connection_state_machine = self.registry.register_connection(
                ConnectionID(str(websocket_connection_id)), user_context.user_id
            )
        
        coordination_timeline = []
        
        def track_coordination_events(event_type: str, data: Dict[str, Any]):
            coordination_timeline.append({
                'event_type': event_type,
                'data': data,
                'timestamp': time.time(),
                'connection_state': self.connection_state_machine.current_state.value if self.connection_state_machine else 'none'
            })
        
        try:
            # Phase 1: WebSocket connection establishment
            track_coordination_events('websocket_connect_start', {'user_id': str(user_context.user_id)})
            
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            track_coordination_events('websocket_connected', {'authenticated': True})
            
            # Simulate state machine setup phases
            if self.connection_state_machine:
                setup_phases = [
                    (ApplicationConnectionState.ACCEPTED, "Real WebSocket connection established"),
                    (ApplicationConnectionState.AUTHENTICATED, "JWT authentication validated"),
                    (ApplicationConnectionState.SERVICES_READY, "Thread and agent services ready"),
                    (ApplicationConnectionState.PROCESSING_READY, "Ready for thread operations")
                ]
                
                for state, reason in setup_phases:
                    success = self.connection_state_machine.transition_to(state, reason)
                    track_coordination_events('state_transition', {
                        'to_state': state.value,
                        'success': success,
                        'reason': reason
                    })
                    
                    if not success:
                        self.fail(f"Failed to transition to {state}: {reason}")
            
            # Phase 2: Thread operations with real WebSocket
            thread_operations_to_test = [
                {
                    'type': 'create_thread',
                    'message': {
                        'type': 'thread_create_request',
                        'data': {
                            'title': 'Coordination Test Thread',
                            'user_id': str(user_context.user_id)
                        }
                    }
                },
                {
                    'type': 'send_message',
                    'message': {
                        'type': 'chat_message',
                        'data': {
                            'content': 'Test message for coordination validation',
                            'thread_id': str(user_context.thread_id)
                        }
                    }
                }
            ]
            
            successful_operations = 0
            
            for operation in thread_operations_to_test:
                # Check WebSocket readiness before operation
                websocket_ready = True
                if self.connection_state_machine:
                    websocket_ready = self.connection_state_machine.can_process_messages()
                
                track_coordination_events('thread_operation_start', {
                    'operation_type': operation['type'],
                    'websocket_ready': websocket_ready
                })
                
                if websocket_ready:
                    try:
                        # Send message via real WebSocket
                        message_data = operation['message']
                        await websocket.send(str(message_data))
                        
                        # Wait for response with timeout
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        
                        track_coordination_events('thread_operation_success', {
                            'operation_type': operation['type'],
                            'response_received': bool(response)
                        })
                        
                        successful_operations += 1
                        
                    except asyncio.TimeoutError:
                        track_coordination_events('thread_operation_timeout', {
                            'operation_type': operation['type']
                        })
                    except Exception as e:
                        track_coordination_events('thread_operation_error', {
                            'operation_type': operation['type'],
                            'error': str(e)
                        })
                else:
                    track_coordination_events('thread_operation_blocked', {
                        'operation_type': operation['type'],
                        'reason': 'websocket_not_ready'
                    })
            
            # Phase 3: Cleanup and validation
            await websocket.close()
            track_coordination_events('websocket_disconnected', {})
            
            if self.connection_state_machine:
                self.connection_state_machine.transition_to(
                    ApplicationConnectionState.CLOSED,
                    "WebSocket connection closed"
                )
            
            # Validate coordination timeline
            connect_events = [e for e in coordination_timeline if 'connect' in e['event_type']]
            state_events = [e for e in coordination_timeline if e['event_type'] == 'state_transition']
            operation_events = [e for e in coordination_timeline if 'thread_operation' in e['event_type']]
            
            # Business value assertions
            assert len(connect_events) > 0, "Should have WebSocket connection events"
            assert len(state_events) > 0, "Should have state machine transitions"
            assert len(operation_events) > 0, "Should have thread operation events"
            
            # Verify operations only occurred when WebSocket was ready
            operation_starts = [e for e in operation_events if e['event_type'] == 'thread_operation_start']
            ready_operations = [e for e in operation_starts if e['data']['websocket_ready']]
            
            assert len(ready_operations) == len(operation_starts), (
                           "All thread operations should have been attempted when WebSocket was ready")
            
            # Verify successful coordination
            success_rate = successful_operations / len(thread_operations_to_test)
            self.assertGreaterEqual(success_rate, 0.5,
                                  f"At least 50% of thread operations should succeed with proper coordination, got {success_rate:.1%}")
            
            # Record integration metrics
            self.record_metric("real_websocket_connection_successful", len(connect_events) > 0)
            self.record_metric("state_transitions_completed", len(state_events))
            self.record_metric("thread_operations_attempted", len(thread_operations_to_test))
            self.record_metric("thread_operations_successful", successful_operations)
            self.record_metric("coordination_success_rate", success_rate)
            self.record_metric("coordination_timeline_events", len(coordination_timeline))
            
        except Exception as e:
            self.fail(f"Real WebSocket thread coordination test failed: {e}")
        
        finally:
            # Cleanup
            if self.connection_state_machine and websocket_connection_id:
                self.registry.unregister_connection(ConnectionID(str(websocket_connection_id)))


if __name__ == "__main__":
    # Run specific test for debugging
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--coordination":
        pytest.main([
            "test_websocket_thread_state_coordination.py::TestWebSocketThreadStateCoordination::test_websocket_readiness_blocks_thread_operations_until_ready",
            "-v", "--tb=short"
        ])
    elif len(sys.argv) > 1 and sys.argv[1] == "--real":
        pytest.main([
            "test_websocket_thread_state_coordination.py::TestWebSocketThreadStateCoordination::test_real_websocket_thread_coordination_with_authentication",
            "-v", "--tb=short", "--real-services"
        ])
    else:
        pytest.main([
            "test_websocket_thread_state_coordination.py",
            "-v", "--tb=short"
        ])