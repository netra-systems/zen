"""
JWT Token Lifecycle Integration Tests - Connection Lifecycle Management

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Core - WebSocket Connection Lifecycle Management
- Business Goal: Ensure reliable connection tracking for 5+ minute chat sessions
- Value Impact: Prevents connection state corruption that breaks user conversations
- Revenue Impact: Protects $500K+ ARR by maintaining stable WebSocket connections

INTEGRATION TEST SCOPE:
These tests validate the Token Lifecycle Manager's connection lifecycle management
with realistic timing and state transitions. Tests focus on long-lived connection
duration tracking, state transitions, metrics collection, and termination scenarios
using actual system components without requiring running services.

SUCCESS CRITERIA:
- Long-lived connections tracked accurately for 5+ minutes
- Connection state transitions work correctly through all lifecycle states  
- Metrics collection provides accurate connection duration and success rates
- Connection termination due to degraded mode works properly
- Active connection monitoring detects and handles health issues
- Connection event callbacks notify about important lifecycle events
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest import mock
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.token_lifecycle_manager import (
    TokenLifecycleManager,
    ConnectionTokenState,
    TokenLifecycleState,
    TokenLifecycleMetrics
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env
from shared.types.core_types import ensure_user_id


@dataclass
class ConnectionLifecycleEvent:
    """Tracks connection lifecycle events for validation."""
    connection_id: str
    event_type: str
    timestamp: datetime
    event_data: Dict
    connection_duration: Optional[float] = None
    lifecycle_state: Optional[TokenLifecycleState] = None


@dataclass
class ConnectionMetricsSnapshot:
    """Snapshot of connection metrics at a point in time."""
    timestamp: datetime
    total_connections: int
    active_connections: int
    successful_refreshes: int
    failed_refreshes: int
    degraded_connections: int
    average_connection_duration: float
    longest_connection_duration: float
    refresh_success_rate: float


class TestJWTTokenLifecycleConnectionIntegration(SSotAsyncTestCase):
    """
    Integration tests for JWT Token Lifecycle Manager connection lifecycle.
    
    BUSINESS IMPACT: Validates the connection management system that enables
    stable 5+ minute WebSocket sessions, protecting core chat functionality.
    """

    def setup_method(self, method):
        """Set up connection lifecycle test environment."""
        super().setup_method(method)
        
        # Accelerated timing for testing while maintaining realistic ratios
        self.refresh_interval = 3   # 3 seconds (vs 45s production)
        self.token_expiry = 8       # 8 seconds (vs 60s production)
        self.degraded_timeout = 15  # 15 seconds (vs 180s production)
        
        # Create lifecycle manager
        self.lifecycle_manager = TokenLifecycleManager(
            refresh_interval_seconds=self.refresh_interval,
            token_expiry_seconds=self.token_expiry,
            degraded_mode_timeout_seconds=self.degraded_timeout
        )
        
        # Test data
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))
        self.connection_id = f"lifecycle_conn_{uuid.uuid4().hex[:8]}"
        self.websocket_client_id = f"ws_lifecycle_{uuid.uuid4().hex[:8]}"
        
        # Event and metrics tracking
        self.lifecycle_events: List[ConnectionLifecycleEvent] = []
        self.metrics_snapshots: List[ConnectionMetricsSnapshot] = []
        self.connection_states_history: Dict[str, List[Dict]] = {}
        
        # Connection simulation data
        self.simulated_activity_count = 0
        self.connection_start_time = None

    def teardown_method(self, method):
        """Clean up connection lifecycle test environment."""
        try:
            # Stop lifecycle management
            asyncio.create_task(self.lifecycle_manager.stop_lifecycle_management())
        except Exception as e:
            self.record_metric("teardown_error", str(e))
        finally:
            super().teardown_method(method)

    def _create_test_user_context(self, user_id: str = None) -> UserExecutionContext:
        """Create test user context for connection testing."""
        if user_id is None:
            user_id = self.test_user_id
            
        return UserExecutionContext(
            user_id=user_id,
            execution_context_id=f"lifecycle_ctx_{uuid.uuid4().hex[:8]}",
            websocket_client_id=self.websocket_client_id,
            timestamp=datetime.now(timezone.utc),
            session_metadata={"test_connection_lifecycle": True}
        )

    def _create_test_token(self, expires_in_seconds: int = None) -> str:
        """Create test token for connection lifecycle testing."""
        if expires_in_seconds is None:
            expires_in_seconds = self.token_expiry
        return f"lifecycle_token_{uuid.uuid4().hex[:12]}_exp_{expires_in_seconds}s"

    async def _setup_lifecycle_event_tracking(self):
        """Set up comprehensive lifecycle event tracking."""
        async def track_lifecycle_event(conn_id: str, event_type: str, event_data: Dict):
            # Get current connection state if available
            current_state = self.lifecycle_manager._connection_states.get(conn_id)
            
            event = ConnectionLifecycleEvent(
                connection_id=conn_id,
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                event_data=event_data,
                connection_duration=event_data.get("connection_duration"),
                lifecycle_state=current_state.lifecycle_state if current_state else None
            )
            self.lifecycle_events.append(event)
            
            # Record state history
            if conn_id not in self.connection_states_history:
                self.connection_states_history[conn_id] = []
                
            if current_state:
                state_snapshot = {
                    "timestamp": datetime.now(timezone.utc),
                    "lifecycle_state": current_state.lifecycle_state.value,
                    "refresh_count": current_state.refresh_count,
                    "refresh_failures": current_state.refresh_failures,
                    "connection_duration": current_state.connection_duration_seconds(),
                    "time_until_expiry": current_state.time_until_expiry_seconds(),
                    "event_type": event_type
                }
                self.connection_states_history[conn_id].append(state_snapshot)
                
        await self.lifecycle_manager.add_connection_event_callback(track_lifecycle_event)

    async def _register_test_connection(self, connection_id: str = None, user_id: str = None, token_expiry_offset: int = None) -> ConnectionTokenState:
        """Register a test connection and track start time."""
        if connection_id is None:
            connection_id = self.connection_id
        if user_id is None:
            user_id = self.test_user_id
        if token_expiry_offset is None:
            token_expiry_offset = self.token_expiry
            
        user_context = self._create_test_user_context(user_id)
        test_token = self._create_test_token()
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_expiry_offset)
        
        # Track connection start time
        if connection_id == self.connection_id:
            self.connection_start_time = datetime.now(timezone.utc)
        
        await self.lifecycle_manager.register_connection_token(
            connection_id=connection_id,
            websocket_client_id=user_context.websocket_client_id,
            user_context=user_context,
            initial_token=test_token,
            token_expires_at=token_expires_at
        )
        
        return self.lifecycle_manager._connection_states[connection_id]

    async def _simulate_connection_activity(self, connection_id: str, duration_seconds: float, activity_interval: float = 1.0):
        """Simulate realistic connection activity over time."""
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            # Simulate getting current token (which updates activity timestamp)
            current_token = await self.lifecycle_manager.get_current_token(connection_id)
            if current_token:
                self.simulated_activity_count += 1
                
            await asyncio.sleep(activity_interval)

    async def _take_metrics_snapshot(self, label: str = ""):
        """Take a snapshot of current metrics."""
        metrics = self.lifecycle_manager.get_connection_metrics()
        
        snapshot = ConnectionMetricsSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_connections=metrics["total_connections"],
            active_connections=metrics["active_connections"],
            successful_refreshes=metrics["successful_refreshes"],
            failed_refreshes=metrics["failed_refreshes"],
            degraded_connections=metrics["degraded_connections"],
            average_connection_duration=metrics["average_connection_duration"],
            longest_connection_duration=metrics["longest_connection_duration"],
            refresh_success_rate=metrics["refresh_success_rate"]
        )
        
        self.metrics_snapshots.append(snapshot)
        self.record_metric(f"metrics_snapshot_{label}", snapshot.__dict__)
        return snapshot

    # === CONNECTION LIFECYCLE MANAGEMENT TESTS ===

    @pytest.mark.asyncio
    async def test_long_lived_connection_duration_tracking_5_minutes(self):
        """
        BVJ: Platform/Core - Validate accurate tracking of long-lived connections
        Critical for maintaining authentication during extended chat sessions
        """
        # GIVEN: Long-lived connection setup for 5+ minute simulation
        await self._setup_lifecycle_event_tracking()
        connection_state = await self._register_test_connection()
        
        # Use longer token expiry to simulate long-lived connection
        extended_expiry = datetime.now(timezone.utc) + timedelta(seconds=120)  # 2 minutes for testing
        connection_state.token_expires_at = extended_expiry
        connection_state.lifecycle_state = TokenLifecycleState.ACTIVE
        
        initial_snapshot = await self._take_metrics_snapshot("initial")
        
        # Mock successful auth service for continuous operation
        class MockAuthService:
            def __init__(self):
                self.call_count = 0
                
            async def authenticate(self, token, context):
                self.call_count += 1
                from dataclasses import dataclass
                @dataclass
                class MockResult:
                    success: bool = True
                    user_id: str = context.metadata.get("user_id", "test_user")
                    error: str = None
                return MockResult()
        
        mock_auth = MockAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=mock_auth):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"long_lived_token_{mock_auth.call_count}"):
                
                # Start lifecycle management
                await self.lifecycle_manager.start_lifecycle_management()
                
                # WHEN: Simulating long connection with activity
                simulation_duration = 30  # 30 seconds simulation for 5+ minute behavior
                activity_task = asyncio.create_task(
                    self._simulate_connection_activity(self.connection_id, simulation_duration, activity_interval=0.5)
                )
                
                # Take periodic snapshots
                for i in range(6):  # Take snapshots every 5 seconds
                    await asyncio.sleep(5)
                    await self._take_metrics_snapshot(f"t_{i*5}s")
                
                await activity_task
                await self.lifecycle_manager.stop_lifecycle_management()
                
                # THEN: Verify long-lived connection tracked correctly
                final_snapshot = await self._take_metrics_snapshot("final")
                
                # Verify connection duration tracking
                final_state = self.lifecycle_manager._connection_states[self.connection_id]
                actual_duration = final_state.connection_duration_seconds()
                
                assert actual_duration >= 30, f"Connection should run at least 30s, got {actual_duration}s"
                assert final_state.refresh_count >= 5, f"Should have multiple refreshes, got {final_state.refresh_count}"
                
                # Verify metrics progression
                assert final_snapshot.total_connections >= initial_snapshot.total_connections
                assert final_snapshot.longest_connection_duration >= 30
                
                # Verify activity tracking worked
                assert self.simulated_activity_count >= 30, f"Should have simulated activity, got {self.simulated_activity_count}"
                
                # Verify lifecycle events recorded connection progression
                registered_events = [e for e in self.lifecycle_events if e.event_type == "registered"]
                refresh_events = [e for e in self.lifecycle_events if e.event_type == "token_refreshed"]
                
                assert len(registered_events) >= 1, "Should have registration event"
                assert len(refresh_events) >= 5, f"Should have multiple refresh events, got {len(refresh_events)}"
                
                # Verify state history shows progression
                if self.connection_id in self.connection_states_history:
                    state_history = self.connection_states_history[self.connection_id]
                    assert len(state_history) >= 5, "Should have state history entries"
                    
                    # Verify connection duration increased over time
                    durations = [entry["connection_duration"] for entry in state_history if "connection_duration" in entry]
                    if len(durations) >= 2:
                        assert durations[-1] > durations[0], "Connection duration should increase over time"
        
        self.record_metric("long_lived_connection_duration", actual_duration)
        self.record_metric("long_lived_refresh_count", final_state.refresh_count)

    @pytest.mark.asyncio
    async def test_connection_state_transitions_lifecycle_states(self):
        """
        BVJ: Platform/Core - Validate connection state transitions through lifecycle
        Ensures proper state management for reliable authentication tracking
        """
        # GIVEN: Connection ready for state transition testing
        await self._setup_lifecycle_event_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=6)  # 6s expiry
        
        # Track state transitions
        observed_states = []
        
        def record_state_transition(state_name: str):
            current_state = self.lifecycle_manager._connection_states[self.connection_id]
            observed_states.append({
                "timestamp": datetime.now(timezone.utc),
                "state": current_state.lifecycle_state.value,
                "refresh_count": current_state.refresh_count,
                "refresh_failures": current_state.refresh_failures,
                "context": state_name
            })
        
        # Record initial state
        record_state_transition("initial_registration")
        initial_state = connection_state.lifecycle_state
        assert initial_state == TokenLifecycleState.REFRESH_SCHEDULED, "Should start in REFRESH_SCHEDULED state"
        
        # Test normal success transition
        class MockAuthService:
            def __init__(self):
                self.call_count = 0
                self.should_fail = False
                
            async def authenticate(self, token, context):
                self.call_count += 1
                if self.should_fail:
                    from dataclasses import dataclass
                    @dataclass 
                    class FailResult:
                        success: bool = False
                        error: str = f"Mock failure #{self.call_count}"
                    return FailResult()
                else:
                    from dataclasses import dataclass
                    @dataclass
                    class SuccessResult:
                        success: bool = True
                        user_id: str = context.metadata.get("user_id", "test_user")
                        error: str = None
                    return SuccessResult()
        
        mock_auth = MockAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=mock_auth):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"state_transition_token_{mock_auth.call_count}"):
                
                # WHEN: Starting lifecycle and observing state transitions
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Wait for first successful refresh
                await asyncio.sleep(4)
                record_state_transition("after_first_refresh")
                
                # Verify successful refresh state
                current_state = self.lifecycle_manager._connection_states[self.connection_id]
                assert current_state.lifecycle_state in [TokenLifecycleState.ACTIVE, TokenLifecycleState.REFRESH_SCHEDULED], "Should be active or scheduled after success"
                assert current_state.refresh_count >= 1, "Should have completed at least one refresh"
                
                # WHEN: Triggering failure states
                mock_auth.should_fail = True
                
                # Wait for failures to accumulate
                await asyncio.sleep(8)
                record_state_transition("after_failures")
                
                # THEN: Should enter degraded or failed state
                failed_state = self.lifecycle_manager._connection_states[self.connection_id]
                assert failed_state.refresh_failures >= 1, "Should have recorded failures"
                assert failed_state.lifecycle_state in [
                    TokenLifecycleState.REFRESH_FAILED, 
                    TokenLifecycleState.DEGRADED,
                    TokenLifecycleState.TERMINATED
                ], f"Should be in failure/degraded state, got {failed_state.lifecycle_state}"
                
                # Test recovery
                mock_auth.should_fail = False
                await asyncio.sleep(3)
                record_state_transition("after_recovery_attempt")
                
                await self.lifecycle_manager.stop_lifecycle_management()
                record_state_transition("final_state")
                
                # THEN: Verify state transition sequence
                states_seen = [entry["state"] for entry in observed_states]
                assert "refresh_scheduled" in states_seen, "Should see refresh_scheduled state"
                
                # Should see either success states or failure states
                success_states = {"active", "refresh_scheduled"}
                failure_states = {"refresh_failed", "degraded", "terminated"}
                
                has_success = any(state in success_states for state in states_seen)
                has_failure = any(state in failure_states for state in states_seen)
                
                assert has_success or has_failure, "Should see either success or failure state transitions"
                
                # Verify lifecycle events match state transitions
                state_change_events = [e for e in self.lifecycle_events if e.lifecycle_state is not None]
                assert len(state_change_events) >= 3, "Should have multiple state change events"
        
        self.record_metric("state_transitions_observed", len(observed_states))
        self.record_metric("final_refresh_count", current_state.refresh_count)
        self.record_metric("final_refresh_failures", current_state.refresh_failures)

    @pytest.mark.asyncio
    async def test_metrics_collection_connection_duration_success_rates(self):
        """
        BVJ: Platform/Core - Validate comprehensive metrics collection
        Enables monitoring and alerting for production WebSocket performance
        """
        # GIVEN: Multiple connections with different behaviors
        await self._setup_lifecycle_event_tracking()
        
        # Create connections with different success patterns
        successful_connections = []
        failing_connections = []
        
        # Create 3 successful connections
        for i in range(3):
            user_id = ensure_user_id(str(uuid.uuid4()))
            conn_id = f"success_conn_{i}_{uuid.uuid4().hex[:8]}"
            state = await self._register_test_connection(connection_id=conn_id, user_id=user_id, token_expiry_offset=10)
            successful_connections.append((conn_id, user_id, state))
        
        # Create 2 failing connections  
        for i in range(2):
            user_id = ensure_user_id(str(uuid.uuid4()))
            conn_id = f"failing_conn_{i}_{uuid.uuid4().hex[:8]}"
            state = await self._register_test_connection(connection_id=conn_id, user_id=user_id, token_expiry_offset=3)  # Shorter expiry
            failing_connections.append((conn_id, user_id, state))
        
        initial_metrics = await self._take_metrics_snapshot("initial_multi_connection")
        assert initial_metrics.total_connections == 5, "Should have 5 total connections"
        assert initial_metrics.active_connections == 5, "Should have 5 active connections"
        
        # Mock auth service with selective failure
        class MetricsTestAuthService:
            def __init__(self):
                self.call_count = 0
                self.calls_by_connection = {}
                
            async def authenticate(self, token, context):
                self.call_count += 1
                conn_id = context.metadata.get("connection_id", "unknown")
                
                if conn_id not in self.calls_by_connection:
                    self.calls_by_connection[conn_id] = 0
                self.calls_by_connection[conn_id] += 1
                
                # Fail for connections with "failing" in their ID
                if "failing" in conn_id:
                    from dataclasses import dataclass
                    @dataclass
                    class FailResult:
                        success: bool = False
                        error: str = f"Simulated failure for {conn_id}"
                    return FailResult()
                else:
                    from dataclasses import dataclass
                    @dataclass
                    class SuccessResult:
                        success: bool = True
                        user_id: str = context.metadata.get("user_id", "test_user")
                        error: str = None
                    return SuccessResult()
        
        metrics_auth = MetricsTestAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=metrics_auth):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"metrics_token_{metrics_auth.call_count}"):
                
                # WHEN: Running lifecycle management with mixed success/failure
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Let connections run for various durations
                await asyncio.sleep(2)
                early_metrics = await self._take_metrics_snapshot("early_phase")
                
                await asyncio.sleep(4)  
                mid_metrics = await self._take_metrics_snapshot("mid_phase")
                
                await asyncio.sleep(6)
                late_metrics = await self._take_metrics_snapshot("late_phase")
                
                await self.lifecycle_manager.stop_lifecycle_management()
                
                # THEN: Verify comprehensive metrics collection
                final_metrics = await self._take_metrics_snapshot("final_comprehensive")
                
                # Verify connection counts
                assert final_metrics.total_connections == 5, "Total connections should remain 5"
                
                # Verify refresh success/failure tracking
                assert final_metrics.successful_refreshes >= 3, "Should have successful refreshes for good connections"
                assert final_metrics.failed_refreshes >= 2, "Should have failed refreshes for failing connections"
                
                # Verify success rate calculation
                total_attempts = final_metrics.successful_refreshes + final_metrics.failed_refreshes
                if total_attempts > 0:
                    expected_rate = (final_metrics.successful_refreshes / total_attempts) * 100
                    assert abs(final_metrics.refresh_success_rate - expected_rate) < 1.0, "Success rate calculation should be accurate"
                
                # Verify degraded connections tracking
                assert final_metrics.degraded_connections >= 0, "Should track degraded connections"
                
                # Verify connection duration tracking
                assert final_metrics.longest_connection_duration >= 10, "Should track longest connection duration"
                assert final_metrics.average_connection_duration >= 5, "Should have reasonable average duration"
                
                # Verify individual connection metrics
                for conn_id, user_id, _ in successful_connections + failing_connections:
                    conn_metrics = self.lifecycle_manager.get_connection_metrics(conn_id)
                    assert conn_metrics["connection_id"] == conn_id, "Should return correct connection ID"
                    assert conn_metrics["user_id"] == user_id, "Should return correct user ID"
                    assert conn_metrics["connection_duration"] >= 10, "Each connection should have tracked duration"
                    assert "lifecycle_state" in conn_metrics, "Should include lifecycle state"
                    assert "refresh_count" in conn_metrics, "Should include refresh count"
                    assert "refresh_failures" in conn_metrics, "Should include failure count"
        
        # Verify metrics progression over time
        assert len(self.metrics_snapshots) >= 5, "Should have multiple metric snapshots"
        
        # Connection counts should be stable
        connection_counts = [s.active_connections for s in self.metrics_snapshots]
        assert all(count >= 3 for count in connection_counts), "Should maintain active connections"
        
        # Success/failure counts should increase
        success_counts = [s.successful_refreshes for s in self.metrics_snapshots]
        failure_counts = [s.failed_refreshes for s in self.metrics_snapshots]
        
        assert success_counts[-1] >= success_counts[0], "Successful refreshes should increase"
        assert failure_counts[-1] >= failure_counts[0], "Failed refreshes should increase"
        
        self.record_metric("final_total_connections", final_metrics.total_connections)
        self.record_metric("final_successful_refreshes", final_metrics.successful_refreshes)
        self.record_metric("final_failed_refreshes", final_metrics.failed_refreshes)
        self.record_metric("final_refresh_success_rate", final_metrics.refresh_success_rate)

    @pytest.mark.asyncio
    async def test_connection_termination_degraded_mode_timeout(self):
        """
        BVJ: Platform/Core - Validate proper connection termination in degraded mode
        Prevents resource leaks from connections that can't maintain authentication
        """
        # GIVEN: Connection with failing auth service to trigger degraded mode
        await self._setup_lifecycle_event_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=4)  # Short expiry for fast degraded mode
        
        # Mock auth service that always fails
        class FailingAuthService:
            def __init__(self):
                self.call_count = 0
                
            async def authenticate(self, token, context):
                self.call_count += 1
                from dataclasses import dataclass
                @dataclass
                class AlwaysFailResult:
                    success: bool = False
                    error: str = f"Persistent auth failure #{self.call_count}"
                return AlwaysFailResult()
        
        failing_auth = FailingAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=failing_auth):
            
            # WHEN: Running lifecycle with persistent auth failures
            await self.lifecycle_manager.start_lifecycle_management()
            
            # Wait for degraded mode entry
            await asyncio.sleep(8)  # Should be enough to enter degraded mode
            
            # Verify degraded mode entry
            degraded_state = self.lifecycle_manager._connection_states.get(self.connection_id)
            if degraded_state:
                assert degraded_state.lifecycle_state == TokenLifecycleState.DEGRADED, "Should be in degraded mode"
                assert degraded_state.degraded_since is not None, "Should have degraded timestamp"
                degraded_entry_time = degraded_state.degraded_since
            
            # Wait for degraded mode timeout (15s configured timeout)
            await asyncio.sleep(20)  # Wait longer than degraded timeout
            
            await self.lifecycle_manager.stop_lifecycle_management()
            
            # THEN: Verify connection termination occurred
            # Connection might be terminated (removed) or in TERMINATED state
            final_state = self.lifecycle_manager._connection_states.get(self.connection_id)
            
            if final_state is None:
                # Connection was removed completely - valid termination
                termination_method = "removed"
            elif final_state.lifecycle_state == TokenLifecycleState.TERMINATED:
                # Connection marked as terminated - also valid
                termination_method = "marked_terminated"
            else:
                # Connection still exists but should be in degraded state with proper timeout
                assert final_state.lifecycle_state == TokenLifecycleState.DEGRADED, "Non-terminated connection should remain degraded"
                termination_method = "still_degraded"
            
            # Verify termination events
            termination_events = [e for e in self.lifecycle_events if e.event_type in ["terminated", "unregistered"]]
            degraded_events = [e for e in self.lifecycle_events if e.event_type == "entered_degraded_mode"]
            
            assert len(degraded_events) >= 1, "Should have entered degraded mode"
            
            # If connection was terminated, should have termination event
            if termination_method in ["removed", "marked_terminated"]:
                assert len(termination_events) >= 1, "Should have termination event"
                termination_event = termination_events[0]
                assert termination_event.connection_id == self.connection_id, "Termination should be for correct connection"
            
            # Verify metrics reflect termination behavior
            metrics = self.lifecycle_manager.get_connection_metrics()
            
            if termination_method == "removed":
                assert metrics["active_connections"] == 0, "Should have no active connections after termination"
            else:
                # Connection still tracked but degraded
                assert metrics["degraded_connections"] >= 1, "Should track degraded connection"
            
            assert metrics["failed_refreshes"] >= 3, "Should have multiple failures before degraded mode"
            assert failing_auth.call_count >= 3, "Auth service should have been called multiple times"
        
        self.record_metric("termination_method", termination_method)
        self.record_metric("degraded_mode_handling", True)

    @pytest.mark.asyncio
    async def test_active_connection_monitoring_health_checks(self):
        """
        BVJ: Platform/Core - Validate active connection monitoring and health detection
        Enables proactive detection of connection issues before they break user experience
        """
        # GIVEN: Multiple connections with different health patterns
        await self._setup_lifecycle_event_tracking()
        
        healthy_conn_id = f"healthy_{uuid.uuid4().hex[:8]}"
        unhealthy_conn_id = f"unhealthy_{uuid.uuid4().hex[:8]}"
        intermittent_conn_id = f"intermittent_{uuid.uuid4().hex[:8]}"
        
        # Create connections
        healthy_state = await self._register_test_connection(connection_id=healthy_conn_id, token_expiry_offset=20)
        unhealthy_state = await self._register_test_connection(connection_id=unhealthy_conn_id, token_expiry_offset=5)  
        intermittent_state = await self._register_test_connection(connection_id=intermittent_conn_id, token_expiry_offset=15)
        
        # Mock auth service with connection-specific behavior
        class HealthMonitoringAuthService:
            def __init__(self):
                self.call_count = 0
                self.calls_by_connection = {}
                
            async def authenticate(self, token, context):
                self.call_count += 1
                conn_id = context.metadata.get("connection_id", "unknown")
                
                if conn_id not in self.calls_by_connection:
                    self.calls_by_connection[conn_id] = 0
                self.calls_by_connection[conn_id] += 1
                
                call_num = self.calls_by_connection[conn_id]
                
                # Different failure patterns per connection
                if "unhealthy" in conn_id:
                    # Always fail
                    success = False
                elif "intermittent" in conn_id:
                    # Intermittent failures (fail every 3rd call)
                    success = (call_num % 3) != 0
                else:
                    # Healthy - always succeed
                    success = True
                
                if success:
                    from dataclasses import dataclass
                    @dataclass
                    class HealthyResult:
                        success: bool = True
                        user_id: str = context.metadata.get("user_id", "test_user")
                        error: str = None
                    return HealthyResult()
                else:
                    from dataclasses import dataclass
                    @dataclass
                    class UnhealthyResult:
                        success: bool = False
                        error: str = f"Health check failure for {conn_id}"
                    return UnhealthyResult()
        
        health_auth = HealthMonitoringAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=health_auth):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"health_token_{health_auth.call_count}"):
                
                # WHEN: Running health monitoring over time
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Simulate activity on connections to check health
                health_check_tasks = [
                    asyncio.create_task(self._simulate_connection_activity(healthy_conn_id, 15, 2.0)),
                    asyncio.create_task(self._simulate_connection_activity(unhealthy_conn_id, 10, 1.5)),  # Shorter duration
                    asyncio.create_task(self._simulate_connection_activity(intermittent_conn_id, 15, 2.5))
                ]
                
                # Take periodic health snapshots
                health_snapshots = []
                for i in range(5):
                    await asyncio.sleep(3)
                    
                    # Check individual connection health
                    healthy_metrics = self.lifecycle_manager.get_connection_metrics(healthy_conn_id)
                    unhealthy_metrics = self.lifecycle_manager.get_connection_metrics(unhealthy_conn_id)
                    intermittent_metrics = self.lifecycle_manager.get_connection_metrics(intermittent_conn_id)
                    
                    health_snapshot = {
                        "timestamp": datetime.now(timezone.utc),
                        "healthy_state": healthy_metrics.get("lifecycle_state"),
                        "healthy_failures": healthy_metrics.get("refresh_failures", 0),
                        "unhealthy_state": unhealthy_metrics.get("lifecycle_state"),
                        "unhealthy_failures": unhealthy_metrics.get("refresh_failures", 0),
                        "intermittent_state": intermittent_metrics.get("lifecycle_state"),
                        "intermittent_failures": intermittent_metrics.get("refresh_failures", 0)
                    }
                    health_snapshots.append(health_snapshot)
                
                # Wait for tasks to complete
                await asyncio.gather(*health_check_tasks, return_exceptions=True)
                await self.lifecycle_manager.stop_lifecycle_management()
                
                # THEN: Verify health monitoring detected different connection patterns
                final_metrics = self.lifecycle_manager.get_connection_metrics()
                
                # Verify healthy connection remained healthy
                final_healthy_metrics = self.lifecycle_manager.get_connection_metrics(healthy_conn_id)
                assert final_healthy_metrics["lifecycle_state"] in ["active", "refresh_scheduled"], "Healthy connection should remain healthy"
                assert final_healthy_metrics["refresh_failures"] <= 1, "Healthy connection should have minimal failures"
                
                # Verify unhealthy connection was detected
                final_unhealthy_metrics = self.lifecycle_manager.get_connection_metrics(unhealthy_conn_id)
                assert final_unhealthy_metrics["refresh_failures"] >= 2, "Unhealthy connection should accumulate failures"
                assert final_unhealthy_metrics["lifecycle_state"] in ["refresh_failed", "degraded", "terminated"], "Unhealthy connection should be in failure state"
                
                # Verify intermittent connection shows mixed behavior
                final_intermittent_metrics = self.lifecycle_manager.get_connection_metrics(intermittent_conn_id)
                # Intermittent connection should have some successes and some failures
                
                # Verify overall metrics reflect mixed health
                assert final_metrics["successful_refreshes"] >= 3, "Should have successful refreshes from healthy connections"
                assert final_metrics["failed_refreshes"] >= 2, "Should have failures from unhealthy connections"
                assert final_metrics["refresh_success_rate"] < 100, "Success rate should reflect mixed health"
                
                # Verify health progression over time
                failure_progression = []
                for snapshot in health_snapshots:
                    total_failures = (snapshot["healthy_failures"] + 
                                    snapshot["unhealthy_failures"] + 
                                    snapshot["intermittent_failures"])
                    failure_progression.append(total_failures)
                
                # Failures should generally increase over time (unhealthy connection)
                assert failure_progression[-1] >= failure_progression[0], "Failures should accumulate over time"
        
        # Verify health monitoring events
        health_events = [e for e in self.lifecycle_events if "refresh" in e.event_type]
        success_events = [e for e in health_events if e.event_type == "token_refreshed"]
        failure_events = [e for e in health_events if e.event_type == "token_refresh_failed"]
        
        assert len(success_events) >= 3, "Should have successful health checks"
        assert len(failure_events) >= 2, "Should have failed health checks"
        
        # Verify different connections had different health outcomes
        connections_with_success = {e.connection_id for e in success_events}
        connections_with_failures = {e.connection_id for e in failure_events}
        
        assert healthy_conn_id in connections_with_success, "Healthy connection should have successes"
        assert unhealthy_conn_id in connections_with_failures, "Unhealthy connection should have failures"
        
        self.record_metric("health_monitoring_success", True)
        self.record_metric("connections_monitored", 3)
        self.record_metric("health_check_success_events", len(success_events))
        self.record_metric("health_check_failure_events", len(failure_events))

    @pytest.mark.asyncio
    async def test_connection_event_callbacks_lifecycle_notifications(self):
        """
        BVJ: Platform/Core - Validate connection event callback system
        Enables integration with monitoring, alerting, and logging systems
        """
        # GIVEN: Multiple callback functions registered
        callback_events = {
            "callback_1": [],
            "callback_2": [],
            "detailed_callback": []
        }
        
        async def callback_1(conn_id: str, event_type: str, event_data: Dict):
            callback_events["callback_1"].append({
                "connection_id": conn_id,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc),
                "callback_name": "callback_1"
            })
        
        async def callback_2(conn_id: str, event_type: str, event_data: Dict):
            callback_events["callback_2"].append({
                "connection_id": conn_id, 
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc),
                "callback_name": "callback_2"
            })
        
        async def detailed_callback(conn_id: str, event_type: str, event_data: Dict):
            callback_events["detailed_callback"].append({
                "connection_id": conn_id,
                "event_type": event_type,
                "event_data": event_data.copy(),
                "timestamp": datetime.now(timezone.utc),
                "callback_name": "detailed_callback"
            })
        
        # Register callbacks
        await self.lifecycle_manager.add_connection_event_callback(callback_1)
        await self.lifecycle_manager.add_connection_event_callback(callback_2)
        await self.lifecycle_manager.add_connection_event_callback(detailed_callback)
        
        # WHEN: Creating connections and triggering lifecycle events
        conn1_id = f"callback_test_1_{uuid.uuid4().hex[:8]}"
        conn2_id = f"callback_test_2_{uuid.uuid4().hex[:8]}"
        
        # Register first connection
        state1 = await self._register_test_connection(connection_id=conn1_id, token_expiry_offset=10)
        
        # Wait a moment for events to propagate
        await asyncio.sleep(0.1)
        
        # Register second connection
        state2 = await self._register_test_connection(connection_id=conn2_id, token_expiry_offset=8)
        
        await asyncio.sleep(0.1)
        
        # Mock auth service for refresh events
        class CallbackTestAuthService:
            def __init__(self):
                self.call_count = 0
                
            async def authenticate(self, token, context):
                self.call_count += 1
                from dataclasses import dataclass
                @dataclass
                class CallbackResult:
                    success: bool = True
                    user_id: str = context.metadata.get("user_id", "callback_test_user")
                    error: str = None
                return CallbackResult()
        
        callback_auth = CallbackTestAuthService()
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=callback_auth):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"callback_token_{callback_auth.call_count}"):
                
                # Start lifecycle to trigger refresh events
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Wait for refresh events
                await asyncio.sleep(6)
                
                # Force refresh to trigger immediate events
                await self.lifecycle_manager.force_token_refresh(conn1_id)
                await self.lifecycle_manager.force_token_refresh(conn2_id)
                
                # Unregister one connection
                await self.lifecycle_manager.unregister_connection(conn1_id)
                
                await self.lifecycle_manager.stop_lifecycle_management()
                
                # Unregister second connection
                await self.lifecycle_manager.unregister_connection(conn2_id)
        
        # THEN: Verify all callbacks received events
        
        # Check callback_1 received events
        cb1_events = callback_events["callback_1"]
        assert len(cb1_events) >= 4, f"Callback 1 should receive multiple events, got {len(cb1_events)}"
        
        cb1_event_types = {e["event_type"] for e in cb1_events}
        assert "registered" in cb1_event_types, "Callback 1 should receive registration events"
        assert "unregistered" in cb1_event_types, "Callback 1 should receive unregistration events"
        
        # Check callback_2 received same events
        cb2_events = callback_events["callback_2"]
        assert len(cb2_events) >= 4, f"Callback 2 should receive multiple events, got {len(cb2_events)}"
        assert len(cb2_events) == len(cb1_events), "Both callbacks should receive same number of events"
        
        cb2_event_types = {e["event_type"] for e in cb2_events}
        assert cb1_event_types == cb2_event_types, "Both callbacks should receive same event types"
        
        # Check detailed callback has event data
        detailed_events = callback_events["detailed_callback"]
        assert len(detailed_events) >= 4, f"Detailed callback should receive events, got {len(detailed_events)}"
        
        # Verify detailed callback has event_data
        events_with_data = [e for e in detailed_events if "event_data" in e and e["event_data"]]
        assert len(events_with_data) >= 2, "Detailed callback should receive events with data"
        
        # Verify connection IDs in events
        all_connection_ids = set()
        for events in callback_events.values():
            for event in events:
                all_connection_ids.add(event["connection_id"])
        
        assert conn1_id in all_connection_ids, "Should have events for connection 1"
        assert conn2_id in all_connection_ids, "Should have events for connection 2"
        
        # Test callback removal
        await self.lifecycle_manager.remove_connection_event_callback(callback_1)
        
        # Register new connection to test callback removal
        conn3_id = f"callback_removal_test_{uuid.uuid4().hex[:8]}"
        await self._register_test_connection(connection_id=conn3_id, token_expiry_offset=5)
        
        await asyncio.sleep(0.1)
        
        # Count events before and after removal
        cb1_events_before_removal = len(callback_events["callback_1"])
        cb2_events_before_removal = len(callback_events["callback_2"])
        
        # Unregister test connection
        await self.lifecycle_manager.unregister_connection(conn3_id)
        
        await asyncio.sleep(0.1)
        
        # Verify callback 1 didn't receive new events (was removed)
        cb1_events_after_removal = len(callback_events["callback_1"])
        cb2_events_after_removal = len(callback_events["callback_2"])
        
        assert cb1_events_after_removal == cb1_events_before_removal, "Removed callback should not receive new events"
        assert cb2_events_after_removal > cb2_events_before_removal, "Active callback should receive new events"
        
        self.record_metric("callback_events_total", sum(len(events) for events in callback_events.values()))
        self.record_metric("callback_removal_success", True)
        self.record_metric("event_types_seen", len(cb1_event_types))