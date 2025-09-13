"""
AgentWebSocketBridge State Management Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Protect $500K+ ARR by ensuring reliable state transitions
- Value Impact: Validates state machine logic preventing WebSocket disconnection failures
- Strategic Impact: Core state management for Golden Path chat reliability

This test suite validates the state management patterns of AgentWebSocketBridge,
ensuring proper state transitions, concurrent access safety, and persistence
that are critical for maintaining WebSocket connections and agent event delivery.

@compliance CLAUDE.md - SSOT patterns, real services over mocks
@compliance SPEC/websocket_agent_integration_critical.xml - State management patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

# Bridge Components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult,
    IntegrationMetrics
)

# User Context for isolation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket Dependencies (for state validation)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentWebSocketBridgeStateManagement(SSotAsyncTestCase):
    """
    Test AgentWebSocketBridge state management and transitions.
    
    CRITICAL: These tests validate state machine logic that determines
    WebSocket connection reliability and agent event delivery success.
    """
    
    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)
        
        # Create test user context for isolation testing
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = f"thread_{uuid.uuid4()}"
        self.test_request_id = f"req_{uuid.uuid4()}"
        
        self.test_run_id = f"run_{uuid.uuid4()}"
        
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            agent_context={"test": "state_management"},
            audit_metadata={"test_suite": "state_management"}
        )
        
        # Create bridge for testing
        self.bridge = AgentWebSocketBridge(user_context=self.user_context)
    
    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
    
    @pytest.mark.unit
    @pytest.mark.state_transitions
    def test_initial_state_is_uninitialized(self):
        """
        Test that bridge starts in UNINITIALIZED state.
        
        BUSINESS CRITICAL: Proper initial state ensures predictable
        behavior during integration setup.
        """
        assert self.bridge.state == IntegrationState.UNINITIALIZED, "Bridge should start in UNINITIALIZED state"
        
        # Verify state is consistent across multiple bridge instances
        bridge2 = AgentWebSocketBridge(user_context=self.user_context)
        assert bridge2.state == IntegrationState.UNINITIALIZED, "All new bridges should start in UNINITIALIZED state"
    
    @pytest.mark.unit
    @pytest.mark.state_transitions
    def test_state_enum_values(self):
        """
        Test that all expected state values are available and valid.
        
        BUSINESS VALUE: Validates complete state machine coverage
        for all operational scenarios.
        """
        # Verify all expected states exist
        expected_states = [
            'UNINITIALIZED', 'INITIALIZING', 'ACTIVE', 'DEGRADED', 'FAILED'
        ]
        
        for state_name in expected_states:
            assert hasattr(IntegrationState, state_name), f"IntegrationState should have {state_name}"
            state_value = getattr(IntegrationState, state_name)
            assert isinstance(state_value, IntegrationState), f"{state_name} should be IntegrationState instance"
        
        # Verify state values are unique
        state_values = [state.value for state in IntegrationState]
        assert len(state_values) == len(set(state_values)), "All state values should be unique"
    
    @pytest.mark.unit
    @pytest.mark.health_status
    def test_health_status_creation(self):
        """
        Test HealthStatus object creation and validation.
        
        BUSINESS VALUE: Health status is critical for monitoring
        and automated recovery of WebSocket connections.
        """
        # Create health status with required fields
        health = HealthStatus(
            state=IntegrationState.ACTIVE,
            websocket_manager_healthy=True,
            registry_healthy=True,
            last_health_check=datetime.now(timezone.utc)
        )
        
        # Verify required fields
        assert health.state == IntegrationState.ACTIVE, "Health state should be set correctly"
        assert health.websocket_manager_healthy is True, "WebSocket manager health should be set"
        assert health.registry_healthy is True, "Registry health should be set"
        assert isinstance(health.last_health_check, datetime), "Last health check should be datetime"
        
        # Verify optional fields have defaults
        assert health.consecutive_failures == 0, "Consecutive failures should default to 0"
        assert health.total_recoveries == 0, "Total recoveries should default to 0"
        assert health.uptime_seconds == 0.0, "Uptime should default to 0.0"
        assert health.error_message is None, "Error message should default to None"
    
    @pytest.mark.unit
    @pytest.mark.health_status
    def test_health_status_with_errors(self):
        """
        Test HealthStatus object with error conditions.
        
        BUSINESS VALUE: Error tracking enables proper escalation
        and recovery procedures for WebSocket failures.
        """
        # Create health status with error conditions
        health = HealthStatus(
            state=IntegrationState.FAILED,
            websocket_manager_healthy=False,
            registry_healthy=True,
            last_health_check=datetime.now(timezone.utc),
            consecutive_failures=3,
            total_recoveries=1,
            uptime_seconds=150.5,
            error_message="WebSocket connection lost"
        )
        
        # Verify error fields
        assert health.state == IntegrationState.FAILED, "Health state should reflect failure"
        assert health.websocket_manager_healthy is False, "WebSocket manager should be unhealthy"
        assert health.consecutive_failures == 3, "Consecutive failures should be tracked"
        assert health.total_recoveries == 1, "Total recoveries should be tracked"
        assert health.uptime_seconds == 150.5, "Uptime should be tracked"
        assert health.error_message == "WebSocket connection lost", "Error message should be preserved"
    
    @pytest.mark.unit
    @pytest.mark.integration_result
    def test_integration_result_success(self):
        """
        Test IntegrationResult for successful operations.
        
        BUSINESS VALUE: Integration results provide detailed feedback
        for monitoring and debugging WebSocket operations.
        """
        # Create successful integration result
        result = IntegrationResult(
            success=True,
            state=IntegrationState.ACTIVE,
            duration_ms=125.5
        )
        
        # Verify success fields
        assert result.success is True, "Result should indicate success"
        assert result.state == IntegrationState.ACTIVE, "Result should have correct state"
        assert result.duration_ms == 125.5, "Duration should be tracked"
        assert result.error is None, "Error should be None for success"
        assert result.recovery_attempted is False, "Recovery should not be attempted for success"
    
    @pytest.mark.unit
    @pytest.mark.integration_result
    def test_integration_result_failure(self):
        """
        Test IntegrationResult for failed operations.
        
        BUSINESS VALUE: Failure tracking enables rapid diagnosis
        and resolution of WebSocket integration issues.
        """
        # Create failed integration result
        result = IntegrationResult(
            success=False,
            state=IntegrationState.FAILED,
            error="Connection timeout",
            duration_ms=30000.0,
            recovery_attempted=True
        )
        
        # Verify failure fields
        assert result.success is False, "Result should indicate failure"
        assert result.state == IntegrationState.FAILED, "Result should have failed state"
        assert result.error == "Connection timeout", "Error message should be preserved"
        assert result.duration_ms == 30000.0, "Duration should be tracked"
        assert result.recovery_attempted is True, "Recovery attempt should be tracked"
    
    @pytest.mark.unit
    @pytest.mark.metrics_tracking
    def test_integration_metrics_initialization(self):
        """
        Test IntegrationMetrics object initialization.
        
        BUSINESS VALUE: Metrics tracking enables performance monitoring
        and capacity planning for WebSocket infrastructure.
        """
        # Create metrics object
        metrics = IntegrationMetrics()
        
        # Verify all counters start at zero
        assert metrics.total_initializations == 0, "Total initializations should start at 0"
        assert metrics.successful_initializations == 0, "Successful initializations should start at 0"
        assert metrics.failed_initializations == 0, "Failed initializations should start at 0"
        assert metrics.recovery_attempts == 0, "Recovery attempts should start at 0"
    
    @pytest.mark.unit
    @pytest.mark.metrics_tracking
    def test_integration_metrics_tracking(self):
        """
        Test IntegrationMetrics counter increments.
        
        BUSINESS VALUE: Accurate metrics enable data-driven optimization
        of WebSocket bridge performance and reliability.
        """
        # Create metrics object and simulate operations
        metrics = IntegrationMetrics(
            total_initializations=10,
            successful_initializations=8,
            failed_initializations=2,
            recovery_attempts=3
        )
        
        # Verify counters can be set to non-zero values
        assert metrics.total_initializations == 10, "Total initializations should be tracked"
        assert metrics.successful_initializations == 8, "Successful initializations should be tracked"
        assert metrics.failed_initializations == 2, "Failed initializations should be tracked"
        assert metrics.recovery_attempts == 3, "Recovery attempts should be tracked"
        
        # Verify arithmetic consistency
        assert metrics.successful_initializations + metrics.failed_initializations == metrics.total_initializations, \
            "Success + failure counts should equal total"
    
    @pytest.mark.unit
    @pytest.mark.concurrent_access
    async def test_concurrent_state_access(self):
        """
        Test concurrent access to bridge state properties.
        
        BUSINESS CRITICAL: Concurrent access must be thread-safe to prevent
        race conditions in multi-user WebSocket scenarios.
        """
        # Create multiple concurrent tasks accessing state
        async def read_state(bridge, results, index):
            """Read bridge state multiple times."""
            for _ in range(10):
                state = bridge.state
                results[index].append(state)
                await asyncio.sleep(0.001)  # Small delay to increase concurrency
        
        # Prepare result storage
        results = [[] for _ in range(5)]
        
        # Run concurrent state reads
        tasks = [
            read_state(self.bridge, results, i) 
            for i in range(5)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all reads returned consistent state
        for i, result_list in enumerate(results):
            assert len(result_list) == 10, f"Task {i} should have 10 state readings"
            for state in result_list:
                assert state == IntegrationState.UNINITIALIZED, f"All states should be UNINITIALIZED"
    
    @pytest.mark.unit
    @pytest.mark.state_persistence
    def test_state_persistence_across_operations(self):
        """
        Test that state persists correctly across bridge operations.
        
        BUSINESS VALUE: State persistence ensures reliable behavior
        during complex WebSocket operation sequences.
        """
        # Verify initial state
        assert self.bridge.state == IntegrationState.UNINITIALIZED, "Should start in UNINITIALIZED"
        
        # Perform various operations that shouldn't change state
        config_before = self.bridge.config
        user_context_before = self.bridge.user_context
        
        # Access properties multiple times
        for _ in range(5):
            _ = self.bridge.user_id
            _ = self.bridge.websocket_manager
            _ = self.bridge.registry
        
        # Verify state remains unchanged
        assert self.bridge.state == IntegrationState.UNINITIALIZED, "State should remain UNINITIALIZED"
        assert self.bridge.config is config_before, "Config should remain unchanged"
        assert self.bridge.user_context is user_context_before, "User context should remain unchanged"
    
    @pytest.mark.unit
    @pytest.mark.isolation_validation
    def test_state_isolation_between_bridges(self):
        """
        Test that state is properly isolated between different bridge instances.
        
        BUSINESS CRITICAL: State isolation prevents cross-user data leakage
        and ensures multi-tenant security.
        """
        # Create multiple bridges with different user contexts
        bridges = []
        user_contexts = []
        
        for i in range(3):
            user_context = UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4()}",
                thread_id=f"thread_{i}_{uuid.uuid4()}",
                run_id=f"run_{i}_{uuid.uuid4()}",
                request_id=f"req_{i}_{uuid.uuid4()}",
                agent_context={"user_index": i},
                audit_metadata={"test": "isolation"}
            )
            user_contexts.append(user_context)
            bridges.append(AgentWebSocketBridge(user_context=user_context))
        
        # Verify each bridge has independent state
        for i, bridge in enumerate(bridges):
            assert bridge.state == IntegrationState.UNINITIALIZED, f"Bridge {i} should be UNINITIALIZED"
            assert bridge.user_context is user_contexts[i], f"Bridge {i} should have correct user context"
            assert bridge.user_id == user_contexts[i].user_id, f"Bridge {i} should have correct user ID"
        
        # Verify bridges are independent objects
        for i in range(len(bridges)):
            for j in range(i + 1, len(bridges)):
                assert bridges[i] is not bridges[j], f"Bridge {i} and {j} should be different instances"
                assert bridges[i].state == bridges[j].state, f"All bridges should have same initial state"
                assert bridges[i].user_id != bridges[j].user_id, f"Bridge {i} and {j} should have different user IDs"
    
    @pytest.mark.unit
    @pytest.mark.lock_initialization
    async def test_asyncio_locks_are_independent(self):
        """
        Test that asyncio locks are properly initialized and independent.
        
        BUSINESS VALUE: Independent locks prevent deadlocks and ensure
        proper concurrency control in WebSocket operations.
        """
        # Create two bridges
        bridge1 = AgentWebSocketBridge(user_context=self.user_context)
        bridge2 = AgentWebSocketBridge(user_context=self.user_context)
        
        # Verify locks exist on both bridges
        for bridge in [bridge1, bridge2]:
            assert hasattr(bridge, 'initialization_lock'), "Bridge should have initialization lock"
            assert hasattr(bridge, 'recovery_lock'), "Bridge should have recovery lock"
            assert hasattr(bridge, 'health_lock'), "Bridge should have health lock"
        
        # Verify locks are independent between bridges
        assert bridge1.initialization_lock is not bridge2.initialization_lock, "Initialization locks should be independent"
        assert bridge1.recovery_lock is not bridge2.recovery_lock, "Recovery locks should be independent"
        assert bridge1.health_lock is not bridge2.health_lock, "Health locks should be independent"
        
        # Test that locks can be acquired independently
        async with bridge1.initialization_lock:
            # While bridge1 lock is held, bridge2 lock should still be acquirable
            lock_acquired = False
            try:
                async with asyncio.wait_for(bridge2.initialization_lock.acquire(), timeout=0.1):
                    lock_acquired = True
                    bridge2.initialization_lock.release()
            except asyncio.TimeoutError:
                pass  # This would indicate a problem with lock independence
            
            assert lock_acquired, "Bridge2 lock should be acquirable while bridge1 lock is held"
    
    @pytest.mark.unit
    @pytest.mark.shutdown_handling
    def test_shutdown_flag_initialization(self):
        """
        Test shutdown flag initialization and state.
        
        BUSINESS VALUE: Proper shutdown handling prevents resource leaks
        and ensures clean WebSocket disconnection.
        """
        # Verify shutdown flag exists and is properly initialized
        assert hasattr(self.bridge, '_shutdown'), "Bridge should have shutdown flag"
        assert self.bridge._shutdown is False, "Shutdown flag should be False initially"
        
        # Verify shutdown flag type
        assert isinstance(self.bridge._shutdown, bool), "Shutdown flag should be boolean"
        
        # Verify shutdown flag is independent per bridge
        bridge2 = AgentWebSocketBridge(user_context=self.user_context)
        assert bridge2._shutdown is False, "New bridge shutdown flag should be False"
        
        # Modify one bridge's shutdown flag and verify independence
        self.bridge._shutdown = True
        assert bridge2._shutdown is False, "Other bridge shutdown flag should remain False"