"""Tests for WebSocket callback failure propagation and handling."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from app.websocket.reconnection_manager import WebSocketReconnectionManager
from app.websocket.reconnection_types import (
    ReconnectionConfig, DisconnectReason, ReconnectionState,
    CallbackType, CallbackCriticality
)
from app.websocket.reconnection_exceptions import (
    CriticalCallbackFailure, StateNotificationFailure, CallbackCircuitBreakerOpen
)


class TestCriticalCallbackFailures:
    """Test critical callback failure propagation."""
    
    @pytest.fixture
    def manager(self):
        """Create reconnection manager for testing."""
        config = ReconnectionConfig(max_attempts=2, initial_delay_ms=100)
        return WebSocketReconnectionManager("test-conn", config)
    
    @pytest.mark.asyncio
    async def test_critical_state_callback_failure_stops_system(self, manager):
        """Test that critical state callback failures stop the system."""
        # Setup failing state callback
        failing_callback = AsyncMock(side_effect=Exception("State callback failed"))
        manager.set_callbacks(state_change_callback=failing_callback)
        
        # Attempt to notify state change should fail critically
        with pytest.raises(StateNotificationFailure):
            await manager._notify_state_change()
        
        # System should be in failed state
        assert manager.state == ReconnectionState.FAILED
        assert manager._permanent_failure is True
        assert manager._stop_reconnecting is True
        assert manager.metrics.critical_callback_failures == 1
    
    @pytest.mark.asyncio 
    async def test_important_callback_failure_logs_warning(self, manager):
        """Test that important callback failures log warnings but continue."""
        # Setup failing connect callback
        failing_callback = AsyncMock(side_effect=Exception("Connect failed"))
        manager.set_callbacks(connect_callback=failing_callback)
        
        # Should log warning but not raise exception
        await manager._execute_connection_callback()
        
        # System should continue normally
        assert manager.state != ReconnectionState.FAILED
        assert manager._permanent_failure is False
    
    @pytest.mark.asyncio
    async def test_non_critical_callback_failure_continues(self, manager):
        """Test that non-critical callback failures are logged but system continues."""
        # Set disconnect callback as non-critical
        manager.set_callback_criticality(CallbackType.DISCONNECT, CallbackCriticality.NON_CRITICAL)
        
        failing_callback = AsyncMock(side_effect=Exception("Disconnect failed"))
        manager.set_callbacks(disconnect_callback=failing_callback)
        
        # Should not raise exception
        await manager.callback_executor.execute_disconnect(failing_callback, DisconnectReason.NORMAL_CLOSURE)
        
        # System should continue normally
        assert manager.state != ReconnectionState.FAILED
        assert manager._permanent_failure is False


class TestCallbackCircuitBreaker:
    """Test callback circuit breaker functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with fast circuit breaker for testing."""
        config = ReconnectionConfig(max_attempts=5, initial_delay_ms=50)
        manager = WebSocketReconnectionManager("test-conn", config)
        # Set circuit breaker threshold low for testing
        for cb_type in manager.callback_failure_manager.circuit_breakers:
            manager.callback_failure_manager.circuit_breakers[cb_type].failure_threshold = 2
        return manager
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, manager):
        """Test that circuit breaker opens after repeated failures."""
        failing_callback = AsyncMock(side_effect=Exception("Always fails"))
        
        # Set as non-critical to avoid system shutdown
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
        
        # First two failures should work (threshold = 2)
        await manager.callback_executor.execute_connect(failing_callback)
        await manager.callback_executor.execute_connect(failing_callback)
        
        # Third attempt should trigger circuit breaker
        with pytest.raises(CallbackCircuitBreakerOpen):
            await manager.callback_executor.execute_connect(failing_callback)
        
        # Circuit breaker should be open
        breaker = manager.callback_failure_manager.circuit_breakers[CallbackType.CONNECT]
        assert breaker.is_open is True
        assert breaker.failure_count == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, manager):
        """Test that circuit breaker resets after successful execution."""
        failing_callback = AsyncMock(side_effect=Exception("Fails initially"))
        success_callback = AsyncMock()
        
        # Set as non-critical
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
        
        # Trigger circuit breaker
        await manager.callback_executor.execute_connect(failing_callback)
        await manager.callback_executor.execute_connect(failing_callback)
        
        with pytest.raises(CallbackCircuitBreakerOpen):
            await manager.callback_executor.execute_connect(failing_callback)
        
        # Manually reset circuit breaker (simulating timeout)
        breaker = manager.callback_failure_manager.circuit_breakers[CallbackType.CONNECT]
        breaker.is_open = False
        breaker.last_failure_time = datetime.now(timezone.utc)  # Simulate timeout elapsed
        
        # Success should reset the breaker
        await manager.callback_executor.execute_connect(success_callback)
        
        assert breaker.is_open is False
        assert breaker.failure_count == 0
        assert len(breaker.recent_failures) == 0


class TestCallbackCriticalityConfiguration:
    """Test callback criticality configuration."""
    
    @pytest.fixture
    def manager(self):
        """Create reconnection manager for testing."""
        return WebSocketReconnectionManager("test-conn", ReconnectionConfig())
    
    def test_default_criticality_mapping(self, manager):
        """Test default callback criticality mapping."""
        criticality_map = manager.callback_failure_manager.criticality_map
        
        assert criticality_map[CallbackType.STATE_CHANGE] == CallbackCriticality.CRITICAL
        assert criticality_map[CallbackType.CONNECT] == CallbackCriticality.IMPORTANT
        assert criticality_map[CallbackType.DISCONNECT] == CallbackCriticality.NON_CRITICAL
    
    def test_update_callback_criticality(self, manager):
        """Test updating callback criticality levels."""
        # Change connect callback to critical
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.CRITICAL)
        
        criticality_map = manager.callback_failure_manager.criticality_map
        assert criticality_map[CallbackType.CONNECT] == CallbackCriticality.CRITICAL
    
    @pytest.mark.asyncio
    async def test_connect_callback_as_critical_stops_system(self, manager):
        """Test that connect callback set to critical stops system on failure."""
        # Set connect callback as critical
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.CRITICAL)
        
        failing_callback = AsyncMock(side_effect=Exception("Critical connect failure"))
        
        # Should raise critical failure
        with pytest.raises(CriticalCallbackFailure):
            await manager.callback_executor.execute_connect(failing_callback)


class TestFailureMetrics:
    """Test callback failure metrics collection."""
    
    @pytest.fixture
    def manager(self):
        """Create reconnection manager for testing."""
        return WebSocketReconnectionManager("test-conn", ReconnectionConfig())
    
    @pytest.mark.asyncio
    async def test_failure_metrics_collection(self, manager):
        """Test that failure metrics are properly collected."""
        failing_callback = AsyncMock(side_effect=Exception("Test failure"))
        
        # Set as non-critical to avoid system shutdown
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
        
        # Generate some failures
        await manager.callback_executor.execute_connect(failing_callback)
        await manager.callback_executor.execute_connect(failing_callback)
        
        # Check metrics
        metrics = manager.callback_failure_manager.get_failure_metrics()
        
        assert metrics['total_failures'] == 2
        assert metrics['critical_failures'] == 0  # Non-critical callbacks
        assert metrics['circuit_breakers'][CallbackType.CONNECT.value]['failure_count'] == 2
        assert metrics['circuit_breakers'][CallbackType.CONNECT.value]['recent_failures'] == 2
    
    @pytest.mark.asyncio
    async def test_critical_failure_metrics(self, manager):
        """Test that critical failures are counted in metrics."""
        failing_callback = AsyncMock(side_effect=Exception("Critical failure"))
        
        try:
            await manager.callback_executor.execute_state_change(failing_callback, ReconnectionState.CONNECTED)
        except (StateNotificationFailure, CriticalCallbackFailure):
            pass
        
        # Should count critical failure
        assert manager.metrics.critical_callback_failures == 1
    
    def test_comprehensive_metrics_include_callback_data(self, manager):
        """Test that comprehensive metrics include callback failure data."""
        metrics = manager.get_metrics()
        
        assert 'callback_metrics' in metrics
        assert 'total_failures' in metrics['callback_metrics']
        assert 'critical_failures' in metrics['callback_metrics']
        assert 'circuit_breakers' in metrics['callback_metrics']


class TestIntegrationScenarios:
    """Test integration scenarios with callback failures."""
    
    @pytest.fixture
    def manager(self):
        """Create reconnection manager for testing."""
        config = ReconnectionConfig(max_attempts=3, initial_delay_ms=10)
        return WebSocketReconnectionManager("test-conn", config)
    
    @pytest.mark.asyncio
    async def test_disconnect_with_failing_callbacks(self, manager):
        """Test disconnect handling with failing callbacks."""
        failing_disconnect_cb = AsyncMock(side_effect=Exception("Disconnect failed"))
        failing_state_cb = AsyncMock(side_effect=Exception("State failed"))
        
        # Set disconnect as non-critical
        manager.set_callback_criticality(CallbackType.DISCONNECT, CallbackCriticality.NON_CRITICAL)
        
        manager.set_callbacks(
            disconnect_callback=failing_disconnect_cb,
            state_change_callback=failing_state_cb
        )
        
        # Disconnect should fail on state change callback (critical)
        with pytest.raises(StateNotificationFailure):
            await manager.handle_disconnect(DisconnectReason.CONNECTION_ERROR)
        
        # System should be in failed state due to critical state callback failure
        assert manager.state == ReconnectionState.FAILED
        assert manager._permanent_failure is True
    
    @pytest.mark.asyncio
    async def test_successful_reconnection_with_some_callback_failures(self, manager):
        """Test successful reconnection despite some callback failures."""
        # Setup callbacks - disconnect fails but is non-critical
        success_connect_cb = AsyncMock()
        failing_disconnect_cb = AsyncMock(side_effect=Exception("Disconnect failed"))
        success_state_cb = AsyncMock()
        
        manager.set_callback_criticality(CallbackType.DISCONNECT, CallbackCriticality.NON_CRITICAL)
        
        manager.set_callbacks(
            connect_callback=success_connect_cb,
            disconnect_callback=failing_disconnect_cb,
            state_change_callback=success_state_cb
        )
        
        # Simulate successful connection after disconnect
        await manager.handle_successful_connection()
        
        # Should be in connected state despite disconnect callback failure
        assert manager.state == ReconnectionState.CONNECTED
        assert success_state_cb.called
        assert manager._permanent_failure is False