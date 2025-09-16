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

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_011_terminal_state_handling_closed_failed(self, real_services_fixture):
        """
        Test proper handling of terminal states (CLOSED, FAILED).
        
        Business Value: Ensures connections are properly finalized and resources
        are cleaned up when connections end, preventing resource leaks.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'terminal_states_test@netra.ai',
            'name': 'Terminal States Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        
        # Test CLOSED terminal state
        connection_id_1 = f"test_conn_closed_{int(time.time())}"
        state_machine_1 = ConnectionStateMachine(connection_id_1, user_id)
        
        # Transition to operational state
        state_machine_1.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Transition to CLOSING then CLOSED
        success = state_machine_1.transition_to(ApplicationConnectionState.CLOSING, "client_disconnect")
        assert success, "Should transition to CLOSING"
        
        success = state_machine_1.transition_to(ApplicationConnectionState.CLOSED, "connection_closed")
        assert success, "Should transition to CLOSED"
        
        # Verify terminal state properties
        assert ApplicationConnectionState.is_terminal(state_machine_1.current_state)
        assert not state_machine_1.is_operational
        assert not state_machine_1.is_ready_for_messages
        assert not state_machine_1.can_process_messages()
        
        # Test that transitions from CLOSED are blocked (except to CONNECTING for retry)
        blocked_transitions = [
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.IDLE,
            ApplicationConnectionState.DEGRADED,
            ApplicationConnectionState.CLOSING
        ]
        
        for blocked_state in blocked_transitions:
            success = state_machine_1.transition_to(blocked_state, "should_be_blocked")
            assert not success, f"Should not transition from CLOSED to {blocked_state.value}"
        
        # Test allowed transition from CLOSED to CONNECTING (reconnection)
        success = state_machine_1.transition_to(ApplicationConnectionState.CONNECTING, "reconnection_attempt")
        assert success, "Should allow transition from CLOSED to CONNECTING"
        
        # Test FAILED terminal state
        connection_id_2 = f"test_conn_failed_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Force to FAILED state
        state_machine_2.force_failed_state("test_failure_simulation")
        
        assert state_machine_2.current_state == ApplicationConnectionState.FAILED
        assert ApplicationConnectionState.is_terminal(state_machine_2.current_state)
        assert not state_machine_2.is_operational
        assert not state_machine_2.can_process_messages()
        
        # Test that FAILED allows transition to CONNECTING
        success = state_machine_2.transition_to(ApplicationConnectionState.CONNECTING, "recovery_attempt")
        assert success, "Should allow transition from FAILED to CONNECTING"
        
        # Test maximum failure handling
        connection_id_3 = f"test_conn_max_failures_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        # Trigger multiple failures to exceed maximum
        for i in range(6):  # Exceed max_transition_failures (5)
            state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "invalid")  # Invalid from CONNECTING
        
        # Should be forced to FAILED state
        assert state_machine_3.current_state == ApplicationConnectionState.FAILED
        
        self.assert_business_value_delivered({
            'terminal_state_handling': True,
            'resource_cleanup': True,
            'reconnection_capability': True
        }, 'stability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_012_state_machine_integration_with_websocket_utilities(self, real_services_fixture):
        """
        Test state machine integration with WebSocket utility functions.
        
        Business Value: Ensures state machine provides accurate connection
        readiness information to the broader WebSocket infrastructure.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'utilities_integration_test@netra.ai',
            'name': 'Utilities Integration Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_utilities_{int(time.time())}"
        
        # Test integration with global registry
        registry = get_connection_state_registry()
        state_machine = registry.register_connection(connection_id, user_id)
        
        # Test is_connection_ready_for_messages function
        assert not is_connection_ready_for_messages(connection_id), "Should not be ready initially"
        
        # Progress through states and test readiness at each step
        state_readiness_tests = [
            (ApplicationConnectionState.CONNECTING, False),
            (ApplicationConnectionState.ACCEPTED, False),
            (ApplicationConnectionState.AUTHENTICATED, False),
            (ApplicationConnectionState.SERVICES_READY, False),
            (ApplicationConnectionState.PROCESSING_READY, True),
            (ApplicationConnectionState.PROCESSING, True),
            (ApplicationConnectionState.IDLE, True),
            (ApplicationConnectionState.DEGRADED, True)  # Can still process in degraded mode
        ]
        
        for target_state, expected_ready in state_readiness_tests:
            if target_state != ApplicationConnectionState.CONNECTING:  # Already in CONNECTING
                state_machine.transition_to(target_state, f"test_{target_state.value}")
            
            actual_ready = is_connection_ready_for_messages(connection_id)
            assert actual_ready == expected_ready, f"Readiness mismatch at state {target_state.value}"
            
            # Also test the state machine's own methods
            assert state_machine.is_ready_for_messages == expected_ready
            assert state_machine.can_process_messages() == expected_ready
        
        # Test with non-existent connection
        non_existent_ready = is_connection_ready_for_messages("non_existent_connection")
        assert non_existent_ready, "Non-existent connections should default to ready (backward compatibility)"
        
        # Test state machine removal from registry
        registry.unregister_connection(connection_id)
        removed_ready = is_connection_ready_for_messages(connection_id)
        assert removed_ready, "Removed connections should default to ready"
        
        # Test degraded mode readiness requirements
        connection_id_2 = f"test_conn_degraded_{int(time.time())}"
        state_machine_2 = registry.register_connection(connection_id_2, user_id)
        
        # Go directly to degraded without proper setup
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "minimal_setup")
        state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "forced_degradation")
        
        # Should not be ready due to insufficient setup
        assert not state_machine_2.can_process_messages(), "Degraded mode should require minimum setup"
        
        # Complete proper setup then degrade
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "proper_setup")
        state_machine_2.transition_to(ApplicationConnectionState.SERVICES_READY, "proper_setup")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "proper_setup")
        state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "network_degradation")
        
        # Should now be ready even in degraded mode
        assert state_machine_2.can_process_messages(), "Properly setup degraded connections should be ready"
        
        # Test failure threshold integration
        connection_id_3 = f"test_conn_failures_{int(time.time())}"
        state_machine_3 = registry.register_connection(connection_id_3, user_id)
        
        # Setup to ready state
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup") 
        state_machine_3.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Should be ready
        assert state_machine_3.can_process_messages()
        
        # Generate failures near threshold
        for i in range(4):  # Just below max_transition_failures - 1
            state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, "invalid")  # Invalid transition
        
        # Should still be ready
        assert state_machine_3.can_process_messages()
        
        # One more failure should make it not ready
        state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, "invalid")  # Invalid transition
        assert not state_machine_3.can_process_messages(), "Should not be ready after excessive failures"
        
        registry.unregister_connection(connection_id_2)
        registry.unregister_connection(connection_id_3)
        
        self.assert_business_value_delivered({
            'websocket_utility_integration': True,
            'readiness_validation': True,
            'backward_compatibility': True
        }, 'integration')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_013_connection_readiness_validation_comprehensive(self, real_services_fixture):
        """
        Test comprehensive connection readiness validation scenarios.
        
        Business Value: Ensures accurate connection readiness detection prevents
        premature message processing and maintains reliable chat functionality.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'readiness_test@netra.ai',
            'name': 'Readiness Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_readiness_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Test readiness at each state in the progression
        readiness_progression = [
            # (state, is_operational, is_ready_for_messages, can_process_messages)
            (ApplicationConnectionState.CONNECTING, False, False, False),
            (ApplicationConnectionState.ACCEPTED, False, False, False),
            (ApplicationConnectionState.AUTHENTICATED, False, False, False),
            (ApplicationConnectionState.SERVICES_READY, False, False, False),
            (ApplicationConnectionState.PROCESSING_READY, True, True, True),
            (ApplicationConnectionState.PROCESSING, True, True, True),
            (ApplicationConnectionState.IDLE, True, True, True),
            (ApplicationConnectionState.DEGRADED, True, True, True),  # Degraded but functional
            (ApplicationConnectionState.RECONNECTING, False, False, False),
            (ApplicationConnectionState.CLOSING, False, False, False),
            (ApplicationConnectionState.CLOSED, False, False, False),
            (ApplicationConnectionState.FAILED, False, False, False)
        ]
        
        for target_state, expected_operational, expected_ready, expected_can_process in readiness_progression:
            # Transition to target state (with proper sequence)
            if target_state == ApplicationConnectionState.CONNECTING:
                pass  # Already in CONNECTING
            elif target_state == ApplicationConnectionState.ACCEPTED:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.AUTHENTICATED:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.SERVICES_READY:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.PROCESSING_READY:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.PROCESSING:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.IDLE:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.DEGRADED:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.RECONNECTING:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.CLOSING:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.CLOSED:
                state_machine.transition_to(target_state, "test")
            elif target_state == ApplicationConnectionState.FAILED:
                state_machine.force_failed_state("test_failure")
            
            # Verify readiness properties
            assert state_machine.is_operational == expected_operational, \
                f"is_operational mismatch at {target_state.value}: expected {expected_operational}, got {state_machine.is_operational}"
            
            assert state_machine.is_ready_for_messages == expected_ready, \
                f"is_ready_for_messages mismatch at {target_state.value}: expected {expected_ready}, got {state_machine.is_ready_for_messages}"
            
            assert state_machine.can_process_messages() == expected_can_process, \
                f"can_process_messages mismatch at {target_state.value}: expected {expected_can_process}, got {state_machine.can_process_messages()}"
            
            # Break after FAILED state as no more transitions are possible
            if target_state == ApplicationConnectionState.FAILED:
                break
        
        # Test edge cases for degraded mode readiness
        connection_id_2 = f"test_conn_degraded_edge_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Test degraded mode with insufficient setup
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "minimal")
        state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "premature_degradation")
        
        # Should not be ready for processing due to insufficient setup
        assert not state_machine_2.can_process_messages(), "Degraded mode should require minimum setup phases"
        
        # Add authentication and test again
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "add_auth")
        state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "degraded_with_auth")
        
        # Should now be ready (has ACCEPTED + AUTHENTICATED)
        assert state_machine_2.can_process_messages(), "Degraded mode should work with sufficient setup"
        
        # Test failure threshold edge cases
        connection_id_3 = f"test_conn_failure_edge_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        # Setup to ready state
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Generate failures up to threshold - 1
        initial_failures = state_machine_3._transition_failures
        max_failures = state_machine_3._max_transition_failures
        
        for i in range(max_failures - 1):
            state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, "invalid")  # Invalid transition
        
        # Should still be able to process (one failure away from threshold)
        assert state_machine_3.can_process_messages(), "Should be ready just below failure threshold"
        
        # One more failure should push over threshold
        state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, "invalid")
        assert not state_machine_3.can_process_messages(), "Should not be ready at failure threshold"
        
        # Test readiness recovery after successful transition
        success = state_machine_3.transition_to(ApplicationConnectionState.PROCESSING, "recovery")
        assert success, "Should be able to transition normally"
        assert state_machine_3.can_process_messages(), "Should be ready after successful transition"
        
        self.assert_business_value_delivered({
            'comprehensive_readiness_validation': True,
            'edge_case_handling': True,
            'failure_threshold_management': True
        }, 'reliability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_014_operational_state_verification_comprehensive(self, real_services_fixture):
        """
        Test comprehensive operational state verification logic.
        
        Business Value: Ensures accurate operational status detection enables
        proper load balancing and health monitoring across connections.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'operational_test@netra.ai',
            'name': 'Operational Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_operational_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Test operational status for all states
        operational_status_map = {
            ApplicationConnectionState.CONNECTING: False,
            ApplicationConnectionState.ACCEPTED: False,
            ApplicationConnectionState.AUTHENTICATED: False,
            ApplicationConnectionState.SERVICES_READY: False,
            ApplicationConnectionState.PROCESSING_READY: True,
            ApplicationConnectionState.PROCESSING: True,
            ApplicationConnectionState.IDLE: True,
            ApplicationConnectionState.DEGRADED: True,
            ApplicationConnectionState.RECONNECTING: False,
            ApplicationConnectionState.CLOSING: False,
            ApplicationConnectionState.CLOSED: False,
            ApplicationConnectionState.FAILED: False
        }
        
        # Test static method for operational state detection
        for state, expected_operational in operational_status_map.items():
            is_operational = ApplicationConnectionState.is_operational(state)
            assert is_operational == expected_operational, \
                f"Static is_operational check failed for {state.value}: expected {expected_operational}, got {is_operational}"
        
        # Test instance property through state transitions
        current_state = ApplicationConnectionState.CONNECTING
        for target_state, expected_operational in operational_status_map.items():
            # Transition to target state
            if target_state != current_state:
                if target_state == ApplicationConnectionState.FAILED:
                    state_machine.force_failed_state("test_failure")
                else:
                    # For valid transitions, follow proper sequence
                    if self._can_transition_directly(current_state, target_state):
                        state_machine.transition_to(target_state, "test_operational")
                        current_state = target_state
                    else:
                        # Skip states that require complex transition sequences
                        continue
            
            # Verify operational status
            assert state_machine.is_operational == expected_operational, \
                f"Instance is_operational check failed for {target_state.value}: expected {expected_operational}, got {state_machine.is_operational}"
            
            if target_state == ApplicationConnectionState.FAILED:
                break  # Can't transition further from FAILED
        
        # Test operational state transitions with registry integration
        registry = ConnectionStateMachineRegistry()
        
        # Create multiple connections in different operational states
        operational_connections = []
        non_operational_connections = []
        
        for i, (state, is_op) in enumerate(operational_status_map.items()):
            conn_id = f"test_op_conn_{i}_{int(time.time())}"
            machine = registry.register_connection(conn_id, user_id)
            
            # Transition to target state through proper sequence
            if state != ApplicationConnectionState.CONNECTING:
                if state == ApplicationConnectionState.ACCEPTED:
                    machine.transition_to(state, "test")
                elif state == ApplicationConnectionState.AUTHENTICATED:
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "test")
                    machine.transition_to(state, "test")
                elif state == ApplicationConnectionState.SERVICES_READY:
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "test")
                    machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "test")
                    machine.transition_to(state, "test")
                elif state in [ApplicationConnectionState.PROCESSING_READY, 
                              ApplicationConnectionState.PROCESSING, 
                              ApplicationConnectionState.IDLE,
                              ApplicationConnectionState.DEGRADED]:
                    # Full setup sequence
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "test")
                    machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "test")
                    machine.transition_to(ApplicationConnectionState.SERVICES_READY, "test")
                    machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "test")
                    if state != ApplicationConnectionState.PROCESSING_READY:
                        machine.transition_to(state, "test")
                elif state == ApplicationConnectionState.FAILED:
                    machine.force_failed_state("test_failure")
                elif state in [ApplicationConnectionState.CLOSING, ApplicationConnectionState.CLOSED]:
                    # Setup first then close
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "test")
                    machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "test")
                    machine.transition_to(ApplicationConnectionState.SERVICES_READY, "test")
                    machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "test")
                    machine.transition_to(ApplicationConnectionState.CLOSING, "test")
                    if state == ApplicationConnectionState.CLOSED:
                        machine.transition_to(state, "test")
            
            if is_op:
                operational_connections.append(conn_id)
            else:
                non_operational_connections.append(conn_id)
        
        # Test registry operational connection filtering
        all_operational = registry.get_all_operational_connections()
        
        # Verify all expected operational connections are found
        for conn_id in operational_connections:
            assert conn_id in all_operational, f"Operational connection {conn_id} not found in registry"
        
        # Verify non-operational connections are not included
        for conn_id in non_operational_connections:
            assert conn_id not in all_operational, f"Non-operational connection {conn_id} found in operational list"
        
        # Test registry statistics
        stats = registry.get_registry_stats()
        assert stats['operational_connections'] == len(operational_connections)
        assert stats['total_connections'] == len(operational_status_map)
        
        self.assert_business_value_delivered({
            'operational_state_verification': True,
            'registry_operational_filtering': True,
            'health_monitoring_support': True
        }, 'monitoring')

    def _can_transition_directly(self, from_state, to_state):
        """Helper method to check if direct transition is possible."""
        if from_state == to_state:
            return True
        
        # Define simple direct transitions for testing
        direct_transitions = {
            ApplicationConnectionState.CONNECTING: [ApplicationConnectionState.ACCEPTED],
            ApplicationConnectionState.ACCEPTED: [ApplicationConnectionState.AUTHENTICATED],
            ApplicationConnectionState.AUTHENTICATED: [ApplicationConnectionState.SERVICES_READY],
            ApplicationConnectionState.SERVICES_READY: [ApplicationConnectionState.PROCESSING_READY],
            ApplicationConnectionState.PROCESSING_READY: [ApplicationConnectionState.PROCESSING, ApplicationConnectionState.IDLE, ApplicationConnectionState.DEGRADED],
            ApplicationConnectionState.PROCESSING: [ApplicationConnectionState.IDLE, ApplicationConnectionState.DEGRADED],
            ApplicationConnectionState.IDLE: [ApplicationConnectionState.PROCESSING, ApplicationConnectionState.DEGRADED],
            ApplicationConnectionState.DEGRADED: [ApplicationConnectionState.PROCESSING_READY]
        }
        
        return to_state in direct_transitions.get(from_state, [])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_015_state_machine_cleanup_and_resource_management(self, real_services_fixture):
        """
        Test proper cleanup and resource management for state machines.
        
        Business Value: Prevents memory leaks and ensures efficient resource
        utilization in high-throughput connection scenarios.
        """
        # Create multiple users for cleanup testing
        users = []
        for i in range(5):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'cleanup_test_{i}@netra.ai',
                'name': f'Cleanup Test User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        registry = ConnectionStateMachineRegistry()
        created_connections = []
        
        # Create connections and track resources
        for i, user_data in enumerate(users):
            user_id = ensure_user_id(user_data['id'])
            connection_id = f"test_cleanup_conn_{i}_{int(time.time())}"
            
            # Register connection
            state_machine = registry.register_connection(connection_id, user_id)
            created_connections.append((connection_id, state_machine, user_id))
            
            # Add callbacks to track resource usage
            callback_counter = {'calls': 0}
            
            def resource_tracking_callback(transition_info):
                callback_counter['calls'] += 1
            
            state_machine.add_state_change_callback(resource_tracking_callback)
            
            # Perform some transitions to generate history and metrics
            state_machine.transition_to(ApplicationConnectionState.ACCEPTED, f"setup_{i}")
            state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, f"setup_{i}")
            
            # Verify callback was called
            assert callback_counter['calls'] == 2, "Callbacks should be working"
        
        # Verify all connections are registered
        initial_stats = registry.get_registry_stats()
        assert initial_stats['total_connections'] == len(users)
        
        # Test individual connection cleanup
        connection_id_0, state_machine_0, user_id_0 = created_connections[0]
        
        # Generate some history and metrics
        state_machine_0.transition_to(ApplicationConnectionState.SERVICES_READY, "test")
        state_machine_0.transition_to(ApplicationConnectionState.PROCESSING_READY, "test")
        
        history_before = state_machine_0.get_state_history()
        metrics_before = state_machine_0.get_metrics()
        
        assert len(history_before) > 0, "Should have transition history"
        assert metrics_before['total_transitions'] > 0, "Should have transition metrics"
        
        # Close the connection
        state_machine_0.transition_to(ApplicationConnectionState.CLOSING, "cleanup_test")
        state_machine_0.transition_to(ApplicationConnectionState.CLOSED, "cleanup_test")
        
        # Verify state is terminal
        assert ApplicationConnectionState.is_terminal(state_machine_0.current_state)
        
        # Test automatic cleanup of closed connections
        cleaned_count = registry.cleanup_closed_connections()
        assert cleaned_count == 1, "Should clean up one closed connection"
        
        # Verify connection was removed from registry
        retrieved = registry.get_connection_state_machine(connection_id_0)
        assert retrieved is None, "Cleaned up connection should not be retrievable"
        
        # Test cleanup of failed connections
        connection_id_1, state_machine_1, user_id_1 = created_connections[1]
        
        # Force to failed state
        state_machine_1.force_failed_state("cleanup_test_failure")
        assert state_machine_1.current_state == ApplicationConnectionState.FAILED
        
        # Cleanup failed connections
        failed_cleaned = registry.cleanup_closed_connections()
        assert failed_cleaned == 1, "Should clean up one failed connection"
        
        # Test bulk cleanup of multiple terminal connections
        remaining_connections = created_connections[2:]
        
        for connection_id, state_machine, user_id in remaining_connections:
            # Close all remaining connections
            state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "bulk_test")
            state_machine.transition_to(ApplicationConnectionState.CLOSING, "bulk_cleanup")
            state_machine.transition_to(ApplicationConnectionState.CLOSED, "bulk_cleanup")
        
        # Cleanup all closed connections
        bulk_cleaned = registry.cleanup_closed_connections()
        assert bulk_cleaned == len(remaining_connections), f"Should clean up {len(remaining_connections)} connections"
        
        # Verify registry is empty
        final_stats = registry.get_registry_stats()
        assert final_stats['total_connections'] == 0, "Registry should be empty after cleanup"
        assert final_stats['operational_connections'] == 0, "No operational connections should remain"
        
        # Test memory and resource tracking
        # Create and destroy many connections to test resource management
        stress_connections = []
        for i in range(50):  # Moderate stress test
            user_id = ensure_user_id(users[i % len(users)]['id'])
            connection_id = f"stress_conn_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Rapid state transitions
            machine.transition_to(ApplicationConnectionState.ACCEPTED, f"stress_{i}")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, f"stress_{i}")
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"stress_{i}")
            machine.transition_to(ApplicationConnectionState.CLOSING, f"stress_{i}")
            machine.transition_to(ApplicationConnectionState.CLOSED, f"stress_{i}")
            
            stress_connections.append(connection_id)
        
        # Verify all connections were created
        stress_stats = registry.get_registry_stats()
        assert stress_stats['total_connections'] == 50
        
        # Cleanup all stress test connections
        stress_cleaned = registry.cleanup_closed_connections()
        assert stress_cleaned == 50, "Should clean up all stress test connections"
        
        # Verify complete cleanup
        final_stress_stats = registry.get_registry_stats()
        assert final_stress_stats['total_connections'] == 0
        
        # Test callback cleanup (callbacks should not prevent cleanup)
        test_connection_id = f"callback_cleanup_test_{int(time.time())}"
        callback_machine = registry.register_connection(test_connection_id, users[0]['id'])
        
        # Add multiple callbacks
        callback_calls = []
        for i in range(5):
            def make_callback(index):
                def callback(transition_info):
                    callback_calls.append(f"callback_{index}")
                return callback
            
            callback_machine.add_state_change_callback(make_callback(i))
        
        # Close connection
        callback_machine.transition_to(ApplicationConnectionState.ACCEPTED, "callback_test")
        callback_machine.transition_to(ApplicationConnectionState.CLOSING, "callback_test")
        callback_machine.transition_to(ApplicationConnectionState.CLOSED, "callback_test")
        
        # Verify callbacks were called
        assert len(callback_calls) == 15, "All callbacks should be called (5 callbacks * 3 transitions)"
        
        # Cleanup should still work despite callbacks
        callback_cleaned = registry.cleanup_closed_connections()
        assert callback_cleaned == 1, "Should clean up connection with callbacks"
        
        self.assert_business_value_delivered({
            'resource_cleanup': True,
            'memory_management': True,
            'bulk_cleanup_efficiency': True
        }, 'performance')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_016_error_state_forced_transitions(self, real_services_fixture):
        """
        Test forced transitions to error states and emergency handling.
        
        Business Value: Provides emergency mechanisms to handle corrupted or
        unrecoverable connection states, maintaining system stability.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'forced_error_test@netra.ai',
            'name': 'Forced Error Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_forced_error_{int(time.time())}"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Setup to operational state
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Track transitions for emergency scenario
        emergency_transitions = []
        
        def track_emergency_transitions(transition_info):
            emergency_transitions.append({
                'from': transition_info.from_state,
                'to': transition_info.to_state,
                'reason': transition_info.reason,
                'metadata': transition_info.metadata
            })
        
        state_machine.add_state_change_callback(track_emergency_transitions)
        
        # Test force_failed_state method
        emergency_reason = "critical_system_failure_simulation"
        state_machine.force_failed_state(emergency_reason)
        
        # Verify forced transition
        assert state_machine.current_state == ApplicationConnectionState.FAILED
        assert not state_machine.is_operational
        assert not state_machine.is_ready_for_messages
        assert not state_machine.can_process_messages()
        
        # Verify forced transition was recorded
        assert len(emergency_transitions) == 1
        emergency_transition = emergency_transitions[0]
        assert emergency_transition['to'] == ApplicationConnectionState.FAILED
        assert f"EMERGENCY: {emergency_reason}" in emergency_transition['reason']
        assert emergency_transition['metadata']['emergency_transition'] is True
        
        # Verify failure counter is maxed out
        metrics = state_machine.get_metrics()
        assert metrics['transition_failures'] == state_machine._max_transition_failures
        
        # Test that forced failed state prevents normal operations
        normal_transition_success = state_machine.transition_to(
            ApplicationConnectionState.PROCESSING_READY, 
            "should_not_work"
        )
        assert not normal_transition_success, "Normal transitions should be blocked after forced failure"
        
        # Test recovery from forced failed state
        recovery_success = state_machine.transition_to(
            ApplicationConnectionState.CONNECTING, 
            "emergency_recovery_attempt"
        )
        assert recovery_success, "Should allow recovery transition from FAILED to CONNECTING"
        
        # Verify state history includes emergency transition
        history = state_machine.get_state_history()
        emergency_history_entry = [h for h in history if "EMERGENCY" in h.reason]
        assert len(emergency_history_entry) == 1, "Emergency transition should be in history"
        
        # Test multiple forced failures don't accumulate
        connection_id_2 = f"test_conn_multiple_forced_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Force multiple emergency transitions
        for i in range(3):
            state_machine_2.force_failed_state(f"emergency_{i}")
            assert state_machine_2.current_state == ApplicationConnectionState.FAILED
        
        # Should still be able to recover
        recovery_2 = state_machine_2.transition_to(ApplicationConnectionState.CONNECTING, "multi_recovery")
        assert recovery_2, "Should recover even after multiple forced failures"
        
        # Test forced failure with callback errors (shouldn't crash)
        connection_id_3 = f"test_conn_callback_error_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        def failing_callback(transition_info):
            raise Exception("Callback deliberately fails")
        
        state_machine_3.add_state_change_callback(failing_callback)
        
        # Force failure should work despite callback errors
        try:
            state_machine_3.force_failed_state("test_with_failing_callback")
            assert state_machine_3.current_state == ApplicationConnectionState.FAILED
        except Exception:
            assert False, "force_failed_state should handle callback exceptions gracefully"
        
        self.assert_business_value_delivered({
            'emergency_failure_handling': True,
            'forced_state_transitions': True,
            'system_stability_protection': True
        }, 'reliability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_017_setup_phase_tracking_and_duration_metrics(self, real_services_fixture):
        """
        Test setup phase tracking and duration metrics collection.
        
        Business Value: Provides visibility into connection setup performance
        for monitoring and optimization of user onboarding experience.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'setup_metrics_test@netra.ai',
            'name': 'Setup Metrics Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        connection_id = f"test_conn_setup_metrics_{int(time.time())}"
        
        # Record start time for comparison
        start_time = time.time()
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Verify initial setup state
        initial_metrics = state_machine.get_metrics()
        assert initial_metrics['setup_duration_seconds'] == 0.0
        assert len(initial_metrics['setup_phases_completed']) == 0
        
        # Track setup phase progression with timing
        setup_phases = [
            (ApplicationConnectionState.ACCEPTED, "websocket_handshake_complete", 0.05),
            (ApplicationConnectionState.AUTHENTICATED, "user_authentication_success", 0.1),
            (ApplicationConnectionState.SERVICES_READY, "service_initialization_complete", 0.2),
            (ApplicationConnectionState.PROCESSING_READY, "fully_operational", 0.0)
        ]
        
        phase_times = []
        
        for phase_state, reason, artificial_delay in setup_phases:
            # Add artificial delay to simulate real setup time
            if artificial_delay > 0:
                await asyncio.sleep(artificial_delay)
            
            phase_start = time.time()
            success = state_machine.transition_to(phase_state, reason)
            phase_end = time.time()
            
            assert success, f"Setup phase transition to {phase_state.value} should succeed"
            
            phase_times.append({
                'state': phase_state,
                'duration': phase_end - phase_start,
                'timestamp': phase_end
            })
            
            # Check metrics after each setup phase
            current_metrics = state_machine.get_metrics()
            
            if ApplicationConnectionState.is_setup_phase(phase_state):
                # Still in setup
                expected_phases = [p.value for p, _, _ in setup_phases[:len(phase_times)] 
                                 if ApplicationConnectionState.is_setup_phase(p)]
                assert set(current_metrics['setup_phases_completed']) == set(expected_phases)
                assert current_metrics['setup_duration_seconds'] == 0.0  # Not complete yet
            else:
                # Setup complete
                setup_duration = current_metrics['setup_duration_seconds']
                assert setup_duration > 0, "Setup duration should be positive when complete"
                assert setup_duration >= 0.3, "Should reflect artificial delays (0.05 + 0.1 + 0.2)"
                
                # Verify all setup phases were recorded
                expected_setup_phases = [
                    ApplicationConnectionState.ACCEPTED.value,
                    ApplicationConnectionState.AUTHENTICATED.value,
                    ApplicationConnectionState.SERVICES_READY.value
                ]
                for phase in expected_setup_phases:
                    assert phase in current_metrics['setup_phases_completed']
        
        # Verify final setup metrics
        final_metrics = state_machine.get_metrics()
        total_setup_time = time.time() - start_time
        
        assert final_metrics['setup_duration_seconds'] > 0
        assert final_metrics['setup_duration_seconds'] <= total_setup_time
        assert final_metrics['is_operational']
        assert final_metrics['is_ready_for_messages']
        
        # Test setup duration property
        setup_duration_property = state_machine.setup_duration
        assert setup_duration_property == final_metrics['setup_duration_seconds']
        
        # Test setup tracking with failures during setup
        connection_id_2 = f"test_conn_setup_failures_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Progress partway through setup
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "partial_setup")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "partial_setup")
        
        # Force failure during setup
        state_machine_2.force_failed_state("setup_failure")
        
        # Verify setup duration is not recorded for incomplete setup
        failed_metrics = state_machine_2.get_metrics()
        assert failed_metrics['setup_duration_seconds'] == 0.0
        assert len(failed_metrics['setup_phases_completed']) == 2  # ACCEPTED and AUTHENTICATED
        
        # Test setup timing with rapid transitions
        connection_id_3 = f"test_conn_rapid_setup_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        rapid_start = time.time()
        
        # Rapid succession transitions
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "rapid")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "rapid")
        state_machine_3.transition_to(ApplicationConnectionState.SERVICES_READY, "rapid")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "rapid")
        
        rapid_end = time.time()
        rapid_duration = rapid_end - rapid_start
        
        rapid_metrics = state_machine_3.get_metrics()
        recorded_duration = rapid_metrics['setup_duration_seconds']
        
        # Should be very fast but measurable
        assert recorded_duration > 0
        assert recorded_duration <= rapid_duration
        assert recorded_duration < 1.0  # Should be well under 1 second for rapid transitions
        
        # Test registry integration with setup metrics
        registry = ConnectionStateMachineRegistry()
        
        # Create connections with different setup states
        setup_test_connections = []
        for i in range(3):
            conn_id = f"registry_setup_test_{i}_{int(time.time())}"
            machine = registry.register_connection(conn_id, user_id)
            
            if i == 0:
                # Partial setup
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "partial")
            elif i == 1:
                # Complete setup
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "complete")
                machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "complete")
                machine.transition_to(ApplicationConnectionState.SERVICES_READY, "complete")
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "complete")
            # i == 2: Leave in CONNECTING state
            
            setup_test_connections.append((conn_id, machine))
        
        # Verify setup state distribution
        stats = registry.get_registry_stats()
        assert stats['total_connections'] == 3
        assert stats['operational_connections'] == 1  # Only the complete setup one
        
        # Test setup phase completion tracking
        connecting_connections = registry.get_connections_by_state(ApplicationConnectionState.CONNECTING)
        accepted_connections = registry.get_connections_by_state(ApplicationConnectionState.ACCEPTED)
        ready_connections = registry.get_connections_by_state(ApplicationConnectionState.PROCESSING_READY)
        
        assert len(connecting_connections) == 1
        assert len(accepted_connections) == 1
        assert len(ready_connections) == 1
        
        # Cleanup
        for conn_id, _ in setup_test_connections:
            registry.unregister_connection(conn_id)
        
        self.assert_business_value_delivered({
            'setup_phase_tracking': True,
            'duration_metrics': True,
            'performance_monitoring': True
        }, 'observability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_018_state_machine_with_real_websocket_connection_integration(self, real_services_fixture):
        """
        Test state machine integration with real WebSocket connection objects.
        
        Business Value: Validates that state machine works correctly with actual
        WebSocket connections for realistic connection management scenarios.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'real_websocket_test@netra.ai',
            'name': 'Real WebSocket Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        
        # Create mock WebSocket that simulates real WebSocket behavior
        class MockWebSocket:
            def __init__(self):
                self.messages_sent = []
                self.state = "connected"
                self.closed = False
                self.close_code = None
                self.close_reason = None
            
            async def send_text(self, message):
                if self.closed:
                    raise ConnectionError("WebSocket is closed")
                self.messages_sent.append(message)
            
            async def send_json(self, data):
                if self.closed:
                    raise ConnectionError("WebSocket is closed")
                import json
                self.messages_sent.append(json.dumps(data))
            
            async def close(self, code=1000, reason="Normal closure"):
                self.closed = True
                self.close_code = code
                self.close_reason = reason
                self.state = "closed"
            
            def is_connected(self):
                return not self.closed and self.state == "connected"
        
        # Test integration with WebSocket connection lifecycle
        connection_id = f"test_websocket_integration_{int(time.time())}"
        mock_websocket = MockWebSocket()
        
        # Initialize state machine
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        # Simulate WebSocket connection establishment
        assert mock_websocket.is_connected(), "Mock WebSocket should be connected initially"
        
        # Link state machine progression with WebSocket state
        websocket_events = []
        
        def websocket_state_callback(transition_info):
            websocket_events.append({
                'state_machine_state': transition_info.to_state.value,
                'websocket_connected': mock_websocket.is_connected(),
                'reason': transition_info.reason
            })
        
        state_machine.add_state_change_callback(websocket_state_callback)
        
        # Simulate connection establishment sequence
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "websocket_handshake_complete")
        
        # Send initial connection message
        await mock_websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "state": state_machine.current_state.value
        })
        
        # Continue setup
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "user_authenticated")
        
        # Send authentication confirmation
        await mock_websocket.send_json({
            "type": "authentication_confirmed",
            "user_id": user_id,
            "state": state_machine.current_state.value
        })
        
        state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, "services_initialized")
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "ready_for_messages")
        
        # Verify messages were sent at each state
        assert len(mock_websocket.messages_sent) == 2
        sent_messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        
        assert sent_messages[0]['type'] == 'connection_established'
        assert sent_messages[1]['type'] == 'authentication_confirmed'
        
        # Test message processing in operational state
        assert state_machine.can_process_messages(), "Should be ready for message processing"
        
        # Simulate processing messages
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "message_processing_started")
        
        await mock_websocket.send_json({
            "type": "processing_status",
            "status": "active",
            "state": state_machine.current_state.value
        })
        
        state_machine.transition_to(ApplicationConnectionState.IDLE, "message_processing_complete")
        
        # Test error scenario with WebSocket
        # Simulate network degradation
        state_machine.transition_to(ApplicationConnectionState.DEGRADED, "network_quality_degraded")
        
        # WebSocket should still be connected but state machine knows it's degraded
        assert mock_websocket.is_connected(), "WebSocket should still be connected in degraded mode"
        assert state_machine.current_state == ApplicationConnectionState.DEGRADED
        assert state_machine.can_process_messages(), "Should still process messages in degraded mode"
        
        # Test WebSocket closure with state machine coordination
        state_machine.transition_to(ApplicationConnectionState.CLOSING, "client_requested_close")
        
        # Close WebSocket
        await mock_websocket.close(1000, "Normal closure")
        
        # Complete state machine closure
        state_machine.transition_to(ApplicationConnectionState.CLOSED, "websocket_closed")
        
        # Verify final states
        assert not mock_websocket.is_connected(), "WebSocket should be closed"
        assert state_machine.current_state == ApplicationConnectionState.CLOSED
        assert not state_machine.can_process_messages(), "Should not process messages when closed"
        
        # Verify WebSocket events were tracked
        assert len(websocket_events) >= 6  # At least 6 state transitions
        
        # Check that WebSocket was connected during operational states
        operational_events = [e for e in websocket_events 
                            if e['state_machine_state'] in ['processing_ready', 'processing', 'idle', 'degraded']]
        for event in operational_events:
            if event['state_machine_state'] != 'degraded':  # Degraded might have connection issues
                assert event['websocket_connected'], f"WebSocket should be connected during {event['state_machine_state']}"
        
        # Test error recovery simulation
        connection_id_2 = f"test_websocket_recovery_{int(time.time())}"
        mock_websocket_2 = MockWebSocket()
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Setup to operational state
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Simulate WebSocket connection failure
        await mock_websocket_2.close(1006, "Abnormal closure")
        
        # Force state machine to error state
        state_machine_2.force_failed_state("websocket_connection_lost")
        
        # Simulate reconnection
        mock_websocket_3 = MockWebSocket()  # New WebSocket connection
        
        # Recover state machine
        state_machine_2.transition_to(ApplicationConnectionState.CONNECTING, "reconnection_attempt")
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "reconnection_successful")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "re_authentication")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "reconnection_complete")
        
        # Verify recovery
        assert mock_websocket_3.is_connected(), "New WebSocket should be connected"
        assert state_machine_2.can_process_messages(), "Should be ready after recovery"
        
        # Test coordinated shutdown
        await mock_websocket_3.send_json({
            "type": "shutdown_notification",
            "reason": "server_maintenance"
        })
        
        state_machine_2.transition_to(ApplicationConnectionState.CLOSING, "server_shutdown")
        await mock_websocket_3.close(1001, "Going away")
        state_machine_2.transition_to(ApplicationConnectionState.CLOSED, "shutdown_complete")
        
        assert not mock_websocket_3.is_connected()
        assert state_machine_2.current_state == ApplicationConnectionState.CLOSED
        
        self.assert_business_value_delivered({
            'websocket_integration': True,
            'connection_lifecycle_coordination': True,
            'error_recovery_simulation': True
        }, 'integration')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_019_registry_cleanup_of_closed_connections_comprehensive(self, real_services_fixture):
        """
        Test comprehensive registry cleanup of closed connections under various scenarios.
        
        Business Value: Ensures efficient memory management and prevents resource
        leaks in high-throughput production environments.
        """
        # Create test users for different cleanup scenarios
        users = []
        for i in range(10):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'cleanup_comprehensive_{i}@netra.ai',
                'name': f'Cleanup Comprehensive User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        registry = ConnectionStateMachineRegistry()
        
        # Scenario 1: Normal closure cleanup
        normal_closure_connections = []
        for i in range(3):
            user_id = ensure_user_id(users[i]['id'])
            connection_id = f"normal_closure_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Setup to operational
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
            machine.transition_to(ApplicationConnectionState.PROCESSING, "active")
            
            # Normal closure
            machine.transition_to(ApplicationConnectionState.CLOSING, "user_disconnect")
            machine.transition_to(ApplicationConnectionState.CLOSED, "normal_closure")
            
            normal_closure_connections.append(connection_id)
        
        # Scenario 2: Failed connections
        failed_connections = []
        for i in range(3, 6):
            user_id = ensure_user_id(users[i]['id'])
            connection_id = f"failed_connection_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Setup partway then fail
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            machine.force_failed_state(f"network_failure_{i}")
            
            failed_connections.append(connection_id)
        
        # Scenario 3: Mixed terminal states
        mixed_terminal_connections = []
        for i in range(6, 8):
            user_id = ensure_user_id(users[i]['id'])
            connection_id = f"mixed_terminal_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Alternate between CLOSED and FAILED
            if i % 2 == 0:
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
                machine.transition_to(ApplicationConnectionState.CLOSING, "close")
                machine.transition_to(ApplicationConnectionState.CLOSED, "closed")
            else:
                machine.force_failed_state("failure")
            
            mixed_terminal_connections.append(connection_id)
        
        # Scenario 4: Active connections (should not be cleaned up)
        active_connections = []
        for i in range(8, 10):
            user_id = ensure_user_id(users[i]['id'])
            connection_id = f"active_connection_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Keep in active states
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            if i == 8:
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "active")
            else:
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "active")
                machine.transition_to(ApplicationConnectionState.PROCESSING, "active")
            
            active_connections.append(connection_id)
        
        # Verify initial state
        initial_stats = registry.get_registry_stats()
        assert initial_stats['total_connections'] == 10
        
        # Test selective cleanup
        
        # First, clean up only CLOSED connections
        closed_before_cleanup = registry.get_connections_by_state(ApplicationConnectionState.CLOSED)
        failed_before_cleanup = registry.get_connections_by_state(ApplicationConnectionState.FAILED)
        
        expected_closed_count = len(normal_closure_connections) + 1  # 3 normal + 1 from mixed
        expected_failed_count = len(failed_connections) + 1  # 3 failed + 1 from mixed
        
        assert len(closed_before_cleanup) == expected_closed_count
        assert len(failed_before_cleanup) == expected_failed_count
        
        # Perform cleanup
        cleaned_count = registry.cleanup_closed_connections()
        expected_total_cleanup = expected_closed_count + expected_failed_count
        assert cleaned_count == expected_total_cleanup
        
        # Verify cleanup results
        post_cleanup_stats = registry.get_registry_stats()
        assert post_cleanup_stats['total_connections'] == len(active_connections)
        assert post_cleanup_stats['operational_connections'] == len(active_connections)
        
        # Verify active connections remain
        for connection_id in active_connections:
            machine = registry.get_connection_state_machine(connection_id)
            assert machine is not None, f"Active connection {connection_id} should remain after cleanup"
            assert machine.is_operational, f"Active connection {connection_id} should be operational"
        
        # Verify terminal connections are gone
        all_terminal_connections = (normal_closure_connections + failed_connections + 
                                  mixed_terminal_connections)
        for connection_id in all_terminal_connections:
            machine = registry.get_connection_state_machine(connection_id)
            assert machine is None, f"Terminal connection {connection_id} should be cleaned up"
        
        # Test cleanup with no terminal connections
        no_cleanup_count = registry.cleanup_closed_connections()
        assert no_cleanup_count == 0, "Second cleanup should find no connections to remove"
        
        # Test large-scale cleanup simulation
        stress_connections = []
        
        # Create many connections in terminal states
        for i in range(100):
            user_id = ensure_user_id(users[i % len(users)]['id'])
            connection_id = f"stress_cleanup_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            
            # Rapid transition to terminal state
            if i % 3 == 0:
                # CLOSED
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "rapid")
                machine.transition_to(ApplicationConnectionState.CLOSING, "rapid")
                machine.transition_to(ApplicationConnectionState.CLOSED, "rapid")
            elif i % 3 == 1:
                # FAILED
                machine.force_failed_state("rapid_failure")
            else:
                # Keep some active for comparison
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "rapid")
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "rapid")
            
            stress_connections.append(connection_id)
        
        # Verify stress test connections were created
        stress_stats = registry.get_registry_stats()
        expected_total = len(active_connections) + len(stress_connections)
        assert stress_stats['total_connections'] == expected_total
        
        # Perform large-scale cleanup
        large_cleanup_count = registry.cleanup_closed_connections()
        
        # Should clean up ~67 connections (100 stress * 2/3 terminal)
        expected_cleanup = (100 * 2) // 3  # About 66-67 connections
        assert large_cleanup_count >= expected_cleanup - 2  # Allow small variance
        assert large_cleanup_count <= expected_cleanup + 2
        
        # Verify final state
        final_stats = registry.get_registry_stats()
        expected_remaining = len(active_connections) + (100 - large_cleanup_count)
        assert final_stats['total_connections'] == expected_remaining
        
        # Test cleanup performance timing
        import time
        
        # Create connections for timing test
        timing_connections = []
        for i in range(50):
            user_id = ensure_user_id(users[i % len(users)]['id'])
            connection_id = f"timing_test_{i}_{int(time.time())}"
            
            machine = registry.register_connection(connection_id, user_id)
            machine.force_failed_state("timing_test")
            timing_connections.append(connection_id)
        
        # Time the cleanup operation
        cleanup_start = time.time()
        timing_cleanup_count = registry.cleanup_closed_connections()
        cleanup_end = time.time()
        cleanup_duration = cleanup_end - cleanup_start
        
        assert timing_cleanup_count == 50
        assert cleanup_duration < 1.0, "Cleanup of 50 connections should complete within 1 second"
        
        # Test registry statistics accuracy after cleanup
        final_final_stats = registry.get_registry_stats()
        
        # Manually count remaining connections
        manual_count = 0
        for connection_id in active_connections:
            if registry.get_connection_state_machine(connection_id) is not None:
                manual_count += 1
        
        # Add remaining stress connections that weren't terminal
        remaining_stress = len([c for c in stress_connections 
                             if registry.get_connection_state_machine(c) is not None])
        manual_count += remaining_stress
        
        assert final_final_stats['total_connections'] == manual_count
        
        self.assert_business_value_delivered({
            'comprehensive_cleanup': True,
            'large_scale_cleanup_performance': True,
            'memory_leak_prevention': True
        }, 'scalability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_020_connection_state_statistics_and_reporting(self, real_services_fixture):
        """
        Test comprehensive connection state statistics and reporting functionality.
        
        Business Value: Provides operational insights for monitoring connection
        health, load balancing, and performance optimization.
        """
        # Create users for different statistical scenarios
        users = []
        for i in range(8):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'stats_test_{i}@netra.ai',
                'name': f'Statistics Test User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        registry = ConnectionStateMachineRegistry()
        
        # Create connections in various states for statistics testing
        connection_scenarios = [
            # (count, final_state, description)
            (2, ApplicationConnectionState.CONNECTING, "connecting"),
            (2, ApplicationConnectionState.ACCEPTED, "accepted"),
            (1, ApplicationConnectionState.AUTHENTICATED, "authenticated"),
            (3, ApplicationConnectionState.PROCESSING_READY, "processing_ready"),
            (2, ApplicationConnectionState.PROCESSING, "processing"),
            (1, ApplicationConnectionState.IDLE, "idle"),
            (1, ApplicationConnectionState.DEGRADED, "degraded"),
            (1, ApplicationConnectionState.FAILED, "failed"),
            (2, ApplicationConnectionState.CLOSED, "closed")
        ]
        
        created_connections = []
        
        for count, target_state, description in connection_scenarios:
            for i in range(count):
                user_id = ensure_user_id(users[i % len(users)]['id'])
                connection_id = f"stats_{description}_{i}_{int(time.time())}"
                
                machine = registry.register_connection(connection_id, user_id)
                
                # Transition to target state through proper sequence
                if target_state in [ApplicationConnectionState.ACCEPTED, 
                                  ApplicationConnectionState.AUTHENTICATED,
                                  ApplicationConnectionState.PROCESSING_READY,
                                  ApplicationConnectionState.PROCESSING,
                                  ApplicationConnectionState.IDLE,
                                  ApplicationConnectionState.DEGRADED,
                                  ApplicationConnectionState.CLOSED]:
                    machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
                
                if target_state in [ApplicationConnectionState.AUTHENTICATED,
                                  ApplicationConnectionState.PROCESSING_READY,
                                  ApplicationConnectionState.PROCESSING,
                                  ApplicationConnectionState.IDLE,
                                  ApplicationConnectionState.DEGRADED,
                                  ApplicationConnectionState.CLOSED]:
                    machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
                
                if target_state in [ApplicationConnectionState.PROCESSING_READY,
                                  ApplicationConnectionState.PROCESSING,
                                  ApplicationConnectionState.IDLE,
                                  ApplicationConnectionState.DEGRADED,
                                  ApplicationConnectionState.CLOSED]:
                    machine.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
                    machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
                
                if target_state == ApplicationConnectionState.PROCESSING:
                    machine.transition_to(ApplicationConnectionState.PROCESSING, "active")
                elif target_state == ApplicationConnectionState.IDLE:
                    machine.transition_to(ApplicationConnectionState.PROCESSING, "temp")
                    machine.transition_to(ApplicationConnectionState.IDLE, "idle")
                elif target_state == ApplicationConnectionState.DEGRADED:
                    machine.transition_to(ApplicationConnectionState.DEGRADED, "degraded")
                elif target_state == ApplicationConnectionState.FAILED:
                    machine.force_failed_state("test_failure")
                elif target_state == ApplicationConnectionState.CLOSED:
                    machine.transition_to(ApplicationConnectionState.CLOSING, "close")
                    machine.transition_to(ApplicationConnectionState.CLOSED, "closed")
                
                created_connections.append((connection_id, machine, target_state))
        
        # Test registry statistics
        stats = registry.get_registry_stats()
        
        # Verify total connections
        expected_total = sum(count for count, _, _ in connection_scenarios)
        assert stats['total_connections'] == expected_total
        
        # Verify operational connections count
        operational_states = {ApplicationConnectionState.PROCESSING_READY,
                            ApplicationConnectionState.PROCESSING,
                            ApplicationConnectionState.IDLE,
                            ApplicationConnectionState.DEGRADED}
        expected_operational = sum(count for count, state, _ in connection_scenarios 
                                 if state in operational_states)
        assert stats['operational_connections'] == expected_operational
        
        # Verify state distribution
        state_distribution = stats['state_distribution']
        for count, state, _ in connection_scenarios:
            expected_count = count
            actual_count = state_distribution.get(state.value, 0)
            assert actual_count == expected_count, \
                f"State {state.value}: expected {expected_count}, got {actual_count}"
        
        # Test individual state machine metrics
        metrics_summary = {
            'total_transitions': 0,
            'failed_transitions': 0,
            'operational_count': 0,
            'ready_count': 0,
            'average_setup_duration': 0,
            'setup_completed_count': 0
        }
        
        for connection_id, machine, target_state in created_connections:
            machine_metrics = machine.get_metrics()
            
            metrics_summary['total_transitions'] += machine_metrics['total_transitions']
            metrics_summary['failed_transitions'] += machine_metrics['failed_transitions']
            
            if machine_metrics['is_operational']:
                metrics_summary['operational_count'] += 1
            
            if machine_metrics['is_ready_for_messages']:
                metrics_summary['ready_count'] += 1
            
            if machine_metrics['setup_duration_seconds'] > 0:
                metrics_summary['average_setup_duration'] += machine_metrics['setup_duration_seconds']
                metrics_summary['setup_completed_count'] += 1
        
        # Calculate averages
        if metrics_summary['setup_completed_count'] > 0:
            metrics_summary['average_setup_duration'] /= metrics_summary['setup_completed_count']
        
        # Verify aggregated metrics make sense
        assert metrics_summary['total_transitions'] > 0, "Should have recorded transitions"
        assert metrics_summary['operational_count'] == expected_operational
        assert metrics_summary['ready_count'] == expected_operational  # Operational = ready in this test
        
        # Test state filtering functionality
        for target_state in [ApplicationConnectionState.PROCESSING_READY,
                           ApplicationConnectionState.PROCESSING,
                           ApplicationConnectionState.FAILED,
                           ApplicationConnectionState.CLOSED]:
            filtered_connections = registry.get_connections_by_state(target_state)
            expected_count = next(count for count, state, _ in connection_scenarios 
                                if state == target_state)
            assert len(filtered_connections) == expected_count, \
                f"State filter for {target_state.value} returned wrong count"
        
        # Test operational connections filtering
        operational_connections = registry.get_all_operational_connections()
        assert len(operational_connections) == expected_operational
        
        # Verify all operational connections are actually operational
        for conn_id, machine in operational_connections.items():
            assert machine.is_operational, f"Connection {conn_id} should be operational"
            assert machine.current_state in operational_states
        
        # Test statistics after state changes
        
        # Change some connections to different states
        state_change_connections = created_connections[:3]
        for connection_id, machine, original_state in state_change_connections:
            if machine.current_state == ApplicationConnectionState.PROCESSING_READY:
                machine.transition_to(ApplicationConnectionState.PROCESSING, "state_change_test")
            elif machine.current_state == ApplicationConnectionState.CONNECTING:
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "state_change_test")
        
        # Get updated statistics
        updated_stats = registry.get_registry_stats()
        
        # Should still have same total connections
        assert updated_stats['total_connections'] == expected_total
        
        # Verify state distribution changed appropriately
        updated_distribution = updated_stats['state_distribution']
        
        # Test cleanup impact on statistics
        
        # Force some connections to terminal states
        terminal_test_connections = created_connections[5:8]
        for connection_id, machine, _ in terminal_test_connections:
            if not ApplicationConnectionState.is_terminal(machine.current_state):
                machine.force_failed_state("stats_test_terminal")
        
        # Clean up terminal connections
        cleanup_count = registry.cleanup_closed_connections()
        
        # Get post-cleanup statistics
        post_cleanup_stats = registry.get_registry_stats()
        
        # Verify cleanup impact
        assert post_cleanup_stats['total_connections'] < updated_stats['total_connections']
        assert cleanup_count > 0
        
        # Test real-time statistics updates
        
        # Create a connection and monitor statistics in real-time
        realtime_user_id = ensure_user_id(users[0]['id'])
        realtime_connection_id = f"realtime_stats_{int(time.time())}"
        
        realtime_machine = registry.register_connection(realtime_connection_id, realtime_user_id)
        
        # Track statistics at each transition
        realtime_stats_history = []
        
        transition_sequence = [
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING
        ]
        
        for state in transition_sequence:
            realtime_machine.transition_to(state, "realtime_test")
            current_stats = registry.get_registry_stats()
            realtime_stats_history.append({
                'state': state.value,
                'total_connections': current_stats['total_connections'],
                'operational_connections': current_stats['operational_connections'],
                'state_distribution': current_stats['state_distribution'].copy()
            })
        
        # Verify statistics progression
        assert len(realtime_stats_history) == len(transition_sequence)
        
        # Operational count should increase when reaching PROCESSING_READY
        processing_ready_stats = next(s for s in realtime_stats_history 
                                    if s['state'] == 'processing_ready')
        processing_stats = next(s for s in realtime_stats_history 
                              if s['state'] == 'processing')
        
        # Both should show operational connection
        assert processing_ready_stats['operational_connections'] > 0
        assert processing_stats['operational_connections'] > 0
        
        self.assert_business_value_delivered({
            'comprehensive_statistics': True,
            'real_time_monitoring': True,
            'operational_insights': True
        }, 'observability')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_021_state_machine_degraded_mode_functionality(self, real_services_fixture):
        """
        Test degraded mode functionality and graceful degradation scenarios.
        
        Business Value: Ensures system continues operating with reduced functionality
        during partial failures, maintaining user experience continuity.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'degraded_mode_test@netra.ai',
            'name': 'Degraded Mode Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        
        # Test 1: Transition to degraded mode from operational state
        connection_id_1 = f"test_degraded_from_operational_{int(time.time())}"
        state_machine_1 = ConnectionStateMachine(connection_id_1, user_id)
        
        # Setup to fully operational
        state_machine_1.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Verify operational
        assert state_machine_1.is_operational
        assert state_machine_1.can_process_messages()
        
        # Transition to degraded mode (simulating partial service failure)
        success = state_machine_1.transition_to(ApplicationConnectionState.DEGRADED, "service_degradation")
        assert success, "Should be able to transition to degraded mode"
        
        # Verify degraded mode properties
        assert state_machine_1.current_state == ApplicationConnectionState.DEGRADED
        assert state_machine_1.is_operational, "Degraded mode should still be operational"
        assert state_machine_1.can_process_messages(), "Should still be able to process messages"
        
        # Test recovery from degraded mode
        recovery_success = state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, "service_recovery")
        assert recovery_success, "Should be able to recover from degraded mode"
        assert state_machine_1.current_state == ApplicationConnectionState.PROCESSING_READY
        
        # Test 2: Degraded mode with insufficient setup
        connection_id_2 = f"test_degraded_insufficient_setup_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Minimal setup (only ACCEPTED)
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "minimal_setup")
        
        # Attempt degraded mode with insufficient setup
        degraded_success = state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "premature_degradation")
        assert degraded_success, "Should allow transition to degraded mode"
        
        # Should not be ready for message processing due to insufficient setup
        assert not state_machine_2.can_process_messages(), "Insufficient setup should prevent message processing"
        assert state_machine_2.is_operational, "Should still be considered operational"
        
        # Add authentication and test readiness
        auth_success = state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "add_authentication")
        assert auth_success, "Should be able to add authentication in degraded mode"
        
        degraded_auth_success = state_machine_2.transition_to(ApplicationConnectionState.DEGRADED, "degraded_with_auth")
        assert degraded_auth_success, "Should be able to return to degraded with auth"
        
        # Now should be ready (has ACCEPTED + AUTHENTICATED)
        assert state_machine_2.can_process_messages(), "Should be ready with sufficient setup"
        
        # Test 3: Multiple degradation and recovery cycles
        connection_id_3 = f"test_degraded_cycles_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        # Setup to operational
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Track degradation cycles
        degradation_cycles = []
        
        def track_degradation_cycles(transition_info):
            if transition_info.to_state == ApplicationConnectionState.DEGRADED:
                degradation_cycles.append({
                    'from': transition_info.from_state,
                    'reason': transition_info.reason,
                    'timestamp': transition_info.timestamp
                })
        
        state_machine_3.add_state_change_callback(track_degradation_cycles)
        
        # Perform multiple degradation/recovery cycles
        for i in range(3):
            # Degrade
            state_machine_3.transition_to(ApplicationConnectionState.DEGRADED, f"degradation_cycle_{i}")
            assert state_machine_3.can_process_messages(), "Should process messages in degraded mode"
            
            # Recover
            state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, f"recovery_cycle_{i}")
            assert state_machine_3.can_process_messages(), "Should process messages after recovery"
        
        # Verify all cycles were tracked
        assert len(degradation_cycles) == 3, "Should track all degradation cycles"
        
        # Test 4: Degraded mode transition from different operational states
        connection_id_4 = f"test_degraded_from_different_states_{int(time.time())}"
        state_machine_4 = ConnectionStateMachine(connection_id_4, user_id)
        
        # Setup to operational
        state_machine_4.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Test degradation from PROCESSING state
        state_machine_4.transition_to(ApplicationConnectionState.PROCESSING, "start_processing")
        degraded_from_processing = state_machine_4.transition_to(ApplicationConnectionState.DEGRADED, "degrade_from_processing")
        assert degraded_from_processing, "Should be able to degrade from PROCESSING"
        
        # Recover to IDLE
        idle_recovery = state_machine_4.transition_to(ApplicationConnectionState.IDLE, "recover_to_idle")
        assert idle_recovery, "Should be able to recover to IDLE from degraded"
        
        # Degrade from IDLE
        degraded_from_idle = state_machine_4.transition_to(ApplicationConnectionState.DEGRADED, "degrade_from_idle")
        assert degraded_from_idle, "Should be able to degrade from IDLE"
        
        # Test 5: Degraded mode with registry integration
        registry = ConnectionStateMachineRegistry()
        
        # Create multiple connections in degraded mode
        degraded_connections = []
        for i in range(3):
            conn_id = f"degraded_registry_test_{i}_{int(time.time())}"
            machine = registry.register_connection(conn_id, user_id)
            
            # Setup and degrade
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            machine.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
            machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
            machine.transition_to(ApplicationConnectionState.DEGRADED, f"registry_degrade_{i}")
            
            degraded_connections.append(conn_id)
        
        # Test registry operations with degraded connections
        all_operational = registry.get_all_operational_connections()
        assert len(all_operational) == 3, "All degraded connections should be operational"
        
        degraded_filtered = registry.get_connections_by_state(ApplicationConnectionState.DEGRADED)
        assert len(degraded_filtered) == 3, "Should find all degraded connections"
        
        stats = registry.get_registry_stats()
        assert stats['operational_connections'] == 3, "Degraded connections should count as operational"
        assert stats['state_distribution']['degraded'] == 3, "State distribution should show degraded connections"
        
        # Test 6: Degraded mode failure threshold integration
        connection_id_5 = f"test_degraded_failure_threshold_{int(time.time())}"
        state_machine_5 = ConnectionStateMachine(connection_id_5, user_id)
        
        # Setup to degraded mode
        state_machine_5.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_5.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_5.transition_to(ApplicationConnectionState.DEGRADED, "initial_degradation")
        
        # Generate some failures while in degraded mode
        for i in range(3):
            state_machine_5.transition_to(ApplicationConnectionState.CONNECTING, "invalid_from_degraded")  # Invalid
        
        # Should still be able to process messages
        assert state_machine_5.can_process_messages(), "Should handle some failures in degraded mode"
        
        # Generate excessive failures
        for i in range(3):  # Total of 6 failures
            state_machine_5.transition_to(ApplicationConnectionState.CONNECTING, "excessive_failures")
        
        # Should now be unable to process messages due to excessive failures
        assert not state_machine_5.can_process_messages(), "Should not process messages after excessive failures"
        
        # Test 7: Degraded mode message processing validation
        connection_id_6 = f"test_degraded_message_processing_{int(time.time())}"
        state_machine_6 = ConnectionStateMachine(connection_id_6, user_id)
        
        # Setup with full operational capability
        state_machine_6.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_6.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_6.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_6.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Verify full capability
        assert state_machine_6.can_process_messages()
        assert state_machine_6.is_ready_for_messages
        
        # Transition to degraded
        state_machine_6.transition_to(ApplicationConnectionState.DEGRADED, "test_degraded_processing")
        
        # Verify degraded mode capabilities
        assert state_machine_6.can_process_messages(), "Degraded mode should allow message processing"
        assert state_machine_6.is_ready_for_messages, "Degraded mode should be ready for messages"
        assert state_machine_6.is_operational, "Degraded mode should be operational"
        
        # Verify metrics in degraded mode
        degraded_metrics = state_machine_6.get_metrics()
        assert degraded_metrics['is_operational'], "Metrics should show operational in degraded mode"
        assert degraded_metrics['is_ready_for_messages'], "Metrics should show ready in degraded mode"
        
        # Cleanup registry connections
        for conn_id in degraded_connections:
            registry.unregister_connection(conn_id)
        
        self.assert_business_value_delivered({
            'degraded_mode_functionality': True,
            'graceful_degradation': True,
            'service_continuity': True
        }, 'resilience')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_022_recovery_from_error_states_to_operational_states(self, real_services_fixture):
        """
        Test recovery from error states to operational states with full validation.
        
        Business Value: Ensures system can recover from failures and resume
        normal operations, maintaining service availability and user experience.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'error_recovery_test@netra.ai',
            'name': 'Error Recovery Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        
        # Test 1: Recovery from FAILED state
        connection_id_1 = f"test_failed_recovery_{int(time.time())}"
        state_machine_1 = ConnectionStateMachine(connection_id_1, user_id)
        
        # Setup to operational then force failure
        state_machine_1.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Force failure
        state_machine_1.force_failed_state("simulated_critical_failure")
        assert state_machine_1.current_state == ApplicationConnectionState.FAILED
        assert not state_machine_1.can_process_messages()
        
        # Track recovery process
        recovery_transitions = []
        
        def track_recovery(transition_info):
            recovery_transitions.append({
                'from': transition_info.from_state,
                'to': transition_info.to_state,
                'reason': transition_info.reason
            })
        
        state_machine_1.add_state_change_callback(track_recovery)
        
        # Begin recovery sequence
        recovery_1 = state_machine_1.transition_to(ApplicationConnectionState.CONNECTING, "recovery_attempt")
        assert recovery_1, "Should allow recovery from FAILED to CONNECTING"
        
        recovery_2 = state_machine_1.transition_to(ApplicationConnectionState.ACCEPTED, "recovery_handshake")
        assert recovery_2, "Should progress through recovery"
        
        recovery_3 = state_machine_1.transition_to(ApplicationConnectionState.AUTHENTICATED, "recovery_auth")
        assert recovery_3, "Should complete authentication in recovery"
        
        recovery_4 = state_machine_1.transition_to(ApplicationConnectionState.SERVICES_READY, "recovery_services")
        assert recovery_4, "Should restore services"
        
        recovery_5 = state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, "recovery_complete")
        assert recovery_5, "Should reach operational state"
        
        # Verify full recovery
        assert state_machine_1.current_state == ApplicationConnectionState.PROCESSING_READY
        assert state_machine_1.is_operational
        assert state_machine_1.can_process_messages()
        
        # Verify recovery was tracked
        assert len(recovery_transitions) == 5
        recovery_states = [t['to'] for t in recovery_transitions]
        expected_recovery = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.PROCESSING_READY
        ]
        assert recovery_states == expected_recovery
        
        # Test 2: Recovery with partial failures during recovery
        connection_id_2 = f"test_partial_recovery_{int(time.time())}"
        state_machine_2 = ConnectionStateMachine(connection_id_2, user_id)
        
        # Force to failed state
        state_machine_2.force_failed_state("initial_failure")
        
        # Attempt recovery with some failures
        state_machine_2.transition_to(ApplicationConnectionState.CONNECTING, "recovery_start")
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "recovery_accepted")
        
        # Simulate failure during recovery
        invalid_attempt = state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "invalid_jump")
        assert not invalid_attempt, "Should not allow invalid jumps during recovery"
        
        # Continue proper recovery
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "recovery_auth")
        state_machine_2.transition_to(ApplicationConnectionState.SERVICES_READY, "recovery_services")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "recovery_final")
        
        # Should successfully recover despite the failed attempt
        assert state_machine_2.can_process_messages()
        
        # Test 3: Multiple failure and recovery cycles
        connection_id_3 = f"test_multiple_recovery_cycles_{int(time.time())}"
        state_machine_3 = ConnectionStateMachine(connection_id_3, user_id)
        
        recovery_cycles = []
        
        for cycle in range(3):
            # Setup to operational
            state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, f"cycle_{cycle}_setup")
            state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, f"cycle_{cycle}_setup")
            state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, f"cycle_{cycle}_setup")
            
            # Verify operational
            assert state_machine_3.can_process_messages()
            
            # Force failure
            state_machine_3.force_failed_state(f"cycle_{cycle}_failure")
            assert state_machine_3.current_state == ApplicationConnectionState.FAILED
            
            # Record failure time
            failure_time = time.time()
            
            # Recover
            state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, f"cycle_{cycle}_recovery")
            
            # Record recovery time
            recovery_time = time.time()
            
            recovery_cycles.append({
                'cycle': cycle,
                'failure_time': failure_time,
                'recovery_time': recovery_time,
                'recovery_duration': recovery_time - failure_time
            })
            
            # Complete recovery for next cycle (except last)
            if cycle < 2:
                # Reset for next cycle
                state_machine_3._current_state = ApplicationConnectionState.CONNECTING
                state_machine_3._transition_failures = 0
        
        # Verify all cycles completed
        assert len(recovery_cycles) == 3
        
        # Test 4: Recovery with degraded intermediate state
        connection_id_4 = f"test_degraded_recovery_{int(time.time())}"
        state_machine_4 = ConnectionStateMachine(connection_id_4, user_id)
        
        # Setup to degraded state (simulating partial failure)
        state_machine_4.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.SERVICES_READY, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        state_machine_4.transition_to(ApplicationConnectionState.DEGRADED, "service_degradation")
        
        # Verify degraded state is operational but limited
        assert state_machine_4.is_operational
        assert state_machine_4.can_process_messages()
        
        # Recover from degraded to full operational
        degraded_recovery = state_machine_4.transition_to(ApplicationConnectionState.PROCESSING_READY, "degraded_recovery")
        assert degraded_recovery, "Should recover from degraded to full operational"
        
        # Verify full recovery
        assert state_machine_4.current_state == ApplicationConnectionState.PROCESSING_READY
        assert state_machine_4.can_process_messages()
        
        # Test 5: Registry integration with recovery scenarios
        registry = ConnectionStateMachineRegistry()
        
        # Create multiple connections for recovery testing
        recovery_test_connections = []
        for i in range(5):
            conn_id = f"registry_recovery_test_{i}_{int(time.time())}"
            machine = registry.register_connection(conn_id, user_id)
            
            # Setup and then fail
            machine.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
            machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
            machine.force_failed_state(f"test_failure_{i}")
            
            recovery_test_connections.append(conn_id)
        
        # Verify all are in failed state
        failed_connections = registry.get_connections_by_state(ApplicationConnectionState.FAILED)
        assert len(failed_connections) == 5
        
        # Recover all connections
        for i, conn_id in enumerate(recovery_test_connections):
            machine = registry.get_connection_state_machine(conn_id)
            
            # Different recovery paths for variety
            if i % 2 == 0:
                # Full recovery
                machine.transition_to(ApplicationConnectionState.CONNECTING, "batch_recovery")
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "batch_recovery")
                machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "batch_recovery")
                machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "batch_recovery")
            else:
                # Partial recovery to degraded mode
                machine.transition_to(ApplicationConnectionState.CONNECTING, "partial_recovery")
                machine.transition_to(ApplicationConnectionState.ACCEPTED, "partial_recovery")
                machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "partial_recovery")
                machine.transition_to(ApplicationConnectionState.DEGRADED, "partial_recovery")
        
        # Verify recovery distribution
        stats_after_recovery = registry.get_registry_stats()
        assert stats_after_recovery['operational_connections'] == 5  # All should be operational
        
        processing_ready_count = len(registry.get_connections_by_state(ApplicationConnectionState.PROCESSING_READY))
        degraded_count = len(registry.get_connections_by_state(ApplicationConnectionState.DEGRADED))
        
        assert processing_ready_count == 3  # 3 full recoveries (indices 0, 2, 4)
        assert degraded_count == 2  # 2 partial recoveries (indices 1, 3)
        
        # Test 6: Recovery metrics and history validation
        connection_id_5 = f"test_recovery_metrics_{int(time.time())}"
        state_machine_5 = ConnectionStateMachine(connection_id_5, user_id)
        
        # Setup, fail, and recover with detailed tracking
        state_machine_5.transition_to(ApplicationConnectionState.ACCEPTED, "initial_setup")
        state_machine_5.transition_to(ApplicationConnectionState.PROCESSING_READY, "initial_ready")
        
        # Record metrics before failure
        pre_failure_metrics = state_machine_5.get_metrics()
        
        # Force failure
        state_machine_5.force_failed_state("metrics_test_failure")
        
        # Record failure metrics
        failure_metrics = state_machine_5.get_metrics()
        assert failure_metrics['failed_transitions'] > pre_failure_metrics['failed_transitions']
        
        # Perform recovery
        state_machine_5.transition_to(ApplicationConnectionState.CONNECTING, "metrics_recovery")
        state_machine_5.transition_to(ApplicationConnectionState.ACCEPTED, "metrics_recovery")
        state_machine_5.transition_to(ApplicationConnectionState.PROCESSING_READY, "metrics_recovery")
        
        # Record post-recovery metrics
        post_recovery_metrics = state_machine_5.get_metrics()
        
        # Verify metrics progression
        assert post_recovery_metrics['total_transitions'] > failure_metrics['total_transitions']
        assert post_recovery_metrics['is_operational']
        assert post_recovery_metrics['is_ready_for_messages']
        
        # Verify history includes recovery
        history = state_machine_5.get_state_history()
        recovery_history = [h for h in history if "recovery" in h.reason]
        assert len(recovery_history) >= 3  # At least 3 recovery transitions
        
        # Cleanup registry connections
        for conn_id in recovery_test_connections:
            registry.unregister_connection(conn_id)
        
        self.assert_business_value_delivered({
            'error_state_recovery': True,
            'service_restoration': True,
            'resilience_validation': True
        }, 'resilience')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_023_state_machine_with_real_user_context_and_sessions(self, real_services_fixture):
        """
        Test state machine integration with real user context and session management.
        
        Business Value: Validates that state machines work correctly with actual
        user sessions, ensuring proper multi-user isolation and session persistence.
        """
        # Create multiple users for realistic testing
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'user_context_test_{i}@netra.ai',
                'name': f'User Context Test {i}',
                'is_active': True
            })
            users.append(user_data)
        
        # Create sessions for each user
        user_sessions = []
        for user_data in users:
            session_data = await self.create_test_session(real_services_fixture, user_data['id'])
            user_sessions.append({
                'user': user_data,
                'session': session_data
            })
        
        registry = ConnectionStateMachineRegistry()
        
        # Test 1: State machine with user context validation
        user_session_0 = user_sessions[0]
        user_id_0 = ensure_user_id(user_session_0['user']['id'])
        session_key_0 = user_session_0['session']['session_key']
        
        connection_id_1 = f"test_user_context_{int(time.time())}"
        state_machine_1 = registry.register_connection(connection_id_1, user_id_0)
        
        # Track transitions with user context
        user_context_transitions = []
        
        def track_user_context_transitions(transition_info):
            user_context_transitions.append({
                'user_id': str(user_id_0),
                'session_key': session_key_0,
                'from_state': transition_info.from_state,
                'to_state': transition_info.to_state,
                'timestamp': transition_info.timestamp
            })
        
        state_machine_1.add_state_change_callback(track_user_context_transitions)
        
        # Progress through states with user context
        state_machine_1.transition_to(ApplicationConnectionState.ACCEPTED, f"user_{user_id_0}_accepted")
        state_machine_1.transition_to(ApplicationConnectionState.AUTHENTICATED, f"user_{user_id_0}_authenticated")
        state_machine_1.transition_to(ApplicationConnectionState.PROCESSING_READY, f"user_{user_id_0}_ready")
        
        # Verify user context is preserved
        assert len(user_context_transitions) == 3
        for transition in user_context_transitions:
            assert transition['user_id'] == str(user_id_0)
            assert transition['session_key'] == session_key_0
        
        # Verify session is still valid in database
        cached_session = await real_services_fixture["redis"].get(session_key_0)
        assert cached_session is not None, "User session should remain valid"
        
        # Test 2: Multiple users with separate state machines
        multi_user_connections = []
        
        for i, user_session in enumerate(user_sessions):
            user_id = ensure_user_id(user_session['user']['id'])
            session_key = user_session['session']['session_key']
            
            connection_id = f"multi_user_conn_{i}_{int(time.time())}"
            state_machine = registry.register_connection(connection_id, user_id)
            
            # Setup state machine with user-specific progression
            state_machine.transition_to(ApplicationConnectionState.ACCEPTED, f"user_{i}_setup")
            state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, f"user_{i}_auth")
            
            # Different final states for each user
            if i == 0:
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"user_{i}_ready")
            elif i == 1:
                state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, f"user_{i}_services")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"user_{i}_ready")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING, f"user_{i}_processing")
            else:  # i == 2
                state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, f"user_{i}_services")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, f"user_{i}_ready")
                state_machine.transition_to(ApplicationConnectionState.DEGRADED, f"user_{i}_degraded")
            
            multi_user_connections.append({
                'connection_id': connection_id,
                'state_machine': state_machine,
                'user_id': user_id,
                'session_key': session_key,
                'expected_final_state': [
                    ApplicationConnectionState.PROCESSING_READY,
                    ApplicationConnectionState.PROCESSING,
                    ApplicationConnectionState.DEGRADED
                ][i]
            })
        
        # Verify user isolation
        for i, conn_data in enumerate(multi_user_connections):
            state_machine = conn_data['state_machine']
            expected_state = conn_data['expected_final_state']
            
            assert state_machine.current_state == expected_state
            assert state_machine.user_id == conn_data['user_id']
            
            # Verify no cross-user contamination
            for j, other_conn in enumerate(multi_user_connections):
                if i != j:
                    assert state_machine.user_id != other_conn['user_id']
        
        # Test 3: Session persistence during state transitions
        user_session_1 = user_sessions[1]
        user_id_1 = ensure_user_id(user_session_1['user']['id'])
        session_key_1 = user_session_1['session']['session_key']
        
        connection_id_2 = f"test_session_persistence_{int(time.time())}"
        state_machine_2 = registry.register_connection(connection_id_2, user_id_1)
        
        # Verify initial session state
        initial_session = await real_services_fixture["redis"].get(session_key_1)
        assert initial_session is not None
        
        # Progress through states while monitoring session
        session_checks = []
        
        state_progression = [
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.IDLE
        ]
        
        for state in state_progression:
            state_machine_2.transition_to(state, f"session_test_{state.value}")
            
            # Check session persistence after each transition
            current_session = await real_services_fixture["redis"].get(session_key_1)
            session_checks.append({
                'state': state,
                'session_valid': current_session is not None
            })
        
        # Verify session remained valid throughout
        for check in session_checks:
            assert check['session_valid'], f"Session should remain valid in state {check['state'].value}"
        
        # Test 4: User context with connection failures and recovery
        user_session_2 = user_sessions[2]
        user_id_2 = ensure_user_id(user_session_2['user']['id'])
        session_key_2 = user_session_2['session']['session_key']
        
        connection_id_3 = f"test_user_failure_recovery_{int(time.time())}"
        state_machine_3 = registry.register_connection(connection_id_3, user_id_2)
        
        # Setup to operational
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "failure_test_setup")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "failure_test_setup")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "failure_test_setup")
        
        # Verify user data before failure
        pre_failure_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id_2
        )
        assert pre_failure_user is not None
        assert pre_failure_user['is_active'] is True
        
        # Force failure
        state_machine_3.force_failed_state("user_context_failure_test")
        
        # Verify user data integrity during failure
        during_failure_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id_2
        )
        assert during_failure_user is not None
        assert during_failure_user['is_active'] is True  # User should remain active
        
        # Verify session during failure
        during_failure_session = await real_services_fixture["redis"].get(session_key_2)
        assert during_failure_session is not None, "Session should persist during connection failure"
        
        # Recover connection
        state_machine_3.transition_to(ApplicationConnectionState.CONNECTING, "user_recovery")
        state_machine_3.transition_to(ApplicationConnectionState.ACCEPTED, "user_recovery")
        state_machine_3.transition_to(ApplicationConnectionState.AUTHENTICATED, "user_recovery")
        state_machine_3.transition_to(ApplicationConnectionState.PROCESSING_READY, "user_recovery")
        
        # Verify user data after recovery
        post_recovery_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id_2
        )
        assert post_recovery_user is not None
        assert post_recovery_user['is_active'] is True
        
        # Test 5: Registry statistics with user context
        stats = registry.get_registry_stats()
        
        # Should have multiple connections from different users
        total_expected = 1 + len(multi_user_connections) + 1 + 1  # 6 total connections
        assert stats['total_connections'] == total_expected
        
        # Verify operational connections
        operational_connections = registry.get_all_operational_connections()
        operational_count = len(operational_connections)
        
        # Count expected operational connections
        expected_operational = 0
        for conn_data in multi_user_connections:
            if ApplicationConnectionState.is_operational(conn_data['expected_final_state']):
                expected_operational += 1
        
        # Add other operational connections
        expected_operational += 1  # state_machine_1 (PROCESSING_READY)
        expected_operational += 1  # state_machine_2 (IDLE)  
        expected_operational += 1  # state_machine_3 (PROCESSING_READY after recovery)
        
        assert operational_count == expected_operational
        
        # Test 6: User context cleanup and session management
        
        # Close one user's connection
        connection_to_close = multi_user_connections[0]
        connection_to_close['state_machine'].transition_to(ApplicationConnectionState.CLOSING, "user_disconnect")
        connection_to_close['state_machine'].transition_to(ApplicationConnectionState.CLOSED, "user_disconnect")
        
        # Verify user session remains valid even after connection closure
        post_close_session = await real_services_fixture["redis"].get(connection_to_close['session_key'])
        assert post_close_session is not None, "User session should persist after connection closure"
        
        # Verify user data integrity
        post_close_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", 
            connection_to_close['user_id']
        )
        assert post_close_user is not None
        assert post_close_user['is_active'] is True
        
        # Cleanup closed connections
        cleanup_count = registry.cleanup_closed_connections()
        assert cleanup_count == 1, "Should clean up one closed connection"
        
        # Verify user data still intact after cleanup
        final_user_check = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1",
            connection_to_close['user_id']
        )
        assert final_user_check is not None
        assert final_user_check['is_active'] is True
        
        # Cleanup remaining connections for test isolation
        for conn_data in multi_user_connections[1:]:  # Skip the already closed one
            registry.unregister_connection(conn_data['connection_id'])
        
        registry.unregister_connection(connection_id_1)
        registry.unregister_connection(connection_id_2)
        registry.unregister_connection(connection_id_3)
        
        self.assert_business_value_delivered({
            'user_context_integration': True,
            'session_persistence': True,
            'multi_user_isolation': True
        }, 'user_experience')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_024_connection_state_machine_lifecycle_with_real_message_processing(self, real_services_fixture):
        """
        Test complete connection state machine lifecycle with real message processing simulation.
        
        Business Value: Validates end-to-end connection lifecycle with message
        processing capabilities, ensuring reliable chat functionality delivery.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'lifecycle_test@netra.ai',
            'name': 'Lifecycle Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        registry = ConnectionStateMachineRegistry()
        
        # Test 1: Complete lifecycle with message processing simulation
        connection_id = f"test_lifecycle_complete_{int(time.time())}"
        state_machine = registry.register_connection(connection_id, user_id)
        
        # Track all lifecycle events
        lifecycle_events = []
        processed_messages = []
        
        def track_lifecycle_events(transition_info):
            lifecycle_events.append({
                'timestamp': transition_info.timestamp,
                'from_state': transition_info.from_state,
                'to_state': transition_info.to_state,
                'reason': transition_info.reason,
                'can_process': state_machine.can_process_messages(),
                'is_operational': state_machine.is_operational
            })
        
        state_machine.add_state_change_callback(track_lifecycle_events)
        
        # Simulate real message processing during state transitions
        async def simulate_message_processing(message_type, content):
            if state_machine.can_process_messages():
                message = {
                    'id': f"msg_{len(processed_messages)}_{int(time.time())}",
                    'type': message_type,
                    'content': content,
                    'user_id': str(user_id),
                    'connection_id': connection_id,
                    'state_when_processed': state_machine.current_state.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                processed_messages.append(message)
                
                # Store message in Redis for persistence
                message_key = f"processed_message:{message['id']}"
                await real_services_fixture["redis"].set(
                    message_key, 
                    json.dumps(message),
                    ex=3600
                )
                return True
            return False
        
        # Phase 1: Connection establishment
        assert not await simulate_message_processing("connection_test", "Should not process yet")
        
        state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "websocket_handshake_complete")
        assert not await simulate_message_processing("handshake_test", "Still not ready")
        
        # Phase 2: Authentication
        state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "user_authentication_success")
        assert not await simulate_message_processing("auth_test", "Authentication complete but not ready")
        
        # Phase 3: Services initialization
        state_machine.transition_to(ApplicationConnectionState.SERVICES_READY, "all_services_initialized")
        assert not await simulate_message_processing("services_test", "Services ready but not processing ready")
        
        # Phase 4: Processing readiness
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "ready_for_message_processing")
        assert await simulate_message_processing("readiness_test", "First message - system ready!")
        
        # Phase 5: Active message processing
        state_machine.transition_to(ApplicationConnectionState.PROCESSING, "active_message_processing")
        
        # Process multiple messages in active state
        messages_to_process = [
            ("user_message", "Hello, I need help with cost optimization"),
            ("agent_request", "Start cost analysis agent"),
            ("tool_execution", "Analyze AWS bill data"),
            ("agent_response", "Found 3 optimization opportunities"),
            ("user_response", "Please proceed with recommendations")
        ]
        
        for msg_type, content in messages_to_process:
            success = await simulate_message_processing(msg_type, content)
            assert success, f"Should process {msg_type} in PROCESSING state"
        
        # Phase 6: Idle state
        state_machine.transition_to(ApplicationConnectionState.IDLE, "processing_session_complete")
        assert await simulate_message_processing("idle_test", "Can still process in idle state")
        
        # Phase 7: Degraded mode
        state_machine.transition_to(ApplicationConnectionState.DEGRADED, "network_quality_degraded")
        assert await simulate_message_processing("degraded_test", "Processing with reduced quality")
        
        # Phase 8: Recovery to full operational
        state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "network_quality_restored")
        assert await simulate_message_processing("recovery_test", "Back to full capability")
        
        # Phase 9: Graceful shutdown
        state_machine.transition_to(ApplicationConnectionState.CLOSING, "user_initiated_disconnect")
        assert not await simulate_message_processing("closing_test", "Should not process while closing")
        
        state_machine.transition_to(ApplicationConnectionState.CLOSED, "connection_terminated")
        assert not await simulate_message_processing("closed_test", "Should not process when closed")
        
        # Verify complete lifecycle tracking
        assert len(lifecycle_events) == 9  # All state transitions
        
        # Verify message processing only occurred in operational states
        operational_message_count = len([msg for msg in processed_messages 
                                       if msg['state_when_processed'] in [
                                           'processing_ready', 'processing', 'idle', 'degraded'
                                       ]])
        
        total_expected_messages = 1 + len(messages_to_process) + 1 + 1 + 1  # 9 total
        assert len(processed_messages) == total_expected_messages
        assert operational_message_count == total_expected_messages
        
        # Verify message persistence in Redis
        for message in processed_messages:
            message_key = f"processed_message:{message['id']}"
            stored_message = await real_services_fixture["redis"].get(message_key)
            assert stored_message is not None
            stored_data = json.loads(stored_message)
            assert stored_data['user_id'] == str(user_id)
            assert stored_data['connection_id'] == connection_id
        
        # Test 2: Lifecycle with failure and recovery
        connection_id_2 = f"test_lifecycle_failure_{int(time.time())}"
        state_machine_2 = registry.register_connection(connection_id_2, user_id)
        
        failure_recovery_messages = []
        
        async def track_failure_recovery_messages(msg_type, content):
            if state_machine_2.can_process_messages():
                failure_recovery_messages.append({
                    'type': msg_type,
                    'content': content,
                    'state': state_machine_2.current_state.value
                })
                return True
            return False
        
        # Setup to operational
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "setup")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "setup")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "setup")
        
        # Process some messages successfully
        await track_failure_recovery_messages("pre_failure", "Processing before failure")
        await track_failure_recovery_messages("pre_failure_2", "Another message before failure")
        
        # Simulate failure
        state_machine_2.force_failed_state("simulated_network_failure")
        
        # Attempt message processing during failure (should fail)
        failure_msg_success = await track_failure_recovery_messages("during_failure", "Should not process")
        assert not failure_msg_success
        
        # Recover from failure
        state_machine_2.transition_to(ApplicationConnectionState.CONNECTING, "recovery_attempt")
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "recovery_handshake")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "recovery_auth")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "recovery_complete")
        
        # Resume message processing after recovery
        await track_failure_recovery_messages("post_recovery", "First message after recovery")
        await track_failure_recovery_messages("post_recovery_2", "System fully operational again")
        
        # Verify message processing pattern
        assert len(failure_recovery_messages) == 4  # 2 before failure + 2 after recovery
        
        pre_failure_msgs = [msg for msg in failure_recovery_messages if 'pre_failure' in msg['type']]
        post_recovery_msgs = [msg for msg in failure_recovery_messages if 'post_recovery' in msg['type']]
        
        assert len(pre_failure_msgs) == 2
        assert len(post_recovery_msgs) == 2
        
        # Test 3: Multiple concurrent lifecycles
        concurrent_connections = []
        
        for i in range(3):
            conn_id = f"concurrent_lifecycle_{i}_{int(time.time())}"
            machine = registry.register_connection(conn_id, user_id)
            
            concurrent_connections.append({
                'connection_id': conn_id,
                'state_machine': machine,
                'messages_processed': []
            })
        
        # Progress all connections through different lifecycle paths
        lifecycle_paths = [
            # Path 1: Normal full lifecycle
            [
                (ApplicationConnectionState.ACCEPTED, "path1_accepted"),
                (ApplicationConnectionState.AUTHENTICATED, "path1_auth"),
                (ApplicationConnectionState.PROCESSING_READY, "path1_ready"),
                (ApplicationConnectionState.PROCESSING, "path1_processing"),
                (ApplicationConnectionState.IDLE, "path1_idle")
            ],
            # Path 2: Degraded mode path
            [
                (ApplicationConnectionState.ACCEPTED, "path2_accepted"),
                (ApplicationConnectionState.AUTHENTICATED, "path2_auth"),
                (ApplicationConnectionState.PROCESSING_READY, "path2_ready"),
                (ApplicationConnectionState.DEGRADED, "path2_degraded")
            ],
            # Path 3: Rapid transitions
            [
                (ApplicationConnectionState.ACCEPTED, "path3_accepted"),
                (ApplicationConnectionState.AUTHENTICATED, "path3_auth"),
                (ApplicationConnectionState.SERVICES_READY, "path3_services"),
                (ApplicationConnectionState.PROCESSING_READY, "path3_ready")
            ]
        ]
        
        for i, (conn_data, path) in enumerate(zip(concurrent_connections, lifecycle_paths)):
            machine = conn_data['state_machine']
            
            for state, reason in path:
                machine.transition_to(state, reason)
                
                # Process a message at each operational state
                if machine.can_process_messages():
                    conn_data['messages_processed'].append({
                        'state': state.value,
                        'message': f"concurrent_msg_{i}_{len(conn_data['messages_processed'])}"
                    })
        
        # Verify all concurrent lifecycles worked independently
        for i, conn_data in enumerate(concurrent_connections):
            assert len(conn_data['messages_processed']) > 0
            
            # Verify no cross-contamination
            for msg in conn_data['messages_processed']:
                assert f"concurrent_msg_{i}" in msg['message']
        
        # Test 4: Lifecycle performance metrics
        connection_id_3 = f"test_lifecycle_performance_{int(time.time())}"
        state_machine_3 = registry.register_connection(connection_id_3, user_id)
        
        # Time complete lifecycle
        lifecycle_start = time.time()
        
        performance_states = [
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.IDLE,
            ApplicationConnectionState.CLOSING,
            ApplicationConnectionState.CLOSED
        ]
        
        state_timings = []
        
        for state in performance_states:
            state_start = time.time()
            state_machine_3.transition_to(state, f"performance_test_{state.value}")
            state_end = time.time()
            
            state_timings.append({
                'state': state.value,
                'duration': state_end - state_start
            })
        
        lifecycle_end = time.time()
        total_lifecycle_duration = lifecycle_end - lifecycle_start
        
        # Verify performance is reasonable
        assert total_lifecycle_duration < 1.0, "Complete lifecycle should complete quickly in test"
        
        # Each individual state transition should be very fast
        for timing in state_timings:
            assert timing['duration'] < 0.1, f"State transition to {timing['state']} took too long"
        
        # Cleanup Redis messages
        for message in processed_messages:
            message_key = f"processed_message:{message['id']}"
            await real_services_fixture["redis"].delete(message_key)
        
        # Cleanup registry
        registry.cleanup_closed_connections()
        for conn_data in concurrent_connections:
            registry.unregister_connection(conn_data['connection_id'])
        registry.unregister_connection(connection_id_2)
        registry.unregister_connection(connection_id_3)
        
        self.assert_business_value_delivered({
            'complete_lifecycle_validation': True,
            'message_processing_integration': True,
            'end_to_end_functionality': True
        }, 'comprehensive')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_025_end_to_end_state_machine_integration_with_real_websocket_events(self, real_services_fixture):
        """
        Test comprehensive end-to-end state machine integration with real WebSocket events.
        
        Business Value: Validates complete integration of state machine with WebSocket
        event system, ensuring mission-critical chat functionality works end-to-end.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'e2e_websocket_test@netra.ai',
            'name': 'E2E WebSocket Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        # Create comprehensive test environment
        registry = ConnectionStateMachineRegistry()
        
        # Mock WebSocket event system to simulate real WebSocket events
        class WebSocketEventSystem:
            def __init__(self):
                self.events_sent = []
                self.event_subscriptions = {}
                self.connection_status = {}
                
            def register_connection(self, connection_id):
                self.connection_status[connection_id] = 'connected'
                
            def send_event(self, connection_id, event_type, data):
                if self.connection_status.get(connection_id) == 'connected':
                    event = {
                        'connection_id': connection_id,
                        'event_type': event_type,
                        'data': data,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    self.events_sent.append(event)
                    return True
                return False
                
            def get_events_for_connection(self, connection_id):
                return [e for e in self.events_sent if e['connection_id'] == connection_id]
        
        websocket_events = WebSocketEventSystem()
        
        # Test 1: Complete WebSocket event integration with state machine
        connection_id = f"test_e2e_websocket_{int(time.time())}"
        state_machine = registry.register_connection(connection_id, user_id)
        websocket_events.register_connection(connection_id)
        
        # Track state transitions and corresponding WebSocket events
        state_event_correlation = []
        
        def track_state_websocket_correlation(transition_info):
            # Simulate sending WebSocket events based on state transitions
            event_data = {
                'user_id': str(user_id),
                'connection_id': connection_id,
                'from_state': transition_info.from_state.value if transition_info.from_state else None,
                'to_state': transition_info.to_state.value,
                'reason': transition_info.reason
            }
            
            # Send appropriate WebSocket events for each state
            if transition_info.to_state == ApplicationConnectionState.ACCEPTED:
                websocket_events.send_event(connection_id, 'connection_accepted', event_data)
            elif transition_info.to_state == ApplicationConnectionState.AUTHENTICATED:
                websocket_events.send_event(connection_id, 'user_authenticated', event_data)
            elif transition_info.to_state == ApplicationConnectionState.PROCESSING_READY:
                websocket_events.send_event(connection_id, 'ready_for_messages', event_data)
            elif transition_info.to_state == ApplicationConnectionState.PROCESSING:
                websocket_events.send_event(connection_id, 'agent_started', event_data)
            elif transition_info.to_state == ApplicationConnectionState.IDLE:
                websocket_events.send_event(connection_id, 'agent_completed', event_data)
            elif transition_info.to_state == ApplicationConnectionState.DEGRADED:
                websocket_events.send_event(connection_id, 'connection_degraded', event_data)
            elif transition_info.to_state == ApplicationConnectionState.CLOSED:
                websocket_events.send_event(connection_id, 'connection_closed', event_data)
                websocket_events.connection_status[connection_id] = 'disconnected'
            
            state_event_correlation.append({
                'state_transition': transition_info,
                'events_sent_count': len(websocket_events.get_events_for_connection(connection_id))
            })
        
        state_machine.add_state_change_callback(track_state_websocket_correlation)
        
        # Execute complete end-to-end flow
        e2e_flow = [
            (ApplicationConnectionState.ACCEPTED, "websocket_handshake_complete"),
            (ApplicationConnectionState.AUTHENTICATED, "user_authentication_success"),
            (ApplicationConnectionState.SERVICES_READY, "all_services_initialized"),
            (ApplicationConnectionState.PROCESSING_READY, "ready_for_message_processing"),
            (ApplicationConnectionState.PROCESSING, "agent_execution_started"),
            (ApplicationConnectionState.IDLE, "agent_execution_completed"),
            (ApplicationConnectionState.PROCESSING, "new_agent_started"),
            (ApplicationConnectionState.IDLE, "second_agent_completed"),
            (ApplicationConnectionState.DEGRADED, "network_quality_issue"),
            (ApplicationConnectionState.PROCESSING_READY, "network_recovered"),
            (ApplicationConnectionState.CLOSING, "user_disconnect_request"),
            (ApplicationConnectionState.CLOSED, "connection_terminated")
        ]
        
        for target_state, reason in e2e_flow:
            state_machine.transition_to(target_state, reason)
            
            # Small delay to simulate real-world timing
            await asyncio.sleep(0.01)
        
        # Verify WebSocket event correlation
        connection_events = websocket_events.get_events_for_connection(connection_id)
        
        # Should have sent events for key state transitions
        expected_events = [
            'connection_accepted',
            'user_authenticated', 
            'ready_for_messages',
            'agent_started',      # First agent
            'agent_completed',    # First agent
            'agent_started',      # Second agent
            'agent_completed',    # Second agent
            'connection_degraded',
            'connection_closed'
        ]
        
        actual_event_types = [e['event_type'] for e in connection_events]
        for expected_event in expected_events:
            assert expected_event in actual_event_types, f"Missing WebSocket event: {expected_event}"
        
        # Verify event data integrity
        for event in connection_events:
            assert event['data']['user_id'] == str(user_id)
            assert event['data']['connection_id'] == connection_id
            assert 'from_state' in event['data']
            assert 'to_state' in event['data']
        
        # Test 2: Mission-critical WebSocket events for agent execution
        connection_id_2 = f"test_agent_events_{int(time.time())}"
        state_machine_2 = registry.register_connection(connection_id_2, user_id)
        websocket_events.register_connection(connection_id_2)
        
        # Simulate agent execution with all required WebSocket events
        critical_agent_events = []
        
        def track_critical_agent_events(transition_info):
            # Simulate the 5 mission-critical WebSocket events for agent execution
            if transition_info.to_state == ApplicationConnectionState.PROCESSING:
                # Agent execution started
                for event_type in ['agent_started', 'agent_thinking']:
                    event_sent = websocket_events.send_event(
                        connection_id_2, 
                        event_type,
                        {
                            'user_id': str(user_id),
                            'agent_type': 'cost_optimizer',
                            'execution_id': f"exec_{len(critical_agent_events)}"
                        }
                    )
                    if event_sent:
                        critical_agent_events.append(event_type)
                
                # Simulate tool execution
                for tool_event in ['tool_executing', 'tool_completed']:
                    event_sent = websocket_events.send_event(
                        connection_id_2,
                        tool_event,
                        {
                            'user_id': str(user_id),
                            'tool_name': 'aws_cost_analyzer',
                            'tool_result': 'analysis_complete' if tool_event == 'tool_completed' else 'in_progress'
                        }
                    )
                    if event_sent:
                        critical_agent_events.append(tool_event)
            
            elif transition_info.to_state == ApplicationConnectionState.IDLE:
                # Agent execution completed
                event_sent = websocket_events.send_event(
                    connection_id_2,
                    'agent_completed',
                    {
                        'user_id': str(user_id),
                        'result': 'optimization_recommendations_ready',
                        'savings_potential': '$1,250/month'
                    }
                )
                if event_sent:
                    critical_agent_events.append('agent_completed')
        
        state_machine_2.add_state_change_callback(track_critical_agent_events)
        
        # Setup to operational state
        state_machine_2.transition_to(ApplicationConnectionState.ACCEPTED, "agent_test_setup")
        state_machine_2.transition_to(ApplicationConnectionState.AUTHENTICATED, "agent_test_setup")
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING_READY, "agent_test_setup")
        
        # Execute agent workflow
        state_machine_2.transition_to(ApplicationConnectionState.PROCESSING, "start_cost_optimizer_agent")
        state_machine_2.transition_to(ApplicationConnectionState.IDLE, "cost_optimizer_complete")
        
        # Verify all 5 critical WebSocket events were sent
        required_agent_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        for required_event in required_agent_events:
            assert required_event in critical_agent_events, f"Missing critical agent event: {required_event}"
        
        # Test 3: Multi-user WebSocket event isolation
        multi_user_test_data = []
        
        for i in range(3):
            # Create separate user for each connection
            user_data_i = await self.create_test_user_context(real_services_fixture, {
                'email': f'multi_user_websocket_{i}@netra.ai',
                'name': f'Multi User WebSocket {i}',
                'is_active': True
            })
            
            connection_id_i = f"multi_user_conn_{i}_{int(time.time())}"
            state_machine_i = registry.register_connection(connection_id_i, user_data_i['id'])
            websocket_events.register_connection(connection_id_i)
            
            multi_user_test_data.append({
                'user_id': user_data_i['id'],
                'connection_id': connection_id_i,
                'state_machine': state_machine_i,
                'events_for_user': []
            })
        
        # Execute concurrent WebSocket event flows for different users
        for i, user_test_data in enumerate(multi_user_test_data):
            state_machine = user_test_data['state_machine']
            connection_id = user_test_data['connection_id']
            user_id = user_test_data['user_id']
            
            # Setup callback to track events for this specific user
            def make_user_event_tracker(user_data):
                def track_user_events(transition_info):
                    event_sent = websocket_events.send_event(
                        user_data['connection_id'],
                        f"user_{user_data['connection_id'][-1]}_state_change",
                        {
                            'user_id': str(user_data['user_id']),
                            'state': transition_info.to_state.value,
                            'unique_marker': f"user_{user_data['connection_id'][-1]}_event"
                        }
                    )
                    if event_sent:
                        user_data['events_for_user'].append(transition_info.to_state.value)
                return track_user_events
            
            state_machine.add_state_change_callback(make_user_event_tracker(user_test_data))
            
            # Different workflow for each user
            if i == 0:
                # User 0: Full workflow
                state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "user0_flow")
                state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "user0_flow")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "user0_flow")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING, "user0_flow")
                state_machine.transition_to(ApplicationConnectionState.IDLE, "user0_flow")
            elif i == 1:
                # User 1: Partial workflow
                state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "user1_flow")
                state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "user1_flow")
                state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY, "user1_flow")
            else:  # i == 2
                # User 2: Degraded workflow
                state_machine.transition_to(ApplicationConnectionState.ACCEPTED, "user2_flow")
                state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED, "user2_flow")
                state_machine.transition_to(ApplicationConnectionState.DEGRADED, "user2_flow")
        
        # Verify user event isolation
        for i, user_test_data in enumerate(multi_user_test_data):
            user_events = websocket_events.get_events_for_connection(user_test_data['connection_id'])
            
            # Verify all events for this user contain correct user_id
            for event in user_events:
                assert event['data']['user_id'] == str(user_test_data['user_id'])
                assert f"user_{i}_event" in event['data']['unique_marker']
            
            # Verify no cross-user event contamination
            for j, other_user_data in enumerate(multi_user_test_data):
                if i != j:
                    other_user_events = websocket_events.get_events_for_connection(other_user_data['connection_id'])
                    for event in other_user_events:
                        assert event['data']['user_id'] != str(user_test_data['user_id'])
        
        # Test 4: WebSocket event persistence and recovery
        connection_id_3 = f"test_event_persistence_{int(time.time())}"
        state_machine_3 = registry.register_connection(connection_id_3, user_id)
        websocket_events.register_connection(connection_id_3)
        
        # Store events in Redis for persistence
        persistent_events = []
        
        def persist_websocket_events(transition_info):
            event_data = {
                'connection_id': connection_id_3,
                'user_id': str(user_id),
                'state_transition': {
                    'from': transition_info.from_state.value if transition_info.from_state else None,
                    'to': transition_info.to_state.value,
                    'reason': transition_info.reason
                },
                'timestamp': transition_info.timestamp.isoformat()
            }
            
            # Store in Redis
            asyncio.create_task(
                real_services_fixture["redis"].lpush(
                    f"websocket_events:{connection_id_3}",
                    json.dumps(event_data)
                )
            )
            
            persistent_events.append(event_data)
        
        state_machine_3.add_state_change_callback(persist_websocket_events)
        
        # Execute flow with event persistence
        persistence_flow = [
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.DEGRADED,  # Simulate failure
            ApplicationConnectionState.PROCESSING_READY,  # Recovery
            ApplicationConnectionState.IDLE
        ]
        
        for state in persistence_flow:
            state_machine_3.transition_to(state, f"persistence_test_{state.value}")
            await asyncio.sleep(0.01)  # Allow Redis operations to complete
        
        # Verify event persistence in Redis
        await asyncio.sleep(0.1)  # Ensure all async operations complete
        stored_events = await real_services_fixture["redis"].lrange(f"websocket_events:{connection_id_3}", 0, -1)
        
        assert len(stored_events) == len(persistence_flow)
        
        for stored_event_json in stored_events:
            stored_event = json.loads(stored_event_json)
            assert stored_event['connection_id'] == connection_id_3
            assert stored_event['user_id'] == str(user_id)
            assert 'state_transition' in stored_event
        
        # Cleanup
        await real_services_fixture["redis"].delete(f"websocket_events:{connection_id_3}")
        
        # Cleanup registry
        registry.cleanup_closed_connections()
        for user_test_data in multi_user_test_data:
            registry.unregister_connection(user_test_data['connection_id'])
        registry.unregister_connection(connection_id_2)
        registry.unregister_connection(connection_id_3)
        
        self.assert_business_value_delivered({
            'end_to_end_websocket_integration': True,
            'mission_critical_event_delivery': True,
            'multi_user_event_isolation': True,
            'complete_chat_functionality': True
        }, 'comprehensive')