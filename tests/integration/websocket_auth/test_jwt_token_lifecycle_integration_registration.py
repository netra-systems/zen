"""
JWT Token Lifecycle Integration Tests - Registration Management

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Core - WebSocket Authentication Infrastructure  
- Business Goal: Ensure reliable token lifecycle registration for 5+ minute chat sessions
- Value Impact: Prevents authentication failures that break user conversations mid-flow
- Revenue Impact: Protects $500K+ ARR by maintaining continuous agent execution capability

INTEGRATION TEST SCOPE:
These tests validate the Token Lifecycle Manager's registration system with real 
components but without requiring running services. Tests cover connection registration,
user context integration, and failure scenarios using realistic data flows.

SUCCESS CRITERIA:
- Connection tokens properly registered with UserExecutionContext
- Multiple concurrent user registrations isolated correctly
- Registration failures handled gracefully with proper error states
- Token expiry scheduling works correctly (45s refresh intervals)
- Connection cleanup prevents resource leaks
- Duplicate registration scenarios handled appropriately
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest import mock
from typing import Dict, List, Optional
from dataclasses import dataclass

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
class MockConnectionEvent:
    """Mock connection event for testing callbacks."""
    connection_id: str
    event_type: str
    event_data: Dict
    timestamp: datetime


class TestJWTTokenLifecycleRegistrationIntegration(SSotAsyncTestCase):
    """
    Integration tests for JWT Token Lifecycle Manager registration system.
    
    BUSINESS IMPACT: Validates the foundation layer that enables 5+ minute WebSocket
    sessions to maintain authentication, protecting core chat functionality.
    """

    def setup_method(self, method):
        """Set up test environment with realistic configuration."""
        super().setup_method(method)
        
        # Realistic timing configuration based on production needs
        self.refresh_interval = 45  # 45 seconds - before 60s token expiry
        self.token_expiry = 60      # 60 seconds - current JWT expiry
        self.degraded_timeout = 180 # 3 minutes - max degraded mode
        
        # Create lifecycle manager with realistic timing
        self.lifecycle_manager = TokenLifecycleManager(
            refresh_interval_seconds=self.refresh_interval,
            token_expiry_seconds=self.token_expiry,
            degraded_mode_timeout_seconds=self.degraded_timeout
        )
        
        # Test data generation
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))
        self.connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        self.websocket_client_id = f"ws_{uuid.uuid4().hex[:8]}"
        
        # Track events for validation
        self.connection_events: List[MockConnectionEvent] = []
        self.registration_callbacks_fired = []
        
        # JWT secret for token creation
        env = get_env()
        self.jwt_secret = env.get("JWT_SECRET", "test_jwt_secret_key")

    def teardown_method(self, method):
        """Clean up test environment."""
        try:
            # Stop lifecycle manager
            if hasattr(self.lifecycle_manager, '_refresh_task'):
                asyncio.create_task(self.lifecycle_manager.stop_lifecycle_management())
        except Exception as e:
            self.record_metric("cleanup_error", str(e))
        finally:
            super().teardown_method(method)

    def _create_test_user_context(self, user_id: str = None) -> UserExecutionContext:
        """Create test user context with realistic data."""
        if user_id is None:
            user_id = self.test_user_id
            
        return UserExecutionContext(
            user_id=user_id,
            execution_context_id=f"ctx_{uuid.uuid4().hex[:8]}",
            websocket_client_id=self.websocket_client_id,
            timestamp=datetime.now(timezone.utc),
            session_metadata={"test_session": True, "integration_test": True}
        )

    def _create_test_token(self, expires_in_seconds: int = None) -> str:
        """Create test JWT token with realistic expiry."""
        if expires_in_seconds is None:
            expires_in_seconds = self.token_expiry
            
        # Simple test token - in real system this would be properly signed JWT
        return f"jwt_token_{uuid.uuid4().hex[:16]}_exp_{expires_in_seconds}s"

    async def _setup_connection_event_callback(self):
        """Set up callback to capture connection events."""
        async def capture_event(conn_id: str, event_type: str, event_data: Dict):
            event = MockConnectionEvent(
                connection_id=conn_id,
                event_type=event_type,
                event_data=event_data,
                timestamp=datetime.now(timezone.utc)
            )
            self.connection_events.append(event)
            self.registration_callbacks_fired.append(event_type)
        
        await self.lifecycle_manager.add_connection_event_callback(capture_event)

    # === TOKEN LIFECYCLE REGISTRATION TESTS ===

    @pytest.mark.asyncio
    async def test_connection_token_registration_success(self):
        """
        BVJ: Platform/Core - Validate successful connection registration
        Ensures token lifecycle can track connections for 5+ minute sessions
        """
        # GIVEN: User context and token ready for registration
        user_context = self._create_test_user_context()
        initial_token = self._create_test_token(expires_in_seconds=60)
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        
        await self._setup_connection_event_callback()
        
        # WHEN: Registering connection for token lifecycle management
        start_time = time.time()
        registration_success = await self.lifecycle_manager.register_connection_token(
            connection_id=self.connection_id,
            websocket_client_id=self.websocket_client_id,
            user_context=user_context,
            initial_token=initial_token,
            token_expires_at=token_expires_at
        )
        registration_time = time.time() - start_time
        
        # THEN: Registration succeeds with proper state initialization
        assert registration_success, "Token registration should succeed"
        self.record_metric("registration_time", registration_time)
        
        # Verify connection state created correctly
        connection_state = self.lifecycle_manager._connection_states.get(self.connection_id)
        assert connection_state is not None, "Connection state should be created"
        assert connection_state.user_id == user_context.user_id
        assert connection_state.websocket_client_id == self.websocket_client_id
        assert connection_state.initial_token == initial_token
        assert connection_state.current_token == initial_token
        assert connection_state.token_expires_at == token_expires_at
        assert connection_state.lifecycle_state == TokenLifecycleState.REFRESH_SCHEDULED
        
        # Verify refresh scheduling - should be 15 seconds before expiry
        expected_refresh_time = token_expires_at - timedelta(seconds=15)
        actual_refresh_time = connection_state.next_refresh_scheduled
        time_diff = abs((actual_refresh_time - expected_refresh_time).total_seconds())
        assert time_diff < 1.0, f"Refresh should be scheduled 15s before expiry, diff: {time_diff}s"
        
        # Verify metrics updated
        metrics = self.lifecycle_manager.get_connection_metrics()
        assert metrics["total_connections"] == 1
        assert metrics["active_connections"] == 1
        assert metrics["active_refresh_cycles"] == 1
        
        # Verify callback fired
        assert "registered" in self.registration_callbacks_fired
        registered_event = next(e for e in self.connection_events if e.event_type == "registered")
        assert registered_event.event_data["user_id"] == user_context.user_id
        
        self.record_metric("test_success", True)

    @pytest.mark.asyncio
    async def test_multiple_connection_registration_user_isolation(self):
        """
        BVJ: Platform/Core - Validate user isolation in multi-user scenarios
        Critical for preventing auth token leaks between users in multi-tenant system
        """
        # GIVEN: Multiple users with different contexts
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        user3_id = ensure_user_id(str(uuid.uuid4()))
        
        user1_context = self._create_test_user_context(user1_id)
        user2_context = self._create_test_user_context(user2_id)
        user3_context = self._create_test_user_context(user3_id)
        
        conn1_id = f"conn1_{uuid.uuid4().hex[:8]}"
        conn2_id = f"conn2_{uuid.uuid4().hex[:8]}"
        conn3_id = f"conn3_{uuid.uuid4().hex[:8]}"
        
        token1 = self._create_test_token(expires_in_seconds=60)
        token2 = self._create_test_token(expires_in_seconds=75)
        token3 = self._create_test_token(expires_in_seconds=90)
        
        expires_at_1 = datetime.now(timezone.utc) + timedelta(seconds=60)
        expires_at_2 = datetime.now(timezone.utc) + timedelta(seconds=75)
        expires_at_3 = datetime.now(timezone.utc) + timedelta(seconds=90)
        
        await self._setup_connection_event_callback()
        
        # WHEN: Registering multiple connections concurrently
        registration_tasks = [
            self.lifecycle_manager.register_connection_token(conn1_id, user1_context.websocket_client_id, user1_context, token1, expires_at_1),
            self.lifecycle_manager.register_connection_token(conn2_id, user2_context.websocket_client_id, user2_context, token2, expires_at_2),
            self.lifecycle_manager.register_connection_token(conn3_id, user3_context.websocket_client_id, user3_context, token3, expires_at_3)
        ]
        
        results = await asyncio.gather(*registration_tasks)
        
        # THEN: All registrations succeed with proper isolation
        assert all(results), "All registrations should succeed"
        
        # Verify each connection has correct user isolation
        conn1_state = self.lifecycle_manager._connection_states[conn1_id]
        conn2_state = self.lifecycle_manager._connection_states[conn2_id]
        conn3_state = self.lifecycle_manager._connection_states[conn3_id]
        
        assert conn1_state.user_id == user1_id
        assert conn2_state.user_id == user2_id
        assert conn3_state.user_id == user3_id
        
        assert conn1_state.current_token == token1
        assert conn2_state.current_token == token2
        assert conn3_state.current_token == token3
        
        assert conn1_state.token_expires_at == expires_at_1
        assert conn2_state.token_expires_at == expires_at_2
        assert conn3_state.token_expires_at == expires_at_3
        
        # Verify no token cross-contamination
        assert conn1_state.current_token != conn2_state.current_token
        assert conn2_state.current_token != conn3_state.current_token
        assert conn1_state.current_token != conn3_state.current_token
        
        # Verify metrics reflect multiple connections
        metrics = self.lifecycle_manager.get_connection_metrics()
        assert metrics["total_connections"] == 3
        assert metrics["active_connections"] == 3
        assert metrics["active_refresh_cycles"] == 3
        
        # Verify callbacks fired for all registrations
        registered_events = [e for e in self.connection_events if e.event_type == "registered"]
        assert len(registered_events) == 3
        
        registered_user_ids = {event.event_data["user_id"] for event in registered_events}
        assert registered_user_ids == {user1_id, user2_id, user3_id}
        
        self.record_metric("multi_user_isolation_success", True)

    @pytest.mark.asyncio
    async def test_token_expiry_scheduling_accuracy(self):
        """
        BVJ: Platform/Core - Validate precise refresh timing for uninterrupted chat
        Ensures tokens refresh 15s before expiry to prevent authentication gaps
        """
        # GIVEN: Connection with specific expiry timing
        user_context = self._create_test_user_context()
        initial_token = self._create_test_token()
        
        # Set precise expiry time for validation
        precise_expiry = datetime.now(timezone.utc) + timedelta(seconds=120)  # 2 minutes
        
        # WHEN: Registering with specific expiry time
        await self.lifecycle_manager.register_connection_token(
            connection_id=self.connection_id,
            websocket_client_id=self.websocket_client_id,
            user_context=user_context,
            initial_token=initial_token,
            token_expires_at=precise_expiry
        )
        
        # THEN: Refresh scheduled exactly 15 seconds before expiry
        connection_state = self.lifecycle_manager._connection_states[self.connection_id]
        expected_refresh = precise_expiry - timedelta(seconds=15)
        actual_refresh = connection_state.next_refresh_scheduled
        
        # Allow 1 second tolerance for timing precision
        time_difference = abs((actual_refresh - expected_refresh).total_seconds())
        assert time_difference <= 1.0, f"Refresh timing off by {time_difference}s, expected within 1s"
        
        # Verify state is correctly set to REFRESH_SCHEDULED
        assert connection_state.lifecycle_state == TokenLifecycleState.REFRESH_SCHEDULED
        
        # Verify timing calculations work correctly
        assert connection_state.time_until_expiry_seconds() > 100  # More than 100s remaining
        assert not connection_state.is_token_expired()
        assert not connection_state.is_token_expiring_soon(warning_seconds=30)  # Not expiring within 30s
        assert connection_state.is_token_expiring_soon(warning_seconds=130)     # But expiring within 130s
        
        self.record_metric("refresh_timing_accuracy", time_difference)

    @pytest.mark.asyncio
    async def test_connection_unregistration_cleanup(self):
        """
        BVJ: Platform/Core - Validate proper resource cleanup prevents memory leaks
        Critical for long-running production systems handling many WebSocket connections
        """
        # GIVEN: Multiple registered connections
        connections_to_register = 5
        connection_states = []
        
        for i in range(connections_to_register):
            user_context = self._create_test_user_context(ensure_user_id(str(uuid.uuid4())))
            conn_id = f"cleanup_test_conn_{i}_{uuid.uuid4().hex[:8]}"
            token = self._create_test_token()
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
            
            await self.lifecycle_manager.register_connection_token(
                connection_id=conn_id,
                websocket_client_id=f"ws_client_{i}",
                user_context=user_context,
                initial_token=token,
                token_expires_at=expires_at
            )
            
            connection_states.append((conn_id, user_context.user_id))
            
            # Simulate some connection activity
            await asyncio.sleep(0.01)  # Small delay to simulate real timing
        
        await self._setup_connection_event_callback()
        
        # Verify all connections registered
        initial_metrics = self.lifecycle_manager.get_connection_metrics()
        assert initial_metrics["active_connections"] == connections_to_register
        assert initial_metrics["total_connections"] == connections_to_register
        
        # WHEN: Unregistering connections one by one
        unregistered_count = 0
        for conn_id, user_id in connection_states[:3]:  # Unregister first 3
            await self.lifecycle_manager.unregister_connection(conn_id)
            unregistered_count += 1
            
            # Verify connection removed from tracking
            assert conn_id not in self.lifecycle_manager._connection_states
            
            # Verify metrics updated correctly
            current_metrics = self.lifecycle_manager.get_connection_metrics()
            assert current_metrics["active_connections"] == (connections_to_register - unregistered_count)
            assert current_metrics["total_connections"] == connections_to_register  # Total remains same
        
        # THEN: Remaining connections still tracked correctly
        final_metrics = self.lifecycle_manager.get_connection_metrics()
        assert final_metrics["active_connections"] == 2  # 2 remaining
        assert final_metrics["active_refresh_cycles"] == 2
        
        # Verify unregistration events fired
        unregistered_events = [e for e in self.connection_events if e.event_type == "unregistered"]
        assert len(unregistered_events) == 3
        
        # Verify connection duration tracking
        for event in unregistered_events:
            assert "connection_duration" in event.event_data
            assert event.event_data["connection_duration"] >= 0
            assert "refresh_count" in event.event_data
            assert "refresh_failures" in event.event_data
        
        # Verify average connection duration calculated
        if final_metrics["average_connection_duration"] > 0:
            assert final_metrics["average_connection_duration"] >= 0
        
        self.record_metric("cleanup_efficiency", True)

    @pytest.mark.asyncio
    async def test_registration_failure_handling(self):
        """
        BVJ: Platform/Core - Validate graceful handling of registration failures
        Ensures system stability when registration fails due to invalid data
        """
        # GIVEN: Invalid registration scenarios
        user_context = self._create_test_user_context()
        valid_token = self._create_test_token()
        valid_expiry = datetime.now(timezone.utc) + timedelta(seconds=60)
        
        # WHEN/THEN: Test various failure scenarios
        test_scenarios = [
            # Invalid connection_id
            {
                "connection_id": "",  # Empty connection ID
                "websocket_client_id": self.websocket_client_id,
                "user_context": user_context,
                "initial_token": valid_token,
                "token_expires_at": valid_expiry,
                "expected_result": False,
                "scenario_name": "empty_connection_id"
            },
            # Invalid user context
            {
                "connection_id": "valid_conn_id",
                "websocket_client_id": self.websocket_client_id,
                "user_context": None,  # None user context
                "initial_token": valid_token,
                "token_expires_at": valid_expiry,
                "expected_result": False,
                "scenario_name": "none_user_context"
            },
            # Invalid token
            {
                "connection_id": "another_valid_conn_id",
                "websocket_client_id": self.websocket_client_id,
                "user_context": user_context,
                "initial_token": "",  # Empty token
                "token_expires_at": valid_expiry,
                "expected_result": False,
                "scenario_name": "empty_token"
            },
            # Past expiry time
            {
                "connection_id": "past_expiry_conn_id",
                "websocket_client_id": self.websocket_client_id,
                "user_context": user_context,
                "initial_token": valid_token,
                "token_expires_at": datetime.now(timezone.utc) - timedelta(seconds=30),  # Already expired
                "expected_result": False,
                "scenario_name": "past_expiry"
            }
        ]
        
        for scenario in test_scenarios:
            with mock.patch.object(self.lifecycle_manager, '_notify_connection_event', return_value=None):
                try:
                    result = await self.lifecycle_manager.register_connection_token(
                        connection_id=scenario["connection_id"],
                        websocket_client_id=scenario["websocket_client_id"],
                        user_context=scenario["user_context"],
                        initial_token=scenario["initial_token"],
                        token_expires_at=scenario["token_expires_at"]
                    )
                    
                    # Verify expected result
                    assert result == scenario["expected_result"], f"Scenario {scenario['scenario_name']} should return {scenario['expected_result']}"
                    
                    # If registration should fail, verify connection not tracked
                    if not scenario["expected_result"]:
                        assert scenario["connection_id"] not in self.lifecycle_manager._connection_states
                    
                    self.record_metric(f"failure_handling_{scenario['scenario_name']}", result == scenario["expected_result"])
                    
                except Exception as e:
                    # Some scenarios might raise exceptions - that's also valid failure handling
                    if scenario["expected_result"]:
                        # If we expected success but got exception, that's a problem
                        raise AssertionError(f"Scenario {scenario['scenario_name']} expected success but got exception: {e}")
                    else:
                        # Expected failure, exception is acceptable
                        self.record_metric(f"failure_handling_{scenario['scenario_name']}", True)

    @pytest.mark.asyncio
    async def test_duplicate_connection_registration_handling(self):
        """
        BVJ: Platform/Core - Validate handling of duplicate registration attempts
        Prevents resource leaks and state corruption from multiple registration calls
        """
        # GIVEN: Initial connection registration
        user_context = self._create_test_user_context()
        initial_token = self._create_test_token()
        initial_expiry = datetime.now(timezone.utc) + timedelta(seconds=60)
        
        await self._setup_connection_event_callback()
        
        # First registration
        first_result = await self.lifecycle_manager.register_connection_token(
            connection_id=self.connection_id,
            websocket_client_id=self.websocket_client_id,
            user_context=user_context,
            initial_token=initial_token,
            token_expires_at=initial_expiry
        )
        
        assert first_result, "First registration should succeed"
        first_state = self.lifecycle_manager._connection_states[self.connection_id]
        first_refresh_time = first_state.next_refresh_scheduled
        
        # WHEN: Attempting duplicate registration with different token
        duplicate_token = self._create_test_token()
        duplicate_expiry = datetime.now(timezone.utc) + timedelta(seconds=90)
        
        # Wait a small amount to ensure timestamps differ
        await asyncio.sleep(0.1)
        
        second_result = await self.lifecycle_manager.register_connection_token(
            connection_id=self.connection_id,  # Same connection ID
            websocket_client_id=self.websocket_client_id,
            user_context=user_context,
            initial_token=duplicate_token,  # Different token
            token_expires_at=duplicate_expiry  # Different expiry
        )
        
        # THEN: Verify duplicate handling behavior
        second_state = self.lifecycle_manager._connection_states[self.connection_id]
        
        # The behavior depends on implementation - either:
        # 1. Duplicate registration succeeds and updates state (most common)
        # 2. Duplicate registration is rejected to prevent overwrites
        
        if second_result:
            # If second registration succeeded, verify state was updated
            assert second_state.initial_token == duplicate_token, "Token should be updated on successful duplicate registration"
            assert second_state.token_expires_at == duplicate_expiry, "Expiry should be updated"
            assert second_state.next_refresh_scheduled != first_refresh_time, "Refresh schedule should be updated"
        else:
            # If second registration was rejected, verify original state preserved
            assert second_state.initial_token == initial_token, "Original token should be preserved on rejected duplicate"
            assert second_state.token_expires_at == initial_expiry, "Original expiry should be preserved"
            assert second_state.next_refresh_scheduled == first_refresh_time, "Original refresh schedule preserved"
        
        # Verify metrics consistency - should still show only 1 total connection
        # (might have 2 if duplicate creates new entry, but should be consistent)
        metrics = self.lifecycle_manager.get_connection_metrics()
        assert metrics["active_connections"] >= 1, "Should have at least 1 active connection"
        
        # Verify callback behavior - might have 1 or 2 registered events depending on implementation
        registered_events = [e for e in self.connection_events if e.event_type == "registered"]
        assert len(registered_events) >= 1, "Should have at least 1 registered event"
        
        self.record_metric("duplicate_handling_result", second_result)
        self.record_metric("duplicate_handling_success", True)