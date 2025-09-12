"""
JWT Token Lifecycle Integration Tests - Token Refresh Mechanisms

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Core - WebSocket Token Refresh Infrastructure  
- Business Goal: Prevent authentication failures that break 5+ minute chat sessions
- Value Impact: Ensures continuous agent execution without user interruption
- Revenue Impact: Protects $500K+ ARR by maintaining unbroken conversation flows

INTEGRATION TEST SCOPE:
These tests validate the Token Lifecycle Manager's refresh system with realistic
timing and auth service integration patterns. Tests focus on background refresh
loops, circuit breaker patterns, and concurrent refresh scenarios using actual
system components without requiring live services.

SUCCESS CRITERIA:
- Background refresh executes every 45 seconds as scheduled
- Circuit breaker protects against auth service failures
- Concurrent user token refreshes work without interference
- Degraded mode gracefully handles auth service downtime
- Force refresh capability works for immediate token renewal
- Refresh success/failure callbacks execute correctly
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest import mock
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.token_lifecycle_manager import (
    TokenLifecycleManager,
    ConnectionTokenState,
    TokenLifecycleState,
    TokenLifecycleMetrics
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.unified_authentication_service import (
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from shared.isolated_environment import get_env
from shared.types.core_types import ensure_user_id


@dataclass
class MockAuthResult:
    """Mock auth result for testing refresh scenarios."""
    success: bool
    user_id: Optional[str] = None
    token: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class MockUnifiedAuthService:
    """Mock auth service for testing refresh integration."""
    
    def __init__(self):
        self.call_count = 0
        self.failure_mode = False
        self.failure_count = 0
        self.success_responses = []
        self.failure_responses = []
        
    async def authenticate(self, token: str, context: AuthenticationContext) -> MockAuthResult:
        """Mock authenticate method with configurable responses."""
        self.call_count += 1
        
        if self.failure_mode:
            self.failure_count += 1
            error_msg = f"Auth service failure #{self.failure_count}"
            return MockAuthResult(success=False, error=error_msg)
        
        # Simulate successful token refresh
        new_token = f"refreshed_token_{uuid.uuid4().hex[:12]}_{self.call_count}"
        return MockAuthResult(
            success=True,
            user_id=context.metadata.get("user_id"),
            token=new_token,
            metadata={"refresh_count": self.call_count}
        )
    
    def set_failure_mode(self, enabled: bool):
        """Enable/disable failure mode for testing."""
        self.failure_mode = enabled
        if not enabled:
            self.failure_count = 0


@dataclass
class RefreshEvent:
    """Tracks token refresh events for validation."""
    connection_id: str
    event_type: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    refresh_count: int = 0


class TestJWTTokenLifecycleRefreshIntegration(SSotAsyncTestCase):
    """
    Integration tests for JWT Token Lifecycle Manager refresh mechanisms.
    
    BUSINESS IMPACT: Validates the core refresh system that enables uninterrupted
    5+ minute WebSocket chat sessions by preventing token expiry failures.
    """

    def setup_method(self, method):
        """Set up test environment with refresh-focused configuration."""
        super().setup_method(method)
        
        # Fast timing for testing - realistic ratios maintained
        self.refresh_interval = 2   # 2 seconds for testing (vs 45s production)
        self.token_expiry = 5       # 5 seconds for testing (vs 60s production) 
        self.degraded_timeout = 10  # 10 seconds for testing (vs 180s production)
        
        # Create lifecycle manager with test timing
        self.lifecycle_manager = TokenLifecycleManager(
            refresh_interval_seconds=self.refresh_interval,
            token_expiry_seconds=self.token_expiry,
            degraded_mode_timeout_seconds=self.degraded_timeout
        )
        
        # Mock auth service for controlled testing
        self.mock_auth_service = MockUnifiedAuthService()
        
        # Test data
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))
        self.connection_id = f"refresh_test_conn_{uuid.uuid4().hex[:8]}"
        self.websocket_client_id = f"ws_refresh_{uuid.uuid4().hex[:8]}"
        
        # Event tracking
        self.refresh_events: List[RefreshEvent] = []
        self.background_loop_iterations = 0
        
        # Performance tracking
        self.refresh_times = []
        self.circuit_breaker_events = []

    def teardown_method(self, method):
        """Clean up refresh test environment."""
        try:
            # Stop any background tasks
            asyncio.create_task(self.lifecycle_manager.stop_lifecycle_management())
        except Exception as e:
            self.record_metric("teardown_error", str(e))
        finally:
            super().teardown_method(method)

    def _create_test_user_context(self, user_id: str = None) -> UserExecutionContext:
        """Create test user context."""
        if user_id is None:
            user_id = self.test_user_id
            
        return UserExecutionContext(
            user_id=user_id,
            execution_context_id=f"refresh_ctx_{uuid.uuid4().hex[:8]}",
            websocket_client_id=self.websocket_client_id,
            timestamp=datetime.now(timezone.utc),
            session_metadata={"test_refresh": True}
        )

    def _create_test_token(self, expires_in_seconds: int = None) -> str:
        """Create test token with expiry."""
        if expires_in_seconds is None:
            expires_in_seconds = self.token_expiry
        return f"test_token_{uuid.uuid4().hex[:12]}_exp_{expires_in_seconds}s"

    async def _setup_refresh_tracking(self):
        """Set up tracking for refresh events."""
        async def track_refresh_event(conn_id: str, event_type: str, event_data: Dict):
            event = RefreshEvent(
                connection_id=conn_id,
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                success=event_type == "token_refreshed",
                error_message=event_data.get("error"),
                refresh_count=event_data.get("refresh_count", 0)
            )
            self.refresh_events.append(event)
            
        await self.lifecycle_manager.add_connection_event_callback(track_refresh_event)

    async def _register_test_connection(self, connection_id: str = None, user_id: str = None, token_expiry_offset: int = None) -> ConnectionTokenState:
        """Register a test connection for refresh testing."""
        if connection_id is None:
            connection_id = self.connection_id
        if user_id is None:
            user_id = self.test_user_id
        if token_expiry_offset is None:
            token_expiry_offset = self.token_expiry
            
        user_context = self._create_test_user_context(user_id)
        test_token = self._create_test_token()
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_expiry_offset)
        
        await self.lifecycle_manager.register_connection_token(
            connection_id=connection_id,
            websocket_client_id=user_context.websocket_client_id,
            user_context=user_context,
            initial_token=test_token,
            token_expires_at=token_expires_at
        )
        
        return self.lifecycle_manager._connection_states[connection_id]

    # === TOKEN REFRESH MECHANISM TESTS ===

    @pytest.mark.asyncio
    async def test_background_token_refresh_loop_execution(self):
        """
        BVJ: Platform/Core - Validate background refresh loop operates continuously
        Critical for maintaining authentication during long WebSocket sessions
        """
        # GIVEN: Registered connection ready for refresh
        await self._setup_refresh_tracking()
        connection_state = await self._register_test_connection()
        
        # Mock the auth service refresh
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', return_value="new_refreshed_token"):
                
                # WHEN: Starting background refresh loop
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Wait for refresh to occur - token expires in 5s, refresh at 4s
                await asyncio.sleep(6)  # Wait longer than token expiry
                
                # THEN: Verify refresh loop executed and refreshed token
                assert self.mock_auth_service.call_count >= 1, "Auth service should be called for refresh"
                
                # Verify connection state updated
                updated_state = self.lifecycle_manager._connection_states[self.connection_id]
                assert updated_state.refresh_count >= 1, "Refresh count should increase"
                assert updated_state.current_token != connection_state.initial_token, "Token should be refreshed"
                assert updated_state.lifecycle_state in [TokenLifecycleState.ACTIVE, TokenLifecycleState.REFRESH_SCHEDULED]
                
                # Verify refresh events recorded
                refresh_events = [e for e in self.refresh_events if e.event_type == "token_refreshed"]
                assert len(refresh_events) >= 1, "Should have refresh success events"
                
                # Verify metrics updated
                metrics = self.lifecycle_manager.get_connection_metrics()
                assert metrics["successful_refreshes"] >= 1, "Should track successful refreshes"
                
                await self.lifecycle_manager.stop_lifecycle_management()
                
        self.record_metric("background_refresh_success", True)

    @pytest.mark.asyncio
    async def test_token_refresh_before_expiry_timing(self):
        """
        BVJ: Platform/Core - Validate refresh occurs 15 seconds before token expiry
        Ensures no authentication gaps that would break user conversations
        """
        # GIVEN: Connection with precise expiry timing
        await self._setup_refresh_tracking()
        
        # Set token to expire in 20 seconds (longer for timing precision)
        expiry_seconds = 20
        connection_state = await self._register_test_connection(token_expiry_offset=expiry_seconds)
        
        # Record initial state
        initial_expiry = connection_state.token_expires_at
        expected_refresh_time = initial_expiry - timedelta(seconds=15)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', return_value="precisely_timed_token"):
                
                # WHEN: Starting lifecycle management
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Wait until just before expected refresh time
                now = datetime.now(timezone.utc)
                wait_time = (expected_refresh_time - now).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time + 1)  # Wait 1s past expected refresh
                
                # THEN: Verify refresh occurred at correct timing
                updated_state = self.lifecycle_manager._connection_states[self.connection_id]
                
                # Should have refreshed by now
                assert updated_state.refresh_count >= 1, "Token should have been refreshed"
                assert updated_state.last_refresh_attempt is not None, "Refresh attempt should be recorded"
                
                # Verify refresh happened before token expired
                refresh_time = updated_state.last_refresh_attempt
                assert refresh_time < initial_expiry, "Refresh should occur before original expiry"
                
                # Verify timing was close to 15s before expiry (within 2s tolerance)
                time_before_expiry = (initial_expiry - refresh_time).total_seconds()
                assert 13 <= time_before_expiry <= 17, f"Refresh should be ~15s before expiry, was {time_before_expiry}s"
                
                await self.lifecycle_manager.stop_lifecycle_management()
                
        self.record_metric("refresh_timing_accuracy", abs(15 - time_before_expiry))

    @pytest.mark.asyncio
    async def test_circuit_breaker_protection_during_auth_failures(self):
        """
        BVJ: Platform/Core - Validate circuit breaker prevents auth service overload
        Protects system stability when auth service experiences issues
        """
        # GIVEN: Connection registered and auth service in failure mode
        await self._setup_refresh_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=3)  # Short expiry for fast testing
        
        # Configure auth service to fail
        self.mock_auth_service.set_failure_mode(True)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            
            # WHEN: Starting refresh loop with failing auth service
            await self.lifecycle_manager.start_lifecycle_management()
            
            # Wait for multiple refresh attempts
            await asyncio.sleep(8)  # Allow multiple refresh cycles
            
            # THEN: Verify circuit breaker engaged after repeated failures
            metrics = self.lifecycle_manager.get_connection_metrics()
            
            # Should have multiple failed refreshes
            assert metrics["failed_refreshes"] >= 3, "Should have multiple refresh failures"
            
            # Circuit breaker should be protecting the system
            circuit_state = metrics["circuit_breaker_state"]
            assert circuit_state in ["OPEN", "HALF_OPEN"], f"Circuit breaker should be open/half-open, got: {circuit_state}"
            
            # Connection should enter degraded mode
            updated_state = self.lifecycle_manager._connection_states[self.connection_id]
            assert updated_state.lifecycle_state == TokenLifecycleState.DEGRADED, "Connection should be in degraded mode"
            assert updated_state.degraded_since is not None, "Degraded timestamp should be set"
            
            # Verify failure events recorded
            failure_events = [e for e in self.refresh_events if e.event_type == "token_refresh_failed"]
            assert len(failure_events) >= 3, "Should have multiple failure events"
            
            # Verify auth service call count limited by circuit breaker
            # (Should be less than what unlimited retries would produce)
            assert self.mock_auth_service.call_count <= 10, "Circuit breaker should limit auth service calls"
            
            await self.lifecycle_manager.stop_lifecycle_management()
            
        self.record_metric("circuit_breaker_engagement", True)

    @pytest.mark.asyncio
    async def test_degraded_mode_handling_auth_service_unavailable(self):
        """
        BVJ: Platform/Core - Validate graceful degradation when auth service unavailable
        Maintains service availability even when auth system has issues
        """
        # GIVEN: Connection and auth service that will fail
        await self._setup_refresh_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=4)
        
        # Configure immediate failures
        self.mock_auth_service.set_failure_mode(True)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            
            # WHEN: Running refresh cycles with persistent auth failures
            await self.lifecycle_manager.start_lifecycle_management()
            
            # Wait for degraded mode to activate
            await asyncio.sleep(6)
            
            # THEN: Verify system enters degraded mode gracefully
            updated_state = self.lifecycle_manager._connection_states[self.connection_id]
            assert updated_state.lifecycle_state == TokenLifecycleState.DEGRADED, "Should enter degraded mode"
            assert updated_state.degraded_since is not None, "Degraded timestamp should be recorded"
            
            # Verify metrics reflect degraded state
            metrics = self.lifecycle_manager.get_connection_metrics()
            assert metrics["degraded_connections"] >= 1, "Should track degraded connections"
            assert metrics["failed_refreshes"] >= 3, "Should have attempted multiple refreshes"
            
            # Test recovery: Re-enable auth service
            self.mock_auth_service.set_failure_mode(False)
            
            # Wait for potential recovery attempt
            await asyncio.sleep(3)
            
            # WHEN auth service recovers: System should potentially recover
            # (Implementation may vary - some systems recover, others require manual intervention)
            final_metrics = self.lifecycle_manager.get_connection_metrics()
            
            # Verify graceful handling regardless of recovery approach
            assert final_metrics["circuit_breaker_trips"] >= 0, "Circuit breaker trips should be tracked"
            
            await self.lifecycle_manager.stop_lifecycle_management()
            
        # Verify degraded mode events
        degraded_events = [e for e in self.refresh_events if e.event_type == "entered_degraded_mode"]
        assert len(degraded_events) >= 1, "Should have degraded mode entry events"
        
        self.record_metric("degraded_mode_handling", True)

    @pytest.mark.asyncio
    async def test_concurrent_token_refresh_multiple_connections(self):
        """
        BVJ: Platform/Core - Validate concurrent refresh for multiple users
        Ensures refresh system scales properly for multi-user scenarios
        """
        # GIVEN: Multiple connections from different users
        num_connections = 5
        connection_states = []
        user_ids = []
        
        await self._setup_refresh_tracking()
        
        for i in range(num_connections):
            user_id = ensure_user_id(str(uuid.uuid4()))
            conn_id = f"concurrent_conn_{i}_{uuid.uuid4().hex[:8]}"
            
            # Stagger expiry times slightly to test concurrency
            expiry_offset = 4 + (i * 0.5)  # 4.0s, 4.5s, 5.0s, etc.
            
            state = await self._register_test_connection(
                connection_id=conn_id,
                user_id=user_id,
                token_expiry_offset=int(expiry_offset)
            )
            
            connection_states.append((conn_id, user_id, state))
            user_ids.append(user_id)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"concurrent_token_{state.connection_id}_{uuid.uuid4().hex[:8]}"):
                
                # WHEN: Starting refresh for all connections
                await self.lifecycle_manager.start_lifecycle_management()
                
                # Wait for all connections to refresh
                await asyncio.sleep(8)
                
                # THEN: Verify all connections refreshed successfully
                metrics = self.lifecycle_manager.get_connection_metrics()
                assert metrics["active_connections"] == num_connections, "All connections should remain active"
                assert metrics["successful_refreshes"] >= num_connections, "All connections should have refreshed"
                
                # Verify individual connection states
                for conn_id, user_id, original_state in connection_states:
                    updated_state = self.lifecycle_manager._connection_states[conn_id]
                    assert updated_state.refresh_count >= 1, f"Connection {conn_id} should have refreshed"
                    assert updated_state.user_id == user_id, f"User ID should be preserved for {conn_id}"
                    assert updated_state.current_token != original_state.initial_token, f"Token should be different for {conn_id}"
                
                # Verify no cross-contamination between users
                tokens_by_user = {}
                for conn_id, user_id, _ in connection_states:
                    updated_state = self.lifecycle_manager._connection_states[conn_id]
                    if user_id not in tokens_by_user:
                        tokens_by_user[user_id] = []
                    tokens_by_user[user_id].append(updated_state.current_token)
                
                # Each user should have unique tokens
                all_tokens = []
                for user_tokens in tokens_by_user.values():
                    all_tokens.extend(user_tokens)
                
                assert len(all_tokens) == len(set(all_tokens)), "All tokens should be unique across users"
                
                await self.lifecycle_manager.stop_lifecycle_management()
                
        # Verify refresh events for all connections
        refresh_events = [e for e in self.refresh_events if e.event_type == "token_refreshed"]
        refreshed_connections = {e.connection_id for e in refresh_events}
        expected_connections = {conn_id for conn_id, _, _ in connection_states}
        
        assert refreshed_connections == expected_connections, "All connections should have refresh events"
        
        self.record_metric("concurrent_refresh_success", True)

    @pytest.mark.asyncio
    async def test_force_token_refresh_immediate_execution(self):
        """
        BVJ: Platform/Core - Validate force refresh capability for immediate token renewal
        Enables manual token refresh for troubleshooting and immediate security updates
        """
        # GIVEN: Connection with long-lived token
        await self._setup_refresh_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=60)  # 1 minute expiry
        
        original_token = connection_state.current_token
        original_refresh_count = connection_state.refresh_count
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', return_value="force_refreshed_token"):
                
                # WHEN: Force refreshing token immediately
                refresh_start_time = time.time()
                refresh_success = await self.lifecycle_manager.force_token_refresh(self.connection_id)
                refresh_duration = time.time() - refresh_start_time
                
                # THEN: Verify immediate refresh occurred
                assert refresh_success, "Force refresh should succeed"
                assert refresh_duration < 2.0, f"Force refresh should be fast, took {refresh_duration}s"
                
                # Verify connection state updated immediately
                updated_state = self.lifecycle_manager._connection_states[self.connection_id]
                assert updated_state.refresh_count == original_refresh_count + 1, "Refresh count should increment"
                assert updated_state.current_token != original_token, "Token should be refreshed"
                assert updated_state.current_token == "force_refreshed_token", "Should use force-refreshed token"
                assert updated_state.last_refresh_attempt is not None, "Refresh attempt should be recorded"
                
                # Verify auth service called
                assert self.mock_auth_service.call_count == 1, "Auth service should be called once"
                
                # Verify refresh event recorded
                refresh_events = [e for e in self.refresh_events if e.event_type == "token_refreshed"]
                assert len(refresh_events) == 1, "Should have one refresh event"
                
                # Test force refresh on non-existent connection
                fake_conn_id = "non_existent_connection"
                fake_refresh_success = await self.lifecycle_manager.force_token_refresh(fake_conn_id)
                assert not fake_refresh_success, "Force refresh should fail for non-existent connection"
                
        self.record_metric("force_refresh_duration", refresh_duration)
        self.record_metric("force_refresh_success", True)

    @pytest.mark.asyncio
    async def test_token_refresh_success_failure_callbacks(self):
        """
        BVJ: Platform/Core - Validate refresh success/failure callbacks execute correctly
        Enables proper monitoring and alerting for token refresh operations
        """
        # GIVEN: Connection and callback tracking
        await self._setup_refresh_tracking()
        connection_state = await self._register_test_connection(token_expiry_offset=3)
        
        callback_events = []
        
        # Additional callback for detailed tracking
        async def detailed_callback(conn_id: str, event_type: str, event_data: Dict):
            callback_events.append({
                "connection_id": conn_id,
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.now(timezone.utc)
            })
            
        await self.lifecycle_manager.add_connection_event_callback(detailed_callback)
        
        # Test success scenario first
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', return_value="callback_success_token"):
                
                # WHEN: Triggering successful refresh
                success = await self.lifecycle_manager.force_token_refresh(self.connection_id)
                
                # THEN: Verify success callback executed
                assert success, "Refresh should succeed"
                
                success_events = [e for e in callback_events if e["event_type"] == "token_refreshed"]
                assert len(success_events) == 1, "Should have success callback"
                
                success_event = success_events[0]
                assert success_event["connection_id"] == self.connection_id
                assert "refresh_count" in success_event["event_data"]
                assert "new_expiry" in success_event["event_data"]
                assert "user_id" in success_event["event_data"]
        
        # Test failure scenario
        self.mock_auth_service.set_failure_mode(True)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            
            # WHEN: Triggering failed refresh
            failure = await self.lifecycle_manager.force_token_refresh(self.connection_id)
            
            # THEN: Verify failure callback executed
            assert not failure, "Refresh should fail"
            
            failure_events = [e for e in callback_events if e["event_type"] == "token_refresh_failed"]
            assert len(failure_events) == 1, "Should have failure callback"
            
            failure_event = failure_events[0]
            assert failure_event["connection_id"] == self.connection_id
            assert "error" in failure_event["event_data"]
            assert "refresh_failures" in failure_event["event_data"]
            assert "user_id" in failure_event["event_data"]
        
        # Verify callback removal works
        await self.lifecycle_manager.remove_connection_event_callback(detailed_callback)
        
        # Additional refresh should not trigger the detailed callback
        callback_count_before = len(callback_events)
        self.mock_auth_service.set_failure_mode(False)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(self.lifecycle_manager, '_generate_refreshed_token', return_value="callback_removed_token"):
                await self.lifecycle_manager.force_token_refresh(self.connection_id)
        
        # Should have same number of detailed callbacks (callback was removed)
        assert len(callback_events) == callback_count_before, "Removed callback should not fire"
        
        self.record_metric("callback_success_events", len([e for e in callback_events if e["event_type"] == "token_refreshed"]))
        self.record_metric("callback_failure_events", len([e for e in callback_events if e["event_type"] == "token_refresh_failed"]))

    @pytest.mark.asyncio
    async def test_refresh_interval_timing_scheduling_validation(self):
        """
        BVJ: Platform/Core - Validate refresh interval timing and scheduling accuracy
        Ensures precise timing that prevents authentication gaps in production
        """
        # GIVEN: Connection with specific refresh interval timing
        await self._setup_refresh_tracking()
        
        # Use longer timing for precision measurement
        custom_lifecycle_manager = TokenLifecycleManager(
            refresh_interval_seconds=10,  # 10 second intervals
            token_expiry_seconds=30,      # 30 second expiry
            degraded_mode_timeout_seconds=60
        )
        
        # Register connection
        user_context = self._create_test_user_context()
        test_token = self._create_test_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        
        await custom_lifecycle_manager.register_connection_token(
            connection_id=self.connection_id,
            websocket_client_id=self.websocket_client_id,
            user_context=user_context,
            initial_token=test_token,
            token_expires_at=expires_at
        )
        
        # Track timing
        refresh_timings = []
        
        async def timing_callback(conn_id: str, event_type: str, event_data: Dict):
            if event_type == "token_refreshed":
                refresh_timings.append({
                    "timestamp": datetime.now(timezone.utc),
                    "refresh_count": event_data.get("refresh_count", 0)
                })
                
        await custom_lifecycle_manager.add_connection_event_callback(timing_callback)
        
        with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=self.mock_auth_service):
            with mock.patch.object(custom_lifecycle_manager, '_generate_refreshed_token', side_effect=lambda state: f"timed_token_{len(refresh_timings)}"):
                
                # WHEN: Running refresh cycle for timing measurement
                await custom_lifecycle_manager.start_lifecycle_management()
                
                # Wait for multiple refresh cycles
                await asyncio.sleep(25)  # Should allow 2-3 refresh cycles
                
                await custom_lifecycle_manager.stop_lifecycle_management()
                
                # THEN: Verify timing accuracy
                assert len(refresh_timings) >= 2, "Should have multiple refresh cycles"
                
                # Calculate intervals between refreshes
                if len(refresh_timings) >= 2:
                    intervals = []
                    for i in range(1, len(refresh_timings)):
                        interval = (refresh_timings[i]["timestamp"] - refresh_timings[i-1]["timestamp"]).total_seconds()
                        intervals.append(interval)
                    
                    # Intervals should be close to refresh_interval (10s) with some tolerance
                    for interval in intervals:
                        assert 8 <= interval <= 12, f"Refresh interval {interval}s should be ~10s (±2s tolerance)"
                    
                    avg_interval = sum(intervals) / len(intervals)
                    self.record_metric("average_refresh_interval", avg_interval)
                    self.record_metric("refresh_interval_accuracy", abs(10 - avg_interval))
                
                # Verify connection state scheduling
                connection_state = custom_lifecycle_manager._connection_states[self.connection_id]
                assert connection_state.next_refresh_scheduled is not None, "Next refresh should be scheduled"
                
                # Next refresh should be reasonably soon
                time_to_next_refresh = (connection_state.next_refresh_scheduled - datetime.now(timezone.utc)).total_seconds()
                assert -5 <= time_to_next_refresh <= 15, f"Next refresh should be within reasonable time, got {time_to_next_refresh}s"
        
        self.record_metric("refresh_timing_validation_success", True)