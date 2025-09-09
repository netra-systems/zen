"""
Test Core WebSocket State Machine Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable WebSocket connection state management
- Value Impact: Eliminates race conditions and ensures consistent connection state tracking
- Strategic Impact: Foundation for $500K+ ARR chat functionality and real-time AI interactions

This comprehensive test suite validates the ConnectionStateMachine functionality that is critical
for maintaining consistent WebSocket connection states across the platform. These tests ensure
that state transitions, persistence, and integration with the broader application work correctly.

CRITICAL: These tests validate the state machine that solves the core race condition issue
where WebSocket "accepted" (transport ready) was conflated with "ready to process messages".
"""

import pytest
import asyncio
import json
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

from netra_backend.app.websocket_core.connection_state_machine import (
    ConnectionStateMachine,
    ApplicationConnectionState,
    ConnectionStateMachineRegistry,
    StateTransitionInfo,
    get_connection_state_registry,
    get_connection_state_machine,
    is_connection_ready_for_messages
)


class TestCoreStateMachineIntegration(BaseIntegrationTest):
    """Comprehensive tests for WebSocket connection state machine core functionality."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_001_state_machine_initialization_and_default_state(self, real_services_fixture):
        """
        Test state machine initialization with proper default state.
        
        Business Value: Ensures connections start in a known, safe state that prevents
        premature message processing and maintains system stability.
        """
        # Create test user context
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'state_init_test@netra.ai',
            'name': 'State Init Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_{int(time.time())}"
        
        # Initialize state machine
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Verify default state
        assert state_machine.current_state == ApplicationConnectionState.CONNECTING
        assert not state_machine.is_operational
        assert not state_machine.is_ready_for_messages
        
        # Verify initialization metadata
        metrics = state_machine.get_metrics()
        assert metrics['current_state'] == ApplicationConnectionState.CONNECTING.value
        assert metrics['total_transitions'] == 0
        assert metrics['failed_transitions'] == 0
        assert not metrics['is_operational']
        assert not metrics['is_ready_for_messages']
        
        # Verify state history is empty initially
        history = state_machine.get_state_history()
        assert len(history) == 0
        
        self.assert_business_value_delivered({
            'safe_initialization': True,
            'proper_default_state': True,
            'no_premature_message_processing': True
        }, 'stability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_002_valid_state_transition_sequences(self, real_services_fixture):
        """
        Test complete valid state transition sequences from CONNECTING to PROCESSING_READY.
        
        Business Value: Validates the complete connection setup flow that enables
        reliable chat interactions and agent execution.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'valid_transitions_test@netra.ai',
            'name': 'Valid Transitions Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_valid_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Track transitions
        transitions_made = []
        def track_transitions(transition_info):
            transitions_made.append(transition_info)
        
        state_machine.add_state_change_callback(track_transitions)
        
        # Complete transition sequence
        transition_sequence = [
            (ApplicationConnectionState.ACCEPTED, "websocket_accepted"),
            (ApplicationConnectionState.AUTHENTICATED, "user_authenticated"),
            (ApplicationConnectionState.SERVICES_READY, "services_initialized"),
            (ApplicationConnectionState.PROCESSING_READY, "ready_for_messages"),
            (ApplicationConnectionState.PROCESSING, "message_processing_started"),
            (ApplicationConnectionState.IDLE, "no_active_processing"),
            (ApplicationConnectionState.CLOSING, "client_disconnect"),
            (ApplicationConnectionState.CLOSED, "connection_terminated")
        ]
        
        for target_state, reason in transition_sequence:
            success = state_machine.transition_to(target_state, reason)
            assert success, f"Failed to transition to {target_state.value}"
            assert state_machine.current_state == target_state
        
        # Verify all transitions were recorded
        assert len(transitions_made) == len(transition_sequence)
        
        # Verify transition details
        for i, (expected_state, expected_reason) in enumerate(transition_sequence):
            transition = transitions_made[i]
            assert transition.to_state == expected_state
            assert transition.reason == expected_reason
            assert isinstance(transition.timestamp, datetime)
        
        # Verify operational states were correctly identified
        operational_transitions = [t for t in transitions_made 
                                 if ApplicationConnectionState.is_operational(t.to_state)]
        assert len(operational_transitions) >= 3  # PROCESSING_READY, PROCESSING, IDLE
        
        self.assert_business_value_delivered({
            'complete_transition_flow': True,
            'operational_state_tracking': True,
            'transition_history': True
        }, 'reliability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_003_invalid_state_transition_rejection(self, real_services_fixture):
        """
        Test that invalid state transitions are properly rejected and logged.
        
        Business Value: Prevents connection state corruption that could lead to
        lost messages or system instability.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'invalid_transitions_test@netra.ai',
            'name': 'Invalid Transitions Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_invalid_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Test invalid transitions from CONNECTING state
        invalid_transitions = [
            ApplicationConnectionState.PROCESSING_READY,  # Skip intermediate states
            ApplicationConnectionState.PROCESSING,        # Can't process without setup
            ApplicationConnectionState.IDLE,             # Can't be idle without being ready
            ApplicationConnectionState.DEGRADED          # Can't degrade before being operational
        ]
        
        initial_state = state_machine.current_state
        initial_metrics = state_machine.get_metrics()
        
        for invalid_state in invalid_transitions:
            success = state_machine.transition_to(invalid_state, "invalid_attempt")
            assert not success, f"Should not allow transition to {invalid_state.value}"
            assert state_machine.current_state == initial_state, "State should not change on invalid transition"
        
        # Verify failed transitions were counted
        final_metrics = state_machine.get_metrics()
        assert final_metrics['failed_transitions'] == len(invalid_transitions)
        assert final_metrics['total_transitions'] == initial_metrics['total_transitions']
        
        # Test valid transition still works after invalid attempts
        success = state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "valid_after_invalid")
        assert success, "Valid transitions should work after invalid attempts"
        assert state_machine.current_state == ApplicationConnectionState.ACCEPTED
        
        self.assert_business_value_delivered({
            'invalid_transition_prevention': True,
            'state_corruption_prevention': True,
            'failure_tracking': True
        }, 'stability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_004_state_transition_callback_notification_system(self, real_services_fixture):
        """
        Test the state transition callback notification system.
        
        Business Value: Enables other system components to react to connection state changes,
        supporting features like message queuing and reconnection logic.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'callbacks_test@netra.ai',
            'name': 'Callbacks Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_callbacks_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Multiple callback handlers to test
        callback_1_calls = []
        callback_2_calls = []
        callback_3_calls = []
        
        def callback_1(transition_info):
            callback_1_calls.append({
                'from': transition_info.from_state,
                'to': transition_info.to_state,
                'reason': transition_info.reason,
                'timestamp': transition_info.timestamp
            })
        
        def callback_2(transition_info):
            callback_2_calls.append(transition_info.to_state)
        
        def callback_3(transition_info):
            # Callback that tracks operational state changes only
            if ApplicationConnectionState.is_operational(transition_info.to_state):
                callback_3_calls.append(f"operational: {transition_info.to_state.value}")
        
        # Add callbacks
        state_machine.add_state_change_callback(callback_1)
        state_machine.add_state_change_callback(callback_2)
        state_machine.add_state_change_callback(callback_3)
        
        # Perform transitions
        transitions = [
            (ApplicationConnectionState.ACCEPTED, "websocket_accepted"),
            (ApplicationConnectionState.AUTHENTICATED, "auth_complete"),
            (ApplicationConnectionState.SERVICES_READY, "services_ready"),
            (ApplicationConnectionState.PROCESSING_READY, "ready_to_process")
        ]
        
        for target_state, reason in transitions:
            state_machine.transition_to(target_state, reason)
        
        # Verify all callbacks were called
        assert len(callback_1_calls) == len(transitions)
        assert len(callback_2_calls) == len(transitions)
        assert len(callback_3_calls) == 1  # Only PROCESSING_READY is operational
        
        # Verify callback details
        for i, (expected_state, expected_reason) in enumerate(transitions):
            assert callback_1_calls[i]['to'] == expected_state
            assert callback_1_calls[i]['reason'] == expected_reason
            assert callback_2_calls[i] == expected_state
        
        # Verify operational callback
        assert callback_3_calls[0] == "operational: processing_ready"
        
        # Test callback removal
        state_machine.remove_state_change_callback(callback_2)
        
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "processing_started")
        
        # Verify removed callback wasn't called
        assert len(callback_1_calls) == 5  # Should be called
        assert len(callback_2_calls) == 4  # Should not be called
        assert len(callback_3_calls) == 2  # Should be called (PROCESSING is operational)
        
        self.assert_business_value_delivered({
            'callback_notification_system': True,
            'multiple_callback_support': True,
            'callback_management': True
        }, 'extensibility')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_005_connection_state_persistence_redis_integration(self, real_services_fixture):
        """
        Test connection state persistence in Redis for application state tracking.
        
        Business Value: Enables connection state recovery and monitoring across 
        service restarts and load balancer changes.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'persistence_test@netra.ai',
            'name': 'Persistence Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_persist_{int(time.time())}"
        
        redis_client = real_services_fixture["redis"]
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Setup persistence callback
        async def persist_state_to_redis(transition_info):
            state_data = {
                'connection_id': connection_id,
                'user_id': user_id,
                'current_state': transition_info.to_state.value,
                'timestamp': transition_info.timestamp.isoformat(),
                'reason': transition_info.reason,
                'metadata': transition_info.metadata
            }
            
            # Store in Redis
            state_key = f"connection_state:{connection_id}"
            await redis_client.set(state_key, json.dumps(state_data), ex=3600)
            
            # Track user connections
            user_connections_key = f"user_connections:{user_id}"
            await redis_client.sadd(user_connections_key, connection_id)
            await redis_client.expire(user_connections_key, 3600)
        
        state_machine.add_state_change_callback(
            lambda t: asyncio.create_task(persist_state_to_redis(t))
        )
        
        # Perform state transitions
        transitions = [
            (ApplicationConnectionState.ACCEPTED, "websocket_accepted"),
            (ApplicationConnectionState.AUTHENTICATED, "user_authenticated"),
            (ApplicationConnectionState.PROCESSING_READY, "ready_for_processing")
        ]
        
        for target_state, reason in transitions:
            state_machine.transition_to(target_state, reason)
            await asyncio.sleep(0.1)  # Allow persistence to complete
        
        # Verify state is persisted in Redis
        state_key = f"connection_state:{connection_id}"
        persisted_data_json = await redis_client.get(state_key)
        assert persisted_data_json is not None, "State should be persisted in Redis"
        
        persisted_data = json.loads(persisted_data_json)
        assert persisted_data['connection_id'] == connection_id
        assert persisted_data['user_id'] == user_id
        assert persisted_data['current_state'] == ApplicationConnectionState.PROCESSING_READY.value
        assert persisted_data['reason'] == "ready_for_processing"
        
        # Verify user connections tracking
        user_connections_key = f"user_connections:{user_id}"
        user_connections = await redis_client.smembers(user_connections_key)
        assert connection_id in {conn.decode() if isinstance(conn, bytes) else conn 
                                for conn in user_connections}
        
        # Test state recovery simulation
        # Create new state machine with same connection ID
        recovered_state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Simulate recovery by setting state from Redis
        recovered_state_machine.transition_to(
            ApplicationConnectionState(persisted_data['current_state']),
            "recovered_from_redis"
        )
        
        assert recovered_state_machine.current_state == ApplicationConnectionState.PROCESSING_READY
        assert recovered_state_machine.is_ready_for_messages
        
        # Cleanup
        await redis_client.delete(state_key)
        await redis_client.delete(user_connections_key)
        
        self.assert_business_value_delivered({
            'state_persistence': True,
            'redis_integration': True,
            'state_recovery_capability': True
        }, 'reliability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_006_registry_connection_registration_and_retrieval(self, real_services_fixture):
        """
        Test ConnectionStateMachineRegistry registration and retrieval functionality.
        
        Business Value: Provides centralized connection state management for 
        monitoring and coordination across the platform.
        """
        # Create multiple test users
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'registry_test_{i}@netra.ai',
                'name': f'Registry Test User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        registry = ConnectionStateMachineRegistry()
        
        # Register multiple connections
        registered_machines = []
        for i, user_data in enumerate(users):
            user_id = ensure_user_id(user_data['id'])
            connection_id = f"test_conn_registry_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            registered_machines.append((connection_id, machine))
            
            # Verify registration
            assert machine is not None
            assert isinstance(machine, ConnectionStateMachine)
            assert str(machine.connection_id) == connection_id
            assert machine.user_id == user_id
        
        # Test retrieval
        for connection_id, original_machine in registered_machines:
            retrieved_machine = registry.get_connection_state_machine(connection_id)
            assert retrieved_machine is original_machine, "Should retrieve exact same instance"
        
        # Test duplicate registration (should return existing)
        connection_id_0, machine_0 = registered_machines[0]
        duplicate_machine = registry.register_connection(connection_id_0, users[0]['id'])
        assert duplicate_machine is machine_0, "Duplicate registration should return existing machine"
        
        # Test non-existent connection
        non_existent = registry.get_connection_state_machine("non_existent_connection")
        assert non_existent is None, "Non-existent connection should return None"
        
        # Test registry statistics
        stats = registry.get_registry_stats()
        assert stats['total_connections'] == 3
        assert stats['registry_size'] == 3
        
        # Test operational connections (none operational yet as all in CONNECTING state)
        operational = registry.get_all_operational_connections()
        assert len(operational) == 0, "No connections should be operational initially"
        
        # Make one connection operational
        machine_0.transition_to(ApplicationConnectionState.ACCEPTED, "test")
        machine_0.transition_to(ApplicationConnectionState.AUTHENTICATED, "test")
        machine_0.transition_to(ApplicationConnectionState.PROCESSING_READY, "test")
        
        operational = registry.get_all_operational_connections()
        assert len(operational) == 1
        assert connection_id_0 in operational
        
        # Test connections by state
        ready_connections = registry.get_connections_by_state(ApplicationConnectionState.PROCESSING_READY)
        assert len(ready_connections) == 1
        assert connection_id_0 in ready_connections
        
        connecting_connections = registry.get_connections_by_state(ApplicationConnectionState.CONNECTING)
        assert len(connecting_connections) == 2  # The other two connections
        
        # Test unregistration
        unregistered = registry.unregister_connection(connection_id_0)
        assert unregistered, "Should successfully unregister existing connection"
        
        unregistered_again = registry.unregister_connection(connection_id_0)
        assert not unregistered_again, "Should not unregister non-existent connection"
        
        # Verify connection is removed
        retrieved_after_removal = registry.get_connection_state_machine(connection_id_0)
        assert retrieved_after_removal is None
        
        final_stats = registry.get_registry_stats()
        assert final_stats['total_connections'] == 2
        
        self.assert_business_value_delivered({
            'centralized_connection_management': True,
            'connection_registration': True,
            'registry_statistics': True
        }, 'management')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_007_registry_multi_connection_management(self, real_services_fixture):
        """
        Test registry management of multiple connections with state filtering.
        
        Business Value: Enables monitoring and management of multiple concurrent 
        connections for operational visibility and debugging.
        """
        # Create test users with different connection patterns
        users = []
        for i in range(5):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'multi_conn_test_{i}@netra.ai',
                'name': f'Multi Connection Test User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        registry = ConnectionStateMachineRegistry()
        connections = []
        
        # Create connections in different states
        connection_states = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING
        ]
        
        for i, (user_data, target_state) in enumerate(zip(users, connection_states)):
            user_id = ensure_user_id(user_data['id'])
            connection_id = f"multi_conn_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Transition to target state
            if target_state != ApplicationConnectionState.CONNECTING:
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            if target_state in [ApplicationConnectionState.AUTHENTICATED, 
                              ApplicationConnectionState.PROCESSING_READY, 
                              ApplicationConnectionState.PROCESSING]:
                machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            if target_state in [ApplicationConnectionState.PROCESSING_READY, 
                              ApplicationConnectionState.PROCESSING]:
                machine.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
            if target_state == ApplicationConnectionState.PROCESSING:
                machine.transition_to(ApplicationConnectionState.PROCESSING, "setup")
            
            connections.append((connection_id, machine, target_state))
        
        # Test state-based filtering
        for state in connection_states:
            filtered_connections = registry.get_connections_by_state(state)
            expected_count = 1
            assert len(filtered_connections) == expected_count, f"Should have {expected_count} connection in {state.value}"
        
        # Test operational connections filtering
        operational_connections = registry.get_all_operational_connections()
        operational_states = {ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING}
        expected_operational = sum(1 for _, _, state in connections if state in operational_states)
        assert len(operational_connections) == expected_operational
        
        # Test registry statistics
        stats = registry.get_registry_stats()
        assert stats['total_connections'] == 5
        assert stats['operational_connections'] == expected_operational
        
        # Verify state distribution in stats
        state_distribution = stats['state_distribution']
        for state in connection_states:
            assert state.value in state_distribution
            assert state_distribution[state.value] == 1
        
        # Test transition of multiple connections
        # Transition all to DEGRADED state for testing
        degraded_count = 0
        for connection_id, machine, current_state in connections:
            if ApplicationConnectionState.is_operational(current_state):
                machine.transition_to(ApplicationConnectionState.DEGRADED, "test_degradation")
                degraded_count += 1
        
        degraded_connections = registry.get_connections_by_state(ApplicationConnectionState.DEGRADED)
        assert len(degraded_connections) == degraded_count
        
        # Test cleanup of closed connections
        # Close some connections
        closed_connections = []
        for i, (connection_id, machine, _) in enumerate(connections[:2]):
            machine.transition_to(ApplicationConnectionState.CLOSING, "test_close")
            machine.transition_to(ApplicationConnectionState.CLOSED, "test_close")
            closed_connections.append(connection_id)
        
        # Verify closed connections are tracked
        closed = registry.get_connections_by_state(ApplicationConnectionState.CLOSED)
        assert len(closed) == 2
        
        # Test cleanup functionality
        cleaned_count = registry.cleanup_closed_connections()
        assert cleaned_count == 2, "Should clean up 2 closed connections"
        
        # Verify cleanup worked
        final_stats = registry.get_registry_stats()
        assert final_stats['total_connections'] == 3, "Should have 3 connections after cleanup"
        
        # Verify closed connections are no longer retrievable
        for connection_id in closed_connections:
            machine = registry.get_connection_state_machine(connection_id)
            assert machine is None, "Closed connections should not be retrievable after cleanup"
        
        self.assert_business_value_delivered({
            'multi_connection_management': True,
            'state_based_filtering': True,
            'connection_cleanup': True
        }, 'scalability')

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_008_state_machine_metrics_and_history_tracking(self, real_services_fixture):
        """
        Test comprehensive state machine metrics and transition history tracking.
        
        Business Value: Provides operational visibility into connection health and 
        performance for monitoring and debugging.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'metrics_test@netra.ai',
            'name': 'Metrics Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_metrics_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Capture initial metrics
        initial_metrics = state_machine.get_metrics()
        initial_time = time.time()
        
        # Verify initial metrics
        assert initial_metrics['total_transitions'] == 0
        assert initial_metrics['failed_transitions'] == 0
        assert initial_metrics['setup_duration_seconds'] == 0.0
        assert not initial_metrics['is_operational']
        assert not initial_metrics['is_ready_for_messages']
        assert initial_metrics['current_state'] == ApplicationConnectionState.CONNECTING.value
        
        # Perform successful transitions
        successful_transitions = [
            (ApplicationConnectionState.ACCEPTED, "websocket_accepted"),
            (ApplicationConnectionState.AUTHENTICATED, "user_auth_success"),
            (ApplicationConnectionState.SERVICES_READY, "services_initialized"),
            (ApplicationConnectionState.PROCESSING_READY, "ready_to_process")
        ]
        
        for target_state, reason in successful_transitions:
            state_machine.transition_to(target_state, reason)
            await asyncio.sleep(0.01)  # Small delay to track timing
        
        # Capture metrics after successful transitions
        success_metrics = state_machine.get_metrics()
        
        # Verify successful transition metrics
        assert success_metrics['total_transitions'] == len(successful_transitions)
        assert success_metrics['failed_transitions'] == 0
        assert success_metrics['setup_duration_seconds'] > 0
        assert success_metrics['is_operational']
        assert success_metrics['is_ready_for_messages']
        assert success_metrics['current_state'] == ApplicationConnectionState.PROCESSING_READY.value
        
        # Test failed transitions
        failed_attempts = [
            (ApplicationConnectionState.CONNECTING, "invalid_backward"),  # Can't go back
            (ApplicationConnectionState.ACCEPTED, "invalid_backward"),    # Can't go back
            (ApplicationConnectionState.CLOSED, "invalid_jump")           # Can't jump to terminal
        ]
        
        for invalid_state, reason in failed_attempts:
            state_machine.transition_to(invalid_state, reason)
        
        # Capture metrics after failed transitions
        failure_metrics = state_machine.get_metrics()
        
        # Verify failed transition metrics
        assert failure_metrics['total_transitions'] == len(successful_transitions)  # No new successful transitions
        assert failure_metrics['failed_transitions'] == len(failed_attempts)
        assert failure_metrics['current_state'] == ApplicationConnectionState.PROCESSING_READY.value  # State unchanged
        
        # Test transition history
        history = state_machine.get_state_history()
        assert len(history) == len(successful_transitions), "History should only include successful transitions"
        
        # Verify history details
        for i, (expected_state, expected_reason) in enumerate(successful_transitions):
            transition = history[i]
            assert isinstance(transition, StateTransitionInfo)
            assert transition.to_state == expected_state
            assert transition.reason == expected_reason
            assert isinstance(transition.timestamp, datetime)
            
            # Verify from_state progression
            if i == 0:
                assert transition.from_state == ApplicationConnectionState.CONNECTING
            else:
                assert transition.from_state == successful_transitions[i-1][0]
        
        # Test setup phase tracking
        setup_phases = success_metrics['setup_phases_completed']
        expected_phases = [
            ApplicationConnectionState.ACCEPTED.value,
            ApplicationConnectionState.AUTHENTICATED.value,
            ApplicationConnectionState.SERVICES_READY.value
        ]
        
        for phase in expected_phases:
            assert phase in setup_phases, f"Setup phase {phase} should be tracked"
        
        # Test timing metrics
        setup_duration = success_metrics['setup_duration_seconds']
        assert setup_duration > 0, "Setup duration should be positive"
        assert setup_duration < 10, "Setup duration should be reasonable (< 10 seconds for test)"
        
        # Test last activity tracking
        last_activity = success_metrics['last_activity']
        assert last_activity >= initial_time, "Last activity should be after initial time"
        assert last_activity <= time.time(), "Last activity should not be in future"
        
        # Test operational state transitions
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "start_processing")
        state_machine.transition_to(ApplicationConnectionState.IDLE, "processing_complete")
        
        final_metrics = state_machine.get_metrics()
        assert final_metrics['total_transitions'] == len(successful_transitions) + 2
        assert final_metrics['is_operational']
        assert final_metrics['is_ready_for_messages']
        
        self.assert_business_value_delivered({
            'comprehensive_metrics': True,
            'transition_history_tracking': True,
            'performance_monitoring': True
        }, 'observability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_009_thread_safe_concurrent_state_transitions(self, real_services_fixture):
        """
        Test thread-safe concurrent state transitions under load.
        
        Business Value: Ensures state machine integrity under concurrent operations,
        preventing race conditions that could corrupt connection state.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'concurrent_test@netra.ai',
            'name': 'Concurrent Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_concurrent_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Setup concurrent execution tracking
        successful_transitions = []
        failed_transitions = []
        transition_lock = threading.Lock()
        
        def track_transition_result(success, transition_info):
            with transition_lock:
                if success:
                    successful_transitions.append(transition_info)
                else:
                    failed_transitions.append(transition_info)
        
        # Transition to a base state first
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Define concurrent transition scenarios
        # Multiple threads trying different valid transitions from PROCESSING_READY
        concurrent_transitions = [
            (ApplicationConnectionState.PROCESSING, "start_processing_1", 0.01),
            (ApplicationConnectionState.PROCESSING, "start_processing_2", 0.01),
            (ApplicationConnectionState.IDLE, "go_idle_1", 0.02),
            (ApplicationConnectionState.IDLE, "go_idle_2", 0.02),
            (ApplicationConnectionState.DEGRADED, "network_issue_1", 0.01),
            (ApplicationConnectionState.DEGRADED, "network_issue_2", 0.01),
            (ApplicationConnectionState.PROCESSING, "start_processing_3", 0.03),
            (ApplicationConnectionState.IDLE, "go_idle_3", 0.03)
        ]
        
        def concurrent_transition_worker(target_state, reason, delay):
            """Worker function for concurrent transition attempts."""
            time.sleep(delay)  # Stagger the attempts
            success = state_machine.transition_to(target_state, reason)
            track_transition_result(success, (target_state, reason, threading.current_thread().ident))
        
        # Launch concurrent transition attempts
        threads = []
        for target_state, reason, delay in concurrent_transitions:
            thread = threading.Thread(
                target=concurrent_transition_worker,
                args=(target_state, reason, delay)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)  # 5 second timeout
            assert not thread.is_alive(), "Thread should complete within timeout"
        
        # Verify thread safety - exactly one transition should succeed per attempt
        # (Some may fail due to timing, but no corruption should occur)
        total_attempts = len(concurrent_transitions)
        with transition_lock:
            total_results = len(successful_transitions) + len(failed_transitions)
            assert total_results == total_attempts, "All transition attempts should be accounted for"
        
        # Verify state machine is in a valid state
        final_state = state_machine.current_state
        valid_final_states = {
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.IDLE,
            ApplicationConnectionState.DEGRADED
        }
        assert final_state in valid_final_states, f"Final state {final_state} should be valid"
        
        # Verify metrics consistency
        metrics = state_machine.get_metrics()
        history = state_machine.get_state_history()
        
        # Total transitions should match successful transitions count
        # (Initial setup transitions + concurrent successful transitions)
        expected_successful = 3 + len(successful_transitions)  # 3 setup + concurrent successes
        assert metrics['total_transitions'] == expected_successful
        
        # Failed transitions should match failed attempts
        assert metrics['failed_transitions'] == len(failed_transitions)
        
        # History should be consistent
        assert len(history) == expected_successful
        
        # Test state consistency after concurrent operations
        # The state machine should still work normally
        if final_state != ApplicationConnectionState.IDLE:
            normal_transition = state_machine.transition_to(ApplicationConnectionState.IDLE, "post_concurrent_test")
            assert normal_transition, "State machine should work normally after concurrent operations"
        
        # Test concurrent callback notifications
        callback_calls = []
        callback_lock = threading.Lock()
        
        def concurrent_callback(transition_info):
            with callback_lock:
                callback_calls.append({
                    'state': transition_info.to_state,
                    'thread': threading.current_thread().ident,
                    'timestamp': transition_info.timestamp
                })
        
        state_machine.add_state_change_callback(concurrent_callback)
        
        # Perform more concurrent transitions with callback
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "callback_test")
        state_machine.transition_to(ApplicationConnectionState.IDLE, "callback_test")
        
        # Verify callbacks were called safely
        with callback_lock:
            assert len(callback_calls) == 2, "Callbacks should be called for each transition"
        
        self.assert_business_value_delivered({
            'thread_safe_operations': True,
            'concurrent_transition_integrity': True,
            'race_condition_prevention': True
        }, 'reliability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_010_state_machine_rollback_on_transition_failures(self, real_services_fixture):
        """
        Test state machine rollback functionality when transitions fail.
        
        Business Value: Ensures system consistency by preventing partial state 
        updates that could lead to undefined behavior.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'rollback_test@netra.ai',
            'name': 'Rollback Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_rollback_{int(time.time())}"
        
        # Create state machine with controlled failure injection
        class FailureInjectingStateMachine(ConnectionStateMachine):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fail_next_transition = False
                self.failure_reason = "test_failure"
            
            def transition_to(self, new_state, reason=None, metadata=None):
                if self.fail_next_transition:
                    # Simulate failure during transition
                    old_state = self._current_state
                    
                    # Temporarily change state to simulate partial update
                    self._current_state = new_state
                    
                    # Reset flag
                    self.fail_next_transition = False
                    
                    # Simulate exception during processing
                    raise Exception(self.failure_reason)
                
                return super().transition_to(new_state, reason, metadata)
        
        state_machine = FailureInjectingStateMachine(connection_id, user_id)
        
        # Establish initial state
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        
        initial_state = state_machine.current_state
        initial_metrics = state_machine.get_metrics()
        
        # Setup failure injection
        state_machine.fail_next_transition = True
        state_machine.failure_reason = "simulated_transition_failure"
        
        # Attempt transition that will fail
        try:
            state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, "should_fail")
            assert False, "Transition should have failed"
        except Exception as e:
            assert "simulated_transition_failure" in str(e)
        
        # Verify rollback occurred
        assert state_machine.current_state == initial_state, "State should be rolled back to initial state"
        
        # Verify metrics reflect the failure
        post_failure_metrics = state_machine.get_metrics()
        assert post_failure_metrics['failed_transitions'] == initial_metrics['failed_transitions'] + 1
        assert post_failure_metrics['total_transitions'] == initial_metrics['total_transitions']
        
        # Verify history doesn't include failed transition
        history = state_machine.get_state_history()
        assert len(history) == 2, "History should not include failed transition"
        assert history[-1].to_state == ApplicationConnectionState.AUTHENTICATED
        
        # Test that normal transitions still work after rollback
        success = state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, "recovery_attempt")
        assert success, "Normal transitions should work after rollback"
        assert state_machine.current_state == ApplicationConnectionState.SERVICES_READY
        
        # Test multiple consecutive failures with rollback
        for i in range(3):
            state_machine.fail_next_transition = True
            state_machine.failure_reason = f"consecutive_failure_{i}"
            
            try:
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"attempt_{i}")
                assert False, f"Attempt {i} should have failed"
            except Exception as e:
                assert f"consecutive_failure_{i}" in str(e)
        
        # Verify state remains consistent after multiple failures
        assert state_machine.current_state == ApplicationConnectionState.SERVICES_READY
        
        # Verify failure count accumulated
        final_metrics = state_machine.get_metrics()
        assert final_metrics['failed_transitions'] == initial_metrics['failed_transitions'] + 4  # 1 + 3 consecutive
        
        # Test recovery after multiple failures
        final_success = state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "final_recovery")
        assert final_success, "Should be able to recover after multiple failures"
        assert state_machine.current_state == ApplicationConnectionState.PROCESSING_READY
        
        # Test callback behavior during rollback
        callback_calls = []
        
        def rollback_callback(transition_info):
            callback_calls.append({
                'from': transition_info.from_state,
                'to': transition_info.to_state,
                'reason': transition_info.reason
            })
        
        state_machine.add_state_change_callback(rollback_callback)
        
        # Test callback during successful transition
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "callback_test")
        assert len(callback_calls) == 1
        
        # Test callback during failed transition (should not be called)
        state_machine.fail_next_transition = True
        state_machine.failure_reason = "callback_failure_test"
        
        try:
            state_machine.transition_to(ApplicationConnectionState.IDLE, "should_fail_with_callback")
            assert False, "Should have failed"
        except Exception:
            pass
        
        # Callback should not be called for failed transition
        assert len(callback_calls) == 1, "Callback should not be called for failed transition"
        
        # Verify final state consistency
        assert state_machine.current_state == ApplicationConnectionState.PROCESSING
        assert state_machine.is_operational
        assert state_machine.is_ready_for_messages
        
        self.assert_business_value_delivered({
            'rollback_on_failure': True,
            'state_consistency': True,
            'failure_recovery': True
        }, 'reliability')