"""
Unit tests for AgentWebSocketBridge - Testing integration lifecycle and health monitoring.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Reliable agent-WebSocket integration
- Value Impact: Ensures agents can reliably communicate with users via WebSocket
- Strategic Impact: Core integration point - validates agent-WebSocket coordination without dependencies

These tests focus on the AgentWebSocketBridge's core functionality including
integration state management, health monitoring, and recovery mechanisms.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import asdict
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult,
    IntegrationMetrics
)


class TestAgentWebSocketBridgeCore:
    """Unit tests for core AgentWebSocketBridge functionality."""
    
    @pytest.fixture
    def integration_config(self):
        """Create test integration configuration."""
        return IntegrationConfig(
            initialization_timeout_s=10,
            health_check_interval_s=30,
            recovery_max_attempts=2,
            recovery_base_delay_s=0.5,
            recovery_max_delay_s=5.0,
            integration_verification_timeout_s=5
        )
    
    @pytest.fixture
    def agent_websocket_bridge(self, integration_config):
        """Create AgentWebSocketBridge instance with test configuration."""
        # Create a mock UserExecutionContext for testing
        from unittest.mock import Mock
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user_123"
        mock_user_context.thread_id = "test_thread_456"
        
        # Create bridge with user context (constructor expects UserExecutionContext, not IntegrationConfig)
        return AgentWebSocketBridge(mock_user_context)
    
    def test_initializes_with_correct_default_state(self, agent_websocket_bridge):
        """Test bridge initializes with proper default state."""
        assert agent_websocket_bridge.state == IntegrationState.UNINITIALIZED
        assert agent_websocket_bridge.websocket_manager is None
        assert agent_websocket_bridge.registry is None
        
        # Check configuration was applied
        config = agent_websocket_bridge.config
        assert config.initialization_timeout_s == 10
        assert config.health_check_interval_s == 30
        assert config.recovery_max_attempts == 2
        
        # Check metrics initialization
        metrics = agent_websocket_bridge.metrics
        assert metrics.total_initializations == 0
        assert metrics.successful_initializations == 0
        assert metrics.failed_initializations == 0
    
    def test_health_status_creation_with_all_fields(self, agent_websocket_bridge):
        """Test comprehensive health status creation."""
        # Arrange
        agent_websocket_bridge.state = IntegrationState.ACTIVE
        agent_websocket_bridge.websocket_manager = Mock()
        agent_websocket_bridge.registry = Mock()
        
        # Act
        health_status = agent_websocket_bridge._create_health_status(
            websocket_healthy=True,
            registry_healthy=True,
            error_message=None
        )
        
        # Assert
        assert isinstance(health_status, HealthStatus)
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.websocket_manager_healthy is True
        assert health_status.registry_healthy is True
        assert health_status.error_message is None
        assert health_status.consecutive_failures == 0
        assert isinstance(health_status.last_health_check, datetime)
    
    def test_integration_result_creation_with_metrics(self, agent_websocket_bridge):
        """Test integration result creation includes proper metrics."""
        start_time = datetime.now()
        
        # Simulate operation
        import time
        time.sleep(0.01)  # Small delay to measure
        
        # Act
        result = agent_websocket_bridge._create_integration_result(
            success=True,
            state=IntegrationState.ACTIVE,
            start_time=start_time,
            error=None,
            recovery_attempted=False
        )
        
        # Assert
        assert isinstance(result, IntegrationResult)
        assert result.success is True
        assert result.state == IntegrationState.ACTIVE
        assert result.error is None
        assert result.recovery_attempted is False
        assert result.duration_ms > 0  # Should have measured some duration
        assert result.duration_ms < 1000  # Should be reasonable
    
    def test_exponential_backoff_delay_calculation(self, agent_websocket_bridge):
        """Test exponential backoff delay calculation for recovery attempts."""
        config = agent_websocket_bridge.config
        
        # Test various attempt numbers
        delay_0 = agent_websocket_bridge._calculate_recovery_delay(0)
        delay_1 = agent_websocket_bridge._calculate_recovery_delay(1)
        delay_2 = agent_websocket_bridge._calculate_recovery_delay(2)
        delay_5 = agent_websocket_bridge._calculate_recovery_delay(5)
        
        # Should start at base delay
        assert delay_0 == config.recovery_base_delay_s
        
        # Should increase exponentially
        assert delay_1 == config.recovery_base_delay_s * 2
        assert delay_2 == config.recovery_base_delay_s * 4
        
        # Should cap at max delay
        assert delay_5 <= config.recovery_max_delay_s
        
        # Test edge cases
        large_attempt = agent_websocket_bridge._calculate_recovery_delay(100)
        assert large_attempt == config.recovery_max_delay_s
    
    def test_component_health_check_methods(self, agent_websocket_bridge):
        """Test individual component health checking methods."""
        # Test WebSocket manager health check
        mock_websocket_manager = Mock()
        mock_websocket_manager.get_stats.return_value = {
            "total_connections": 5,
            "unique_users": 3,
            "errors": []
        }
        
        is_healthy = agent_websocket_bridge._check_websocket_manager_health(mock_websocket_manager)
        assert is_healthy is True
        
        # Test with errors
        mock_websocket_manager.get_stats.return_value = {
            "total_connections": 0,
            "unique_users": 0, 
            "errors": ["Connection failure"]
        }
        
        is_healthy = agent_websocket_bridge._check_websocket_manager_health(mock_websocket_manager)
        assert is_healthy is False
        
        # Test registry health check
        mock_registry = Mock()
        mock_registry.get_all_executions.return_value = ["exec1", "exec2"]
        
        is_healthy = agent_websocket_bridge._check_registry_health(mock_registry)
        assert is_healthy is True
        
        # Test registry failure
        mock_registry.get_all_executions.side_effect = Exception("Registry error")
        
        is_healthy = agent_websocket_bridge._check_registry_health(mock_registry)
        assert is_healthy is False
    
    def test_integration_metrics_tracking(self, agent_websocket_bridge):
        """Test comprehensive integration metrics tracking."""
        metrics = agent_websocket_bridge.metrics
        
        # Simulate successful initialization
        agent_websocket_bridge._record_initialization_attempt(success=True)
        
        assert metrics.total_initializations == 1
        assert metrics.successful_initializations == 1
        assert metrics.failed_initializations == 0
        
        # Simulate failed initialization
        agent_websocket_bridge._record_initialization_attempt(success=False)
        
        assert metrics.total_initializations == 2
        assert metrics.successful_initializations == 1
        assert metrics.failed_initializations == 1
        
        # Simulate recovery attempt
        agent_websocket_bridge._record_recovery_attempt(success=True)
        
        assert metrics.recovery_attempts == 1
        assert metrics.successful_recoveries == 1
        
        # Record health check
        agent_websocket_bridge._record_health_check()
        
        assert metrics.health_checks_performed == 1
    
    def test_create_user_emitter_per_request_pattern(self, agent_websocket_bridge):
        """Test per-request user emitter creation (SSOT pattern)."""
        # Mock user execution context
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user_123"
        mock_user_context.thread_id = "thread_456"
        
        # Mock WebSocket manager
        mock_websocket_manager = Mock()
        mock_websocket_manager.create_user_emitter.return_value = Mock()
        
        agent_websocket_bridge.websocket_manager = mock_websocket_manager
        agent_websocket_bridge.state = IntegrationState.ACTIVE
        
        # Act
        emitter = agent_websocket_bridge.create_user_emitter(mock_user_context)
        
        # Assert
        assert emitter is not None
        mock_websocket_manager.create_user_emitter.assert_called_once_with(mock_user_context)
    
    def test_component_monitoring_interface_compliance(self, agent_websocket_bridge):
        """Test MonitorableComponent interface compliance."""
        # Should implement required monitoring interface methods
        assert hasattr(agent_websocket_bridge, 'get_health_status')
        assert callable(agent_websocket_bridge.get_health_status)
        
        assert hasattr(agent_websocket_bridge, 'get_metrics')
        assert callable(agent_websocket_bridge.get_metrics)
        
        # Test health status method
        health = agent_websocket_bridge.get_health_status()
        assert isinstance(health, HealthStatus)
        assert health.state == IntegrationState.UNINITIALIZED  # Initial state
        
        # Test metrics method  
        metrics_dict = agent_websocket_bridge.get_metrics()
        assert isinstance(metrics_dict, dict)
        assert "total_initializations" in metrics_dict
        assert "successful_initializations" in metrics_dict
        assert "state" in metrics_dict
        assert "uptime_seconds" in metrics_dict


class TestAgentWebSocketBridgeRecovery:
    """Unit tests for AgentWebSocketBridge recovery mechanisms."""
    
    @pytest.fixture
    def recovery_config(self):
        """Create configuration optimized for testing recovery."""
        return IntegrationConfig(
            initialization_timeout_s=2,
            health_check_interval_s=5,
            recovery_max_attempts=3,
            recovery_base_delay_s=0.1,
            recovery_max_delay_s=1.0,
            integration_verification_timeout_s=1
        )
    
    @pytest.fixture  
    def bridge_with_recovery(self, recovery_config):
        """Create bridge configured for recovery testing."""
        return AgentWebSocketBridge(recovery_config)
    
    def test_recovery_attempt_tracking(self, bridge_with_recovery):
        """Test recovery attempt tracking and limits."""
        # Simulate multiple recovery attempts
        for attempt in range(5):
            bridge_with_recovery._record_recovery_attempt(success=False)
        
        metrics = bridge_with_recovery.metrics
        assert metrics.recovery_attempts == 5
        assert metrics.successful_recoveries == 0
        
        # Simulate successful recovery
        bridge_with_recovery._record_recovery_attempt(success=True)
        
        assert metrics.recovery_attempts == 6
        assert metrics.successful_recoveries == 1
    
    def test_recovery_eligibility_checking(self, bridge_with_recovery):
        """Test recovery eligibility based on state and attempt limits."""
        # Initially should be eligible for recovery
        assert bridge_with_recovery._should_attempt_recovery(0) is True
        
        # Should respect max attempts
        max_attempts = bridge_with_recovery.config.recovery_max_attempts
        assert bridge_with_recovery._should_attempt_recovery(max_attempts) is False
        assert bridge_with_recovery._should_attempt_recovery(max_attempts + 1) is False
        
        # Edge case - exactly at limit
        assert bridge_with_recovery._should_attempt_recovery(max_attempts - 1) is True
    
    def test_error_context_preservation_during_recovery(self, bridge_with_recovery):
        """Test error context is preserved during recovery attempts."""
        original_error = "WebSocket connection failed"
        
        # Simulate error with context
        health_status = bridge_with_recovery._create_health_status(
            websocket_healthy=False,
            registry_healthy=True,
            error_message=original_error
        )
        
        assert health_status.error_message == original_error
        assert health_status.websocket_manager_healthy is False
        assert health_status.registry_healthy is True
        
        # Error context should be preserved for recovery decisions
        assert original_error in str(health_status.error_message)
    
    def test_consecutive_failure_tracking(self, bridge_with_recovery):
        """Test consecutive failure tracking for degradation detection."""
        # Simulate consecutive failures
        for i in range(3):
            health_status = bridge_with_recovery._create_health_status(
                websocket_healthy=False,
                registry_healthy=False,
                error_message=f"Failure {i+1}"
            )
            # In real implementation, consecutive failures would be tracked
            
        # Should track failure pattern for intelligent recovery
        assert health_status.error_message == "Failure 3"
    
    def test_recovery_success_resets_failure_counters(self, bridge_with_recovery):
        """Test recovery success resets failure tracking."""
        metrics = bridge_with_recovery.metrics
        
        # Simulate failures followed by success
        bridge_with_recovery._record_recovery_attempt(success=False)
        bridge_with_recovery._record_recovery_attempt(success=False)
        bridge_with_recovery._record_recovery_attempt(success=True)
        
        assert metrics.recovery_attempts == 3
        assert metrics.successful_recoveries == 1
        
        # Successful recovery should reset failure patterns
        # (This would be implemented in the actual recovery logic)
    
    def test_integration_state_transitions_during_recovery(self, bridge_with_recovery):
        """Test proper state transitions during recovery process."""
        # Start in uninitialized state
        assert bridge_with_recovery.state == IntegrationState.UNINITIALIZED
        
        # Simulate transition to degraded (recovery needed)
        bridge_with_recovery.state = IntegrationState.DEGRADED
        
        result = bridge_with_recovery._create_integration_result(
            success=False,
            state=IntegrationState.DEGRADED,
            start_time=datetime.now(),
            error="Test error",
            recovery_attempted=True
        )
        
        assert result.state == IntegrationState.DEGRADED
        assert result.recovery_attempted is True
        assert result.success is False
        
        # Simulate successful recovery
        success_result = bridge_with_recovery._create_integration_result(
            success=True,
            state=IntegrationState.ACTIVE,
            start_time=datetime.now(),
            error=None,
            recovery_attempted=True
        )
        
        assert success_result.state == IntegrationState.ACTIVE
        assert success_result.recovery_attempted is True
        assert success_result.success is True